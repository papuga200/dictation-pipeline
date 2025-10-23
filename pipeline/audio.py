"""
Audio processing utilities using FFmpeg.
Handles cutting, tempo changes, silence generation, and concatenation.
"""

import subprocess
import tempfile
import os
import json
from pathlib import Path
from typing import List, Union, Tuple


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_ffmpeg(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """
    Run ffmpeg command with given arguments.
    
    Args:
        args: List of ffmpeg arguments
        check: If True, raise exception on error
    
    Returns:
        CompletedProcess object
    """
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error'] + args
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def run_ffprobe(args: List[str]) -> subprocess.CompletedProcess:
    """Run ffprobe command."""
    cmd = ['ffprobe', '-v', 'error'] + args
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def ms_to_timestamp(ms: int) -> str:
    """
    Convert milliseconds to FFmpeg timestamp format HH:MM:SS.mmm
    
    Args:
        ms: Milliseconds
    
    Returns:
        Timestamp string
    """
    total_seconds = ms / 1000.0
    hours = int(total_seconds // 3600)
    total_seconds -= hours * 3600
    minutes = int(total_seconds // 60)
    seconds = total_seconds - minutes * 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def get_audio_info(audio_path: Path) -> dict:
    """
    Get audio file information using ffprobe.
    
    Returns:
        Dictionary with duration_ms, sample_rate, channels
    """
    result = run_ffprobe([
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        str(audio_path)
    ])
    
    info = json.loads(result.stdout)
    
    duration_s = float(info['format']['duration'])
    
    # Find audio stream
    audio_stream = None
    for stream in info['streams']:
        if stream['codec_type'] == 'audio':
            audio_stream = stream
            break
    
    if not audio_stream:
        raise ValueError(f"No audio stream found in {audio_path}")
    
    return {
        'duration_ms': int(duration_s * 1000),
        'sample_rate': int(audio_stream.get('sample_rate', 44100)),
        'channels': int(audio_stream.get('channels', 1))
    }


def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 44100, channels: int = 1):
    """
    Convert any audio format to WAV with specified parameters.
    
    Args:
        input_path: Input audio file
        output_path: Output WAV file
        sample_rate: Target sample rate (Hz)
        channels: Number of channels (1=mono, 2=stereo)
    """
    run_ffmpeg([
        '-y',
        '-i', str(input_path),
        '-ar', str(sample_rate),
        '-ac', str(channels),
        '-acodec', 'pcm_s16le',
        str(output_path)
    ])


def cut_audio_clip(
    input_path: Path,
    output_path: Path,
    start_ms: int,
    end_ms: int,
    fade_ms: int = 8
) -> None:
    """
    Extract a clip from audio file with optional fade in/out to prevent clicks.
    
    Args:
        input_path: Source audio file
        output_path: Output clip file
        start_ms: Start time in milliseconds
        end_ms: End time in milliseconds
        fade_ms: Fade duration in milliseconds for in/out
    """
    # Ensure valid times
    start_ms = max(0, start_ms)
    duration_ms = max(1, end_ms - start_ms)
    
    start_ts = ms_to_timestamp(start_ms)
    duration_ts = ms_to_timestamp(duration_ms)
    
    # Build fade filter
    fade_sec = fade_ms / 1000.0
    duration_sec = duration_ms / 1000.0
    fade_out_start = max(0, duration_sec - fade_sec)
    
    audio_filter = f"afade=t=in:ss=0:d={fade_sec},afade=t=out:st={fade_out_start}:d={fade_sec}"
    
    run_ffmpeg([
        '-y',
        '-ss', start_ts,
        '-t', duration_ts,
        '-i', str(input_path),
        '-af', audio_filter,
        '-acodec', 'pcm_s16le',
        str(output_path)
    ])


def change_tempo(
    input_path: Path,
    output_path: Path,
    tempo: float = 0.92
) -> None:
    """
    Change audio tempo while preserving pitch using atempo filter.
    
    Args:
        input_path: Source audio file
        output_path: Output file
        tempo: Tempo multiplier (0.5 to 2.0). 0.92 = 92% speed
    """
    if tempo < 0.5 or tempo > 2.0:
        raise ValueError(f"Tempo {tempo} out of range [0.5, 2.0]")
    
    # For tempos outside [0.5, 2.0], chain multiple atempo filters
    # But 0.92 is within range, so single filter is fine
    run_ffmpeg([
        '-y',
        '-i', str(input_path),
        '-filter:a', f'atempo={tempo}',
        '-acodec', 'pcm_s16le',
        str(output_path)
    ])


def generate_silence(
    output_path: Path,
    duration_ms: int,
    sample_rate: int = 44100,
    channels: int = 1
) -> None:
    """
    Generate a silent audio file.
    
    Args:
        output_path: Output file path
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz
        channels: Number of channels
    """
    duration_sec = duration_ms / 1000.0
    channel_layout = 'mono' if channels == 1 else 'stereo'
    
    run_ffmpeg([
        '-y',
        '-f', 'lavfi',
        '-i', f'anullsrc=r={sample_rate}:cl={channel_layout}',
        '-t', f'{duration_sec:.3f}',
        '-acodec', 'pcm_s16le',
        str(output_path)
    ])


def concatenate_audio_files(
    input_files: List[Path],
    output_path: Path
) -> None:
    """
    Concatenate multiple audio files into one.
    
    Args:
        input_files: List of audio file paths
        output_path: Output file path
    """
    # Create temporary concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_file = f.name
        for file_path in input_files:
            # Use forward slashes for FFmpeg even on Windows
            file_str = str(file_path.resolve()).replace('\\', '/')
            f.write(f"file '{file_str}'\n")
    
    try:
        run_ffmpeg([
            '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'pcm_s16le',
            str(output_path)
        ])
    finally:
        os.unlink(concat_file)


def build_sentence_audio_block(
    sentence_clip: Path,
    output_path: Path,
    silence_path: Path,
    repeats: int = 3
) -> List[Path]:
    """
    Build a sentence block: clip + silence + clip + silence + clip
    
    Args:
        sentence_clip: Path to the tempo-adjusted sentence clip
        output_path: Where to save the block (not used, returns list instead)
        silence_path: Path to silence audio file
        repeats: Number of times to repeat the sentence
    
    Returns:
        List of paths in order for concatenation
    """
    parts = []
    for i in range(repeats):
        parts.append(sentence_clip)
        if i < repeats - 1:  # Don't add silence after last repeat
            parts.append(silence_path)
    
    return parts


class AudioPipeline:
    """Manages audio processing pipeline for dictation building."""
    
    def __init__(self, work_dir: Path, sample_rate: int = 44100):
        """
        Args:
            work_dir: Working directory for temporary files
            sample_rate: Target sample rate
        """
        self.work_dir = Path(work_dir)
        self.sample_rate = sample_rate
        
        # Create subdirectories
        self.clips_dir = self.work_dir / 'clips'
        self.tempo_dir = self.work_dir / 'tempo'
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.tempo_dir.mkdir(parents=True, exist_ok=True)
        
        # Silence file (will be created when needed)
        self.silence_file = None
    
    def prepare_silence(self, duration_ms: int) -> Path:
        """Create or return silence file."""
        silence_path = self.work_dir / f'silence_{duration_ms}ms.wav'
        
        if not silence_path.exists():
            generate_silence(silence_path, duration_ms, self.sample_rate, channels=1)
        
        self.silence_file = silence_path
        return silence_path
    
    def process_sentence(
        self,
        source_audio: Path,
        sentence_idx: int,
        start_ms: int,
        end_ms: int,
        tempo: float,
        fade_ms: int = 8
    ) -> Path:
        """
        Process a single sentence: cut and apply tempo.
        
        Returns:
            Path to tempo-adjusted clip
        """
        # Cut clip
        clip_path = self.clips_dir / f'sent_{sentence_idx:04d}.wav'
        cut_audio_clip(source_audio, clip_path, start_ms, end_ms, fade_ms)
        
        # Apply tempo
        tempo_path = self.tempo_dir / f'sent_{sentence_idx:04d}_tempo.wav'
        change_tempo(clip_path, tempo_path, tempo)
        
        return tempo_path
    
    def build_dictation_audio(
        self,
        source_audio: Path,
        sentence_spans: List[Tuple[int, int]],
        output_path: Path,
        tempo: float = 0.92,
        repeats: int = 3,
        pause_ms: int = 10000,
        inter_sentence_pause_ms: int = 10000,
        fade_ms: int = 8,
        dynamic_reps_enabled: bool = False,
        dynamic_threshold_seconds: float = 4.5,
        dynamic_short_repeats: int = 3,
        dynamic_long_repeats: int = 5
    ) -> List[dict]:
        """
        Build complete dictation audio from sentence spans.
        
        Args:
            source_audio: Source audio file
            sentence_spans: List of (start_ms, end_ms) tuples
            output_path: Output file path
            tempo: Tempo multiplier
            repeats: Number of repeats per sentence (used if dynamic_reps_enabled=False)
            pause_ms: Pause between repeats (ms)
            inter_sentence_pause_ms: Pause between different sentences (ms)
            fade_ms: Fade duration for clips
            dynamic_reps_enabled: If True, use dynamic repetitions based on chunk length
            dynamic_threshold_seconds: Threshold for determining short vs long chunks
            dynamic_short_repeats: Repetitions for chunks < threshold
            dynamic_long_repeats: Repetitions for chunks >= threshold
        
        Returns:
            List of dictionaries with timing info for each sentence
        """
        # Prepare silence files
        silence_repeat = self.prepare_silence(pause_ms)
        
        if inter_sentence_pause_ms != pause_ms:
            silence_inter = self.work_dir / f'silence_{inter_sentence_pause_ms}ms.wav'
            generate_silence(silence_inter, inter_sentence_pause_ms, self.sample_rate, channels=1)
        else:
            silence_inter = silence_repeat
        
        # Process all sentences and build concat list
        all_parts = []
        sentence_info = []
        current_offset_ms = 0
        
        for idx, (start_ms, end_ms) in enumerate(sentence_spans, start=1):
            # Calculate original chunk duration (before tempo change)
            original_chunk_duration_ms = end_ms - start_ms
            original_chunk_duration_seconds = original_chunk_duration_ms / 1000.0
            
            # Determine repetitions for this sentence
            if dynamic_reps_enabled:
                if original_chunk_duration_seconds < dynamic_threshold_seconds:
                    sentence_repeats = dynamic_short_repeats
                else:
                    sentence_repeats = dynamic_long_repeats
            else:
                sentence_repeats = repeats
            
            # Process sentence
            tempo_clip = self.process_sentence(
                source_audio, idx, start_ms, end_ms, tempo, fade_ms
            )
            
            # Get clip duration after tempo change
            clip_info = get_audio_info(tempo_clip)
            clip_duration_ms = clip_info['duration_ms']
            
            # Build sentence block
            block_parts = []
            repeat_offsets = []
            
            for rep in range(sentence_repeats):
                block_parts.append(tempo_clip)
                
                # Record offset for this repeat
                repeat_start = current_offset_ms
                repeat_end = current_offset_ms + clip_duration_ms
                repeat_offsets.append((repeat_start, repeat_end))
                
                current_offset_ms += clip_duration_ms
                
                if rep < sentence_repeats - 1:
                    # Add pause between repeats
                    block_parts.append(silence_repeat)
                    current_offset_ms += pause_ms
            
            # Add inter-sentence pause
            block_parts.append(silence_inter)
            current_offset_ms += inter_sentence_pause_ms
            
            all_parts.extend(block_parts)
            
            # Store info
            sentence_info.append({
                'idx': idx,
                'source_span_ms': {'start': start_ms, 'end': end_ms},
                'clip_duration_ms': clip_duration_ms,
                'repeat_offsets_ms': repeat_offsets,
                'block_end_ms': current_offset_ms,
                'num_repeats': sentence_repeats,  # Track actual repetitions used
                'original_duration_seconds': original_chunk_duration_seconds
            })
        
        # Concatenate all parts
        concatenate_audio_files(all_parts, output_path)
        
        return sentence_info

