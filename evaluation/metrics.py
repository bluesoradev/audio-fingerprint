"""Evaluation metrics computation."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def extract_file_id_from_segment_id(segment_id: str) -> str:
    """
    Extract base file ID from segment ID.
    
    Examples:
        track1_seg_0000 -> track1
        track2_seg_0042 -> track2
        track1 -> track1 (if already a file ID)
    """
    if pd.isna(segment_id) or not segment_id:
        return ""
    
    segment_id_str = str(segment_id)
    # Check if it's a segment ID (contains _seg_)
    if "_seg_" in segment_id_str:
        # Split on _seg_ and take the first part
        return segment_id_str.split("_seg_")[0]
    else:
        # Already a file ID, return as-is
        return segment_id_str


def compute_recall_at_k(
    query_results: pd.DataFrame,
    ground_truth_map: Dict[str, str],
    k_values: List[int] = [1, 5, 10]
) -> Dict[str, float]:
    """
    Compute recall@K metrics.
    
    Args:
        query_results: DataFrame with query results (must have 'transformed_id', 'top_match_id', etc.)
        ground_truth_map: Dictionary mapping transformed_id -> orig_id
        k_values: List of K values to compute recall for
        
    Returns:
        Dictionary with recall@K for each K
    """
    recalls = {}
    
    # Map transformed_id to expected orig_id
    query_results = query_results.copy()
    query_results["expected_orig_id"] = query_results["transformed_id"].map(ground_truth_map)
    
    # Extract base file ID from segment IDs in top_match_id
    # Index stores segment IDs like "track1_seg_0000", but we need to compare to file ID "track1"
    query_results["top_match_file_id"] = query_results["top_match_id"].apply(extract_file_id_from_segment_id)
    
    # For each K, check if correct match is in top-K
    for k in k_values:
        if k == 1:
            # Check if top match is correct (compare file IDs, not segment IDs)
            correct = query_results["top_match_file_id"] == query_results["expected_orig_id"]
            recall = correct.sum() / len(query_results) if len(query_results) > 0 else 0.0
        else:
            # For K > 1, load full query results from JSON files
            correct_count = 0
            for _, row in query_results.iterrows():
                expected_id = row["expected_orig_id"]
                result_path = Path(row.get("result_path", ""))
                
                if result_path.exists():
                    try:
                        with open(result_path, 'r') as f:
                            result_data = json.load(f)
                        
                        # Get top-K aggregated results
                        aggregated_results = result_data.get("aggregated_results", [])[:k]
                        
                        # Check if expected ID is in top-K
                        found = False
                        for result in aggregated_results:
                            match_id = result.get("id", "")
                            match_file_id = extract_file_id_from_segment_id(match_id)
                            if match_file_id == expected_id:
                                found = True
                                break
                        
                        if found:
                            correct_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to load query results from {result_path}: {e}")
                        # Fallback: use top_match_id if available
                        if row["top_match_file_id"] == expected_id:
                            correct_count += 1
                else:
                    # Fallback: use top_match_id if JSON not available
                    if row["top_match_file_id"] == expected_id:
                        correct_count += 1
            
            recall = correct_count / len(query_results) if len(query_results) > 0 else 0.0
        
        recalls[f"recall_at_{k}"] = recall
    
    return recalls


def compute_rank_distribution(
    query_results: pd.DataFrame,
    ground_truth_map: Dict[str, str]
) -> Dict[str, float]:
    """
    Compute rank distribution statistics.
    
    Returns:
        Dictionary with rank statistics
    """
    query_results = query_results.copy()
    query_results["expected_orig_id"] = query_results["transformed_id"].map(ground_truth_map)
    
    # Extract base file ID from segment IDs in top_match_id
    query_results["top_match_file_id"] = query_results["top_match_id"].apply(extract_file_id_from_segment_id)
    
    # Get ranks where correct match was found (compare file IDs, not segment IDs)
    correct_mask = query_results["top_match_file_id"] == query_results["expected_orig_id"]
    ranks = query_results.loc[correct_mask, "top_match_rank"]
    
    stats = {
        "mean_rank": ranks.mean() if len(ranks) > 0 else float("inf"),
        "median_rank": ranks.median() if len(ranks) > 0 else float("inf"),
        "std_rank": ranks.std() if len(ranks) > 0 else float("inf"),
        "min_rank": ranks.min() if len(ranks) > 0 else float("inf"),
        "max_rank": ranks.max() if len(ranks) > 0 else float("inf"),
        "p95_rank": ranks.quantile(0.95) if len(ranks) > 0 else float("inf"),
        "num_correct": len(ranks),
        "num_total": len(query_results),
        "correct_rate": len(ranks) / len(query_results) if len(query_results) > 0 else 0.0,
    }
    
    return stats


def compute_similarity_stats(
    query_results: pd.DataFrame,
    ground_truth_map: Dict[str, str]
) -> Dict[str, float]:
    """Compute similarity score statistics."""
    query_results = query_results.copy()
    query_results["expected_orig_id"] = query_results["transformed_id"].map(ground_truth_map)
    
    # Extract base file ID from segment IDs in top_match_id
    query_results["top_match_file_id"] = query_results["top_match_id"].apply(extract_file_id_from_segment_id)
    
    # Get similarities for correct matches (compare file IDs, not segment IDs)
    correct_mask = query_results["top_match_file_id"] == query_results["expected_orig_id"]
    similarities = query_results.loc[correct_mask, "top_match_similarity"]
    
    # Get all similarities
    all_similarities = query_results["top_match_similarity"]
    
    stats = {
        "mean_similarity_correct": similarities.mean() if len(similarities) > 0 else 0.0,
        "median_similarity_correct": similarities.median() if len(similarities) > 0 else 0.0,
        "std_similarity_correct": similarities.std() if len(similarities) > 0 else 0.0,
        "min_similarity_correct": similarities.min() if len(similarities) > 0 else 0.0,
        "max_similarity_correct": similarities.max() if len(similarities) > 0 else 0.0,
        "mean_similarity_all": all_similarities.mean() if len(all_similarities) > 0 else 0.0,
    }
    
    return stats


def compute_latency_stats(query_results: pd.DataFrame) -> Dict[str, float]:
    """Compute latency statistics."""
    latencies = query_results["latency_ms"]
    
    return {
        "mean_latency_ms": latencies.mean(),
        "median_latency_ms": latencies.median(),
        "std_latency_ms": latencies.std(),
        "min_latency_ms": latencies.min(),
        "max_latency_ms": latencies.max(),
        "p95_latency_ms": latencies.quantile(0.95),
    }
