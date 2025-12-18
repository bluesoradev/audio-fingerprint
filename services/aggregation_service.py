"""Service for aggregating segment results."""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from core.models import SegmentResult, QueryConfig

logger = logging.getLogger(__name__)


class AggregationService:
    """Service for aggregating segment-level query results."""
    
    @staticmethod
    def aggregate_segment_results(
        segment_results: List[SegmentResult],
        query_config: QueryConfig,
        expected_orig_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Aggregate results from multiple segments into final candidates.
        
        Args:
            segment_results: List of segment query results
            query_config: Query configuration
            expected_orig_id: Optional expected original ID for filtering
            
        Returns:
            Aggregated candidate list sorted by score
        """
        if not segment_results:
            return []
        
        # Collect all candidates with their scores
        candidate_scores = {}
        
        for seg_result in segment_results:
            if not seg_result.results:
                continue
            
            scale_weight = seg_result.scale_weight
            
            # Filter by similarity threshold
            filtered_results = [
                r for r in seg_result.results
                if r.get("similarity", 0) >= query_config.min_similarity_threshold
            ]
            
            if not filtered_results:
                # If all filtered out, use top result anyway
                filtered_results = seg_result.results[:1] if seg_result.results else []
            
            # Weight results by scale weight and rank
            for rank, result in enumerate(filtered_results, start=1):
                candidate_id = result.get("id", f"index_{result.get('index', '')}")
                similarity = result.get("similarity", 0.0)
                
                # Calculate weighted score
                # Higher rank = higher score, higher similarity = higher score
                rank_score = 1.0 / rank  # Inverse rank
                weighted_score = similarity * scale_weight * rank_score
                
                if candidate_id not in candidate_scores:
                    candidate_scores[candidate_id] = {
                        "id": candidate_id,
                        "index": result.get("index"),
                        "total_score": 0.0,
                        "max_similarity": 0.0,
                        "min_rank": float('inf'),
                        "segment_count": 0,
                        "rank_5_count": 0,
                        "rank_10_count": 0,
                    }
                
                candidate_scores[candidate_id]["total_score"] += weighted_score
                candidate_scores[candidate_id]["max_similarity"] = max(
                    candidate_scores[candidate_id]["max_similarity"],
                    similarity
                )
                candidate_scores[candidate_id]["min_rank"] = min(
                    candidate_scores[candidate_id]["min_rank"],
                    rank
                )
                candidate_scores[candidate_id]["segment_count"] += 1
                
                if rank <= 5:
                    candidate_scores[candidate_id]["rank_5_count"] += 1
                if rank <= 10:
                    candidate_scores[candidate_id]["rank_10_count"] += 1
        
        # Apply temporal consistency if enabled
        if query_config.use_temporal_consistency:
            candidate_scores = AggregationService._apply_temporal_consistency(
                candidate_scores,
                segment_results,
                query_config.temporal_consistency_weight
            )
        
        # Convert to list and sort by total score
        candidates = list(candidate_scores.values())
        candidates.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Format as query results
        formatted_results = []
        for rank, candidate in enumerate(candidates, start=1):
            formatted_results.append({
                "id": candidate["id"],
                "index": candidate["index"],
                "rank": rank,
                "similarity": candidate["max_similarity"],
                "score": candidate["total_score"],
                "segment_count": candidate["segment_count"],
                "min_rank": candidate["min_rank"],
                "rank_5_count": candidate["rank_5_count"],
                "rank_10_count": candidate["rank_10_count"],
            })
        
        return formatted_results
    
    @staticmethod
    def _apply_temporal_consistency(
        candidate_scores: Dict[str, Dict[str, Any]],
        segment_results: List[SegmentResult],
        consistency_weight: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply temporal consistency boost to candidates.
        
        Boosts candidates that appear consistently across consecutive segments.
        """
        # Group segments by position
        sorted_segments = sorted(segment_results, key=lambda s: s.start)
        
        # Find consecutive matches
        for i in range(len(sorted_segments) - 1):
            seg1_results = sorted_segments[i].results[:10] if sorted_segments[i].results else []
            seg2_results = sorted_segments[i + 1].results[:10] if sorted_segments[i + 1].results else []
            
            # Find common candidates in top-10
            seg1_ids = {r.get("id") for r in seg1_results}
            seg2_ids = {r.get("id") for r in seg2_results}
            common_ids = seg1_ids & seg2_ids
            
            # Boost common candidates
            for candidate_id in common_ids:
                if candidate_id in candidate_scores:
                    boost = consistency_weight * candidate_scores[candidate_id]["total_score"]
                    candidate_scores[candidate_id]["total_score"] += boost
        
        return candidate_scores
