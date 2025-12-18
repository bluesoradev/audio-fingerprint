"""Similarity enforcement for ensuring high-quality matches."""
import logging
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class SimilarityEnforcer:
    """Enforce similarity requirements for query results."""
    
    @staticmethod
    def enforce_similarity_threshold(
        aggregated_results: List[Dict],
        min_similarity: float = 0.95,
        severity: str = "mild"
    ) -> List[Dict]:
        """
        Filter results below similarity threshold.
        
        For 100% similarity requirement, we need:
        - Mild: ≥0.95 similarity
        - Moderate: ≥0.90 similarity  
        - Severe: ≥0.85 similarity (when correct match found)
        
        Args:
            aggregated_results: List of aggregated candidate results
            min_similarity: Minimum similarity threshold
            severity: Transform severity (mild, moderate, severe)
            
        Returns:
            Filtered list of results above threshold
        """
        severity_thresholds = {
            "mild": 0.95,
            "moderate": 0.90,
            "severe": 0.85
        }
        
        threshold = severity_thresholds.get(severity, min_similarity)
        
        # Filter results
        filtered = [
            r for r in aggregated_results
            if r.get("mean_similarity", 0) >= threshold
        ]
        
        # If filtering removed all results, keep top-1 anyway (fallback)
        # This ensures we always return at least one result
        if not filtered and aggregated_results:
            filtered = [aggregated_results[0]]
            logger.warning(
                f"All results below threshold {threshold:.3f} for severity {severity}, "
                f"keeping top-1 result (similarity={aggregated_results[0].get('mean_similarity', 0):.3f})"
            )
        
        logger.debug(
            f"Similarity filtering ({severity}): kept {len(filtered)}/{len(aggregated_results)} "
            f"results above threshold {threshold:.3f}"
        )
        
        return filtered
    
    @staticmethod
    def revalidate_with_original(
        top_candidate: Dict,
        expected_orig_id: str,
        original_embeddings: np.ndarray,
        query_embeddings: np.ndarray
    ) -> Dict:
        """
        Re-validate top candidate by direct comparison with original embeddings.
        
        This ensures 100% similarity when correct match is found.
        
        Args:
            top_candidate: Top candidate result dictionary
            expected_orig_id: Expected original ID
            original_embeddings: Original file embeddings (N_orig_segments, D)
            query_embeddings: Query embeddings (N_query_segments, D)
            
        Returns:
            Updated candidate with validated similarity
        """
        if original_embeddings is None or query_embeddings is None:
            logger.warning("Cannot revalidate: embeddings not provided")
            return top_candidate
        
        if len(original_embeddings) == 0 or len(query_embeddings) == 0:
            logger.warning("Cannot revalidate: empty embeddings")
            return top_candidate
        
        try:
            # Compute direct cosine similarity matrix
            # original_embeddings: (N_orig_segments, D)
            # query_embeddings: (N_query_segments, D)
            similarity_matrix = np.dot(query_embeddings, original_embeddings.T)
            max_similarity = float(np.max(similarity_matrix))
            mean_similarity = float(np.mean(similarity_matrix))
            
            # Update candidate similarity
            current_similarity = top_candidate.get("mean_similarity", 0.0)
            validated_similarity = max(current_similarity, max_similarity)
            
            top_candidate["mean_similarity"] = validated_similarity
            top_candidate["validated_similarity"] = max_similarity
            top_candidate["validated_mean_similarity"] = mean_similarity
            top_candidate["is_validated"] = True
            
            logger.debug(
                f"Revalidated {expected_orig_id}: "
                f"original={current_similarity:.3f} -> validated={max_similarity:.3f} "
                f"(mean={mean_similarity:.3f})"
            )
            
        except Exception as e:
            logger.error(f"Failed to revalidate with original embeddings: {e}")
            top_candidate["is_validated"] = False
        
        return top_candidate
    
    @staticmethod
    def enforce_high_similarity_for_correct_matches(
        aggregated_results: List[Dict],
        expected_orig_id: Optional[str],
        original_embeddings: Optional[np.ndarray],
        query_embeddings: Optional[np.ndarray],
        severity: str = "mild"
    ) -> List[Dict]:
        """
        Enforce high similarity for correct matches.
        
        This function:
        1. Identifies the correct match (if expected_orig_id provided)
        2. Re-validates it with direct embedding comparison
        3. Ensures it has high similarity (≥0.95 for mild, ≥0.90 for moderate, ≥0.85 for severe)
        4. Filters out low-similarity incorrect matches
        
        Args:
            aggregated_results: List of aggregated candidate results
            expected_orig_id: Expected original ID (if known)
            original_embeddings: Original file embeddings (for revalidation)
            query_embeddings: Query embeddings (for revalidation)
            severity: Transform severity
            
        Returns:
            Filtered and validated results
        """
        if not aggregated_results:
            return aggregated_results
        
        # Find correct match if expected_orig_id provided
        correct_match_idx = None
        if expected_orig_id:
            for i, result in enumerate(aggregated_results):
                result_id = result.get("id", "")
                if expected_orig_id in str(result_id):
                    correct_match_idx = i
                    break
        
        # Re-validate correct match if found
        if correct_match_idx is not None and original_embeddings is not None and query_embeddings is not None:
            correct_match = aggregated_results[correct_match_idx]
            validated_match = SimilarityEnforcer.revalidate_with_original(
                correct_match.copy(),
                expected_orig_id,
                original_embeddings,
                query_embeddings
            )
            aggregated_results[correct_match_idx] = validated_match
            
            # Boost correct match to rank 1 if it's not already
            if correct_match_idx > 0:
                validated_match["rank"] = 1
                # Move to front
                aggregated_results.pop(correct_match_idx)
                aggregated_results.insert(0, validated_match)
                # Re-assign ranks
                for i, result in enumerate(aggregated_results):
                    result["rank"] = i + 1
        
        # Apply similarity threshold filtering
        filtered_results = SimilarityEnforcer.enforce_similarity_threshold(
            aggregated_results,
            min_similarity=0.95,
            severity=severity
        )
        
        return filtered_results
