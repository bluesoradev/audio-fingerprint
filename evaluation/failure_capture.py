"""Capture failure cases with artifacts."""
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from tqdm import tqdm

# Import function to extract file ID from segment ID
from evaluation.metrics import extract_file_id_from_segment_id

logger = logging.getLogger(__name__)


def save_failure_summary(
    case_dir: Path,
    transformed_id: str,
    original_id: str,
    top_matches: List[Dict],
    query_results: Dict,
    reason: str
):
    """
    Generate fast text summary for failure case (replaces slow spectrograms).
    
    This provides comprehensive verification data in <0.1 seconds vs 10-14 seconds
    for spectrogram generation, while maintaining full accuracy.
    
    Args:
        case_dir: Directory to save summary
        transformed_id: ID of transformed file
        original_id: Expected original ID
        top_matches: Top-K match results
        query_results: Full query result dictionary
        reason: Failure reason
    """
    # Find correct match rank (if present in top matches)
    correct_match_rank = None
    correct_match_similarity = None
    correct_match_id = None
    
    for i, match in enumerate(top_matches, 1):
        match_id = match.get("id", "")
        match_file_id = extract_file_id_from_segment_id(match_id)
        if match_file_id == original_id:
            correct_match_rank = i
            correct_match_similarity = match.get("mean_similarity", match.get("similarity", 0))
            correct_match_id = match_id
            break
    
    # Extract key metrics
    top_match = top_matches[0] if top_matches else {}
    similarity_metrics = query_results.get("similarity_metrics", {})
    performance_metrics = query_results.get("performance_metrics", {})
    cache_metrics = query_results.get("cache_metrics", {})
    
    # Build summary
    summary_lines = [
        "=" * 70,
        "FAILURE CASE SUMMARY",
        "=" * 70,
        f"Transform ID: {transformed_id}",
        f"Expected Original: {original_id}",
        f"Failure Reason: {reason}",
        f"Transform Type: {query_results.get('transform_type', 'unknown')}",
        f"Severity: {query_results.get('severity', 'unknown')}",
        "",
        "TOP 5 MATCHES:",
        "-" * 70,
    ]
    
    # Add top 5 matches
    for i, match in enumerate(top_matches[:5], 1):
        match_id = match.get("id", "")
        match_file_id = extract_file_id_from_segment_id(match_id)
        similarity = match.get("mean_similarity", match.get("similarity", 0))
        rank = match.get("rank", i)
        confidence = match.get("confidence", 0)
        quality = match.get("quality_score", 0)
        max_seg_sim = match.get("max_segment_similarity", similarity)
        match_count = match.get("match_count", 0)
        rank_1_count = match.get("rank_1_count", 0)
        
        is_correct = "✓ CORRECT" if match_file_id == original_id else "✗ WRONG"
        
        summary_lines.append(f"  {i}. {match_id[:70]}")
        summary_lines.append(f"     File ID: {match_file_id} {is_correct}")
        summary_lines.append(f"     Similarity: {similarity:.4f} | Max Segment: {max_seg_sim:.4f}")
        summary_lines.append(f"     Rank: {rank} | Confidence: {confidence:.3f} | Quality: {quality:.3f}")
        summary_lines.append(f"     Segment Matches: {match_count} | Rank-1 Segments: {rank_1_count}")
        summary_lines.append("")
    
    # Correct match analysis
    summary_lines.extend([
        "CORRECT MATCH ANALYSIS:",
        "-" * 70,
    ])
    
    if correct_match_rank:
        summary_lines.append(f"  ✓ Found in top-{correct_match_rank} (similarity: {correct_match_similarity:.4f})")
        summary_lines.append(f"  Segment ID: {correct_match_id}")
        if correct_match_rank == 1:
            summary_lines.append(f"  Issue: ID mismatch (correct match is rank 1 but wrong file ID)")
        else:
            summary_lines.append(f"  Issue: Aggregation problem (correct match is rank {correct_match_rank}, not rank 1)")
    else:
        summary_lines.append(f"  ✗ Not found in top-5 matches")
        summary_lines.append(f"  Issue: Correct match missing from top results (query/index issue)")
    
    summary_lines.extend([
        "",
        "SIMILARITY METRICS:",
        "-" * 70,
    ])
    
    # Add similarity metrics
    num_segments = query_results.get("num_segments", 0)
    if top_match:
        summary_lines.append(f"  Top Match Similarity: {top_match.get('mean_similarity', 0):.4f}")
        summary_lines.append(f"  Max Segment Similarity: {top_match.get('max_segment_similarity', 0):.4f}")
        summary_lines.append(f"  P95 Similarity: {top_match.get('p95_similarity', 0):.4f}")
    
    if similarity_metrics:
        summary_lines.append(f"  Mean Similarity: {similarity_metrics.get('mean_similarity', 0):.4f}")
        summary_lines.append(f"  Min Similarity: {similarity_metrics.get('min_similarity', 0):.4f}")
        summary_lines.append(f"  Max Similarity: {similarity_metrics.get('max_similarity', 0):.4f}")
        summary_lines.append(f"  Std Deviation: {similarity_metrics.get('std_similarity', 0):.4f}")
    
    summary_lines.extend([
        "",
        "SEGMENT ANALYSIS:",
        "-" * 70,
    ])
    
    if top_match and num_segments > 0:
        match_count = top_match.get("match_count", 0)
        rank_1_count = top_match.get("rank_1_count", 0)
        summary_lines.append(f"  Total Segments: {num_segments}")
        summary_lines.append(f"  Segments Matching Top Result: {match_count} ({match_count/num_segments*100:.1f}%)")
        summary_lines.append(f"  Rank-1 Segment Ratio: {rank_1_count}/{num_segments} ({rank_1_count/num_segments*100:.1f}%)")
    
    # Find correct match in segment results
    segment_results = query_results.get("segment_results", [])
    correct_segment_matches = 0
    correct_segment_similarities = []
    
    if segment_results:
        for seg_result in segment_results:
            seg_matches = seg_result.get("results", [])
            for seg_match in seg_matches[:5]:  # Check top 5 per segment
                seg_match_id = seg_match.get("id", "")
                seg_match_file_id = extract_file_id_from_segment_id(seg_match_id)
                if seg_match_file_id == original_id:
                    correct_segment_matches += 1
                    correct_segment_similarities.append(seg_match.get("similarity", 0))
                    break
        
        if correct_segment_matches > 0:
            total_segments = len(segment_results)
            match_percentage = (correct_segment_matches / total_segments * 100) if total_segments > 0 else 0.0
            summary_lines.append(f"  Segments Matching Correct File: {correct_segment_matches}/{total_segments} ({match_percentage:.1f}%)")
            if correct_segment_similarities:
                summary_lines.append(f"  Avg Similarity for Correct Segments: {np.mean(correct_segment_similarities):.4f}")
                summary_lines.append(f"  Max Similarity for Correct Segments: {np.max(correct_segment_similarities):.4f}")
    
    if not segment_results:
        summary_lines.append(f"  No segment results available")
    
    summary_lines.extend([
        "",
        "QUERY PERFORMANCE:",
        "-" * 70,
        f"  Latency: {query_results.get('latency_ms', 0):.1f}ms",
        f"  Cache Hit: {cache_metrics.get('cache_hit', False)}",
    ])
    
    if performance_metrics:
        summary_lines.append(f"  Query Time: {performance_metrics.get('query_time_ms', 0):.1f}ms")
        summary_lines.append(f"  Embedding Time: {performance_metrics.get('embedding_time_ms', 0):.1f}ms")
        summary_lines.append(f"  Index Time: {performance_metrics.get('index_time_ms', 0):.1f}ms")
    
    summary_lines.extend([
        "",
        "AUDIO FILES:",
        "-" * 70,
        f"  - transformed.wav: Query file ({transformed_id})",
        f"  - original.wav: Expected match ({original_id})",
        "",
        "VERIFICATION:",
        "-" * 70,
        "  1. Listen to transformed.wav vs original.wav to verify audio similarity",
        "  2. Check JSON metadata (failure_details.json) for detailed query results",
        "  3. Analyze segment_results to understand which segments matched correctly",
        "  4. Review similarity metrics to identify the failure mode",
        "",
        "=" * 70,
    ])
    
    # Save summary
    summary_path = case_dir / "failure_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))


