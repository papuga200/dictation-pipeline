"""
Demo script for Grok-based alignment.
Shows how to use the Grok alignment engine instead of fuzzy matching.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from pipeline.grok_alignment import align_sentences_with_grok, GrokAlignerConfig
from pipeline.segmentation import segment_sentences

# Load environment variables from .env file
load_dotenv()


def load_transcription_json(json_path: str):
    """Load transcription JSON from file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def load_canonical_text(text_path: str):
    """Load canonical text from file."""
    with open(text_path, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    """
    Demo: Align U4A.txt with U4A.json using Grok API.
    """
    
    # Check for API key
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("❌ Error: XAI_API_KEY environment variable not set!")
        print("\nTo use Grok alignment:")
        print("1. Get your API key from https://console.x.ai/")
        print("2. Set the environment variable:")
        print("   export XAI_API_KEY='your-api-key-here'")
        print("\nOr in Python:")
        print("   os.environ['XAI_API_KEY'] = 'your-api-key-here'")
        return
    
    print("🚀 Grok Alignment Demo\n")
    print("=" * 60)
    
    # Load data
    print("\n📂 Loading data...")
    transcription = load_transcription_json("U4A.json")
    canonical_text = load_canonical_text("U4A.txt")
    
    # Extract words from transcription
    words = transcription.get("words", [])
    print(f"   ✓ Loaded {len(words)} words from transcription")
    
    # Segment canonical text into sentences
    print("\n📝 Segmenting canonical text into sentences...")
    sentences = segment_sentences(canonical_text)
    print(f"   ✓ Found {len(sentences)} sentences")
    
    # Show first few sentences
    print("\n   First 3 sentences:")
    for i, sent in enumerate(sentences[:3], 1):
        print(f"   {i}. {sent[:80]}{'...' if len(sent) > 80 else ''}")
    
    # Configure Grok aligner
    print("\n⚙️  Configuring Grok aligner...")
    config = GrokAlignerConfig()
    config.max_workers = 3  # Process 3 sentences at a time
    config.temperature = 0.1  # Low temperature for consistency
    print(f"   ✓ Model: {config.model}")
    print(f"   ✓ Parallel workers: {config.max_workers}")
    
    # Run alignment
    print("\n🤖 Running Grok alignment (this may take a minute)...")
    print("   Sending requests to Grok API...")
    
    try:
        spans, report = align_sentences_with_grok(
            sentences=sentences,
            words=words,
            config=config,
            pad_ms=100
        )
        
        # Display results
        print("\n✅ Alignment complete!")
        print("\n" + "=" * 60)
        print("📊 ALIGNMENT REPORT")
        print("=" * 60)
        
        global_stats = report["global"]
        print(f"\n📈 Global Statistics:")
        print(f"   Total sentences:    {global_stats['num_sentences']}")
        print(f"   ✓ Aligned:          {global_stats['aligned']}")
        print(f"   ✗ Unaligned:        {global_stats['unaligned']}")
        print(f"   ⚠ Warnings:         {global_stats['warnings']}")
        
        # Show success rate
        success_rate = (global_stats['aligned'] / global_stats['num_sentences']) * 100
        print(f"\n   Success rate: {success_rate:.1f}%")
        
        # Show detailed results for first few sentences
        print("\n📋 First 5 aligned sentences:")
        print("-" * 60)
        
        for i, (sentence, span) in enumerate(zip(sentences[:5], spans[:5]), 1):
            if span:
                start_ms, end_ms = span
                duration_ms = end_ms - start_ms
                print(f"\n{i}. {sentence[:60]}{'...' if len(sentence) > 60 else ''}")
                print(f"   ⏱️  {start_ms}ms → {end_ms}ms (duration: {duration_ms}ms)")
            else:
                print(f"\n{i}. {sentence[:60]}{'...' if len(sentence) > 60 else ''}")
                print(f"   ❌ Failed to align")
        
        # Show warnings if any
        if report["details"]:
            print("\n⚠️  Warnings and Issues:")
            print("-" * 60)
            for detail in report["details"][:5]:  # Show first 5
                idx = detail["idx"]
                status = detail["status"]
                reason = detail.get("reason", "Unknown")
                print(f"\nSentence {idx}: [{status.upper()}]")
                print(f"   {detail['text'][:60]}...")
                print(f"   Reason: {reason}")
                if "confidence" in detail:
                    print(f"   Confidence: {detail['confidence']:.2f}")
        
        # Save results to file
        output_path = "output/grok_alignment_results.json"
        os.makedirs("output", exist_ok=True)
        
        result_data = {
            "sentences": [
                {
                    "idx": i + 1,
                    "text": sent,
                    "span_ms": {"start": span[0], "end": span[1]} if span else None
                }
                for i, (sent, span) in enumerate(zip(sentences, spans))
            ],
            "report": report
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_path}")
        
        # Compare with original alignment if available
        original_manifest = Path("output/final_manifest.json")
        if original_manifest.exists():
            print("\n🔍 Comparison with original alignment:")
            with open(original_manifest, 'r') as f:
                original_data = json.load(f)
            
            original_aligned = sum(
                1 for s in original_data["sentences"] 
                if s.get("source_span_ms") is not None
            )
            
            print(f"   Original fuzzy matching: {original_aligned} aligned")
            print(f"   Grok-based alignment:    {global_stats['aligned']} aligned")
            
            if global_stats['aligned'] > original_aligned:
                print(f"   🎉 Grok found {global_stats['aligned'] - original_aligned} more alignments!")
            elif global_stats['aligned'] == original_aligned:
                print(f"   ✓ Same number of alignments")
            else:
                print(f"   ⚠️  Grok found {original_aligned - global_stats['aligned']} fewer alignments")
        
    except Exception as e:
        print(f"\n❌ Error during alignment: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("\nNext steps:")
    print("1. Review the alignment results in output/grok_alignment_results.json")
    print("2. Compare quality with the fuzzy matching results")
    print("3. Integrate Grok alignment into your main pipeline if satisfied")
    print("=" * 60)


if __name__ == "__main__":
    main()

