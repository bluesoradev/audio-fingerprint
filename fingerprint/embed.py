"""Audio segmentation and embedding extraction."""
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import librosa
from tqdm import tqdm

logger = logging.getLogger(__name__)


def segment_audio(
    audio_path: Path,
    segment_length: float = 0.5,
    hop_length: Optional[float] = None,
    sample_rate: int = 44100,
    overlap_ratio: Optional[float] = None
) -> List[Dict]:
    """
    Segment audio into fixed-length chunks with optional overlap.
    
    Args:
        audio_path: Path to audio file
        segment_length: Length of each segment in seconds
        hop_length: Hop length in seconds (if None, calculated from overlap_ratio or no overlap)
        sample_rate: Sample rate for audio
        overlap_ratio: Overlap ratio (0.0 = no overlap, 0.5 = 50% overlap)
    
    Returns:
        List of segment dictionaries with start, end, path, etc.
    """
    try:
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=sample_rate, mono=True)
        
        duration = len(y) / sr
        segment_samples = int(segment_length * sr)
        
        # Determine hop length
        if hop_length is None:
            if overlap_ratio is not None and overlap_ratio > 0:
                # Calculate hop length from overlap ratio
                hop_samples = int(segment_samples * (1 - overlap_ratio))
            else:
                hop_samples = segment_samples  # No overlap
        else:
            hop_samples = int(hop_length * sr)
        
        segments = []
        start_sample = 0
        segment_idx = 0
        
        while start_sample + segment_samples <= len(y):
            end_sample = start_sample + segment_samples
            segment_audio = y[start_sample:end_sample]
            
            start_time = start_sample / sr
            end_time = end_sample / sr
            
            segment_id = f"{audio_path.stem}_seg_{segment_idx:04d}"
            
            segments.append({
                "segment_id": segment_id,
                "file_id": audio_path.stem,
                "start": start_time,
                "end": end_time,
                "duration": end_time - start_time,
                "start_sample": start_sample,
                "end_sample": end_sample,
                "audio": segment_audio,  # In-memory for now
                "sample_rate": sr,
            })
            
            start_sample += hop_samples
            segment_idx += 1
        
        logger.debug(f"Segmented {audio_path} into {len(segments)} segments")
        return segments
        
    except Exception as e:
        logger.error(f"Segmentation failed for {audio_path}: {e}")
        raise