def capture_failure_case(
    transformed_id: str,
    transformed_path: Path,
    original_id: str,
    original_path: Path,
    query_results: Dict,
    top_matches: List[Dict],
    reason: str,
    output_dir: Path,
    index_metadata: Dict = None,
    include_daw_context: bool = True,
    orig_to_path: Dict = None
):
    """
    Capture a failure case with all artifacts.
    
    Args:
        transformed_id: ID of transformed file
        transformed_path: Path to transformed audio
        original_id: Expected original ID
        original_path: Path to original audio
        query_results: Full query result dictionary
        top_matches: Top-K match results
        reason: Reason for failure
        output_dir: Directory to save artifacts
        index_metadata: Index metadata (for finding matched audio paths)
    """
    case_dir = output_dir / transformed_id
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # Save transformed audio
    if transformed_path.exists():
        copy_path = case_dir / "transformed.wav"
        shutil.copy2(transformed_path, copy_path)
    
    # Save original audio
    if original_path.exists():
        copy_path = case_dir / "original.wav"
        shutil.copy2(original_path, copy_path)
    
    # Save top match audio (if we can find it)
    if top_matches and len(top_matches) > 0 and orig_to_path:
        top_match_id = top_matches[0].get("id", "")
        top_match_file_id = extract_file_id_from_segment_id(top_match_id)
        
        # Try to find and save top match audio file
        top_match_path = orig_to_path.get(top_match_file_id)
        if top_match_path and Path(top_match_path).exists():
            copy_path = case_dir / "top_match.wav"
            shutil.copy2(Path(top_match_path), copy_path)
            logger.debug(f"Saved top match audio: {copy_path}")
    
    # Generate fast text summary (replaces slow spectrogram generation)
    # This provides comprehensive verification data in <0.1s vs 10-14s for spectrograms
    save_failure_summary(
        case_dir=case_dir,
        transformed_id=transformed_id,
        original_id=original_id,
        top_matches=top_matches,
        query_results=query_results,
        reason=reason
    )
    
    # Load DAW metadata if available
    daw_metadata = None
    if include_daw_context:
        try:
            from daw_parser.integration import find_daw_file_for_audio, get_parser_for_file
            from daw_parser.integration import get_daw_metadata_for_file
            
            # Try to get DAW metadata from index_metadata first
            if index_metadata:
                daw_metadata = get_daw_metadata_for_file(original_id, index_metadata)
            
            # If not in index, try to find and parse DAW file
            if not daw_metadata and original_path.exists():
                daw_file = find_daw_file_for_audio(original_path)
                if daw_file:
                    try:
                        parser = get_parser_for_file(daw_file)
                        daw_metadata_obj = parser.parse()
                        daw_metadata = daw_metadata_obj.to_dict()
                    except Exception as e:
                        logger.debug(f"Failed to parse DAW file for failure case: {e}")
        except ImportError:
            logger.debug("DAW parser not available, skipping DAW context")
        except Exception as e:
            logger.debug(f"Error loading DAW context: {e}")
    
    # Save query results JSON snippet
    query_snippet = {
        "transformed_id": transformed_id,
        "expected_original_id": original_id,
        "top_matches": top_matches[:5],  # Top 5
        "query_results": query_results,
        "failure_reason": reason,
        "daw_metadata": daw_metadata,  # Include DAW context
    }
    
    with open(case_dir / "failure_details.json", 'w') as f:
        json.dump(query_snippet, f, indent=2, default=str)
    
    logger.debug(f"Captured failure case: {case_dir}")


