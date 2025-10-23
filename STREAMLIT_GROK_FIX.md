# Streamlit Grok Alignment Fix

## Problem Identified

The Streamlit app had **two separate alignment code paths**:

### 1. Tab 2: "Review & Adjust" - Run Automatic Alignment Button
**OLD CODE (lines 566-587):**
```python
from pipeline.alignment import align_sentences_to_words, AlignmentConfig  # FUZZY ONLY!

config = AlignmentConfig()
spans, report = align_sentences_to_words(...)  # Direct fuzzy matching
```

**Result:** ❌ Used fuzzy matching only, no Grok AI

### 2. Tab 3: "Build & Download" - Build Dictation Audio Button
**CODE (lines 835-899):**
```python
builder = DictationBuilder(config)  # Uses hybrid mode from defaults
result = builder.build(...)
```

**Result:** ✅ Used hybrid mode (Grok + fuzzy fallback)

## Why Empty Log Files Were Created

Empty log files appeared because:

1. **Module Import Creates Log File**: When `grok_alignment.py` is imported, it runs:
   ```python
   logger = setup_grok_logger()  # Creates timestamped log file
   ```

2. **Tab 2 Only Used Fuzzy**: When you clicked "Run Automatic Alignment" in Tab 2:
   - `builder.py` was imported (which imports `grok_alignment.py`)
   - Empty log file was created
   - But only fuzzy matching ran (no Grok API calls)
   - Log file stayed empty

3. **Tab 3 Used Hybrid**: When you clicked "Build Dictation Audio" in Tab 3:
   - `builder.build()` ran with hybrid mode
   - Grok API calls were made
   - Log file was populated (6KB)

## Solution Implemented

Updated Tab 2's "Run Automatic Alignment" button to use **hybrid mode**:

**NEW CODE (lines 566-602):**
```python
from pipeline.builder import DictationBuilder

# Create config with hybrid mode (Grok + fuzzy fallback)
config = {
    'pad_ms': pad_ms,
    'alignment': {
        'method': 'hybrid',  # Use Grok AI with fuzzy fallback
        'min_accept': min_accept,
        'warn_accept': warn_accept,
        'window_tokens': window_tokens
    }
}

builder = DictationBuilder(config)
spans, report = builder._perform_alignment(
    st.session_state.sentences, 
    words, 
    'hybrid'  # Grok AI + fuzzy fallback
)

# Show method breakdown
if 'methods' in report.get('global', {}):
    methods = report['global']['methods']
    st.success(f"✅ Alignment complete! Grok: {methods.get('grok', 0)}, Fuzzy: {methods.get('fuzzy', 0)}")
```

## Changes Made

**File:** `app.py`
- **Lines 566-602:** Updated "Run Automatic Alignment" button
- **Changed from:** Direct fuzzy matching (`align_sentences_to_words`)
- **Changed to:** Hybrid mode (`builder._perform_alignment(..., 'hybrid')`)
- **Added:** Method breakdown in success message showing Grok vs Fuzzy count

## Benefits

✅ **Consistent behavior** - Both alignment points now use Grok AI  
✅ **Better accuracy** - Grok AI used in Tab 2 preview, not just final build  
✅ **Visible feedback** - Success message shows how many sentences used each method  
✅ **Proper logging** - All Grok API calls are now logged to `logs/` directory  
✅ **Method tracking** - Alignment reports include which method was used per sentence  

## Testing

After this fix, when you click "Run Automatic Alignment" in Tab 2:

1. You'll see: **"Aligning sentences (using Grok AI + fuzzy fallback)..."**
2. Terminal will show: **"Using: Hybrid (Grok AI → Fuzzy fallback)"**
3. Log file will be created in `logs/grok_alignment_YYYYMMDD_HHMMSS.log` with full details
4. Success message will show: **"✅ Alignment complete! Grok: 18, Fuzzy: 3"**
5. `alignment_report.json` will include method tracking for each sentence

## Verification

To verify Grok is working in the Streamlit app:

```bash
# 1. Start Streamlit
streamlit run app.py

# 2. In the app:
#    - Tab 1: Upload your files
#    - Tab 2: Click "Run Automatic Alignment"

# 3. Check terminal output for:
#    "Using: Hybrid (Grok AI → Fuzzy fallback)"
#    "[OK] Grok: X/Y"

# 4. Check logs directory:
ls -l logs/
# Should see a new log file with size > 0 bytes

# 5. View the log:
cat logs/grok_alignment_*.log | tail -50
# Should see API calls and SUCCESS messages
```

## Summary

**Root Cause:** Streamlit's Tab 2 used a direct fuzzy-only alignment call, bypassing the hybrid mode.

**Fix:** Updated Tab 2 to use `DictationBuilder` with hybrid mode, ensuring Grok AI is used throughout the app.

**Result:** Grok AI is now active in production for both preview alignment (Tab 2) and final audio building (Tab 3).

