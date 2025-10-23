# 📋 Dictation Builder Workflow Guide

## Overview

This guide explains the complete workflow of the Dictation Builder with both manual and automatic transcription options.

---

## 🎯 Quick Start Decision Tree

```
Do you have word-level timestamps JSON already?
│
├─ YES ──► Use Manual Upload Mode
│          (Original workflow, no API key needed)
│
└─ NO ──► Use Auto-Transcribe Mode
           (Requires AssemblyAI API key)
```

---

## 🤖 Workflow A: Auto-Transcription (NEW)

**Best for:** New projects, when you only have audio + text

### Prerequisites
- AssemblyAI API key ([sign up here](https://www.assemblyai.com/))
- Audio file (WAV, MP3, M4A, or FLAC)
- Canonical text (the reference text to be dictated)

### Steps

#### 1️⃣ Setup (One-time)
```
Open App
  ↓
Sidebar → "🤖 AssemblyAI Auto-Transcription"
  ↓
Enter API Key
  ↓
Click "🔑 Test API Key"
  ↓
✅ Success!
```

#### 2️⃣ Upload & Transcribe
```
Tab 1: Upload & Configure
  ↓
Paste canonical text
  ↓
Select "🤖 Auto-transcribe with AssemblyAI"
  ↓
Upload audio file only
  ↓
Click "🤖 Auto-Transcribe & Load"
  ↓
⏳ Wait 1-3 minutes (progress shown)
  ↓
✅ Transcription complete!
  └─ Sentence preview displayed
  └─ Transcribed text shown for comparison
```

**Time estimate:** 2-5 minutes (depending on audio length)

#### 3️⃣ Review & Adjust
```
Tab 2: Review & Adjust
  ↓
Click "🔄 Run Automatic Alignment"
  ↓
Review alignment results:
  ├─ ✅ Good alignments (green)
  ├─ ⚠️ Warnings (yellow)
  └─ 🔴 Failed (red - requires manual adjustment)
  ↓
For any problematic sentences:
  ├─ Click "🎯 Jump Start/End" to listen
  ├─ Use audio player fine controls (±100ms)
  ├─ Adjust start/end times
  └─ Click "💾 Save"
  ↓
✅ All sentences reviewed
```

**Time estimate:** 5-15 minutes (depending on alignment quality)

#### 4️⃣ Build & Download
```
Tab 3: Build & Download
  ↓
Review settings (tempo, repeats, pauses)
  ↓
Click "🚀 Build Dictation Audio"
  ↓
⏳ Wait 1-3 minutes (FFmpeg processing)
  ↓
🔄 Auto-convert to MP3
  ↓
✅ Build complete!
  ├─ Preview audio in browser
  ├─ Download MP3 (compressed)
  ├─ Download manifest JSON
  └─ Download alignment report JSON
```

**Time estimate:** 2-5 minutes

### Total Time: **10-25 minutes**

---

## 📄 Workflow B: Manual Upload (Original)

**Best for:** When you already have word timestamps JSON

### Prerequisites
- Word timestamps JSON file (AssemblyAI or custom format)
- Audio file (WAV, MP3, M4A, or FLAC)
- Canonical text (the reference text to be dictated)

### Steps

#### 1️⃣ Upload Files
```
Tab 1: Upload & Configure
  ↓
Paste canonical text
  ↓
Select "📄 Upload JSON manually"
  ↓
Upload word timestamps JSON
  ↓
Upload audio file
  ↓
Click "🔍 Preview Sentences & Load"
  ↓
✅ Files loaded!
  └─ Sentence preview displayed
```

**Time estimate:** 1-2 minutes

#### 2️⃣ Review & Adjust
```
(Same as Auto-Transcription workflow above)
Tab 2: Review & Adjust
  ↓
Run alignment → Review → Adjust → Save
```

**Time estimate:** 5-15 minutes

#### 3️⃣ Build & Download
```
(Same as Auto-Transcription workflow above)
Tab 3: Build & Download
  ↓
Build → Convert to MP3 → Download
```

**Time estimate:** 2-5 minutes

### Total Time: **8-22 minutes**

---

## 🎨 Visual Workflow Diagram

### Auto-Transcription Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INPUTS                              │
├─────────────────────────────────────────────────────────────┤
│  📝 Canonical Text          🎵 Audio File                    │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             │                            ↓
             │                   ┌────────────────────┐
             │                   │  AssemblyAI API    │
             │                   │  (Transcription)   │
             │                   └─────────┬──────────┘
             │                            │
             │                            ↓
             │                   ┌────────────────────┐
             │                   │  Words JSON        │
             │                   │  (auto-generated)  │
             │                   └─────────┬──────────┘
             │                            │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │  Sentence Segmentation     │
             │  (NLTK)                    │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │  Fuzzy Alignment           │
             │  (Sentences ↔ Timestamps)  │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │  Manual Adjustment         │
             │  (Optional)                │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │  Audio Building            │
             │  • Tempo adjust (FFmpeg)   │
             │  • Repeat 3×               │
             │  • Add pauses              │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │  MP3 Conversion            │
             │  (pydub + FFmpeg)          │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │  OUTPUTS                   │
             ├────────────────────────────┤
             │  📦 Dictation MP3          │
             │  📊 Manifest JSON          │
             │  📋 Alignment Report       │
             └────────────────────────────┘
```

### Manual Upload Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INPUTS                              │
├─────────────────────────────────────────────────────────────┤
│  📝 Canonical Text    📄 Words JSON    🎵 Audio File         │
└────────────┬───────────────┬──────────────┬─────────────────┘
             │               │              │
             └───────────────┴──────────────┘
                          ↓
             ┌────────────────────────────┐
             │  Sentence Segmentation     │
             └────────────┬───────────────┘
                          ↓
                     (Continue as above from "Fuzzy Alignment")
```

---

## 🔄 Feature Comparison

| Feature | Auto-Transcription | Manual Upload |
|---------|-------------------|---------------|
| **Setup Required** | API key (one-time) | None |
| **Files Needed** | Audio + Text | Audio + Text + JSON |
| **Processing Time** | +3-5 min (transcription) | Immediate |
| **Cost** | ~$0.08-0.90 per file | Free |
| **Accuracy** | AI-powered (very high) | Depends on JSON quality |
| **Languages** | 100+ supported | Any (if you create JSON) |
| **Best For** | New projects | Existing timestamps |

---

## ⚙️ Configuration Options

### Tempo Settings
- **Default:** 0.92× (92% speed)
- **Range:** 0.5× to 2.0×
- **Use case:** Adjust based on learner level
  - Beginners: 0.85-0.92×
  - Intermediate: 0.92-1.0×
  - Advanced: 1.0×

### Repetition Settings
- **Default:** 3 repeats per sentence
- **Range:** 1-5 repeats
- **Use case:** 
  - Difficult content: 4-5 repeats
  - Easy content: 2-3 repeats

### Pause Settings
- **Between repeats:** 10,000ms (10 seconds) default
- **Between sentences:** 10,000ms (10 seconds) default
- **Range:** 0-60,000ms
- **Use case:**
  - Beginners: 12,000-15,000ms
  - Advanced: 5,000-8,000ms
  - Exam prep: Match actual test timing

### Audio Padding
- **Default:** 100ms before/after each sentence
- **Range:** 0-500ms
- **Purpose:** Prevent cutting off start/end of words

### Fade Duration
- **Default:** 8ms
- **Range:** 0-50ms
- **Purpose:** Prevent audio clicks/pops

---

## 🎯 Best Practices

### For Best Alignment Results

1. **Clean canonical text:**
   - Remove extra whitespace
   - Use consistent punctuation
   - Match the actual spoken text as closely as possible

2. **Good audio quality:**
   - Clear speech, minimal background noise
   - Consistent volume level
   - Proper microphone technique

3. **Manual adjustment strategy:**
   - Start with failed alignments (🔴 red)
   - Then review warnings (⚠️ yellow)
   - Use audio player controls to find exact boundaries
   - Save adjustments incrementally

4. **Review transcription (auto mode):**
   - Compare transcribed text with canonical text
   - Note discrepancies (may affect alignment)
   - Consider re-recording if transcription is very different

### For Efficient Processing

1. **Batch similar files:**
   - Use same settings for similar content
   - Process multiple files in one session

2. **Save intermediate results:**
   - Download manifest JSON for records
   - Keep alignment reports for analysis

3. **Iterative improvement:**
   - Build once, review quality
   - Adjust settings if needed
   - Rebuild with new settings

---

## 🐛 Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Can't see auto-transcribe option | Add API key in sidebar |
| Transcription fails | Check internet + API key validity |
| Poor alignment | Verify canonical text matches audio |
| Failed sentences | Use manual adjustment with audio player |
| MP3 conversion fails | App falls back to WAV automatically |
| Build takes too long | Normal for large files; check FFmpeg |
| Download doesn't start | Check browser download settings |

See [ASSEMBLYAI_INTEGRATION.md](ASSEMBLYAI_INTEGRATION.md) for detailed troubleshooting.

---

## 📊 Example Timeline

### Typical 10-minute audio file (400 words, 20 sentences)

| Step | Auto-Transcribe | Manual Upload |
|------|----------------|---------------|
| Setup | 1 min (API key) | 0 min |
| Upload | 1 min | 1 min |
| **Transcription** | **3 min** | **0 min** |
| Alignment | 30 sec | 30 sec |
| Review | 10 min | 10 min |
| Build | 3 min | 3 min |
| **Total** | **~18 minutes** | **~15 minutes** |

*Note: First-time setup adds ~2 minutes for API key configuration*

---

## 🎓 Learning Path

### For New Users

1. **Week 1:** Try manual upload with provided sample files
2. **Week 2:** Set up AssemblyAI and test auto-transcription
3. **Week 3:** Process your own content
4. **Week 4:** Experiment with different settings

### For Advanced Users

1. Explore command-line interface for batch processing
2. Integrate Python API into your own scripts
3. Customize configuration files for your use case
4. Consider contributing improvements back to the project

---

## 📚 Related Documentation

- [README.md](README.md) - Main project overview
- [ASSEMBLYAI_INTEGRATION.md](ASSEMBLYAI_INTEGRATION.md) - Detailed AssemblyAI guide
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md) - Technical change log

---

**Questions?** Open an issue on GitHub or check the troubleshooting section in the main documentation.

