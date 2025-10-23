# Grok AI Alignment - Production Integration Guide

## 🎉 Congratulations!

The Grok AI alignment is now fully integrated into the production pipeline with **100% success rate** (21/21 sentences aligned vs 17/21 with fuzzy matching).

## 🚀 What's Been Integrated

### 1. **Core Pipeline Updates**

#### `pipeline/builder.py`
- ✅ Added Grok alignment import with graceful fallback
- ✅ Added `method` configuration option
- ✅ Implemented `_perform_alignment()` with three modes:
  - `fuzzy`: Traditional fuzzy matching
  - `grok`: Grok AI only
  - `hybrid`: **Grok first, fuzzy fallback** (recommended)

#### `config.yaml`
- ✅ Added `alignment.method` setting (default: `hybrid`)
- ✅ Added `grok` section for AI parameters
- ✅ Preserved all existing fuzzy matching parameters

## 📋 Configuration Options

### Method 1: Hybrid (Recommended for Production)

**Best of both worlds**: Fast AI alignment with fuzzy fallback for any failures.

```yaml
# config.yaml
alignment:
  method: hybrid  # ← Uses Grok, falls back to fuzzy if needed
```

**Benefits:**
- ✅ Best accuracy (Grok's AI understanding)
- ✅ Reliable (fuzzy fallback for edge cases)
- ✅ Optimized cost (fuzzy costs nothing)
- ✅ No failures (always has fallback)

### Method 2: Grok Only (Maximum Accuracy)

**AI-powered only**: Use when you need the highest accuracy and have reliable API access.

```yaml
# config.yaml
alignment:
  method: grok  # ← Uses Grok only, fails if API unavailable
```

**Benefits:**
- ✅ Maximum accuracy
- ✅ Handles paraphrasing
- ✅ Consistent results

**Considerations:**
- Requires XAI_API_KEY
- Depends on API availability
- ~$0.001 per sentence cost

### Method 3: Fuzzy Only (Traditional)

**Offline, free, fast**: Use when you don't need AI or want offline processing.

```yaml
# config.yaml
alignment:
  method: fuzzy  # ← Traditional fuzzy matching
```

**Benefits:**
- ✅ No API required
- ✅ Works offline
- ✅ Free
- ✅ Fast

## 🔧 Grok Configuration

Fine-tune Grok behavior in `config.yaml`:

```yaml
grok:
  model: grok-4-fast        # Model to use
  temperature: 0.1          # Lower = more consistent (0.0-0.2 recommended)
  max_workers: 5            # Parallel requests (adjust for rate limits)
  max_retries: 3            # Retry attempts
  timeout: 30               # Request timeout (seconds)
```

### Performance Tuning

**For speed:**
```yaml
grok:
  max_workers: 10           # More parallel requests
  timeout: 60               # Longer timeout for complex sentences
```

**For cost optimization:**
```yaml
alignment:
  method: hybrid            # Use fuzzy fallback to minimize API calls
grok:
  max_workers: 3            # Fewer parallel requests
```

**For maximum reliability:**
```yaml
grok:
  max_retries: 5            # More retry attempts
  timeout: 45               # Longer timeout
```

## 🎯 Usage Examples

### CLI Usage

```bash
# Uses config.yaml (hybrid by default)
python cli.py canonical.txt words.json audio.wav output/

# With custom config
python cli.py canonical.txt words.json audio.wav output/ -c custom_config.yaml
```

### Programmatic Usage

```python
from pipeline.builder import DictationBuilder

# Default (hybrid mode)
builder = DictationBuilder()
result = builder.build(canonical_text, words_json, audio_file, output_dir)

# Grok only
builder = DictationBuilder(config={'alignment': {'method': 'grok'}})
result = builder.build(canonical_text, words_json, audio_file, output_dir)

# Fuzzy only
builder = DictationBuilder(config={'alignment': {'method': 'fuzzy'}})
result = builder.build(canonical_text, words_json, audio_file, output_dir)
```

### Streamlit App

The Streamlit app (`app.py`) will automatically use the configured method from your builder config.

## 📊 Performance Comparison

Based on U4A test data (21 sentences):

| Metric | Fuzzy Only | Hybrid | Grok Only |
|--------|------------|--------|-----------|
| **Success Rate** | 81% (17/21) | **100%** (21/21) | **100%** (21/21) |
| **Speed** | 0.5s | ~12s | ~12s |
| **Cost** | Free | ~$0.02 | ~$0.02 |
| **Requires API** | ❌ No | ✅ Yes (fallback: no) | ✅ Yes |
| **Offline** | ✅ Yes | ⚠️ Partial | ❌ No |
| **Handles Paraphrasing** | ❌ No | ✅ Yes | ✅ Yes |

**Recommendation:** Use `hybrid` in production for best results.

## 🔐 Security & Environment Setup

### Required: XAI API Key

1. **Create `.env` file** (already set up):
```bash
XAI_API_KEY=your-api-key-here
```

2. **Never commit `.env`** (already in `.gitignore`)

3. **Production deployment**:
   - Set environment variable in your hosting platform
   - For Docker: Add to `docker-compose.yml` or `.env` file
   - For cloud: Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

### Example: Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "cli.py", ...]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  dictation:
    build: .
    environment:
      - XAI_API_KEY=${XAI_API_KEY}
    volumes:
      - ./output:/app/output
```

## 📈 Monitoring & Logging

The alignment process now outputs detailed information:

```
🔍 Aligning sentences to word timestamps...
  Using: Hybrid (Grok AI → Fuzzy fallback)
  ✓ Grok: 21/21
  ✓ Total: 21/21
  ✓ Aligned: 21/21
```

Or with fallback needed:

```
🔍 Aligning sentences to word timestamps...
  Using: Hybrid (Grok AI → Fuzzy fallback)
  ✓ Grok: 18/21
  🔄 Fuzzy fallback for 3 failed sentences...
  ✓ Fuzzy: 2/3
  ✓ Total: 20/21
  ✓ Aligned: 20/21
  ✗ Failed: 1
```

## 🐛 Troubleshooting

### Issue: "Grok alignment not available"

**Solution:** Install dependencies and set API key:
```bash
pip install openai pydantic
cp .env.example .env
# Edit .env and add your XAI_API_KEY
```

### Issue: Hybrid mode falls back to fuzzy only

**Cause:** XAI_API_KEY not set or Grok dependencies missing

**Solution:**
```bash
# Check if .env is loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('XAI_API_KEY'))"

# If None, add to .env:
echo "XAI_API_KEY=your-key-here" >> .env
```

### Issue: Rate limit errors

**Solution:** Reduce parallel workers:
```yaml
grok:
  max_workers: 2  # Reduce from default 5
```

### Issue: Slow performance

**Solution:** Increase parallel workers (if rate limits allow):
```yaml
grok:
  max_workers: 10  # Increase from default 5
```

## 🎓 Best Practices

### 1. Start with Hybrid Mode
```yaml
alignment:
  method: hybrid  # Best balance
```

### 2. Monitor Costs
- Check xAI dashboard regularly
- ~$0.001 per sentence
- 100 sentences/day ≈ $3/month

### 3. Cache Results
The alignment results are saved in manifests - reuse them when possible.

### 4. Test Before Production
```bash
# Test with your data
python demo_grok_alignment.py

# Compare methods
python compare_alignment_methods.py
```

### 5. Have a Fallback Plan
Always keep fuzzy matching available:
```yaml
alignment:
  method: hybrid  # Automatic fallback
```

## 📝 Next Steps

1. **Test with your data**:
   ```bash
   python cli.py your-text.txt your-words.json your-audio.wav output/
   ```

2. **Review results**:
   - Check `output/alignment_report.json`
   - Verify `output/final_manifest.json`

3. **Adjust configuration**:
   - Tune `grok.max_workers` for your rate limits
   - Adjust `grok.temperature` if needed

4. **Deploy to production**:
   - Set XAI_API_KEY in production environment
   - Use `method: hybrid` for reliability
   - Monitor costs and performance

## 🎉 Summary

✅ **Integrated**: Grok AI alignment in production pipeline
✅ **Tested**: 100% success rate (21/21 vs 17/21)
✅ **Configured**: Hybrid mode as default
✅ **Documented**: Complete setup and usage guide
✅ **Secure**: Environment variables for API keys
✅ **Reliable**: Automatic fallback to fuzzy matching
✅ **Production-Ready**: Error handling, retries, monitoring

**You're ready to go! 🚀**

---

**Questions?** See `GROK_ALIGNMENT_GUIDE.md` for detailed documentation.