def capture_failures(
    query_summary_path: Path,
    transform_manifest_path: Path,
    files_manifest_path: Path,
    query_results_dir: Path,
    output_dir: Path,
    max_failures_per_transform: int = 10,
    index_metadata: Dict = None
):
    """
    Capture failure cases from query results.
    
    Args:
        query_summary_path: Path to query summary CSV
        transform_manifest_path: Path to transform manifest
        files_manifest_path: Path to original files manifest
        query_results_dir: Directory with individual query JSON files
        output_dir: Directory to save failure artifacts
        max_failures_per_transform: Max failures to capture per transform type
        index_metadata: Index metadata
    """
    # Load data
    query_df = pd.read_csv(query_summary_path)
    transform_df = pd.read_csv(transform_manifest_path)
    files_df = pd.read_csv(files_manifest_path)
    
    # Build mappings
    transform_to_orig = dict(zip(transform_df["transformed_id"], transform_df["orig_id"]))
    transform_to_path = dict(zip(transform_df["transformed_id"], transform_df["output_path"]))
    orig_to_path = dict(zip(files_df["id"], files_df["file_path"]))
    
    # Identify failures (where top_match_id != expected orig_id)
    # CRITICAL FIX: Extract file ID from segment ID before comparison
    # top_match_id is a segment ID (e.g., "track1_seg_0000"), but expected_orig_id is a file ID (e.g., "track1")
    query_df = query_df.copy()
    query_df["expected_orig_id"] = query_df["transformed_id"].map(transform_to_orig)
    
    # Extract file ID from segment ID in top_match_id
    query_df["top_match_file_id"] = query_df["top_match_id"].apply(extract_file_id_from_segment_id)
    
    # Compare file IDs (not segment IDs)
    failures = query_df[query_df["top_match_file_id"] != query_df["expected_orig_id"]].copy()
    
    logger.info(f"Found {len(failures)} failure cases (after fixing ID comparison)")
    
    # Group by transform type
    failures_by_transform = failures.groupby("transform_type")
    
    captured_count = 0
    
    for transform_type, group in failures_by_transform:
        transform_failures = group.head(max_failures_per_transform)
        
        for _, row in tqdm(transform_failures.iterrows(), total=len(transform_failures), desc=f"Capturing {transform_type}"):
            transformed_id = row["transformed_id"]
            original_id = row["expected_orig_id"]
            
            transformed_path = Path(transform_to_path.get(transformed_id, ""))
            original_path = Path(orig_to_path.get(original_id, ""))
            
            # Load full query results
            query_result_path = query_results_dir / f"{transformed_id}_query.json"
            if query_result_path.exists():
                with open(query_result_path, 'r') as f:
                    query_results = json.load(f)
            else:
                query_results = {}
            
            top_matches = query_results.get("aggregated_results", [])[:10]
            
            # Determine failure reason
            # Extract file ID from segment ID for display
            top_match_file_id = extract_file_id_from_segment_id(row["top_match_id"])
            
            if row["top_match_rank"] == -1:
                reason = "No matches found"
            elif row["top_match_similarity"] < 0.5:
                reason = f"Low similarity: {row['top_match_similarity']:.3f}"
            else:
                reason = f"Wrong match: {top_match_file_id} (expected {original_id}, segment: {row['top_match_id']})"
            
            # Capture failure
            capture_failure_case(
                transformed_id=transformed_id,
                transformed_path=transformed_path,
                original_id=original_id,
                original_path=original_path,
                query_results=query_results,
                top_matches=top_matches,
                reason=reason,
                output_dir=output_dir,
                index_metadata=index_metadata,
                include_daw_context=True,
                orig_to_path=orig_to_path  # Pass mapping to save top match audio
            )
            
            captured_count += 1
    
    logger.info(f"Captured {captured_count} failure cases to {output_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture failure cases")
    parser.add_argument("--query-summary", type=Path, required=True)
    parser.add_argument("--transform-manifest", type=Path, required=True)
    parser.add_argument("--files-manifest", type=Path, required=True)
    parser.add_argument("--query-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-per-transform", type=int, default=10)
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    capture_failures(
        args.query_summary,
        args.transform_manifest,
        args.files_manifest,
        args.query_results,
        args.output,
        max_failures_per_transform=args.max_per_transform
    )
