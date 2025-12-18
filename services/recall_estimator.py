"""Service for estimating recall metrics."""
import logging
from typing import List, Optional

from core.models import SegmentResult

logger = logging.getLogger(__name__)


class RecallEstimator:
    """Service for estimating recall from segment results."""
    
    @staticmethod
    def estimate_recall_at_k(
        segment_results: List[SegmentResult],
        expected_orig_id: Optional[str],
        k: int = 5
    ) -> float:
        """
        Estimate Recall@K from segment results.
        
        Recall@K = fraction of segments where original is in top-K results.
        
        Args:
            segment_results: List of segment query results
            expected_orig_id: Expected original file ID
            k: K value for recall calculation
            
        Returns:
            Estimated Recall@K (0.0 to 1.0)
        """
        if not segment_results or not expected_orig_id:
            return 0.0
        
        segments_with_orig_in_topk = 0
        
        for seg_result in segment_results:
            if not seg_result.results:
                continue
            
            # Check if original is in top-K for THIS segment
            found_in_topk = False
            for result in seg_result.results[:k]:  # Check only top-K
                candidate_id = result.get("id", f"index_{result.get('index', '')}")
                if expected_orig_id in str(candidate_id):
                    found_in_topk = True
                    break
            
            if found_in_topk:
                segments_with_orig_in_topk += 1
        
        return segments_with_orig_in_topk / len(segment_results) if segment_results else 0.0
    
    @staticmethod
    def should_activate_multi_scale(
        estimated_recall_5: float,
        severity: str,
        requirement_recall_5: float
    ) -> bool:
        """
        Determine if multi-scale processing should be activated.
        
        Uses conservative threshold to ensure requirements are met.
        
        Args:
            estimated_recall_5: Estimated Recall@5 from first scale
            severity: Transform severity ("mild", "moderate", "severe")
            requirement_recall_5: Required Recall@5 for this severity
            
        Returns:
            True if multi-scale should be activated
        """
        # Conservative thresholds: require higher estimated recall to skip multi-scale
        if severity == "severe":
            # Need Recall@5 ≥ 0.70, so threshold = 0.75 (not 0.65)
            return estimated_recall_5 < 0.75
        elif severity == "moderate":
            # Need Recall@5 ≥ 0.85, so threshold = 0.88 (not 0.80)
            return estimated_recall_5 < 0.88
        else:
            # Mild: usually single scale is sufficient
            return estimated_recall_5 < requirement_recall_5 * 0.95
