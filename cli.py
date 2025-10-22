"""
Command-line interface for Dictation Builder.
Allows building dictation from config file and command-line arguments.
"""

import argparse
import yaml
from pathlib import Path
import sys

from pipeline.builder import build_from_files


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description='Build dictation audio from source recording and word timestamps'
    )
    
    parser.add_argument(
        'text_file',
        type=Path,
        help='Path to canonical text file (.txt)'
    )
    
    parser.add_argument(
        'words_json',
        type=Path,
        help='Path to word timestamps JSON file'
    )
    
    parser.add_argument(
        'audio_file',
        type=Path,
        help='Path to source audio file (.wav, .mp3, etc.)'
    )
    
    parser.add_argument(
        'output_dir',
        type=Path,
        help='Output directory for generated files'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=Path,
        default=Path('config.yaml'),
        help='Path to configuration YAML file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--tempo',
        type=float,
        help='Override tempo setting (0.5-2.0)'
    )
    
    parser.add_argument(
        '--repeats',
        type=int,
        help='Override repeats setting'
    )
    
    parser.add_argument(
        '--pause',
        type=int,
        help='Override pause duration in milliseconds'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.text_file.exists():
        print(f"Error: Text file not found: {args.text_file}", file=sys.stderr)
        sys.exit(1)
    
    if not args.words_json.exists():
        print(f"Error: Words JSON not found: {args.words_json}", file=sys.stderr)
        sys.exit(1)
    
    if not args.audio_file.exists():
        print(f"Error: Audio file not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)
    
    # Load config
    config = None
    if args.config.exists():
        print(f"Loading configuration from {args.config}")
        config = load_config(args.config)
    else:
        print(f"Warning: Config file not found: {args.config}")
        print("Using default configuration")
    
    # Apply command-line overrides
    if config and args.tempo:
        config['tempo'] = args.tempo
    if config and args.repeats:
        config['repeats'] = args.repeats
    if config and args.pause:
        config['pause_ms'] = args.pause
    
    # Build
    print("\n" + "="*60)
    print("DICTATION BUILDER - CLI")
    print("="*60)
    
    try:
        result = build_from_files(
            text_file=args.text_file,
            words_json_file=args.words_json,
            audio_file=args.audio_file,
            output_dir=args.output_dir,
            config=config
        )
        
        print("\n" + "="*60)
        print("SUCCESS")
        print("="*60)
        print(f"\nOutput files:")
        print(f"  Audio:    {result['audio']}")
        print(f"  Manifest: {result['manifest']}")
        print(f"  Report:   {result['report']}")
        print()
        
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

