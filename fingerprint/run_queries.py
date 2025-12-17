"""Run queries on transformed audio files."""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import time
import numpy as np
import pandas as pd
from tqdm import tqdm

from .load_model import load_fingerprint_model
from .embed import segment_audio, extract_embeddings, normalize_embeddings
from .query_index import load_index, query_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _extract_file_id_from_segment_id(segment_id: str) -> str:
    """
    Extract base file ID from segment ID.
    
    Examples:
        track1_seg_0000 -> track1
        track2_seg_0042 -> track2
        track1 -> track1 (if already a file ID)
    """
    if not segment_id:
        return ""
    
    segment_id_str = str(segment_id)
    # Check if it's a segment ID (contains _seg_)
    if "_seg_" in segment_id_str:
        # Split on _seg_ and take the first part
        return segment_id_str.split("_seg_")[0]
    else:
        # Already a file ID, return as-is
        return segment_id_str


def _apply_query_augmentation(file_path: Path, variant: str, model_config: Dict) -> Optional[Path]:
    """
    Apply query-time augmentation to audio file.
    
    Args:
        file_path: Original audio file path
        variant: Augmentation variant name (e.g., "speed_0.98", "pitch_+1")
        model_config: Model configuration dict
        
    Returns:
        Path to augmented audio file (temporary), or None if failed
    """
    import tempfile
    import librosa
    import soundfile as sf
    
    try:
        # Parse variant (format: "type_value", e.g., "speed_0.98", "pitch_+1")
        parts = variant.split("_")
        if len(parts) < 2:
            return None
        
        aug_type = parts[0]
        aug_value = parts[1]
        
        # Load audio
        y, sr = librosa.load(str(file_path), sr=model_config["sample_rate"], mono=True)
        
        # Apply augmentation
        if aug_type == "speed":
            speed_ratio = float(aug_value)
            y_aug = librosa.effects.time_stretch(y, rate=speed_ratio)
        elif aug_type == "pitch":
            semitones = int(aug_value)
            y_aug = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
        else:
            logger.warning(f"Unknown augmentation type: {aug_type}")
            return None
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)
        sf.write(str(temp_path), y_aug, sr)
        temp_file.close()
        
        return temp_path
        
    except Exception as e:
        logger.warning(f"Query augmentation failed for {variant}: {e}")
        return None


def _second_stage_rerank(
    top_candidates: List[Dict],
    segment_results: List[Dict],
    index: any,
    index_metadata: Dict,
    model_config: Dict,
    topk: int
) -> List[Dict]:
    """
    Second-stage re-ranking: re-query top candidates with more detailed analysis.
    
    This performs a more thorough analysis of top candidates by:
    1. Checking segment-level consistency
    2. Analyzing match distribution
    3. Computing cross-segment similarity patterns
    
    Args:
        top_candidates: Top-K candidates from first stage
        segment_results: All segment query results
        index: FAISS index
        index_metadata: Index metadata
        model_config: Model configuration
        topk: Top-K for queries
        
    Returns:
        Re-ranked candidate list
    """
    reranked = []
    
    for candidate in top_candidates:
        candidate_id = candidate["id"]
        
        # Analyze segment-level matches for this candidate
        segment_matches = []
        for seg_result in segment_results:
            for result in seg_result["results"]:
                if result.get("id") == candidate_id:
                    segment_matches.append({
                        "similarity": result["similarity"],
                        "rank": result["rank"],
                        "segment_idx": seg_result.get("segment_idx", 0),
                        "scale_length": seg_result.get("scale_length", 1.0)
                    })
                    break
        
        if not segment_matches:
            continue
        
        # Compute detailed metrics
        similarities = np.array([m["similarity"] for m in segment_matches])
        ranks = np.array([m["rank"] for m in segment_matches])
        
        # Enhanced scoring factors:
        # 1. Consistency: how consistent are the similarities?
        similarity_std = np.std(similarities) if len(similarities) > 1 else 0.0
        consistency_score = 1.0 / (1.0 + similarity_std)  # Lower std = higher consistency
        
        # 2. Rank distribution: how many rank-1 matches?
        rank_1_ratio = np.sum(ranks == 1) / len(ranks) if len(ranks) > 0 else 0.0
        
        # 3. Average similarity
        avg_similarity = np.mean(similarities)
        
        # 4. Match coverage: how many segments matched?
        coverage = len(segment_matches) / len(segment_results) if len(segment_results) > 0 else 0.0
        
        # 5. Cross-scale consistency (if multi-scale)
        scale_lengths = [m["scale_length"] for m in segment_matches]
        if len(set(scale_lengths)) > 1:
            # Multi-scale: check consistency across scales
            scale_consistency = 1.0 - (np.std([m["similarity"] for m in segment_matches]) / np.mean(similarities)) if np.mean(similarities) > 0 else 0.0
        else:
            scale_consistency = 1.0
        
        # Combined re-ranking score (weighted)
        rerank_score = (
            0.35 * avg_similarity +           # Average similarity
            0.25 * consistency_score +        # Consistency
            0.20 * rank_1_ratio +            # Rank-1 ratio
            0.10 * coverage +                # Coverage
            0.10 * scale_consistency         # Cross-scale consistency
        )
        
        # Update candidate with re-ranking score
        reranked_candidate = candidate.copy()
        reranked_candidate["rerank_score"] = float(rerank_score)
        reranked_candidate["consistency_score"] = float(consistency_score)
        reranked_candidate["scale_consistency"] = float(scale_consistency)
        reranked.append(reranked_candidate)
    
    # Sort by re-ranking score
    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    return reranked


