# 🎧 Dictation Builder

A powerful tool for creating dictation audio from source recordings with word-level timestamps. Perfect for language learning applications.

## 🆕 What's New

- **📝 Custom Filenames**: NEW! Specify custom output filenames in the UI - organize your dictation files with descriptive names
- **🔁 Dynamic Repetitions**: NEW! Automatically adjust repetitions based on sentence length - short chunks (< 4.5s) get 3 repeats, long chunks (≥ 4.5s) get 5 repeats, fully adjustable via UI
- **🧠 Grok AI Alignment**: Use xAI's Grok-4-fast with structured outputs for AI-powered sentence alignment (see `GROK_ALIGNMENT_README.md`)
- **📝 Environment Variables**: Uses `.env` files for easy API key management (see `ENV_SETUP.md`)
- **🤖 Auto-Transcription**: Skip manual JSON creation! Automatically transcribe audio using AssemblyAI's API
- **📦 MP3 Output**: Downloads are now compressed to MP3 format (80-90% smaller file sizes)
- **🎯 Enhanced Workflow**: Choose between auto-transcription or manual JSON upload

## Features

- 🤖 **Auto-Transcription**: Automatically transcribe audio using AssemblyAI's API (optional)
- 🎵 **Tempo Adjustment**: Slows audio to 92% (configurable) while preserving pitch using FFmpeg's `atempo` filter
- 🔁 **Dynamic Repetitions** (NEW): Automatically adjusts repetitions based on chunk length - shorter chunks get fewer repeats (3×), longer chunks get more (5×), with configurable threshold
- 🎯 **Dual Alignment Modes**:
  - **Fuzzy Matching**: Fast, offline alignment using anchor-based matching and composite scoring
  - **🧠 Grok AI Alignment**: AI-powered alignment using xAI's Grok-4-fast for superior accuracy with paraphrased or differently-worded text
- ✏️ **Manual Adjustment**: Web GUI allows manual time correction for any sentence
- 📊 **Detailed Reports**: JSON manifests with timing, quality scores, and diagnostics
- 🌐 **Web Interface**: User-friendly Streamlit GUI
- 🖥️ **CLI Support**: Batch processing via command line
- 📦 **MP3 Output**: Compressed MP3 downloads for smaller file sizes

## Requirements

- **Python 3.11+**
- **FFmpeg** (must be installed and in PATH)

### Installing FFmpeg

#### Windows
```powershell
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Verify FFmpeg installation**
```bash
ffmpeg -version
```

## Usage

### Option 1: Web GUI (Recommended)

1. **Start the Streamlit app**
```bash
streamlit run app.py
```

2. **Open your browser** to the URL shown (usually `http://localhost:8501`)

3. **Follow the three-step workflow**:
   - **Upload & Configure**: Paste canonical text, then either:
     - 🤖 **Auto-transcribe** with AssemblyAI (requires API key), or
     - 📄 Upload existing words JSON and audio files
   - **Review & Adjust**: Run automatic alignment, manually adjust any problematic sentences
   - **Build & Download**: Generate dictation audio and download as MP3

#### Auto-Transcription with AssemblyAI (Optional)

To enable automatic transcription:

