# Quick Start Guide

## 1. Install Dependencies

### Windows (PowerShell)
```powershell
# Install FFmpeg (if not already installed)
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html

# Install Python packages
pip install -r requirements.txt
```

### macOS/Linux
```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Install Python packages
pip install -r requirements.txt
```

## 2. Launch the GUI

```bash
streamlit run app.py
```

Your browser will open to `http://localhost:8501`

## 3. Use the Interface

### Tab 1: Upload & Configure
1. **Paste your canonical text** in the text area
2. **Upload words.json** (your word timestamps file)
3. **Upload audio file** (WAV, MP3, M4A, or FLAC)
4. Click **"Preview Sentences"** to segment and analyze

### Tab 2: Review & Adjust
1. Click **"Run Automatic Alignment"** 
2. Review alignment results:
   - ✅ = Successfully aligned
   - ⚠️ = Warning (low score but usable)
   - ❌ = Failed alignment
3. **Manually adjust** any problematic sentences:
   - Use the time input boxes (format: MM:SS.mmm or seconds)
   - Click 💾 to save adjustments
4. Filter view: "All sentences" | "Only warnings/failures" | "Only manual adjustments"

### Tab 3: Build & Download
1. Review settings summary
2. (Optional) Choose custom output directory
3. Click **"Build Dictation Audio"**
4. Wait for processing (typically 2-5 minutes for a 10-minute source)
5. **Preview audio** in the player
6. **Download** files:
   - `dictation_final.wav` - Final dictation audio
   - `final_manifest.json` - Timing information
   - `alignment_report.json` - Quality diagnostics

## 4. Test with Your Data

Your existing files are ready to test:

```bash
streamlit run app.py
```

Then:
- Paste content from `U4A.txt`
- Upload `U4A.json`
- Upload `Unit 4A (clean).mp3`

## Command Line Alternative

If you prefer CLI:

```bash
python cli.py "U4A.txt" "U4A.json" "Unit 4A (clean).mp3" output/
```

Results will be saved to `output/` directory.

## What to Expect

✅ **Processing time**: ~2-5 minutes for 10-minute audio  
✅ **Output size**: ~3-4× larger than source (more silence)  
✅ **Quality**: 85-95% of sentences auto-aligned successfully  

### Example Output Structure

```
output/
├── dictation_final.wav       # Final audio (tempo 0.92×, 3× repeats)
├── final_manifest.json        # Timing data for each sentence
└── alignment_report.json      # Alignment quality report
```

## Typical Workflow

1. **First run**: Upload files → Auto-align → Review results
2. **Check warnings**: Filter to "Only warnings/failures"
3. **Manual fixes**: Adjust 1-2 problematic sentences if needed
4. **Build**: Generate final audio
5. **Quality check**: Listen to a few random sentences in preview
6. **Download**: Save all output files

## Configuration Tips

### Sidebar Settings (Left Panel)

- **Tempo**: 0.92 = 92% speed (slower for dictation)
- **Repeats**: 3 = each sentence plays 3 times
- **Pause between repeats**: 10s = student writing time
- **Pause between sentences**: 10s = transition time

### Advanced Alignment (Expand in Sidebar)

- **Min acceptance score**: 0.85 = auto-accept threshold
- **Warning threshold**: 0.78 = review recommended
- **Search window**: 4000 tokens = how far to look ahead

## Troubleshooting

### "FFmpeg not found"
- **Windows**: Install via Chocolatey or download from ffmpeg.org
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

### Many alignment failures
1. Check that timestamps match audio file
2. Verify text is accurate (not a different version)
3. Lower "Min acceptance score" to 0.80
4. Use manual adjustment for failed sentences

### Clicks or pops in audio
- Increase **Fade in/out** to 10-15ms
- Increase **Audio padding** to 150-200ms

### Slow performance
- Normal for first run (downloads NLTK data)
- 20+ minute audio may take 10-15 minutes to process
- FFmpeg operations are CPU-intensive

## Need Help?

1. Check `alignment_report.json` for diagnostics
2. Use the filter "Only warnings/failures" to focus on problems
3. Manual adjustment can fix any sentence in seconds
4. Refer to README.md for detailed documentation

---

**🎉 You're ready to build dictation audio!**

