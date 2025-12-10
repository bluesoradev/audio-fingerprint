"""Load frozen fingerprint model."""
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

logger = logging.getLogger(__name__)

# Try to import embedding generator from parent project
try:
    import sys
    parent_dir = Path(__file__).parent.parent.parent / "audio-ai"
    if parent_dir.exists():
        sys.path.insert(0, str(parent_dir))
    from src.stage3_embedding.embedding_generator import EmbeddingGenerator
    HAS_EMBEDDING_GENERATOR = True
except ImportError:
    HAS_EMBEDDING_GENERATOR = False
    logger.warning("Could not import EmbeddingGenerator from parent project. Will use fallback.")


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute file hash for verification."""
    hash_obj = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def load_fingerprint_model(config_path: Path) -> Dict[str, Any]:
    """
    Load fingerprint model according to config.
    
    Returns:
        Dictionary with 'model' (EmbeddingGenerator) and 'config' (dict)
    """
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    model_config = config.get("model", {})
    audio_config = config.get("audio", {})
    embedding_config = config.get("embedding", {})
    
    # Verify model checksum if specified
    model_path = model_config.get("path")
    expected_checksum = model_config.get("checksum")
    
    if model_path and expected_checksum:
        actual_checksum = compute_file_hash(Path(model_path))
        if actual_checksum != expected_checksum:
            logger.warning(f"Model checksum mismatch! Expected {expected_checksum}, got {actual_checksum}")
    
    # Initialize embedding generator
    if HAS_EMBEDDING_GENERATOR:
        generator = EmbeddingGenerator(
            embedding_dim=embedding_config.get("dimension", 512),
            sample_rate=audio_config.get("sample_rate", 44100),
            model_type=model_config.get("type", "mert"),
            device=model_config.get("device")
        )
        logger.info(f"Loaded {generator.active_model_name} model")
    else:
        # Fallback: create a minimal wrapper
        logger.warning("Using fallback embedding generator")
        generator = None
    
    return {
        "model": generator,
        "config": config,
        "sample_rate": audio_config.get("sample_rate", 44100),
        "segment_length": audio_config.get("segment_length", 0.5),
        "embedding_dim": embedding_config.get("dimension", 512),
    }


class FallbackEmbeddingGenerator:
    """Fallback embedding generator using librosa features."""
    
    def __init__(self, embedding_dim: int = 512, sample_rate: int = 44100):
        self.embedding_dim = embedding_dim
        self.sample_rate = sample_rate
    
    def generate_embedding(self, audio_path: Path):
        """Generate embedding using librosa features."""
        import numpy as np
        import librosa
        
        y, sr = librosa.load(str(audio_path), sr=self.sample_rate, mono=True)
        
        # Extract features
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        chroma = librosa.feature.chroma(y=y, sr=sr)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        
        # Concatenate and flatten
        features = np.concatenate([
            mfcc.mean(axis=1),
            chroma.mean(axis=1),
            spectral_centroid.mean(axis=1, keepdims=True).flatten()
        ])
        
        # Pad or truncate to embedding_dim
        if len(features) < self.embedding_dim:
            features = np.pad(features, (0, self.embedding_dim - len(features)))
        else:
            features = features[:self.embedding_dim]
        
        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm
        
        return features.astype(np.float32)