1. Sign up at [AssemblyAI](https://www.assemblyai.com/) and get your API key
2. In the sidebar, expand **"🤖 AssemblyAI Auto-Transcription"**
3. Enter your API key and click **"🔑 Test API Key"**
4. Select **"🤖 Auto-transcribe with AssemblyAI"** mode in Step 1
5. Upload only your audio file (no JSON needed!)

See [ASSEMBLYAI_INTEGRATION.md](ASSEMBLYAI_INTEGRATION.md) for detailed setup and usage.

### Option 2: Command Line

1. **Prepare your files**:
   - `text.txt` - Canonical text
   - `words.json` - Word timestamps (see format below)
   - `audio.wav` - Source audio

2. **Run the CLI**:
```bash
python cli.py text.txt words.json audio.wav output/
```

3. **With custom config**:
```bash
python cli.py text.txt words.json audio.wav output/ --config my_config.yaml
```

4. **Override specific settings**:
```bash
python cli.py text.txt words.json audio.wav output/ --tempo 0.85 --repeats 4 --pause 12000
```

### Option 3: Python API

```python
from pathlib import Path
from pipeline.builder import DictationBuilder

# Create builder
builder = DictationBuilder(config={
    'tempo': 0.92,
    'repeats': 3,
    'pause_ms': 10000
})

# Build from files
result = builder.build(
    canonical_text="Your text here...",
    words_json=Path("words.json"),
    audio_file=Path("audio.wav"),
    output_dir=Path("output")
)

# Access outputs
print(f"Audio: {result['audio']}")
print(f"Manifest: {result['manifest']}")
print(f"Report: {result['report']}")
```

## Input Formats

### Canonical Text (`text.txt`)
Plain text file with the exact content to be dictated. Example:
```
As a boy, Robert Ballard liked to read about shipwrecks. He read a lot about the Titanic. "My lifelong dream was to find this great ship," he says.

On August 31, 1985, Ballard's dream came true. He found the wreck of the Titanic.
```

**Note**: Embedded quotes will be automatically stripped for alignment purposes while preserving sentence structure.

### Word Timestamps (`words.json`)

Supports two formats:

#### Spec Format
```json
{
  "audio_id": "unique_id",
  "sr_hz": 44100,
  "words": [
    {"text": "As", "start": 320, "end": 440},
    {"text": "a", "start": 440, "end": 600},
    {"text": "boy", "start": 600, "end": 960}
  ]
}
```

#### AssemblyAI Format (Auto-detected)
```json
{
  "id": "transcript_id",
  "language_code": "en",
  "text": "As a boy...",
  "words": [
    {
      "text": "As",
      "start": 320,
      "end": 440,
      "confidence": 0.99,
      "speaker": "A"
    }
  ]
}
```

**Key points**:
- `start` and `end` are in **milliseconds**
- Words must be in chronological order
- Extra fields (confidence, speaker) are ignored

### Source Audio
Supported formats: WAV, MP3, M4A, FLAC

## Output Files

### `dictation_final.wav`
Final dictation audio with:
- Each sentence repeated 3× (configurable)
- 10-second pauses between repeats (configurable)
- 10-second pauses between sentences (configurable)
- Tempo adjusted to 0.92× with pitch preserved

### `final_manifest.json`
Detailed manifest with timing information:
```json
{
  "audio_in": "path/to/source.wav",
  "tempo": 0.92,
  "pause_ms": 10000,
  "repeats": 3,
  "sentences": [
    {
      "idx": 1,
      "text": "First sentence here.",
      "source_span_ms": {"start": 320, "end": 4160, "pad_ms": 100},
      "quality": {"score": 0.94, "note": "ok"},
      "output_offsets_ms": {
        "first_read_start": 0,
        "first_read_end": 4500,
        "second_read_start": 14500,
        "second_read_end": 19000,
        "third_read_start": 29000,
        "third_read_end": 33500,
        "block_end": 43500
      }
    }
  ],
  "total_duration_ms": 250000
}
```

### `alignment_report.json`
Diagnostic information about alignment quality:
```json
{
  "global": {
    "num_sentences": 42,
    "aligned": 41,
    "unaligned": 0,
    "warnings": 1
  },
  "details": [
    {
      "idx": 7,
      "text": "Problematic sentence...",
      "status": "warning",
      "score": 0.79,
      "reason": "low score but acceptable"
    }
  ]
}
```

## Configuration

Edit `config.yaml` to customize behavior:

```yaml
# Audio processing
tempo: 0.92                    # Speed multiplier (0.5-2.0)
repeats: 3                     # Repetitions per sentence (deprecated - use dynamic_repetitions)
pause_ms: 10000               # Pause between repeats
inter_sentence_pause_ms: 10000 # Pause between sentences
pad_ms: 100                   # Boundary padding
fade_ms: 8                    # Fade duration

# Dynamic repetitions based on chunk length
dynamic_repetitions:
  enabled: true                # Enable dynamic repetitions
  threshold_seconds: 4.5       # Chunks < this get short_repeats, >= get long_repeats
  short_chunk_repeats: 3       # Repetitions for short chunks
  long_chunk_repeats: 5        # Repetitions for long chunks

# Alignment
alignment:
  min_accept: 0.85            # Auto-accept threshold
  warn_accept: 0.78           # Warning threshold
  window_tokens: 4000         # Search window size
  
  weights:
    token_sim: 0.50           # Token similarity weight
    coverage: 0.25            # Coverage weight
    gap_penalty: 0.20         # Gap penalty weight
    anchor_bonus: 0.08        # Anchor bonus
    bigram_bonus: 0.05        # Bigram bonus
```

### Dynamic Repetitions

The dynamic repetitions feature automatically adjusts how many times each sentence is repeated based on its original length:

- **Short chunks** (< 4.5 seconds by default): Repeated 3 times
- **Long chunks** (≥ 4.5 seconds by default): Repeated 5 times

**Benefits:**
- Short, simple sentences don't take up excessive time
- Long, complex sentences get more repetitions for better comprehension
- Fully configurable via UI or config file

**Example:**
```
Sentence 1: "Hi!" (1.2s) → 3 repeats
Sentence 2: "The ship was in two main parts." (5.8s) → 5 repeats
```

Enable/disable and adjust thresholds in the Streamlit UI sidebar under "🔄 Repetitions".

## How It Works

### 1. Normalization
- Unicode NFKC normalization
- Quote stripping for alignment
- Hyphen collapsing (re-enter → reenter)
- Number equivalence (1912 ↔ "nineteen twelve")

### 2. Sentence Segmentation
- NLTK-based splitting
- Abbreviation handling (Mr., Dr., U.S., etc.)

### 3. Fuzzy Alignment
- **Anchor extraction**: Identifies distinctive words (proper nouns, numbers, rare terms)
- **Sliding window**: Monotonic search prevents backward drift
- **Composite scoring**:
  - Token similarity (weighted by IDF)
  - Coverage (% of sentence tokens found)
  - Gap penalty (missing/extra tokens)
  - Anchor bonus (all anchors present)
  - Bigram bonus (consecutive word matches)
- **Fallback**: Expands search window and relaxes thresholds for difficult sentences

### 4. Audio Processing
- Extract clips from source audio with padding
- Apply tempo change (0.92×) using FFmpeg `atempo` filter
- Add fade in/out to prevent clicks
- Build blocks: `sentence × 3` with silence between repeats
- Concatenate all blocks with inter-sentence pauses

### 5. Manual Adjustment (GUI only)
- Review automatic alignment results
- Adjust start/end times for any sentence
- Times relative to original audio
- Adjustments applied before audio rendering

## Troubleshooting

### FFmpeg not found
```
RuntimeError: FFmpeg not found
```
**Solution**: Install FFmpeg and ensure it's in your system PATH.

### Alignment failures
If many sentences fail to align:
1. Check that word timestamps match the audio file
2. Verify canonical text matches the actual spoken content
3. Try relaxing `warn_accept` threshold in config
4. Use manual adjustment in GUI for problem sentences

### Audio quality issues
- Increase `fade_ms` if you hear clicks at sentence boundaries
- Adjust `pad_ms` if words are cut off at start/end
- Ensure source audio quality is good

### Performance
- Large files (20+ minutes, 1000+ sentences) may take 5-10 minutes
- Processing is CPU-bound (FFmpeg operations)
- Use CLI for batch processing multiple files

## Project Structure

```
dictation-builder/
├── app.py                    # Streamlit GUI
├── cli.py                    # Command-line interface
├── config.yaml               # Default configuration
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
└── pipeline/
    ├── __init__.py
    ├── normalize.py          # Text normalization & tokenization
    ├── segmentation.py       # Sentence splitting
    ├── alignment.py          # Fuzzy alignment engine
    ├── audio.py              # FFmpeg operations
    ├── manifest.py           # Report generation
    └── builder.py            # Main orchestrator
```

## Testing with Provided Data

Test the system with your `U4A` files:

```bash
# Using GUI
streamlit run app.py
# Then upload U4A.txt, U4A.json, and Unit 4A (clean).mp3

# Using CLI
python cli.py "U4A.txt" "U4A.json" "Unit 4A (clean).mp3" output/
```

## Advanced Usage

### Custom Alignment Config

```python
from pipeline.alignment import AlignmentConfig

config = AlignmentConfig()
config.min_accept = 0.90  # Stricter threshold
config.window_tokens = 2000  # Smaller search window

builder = DictationBuilder(config={'alignment': config.__dict__})
```

### Processing Multiple Files

```python
import glob
from pathlib import Path
from pipeline.builder import build_from_files

for text_file in glob.glob("texts/*.txt"):
    base_name = Path(text_file).stem
    
    result = build_from_files(
        text_file=Path(text_file),
        words_json_file=Path(f"json/{base_name}.json"),
        audio_file=Path(f"audio/{base_name}.mp3"),
        output_dir=Path(f"output/{base_name}")
    )
    
    print(f"Completed: {base_name}")
```

## Success Criteria (from PRD)

✅ **98%+ sentences aligned** above threshold (configurable via `warn_accept`)  
✅ **Exactly 3 repeats** per sentence  
✅ **10.0 ± 0.05s pauses** (configurable precision)  
✅ **Clean word boundaries** via padding and fade filters  
✅ **Valid output structure** with full manifests and reports

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review `alignment_report.json` for diagnostic info
3. Use manual adjustment feature in GUI for problem sentences
4. Ensure FFmpeg is properly installed

---

**Built with**: Python, Streamlit, FFmpeg, NLTK, RapidFuzz, num2words

