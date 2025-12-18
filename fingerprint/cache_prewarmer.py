"""Pre-warm cache for original embeddings to improve query performance.

PHASE 1 OPTIMIZATION: This module pre-warms the cache for original files
before queries, ensuring TIER 1 (direct similarity) activates more often.
This provides faster and more accurate similarity scores.
"""
import logging
from pathlib import Path
from typing import Optional, List
import pandas as pd
from .original_embeddings_cache import OriginalEmbeddingsCache

logger = logging.getLogger(__name__)


def prewarm_cache_for_original(
    expected_orig_id: str,
    files_manifest_path: Optional[Path],
    model_config: dict
) -> bool:
    """
    Pre-warm cache for a specific original file before query.
    
    This ensures TIER 1 (direct similarity) activates more often,
    providing faster and more accurate similarity scores.
    
    Args:
        expected_orig_id: Expected original file ID
        files_manifest_path: Path to files manifest CSV
        model_config: Model configuration dictionary
        
    Returns:
        True if cache was successfully pre-warmed, False otherwise
    """
    if not files_manifest_path or not files_manifest_path.exists():
        logger.debug(f"Cannot pre-warm cache: manifest not found")
        return False
    
    try:
        cache = OriginalEmbeddingsCache()
        files_df = pd.read_csv(files_manifest_path)
        orig_row = files_df[files_df["id"] == expected_orig_id]
        
        if orig_row.empty:
            logger.debug(f"Original ID {expected_orig_id} not found in manifest")
            return False
        
        orig_file_path_str = orig_row.iloc[0].get("file_path") or orig_row.iloc[0].get("path")
        if not orig_file_path_str:
            logger.debug(f"No file path found for {expected_orig_id}")
            return False
        
        orig_file_path = Path(orig_file_path_str)
        if not orig_file_path.is_absolute():
            # Try resolving relative paths
            for base_dir in [Path("data/originals"), Path("data/test_audio"), Path.cwd()]:
                potential_path = base_dir / orig_file_path
                if potential_path.exists():
                    orig_file_path = potential_path
                    break
        
        if not orig_file_path.exists():
            logger.debug(f"Original file not found: {orig_file_path}")
            return False
        
        # Pre-warm cache by getting embeddings (will cache if not already cached)
        embeddings, segments = cache.get(expected_orig_id, orig_file_path, model_config)
        
        if embeddings is not None:
            logger.debug(f"PHASE 1: Successfully pre-warmed cache for {expected_orig_id} ({len(embeddings)} segments)")
            return True
        else:
            logger.debug(f"PHASE 1: Cache pre-warming returned None for {expected_orig_id} (will be loaded on-demand)")
            return False
            
    except Exception as e:
        logger.debug(f"PHASE 1: Failed to pre-warm cache for {expected_orig_id}: {e}")
        return False


def prewarm_all_originals(
    files_manifest_path: Path,
    model_config: dict,
    limit: Optional[int] = None
) -> int:
    """
    Pre-warm cache for all original files in manifest.
    
    This can be called at startup to cache all originals,
    eliminating cache misses during queries.
    
    Args:
        files_manifest_path: Path to files manifest CSV
        model_config: Model configuration dictionary
        limit: Optional limit on number of files to pre-warm (None = all)
        
    Returns:
        Number of files successfully pre-warmed
    """
    if not files_manifest_path.exists():
        logger.warning(f"PHASE 1: Manifest not found: {files_manifest_path}")
        return 0
    
    try:
        files_df = pd.read_csv(files_manifest_path)
        total_files = len(files_df)
        
        if limit:
            files_df = files_df.head(limit)
        
        logger.info(f"PHASE 1: Pre-warming cache for {len(files_df)}/{total_files} original files...")
        
        cache = OriginalEmbeddingsCache()
        prewarmed_count = 0
        
        for idx, row in files_df.iterrows():
            file_id = row.get("id")
            file_path_str = row.get("file_path") or row.get("path")
            
            if not file_id or not file_path_str:
                continue
            
            file_path = Path(file_path_str)
            if not file_path.is_absolute():
                for base_dir in [Path("data/originals"), Path("data/test_audio"), Path.cwd()]:
                    potential_path = base_dir / file_path
                    if potential_path.exists():
                        file_path = potential_path
                        break
            
            if file_path.exists():
                try:
                    embeddings, _ = cache.get(file_id, file_path, model_config)
                    if embeddings is not None:
                        prewarmed_count += 1
                        if (prewarmed_count % 10) == 0:
                            logger.info(f"PHASE 1: Pre-warmed {prewarmed_count}/{len(files_df)} files...")
                except Exception as e:
                    logger.debug(f"PHASE 1: Failed to pre-warm {file_id}: {e}")
        
        logger.info(f"PHASE 1: Cache pre-warming complete: {prewarmed_count}/{len(files_df)} files cached")
        return prewarmed_count
        
    except Exception as e:
        logger.error(f"PHASE 1: Failed to pre-warm cache: {e}")
        return 0
