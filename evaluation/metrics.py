"""Evaluation metrics computation."""
import logging
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
    
    # For each K, check if correct match is in top-K
    for k in k_values:
        # For now, we only have top_match_id. In full implementation, we'd check top-K
        # This is simplified - full version would load full query results
        if k == 1:
            # Check if top match is correct
            correct = query_results["top_match_id"] == query_results["expected_orig_id"]
            recall = correct.sum() / len(query_results) if len(query_results) > 0 else 0.0
        else:
            # For K > 1, we'd need to load full query results from JSON
            # For now, approximate using similarity threshold
            # This is a limitation - full implementation would load full results
            logger.warning(f"Recall@{k} calculation simplified - loading full results recommended")
            recall = 0.0
        
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
    
    # Get ranks where correct match was found
    correct_mask = query_results["top_match_id"] == query_results["expected_orig_id"]
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
    
    # Get similarities for correct matches
    correct_mask = query_results["top_match_id"] == query_results["expected_orig_id"]
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