def _compute_result_quality(item: Dict, total_segments: int) -> float:
    """
    Compute quality score for a result candidate.
    
    Quality factors:
    - Rank-1 ratio (higher is better)
    - Match ratio (coverage)
    - Temporal consistency
    - Score gap from next candidate
    
    Returns:
        Quality score (0-1)
    """
    rank_1_ratio = item.get("rank_1_count", 0) / total_segments if total_segments > 0 else 0.0
    match_ratio = item.get("match_count", 0) / total_segments if total_segments > 0 else 0.0
    temporal_score = item.get("temporal_score", 0.0)
    combined_score = item.get("combined_score", 0.0)
    
    # Quality score: weighted combination
    quality = (
        0.30 * rank_1_ratio +        # Rank-1 matches are strongest signal
        0.25 * match_ratio +         # Coverage
        0.25 * temporal_score +      # Temporal consistency
        0.20 * min(combined_score, 1.0)  # Combined score (capped at 1.0)
    )
    
    return quality


def _ensemble_augmented_results(all_results: List[Dict], topk: int) -> List[Dict]:
    """
    Ensemble results from multiple query-time augmentation variants.
    
    Args:
        all_results: List of result dicts, each with "variant", "results", "num_segments"
        topk: Number of top results to return
        
    Returns:
        Ensembled aggregated results
    """
    # Collect all candidates from all variants
    candidate_scores = {}  # candidate_id -> list of (score, variant_weight)
    
    # Weight variants (original gets highest weight)
    variant_weights = {}
    for result in all_results:
        variant = result["variant"]
        if variant == "original":
            variant_weights[variant] = 1.0
        else:
            variant_weights[variant] = 0.7  # Augmented variants get 70% weight
    
    # Aggregate scores across variants
    for result in all_results:
        variant = result["variant"]
        weight = variant_weights.get(variant, 0.5)
        
        for item in result["results"]:
            candidate_id = item["id"]
            if candidate_id not in candidate_scores:
                candidate_scores[candidate_id] = {
                    "id": candidate_id,
                    "scores": [],
                    "confidences": [],
                    "rank_1_counts": [],
                    "temporal_scores": [],
                    "variants": []
                }
            
            # Weight the scores by variant importance
            weighted_score = item["combined_score"] * weight
            candidate_scores[candidate_id]["scores"].append(weighted_score)
            candidate_scores[candidate_id]["confidences"].append(item.get("confidence", 0.0) * weight)
            candidate_scores[candidate_id]["rank_1_counts"].append(item.get("rank_1_count", 0))
            candidate_scores[candidate_id]["temporal_scores"].append(item.get("temporal_score", 0.0))
            candidate_scores[candidate_id]["variants"].append(variant)
    
    # Compute ensemble scores
    ensemble_results = []
    for candidate_id, data in candidate_scores.items():
        # Mean of weighted scores
        ensemble_score = np.mean(data["scores"]) if data["scores"] else 0.0
        ensemble_confidence = np.mean(data["confidences"]) if data["confidences"] else 0.0
        
        # Aggregate other metrics
        total_rank_1 = sum(data["rank_1_counts"])
        avg_temporal = np.mean(data["temporal_scores"]) if data["temporal_scores"] else 0.0
        
        ensemble_results.append({
            "id": candidate_id,
            "combined_score": float(ensemble_score),
            "confidence": float(ensemble_confidence),
            "rank_1_count": total_rank_1,
            "temporal_score": float(avg_temporal),
            "variant_count": len(data["variants"]),
            "variants": list(set(data["variants"]))
        })
    
    # Sort by ensemble score
    ensemble_results.sort(key=lambda x: x["combined_score"], reverse=True)
    for i, item in enumerate(ensemble_results):
        item["rank"] = i + 1
    
    return ensemble_results[:topk]


