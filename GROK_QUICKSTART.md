# Grok Alignment - Quick Start

## 🚀 5-Minute Setup

### 1. Install
```bash
pip install -r requirements.txt
# Includes: openai>=1.0.0, pydantic>=2.0.0
```

### 2. Get API Key
Visit: https://console.x.ai/ → Create API Key

### 3. Set Environment Variable

**Option A: Use .env file (Recommended)**
```bash
# Copy the example
cp .env.example .env

# Edit .env and add your API key
# XAI_API_KEY=your-actual-api-key-here
```

**Option B: Set in terminal**
```bash
# Linux/Mac
export XAI_API_KEY='your-api-key-here'

# Windows PowerShell
$env:XAI_API_KEY='your-api-key-here'
```

See [ENV_SETUP.md](ENV_SETUP.md) for detailed setup instructions.

### 4. Run Demo
```bash
python demo_grok_alignment.py
```

## 📝 Basic Usage

```python
from pipeline.grok_alignment import align_sentences_with_grok

# Your data
words = [{"text": "Hello", "start": 0, "end": 500}, ...]
sentences = ["Hello world.", "How are you?"]

# Align using Grok-4-fast with structured outputs
spans, report = align_sentences_with_grok(sentences, words)

# Results (type-safe, validated)
for sentence, span in zip(sentences, spans):
    if span:
        start_ms, end_ms = span
        print(f"{sentence}: {start_ms}ms → {end_ms}ms")
```

**✨ Uses Pydantic structured outputs** for type-safe, validated responses!

## 🎯 When to Use

**Use Grok if:**
- ✅ Canonical text differs from transcription (paraphrasing)
- ✅ Need high accuracy
- ✅ Can afford ~$0.001 per sentence
- ✅ Have internet connection

**Use Fuzzy Matching if:**
- ✅ Text closely matches transcription
- ✅ Need offline processing
- ✅ Speed is critical
- ✅ Processing 1000s of sentences

## 📊 Quick Comparison

| Feature | Fuzzy | Grok |
|---------|-------|------|
| Speed | ⚡ Fast | 🐌 Slower |
| Accuracy | 😊 Good | 🎯 Excellent |
| Cost | Free | ~$0.001/sentence |
| Offline | ✅ Yes | ❌ No |
| Paraphrasing | ❌ Struggles | ✅ Handles well |

## 🔧 Configuration

```python
from pipeline.grok_alignment import GrokAlignerConfig

config = GrokAlignerConfig()
config.max_workers = 5      # Parallel processing
config.temperature = 0.1    # Low = consistent
config.max_retries = 3      # Error handling

spans, report = align_sentences_with_grok(
    sentences, words, config=config
)
```

## 📚 More Help

- **Full Guide**: `GROK_ALIGNMENT_GUIDE.md`
- **Overview**: `GROK_ALIGNMENT_README.md`
- **Demo**: `python demo_grok_alignment.py`
- **Comparison**: `python compare_alignment_methods.py`
- **Setup**: `python setup_grok.py`

## 💡 Tips

1. **Start with demo**: `python demo_grok_alignment.py`
2. **Compare methods**: `python compare_alignment_methods.py`
3. **Use hybrid approach**: Grok first, fuzzy fallback
4. **Cache results**: Save alignments to avoid reprocessing
5. **Tune workers**: Adjust based on your rate limits

## 🆘 Troubleshooting

**Problem**: API key error
```bash
python setup_grok.py  # Interactive setup
```

**Problem**: Rate limit
```python
config.max_workers = 2  # Reduce parallel requests
```

**Problem**: Connection timeout
```python
config.timeout = 60  # Increase timeout
```

## 📖 Example Output

```
🚀 Grok Alignment Demo

📂 Loading data...
   ✓ Loaded 241 words from transcription
   ✓ Found 21 sentences

🤖 Running Grok alignment...
   
✅ Alignment complete!

📊 ALIGNMENT REPORT
═══════════════════════════════════════════════

📈 Global Statistics:
   Total sentences:    21
   ✓ Aligned:          21
   ✗ Unaligned:        0
   
   Success rate: 100.0%
```

---

**Ready?** Run `python setup_grok.py` to get started!

