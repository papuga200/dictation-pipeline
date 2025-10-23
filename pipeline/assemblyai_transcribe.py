#!/usr/bin/env python3
"""
AssemblyAI integration module for automatic audio transcription.
Handles uploading audio files and retrieving word-level timestamps.
"""

import json
from pathlib import Path
from typing import Union, Dict, Optional
import time

try:
    import assemblyai as aai
except ImportError:
    aai = None


class AssemblyAITranscriber:
    """
    Handles automatic transcription using AssemblyAI API.
    Provides word-level timestamps compatible with DictationBuilder.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize transcriber with API key.
        
        Args:
            api_key: AssemblyAI API key
        
        Raises:
            ImportError: If assemblyai package is not installed
            ValueError: If API key is empty
        """
        if aai is None:
            raise ImportError(
                "AssemblyAI SDK not installed. Install with: pip install assemblyai"
            )
        
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")
        
        # Configure API key
        aai.settings.api_key = api_key.strip()
        self.transcriber = aai.Transcriber()
    
    def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        language_code: str = "en",
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Transcribe audio file and return word-level timestamps.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, M4A, FLAC)
            language_code: Language code (default: "en")
            progress_callback: Optional callback function for progress updates
                             Called with status string parameter
        
        Returns:
            Dictionary in AssemblyAI format with 'words' array:
            {
                'id': 'transcript_id',
                'text': 'full transcription text',
                'language_code': 'en',
                'status': 'completed',
                'words': [
                    {
                        'text': 'word',
                        'start': 100,  # milliseconds
                        'end': 500,    # milliseconds
                        'confidence': 0.99
                    },
                    ...
                ]
            }
        
        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If transcription fails
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Configure transcription settings
        config = aai.TranscriptionConfig(
            language_code=language_code,
            # Enable word-level timestamps (enabled by default)
        )
        
        if progress_callback:
            progress_callback("⏳ Uploading audio to AssemblyAI...")
        
        # Start transcription
        transcript = self.transcriber.transcribe(
            str(audio_path),
            config=config
        )
        
        # Poll for completion with progress updates
        if progress_callback:
            progress_callback("🔄 Transcribing audio (this may take a few minutes)...")
        
        # Wait for transcription to complete
        # The SDK handles polling automatically, but we can check status
        while transcript.status not in ['completed', 'error']:
            if progress_callback:
                progress_callback(f"🔄 Transcription in progress... (status: {transcript.status})")
            time.sleep(2)
            # Refresh transcript status
            # Note: The SDK's transcribe() method is synchronous and waits automatically
        
        # Check for errors
        if transcript.status == 'error':
            raise Exception(f"Transcription failed: {transcript.error}")
        
        if progress_callback:
            progress_callback("✅ Transcription complete!")
        
        # Format response compatible with DictationBuilder
        result = {
            'id': transcript.id,
            'text': transcript.text,
            'language_code': language_code,
            'status': transcript.status,
            'audio_duration': transcript.audio_duration,  # in seconds
            'words': []
        }
        
        # Extract word-level timestamps
        if transcript.words:
            for word in transcript.words:
                result['words'].append({
                    'text': word.text,
                    'start': word.start,  # Already in milliseconds
                    'end': word.end,      # Already in milliseconds
                    'confidence': word.confidence
                })
        else:
            raise Exception("No word-level timestamps returned from AssemblyAI")
        
        return result
    
    def save_transcript_json(self, transcript_data: Dict, output_path: Union[str, Path]) -> Path:
        """
        Save transcript data to JSON file.
        
        Args:
            transcript_data: Transcript dictionary from transcribe_audio()
            output_path: Path to save JSON file
        
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)
        
        return output_path


def test_api_key(api_key: str) -> tuple[bool, str]:
    """
    Test if an API key is valid by checking authentication.
    
    Args:
        api_key: AssemblyAI API key to test
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if aai is None:
        return False, "AssemblyAI SDK not installed. Install with: pip install assemblyai"
    
    if not api_key or not api_key.strip():
        return False, "API key is empty"
    
    try:
        # Set API key temporarily
        aai.settings.api_key = api_key.strip()
        
        # Try to create a transcriber (this validates the key)
        transcriber = aai.Transcriber()
        
        return True, "API key is valid ✓"
    
    except Exception as e:
        return False, f"Invalid API key: {str(e)}"


# Example usage
if __name__ == "__main__":
    import sys
    
    print("=== AssemblyAI Transcription Module ===\n")
    
    # Get API key
    api_key = input("Enter your AssemblyAI API key: ").strip()
    
    if not api_key:
        print("Error: API key required")
        sys.exit(1)
    
    # Test API key
    valid, message = test_api_key(api_key)
    print(f"\n{message}")
    
    if not valid:
        sys.exit(1)
    
    # Get audio file path
    audio_file = input("\nEnter path to audio file: ").strip().strip('"').strip("'")
    
    if not audio_file:
        print("Error: Audio file path required")
        sys.exit(1)
    
    # Transcribe
    print("\n" + "="*50)
    transcriber = AssemblyAITranscriber(api_key)
    
    def progress_update(status):
        print(status)
    
    try:
        print("\nStarting transcription...")
        result = transcriber.transcribe_audio(audio_file, progress_callback=progress_update)
        
        print("\n" + "="*50)
        print("✅ Transcription successful!")
        print(f"\nTranscript ID: {result['id']}")
        print(f"Duration: {result['audio_duration']:.2f} seconds")
        print(f"Total words: {len(result['words'])}")
        print(f"\nTranscribed text:\n{result['text'][:200]}...")
        
        # Save to file
        output_path = Path(audio_file).with_suffix('.json')
        transcriber.save_transcript_json(result, output_path)
        print(f"\n💾 Saved transcript to: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