def run_query_on_file(
    file_path: Path,
    index: any,
    model_config: Dict,
    topk: int = 10,
    index_metadata: Dict = None,
    transform_type: str = None,
    expected_orig_id: str = None
) -> Dict:
    """
    Run fingerprint query on a single file.
    
    Returns:
        Dictionary with query results and metadata
    """
    start_time = time.time()
    
    try:
        # Check for multi-scale fusion
        multi_scale_config = model_config.get("multi_scale", {})
        use_multi_scale = multi_scale_config.get("enabled", False)
        multi_scale_lengths = multi_scale_config.get("segment_lengths", [])
        multi_scale_weights = multi_scale_config.get("weights", [])
        
        # Get overlap ratio
        overlap_ratio = model_config.get("overlap_ratio", None)
        if overlap_ratio is None:
            seg_config = model_config.get("segmentation", {})
            overlap_ratio = seg_config.get("overlap_ratio", None)
        
        # Determine segment lengths to use
        if use_multi_scale and multi_scale_lengths:
            # Normalize weights
            if len(multi_scale_weights) != len(multi_scale_lengths):
                multi_scale_weights = [1.0 / len(multi_scale_lengths)] * len(multi_scale_lengths)
            total_weight = sum(multi_scale_weights)
            if total_weight > 0:
                multi_scale_weights = [w / total_weight for w in multi_scale_weights]
            segment_lengths_to_use = multi_scale_lengths
            scale_weights_to_use = multi_scale_weights
        else:
            # Single scale
            segment_lengths_to_use = [model_config["segment_length"]]
            scale_weights_to_use = [1.0]
        
        # Process each scale
        all_scale_segment_results = []
        stored_embeddings = None  # Store embeddings from first scale for enhanced detection
        for scale_idx, (seg_len, scale_weight) in enumerate(zip(segment_lengths_to_use, scale_weights_to_use)):
            # Segment audio with current scale
            segments = segment_audio(
                file_path,
                segment_length=seg_len,
                sample_rate=model_config["sample_rate"],
                overlap_ratio=overlap_ratio
            )
            
            # Extract embeddings
            embeddings = extract_embeddings(
                segments,
                model_config,
                save_embeddings=False
            )
            
            # Normalize embeddings
            embeddings = normalize_embeddings(embeddings, method="l2")
            
            # Store embeddings from first scale for enhanced detection
            if scale_idx == 0:
                stored_embeddings = embeddings
            
            # Query index for each segment
            scale_segment_results = []
            for seg, emb in zip(segments, embeddings):
                results = query_index(
                    index,
                    emb,
                    topk=topk,
                    ids=index_metadata.get("ids") if index_metadata else None,
                    normalize=True,
                    index_metadata=index_metadata
                )
                
                scale_segment_results.append({
                    "segment_id": seg["segment_id"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "segment_idx": len(scale_segment_results),
                    "scale_length": seg_len,
                    "scale_weight": scale_weight,
                    "results": results
                })
            
            all_scale_segment_results.extend(scale_segment_results)
        
        # Combine results from all scales
        segment_results = all_scale_segment_results
        
        # Get aggregation parameters from config (with defaults)
        agg_config = model_config.get("aggregation", {})
        min_similarity_threshold = agg_config.get("min_similarity_threshold", 0.2)  # Filter low-quality matches
        top_k_fusion_ratio = agg_config.get("top_k_fusion_ratio", 0.6)  # Use top 60% of segments
        temporal_consistency_weight = agg_config.get("temporal_consistency_weight", 0.15)  # Weight for consecutive matches
        use_temporal_consistency = agg_config.get("use_temporal_consistency", True)
        use_adaptive_threshold = agg_config.get("use_adaptive_threshold", False)
        
        # Adaptive threshold: adjust based on query quality
        if use_adaptive_threshold and len(segment_results) > 0:
            # Calculate average top similarity across all segments
            top_similarities = []
            for seg_result in segment_results:
                if seg_result["results"]:
                    top_similarities.append(seg_result["results"][0].get("similarity", 0))
            
            if top_similarities:
                avg_top_similarity = np.mean(top_similarities)
                adaptive_base = agg_config.get("adaptive_threshold_base", 0.2)
                adaptive_sensitivity = agg_config.get("adaptive_threshold_sensitivity", 0.1)
                
                # Adjust threshold: if average similarity is high, lower threshold; if low, raise it
                similarity_adjustment = (avg_top_similarity - 0.5) * adaptive_sensitivity
                adaptive_threshold = max(0.1, min(0.4, adaptive_base - similarity_adjustment))
                min_similarity_threshold = adaptive_threshold
                logger.debug(f"Adaptive threshold: avg_sim={avg_top_similarity:.3f}, threshold={min_similarity_threshold:.3f}")
        
        # Filter segments by similarity threshold (exclude low-quality matches)
        filtered_segment_results = []
        for seg_result in segment_results:
            top_result = seg_result["results"][0] if seg_result["results"] else None
            if top_result and top_result.get("similarity", 0) >= min_similarity_threshold:
                filtered_segment_results.append(seg_result)
        
        # If filtering removed too many segments, use original (at least 30% needed)
        if len(filtered_segment_results) < len(segment_results) * 0.3:
            logger.debug(f"Similarity filtering too aggressive ({len(filtered_segment_results)}/{len(segment_results)}), using all segments")
            filtered_segment_results = segment_results
        
        # Top-K fusion: use only best-matching segments
        if top_k_fusion_ratio < 1.0 and len(filtered_segment_results) > 5:
            # Sort segments by their top match similarity
            filtered_segment_results.sort(
                key=lambda x: x["results"][0].get("similarity", 0) if x["results"] else 0,
                reverse=True
            )
            # Keep top K% of segments
            keep_count = max(5, int(len(filtered_segment_results) * top_k_fusion_ratio))
            filtered_segment_results = filtered_segment_results[:keep_count]
            logger.debug(f"Top-K fusion: using top {keep_count}/{len(segment_results)} segments")
        
        # Aggregate segment results using weighted voting fusion with temporal consistency
        # This method combines multiple signals for better robustness:
        # 1. Weighted similarity (higher similarity segments weighted more)
        # 2. Rank-1 voting (segments that match at rank 1 are strongest signal)
        # 3. Rank-5 voting (segments matching in top-5)
        # 4. Temporal consistency (consecutive segments matching same file)
        all_candidates = {}
        total_segments = len(filtered_segment_results)
        
        # Track temporal consistency: consecutive segments matching same file
        temporal_matches = {}  # candidate_id -> list of consecutive match lengths
        prev_top_match_id = None
        consecutive_count = 0
        
        for seg_result in filtered_segment_results:
            top_result = seg_result["results"][0] if seg_result["results"] else None
            if top_result:
                top_match_id = top_result.get("id", "")
                if top_match_id == prev_top_match_id:
                    consecutive_count += 1
                else:
                    if prev_top_match_id and consecutive_count > 0:
                        if prev_top_match_id not in temporal_matches:
                            temporal_matches[prev_top_match_id] = []
                        temporal_matches[prev_top_match_id].append(consecutive_count)
                    consecutive_count = 1
                    prev_top_match_id = top_match_id
            else:
                if prev_top_match_id and consecutive_count > 0:
                    if prev_top_match_id not in temporal_matches:
                        temporal_matches[prev_top_match_id] = []
                    temporal_matches[prev_top_match_id].append(consecutive_count)
                consecutive_count = 0
                prev_top_match_id = None
        
        # Record final consecutive match
        if prev_top_match_id and consecutive_count > 0:
            if prev_top_match_id not in temporal_matches:
                temporal_matches[prev_top_match_id] = []
            temporal_matches[prev_top_match_id].append(consecutive_count)
        
        for seg_result in filtered_segment_results:
            # Get scale weight for multi-scale fusion
            scale_weight = seg_result.get("scale_weight", 1.0)
            
            for result in seg_result["results"]:
                candidate_id = result.get("id", f"index_{result['index']}")
                if candidate_id not in all_candidates:
                    all_candidates[candidate_id] = {
                        "id": candidate_id,
                        "similarities": [],
                        "ranks": [],
                        "rank_1_count": 0,
                        "rank_5_count": 0,
                        "count": 0,
                        "temporal_score": 0.0,
                        "scale_weights": []  # Track weights from different scales
                    }
                # Weight similarity by scale importance
                weighted_similarity = result["similarity"] * scale_weight
                all_candidates[candidate_id]["similarities"].append(weighted_similarity)
                all_candidates[candidate_id]["ranks"].append(result["rank"])
                all_candidates[candidate_id]["count"] += 1
                all_candidates[candidate_id]["scale_weights"].append(scale_weight)
                if result["rank"] == 1:
                    all_candidates[candidate_id]["rank_1_count"] += 1
                if result["rank"] <= 5:
                    all_candidates[candidate_id]["rank_5_count"] += 1
        
        # Calculate temporal consistency scores
        for candidate_id, data in all_candidates.items():
            if candidate_id in temporal_matches and use_temporal_consistency:
                # Score based on longest consecutive match and total consecutive matches
                consecutive_lengths = temporal_matches[candidate_id]
                max_consecutive = max(consecutive_lengths) if consecutive_lengths else 0
                total_consecutive = sum(consecutive_lengths)
                # Normalize: longer consecutive matches = higher score
                temporal_score = (max_consecutive / total_segments) * 0.5 + (total_consecutive / total_segments) * 0.5
                data["temporal_score"] = temporal_score
            else:
                data["temporal_score"] = 0.0
        
        # Get aggregation weights from config (with optimized defaults)
        agg_weights = agg_config.get("weights", {})
        weight_similarity = agg_weights.get("similarity", 0.35)
        weight_rank1 = agg_weights.get("rank_1", 0.30)
        weight_rank5 = agg_weights.get("rank_5", 0.15)
        weight_match_ratio = agg_weights.get("match_ratio", 0.10)
        weight_temporal = agg_weights.get("temporal", temporal_consistency_weight)
        
        # Normalize weights to sum to 1.0
        total_weight = weight_similarity + weight_rank1 + weight_rank5 + weight_match_ratio + weight_temporal
        if total_weight > 0:
            weight_similarity /= total_weight
            weight_rank1 /= total_weight
            weight_rank5 /= total_weight
            weight_match_ratio /= total_weight
            weight_temporal /= total_weight
        
        # Compute aggregate scores with multiple signals
        aggregated = []
        for candidate_id, data in all_candidates.items():
            similarities = np.array(data["similarities"])
            
            # 1. Weighted similarity (weight by similarity squared and scale weights)
            if len(similarities) > 0:
                # Combine similarity weights with scale weights
                scale_weights = np.array(data.get("scale_weights", [1.0] * len(similarities)))
                similarity_weights = similarities ** 2  # Square weighting for high-similarity segments
                combined_weights = similarity_weights * scale_weights  # Multiply by scale importance
                weighted_sim = np.sum(similarities * combined_weights) / np.sum(combined_weights) if np.sum(combined_weights) > 0 else np.mean(similarities)
            else:
                weighted_sim = 0.0
            
            # 2. Voting scores (normalized by total segments)
            rank_1_score = data["rank_1_count"] / total_segments if total_segments > 0 else 0.0
            rank_5_score = data["rank_5_count"] / total_segments if total_segments > 0 else 0.0
            
            # 3. Match count ratio (how many segments matched this candidate)
            match_ratio = data["count"] / total_segments if total_segments > 0 else 0.0
            
            # 4. Temporal consistency score
            temporal_score = data["temporal_score"]
            
            # 5. Combined score: weighted similarity + voting bonuses + temporal consistency
            combined_score = (
                weight_similarity * weighted_sim +      # Weighted similarity (primary signal)
                weight_rank1 * rank_1_score +           # Rank-1 voting (strongest signal)
                weight_rank5 * rank_5_score +          # Rank-5 voting (supporting signal)
                weight_match_ratio * match_ratio +      # Match ratio (coverage signal)
                weight_temporal * temporal_score        # Temporal consistency (consecutive matches)
            )
            
            # Also compute traditional metrics for compatibility
            avg_similarity = np.mean(similarities) if len(similarities) > 0 else 0.0
            avg_rank = np.mean(data["ranks"]) if len(data["ranks"]) > 0 else float('inf')
            min_rank = min(data["ranks"]) if len(data["ranks"]) > 0 else float('inf')
            
            aggregated.append({
                "id": candidate_id,
                "mean_similarity": float(weighted_sim),  # Use weighted similarity
                "combined_score": float(combined_score),  # New combined score for ranking
                "rank_1_count": data["rank_1_count"],
                "rank_5_count": data["rank_5_count"],
                "rank_1_score": float(rank_1_score),
                "rank_5_score": float(rank_5_score),
                "match_ratio": float(match_ratio),
                "temporal_score": float(temporal_score),
                "avg_similarity": float(avg_similarity),  # Keep for backward compatibility
                "avg_rank": float(avg_rank),
                "min_rank": int(min_rank),
                "match_count": data["count"],
                "rank": len(aggregated) + 1
            })
        
        # Sort by combined_score (primary) then by mean_similarity (secondary)
        aggregated.sort(key=lambda x: (x["combined_score"], x["mean_similarity"]), reverse=True)
        for i, item in enumerate(aggregated):
            item["rank"] = i + 1
        
        # Second-stage re-ranking: re-query top candidates with more detailed analysis
        rerank_config = agg_config.get("second_stage_rerank", {})
        use_second_stage = rerank_config.get("enabled", False)
        rerank_top_k = rerank_config.get("top_k", 5)  # Re-rank top 5 candidates
        
        if use_second_stage and len(aggregated) > 1:
            top_candidates = aggregated[:rerank_top_k]
            reranked_candidates = _second_stage_rerank(
                top_candidates,
                filtered_segment_results,
                index,
                index_metadata,
                model_config,
                topk
            )
            
            # Replace top candidates with re-ranked results
            if reranked_candidates:
                aggregated = reranked_candidates + aggregated[rerank_top_k:]
                # Re-assign ranks
                for i, item in enumerate(aggregated):
                    item["rank"] = i + 1
                logger.debug(f"Second-stage re-ranking: re-ranked top {rerank_top_k} candidates")
        
        # Result validation: check consistency and quality
        validation_config = agg_config.get("validation", {})
        use_validation = validation_config.get("enabled", True)
        min_quality_score = validation_config.get("min_quality_score", 0.0)
        
        if use_validation:
            for item in aggregated:
                # Compute quality score
                quality_score = _compute_result_quality(item, total_segments)
                item["quality_score"] = float(quality_score)
                
                # Mark as validated
                item["validated"] = quality_score >= min_quality_score
        
        # Compute confidence scores for re-ranking
        # Confidence combines multiple signals: score gap, consistency, match quality
        if len(aggregated) > 1:
            top_score = aggregated[0]["combined_score"]
            second_score = aggregated[1]["combined_score"] if len(aggregated) > 1 else 0.0
            score_gap = top_score - second_score if top_score > 0 else 0.0
            
            for item in aggregated:
                # Confidence factors:
                # 1. Score gap (how much better than second place)
                # 2. Rank-1 ratio (how many segments matched at rank 1)
                # 3. Temporal consistency (consecutive matches)
                # 4. Match ratio (coverage)
                rank_1_ratio = item["rank_1_count"] / total_segments if total_segments > 0 else 0.0
                match_ratio = item["match_count"] / total_segments if total_segments > 0 else 0.0
                
                # Normalized score gap (relative to top score)
                normalized_gap = score_gap / top_score if top_score > 0 else 0.0
                
                # Optimized confidence score (0-1): weighted combination
                # Enhanced with quality score and re-ranking score if available
                quality_score = item.get("quality_score", 0.0)
                rerank_score = item.get("rerank_score", None)
                
                # Base confidence factors
                confidence_base = (
                    0.25 * min(normalized_gap * 2, 1.0) +      # Score gap (max 0.25)
                    0.25 * rank_1_ratio +                      # Rank-1 ratio (max 0.25)
                    0.20 * item["temporal_score"] +            # Temporal consistency (max 0.20)
                    0.15 * min(match_ratio * 2, 1.0) +         # Match ratio (max 0.15)
                    0.15 * quality_score                       # Quality score (max 0.15)
                )
                
                # Boost confidence if second-stage re-ranking was performed
                if rerank_score is not None:
                    rerank_boost = rerank_score * 0.1  # Up to 10% boost
                    confidence = min(1.0, confidence_base + rerank_boost)
                else:
                    confidence = confidence_base
                
                item["confidence"] = float(confidence)
        else:
            # Single candidate: moderate confidence
            for item in aggregated:
                item["confidence"] = 0.5
        
        # Re-rank by confidence if enabled
        use_confidence_rerank = agg_config.get("use_confidence_rerank", True)
        min_confidence_threshold = agg_config.get("min_confidence_threshold", 0.0)
        
        if use_confidence_rerank:
            # Sort by confidence-weighted score: (confidence * combined_score)
            aggregated.sort(
                key=lambda x: (x["confidence"] * x["combined_score"], x["combined_score"]),
                reverse=True
            )
            # Re-assign ranks
            for i, item in enumerate(aggregated):
                item["rank"] = i + 1
        
        # Filter results below confidence threshold
        if min_confidence_threshold > 0:
            filtered_aggregated = [
                item for item in aggregated
                if item["confidence"] >= min_confidence_threshold
            ]
            if len(filtered_aggregated) > 0:
                aggregated = filtered_aggregated
                logger.debug(f"Confidence filtering: kept {len(aggregated)}/{len(aggregated) + len([x for x in aggregated if x.get('confidence', 0) < min_confidence_threshold])} candidates")
        
        # Enhanced detection for song_a_in_song_b using direct similarity
        if transform_type == 'song_a_in_song_b' and expected_orig_id and index_metadata:
            # Find maximum similarity to original file by re-querying with larger topk
            # Most segments won't have original in top 10-30, so we need to query more
            max_direct_similarity = 0.0
            best_orig_match_id = None
            
            # Get all original segment IDs from index using proper file ID extraction
            index_ids = index_metadata.get("ids", [])
            orig_segment_ids = [
                idx for idx in index_ids 
                if _extract_file_id_from_segment_id(str(idx)) == expected_orig_id
            ]
            
            # Re-query each segment with MUCH larger topk to find original segments
            if orig_segment_ids and stored_embeddings is not None:
                # Query with topk = all original segments + buffer to ensure we find them
                extended_topk = min(len(orig_segment_ids) * 3, index.ntotal)
                
                for seg_emb in stored_embeddings:
                    # Re-query with extended topk to find original segments
                    extended_results = query_index(
                        index,
                        seg_emb,
                        topk=extended_topk,
                        ids=index_ids,
                        normalize=True,
                        index_metadata=index_metadata
                    )
                    
                    # Find best match to original in extended results using proper file ID extraction
                    for result in extended_results:
                        result_id = result.get("id", "")
                        result_file_id = _extract_file_id_from_segment_id(str(result_id))
                        if result_file_id == expected_orig_id:
                            seg_sim = result.get("similarity", 0.0)
                            if seg_sim > max_direct_similarity:
                                max_direct_similarity = seg_sim
                                best_orig_match_id = result_id
            else:
                # Fallback: Check existing segment results (may not find original if topk was too small)
                for seg_result in segment_results:
                    seg_results_list = seg_result.get("results", [])
                    for result in seg_results_list:
                        result_id = result.get("id", "")
                        result_file_id = _extract_file_id_from_segment_id(str(result_id))
                        if result_file_id == expected_orig_id:
                            seg_sim = result.get("similarity", 0.0)
                            if seg_sim > max_direct_similarity:
                                max_direct_similarity = seg_sim
                                best_orig_match_id = result_id
            
            # If direct similarity > 0.4 (lowered threshold for quiet/transformed samples), override aggregation
            if max_direct_similarity > 0.4 and best_orig_match_id:
                # Check if original is already in aggregated results using proper file ID extraction
                orig_in_results = False
                orig_result_idx = None
                for i, item in enumerate(aggregated):
                    item_id = str(item.get("id", ""))
                    item_file_id = _extract_file_id_from_segment_id(item_id)
                    if item_file_id == expected_orig_id:
                        orig_in_results = True
                        orig_result_idx = i
                        break
                
                if orig_in_results and orig_result_idx is not None and orig_result_idx > 0:
                    # Move original to rank 1
                    orig_item = aggregated.pop(orig_result_idx)
                    orig_item["rank"] = 1
                    orig_item["mean_similarity"] = max(orig_item.get("mean_similarity", 0.0), max_direct_similarity)
                    orig_item["combined_score"] = max(orig_item.get("combined_score", 0.0), max_direct_similarity)
                    aggregated.insert(0, orig_item)
                    # Re-assign ranks
                    for i, item in enumerate(aggregated):
                        item["rank"] = i + 1
                elif not orig_in_results:
                    # Add original as rank 1
                    orig_item = {
                        "id": best_orig_match_id,
                        "mean_similarity": float(max_direct_similarity),
                        "combined_score": float(max_direct_similarity),
                        "rank": 1,
                        "rank_1_count": 0,
                        "rank_5_count": 0,
                        "match_ratio": 0.0,
                        "temporal_score": 0.0,
                        "confidence": 1.0,
                        "match_count": 0,
                        "avg_similarity": float(max_direct_similarity),
                        "avg_rank": 1.0,
                        "min_rank": 1
                    }
                    aggregated.insert(0, orig_item)
                    # Re-assign ranks
                    for i, item in enumerate(aggregated):
                        item["rank"] = i + 1
        
        # Log aggregation metrics for top candidates (for debugging/optimization)
        if logger.isEnabledFor(logging.DEBUG) and len(aggregated) > 0:
            top_3 = aggregated[:3]
            logger.debug(f"Aggregation metrics for {file_path.stem}:")
            for idx, candidate in enumerate(top_3, 1):
                logger.debug(
                    f"  Rank {idx}: {candidate['id'][:30]}... | "
                    f"Score: {candidate['combined_score']:.4f} | "
                    f"Conf: {candidate.get('confidence', 0):.3f} | "
                    f"Sim: {candidate['mean_similarity']:.3f} | "
                    f"R1: {candidate['rank_1_count']}/{total_segments} | "
                    f"Temp: {candidate['temporal_score']:.3f} | "
                    f"Qual: {candidate.get('quality_score', 0):.3f}"
                )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "file_path": str(file_path),
            "file_id": file_path.stem,
            "num_segments": len(segment_results),
            "latency_ms": latency_ms,
            "segment_results": segment_results,
            "aggregated_results": aggregated[:topk],
            "confidence_scores": {item["id"]: item.get("confidence", 0.0) for item in aggregated[:topk]},
            "quality_scores": {item["id"]: item.get("quality_score", 0.0) for item in aggregated[:topk]},
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Query failed for {file_path}: {e}")
        return {
            "file_path": str(file_path),
            "file_id": file_path.stem,
            "error": str(e),
            "latency_ms": (time.time() - start_time) * 1000,
            "timestamp": time.time()
        }


def run_queries(
    transform_manifest_path: Path,
    index_path: Path,
    fingerprint_config_path: Path,
    output_dir: Path,
    topk: int = 30
) -> pd.DataFrame:
    """
    Run queries on all transformed files.
    
    Returns:
        DataFrame with query results
    """
    # Load transform manifest
    transform_df = pd.read_csv(transform_manifest_path)
    logger.info(f"Loaded {len(transform_df)} transformed files")
    
    # Load fingerprint model
    model_config = load_fingerprint_model(fingerprint_config_path)
    logger.info(f"Loaded fingerprint model: {model_config['embedding_dim']}D")
    
    # Load index
    index, index_metadata = load_index(index_path)
    logger.info(f"Loaded index with {index.ntotal} vectors")
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    query_records = []
    
    # Process each transformed file
    for _, row in tqdm(transform_df.iterrows(), total=len(transform_df), desc="Running queries"):
        file_path = Path(row["output_path"])
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Run query with transform info for enhanced detection
        result = run_query_on_file(
            file_path,
            index,
            model_config,
            topk=topk,
            index_metadata=index_metadata,
            transform_type=row.get("transform_type"),
            expected_orig_id=row.get("orig_id")
        )
        
        # Save individual result JSON
        # Sanitize transformed_id to remove filesystem-invalid characters (/, \, :, *, ?, ", <, >, |)
        safe_id = str(row['transformed_id']).replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        result_path = results_dir / f"{safe_id}_query.json"
        # Ensure parent directory exists
        result_path.parent.mkdir(parents=True, exist_ok=True)
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Extract top match info
        top_match = result.get("aggregated_results", [{}])[0] if result.get("aggregated_results") else {}
        
        query_records.append({
            "transformed_id": row["transformed_id"],
            "orig_id": row["orig_id"],
            "transform_type": row["transform_type"],
            "severity": row["severity"],
            "file_path": str(file_path),
            "latency_ms": result.get("latency_ms", 0),
            "num_segments": result.get("num_segments", 0),
            "top_match_id": top_match.get("id", ""),
            "top_match_similarity": top_match.get("mean_similarity", 0.0),
            "top_match_rank": top_match.get("rank", -1),
            "result_path": str(result_path),
            "error": result.get("error", ""),
        })
    
    # Save summary CSV
    results_df = pd.DataFrame(query_records)
    summary_path = output_dir / "query_summary.csv"
    results_df.to_csv(summary_path, index=False)
    
    logger.info(f"Saved query results to {output_dir}")
    
    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fingerprint queries")
    parser.add_argument("--manifest", type=Path, required=True, help="Transform manifest CSV")
    parser.add_argument("--index", type=Path, required=True, help="FAISS index path")
    parser.add_argument("--config", type=Path, required=True, help="Fingerprint config YAML")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--topk", type=int, default=30, help="Top-K results (increased from 10 for better aggregation)")
    
    args = parser.parse_args()
    
    run_queries(
        args.manifest,
        args.index,
        args.config,
        args.output,
        topk=args.topk
    )
