"""
Test script for dynamic repetitions feature.
This script demonstrates the dynamic repetition logic without requiring full audio processing.
"""

def calculate_repetitions(chunk_duration_seconds, threshold_seconds, short_repeats, long_repeats):
    """
    Calculate number of repetitions for a chunk based on its duration.
    
    Args:
        chunk_duration_seconds: Original chunk duration in seconds
        threshold_seconds: Threshold for determining short vs long chunks
        short_repeats: Repetitions for short chunks
        long_repeats: Repetitions for long chunks
    
    Returns:
        Number of repetitions
    """
    if chunk_duration_seconds < threshold_seconds:
        return short_repeats
    else:
        return long_repeats


def test_dynamic_repetitions():
    """Test dynamic repetition logic with sample data."""
    
    # Configuration
    threshold_seconds = 4.5
    short_chunk_repeats = 3
    long_chunk_repeats = 5
    
    # Sample sentence durations (in seconds)
    test_sentences = [
        ("Sentence 1", 2.5),   # Short - should get 3 repeats
        ("Sentence 2", 3.8),   # Short - should get 3 repeats
        ("Sentence 3", 4.2),   # Short - should get 3 repeats
        ("Sentence 4", 4.5),   # Long - should get 5 repeats (exactly at threshold)
        ("Sentence 5", 5.8),   # Long - should get 5 repeats
        ("Sentence 6", 7.2),   # Long - should get 5 repeats
        ("Sentence 7", 1.5),   # Short - should get 3 repeats
        ("Sentence 8", 8.9),   # Long - should get 5 repeats
    ]
    
    print("=" * 70)
    print("DYNAMIC REPETITIONS TEST")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Threshold: {threshold_seconds} seconds")
    print(f"  Short chunks (< {threshold_seconds}s): {short_chunk_repeats} repetitions")
    print(f"  Long chunks (≥ {threshold_seconds}s): {long_chunk_repeats} repetitions")
    print("\n" + "-" * 70)
    print(f"{'Sentence':<15} {'Duration (s)':<15} {'Type':<10} {'Repeats':<10}")
    print("-" * 70)
    
    short_count = 0
    long_count = 0
    
    for name, duration in test_sentences:
        repeats = calculate_repetitions(
            duration, 
            threshold_seconds, 
            short_chunk_repeats, 
            long_chunk_repeats
        )
        
        chunk_type = "Short" if duration < threshold_seconds else "Long"
        
        if chunk_type == "Short":
            short_count += 1
        else:
            long_count += 1
        
        print(f"{name:<15} {duration:<15.1f} {chunk_type:<10} {repeats:<10}")
    
    print("-" * 70)
    print(f"\nSummary:")
    print(f"  Short chunks: {short_count} sentences → {short_chunk_repeats} repeats each")
    print(f"  Long chunks:  {long_count} sentences → {long_chunk_repeats} repeats each")
    print(f"  Total sentences: {len(test_sentences)}")
    
    # Calculate total repetitions
    total_reps = (short_count * short_chunk_repeats) + (long_count * long_chunk_repeats)
    print(f"  Total repetitions: {total_reps}")
    print("=" * 70)
    print("Test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    test_dynamic_repetitions()

