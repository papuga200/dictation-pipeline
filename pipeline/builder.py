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

# Grok AI alignment (optional - requires XAI_API_KEY)
try:
    from .grok_alignment import align_sentences_with_grok, GrokAlignerConfig
    GROK_AVAILABLE = True
except ImportError:
    GROK_AVAILABLE = False


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
            'repeats': 3,  # Deprecated - use dynamic_repetitions
            'pause_ms': 10000,
            'inter_sentence_pause_ms': 10000,
            'pad_ms': 100,
            'fade_ms': 8,
            'sample_rate': 44100,
            'dynamic_repetitions': {
                'enabled': True,
                'threshold_seconds': 4.5,
                'short_chunk_repeats': 3,
                'long_chunk_repeats': 5,
            },
            'alignment': {
                'method': 'hybrid',  # Options: 'fuzzy', 'grok', 'hybrid'
                'window_tokens': 4000,
                'elastic_gap': 10,
                'min_accept': 0.85,
                'warn_accept': 0.78,
                'token_ratio_cutoff': 92,
                'coverage_min': 0.80,
                'small_sentence_coverage_min': 0.67,
            },
            'grok': {
                'model': 'grok-4-fast',
                'temperature': 0.1,
                'max_workers': 5,
                'max_retries': 3,
                'timeout': 30,
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
    
    def _perform_alignment(
        self,
        sentences: List[str],
        words: List[dict],
        method: str
    ) -> Tuple[List[Optional[Tuple[int, int]]], Dict]:
        """
        Perform sentence alignment using specified method.
        
        Args:
            sentences: List of sentence strings
            words: List of word dicts with timestamps
            method: Alignment method ('fuzzy', 'grok', or 'hybrid')
        
        Returns:
            (sentence_spans, alignment_report)
        """
        pad_ms = self.config['pad_ms']
        
        if method == 'grok':
            # Grok AI alignment only
            if not GROK_AVAILABLE:
                raise RuntimeError(
                    "Grok alignment not available. Install: pip install openai pydantic\n"
                    "And set XAI_API_KEY environment variable."
                )
            
            print("  Using: Grok AI alignment (grok-4-fast)")
            grok_config = GrokAlignerConfig()
            if 'grok' in self.config:
                for key, value in self.config['grok'].items():
                    if hasattr(grok_config, key):
                        setattr(grok_config, key, value)
            
            spans, report = align_sentences_with_grok(sentences, words, grok_config, pad_ms)
            
            # Tag all details with method
            for detail in report.get('details', []):
                detail['method'] = 'grok'
            
            # Add method stats to global
            report['global']['methods'] = {
                'grok': report['global']['aligned'],
                'fuzzy': 0
            }
            
            return spans, report
        
        elif method == 'hybrid':
            # Hybrid: Try Grok first, fallback to fuzzy for failures
            if not GROK_AVAILABLE:
                print("  ⚠️  Grok not available, using fuzzy matching only")
                method = 'fuzzy'
            else:
                print("  Using: Hybrid (Grok AI → Fuzzy fallback)")
                
                # Try Grok alignment
                grok_config = GrokAlignerConfig()
                if 'grok' in self.config:
                    for key, value in self.config['grok'].items():
                        if hasattr(grok_config, key):
                            setattr(grok_config, key, value)
                
                grok_spans, grok_report = align_sentences_with_grok(
                    sentences, words, grok_config, pad_ms
                )
                
                # Tag Grok details with method
                for detail in grok_report.get('details', []):
                    detail['method'] = 'grok'
                
                # Find failures
                failed_indices = [i for i, span in enumerate(grok_spans) if span is None]
                
                if not failed_indices:
                    # All succeeded with Grok
                    print(f"  [OK] Grok: {grok_report['global']['aligned']}/{len(sentences)}")
                    # Add method stats to global
                    grok_report['global']['methods'] = {
                        'grok': grok_report['global']['aligned'],
                        'fuzzy': 0
                    }
                    return grok_spans, grok_report
                
                # Use fuzzy matching for failures
                print(f"  [OK] Grok: {grok_report['global']['aligned']}/{len(sentences)}")
                print(f"  [->] Fuzzy fallback for {len(failed_indices)} failed sentences...")
                
                align_config = AlignmentConfig()
                if 'alignment' in self.config:
                    for key, value in self.config['alignment'].items():
                        if hasattr(align_config, key) and key != 'method':
                            setattr(align_config, key, value)
                
                failed_sentences = [sentences[i] for i in failed_indices]
                fuzzy_spans, fuzzy_report = align_sentences_to_words(
                    failed_sentences, words, align_config, pad_ms
                )
                
                # Tag fuzzy details with method and adjust indices
                for detail in fuzzy_report.get('details', []):
                    detail['method'] = 'fuzzy'
                    # Adjust idx to match original sentence list
                    original_idx = failed_indices[detail['idx'] - 1] + 1
                    detail['idx'] = original_idx
                
                # Merge results
                final_spans = grok_spans.copy()
                for i, fuzzy_idx in enumerate(failed_indices):
                    final_spans[fuzzy_idx] = fuzzy_spans[i]
                
                # Count successful fuzzy alignments
                fuzzy_successes = sum(1 for s in fuzzy_spans if s is not None)
                
                # Merge reports
                merged_report = {
                    "global": {
                        "num_sentences": len(sentences),
                        "aligned": sum(1 for s in final_spans if s is not None),
                        "unaligned": sum(1 for s in final_spans if s is None),
                        "warnings": grok_report['global']['warnings'] + fuzzy_report['global']['warnings'],
                        "methods": {
                            "grok": grok_report['global']['aligned'],
                            "fuzzy": fuzzy_successes
                        }
                    },
                    "details": grok_report.get('details', []) + fuzzy_report.get('details', [])
                }
                
                print(f"  [OK] Fuzzy: {fuzzy_successes}/{len(failed_sentences)}")
                print(f"  [OK] Total: {merged_report['global']['aligned']}/{len(sentences)}")
                
                return final_spans, merged_report
        
        # Default: Fuzzy matching only
        print("  Using: Fuzzy matching (traditional)")
        align_config = AlignmentConfig()
        if 'alignment' in self.config:
            for key, value in self.config['alignment'].items():
                if hasattr(align_config, key) and key != 'method':
                    setattr(align_config, key, value)
        
        spans, report = align_sentences_to_words(sentences, words, align_config, pad_ms)
        
        # Tag all details with method
        for detail in report.get('details', []):
            detail['method'] = 'fuzzy'
        
        # Add method stats to global
        report['global']['methods'] = {
            'grok': 0,
            'fuzzy': report['global']['aligned']
        }
        
        return spans, report
    
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
        
        # Determine alignment method
        alignment_method = self.config.get('alignment', {}).get('method', 'fuzzy')
        
        sentence_spans, aligner_report = self._perform_alignment(
            sentences, words, alignment_method
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
        
        # Prepare dynamic repetition parameters
        dyn_rep = self.config.get('dynamic_repetitions', {})
        if dyn_rep.get('enabled', False):
            # Use dynamic repetitions
            sentence_timing_info = audio_pipeline.build_dictation_audio(
                source_audio=audio_input,
                sentence_spans=valid_span_list,
                output_path=final_audio,
                tempo=self.config['tempo'],
                repeats=None,  # Signal to use dynamic repetitions
                pause_ms=self.config['pause_ms'],
                inter_sentence_pause_ms=self.config.get('inter_sentence_pause_ms', self.config['pause_ms']),
                fade_ms=self.config['fade_ms'],
                dynamic_reps_enabled=True,
                dynamic_threshold_seconds=dyn_rep.get('threshold_seconds', 4.5),
                dynamic_short_repeats=dyn_rep.get('short_chunk_repeats', 3),
                dynamic_long_repeats=dyn_rep.get('long_chunk_repeats', 5)
            )
        else:
            # Use fixed repetitions
            sentence_timing_info = audio_pipeline.build_dictation_audio(
                source_audio=audio_input,
                sentence_spans=valid_span_list,
                output_path=final_audio,
                tempo=self.config['tempo'],
                repeats=self.config['repeats'],
                pause_ms=self.config['pause_ms'],
                inter_sentence_pause_ms=self.config.get('inter_sentence_pause_ms', self.config['pause_ms']),
                fade_ms=self.config['fade_ms'],
                dynamic_reps_enabled=False
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