def extract_embeddings(
    segments: List[Dict],
    model: any,
    output_dir: Optional[Path] = None,
    save_embeddings: bool = True,
    batch_size: int = 32
) -> np.ndarray:
    """
    Extract embeddings for segments using model with batch processing for GPU acceleration.
    
    Args:
        segments: List of segment dictionaries
        model: EmbeddingGenerator model (or dict with 'model' key)
        output_dir: Directory to save embeddings (optional)
        save_embeddings: Whether to save to disk
        batch_size: Batch size for GPU processing (default: 32, optimized for GPU throughput)
        
    Returns:
        Array of embeddings (N_segments, D)
    """
    embeddings = []
    
    # Extract the actual model from dict if needed
    actual_model = model
    if isinstance(model, dict):
        actual_model = model.get("model", model)
    
    # Check if model supports batch processing
    has_batch_method = hasattr(actual_model, "generate_embeddings_batch")
    has_generate_embedding = hasattr(actual_model, "generate_embedding")
    
    # Import required modules
    import tempfile
    import soundfile as sf
    
    # Get embedding dimension for fallback
    embedding_dim = 512
    if hasattr(actual_model, "embedding_dim"):
        embedding_dim = actual_model.embedding_dim
    elif isinstance(model, dict) and "embedding_dim" in model:
        embedding_dim = model["embedding_dim"]
    
    logger.info(f"Extracting embeddings using model: {type(actual_model).__name__}, batch_support: {has_batch_method}, batch_size: {batch_size}")
    
    # Try batch processing first (much faster on GPU)
    if has_batch_method and len(segments) > 1:
        try:
            # Prepare temporary files for all segments
            temp_paths = []
            temp_files_to_cleanup = []
            
            for seg in segments:
                try:
                    tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    tmp_path = Path(tmp_file.name)
                    sf.write(str(tmp_path), seg["audio"], seg["sample_rate"])
                    tmp_file.close()
                    temp_paths.append(tmp_path)
                    temp_files_to_cleanup.append(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to create temp file for {seg['segment_id']}: {e}")
                    temp_paths.append(None)
            
            # Process in batches
            for i in range(0, len(temp_paths), batch_size):
                batch_paths = temp_paths[i:i+batch_size]
                batch_segments = segments[i:i+batch_size]
                
                # Filter out None paths
                valid_batch = [(p, s) for p, s in zip(batch_paths, batch_segments) if p is not None]
                if not valid_batch:
                    continue
                
                valid_paths = [p for p, _ in valid_batch]
                valid_seg_ids = [s["segment_id"] for _, s in valid_batch]
                
                try:
                    # Use batch processing
                    batch_embeddings = actual_model.generate_embeddings_batch(valid_paths, batch_size=len(valid_paths))
                    
                    # Process results
                    for emb, seg_id in zip(batch_embeddings, valid_seg_ids):
                        if emb is not None:
                            emb = np.asarray(emb)
                            if len(emb.shape) > 1:
                                emb = emb.flatten()
                            
                            if emb.size > 0:
                                embeddings.append(emb)
                                
                                # Save if requested
                                if save_embeddings and output_dir:
                                    output_dir.mkdir(parents=True, exist_ok=True)
                                    emb_path = output_dir / f"{seg_id}.npy"
                                    np.save(emb_path, emb)
                            else:
                                logger.warning(f"Empty embedding for {seg_id}")
                        else:
                            logger.warning(f"None embedding for {seg_id}")
                            
                except Exception as e:
                    logger.warning(f"Batch processing failed for batch {i//batch_size}: {e}, falling back to sequential")
                    # Fall back to sequential for this batch
                    for tmp_path, seg in valid_batch:
                        try:
                            if has_generate_embedding:
                                emb = actual_model.generate_embedding(tmp_path)
                                if emb is not None:
                                    emb = np.asarray(emb)
                                    if len(emb.shape) > 1:
                                        emb = emb.flatten()
                                    if emb.size > 0:
                                        embeddings.append(emb)
                        except Exception as e2:
                            logger.error(f"Failed to extract embedding for {seg['segment_id']}: {e2}")
            
            # Cleanup temp files
            for tmp_path in temp_files_to_cleanup:
                if tmp_path and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp file {tmp_path}: {cleanup_error}")
            
            if embeddings:
                embeddings_array = np.vstack(embeddings)
                logger.info(f"Successfully extracted {len(embeddings)}/{len(segments)} embeddings using batch processing, shape: {embeddings_array.shape}")
                return embeddings_array
            else:
                logger.warning("Batch processing produced no embeddings, falling back to sequential")
                
        except Exception as e:
            logger.warning(f"Batch processing failed: {e}, falling back to sequential processing")
    
    # Fallback to sequential processing
    logger.debug("Using sequential embedding extraction")
    for seg in tqdm(segments, desc="Extracting embeddings", leave=False):
        tmp_path = None
        try:
            # Always save segment to temp file since models expect file paths
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                sf.write(str(tmp_path), seg["audio"], seg["sample_rate"])
            
            # Use generate_embedding (takes Path) if available
            if has_generate_embedding:
                try:
                    emb = actual_model.generate_embedding(tmp_path)
                except Exception as e:
                    logger.warning(f"Model.generate_embedding failed for {seg['segment_id']}: {e}, trying fallback")
                    # Fall back to librosa-based extraction
                    from fingerprint.load_model import FallbackEmbeddingGenerator
                    fallback = FallbackEmbeddingGenerator(
                        embedding_dim=embedding_dim,
                        sample_rate=seg["sample_rate"]
                    )
                    emb = fallback.generate_embedding(tmp_path)
            else:
                # Fallback: use librosa features
                from fingerprint.load_model import FallbackEmbeddingGenerator
                fallback = FallbackEmbeddingGenerator(
                    embedding_dim=embedding_dim,
                    sample_rate=seg["sample_rate"]
                )
                emb = fallback.generate_embedding(tmp_path)
            
            # Validate embedding
            if emb is not None:
                emb = np.asarray(emb)
                if len(emb.shape) == 0 or emb.size == 0:
                    logger.warning(f"Empty embedding for {seg['segment_id']}")
                    emb = None
                elif len(emb.shape) > 1:
                    # Flatten if needed
                    emb = emb.flatten()
            
            if emb is not None and emb.size > 0:
                embeddings.append(emb)
                
                # Save if requested
                if save_embeddings and output_dir:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    emb_path = output_dir / f"{seg['segment_id']}.npy"
                    np.save(emb_path, emb)
            else:
                logger.warning(f"Failed to extract embedding for {seg['segment_id']}: embedding is None or empty")
                
        except Exception as e:
            logger.error(f"Failed to extract embedding for {seg['segment_id']}: {e}", exc_info=True)
        finally:
            # Always clean up temp file
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file {tmp_path}: {cleanup_error}")
    
    if not embeddings:
        error_msg = (
            "No embeddings were extracted - all segments failed. "
            "Check logs above for error details. "
            f"Processed {len(segments)} segments."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    embeddings_array = np.vstack(embeddings)
    logger.info(f"Successfully extracted {len(embeddings)}/{len(segments)} embeddings, shape: {embeddings_array.shape}")
    
    return embeddings_array


def normalize_embeddings(embeddings: np.ndarray, method: str = "l2") -> np.ndarray:
    """Normalize embeddings."""
    if method == "l2":
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        return embeddings / norms
    elif method == "none":
        return embeddings
    else:
        raise ValueError(f"Unknown normalization method: {method}")
