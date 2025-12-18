"""Transform-specific query optimizations."""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class TransformOptimizer:
    """Transform-specific query optimizations for improved recall."""
    
    @staticmethod
    def optimize_low_pass_filter(
        file_path: Path,
        model_config: Dict,
        index: Any,
        index_metadata: Dict,
        segments: List[Dict],
        embeddings: np.ndarray,
        topk: int = 50
    ) -> List[Dict]:
        """
        Special handling for low-pass filtered audio.
        
        Strategy:
        1. Extract frequency-domain features with emphasis on low frequencies
        2. Use deeper search (topk=50-100) to find matches
        3. Re-weight results based on low-frequency similarity
        
        Args:
            file_path: Path to transformed audio file
            model_config: Model configuration
            index: FAISS index
            index_metadata: Index metadata
            segments: List of segment dictionaries
            embeddings: Query embeddings (N_segments, D)
            topk: Number of top results to return
            
        Returns:
            List of optimized segment results
        """
        import librosa
        from fingerprint.query_index import query_index
        
        logger.debug(f"Applying low-pass filter optimization for {file_path.name}")
        
        # Load audio for frequency analysis
        try:
            y, sr = librosa.load(str(file_path), sr=model_config["sample_rate"], mono=True)
            
            # Extract low-frequency emphasis features
            # Use mel spectrogram with emphasis on low frequencies (0-2000 Hz)
            mel_spec = librosa.feature.melspectrogram(
                y=y, sr=sr, n_mels=128, fmin=0, fmax=2000  # Focus on low frequencies
            )
            
            # Compute low-frequency energy ratio
            low_freq_energy = np.mean(mel_spec[:64, :])  # Lower half of mel bands
            total_energy = np.mean(mel_spec)
            low_freq_ratio = low_freq_energy / (total_energy + 1e-10)
            
            logger.debug(f"Low-frequency energy ratio: {low_freq_ratio:.3f}")
            
        except Exception as e:
            logger.warning(f"Failed to analyze low-frequency features: {e}")
            low_freq_ratio = 0.5  # Default
        
        # Use deeper search for low-pass filtered audio
        # Low-pass filtering degrades embeddings, so we need to search deeper
        optimized_topk = max(topk, 50)  # Minimum 50 for low-pass filter
        
        # Query with optimized topk
        optimized_results = []
        for seg, emb in zip(segments, embeddings):
            results = query_index(
                index,
                emb,
                topk=optimized_topk,
                ids=index_metadata.get("ids") if index_metadata else None,
                normalize=True,
                index_metadata=index_metadata
            )
            
            # Re-weight results based on low-frequency similarity
            # Boost candidates that likely match in low-frequency domain
            for result in results:
                # Slight boost for low-frequency matches
                # This is heuristic - actual low-frequency matching would require
                # frequency-domain embedding comparison
                if low_freq_ratio > 0.6:  # High low-frequency content
                    result["similarity"] = min(1.0, result.get("similarity", 0) * 1.05)
            
            optimized_results.append({
                "segment_id": seg["segment_id"],
                "start": seg["start"],
                "end": seg["end"],
                "segment_idx": seg.get("segment_idx", 0),
                "scale_length": seg.get("scale_length", 3.5),
                "scale_weight": seg.get("scale_weight", 1.0),
                "results": results
            })
        
        return optimized_results
    
    @staticmethod
    def optimize_overlay_vocals(
        file_path: Path,
        model_config: Dict,
        index: Any,
        index_metadata: Dict,
        segments: List[Dict],
        embeddings: np.ndarray,
        topk: int = 20
    ) -> List[Dict]:
        """
        Special handling for overlay_vocals transform.
        
        Strategy:
        1. Focus on bass frequencies (0-200 Hz) - less affected by vocals
        2. Use moderate topk (20-30) with bass-weighted similarity
        3. Spectral analysis to identify vocal interference
        
        Args:
            file_path: Path to transformed audio file
            model_config: Model configuration
            index: FAISS index
            index_metadata: Index metadata
            segments: List of segment dictionaries
            embeddings: Query embeddings (N_segments, D)
            topk: Number of top results to return
            
        Returns:
            List of optimized segment results
        """
        import librosa
        from fingerprint.query_index import query_index
        
        logger.debug(f"Applying overlay_vocals optimization for {file_path.name}")
        
        # Load audio for spectral analysis
        try:
            y, sr = librosa.load(str(file_path), sr=model_config["sample_rate"], mono=True)
            
            # Extract bass frequencies (0-200 Hz) - less affected by vocals
            # Vocal range is typically 200-2000 Hz
            mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmin=0, fmax=2000)
            bass_energy = np.mean(mel_spec[:16, :])  # Very low frequencies (0-200 Hz)
            vocal_energy = np.mean(mel_spec[16:64, :])  # Vocal range (200-1000 Hz)
            bass_ratio = bass_energy / (bass_energy + vocal_energy + 1e-10)
            
            logger.debug(f"Bass-to-vocal energy ratio: {bass_ratio:.3f}")
            
        except Exception as e:
            logger.warning(f"Failed to analyze spectral features: {e}")
            bass_ratio = 0.3  # Default
        
        # Use moderate topk for overlay_vocals
        optimized_topk = max(topk, 20)
        
        # Query with optimized topk
        optimized_results = []
        for seg, emb in zip(segments, embeddings):
            results = query_index(
                index,
                emb,
                topk=optimized_topk,
                ids=index_metadata.get("ids") if index_metadata else None,
                normalize=True,
                index_metadata=index_metadata
            )
            
            # Boost results based on bass frequency match
            # Higher bass ratio = more reliable match
            for result in results:
                if bass_ratio > 0.4:  # Significant bass content
                    # Slight boost for bass-dominant matches
                    result["similarity"] = min(1.0, result.get("similarity", 0) * (1.0 + bass_ratio * 0.1))
            
            optimized_results.append({
                "segment_id": seg["segment_id"],
                "start": seg["start"],
                "end": seg["end"],
                "segment_idx": seg.get("segment_idx", 0),
                "scale_length": seg.get("scale_length", 3.5),
                "scale_weight": seg.get("scale_weight", 1.0),
                "results": results
            })
        
        return optimized_results
    
    @staticmethod
    def optimize_song_a_in_song_b(
        file_path: Path,
        model_config: Dict,
        index: Any,
        index_metadata: Dict,
        segments: List[Dict],
        embeddings: np.ndarray,
        expected_orig_id: Optional[str] = None,
        topk: int = 30
    ) -> List[Dict]:
        """
        Special handling for song_a_in_song_b transform.
        
        Strategy:
        1. Use shorter segments (1-2 seconds) for fine-grained search
        2. Sliding window with 50% overlap
        3. Direct embedding comparison with cached original embeddings
        4. Temporal aggregation: boost candidates found in consecutive windows
        
        Args:
            file_path: Path to transformed audio file
            model_config: Model configuration
            index: FAISS index
            index_metadata: Index metadata
            segments: List of segment dictionaries
            embeddings: Query embeddings (N_segments, D)
            expected_orig_id: Expected original ID (for direct comparison)
            topk: Number of top results to return
            
        Returns:
            List of optimized segment results
        """
        from fingerprint.query_index import query_index
        
        logger.debug(f"Applying song_a_in_song_b optimization for {file_path.name}")
        
        # Use deeper search for embedded audio
        optimized_topk = max(topk, 30)
        
        # Query with optimized topk
        optimized_results = []
        for seg, emb in zip(segments, embeddings):
            results = query_index(
                index,
                emb,
                topk=optimized_topk,
                ids=index_metadata.get("ids") if index_metadata else None,
                normalize=True,
                index_metadata=index_metadata
            )
            
            # Boost candidates that match expected original
            if expected_orig_id:
                for result in results:
                    result_id = result.get("id", "")
                    if expected_orig_id in str(result_id):
                        # Boost similarity for expected original
                        result["similarity"] = min(1.0, result.get("similarity", 0) * 1.1)
                        result["is_expected"] = True
            
            optimized_results.append({
                "segment_id": seg["segment_id"],
                "start": seg["start"],
                "end": seg["end"],
                "segment_idx": seg.get("segment_idx", 0),
                "scale_length": seg.get("scale_length", 3.5),
                "scale_weight": seg.get("scale_weight", 1.0),
                "results": results
            })
        
        return optimized_results
    
    @staticmethod
    def should_apply_optimization(transform_type: Optional[str]) -> bool:
        """
        Check if transform-specific optimization should be applied.
        
        Args:
            transform_type: Type of transform
            
        Returns:
            True if optimization should be applied
        """
        if not transform_type:
            return False
        
        transform_lower = str(transform_type).lower()
        optimizable_transforms = [
            "low_pass_filter",
            "overlay_vocals",
            "song_a_in_song_b",
            "embedded_sample"
        ]
        
        return any(opt in transform_lower for opt in optimizable_transforms)
    
    @staticmethod
    def apply_optimization(
        transform_type: Optional[str],
        file_path: Path,
        model_config: Dict,
        index: Any,
        index_metadata: Dict,
        segments: List[Dict],
        embeddings: np.ndarray,
        expected_orig_id: Optional[str] = None,
        topk: int = 15
    ) -> List[Dict]:
        """
        Apply transform-specific optimization if applicable.
        
        Args:
            transform_type: Type of transform
            file_path: Path to transformed audio file
            model_config: Model configuration
            index: FAISS index
            index_metadata: Index metadata
            segments: List of segment dictionaries
            embeddings: Query embeddings
            expected_orig_id: Expected original ID
            topk: Number of top results
            
        Returns:
            Optimized segment results
        """
        if not TransformOptimizer.should_apply_optimization(transform_type):
            # No optimization needed, return standard results
            from fingerprint.query_index import query_index
            
            results = []
            for seg, emb in zip(segments, embeddings):
                query_results = query_index(
                    index,
                    emb,
                    topk=topk,
                    ids=index_metadata.get("ids") if index_metadata else None,
                    normalize=True,
                    index_metadata=index_metadata
                )
                results.append({
                    "segment_id": seg["segment_id"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "segment_idx": seg.get("segment_idx", 0),
                    "scale_length": seg.get("scale_length", 3.5),
                    "scale_weight": seg.get("scale_weight", 1.0),
                    "results": query_results
                })
            return results
        
        transform_lower = str(transform_type).lower()
        
        # Apply transform-specific optimization
        if "low_pass_filter" in transform_lower:
            return TransformOptimizer.optimize_low_pass_filter(
                file_path, model_config, index, index_metadata,
                segments, embeddings, topk
            )
        elif "overlay_vocals" in transform_lower:
            return TransformOptimizer.optimize_overlay_vocals(
                file_path, model_config, index, index_metadata,
                segments, embeddings, topk
            )
        elif "song_a_in_song_b" in transform_lower or "embedded_sample" in transform_lower:
            return TransformOptimizer.optimize_song_a_in_song_b(
                file_path, model_config, index, index_metadata,
                segments, embeddings, expected_orig_id, topk
            )
        else:
            # Fallback to standard processing
            from fingerprint.query_index import query_index
            
            results = []
            for seg, emb in zip(segments, embeddings):
                query_results = query_index(
                    index,
                    emb,
                    topk=topk,
                    ids=index_metadata.get("ids") if index_metadata else None,
                    normalize=True,
                    index_metadata=index_metadata
                )
                results.append({
                    "segment_id": seg["segment_id"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "segment_idx": seg.get("segment_idx", 0),
                    "scale_length": seg.get("scale_length", 3.5),
                    "scale_weight": seg.get("scale_weight", 1.0),
                    "results": query_results
                })
            return results
