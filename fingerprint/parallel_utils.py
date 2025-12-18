"""Parallel processing utilities for query optimization."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


def _query_single_segment(args: Tuple) -> Dict:
    """
    Query single segment - thread-safe wrapper for parallel processing.
    
    Args:
        args: Tuple of (seg, emb, index, topk, index_metadata)
        
    Returns:
        Dictionary with segment query results
    """
    seg, emb, index, topk, index_metadata = args
    
    from .query_index import query_index
    
    results = query_index(
        index,
        emb,
        topk=topk,
        ids=index_metadata.get("ids") if index_metadata else None,
        normalize=True,
        index_metadata=index_metadata
    )
    
    return {
        "segment_id": seg["segment_id"],
        "start": seg["start"],
        "end": seg["end"],
        "segment_idx": seg.get("segment_idx", 0),
        "scale_length": seg.get("scale_length", 3.5),
        "scale_weight": seg.get("scale_weight", 1.0),
        "results": results
    }


def query_segments_parallel(
    segments: List[Dict],
    embeddings: np.ndarray,
    index: Any,
    topk: int,
    index_metadata: Optional[Dict] = None,
    max_workers: Optional[int] = None
) -> List[Dict]:
    """
    Query multiple segments in parallel for improved performance.
    
    Args:
        segments: List of segment dictionaries
        embeddings: Array of embeddings (N_segments, D)
        index: FAISS index
        topk: Number of top results per segment
        index_metadata: Index metadata dictionary
        max_workers: Maximum number of worker threads (default: min(8, len(segments)))
        
    Returns:
        List of segment result dictionaries, in same order as input
    """
    if len(segments) == 0:
        return []
    
    # Determine optimal number of workers
    if max_workers is None:
        max_workers = min(8, len(segments), 4)  # Conservative: max 8 workers
    
    # If only 1 segment, no need for parallel processing
    if len(segments) == 1:
        return [_query_single_segment((segments[0], embeddings[0], index, topk, index_metadata))]
    
    # Prepare arguments for parallel processing
    query_args = [
        (seg, emb, index, topk, index_metadata)
        for seg, emb in zip(segments, embeddings)
    ]
    
    # Execute queries in parallel
    results = [None] * len(segments)
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(_query_single_segment, args): i 
                      for i, args in enumerate(query_args)}
            
            # Collect results as they complete
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.error(f"Error querying segment {idx}: {e}")
                    # Fallback: create empty result
                    results[idx] = {
                        "segment_id": segments[idx].get("segment_id", f"seg_{idx}"),
                        "start": segments[idx].get("start", 0.0),
                        "end": segments[idx].get("end", 0.0),
                        "segment_idx": idx,
                        "scale_length": segments[idx].get("scale_length", 3.5),
                        "scale_weight": segments[idx].get("scale_weight", 1.0),
                        "results": []
                    }
    except Exception as e:
        logger.error(f"Parallel query execution failed: {e}, falling back to sequential")
        # Fallback to sequential processing
        results = []
        for args in query_args:
            results.append(_query_single_segment(args))
    
    return results


def check_early_termination(
    segment_results: List[Dict],
    expected_orig_id: Optional[str] = None,
    min_confidence: float = 0.95,
    min_rank_1_ratio: float = 0.8,
    min_similarity: float = 0.90
) -> Tuple[bool, Optional[Dict]]:
    """
    Check if we can terminate early with high confidence.
    
    Args:
        segment_results: List of segment query results
        expected_orig_id: Expected original ID to match
        min_confidence: Minimum confidence threshold for early termination
        min_rank_1_ratio: Minimum ratio of rank-1 matches
        min_similarity: Minimum similarity threshold
        
    Returns:
        Tuple of (can_terminate: bool, early_result: Optional[Dict])
    """
    if not expected_orig_id or not segment_results:
        return False, None
    
    # Aggregate first scale results quickly
    candidate_scores = {}
    total_segments = len(segment_results)
    
    for seg_result in segment_results:
        if not seg_result.get("results"):
            continue
        
        top_result = seg_result["results"][0] if seg_result["results"] else None
        if not top_result:
            continue
        
        candidate_id = top_result.get("id", "")
        similarity = top_result.get("similarity", 0.0)
        rank = top_result.get("rank", 1)
        
        if not candidate_id:
            continue
        
        if candidate_id not in candidate_scores:
            candidate_scores[candidate_id] = {
                "id": candidate_id,
                "max_similarity": 0.0,
                "min_similarity": float('inf'),
                "rank_1_count": 0,
                "total_segments": 0,
                "similarities": []
            }
        
        candidate_scores[candidate_id]["max_similarity"] = max(
            candidate_scores[candidate_id]["max_similarity"], similarity
        )
        candidate_scores[candidate_id]["min_similarity"] = min(
            candidate_scores[candidate_id]["min_similarity"], similarity
        )
        candidate_scores[candidate_id]["similarities"].append(similarity)
        
        if rank == 1:
            candidate_scores[candidate_id]["rank_1_count"] += 1
        candidate_scores[candidate_id]["total_segments"] += 1
    
    # Check if expected original is top candidate with high confidence
    for candidate_id, scores in candidate_scores.items():
        if expected_orig_id in str(candidate_id):
            rank_1_ratio = scores["rank_1_count"] / scores["total_segments"] if scores["total_segments"] > 0 else 0.0
            max_similarity = scores["max_similarity"]
            mean_similarity = np.mean(scores["similarities"]) if scores["similarities"] else 0.0
            
            # High confidence criteria:
            # 1. Rank-1 in >80% of segments AND similarity >0.90
            # 2. OR similarity >0.95 regardless of rank
            # 3. OR mean similarity >0.92 with rank-1 in >70% of segments
            high_confidence = (
                (rank_1_ratio >= min_rank_1_ratio and max_similarity >= min_similarity) or
                max_similarity >= 0.95 or
                (mean_similarity >= 0.92 and rank_1_ratio >= 0.7)
            )
            
            if high_confidence:
                confidence_score = min(1.0, mean_similarity * rank_1_ratio)
                if confidence_score >= min_confidence:
                    return True, {
                        "id": candidate_id,
                        "similarity": mean_similarity,
                        "max_similarity": max_similarity,
                        "rank_1_ratio": rank_1_ratio,
                        "confidence": confidence_score,
                        "total_segments": scores["total_segments"]
                    }
    
    return False, None


def get_adaptive_topk(
    transform_type: Optional[str] = None,
    severity: str = "mild",
    initial_confidence: Optional[float] = None
) -> int:
    """
    Determine optimal topk based on transform type, severity, and confidence.
    
    Args:
        transform_type: Type of transform applied
        severity: Transform severity (mild, moderate, severe)
        initial_confidence: Initial confidence from early check (if available)
        
    Returns:
        Optimal topk value
    """
    transform_lower = str(transform_type).lower() if transform_type else ""
    
    # Base topk by transform type
    base_topk_map = {
        "low_pass_filter": 50,      # Very challenging
        "song_a_in_song_b": 30,     # Challenging
        "embedded_sample": 30,      # Challenging
        "overlay_vocals": 20,       # Moderate
        "default": 15                # Standard
    }
    
    # Get base topk
    topk = base_topk_map.get(transform_lower, base_topk_map["default"])
    
    # Adjust based on severity
    severity_multiplier = {
        "severe": 1.5,
        "moderate": 1.2,
        "mild": 1.0
    }
    
    topk = int(topk * severity_multiplier.get(severity, 1.0))
    
    # Reduce if high initial confidence (from early check)
    if initial_confidence and initial_confidence > 0.90:
        topk = max(10, int(topk * 0.7))  # Reduce by 30%
        logger.debug(f"Reducing topk from {int(topk / 0.7)} to {topk} due to high confidence {initial_confidence:.3f}")
    
    return topk
