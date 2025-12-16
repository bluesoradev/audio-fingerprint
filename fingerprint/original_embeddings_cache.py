"""Cache system for original file embeddings."""
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OriginalEmbeddingsCache:
    """Cache for original file embeddings with incremental updates."""
    
    def __init__(self, cache_dir: Path = Path("data/cache/original_embeddings")):
        """
        Initialize embeddings cache.
        
        Args:
            cache_dir: Directory to store cached embeddings
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = cache_dir / "cache_manifest.json"
        self.manifest = self._load_manifest()
        logger.info(f"Initialized embeddings cache at {cache_dir}")
        logger.info(f"Cache contains {len(self.manifest)} entries")
    
    def _load_manifest(self) -> dict:
        """Load cache manifest."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    manifest = json.load(f)
                    logger.info(f"Loaded cache manifest with {len(manifest)} entries")
                    return manifest
            except Exception as e:
                logger.warning(f"Failed to load cache manifest: {e}, starting fresh")
                return {}
        return {}
    
    def _save_manifest(self):
        """Save cache manifest."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache manifest: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get file hash for cache key."""
        try:
            return hashlib.md5(file_path.read_bytes()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute file hash for {file_path}: {e}")
            # Fallback to file modification time and size
            stat = file_path.stat()
            return hashlib.md5(f"{stat.st_mtime}_{stat.st_size}".encode()).hexdigest()
    
    def _get_model_hash(self, model_config: dict) -> str:
        """Generate hash from model configuration."""
        # Create hash from model config (excluding model object itself)
        config_str = json.dumps({
            "embedding_dim": model_config.get("embedding_dim", 512),
            "segment_length": model_config.get("segment_length", 10.0),
            "sample_rate": model_config.get("sample_rate", 44100),
            "model_type": str(type(model_config.get("model", ""))),
        }, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:16]
    
    def _get_cache_key(self, file_id: str, file_hash: str, model_hash: str) -> str:
        """Generate cache key."""
        return f"{file_id}_{file_hash[:12]}_{model_hash[:8]}"
    
    def get(self, file_id: str, file_path: Path, model_config: dict) -> Tuple[Optional[np.ndarray], Optional[List[Dict]]]:
        """
        Get cached embeddings and segments.
        
        Args:
            file_id: Unique identifier for the file
            file_path: Path to the audio file
            model_config: Model configuration dictionary
            
        Returns:
            Tuple of (embeddings_array, segments_list) or (None, None) if not cached
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None, None
        
        file_hash = self._get_file_hash(file_path)
        model_hash = self._get_model_hash(model_config)
        cache_key = self._get_cache_key(file_id, file_hash, model_hash)
        
        # Check manifest
        if cache_key not in self.manifest:
            logger.debug(f"No cache entry for {file_id} (key: {cache_key})")
            return None, None
        
        cache_info = self.manifest[cache_key]
        cache_dir = self.cache_dir / cache_key
        
        if not cache_dir.exists():
            logger.warning(f"Cache directory missing for {file_id}, removing from manifest")
            del self.manifest[cache_key]
            self._save_manifest()
            return None, None
        
        # Load embeddings
        embedding_files = sorted(cache_dir.glob("seg_*.npy"))
        if not embedding_files:
            logger.warning(f"No embedding files found in cache for {file_id}")
            return None, None
        
        try:
            embeddings = np.vstack([np.load(f) for f in embedding_files])
            
            # Load segments metadata
            segments_path = cache_dir / "segments.json"
            segments = None
            if segments_path.exists():
                with open(segments_path, 'r') as f:
                    segments = json.load(f)
            
            logger.info(f"✓ Using cached embeddings for {file_id} ({len(embeddings)} segments)")
            return embeddings, segments
        except Exception as e:
            logger.error(f"Failed to load cached embeddings for {file_id}: {e}")
            return None, None
    
    def set(self, file_id: str, file_path: Path, model_config: dict, 
             embeddings: np.ndarray, segments: List[Dict]):
        """
        Cache embeddings and segments.
        
        Args:
            file_id: Unique identifier for the file
            file_path: Path to the audio file
            model_config: Model configuration dictionary
            embeddings: Embeddings array (N_segments, D)
            segments: List of segment dictionaries
        """
        file_hash = self._get_file_hash(file_path)
        model_hash = self._get_model_hash(model_config)
        cache_key = self._get_cache_key(file_id, file_hash, model_hash)
        
        cache_dir = self.cache_dir / cache_key
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save embeddings
            for i, emb in enumerate(embeddings):
                emb_path = cache_dir / f"seg_{i:04d}.npy"
                np.save(emb_path, emb)
            
            # Save segments metadata
            segments_path = cache_dir / "segments.json"
            with open(segments_path, 'w') as f:
                json.dump(segments, f, indent=2)
            
            # Update manifest
            self.manifest[cache_key] = {
                "file_id": file_id,
                "file_path": str(file_path),
                "file_hash": file_hash,
                "model_hash": model_hash,
                "num_segments": len(embeddings),
                "embedding_dim": embeddings.shape[1] if len(embeddings) > 0 else 0,
                "cached_at": time.time()
            }
            self._save_manifest()
            
            logger.info(f"✓ Cached embeddings for {file_id} ({len(embeddings)} segments, dim={embeddings.shape[1] if len(embeddings) > 0 else 0})")
        except Exception as e:
            logger.error(f"Failed to cache embeddings for {file_id}: {e}", exc_info=True)
    
    def get_new_files(self, files_manifest_path: Path, model_config: dict) -> pd.DataFrame:
        """
        Identify which files in manifest are not yet cached.
        
        Args:
            files_manifest_path: Path to files manifest CSV
            model_config: Model configuration dictionary
            
        Returns:
            DataFrame with only new files that need embedding generation
        """
        files_df = pd.read_csv(files_manifest_path)
        model_hash = self._get_model_hash(model_config)
        new_files = []
        
        for _, row in files_df.iterrows():
            file_id = row["id"]
            file_path_str = row.get("file_path") or row.get("path")
            if not file_path_str:
                continue
            
            file_path = Path(file_path_str)
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}, skipping")
                continue
            
            # Check if cached
            file_hash = self._get_file_hash(file_path)
            cache_key = self._get_cache_key(file_id, file_hash, model_hash)
            
            if cache_key not in self.manifest:
                new_files.append(row)
            else:
                # Verify cache directory exists
                cache_dir = self.cache_dir / cache_key
                if not cache_dir.exists() or not list(cache_dir.glob("seg_*.npy")):
                    logger.warning(f"Cache entry exists but files missing for {file_id}, will regenerate")
                    new_files.append(row)
        
        new_df = pd.DataFrame(new_files)
        logger.info(f"Found {len(new_df)} new files out of {len(files_df)} total files")
        return new_df
    
    def clear(self, file_id: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            file_id: If provided, clear only this file's cache. Otherwise clear all.
        """
        if file_id:
            # Clear specific file
            keys_to_remove = [
                key for key, info in self.manifest.items()
                if info.get("file_id") == file_id
            ]
            for key in keys_to_remove:
                cache_dir = self.cache_dir / key
                if cache_dir.exists():
                    import shutil
                    shutil.rmtree(cache_dir)
                del self.manifest[key]
            self._save_manifest()
            logger.info(f"Cleared cache for {file_id}")
        else:
            # Clear all
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.manifest = {}
            self._save_manifest()
            logger.info("Cleared all cached embeddings")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total_size = 0
        for cache_dir in self.cache_dir.iterdir():
            if cache_dir.is_dir():
                for file in cache_dir.glob("*.npy"):
                    total_size += file.stat().st_size
        
        return {
            "num_cached_files": len(self.manifest),
            "total_cache_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }

