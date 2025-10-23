# AssemblyAI Auto-Transcription Integration

## Overview

The Dictation Builder now supports **automatic audio transcription** using [AssemblyAI's Speech-to-Text API](https://www.assemblyai.com/). This eliminates the need to manually create or upload word-level timestamp JSON files.

## Benefits

- ⚡ **Faster workflow**: Skip manual JSON creation
- 🎯 **Accurate word timestamps**: Get millisecond-precise word boundaries
- 🌍 **Multi-language support**: Transcribe audio in multiple languages
- 📊 **High quality**: Industry-leading speech recognition accuracy

## Setup

### 1. Install AssemblyAI SDK

The SDK is included in `requirements.txt`. If you haven't installed it yet:

```bash
pip install assemblyai
```

Or reinstall all dependencies:

```bash
pip install -r requirements.txt
```

### 2. Get API Key

1. Sign up at [AssemblyAI](https://www.assemblyai.com/)
2. Navigate to your dashboard
3. Copy your API key from the dashboard

### 3. Add API Key to the App

1. Open the Dictation Builder app (run `streamlit run app.py`)
2. In the **sidebar**, expand **"🤖 AssemblyAI Auto-Transcription"**
3. Paste your API key in the text field
4. Click **"🔑 Test API Key"** to verify it works

## Usage

### Auto-Transcription Workflow

Once your API key is configured:

1. **Step 1: Upload & Configure**
   - Paste your canonical text (the reference text)
   - Select **"🤖 Auto-transcribe with AssemblyAI"** mode
   - Upload your audio file (WAV, MP3, M4A, or FLAC)
   - Click **"🤖 Auto-Transcribe & Load"**
   - Wait for transcription (usually 1-3 minutes for typical audio)

2. **Step 2: Review & Adjust**
   - Review automatic alignment results
   - The transcribed text will be shown for reference
   - Manually adjust any problematic sentence boundaries if needed

3. **Step 3: Build & Download**
   - Build your dictation audio
   - Download as MP3 (compressed for smaller file size)

### Manual JSON Workflow (Original)

If you already have a word timestamps JSON file:

1. Select **"📄 Upload JSON manually"** mode
2. Upload both the JSON file and audio file
3. Continue with steps 2 and 3 as usual

## How It Works

### Transcription Process

1. **Upload**: Your audio file is securely uploaded to AssemblyAI's servers
2. **Transcription**: AssemblyAI's AI model transcribes the audio with word-level timestamps
3. **Format**: The response is automatically formatted to match the expected JSON structure:

```json
{
  "id": "transcript_abc123",
  "text": "Full transcribed text...",
  "language_code": "en",
  "words": [
    {
      "text": "Hello",
      "start": 100,
      "end": 450,
      "confidence": 0.99
    },
    {
      "text": "world",
      "start": 500,
      "end": 950,
      "confidence": 0.98
    }
  ]
}
```

### Timestamp Format

- `start` and `end` are in **milliseconds**
- Word boundaries are automatically detected
- Confidence scores indicate transcription accuracy (0.0-1.0)

### Data Privacy

- Audio is processed by AssemblyAI's secure API
- Audio files are **not stored permanently** by AssemblyAI after processing
- Your API key is stored only in your browser session
- See [AssemblyAI's Privacy Policy](https://www.assemblyai.com/legal/privacy-policy) for details

## Pricing

AssemblyAI offers:
- **Free tier**: Limited transcription hours per month
- **Pay-as-you-go**: ~$0.00025 per second of audio (~$15 per hour)
- Check [AssemblyAI Pricing](https://www.assemblyai.com/pricing) for current rates

**Example costs**:
- 5-minute audio file: ~$0.08
- 30-minute audio file: ~$0.45
- 1-hour audio file: ~$0.90

## Troubleshooting

### "AssemblyAI SDK not installed"

**Solution**: Install the SDK
```bash
pip install assemblyai
```

### "Invalid API key"

**Solution**: 
1. Verify your API key is correct
2. Check if your AssemblyAI account is active
3. Ensure you have available credits/quota

### Transcription taking too long

**Expected behavior**: 
- Typical transcription takes 1/3 to 1/2 of the audio duration
- A 10-minute audio file should transcribe in 3-5 minutes
- Progress updates are shown during transcription

### Transcription fails

**Possible causes**:
1. **Unsupported audio format**: Convert to WAV, MP3, M4A, or FLAC
2. **File too large**: AssemblyAI supports files up to ~5GB
3. **Poor audio quality**: Very low quality audio may fail to transcribe
4. **Network issues**: Check your internet connection

## Command-Line Usage

You can also use the AssemblyAI module directly from the command line:

```bash
python pipeline/assemblyai_transcribe.py
```

This will:
1. Prompt for your API key
2. Test the key
3. Ask for an audio file path
4. Transcribe and save the JSON

Example:
```
=== AssemblyAI Transcription Module ===

Enter your AssemblyAI API key: YOUR_KEY_HERE

API key is valid ✓

Enter path to audio file: my_audio.wav

Starting transcription...
⏳ Uploading audio to AssemblyAI...
🔄 Transcribing audio (this may take a few minutes)...
✅ Transcription complete!

==================================================
✅ Transcription successful!

Transcript ID: abc123...
Duration: 125.30 seconds
Total words: 487

Transcribed text:
Hello and welcome to today's lesson...

💾 Saved transcript to: my_audio.json
```

## Python API Usage

You can also integrate the transcriber into your own Python scripts:

```python
from pipeline.assemblyai_transcribe import AssemblyAITranscriber

# Initialize with API key
transcriber = AssemblyAITranscriber("YOUR_API_KEY")

# Transcribe audio
def progress(status):
    print(status)

result = transcriber.transcribe_audio(
    "audio.wav",
    language_code="en",
    progress_callback=progress
)

# Access results
print(f"Transcribed text: {result['text']}")
print(f"Total words: {len(result['words'])}")

# Save to file
transcriber.save_transcript_json(result, "output.json")
```

## Advanced Features

### Language Selection

Currently set to English (`en`) by default. To support other languages, you would modify the `language_code` parameter in `pipeline/assemblyai_transcribe.py`.

Supported languages include:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Dutch (nl)
- And many more...

See [AssemblyAI Language Support](https://www.assemblyai.com/docs/walkthroughs/transcribing-languages) for the full list.

### Additional Features

AssemblyAI supports many advanced features that could be integrated:

- **Speaker diarization**: Identify different speakers
- **Custom vocabulary**: Boost accuracy for specific words
- **Profanity filtering**: Automatically censor explicit content
- **Auto chapters**: Automatically segment long audio
- **Content safety detection**: Detect sensitive content
- **Sentiment analysis**: Analyze emotional tone

These features are available in the API but not yet integrated into the UI. They can be enabled by modifying `pipeline/assemblyai_transcribe.py`.

## Comparison: Auto-Transcription vs Manual JSON

| Feature | Auto-Transcription | Manual JSON |
|---------|-------------------|-------------|
| **Speed** | Fast (automated) | Slow (manual work) |
| **Accuracy** | High (AI-powered) | Variable (depends on source) |
| **Cost** | ~$0.08-0.90 per file | Free (but time-consuming) |
| **Setup** | API key required | No setup needed |
| **Languages** | 100+ languages | Any (if you create JSON) |
| **Word timestamps** | Automatic | Must be pre-generated |

## Support

For issues related to:
- **Dictation Builder integration**: Open an issue in this repository
- **AssemblyAI API**: Contact [AssemblyAI Support](https://www.assemblyai.com/support)

## References

- [AssemblyAI Documentation](https://www.assemblyai.com/docs)
- [AssemblyAI Python SDK](https://github.com/AssemblyAI/assemblyai-python-sdk)
- [API Reference](https://www.assemblyai.com/docs/api-reference)

