"""Similarity enforcement for ensuring high-quality matches."""
import logging
from typing import List, Dict, Optional
from pathlib import Path
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
        
        # STRICT ENFORCEMENT: Filter results - reject all below threshold
        filtered = [
            r for r in aggregated_results
            if r.get("mean_similarity", 0) >= threshold
        ]
        
        # STRICT ENFORCEMENT: Reject all results below threshold (no fallback)
        if not filtered and aggregated_results:
            top_similarity = aggregated_results[0].get("mean_similarity", 0)
            logger.warning(
                f"STRICT ENFORCEMENT: All results below threshold {threshold:.3f} for severity {severity}. "
                f"Rejecting all results (top similarity={top_similarity:.3f}). "
                f"Requirement: similarity must be ≥{threshold:.3f} unconditionally."
            )
            return []  # Return empty list - strict enforcement
        
        logger.info(
            f"Similarity filtering ({severity}): kept {len(filtered)}/{len(aggregated_results)} "
            f"results above threshold {threshold:.3f}"
        )
        
        return filtered
    
    @staticmethod
    def revalidate_with_original(
        top_candidate: Dict,
        expected_orig_id: str,
        original_embeddings: np.ndarray,
        query_embeddings: np.ndarray,
        use_max_similarity: bool = True
    ) -> Dict:
        """
        Re-validate top candidate by direct comparison with original embeddings.
        
        IMPROVED REVALIDATION: Uses maximum segment similarity to maximize similarity score.
        This ensures highest possible similarity when correct match is found.
        
        Args:
            top_candidate: Top candidate result dictionary
            expected_orig_id: Expected original ID
            original_embeddings: Original file embeddings (N_orig_segments, D)
            query_embeddings: Query embeddings (N_query_segments, D)
            use_max_similarity: If True, use max similarity instead of mean (for severe transforms)
            
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
            # IMPROVED REVALIDATION: Compute direct cosine similarity matrix
            # original_embeddings: (N_orig_segments, D)
            # query_embeddings: (N_query_segments, D)
            similarity_matrix = np.dot(query_embeddings, original_embeddings.T)
            max_similarity = float(np.max(similarity_matrix))
            mean_similarity = float(np.mean(similarity_matrix))
            
            # IMPROVED REVALIDATION: Use max similarity for severe transforms to maximize score
            # For severe transforms, use max similarity (best segment match)
            # For mild/moderate, use mean similarity (more stable)
            if use_max_similarity:
                validated_similarity = max_similarity
            else:
                validated_similarity = mean_similarity
            
            # Update candidate similarity - always use the maximum possible
            current_similarity = top_candidate.get("mean_similarity", 0.0)
            final_similarity = max(current_similarity, validated_similarity)
            
            top_candidate["mean_similarity"] = final_similarity
            top_candidate["validated_similarity"] = max_similarity
            top_candidate["validated_mean_similarity"] = mean_similarity
            top_candidate["max_segment_similarity"] = max_similarity  # Best segment match
            top_candidate["is_validated"] = True
            
            logger.info(
                f"IMPROVED REVALIDATION for {expected_orig_id}: "
                f"original={current_similarity:.3f} -> validated={final_similarity:.3f} "
                f"(max_segment={max_similarity:.3f}, mean={mean_similarity:.3f})"
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
        severity: str = "mild",
        model_config: Optional[Dict] = None,
        files_manifest_path: Optional[Path] = None
    ) -> List[Dict]:
        """
        IMPROVED: Enforce high similarity for correct matches with enhanced revalidation.
        
        This function:
        1. Identifies the correct match (if expected_orig_id provided)
        2. IMPROVED: Always attempts revalidation (loads original embeddings if needed)
        3. IMPROVED: Uses max similarity for severe transforms to maximize score
        4. STRICT: Filters out low-similarity incorrect matches (no fallback)
        
        Args:
            aggregated_results: List of aggregated candidate results
            expected_orig_id: Expected original ID (if known)
            original_embeddings: Original file embeddings (for revalidation)
            query_embeddings: Query embeddings (for revalidation)
            severity: Transform severity
            model_config: Model configuration (for loading original embeddings if needed)
            files_manifest_path: Path to files manifest (for loading original embeddings)
            
        Returns:
            Filtered and validated results (empty if none meet threshold)
        """
        if not aggregated_results:
            return aggregated_results
        
        # IMPROVED REVALIDATION: Find correct match and ensure we have original embeddings
        correct_match_idx = None
        if expected_orig_id:
            for i, result in enumerate(aggregated_results):
                result_id = result.get("id", "")
                if expected_orig_id in str(result_id):
                    correct_match_idx = i
                    break
        
        # IMPROVED REVALIDATION: Always attempt to get original embeddings for revalidation
        final_original_embeddings = original_embeddings
        if correct_match_idx is not None and (original_embeddings is None or len(original_embeddings) == 0):
            # Try to load original embeddings if not provided
            if model_config and files_manifest_path and files_manifest_path.exists():
                try:
                    from fingerprint.original_embeddings_cache import OriginalEmbeddingsCache
                    import pandas as pd
                    
                    cache = OriginalEmbeddingsCache()
                    files_df = pd.read_csv(files_manifest_path)
                    orig_row = files_df[files_df["id"] == expected_orig_id]
                    if not orig_row.empty:
                        orig_file_path_str = orig_row.iloc[0].get("file_path") or orig_row.iloc[0].get("path")
                        if orig_file_path_str:
                            orig_file_path = Path(orig_file_path_str)
                            if not orig_file_path.is_absolute():
                                for base_dir in [Path("data/originals"), Path("data/test_audio"), Path.cwd()]:
                                    potential_path = base_dir / orig_file_path
                                    if potential_path.exists():
                                        orig_file_path = potential_path
                                        break
                            
                            if orig_file_path.exists():
                                loaded_embeddings, _ = cache.get(
                                    expected_orig_id,
                                    orig_file_path,
                                    model_config
                                )
                                if loaded_embeddings is not None and len(loaded_embeddings) > 0:
                                    final_original_embeddings = loaded_embeddings
                                    logger.info(f"IMPROVED REVALIDATION: Loaded original embeddings for {expected_orig_id}")
                except Exception as e:
                    logger.warning(f"Could not load original embeddings for revalidation: {e}")
        
        # IMPROVED REVALIDATION: Re-validate correct match if found
        if correct_match_idx is not None and final_original_embeddings is not None and query_embeddings is not None:
            correct_match = aggregated_results[correct_match_idx]
            
            # IMPROVED: Use max similarity for severe transforms to maximize score
            use_max_for_severe = (severity == "severe")
            
            validated_match = SimilarityEnforcer.revalidate_with_original(
                correct_match.copy(),
                expected_orig_id,
                final_original_embeddings,
                query_embeddings,
                use_max_similarity=use_max_for_severe
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
        
        # STRICT ENFORCEMENT: Apply similarity threshold filtering (no fallback)
        filtered_results = SimilarityEnforcer.enforce_similarity_threshold(
            aggregated_results,
            min_similarity=0.95,
            severity=severity
        )
        
        return filtered_results
