"""
Manifest generation for dictation output.
Produces final_manifest.json and alignment_report.json
"""

from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import json


def create_final_manifest(
    audio_input: Path,
    sentences: List[str],
    sentence_spans: List[Optional[Tuple[int, int]]],
    sentence_timing_info: List[dict],
    alignment_report: dict,
    tempo: float,
    repeats: int,
    pause_ms: int,
    total_duration_ms: int,
    pad_ms: int
) -> dict:
    """
    Create the final manifest JSON structure.
    
    Args:
        audio_input: Path to source audio
        sentences: List of canonical sentences
        sentence_spans: List of (start_ms, end_ms) or None for each sentence
        sentence_timing_info: Timing info from audio pipeline
        alignment_report: Alignment report from aligner
        tempo: Tempo multiplier
        repeats: Number of repeats
        pause_ms: Pause duration
        total_duration_ms: Total output duration
        pad_ms: Padding used
    
    Returns:
        Manifest dictionary
    """
    manifest = {
        "audio_in": str(audio_input),
        "tempo": tempo,
        "pause_ms": pause_ms,
        "repeats": repeats,
        "sentences": [],
        "total_duration_ms": total_duration_ms
    }
    
    # Build sentence entries
    info_idx = 0
    for idx, sentence in enumerate(sentences, start=1):
        span = sentence_spans[idx - 1]
        
        if span is None:
            # Sentence not aligned
            manifest["sentences"].append({
                "idx": idx,
                "text": sentence,
                "status": "not_aligned",
                "source_span_ms": None,
                "quality": {"score": 0.0, "note": "alignment failed"},
                "output_offsets_ms": None
            })
            continue
        
        # Get timing info from audio pipeline
        if info_idx < len(sentence_timing_info):
            timing = sentence_timing_info[info_idx]
            info_idx += 1
        else:
            # Shouldn't happen, but handle gracefully
            manifest["sentences"].append({
                "idx": idx,
                "text": sentence,
                "status": "error",
                "source_span_ms": {"start": span[0], "end": span[1], "pad_ms": pad_ms},
                "quality": {"score": 0.0, "note": "timing info missing"},
                "output_offsets_ms": None
            })
            continue
        
        # Determine quality score from alignment report
        quality_score = 1.0
        quality_note = "ok"
        
        for detail in alignment_report.get("details", []):
            if detail.get("idx") == idx:
                quality_score = detail.get("score", 0.85)
                status = detail.get("status", "ok")
                if status == "warning":
                    quality_note = "low score but acceptable"
                elif status == "fallback":
                    quality_note = "found with fallback search"
                break
        
        # Build output offsets
        repeat_offsets = timing['repeat_offsets_ms']
        output_offsets = {}
        
        # Handle variable number of repetitions
        for rep_idx, (rep_start, rep_end) in enumerate(repeat_offsets, start=1):
            if rep_idx == 1:
                output_offsets["first_read_start"] = rep_start
                output_offsets["first_read_end"] = rep_end
            elif rep_idx == 2:
                output_offsets["second_read_start"] = rep_start
                output_offsets["second_read_end"] = rep_end
            elif rep_idx == 3:
                output_offsets["third_read_start"] = rep_start
                output_offsets["third_read_end"] = rep_end
            elif rep_idx == 4:
                output_offsets["fourth_read_start"] = rep_start
                output_offsets["fourth_read_end"] = rep_end
            elif rep_idx == 5:
                output_offsets["fifth_read_start"] = rep_start
                output_offsets["fifth_read_end"] = rep_end
        
        output_offsets["block_end"] = timing['block_end_ms']
        
        # Build sentence entry
        sentence_entry = {
            "idx": idx,
            "text": sentence,
            "source_span_ms": {
                "start": span[0],
                "end": span[1],
                "pad_ms": pad_ms
            },
            "quality": {
                "score": quality_score,
                "note": quality_note
            },
            "output_offsets_ms": output_offsets
        }
        
        # Add repetition count if available from timing info
        if 'num_repeats' in timing:
            sentence_entry['num_repeats'] = timing['num_repeats']
        
        # Add original duration if available
        if 'original_duration_seconds' in timing:
            sentence_entry['original_duration_seconds'] = round(timing['original_duration_seconds'], 3)
        
        manifest["sentences"].append(sentence_entry)
    
    return manifest


def create_alignment_report(
    aligner_report: dict,
    sentences: List[str]
) -> dict:
    """
    Create alignment report JSON structure.
    
    Args:
        aligner_report: Raw report from aligner
        sentences: List of sentences
    
    Returns:
        Formatted alignment report
    """
    report = {
        "global": {
            "num_sentences": len(sentences),
            "aligned": aligner_report["global"]["aligned"],
            "unaligned": aligner_report["global"]["unaligned"],
            "warnings": aligner_report["global"].get("warnings", 0)
        },
        "details": []
    }
    
    # Add method statistics if available
    if "methods" in aligner_report["global"]:
        report["global"]["methods"] = aligner_report["global"]["methods"]
    
    # Copy details with enhanced formatting
    for detail in aligner_report.get("details", []):
        entry = {
            "idx": detail["idx"],
            "text": detail["text"],
            "status": detail["status"],
            "score": detail.get("score", 0.0),
            "reason": detail.get("reason", detail.get("note", "")),
        }
        
        # Add alignment method if available
        if "method" in detail:
            entry["method"] = detail["method"]
        
        if "span" in detail:
            entry["span_indices"] = detail["span"]
        
        if "window_bounds" in detail:
            entry["window_bounds"] = detail["window_bounds"]
        
        report["details"].append(entry)
    
    return report


def save_manifests(
    output_dir: Path,
    manifest: dict,
    alignment_report: dict
) -> Tuple[Path, Path]:
    """
    Save manifest and alignment report to disk.
    
    Returns:
        (manifest_path, report_path)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = output_dir / "final_manifest.json"
    report_path = output_dir / "alignment_report.json"
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(alignment_report, f, ensure_ascii=False, indent=2)
    
    return manifest_path, report_path


def generate_alignment_summary(alignment_report: dict) -> str:
    """
    Generate a human-readable alignment summary.
    
    Returns:
        Summary string
    """
    global_stats = alignment_report["global"]
    total = global_stats["num_sentences"]
    aligned = global_stats["aligned"]
    unaligned = global_stats["unaligned"]
    warnings = global_stats.get("warnings", 0)
    
    lines = [
        f"Alignment Summary:",
        f"  Total sentences: {total}",
        f"  Successfully aligned: {aligned} ({aligned/total*100:.1f}%)",
        f"  Failed to align: {unaligned}",
        f"  Warnings: {warnings}"
    ]
    
    # Add method breakdown if available
    if "methods" in global_stats:
        methods = global_stats["methods"]
        lines.append(f"\nAlignment Methods:")
        lines.append(f"  Grok AI: {methods.get('grok', 0)}")
        lines.append(f"  Fuzzy matching: {methods.get('fuzzy', 0)}")
    
    if alignment_report.get("details"):
        lines.append(f"\nIssues:")
        for detail in alignment_report["details"]:
            idx = detail["idx"]
            status = detail["status"]
            score = detail.get("score", 0)
            method = detail.get("method", "unknown")
            text_preview = detail["text"][:60]
            if len(detail["text"]) > 60:
                text_preview += "..."
            lines.append(f"  [{idx}] {status} (score: {score:.2f}, method: {method}) - {text_preview}")
    
    return "\n".join(lines)

