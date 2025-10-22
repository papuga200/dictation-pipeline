"""
Main pipeline orchestrator for dictation building.
Coordinates alignment, audio processing, and manifest generation.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import shutil

from .segmentation import segment_sentences
from .alignment import align_sentences_to_words, AlignmentConfig
from .audio import (
    AudioPipeline, convert_to_wav, get_audio_info, check_ffmpeg
)
from .manifest import (
    create_final_manifest, create_alignment_report,
    save_manifests, generate_alignment_summary
)


class DictationBuilder:
    """Main class for building dictation audio from source materials."""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize builder with configuration.
        
        Args:
            config: Configuration dictionary (optional)
        """
        # Start with defaults and merge any provided overrides to avoid missing keys
        self.config = self._default_config()
        if config:
            self._merge_config(config)
        
        # Check FFmpeg availability
        if not check_ffmpeg():
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.\n"
                "Download from: https://ffmpeg.org/download.html"
            )
    
    @staticmethod
    def _default_config() -> dict:
        """Return default configuration."""
        return {
            'tempo': 0.92,
            'repeats': 3,
            'pause_ms': 10000,
            'inter_sentence_pause_ms': 10000,
            'pad_ms': 100,
            'fade_ms': 8,
            'sample_rate': 44100,
            'alignment': {
                'window_tokens': 4000,
                'elastic_gap': 10,
                'min_accept': 0.85,
                'warn_accept': 0.78,
                'token_ratio_cutoff': 92,
                'coverage_min': 0.80,
                'small_sentence_coverage_min': 0.67,
            }
        }

    def _merge_config(self, custom_config: dict) -> None:
        """Recursively merge custom configuration into defaults."""
        def _merge(dst: dict, src: dict) -> None:
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    _merge(dst[k], v)
                else:
                    dst[k] = v
        _merge(self.config, custom_config)
    
    def load_words_json(self, json_path: Union[Path, bytes, str]) -> Tuple[List[dict], dict]:
        """
        Load and parse words JSON file.
        Supports both spec format and AssemblyAI format.
        
        Args:
            json_path: Path to JSON file, JSON bytes, or JSON string
        
        Returns:
            (words_list, metadata_dict)
        """
        if isinstance(json_path, bytes):
            data = json.loads(json_path.decode('utf-8'))
        elif isinstance(json_path, str):
            if json_path.startswith('{'):
                # It's JSON string
                data = json.loads(json_path)
            else:
                # It's a file path
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
        else:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # Detect format
        if 'words' in data:
            # Could be spec format or AssemblyAI format
            words = data['words']
            
            # Check if it's AssemblyAI format (has 'text', 'start', 'end', but might have extras)
            if words and all('text' in w and 'start' in w and 'end' in w for w in words):
                # Valid format
                metadata = {
                    'format': 'assemblyai' if 'language_code' in data else 'spec',
                    'audio_id': data.get('audio_id', data.get('id', 'unknown')),
                    'sr_hz': data.get('sr_hz', None)
                }
                return words, metadata
        
        raise ValueError("Invalid words JSON format. Expected 'words' array with 'text', 'start', 'end' fields.")
    
    def build(
        self,
        canonical_text: str,
        words_json: Union[Path, bytes, str],
        audio_file: Union[Path, bytes],
        output_dir: Optional[Path] = None,
        manual_adjustments: Optional[List[Dict]] = None
    ) -> Dict[str, Path]:
        """
        Build dictation audio from inputs.
        
        Args:
            canonical_text: The canonical text to dictate
            words_json: Path to or content of words JSON
            audio_file: Path to or bytes of source audio
            output_dir: Output directory (if None, uses temp dir)
            manual_adjustments: Optional list of manual time adjustments
                Format: [{"sentence_idx": 1, "start_ms": 1000, "end_ms": 5000}, ...]
        
        Returns:
            Dictionary with paths to output files:
                - 'audio': Path to dictation_final.wav
                - 'manifest': Path to final_manifest.json
                - 'report': Path to alignment_report.json
                - 'work_dir': Path to working directory
        """
        # Setup working directory
        if output_dir is None:
            work_dir = Path(tempfile.mkdtemp(prefix='dictation_'))
        else:
            work_dir = Path(output_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        
        input_dir = work_dir / 'input'
        output_dir_final = work_dir / 'output'
        input_dir.mkdir(exist_ok=True)
        output_dir_final.mkdir(exist_ok=True)
        
        print("📁 Working directory:", work_dir)
        
        # Step 1: Load and prepare inputs
        print("\n📥 Loading inputs...")
        
        # Load words JSON
        words, metadata = self.load_words_json(words_json)
        print(f"  ✓ Loaded {len(words)} word timestamps ({metadata['format']} format)")
        
        # Save/prepare audio file
        if isinstance(audio_file, bytes):
            # Audio provided as bytes
            audio_input = input_dir / 'source_audio.wav'
            temp_audio = input_dir / 'temp_audio'
            temp_audio.write_bytes(audio_file)
            convert_to_wav(temp_audio, audio_input, sample_rate=self.config['sample_rate'])
            temp_audio.unlink()
        else:
            # Audio provided as path
            audio_path = Path(audio_file)
            if audio_path.suffix.lower() != '.wav':
                # Convert to WAV
                audio_input = input_dir / 'source_audio.wav'
                convert_to_wav(audio_path, audio_input, sample_rate=self.config['sample_rate'])
            else:
                audio_input = audio_path
        
        audio_info = get_audio_info(audio_input)
        print(f"  ✓ Audio: {audio_info['duration_ms']/1000:.1f}s, {audio_info['sample_rate']}Hz")
        
        # Step 2: Segment sentences
        print("\n📝 Segmenting sentences...")
        sentences = segment_sentences(canonical_text, strip_quotes=True)
        print(f"  ✓ Found {len(sentences)} sentences")
        
        # Step 3: Align sentences to words
        print("\n🔍 Aligning sentences to word timestamps...")
        
        # Create alignment config
        align_config = AlignmentConfig()
        if 'alignment' in self.config:
            for key, value in self.config['alignment'].items():
                if hasattr(align_config, key):
                    setattr(align_config, key, value)
        
        sentence_spans, aligner_report = align_sentences_to_words(
            sentences, words, config=align_config, pad_ms=self.config['pad_ms']
        )
        
        print(f"  ✓ Aligned: {aligner_report['global']['aligned']}/{len(sentences)}")
        if aligner_report['global']['warnings'] > 0:
            print(f"  ⚠ Warnings: {aligner_report['global']['warnings']}")
        if aligner_report['global']['unaligned'] > 0:
            print(f"  ✗ Failed: {aligner_report['global']['unaligned']}")
        
        # Step 4: Apply manual adjustments if provided
        if manual_adjustments:
            print(f"\n✏️  Applying {len(manual_adjustments)} manual adjustments...")
            for adj in manual_adjustments:
                idx = adj['sentence_idx']
                if 1 <= idx <= len(sentence_spans):
                    sentence_spans[idx - 1] = (adj['start_ms'], adj['end_ms'])
                    print(f"  ✓ Adjusted sentence {idx}: {adj['start_ms']}ms - {adj['end_ms']}ms")
        
        # Step 5: Build audio
        print("\n🎵 Building dictation audio...")
        
        # Filter out None spans (failed alignments)
        valid_spans = [(i, span) for i, span in enumerate(sentence_spans) if span is not None]
        
        if not valid_spans:
            raise RuntimeError("No sentences were successfully aligned. Cannot build audio.")
        
        print(f"  Processing {len(valid_spans)} sentences...")
        
        # Create audio pipeline
        audio_pipeline = AudioPipeline(work_dir / 'audio_work', sample_rate=self.config['sample_rate'])
        
        # Build audio with only valid spans
        valid_span_list = [span for _, span in valid_spans]
        
        final_audio = output_dir_final / 'dictation_final.wav'
        
        sentence_timing_info = audio_pipeline.build_dictation_audio(
            source_audio=audio_input,
            sentence_spans=valid_span_list,
            output_path=final_audio,
            tempo=self.config['tempo'],
            repeats=self.config['repeats'],
            pause_ms=self.config['pause_ms'],
            inter_sentence_pause_ms=self.config.get('inter_sentence_pause_ms', self.config['pause_ms']),
            fade_ms=self.config['fade_ms']
        )
        
        final_audio_info = get_audio_info(final_audio)
        print(f"  ✓ Created dictation audio: {final_audio_info['duration_ms']/1000:.1f}s")
        
        # Step 6: Generate manifests
        print("\n📋 Generating manifests...")
        
        alignment_report = create_alignment_report(aligner_report, sentences)
        
        manifest = create_final_manifest(
            audio_input=audio_input,
            sentences=sentences,
            sentence_spans=sentence_spans,
            sentence_timing_info=sentence_timing_info,
            alignment_report=alignment_report,
            tempo=self.config['tempo'],
            repeats=self.config['repeats'],
            pause_ms=self.config['pause_ms'],
            total_duration_ms=final_audio_info['duration_ms'],
            pad_ms=self.config['pad_ms']
        )
        
        manifest_path, report_path = save_manifests(
            output_dir_final, manifest, alignment_report
        )
        
        print(f"  ✓ Saved final_manifest.json")
        print(f"  ✓ Saved alignment_report.json")
        
        # Print summary
        print("\n" + "="*50)
        print("✅ BUILD COMPLETE")
        print("="*50)
        print(generate_alignment_summary(alignment_report))
        print(f"\nOutput files:")
        print(f"  • Audio: {final_audio}")
        print(f"  • Manifest: {manifest_path}")
        print(f"  • Report: {report_path}")
        
        return {
            'audio': final_audio,
            'manifest': manifest_path,
            'report': report_path,
            'work_dir': work_dir
        }


def build_from_files(
    text_file: Path,
    words_json_file: Path,
    audio_file: Path,
    output_dir: Path,
    config: Optional[dict] = None
) -> Dict[str, Path]:
    """
    Convenience function to build dictation from file paths.
    
    Args:
        text_file: Path to canonical text file
        words_json_file: Path to words JSON file
        audio_file: Path to audio file
        output_dir: Output directory
        config: Optional configuration dictionary
    
    Returns:
        Dictionary with output file paths
    """
    # Load text
    with open(text_file, 'r', encoding='utf-8') as f:
        canonical_text = f.read()
    
    # Build
    builder = DictationBuilder(config)
    return builder.build(
        canonical_text=canonical_text,
        words_json=words_json_file,
        audio_file=audio_file,
        output_dir=output_dir
    )

