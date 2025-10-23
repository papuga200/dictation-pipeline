# Grok-Based Alignment Guide

This guide explains how to use xAI's Grok-4-fast model for aligning canonical text with transcription timestamps.

## Overview

The Grok alignment system uses AI-powered natural language understanding to match sentences from canonical text with their corresponding timestamps in a transcription. This can be more accurate than fuzzy matching for:

- Handling paraphrased or slightly different wording
- Understanding context and meaning
- Dealing with punctuation and formatting differences
- Recognizing contractions and expansions

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the `openai` library (version >= 1.0.0) needed for Grok API access.

### 2. Get Your xAI API Key

1. Visit [https://console.x.ai/](https://console.x.ai/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (keep it secure!)

### 3. Set Environment Variable

**On Linux/Mac:**
```bash
export XAI_API_KEY='your-api-key-here'
```

**On Windows (PowerShell):**
```powershell
$env:XAI_API_KEY='your-api-key-here'
```

**Or in Python:**
```python
import os
os.environ['XAI_API_KEY'] = 'your-api-key-here'
```

## Quick Start

### Run the Demo

```bash
python demo_grok_alignment.py
```

This will:
1. Load the sample data (U4A.txt and U4A.json)
2. Segment the text into sentences
3. Use Grok API to align each sentence with timestamps
4. Display results and save to `output/grok_alignment_results.json`

### Basic Usage in Code

```python
from pipeline.grok_alignment import align_sentences_with_grok

# Your transcription words (from AssemblyAI or similar)
words = [
    {"text": "Hello", "start": 0, "end": 500},
    {"text": "world", "start": 500, "end": 1000},
    # ... more words
]

# Your canonical sentences
sentences = [
    "Hello world.",
    "How are you today?"
]

# Align sentences using Grok
spans, report = align_sentences_with_grok(sentences, words)

# Process results
for sentence, span in zip(sentences, spans):
    if span:
        start_ms, end_ms = span
        print(f"{sentence}: {start_ms}ms → {end_ms}ms")
    else:
        print(f"{sentence}: No alignment found")
```

## Advanced Configuration

```python
from pipeline.grok_alignment import GrokAlignerConfig, align_sentences_with_grok

# Create custom configuration
config = GrokAlignerConfig()

# API settings
config.api_key = "your-api-key"  # Or use environment variable
config.model = "grok-2-1212"  # Current model version
config.base_url = "https://api.x.ai/v1"

# Request parameters
config.temperature = 0.1  # Lower = more consistent (0.0 - 2.0)
config.max_tokens = 200   # Max tokens for response
config.timeout = 30       # Request timeout in seconds

# Parallel processing
config.max_workers = 5    # Number of parallel API calls

# Retry settings
config.max_retries = 3
config.retry_delay = 1    # Seconds between retries

# Use custom config
spans, report = align_sentences_with_grok(
    sentences=sentences,
    words=words,
    config=config,
    pad_ms=100  # Padding around timestamps
)
```

## Understanding the Output

### Alignment Report Structure

```json
{
  "global": {
    "num_sentences": 21,
    "aligned": 19,
    "unaligned": 2,
    "warnings": 3
  },
  "details": [
    {
      "idx": 5,
      "text": "Example sentence...",
      "status": "warning",
      "confidence": 0.87,
      "reason": "Low confidence alignment",
      "span_ms": {"start": 5000, "end": 7500}
    }
  ]
}
```

### Span Format

Each span is a tuple: `(start_ms, end_ms)` or `None` if alignment failed.

```python
spans = [
    (0, 4260),      # Sentence 1: 0ms to 4260ms
    (4700, 7140),   # Sentence 2: 4700ms to 7140ms
    None,           # Sentence 3: Failed to align
    # ...
]
```

## Integration with Existing Pipeline

### Option 1: Replace Fuzzy Alignment

In your `DictationBuilder` or similar code:

```python
# OLD: Using fuzzy matching
from pipeline.alignment import align_sentences_to_words

# NEW: Using Grok
from pipeline.grok_alignment import align_sentences_with_grok

# Replace the alignment call
spans, report = align_sentences_with_grok(
    sentences=sentences,
    words=words,
    pad_ms=100
)
```

### Option 2: Hybrid Approach (Fallback)

Use Grok first, fall back to fuzzy matching if needed:

```python
from pipeline.grok_alignment import align_sentences_with_grok
from pipeline.alignment import align_sentences_to_words

# Try Grok first
grok_spans, grok_report = align_sentences_with_grok(sentences, words)

# Identify failed alignments
failed_indices = [i for i, span in enumerate(grok_spans) if span is None]

if failed_indices:
    print(f"Grok failed on {len(failed_indices)} sentences, using fuzzy matching fallback...")
    
    # Use fuzzy matching for failed sentences
    fuzzy_spans, _ = align_sentences_to_words(
        [sentences[i] for i in failed_indices],
        words
    )
    
    # Merge results
    final_spans = grok_spans.copy()
    for i, fuzzy_idx in enumerate(failed_indices):
        final_spans[fuzzy_idx] = fuzzy_spans[i]
```

## Performance Considerations

### Rate Limits

- Grok API has rate limits (check xAI documentation for current limits)
- The `max_workers` setting controls parallel requests
- Adjust based on your API tier and rate limits

### Cost

- Grok API is paid (check xAI pricing)
- Each sentence requires one API call
- For 21 sentences: ~21 API calls
- Consider caching results for repeated use

### Speed

- Parallel processing improves speed significantly
- Typical: 1-3 seconds per sentence (including network latency)
- For 21 sentences with 5 workers: ~10-15 seconds total

### Optimization Tips

1. **Batch Processing**: Process files in batches rather than one-by-one
2. **Caching**: Cache alignment results to avoid re-processing
3. **Worker Tuning**: Adjust `max_workers` based on your rate limits
4. **Temperature**: Keep low (0.0-0.2) for consistent results

## Troubleshooting

### Error: "XAI_API_KEY environment variable not set"

**Solution**: Set your API key as shown in Setup section.

### Error: "Rate limit exceeded"

**Solution**: Reduce `max_workers` or add delays between requests.

```python
config.max_workers = 2  # Reduce parallel requests
```

### Error: "Invalid JSON response"

**Solution**: Grok occasionally returns non-JSON. The system retries automatically (up to `max_retries`).

### Low Confidence Scores

**Solution**: 
- Check if the canonical text matches the transcription closely
- Review the transcription quality
- Consider using fuzzy matching as fallback for low-confidence results

### Alignment Mismatches

**Solution**:
- Compare canonical text with actual transcription
- Check for significant paraphrasing or different wording
- Verify transcription accuracy (AssemblyAI confidence scores)

## Comparison: Grok vs Fuzzy Matching

| Feature | Grok Alignment | Fuzzy Matching |
|---------|---------------|----------------|
| **Accuracy** | High - understands context | Good - exact/similar words |
| **Paraphrasing** | ✅ Handles well | ❌ Struggles |
| **Speed** | Slower (~1-3s/sentence) | Fast (<0.1s/sentence) |
| **Cost** | Paid API | Free |
| **Offline** | ❌ Requires internet | ✅ Works offline |
| **Setup** | Requires API key | No setup |
| **Different Wording** | ✅ Handles well | ❌ May fail |

## Best Practices

1. **Start Small**: Test with a few sentences before processing large batches
2. **Monitor Costs**: Track API usage and costs
3. **Validate Results**: Always review alignment report for issues
4. **Use Hybrid**: Combine Grok + fuzzy matching for best results
5. **Cache Results**: Save alignment results to avoid re-processing
6. **Handle Failures**: Always check for None spans and have fallback logic

## Example: Complete Integration

```python
import os
import json
from pipeline.grok_alignment import align_sentences_with_grok, GrokAlignerConfig
from pipeline.segmentation import segment_sentences

# Load your data
with open('transcription.json', 'r') as f:
    transcription = json.load(f)
    words = transcription['words']

with open('canonical.txt', 'r') as f:
    canonical_text = f.read()

# Segment into sentences
sentences = segment_sentences(canonical_text)

# Configure
config = GrokAlignerConfig()
config.max_workers = 3
config.temperature = 0.1

# Align
print(f"Aligning {len(sentences)} sentences...")
spans, report = align_sentences_with_grok(
    sentences=sentences,
    words=words,
    config=config,
    pad_ms=100
)

# Display results
print(f"✓ Aligned: {report['global']['aligned']}")
print(f"✗ Failed: {report['global']['unaligned']}")

# Save results
output = {
    "sentences": [
        {
            "text": sent,
            "span_ms": {"start": span[0], "end": span[1]} if span else None
        }
        for sent, span in zip(sentences, spans)
    ]
}

with open('aligned_output.json', 'w') as f:
    json.dump(output, f, indent=2)

print("Results saved to aligned_output.json")
```

## Support

- xAI Documentation: https://docs.x.ai/
- xAI Console: https://console.x.ai/
- API Support: Check xAI documentation for support channels

## License

This integration uses the OpenAI Python library to communicate with xAI's Grok API. Ensure compliance with both xAI's terms of service and your project's license requirements.

