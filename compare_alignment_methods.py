"""
Comparison script: Fuzzy Matching vs Grok Alignment
Shows the differences in alignment results between the two methods.
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from pipeline.grok_alignment import align_sentences_with_grok, GrokAlignerConfig
from pipeline.alignment import align_sentences_to_words, AlignmentConfig
from pipeline.segmentation import segment_sentences

# Load environment variables from .env file
load_dotenv()


def load_data():
    """Load transcription and canonical text."""
    with open("U4A.json", 'r', encoding='utf-8') as f:
        transcription = json.load(f)
    
    with open("U4A.txt", 'r', encoding='utf-8') as f:
        canonical_text = f.read()
    
    return transcription["words"], canonical_text


def format_time_ms(ms):
    """Format milliseconds as MM:SS.mmm"""
    total_sec = ms / 1000.0
    minutes = int(total_sec // 60)
    seconds = total_sec % 60
    return f"{minutes:02d}:{seconds:06.3f}"


def compare_alignments():
    """Compare fuzzy matching and Grok alignment."""
    
    print("=" * 80)
    print("🔍 ALIGNMENT METHOD COMPARISON")
    print("=" * 80)
    print()
    
    # Check for API key
    has_api_key = bool(os.getenv("XAI_API_KEY"))
    
    if not has_api_key:
        print("⚠️  WARNING: XAI_API_KEY not set. Grok alignment will be skipped.")
        print("   Set your API key to enable Grok comparison.")
        print()
    
    # Load data
    print("📂 Loading data...")
    words, canonical_text = load_data()
    sentences = segment_sentences(canonical_text)
    print(f"   ✓ {len(words)} words in transcription")
    print(f"   ✓ {len(sentences)} sentences in canonical text")
    print()
    
    # Method 1: Fuzzy Matching
    print("=" * 80)
    print("METHOD 1: FUZZY MATCHING (Traditional)")
    print("=" * 80)
    
    print("\n⚙️  Running fuzzy matching alignment...")
    fuzzy_start = time.time()
    
    fuzzy_config = AlignmentConfig()
    fuzzy_spans, fuzzy_report = align_sentences_to_words(
        sentences=sentences,
        words=words,
        config=fuzzy_config,
        pad_ms=100
    )
    
    fuzzy_duration = time.time() - fuzzy_start
    
    print(f"✓ Completed in {fuzzy_duration:.2f} seconds")
    print(f"\n📊 Results:")
    print(f"   Aligned:    {fuzzy_report['global']['aligned']}/{fuzzy_report['global']['num_sentences']}")
    print(f"   Unaligned:  {fuzzy_report['global']['unaligned']}")
    print(f"   Warnings:   {fuzzy_report['global']['warnings']}")
    
    success_rate_fuzzy = (fuzzy_report['global']['aligned'] / fuzzy_report['global']['num_sentences']) * 100
    print(f"   Success:    {success_rate_fuzzy:.1f}%")
    
    # Method 2: Grok Alignment
    grok_spans = None
    grok_report = None
    grok_duration = None
    
    if has_api_key:
        print("\n" + "=" * 80)
        print("METHOD 2: GROK AI ALIGNMENT")
        print("=" * 80)
        
        print("\n⚙️  Running Grok alignment...")
        grok_start = time.time()
        
        try:
            grok_config = GrokAlignerConfig()
            grok_config.max_workers = 3  # Parallel processing
            
            grok_spans, grok_report = align_sentences_with_grok(
                sentences=sentences,
                words=words,
                config=grok_config,
                pad_ms=100
            )
            
            grok_duration = time.time() - grok_start
            
            print(f"✓ Completed in {grok_duration:.2f} seconds")
            print(f"\n📊 Results:")
            print(f"   Aligned:    {grok_report['global']['aligned']}/{grok_report['global']['num_sentences']}")
            print(f"   Unaligned:  {grok_report['global']['unaligned']}")
            print(f"   Warnings:   {grok_report['global']['warnings']}")
            
            success_rate_grok = (grok_report['global']['aligned'] / grok_report['global']['num_sentences']) * 100
            print(f"   Success:    {success_rate_grok:.1f}%")
            
        except Exception as e:
            print(f"❌ Error running Grok alignment: {e}")
            has_api_key = False  # Disable comparison
    
    # Comparison
    print("\n" + "=" * 80)
    print("📊 COMPARISON")
    print("=" * 80)
    
    print("\n┌─────────────────────────┬──────────────────┬──────────────────┐")
    print("│ Metric                  │ Fuzzy Matching   │ Grok Alignment   │")
    print("├─────────────────────────┼──────────────────┼──────────────────┤")
    
    print(f"│ Time                    │ {fuzzy_duration:>14.2f}s │", end="")
    if has_api_key and grok_duration:
        print(f" {grok_duration:>14.2f}s │")
    else:
        print(" N/A              │")
    
    print(f"│ Aligned                 │ {fuzzy_report['global']['aligned']:>16} │", end="")
    if has_api_key and grok_report:
        print(f" {grok_report['global']['aligned']:>16} │")
    else:
        print(" N/A              │")
    
    print(f"│ Unaligned               │ {fuzzy_report['global']['unaligned']:>16} │", end="")
    if has_api_key and grok_report:
        print(f" {grok_report['global']['unaligned']:>16} │")
    else:
        print(" N/A              │")
    
    print(f"│ Warnings                │ {fuzzy_report['global']['warnings']:>16} │", end="")
    if has_api_key and grok_report:
        print(f" {grok_report['global']['warnings']:>16} │")
    else:
        print(" N/A              │")
    
    print(f"│ Success Rate            │ {success_rate_fuzzy:>14.1f}% │", end="")
    if has_api_key and grok_report:
        success_rate_grok = (grok_report['global']['aligned'] / grok_report['global']['num_sentences']) * 100
        print(f" {success_rate_grok:>14.1f}% │")
    else:
        print(" N/A              │")
    
    print("└─────────────────────────┴──────────────────┴──────────────────┘")
    
    # Detailed sentence comparison
    if has_api_key and grok_spans:
        print("\n" + "=" * 80)
        print("🔎 SENTENCE-BY-SENTENCE COMPARISON")
        print("=" * 80)
        
        differences = []
        
        for i, (sentence, fuzzy_span, grok_span) in enumerate(zip(sentences, fuzzy_spans, grok_spans), 1):
            fuzzy_aligned = fuzzy_span is not None
            grok_aligned = grok_span is not None
            
            # Case 1: Both aligned - compare timestamps
            if fuzzy_aligned and grok_aligned:
                fuzzy_start, fuzzy_end = fuzzy_span
                grok_start, grok_end = grok_span
                
                start_diff_ms = abs(fuzzy_start - grok_start)
                end_diff_ms = abs(fuzzy_end - grok_end)
                
                # Significant difference (>500ms)
                if start_diff_ms > 500 or end_diff_ms > 500:
                    differences.append({
                        'idx': i,
                        'sentence': sentence,
                        'type': 'timestamp_diff',
                        'fuzzy': fuzzy_span,
                        'grok': grok_span,
                        'diff_ms': max(start_diff_ms, end_diff_ms)
                    })
            
            # Case 2: Only fuzzy aligned
            elif fuzzy_aligned and not grok_aligned:
                differences.append({
                    'idx': i,
                    'sentence': sentence,
                    'type': 'fuzzy_only',
                    'fuzzy': fuzzy_span,
                    'grok': None
                })
            
            # Case 3: Only Grok aligned
            elif not fuzzy_aligned and grok_aligned:
                differences.append({
                    'idx': i,
                    'sentence': sentence,
                    'type': 'grok_only',
                    'fuzzy': None,
                    'grok': grok_span
                })
            
            # Case 4: Both failed
            elif not fuzzy_aligned and not grok_aligned:
                differences.append({
                    'idx': i,
                    'sentence': sentence,
                    'type': 'both_failed',
                    'fuzzy': None,
                    'grok': None
                })
        
        # Display differences
        if differences:
            print(f"\nFound {len(differences)} differences:\n")
            
            for diff in differences[:10]:  # Show first 10
                idx = diff['idx']
                sentence = diff['sentence'][:70] + ('...' if len(diff['sentence']) > 70 else '')
                
                print(f"Sentence {idx}:")
                print(f"  {sentence}")
                
                if diff['type'] == 'timestamp_diff':
                    fuzzy_s, fuzzy_e = diff['fuzzy']
                    grok_s, grok_e = diff['grok']
                    print(f"  Fuzzy:  {format_time_ms(fuzzy_s)} → {format_time_ms(fuzzy_e)}")
                    print(f"  Grok:   {format_time_ms(grok_s)} → {format_time_ms(grok_e)}")
                    print(f"  ⚠️  Difference: {diff['diff_ms']:.0f}ms")
                
                elif diff['type'] == 'fuzzy_only':
                    fuzzy_s, fuzzy_e = diff['fuzzy']
                    print(f"  Fuzzy:  {format_time_ms(fuzzy_s)} → {format_time_ms(fuzzy_e)}")
                    print(f"  Grok:   ❌ Failed to align")
                
                elif diff['type'] == 'grok_only':
                    grok_s, grok_e = diff['grok']
                    print(f"  Fuzzy:  ❌ Failed to align")
                    print(f"  Grok:   {format_time_ms(grok_s)} → {format_time_ms(grok_e)}")
                    print(f"  ✨ Grok found alignment!")
                
                elif diff['type'] == 'both_failed':
                    print(f"  Both methods failed to align this sentence")
                
                print()
        else:
            print("\n✅ No significant differences found!")
    
    # Save comparison results
    print("=" * 80)
    print("💾 Saving results...")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    comparison_data = {
        "fuzzy_matching": {
            "duration_seconds": fuzzy_duration,
            "report": fuzzy_report,
            "spans": [
                {"start": s[0], "end": s[1]} if s else None
                for s in fuzzy_spans
            ]
        }
    }
    
    if has_api_key and grok_report:
        comparison_data["grok_alignment"] = {
            "duration_seconds": grok_duration,
            "report": grok_report,
            "spans": [
                {"start": s[0], "end": s[1]} if s else None
                for s in grok_spans
            ]
        }
    
    comparison_data["sentences"] = sentences
    
    output_path = output_dir / "alignment_comparison.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Saved to: {output_path}")
    
    print("\n" + "=" * 80)
    print("✅ Comparison complete!")
    print("=" * 80)


if __name__ == "__main__":
    compare_alignments()

