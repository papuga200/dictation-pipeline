# Grok Alignment Logging & Method Tracking

## Overview

The Grok alignment system now includes comprehensive logging and method tracking to help you understand which alignment method (Grok AI or fuzzy matching) was used for each sentence.

## Features

### 1. Detailed Activity Logs

All Grok API activity is automatically logged to timestamped files in the `logs/` directory:

```
logs/
  └── grok_alignment_YYYYMMDD_HHMMSS.log
```

**What's logged:**
- API initialization and configuration
- Each sentence being aligned (with text preview)
- API request/response details
- Timestamps and confidence scores
- Errors and retry attempts
- Summary statistics

**Example log entries:**
```
2025-10-23 17:07:02 - grok_alignment - INFO - Initializing Grok Aligner
2025-10-23 17:07:02 - grok_alignment - INFO - Model: grok-4-fast
2025-10-23 17:07:02 - grok_alignment - INFO - [1] Aligning: 'As a boy, Robert Ballard...'
2025-10-23 17:07:04 - grok_alignment - INFO - [1] SUCCESS: 220ms - 4260ms (confidence: 1.00)
```

### 2. Method Tracking in Alignment Reports

The `alignment_report.json` now includes:

**A) Global Method Statistics:**
```json
{
  "global": {
    "num_sentences": 21,
    "aligned": 21,
    "unaligned": 0,
    "warnings": 0,
    "methods": {
      "grok": 18,
      "fuzzy": 3
    }
  }
}
```

**B) Method Tag on Each Detail:**
```json
{
  "details": [
    {
      "idx": 1,
      "text": "As a boy, Robert Ballard...",
      "status": "ok",
      "method": "grok",
      "score": 0.95,
      "reason": ""
    },
    {
      "idx": 4,
      "text": "On August 31, 1985...",
      "status": "warning",
      "method": "fuzzy",
      "score": 0.82,
      "reason": "acceptable but low score"
    }
  ]
}
```

### 3. Enhanced Terminal Output

When running alignment, you'll see clear indicators:

```
Using: Hybrid (Grok AI → Fuzzy fallback)
  [OK] Grok: 18/21
  [->] Fuzzy fallback for 3 failed sentences...
  [OK] Fuzzy: 3/3
  [OK] Total: 21/21

Alignment Methods:
  Grok AI: 18
  Fuzzy matching: 3
```

## How It Works

### Hybrid Mode (Default)

1. **First Pass:** Grok AI attempts to align all sentences
2. **Logging:** Each API call is logged with request/response details
3. **Tagging:** Successful alignments are tagged with `method: "grok"`
4. **Fallback:** Failed sentences go to fuzzy matching
5. **Tagging:** Fuzzy alignments are tagged with `method: "fuzzy"`
6. **Summary:** Final report includes method breakdown

### Pure Grok Mode

All sentences use Grok AI only. All details tagged with `method: "grok"`.

### Pure Fuzzy Mode

All sentences use fuzzy matching only. All details tagged with `method: "fuzzy"`.

## Viewing Logs

### Find Log Files

```bash
# List all log files
ls -l logs/

# View latest log
cat logs/grok_alignment_*.log | tail -50

# Windows PowerShell
Get-ChildItem logs\grok_alignment_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

### Log File Contents

Each log file contains:
1. **Initialization block** - Configuration and API key status
2. **Alignment progress** - Each sentence with API results
3. **Summary block** - Final statistics

### Analyzing Logs

**Check for API errors:**
```bash
grep "ERROR" logs/grok_alignment_*.log
```

**Check for retries:**
```bash
grep "WARNING" logs/grok_alignment_*.log
```

**View successful alignments:**
```bash
grep "SUCCESS" logs/grok_alignment_*.log
```

## Checking Method Usage

### In Python

```python
from pipeline.builder import DictationBuilder
from pipeline.segmentation import segment_sentences

# Load data
with open('canonical.txt') as f:
    text = f.read()
    
sentences = segment_sentences(text)

# Build with hybrid mode
builder = DictationBuilder({'alignment': {'method': 'hybrid'}})
result = builder.build(
    canonical_text=text,
    words_json='words.json',
    audio_file='audio.mp3',
    output_dir='output'
)

# Check alignment report
with open('output/alignment_report.json') as f:
    report = json.load(f)
    
# View method breakdown
print(report['global']['methods'])
# Output: {'grok': 18, 'fuzzy': 3}

# Check specific sentences
for detail in report['details']:
    print(f"Sentence {detail['idx']}: {detail['method']}")
```

### In Streamlit App

The Streamlit interface automatically uses hybrid mode. After building dictation audio:

1. Download `alignment_report.json` from the output
2. Check the `methods` field in `global` stats
3. Review `method` field in each `details` entry

## Troubleshooting

### No Log Files Created

**Problem:** `logs/` directory is empty

**Solutions:**
1. Check if `.env` file has `XAI_API_KEY` set
2. Verify Grok alignment is actually running (not falling back to fuzzy-only)
3. Check terminal output for "Using: Hybrid" or "Using: Grok AI alignment"

### All Sentences Show "fuzzy" Method

**Problem:** Grok isn't being used

**Check:**
1. Is `XAI_API_KEY` in `.env`?
   ```bash
   # Test if API key is loaded
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Key found' if os.getenv('XAI_API_KEY') else 'Key missing')"
   ```

2. Are dependencies installed?
   ```bash
   pip install openai pydantic python-dotenv
   ```

3. Check terminal output for errors

### Logs Show API Errors

**Problem:** Grok API calls are failing

**Check log file for:**
- `ERROR` lines showing API failure reasons
- Authentication errors (invalid API key)
- Rate limit errors
- Network errors

**Solutions:**
- Verify API key is correct: https://console.x.ai/
- Check internet connection
- Try reducing `max_workers` in config.yaml:
  ```yaml
  grok:
    max_workers: 3  # Reduce from 5
  ```

## Best Practices

1. **Keep logs for debugging:** Don't delete log files immediately, they help diagnose issues

2. **Review method breakdown:** After alignment, check how many sentences used each method

3. **Monitor confidence scores:** Low confidence may indicate transcription quality issues

4. **Check fallback patterns:** If many sentences fall back to fuzzy, review your transcription quality

5. **Analyze failed alignments:** Use logs to understand why Grok couldn't align certain sentences

## Configuration

### Adjust Logging Level

Currently set to INFO. To see more details, edit `pipeline/grok_alignment.py`:

```python
logger.setLevel(logging.DEBUG)  # Change from INFO to DEBUG
```

### Disable File Logging

If you don't want log files, comment out the file handler in `pipeline/grok_alignment.py`:

```python
# file_handler = logging.FileHandler(log_file, encoding='utf-8')
# logger.addHandler(file_handler)
```

## Summary

✓ **Comprehensive logging** - Every API call recorded  
✓ **Method tracking** - Know which sentences used Grok vs Fuzzy  
✓ **Global statistics** - Overall method breakdown  
✓ **Per-sentence details** - Individual method tags  
✓ **Easy debugging** - Timestamped logs in `logs/` directory  

Now you can confidently monitor Grok alignment activity and verify which method was used for each sentence!

