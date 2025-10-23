#!/usr/bin/env python3
"""
Quick script to convert WAV files to MP3
Usage: python to_mp3.py input.wav [output.mp3]
"""

import sys
import os
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub not installed. Install with: pip install pydub")
    sys.exit(1)


def convert_wav_to_mp3(input_path, output_path=None, bitrate="192k"):
    """
    Convert WAV file to MP3
    
    Args:
        input_path: Path to input WAV file
        output_path: Path to output MP3 file (optional, defaults to same name with .mp3)
        bitrate: MP3 bitrate (default: 192k)
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found")
        return False
    
    if not input_path.suffix.lower() == '.wav':
        print(f"Warning: Input file doesn't have .wav extension")
    
    # Default output path if not specified
    if output_path is None:
        output_path = input_path.with_suffix('.mp3')
    else:
        output_path = Path(output_path)
        # If output_path is a directory, create filename in that directory
        if output_path.is_dir():
            output_path = output_path / input_path.with_suffix('.mp3').name
    
    try:
        print(f"Loading {input_path}...")
        audio = AudioSegment.from_wav(str(input_path))
        
        print(f"Converting to MP3 (bitrate: {bitrate})...")
        audio.export(str(output_path), format="mp3", bitrate=bitrate)
        
        print(f"✓ Successfully converted to {output_path}")
        print(f"  Original size: {input_path.stat().st_size / 1024:.1f} KB")
        print(f"  MP3 size: {output_path.stat().st_size / 1024:.1f} KB")
        return True
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False


def main():
    print("=== WAV to MP3 Converter ===\n")
    
    # Prompt for input file
    input_file = input("Enter the path to the WAV file: ").strip()
    
    # Remove quotes if user pasted path with quotes
    input_file = input_file.strip('"').strip("'")
    
    if not input_file:
        print("Error: No input file specified")
        sys.exit(1)
    
    # Prompt for output file (optional)
    output_file = input("Enter output MP3 path (or press Enter for auto-naming): ").strip()
    output_file = output_file.strip('"').strip("'") if output_file else None
    
    print()  # Blank line for readability
    convert_wav_to_mp3(input_file, output_file)


if __name__ == "__main__":
    main()

