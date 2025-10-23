# Dynamic Repetitions Feature

## Overview

The dynamic repetitions feature automatically adjusts the number of times each sentence is repeated based on the original chunk duration (before tempo adjustment). This provides a more intelligent dictation experience where:
- **Short chunks** get fewer repetitions (default: 3×)
- **Long chunks** get more repetitions (default: 5×)

## Rationale

Previously, all sentences were repeated the same number of times regardless of their length or complexity. This led to:
- Short, simple sentences taking up excessive time
- Long, complex sentences potentially not getting enough practice time

With dynamic repetitions, the system intelligently adjusts based on each sentence's characteristics.

## Configuration

### Default Settings

```yaml
dynamic_repetitions:
  enabled: true                # Enable dynamic repetitions
  threshold_seconds: 4.5       # Chunks < this get short_repeats, >= get long_repeats
  short_chunk_repeats: 3       # Repetitions for short chunks
  long_chunk_repeats: 5        # Repetitions for long chunks
```

### UI Controls

In the Streamlit interface sidebar, under **"🔄 Repetitions"**:

1. **Enable dynamic repetitions** (checkbox)
   - When enabled, shows threshold slider and repeat counts
   - When disabled, shows single repeat count input (fixed repetitions)

2. **Long chunk threshold** (slider: 1.0 - 10.0 seconds)
   - Default: 4.5 seconds
   - Chunks shorter than this threshold get `short_chunk_repeats`
   - Chunks at or above this threshold get `long_chunk_repeats`

3. **Short chunks repetitions** (number input: 1-10)
   - Default: 3 repetitions
   - Applied to chunks < threshold

4. **Long chunks repetitions** (number input: 1-10)
   - Default: 5 repetitions
   - Applied to chunks ≥ threshold

## Implementation Details

### Logic Flow

1. **Chunk Duration Calculation**
   - Original chunk duration is calculated from source audio timestamps: `end_ms - start_ms`
   - This is done BEFORE tempo adjustment to use the natural speaking rate

2. **Repetition Determination**
   ```python
   if original_chunk_duration_seconds < threshold_seconds:
       sentence_repeats = short_chunk_repeats
   else:
       sentence_repeats = long_chunk_repeats
   ```

3. **Audio Processing**
   - Each sentence uses its calculated repetition count
   - Pauses are inserted between repetitions as configured
   - Timing information tracks actual repetitions used

### Files Modified

1. **config.yaml**
   - Added `dynamic_repetitions` section with default parameters

2. **pipeline/builder.py**
   - Added dynamic repetitions to default config
   - Passes dynamic repetition parameters to audio pipeline
   - Supports both dynamic and fixed repetition modes

3. **pipeline/audio.py**
   - Updated `build_dictation_audio()` function signature
   - Added parameters: `dynamic_reps_enabled`, `dynamic_threshold_seconds`, `dynamic_short_repeats`, `dynamic_long_repeats`
   - Calculates repetitions per sentence based on original duration
   - Stores `num_repeats` and `original_duration_seconds` in timing info

4. **pipeline/manifest.py**
   - Updated to handle variable number of repetitions (up to 5)
   - Adds `num_repeats` and `original_duration_seconds` to manifest output
   - Supports `fourth_read` and `fifth_read` offset keys

5. **app.py**
   - Added UI controls in sidebar for dynamic repetitions
   - Checkbox to enable/disable feature
   - Slider for threshold adjustment
   - Number inputs for short and long repetition counts
   - Updated build summary to show repetition mode
   - Added repetition breakdown display after build completion

6. **README.md**
   - Added feature to "What's New" section
   - Added feature to main features list
   - Added detailed "Dynamic Repetitions" configuration section with examples

### Manifest Output

Each sentence in the final manifest now includes:

```json
{
  "idx": 5,
  "text": "This is a longer sentence that takes more time.",
  "num_repeats": 5,
  "original_duration_seconds": 5.8,
  "source_span_ms": { ... },
  "quality": { ... },
  "output_offsets_ms": {
    "first_read_start": 0,
    "first_read_end": 6200,
    "second_read_start": 16200,
    "second_read_end": 22400,
    "third_read_start": 32400,
    "third_read_end": 38600,
    "fourth_read_start": 48600,
    "fourth_read_end": 54800,
    "fifth_read_start": 64800,
    "fifth_read_end": 71000,
    "block_end": 81000
  }
}
```

## Examples

### Example 1: Default Settings

With threshold = 4.5s, short = 3, long = 5:

| Sentence | Duration | Type | Repeats |
|----------|----------|------|---------|
| "Hi there!" | 1.2s | Short | 3× |
| "How are you?" | 2.5s | Short | 3× |
| "The weather is nice today." | 3.8s | Short | 3× |
| "I'm going to the store later." | 4.2s | Short | 3× |
| "Would you like to come with me?" | 4.5s | Long | 5× |
| "The ship was discovered in two main parts." | 5.8s | Long | 5× |
| "It was lying four kilometers under the sea." | 7.2s | Long | 5× |

### Example 2: Custom Settings

With threshold = 3.0s, short = 2, long = 4:

| Sentence | Duration | Type | Repeats |
|----------|----------|------|---------|
| "Hi!" | 0.8s | Short | 2× |
| "Good morning." | 2.1s | Short | 2× |
| "How are you today?" | 3.0s | Long | 4× |
| "I'm doing very well, thank you." | 4.5s | Long | 4× |

## Benefits

1. **Time Efficiency**
   - Short sentences don't waste time with excessive repetitions
   - Total audio duration is optimized

2. **Learning Optimization**
   - Longer, more complex sentences get extra practice time
   - Students have more opportunities to transcribe difficult content

3. **Flexibility**
   - Fully configurable threshold and repetition counts
   - Can be disabled for traditional fixed repetitions
   - Easy to adjust per project needs

4. **Transparency**
   - Manifest includes exact repetition count per sentence
   - UI shows breakdown after build completion
   - Easy to verify and analyze results

## Testing

Run the included test script to verify the logic:

```bash
python test_dynamic_reps.py
```

Output example:
```
======================================================================
DYNAMIC REPETITIONS TEST
======================================================================

Configuration:
  Threshold: 4.5 seconds
  Short chunks (< 4.5s): 3 repetitions
  Long chunks (≥ 4.5s): 5 repetitions

----------------------------------------------------------------------
Sentence        Duration (s)    Type       Repeats   
----------------------------------------------------------------------
Sentence 1      2.5             Short      3         
Sentence 2      3.8             Short      3         
Sentence 3      4.2             Short      3         
Sentence 4      4.5             Long       5         
Sentence 5      5.8             Long       5         
Sentence 6      7.2             Long       5         
Sentence 7      1.5             Short      3         
Sentence 8      8.9             Long       5         
----------------------------------------------------------------------

Summary:
  Short chunks: 4 sentences → 3 repeats each
  Long chunks:  4 sentences → 5 repeats each
  Total sentences: 8
  Total repetitions: 32
======================================================================
Test completed successfully!
======================================================================
```

## Backwards Compatibility

- The old `repeats` parameter is still supported for backwards compatibility
- When `dynamic_repetitions.enabled = false`, system uses fixed `repeats` value
- Existing config files and code will continue to work
- Default behavior is dynamic repetitions enabled

## Future Enhancements

Potential future improvements:
- Multiple thresholds (very short, short, medium, long, very long)
- Automatic threshold detection based on content analysis
- Per-sentence manual override in UI
- Difficulty-based repetitions (combining with quality scores)
- Integration with learning analytics

---

**Date Implemented:** October 23, 2024  
**Version:** 1.1.0  
**Author:** Assistant (via user request)

