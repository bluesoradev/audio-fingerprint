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
    sample_rate: int = 44100
) -> List[Dict]:
    """
    Segment audio into fixed-length chunks.
    
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
    save_embeddings: bool = True
) -> np.ndarray:
    """
    Extract embeddings for segments using model.
    
    Args:
        segments: List of segment dictionaries
        model: EmbeddingGenerator model
        output_dir: Directory to save embeddings (optional)
        save_embeddings: Whether to save to disk
        
    Returns:
        Array of embeddings (N_segments, D)
    """
    embeddings = []
    
    # Determine if we have a proper EmbeddingGenerator or fallback
    if hasattr(model, "generate_embedding"):
        # Use standard interface
        generate_fn = lambda seg: model.generate_embedding_from_audio(
            seg["audio"], seg["sample_rate"]
        ) if hasattr(model, "generate_embedding_from_audio") else None
    elif hasattr(model, "model") and hasattr(model["model"], "generate_embedding"):
        # Model dict format
        generate_fn = lambda seg: model["model"].generate_embedding_from_audio(
            seg["audio"], seg["sample_rate"]
        ) if hasattr(model["model"], "generate_embedding_from_audio") else None
    else:
        # Fallback: use librosa features
        logger.warning("Using fallback embedding extraction")
        generate_fn = None
    
    for seg in tqdm(segments, desc="Extracting embeddings", leave=False):
        try:
            if generate_fn:
                emb = generate_fn(seg)
            else:
                # Fallback: extract using librosa
                from fingerprint.load_model import FallbackEmbeddingGenerator
                fallback = FallbackEmbeddingGenerator()
                
                # Save segment temporarily
                import tempfile
                import soundfile as sf
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    sf.write(str(tmp_path), seg["audio"], seg["sample_rate"])
                    emb = fallback.generate_embedding(tmp_path)
                    tmp_path.unlink()
            
            if emb is not None:
                embeddings.append(emb)
                
                # Save if requested
                if save_embeddings and output_dir:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    emb_path = output_dir / f"{seg['segment_id']}.npy"
                    np.save(emb_path, emb)
            else:
                logger.warning(f"Failed to extract embedding for {seg['segment_id']}")
                
        except Exception as e:
            logger.error(f"Failed to extract embedding for {seg['segment_id']}: {e}")
            continue
    
    if not embeddings:
        raise ValueError("No embeddings were extracted")
    
    embeddings_array = np.vstack(embeddings)
    logger.info(f"Extracted {len(embeddings)} embeddings, shape: {embeddings_array.shape}")
    
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
