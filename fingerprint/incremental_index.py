"""Incremental FAISS index updates for new files."""
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import faiss
import pandas as pd

from .load_model import load_fingerprint_model
from .embed import segment_audio, extract_embeddings, normalize_embeddings
from .original_embeddings_cache import OriginalEmbeddingsCache
from .query_index import load_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_index_incremental(
    new_files_manifest_path: Path,
    existing_index_path: Path,
    fingerprint_config_path: Path,
    output_index_path: Path,
    index_config_path: Path = None
) -> Tuple[faiss.Index, Dict]:
    """
    Add new files to existing index incrementally.
    
    Args:
        new_files_manifest_path: Path to manifest CSV with new files
        existing_index_path: Path to existing FAISS index
        fingerprint_config_path: Path to fingerprint config YAML
        output_index_path: Path to save updated index
        index_config_path: Path to index config JSON (optional)
        
    Returns:
        Tuple of (updated_index, updated_metadata)
    """
    logger.info("=" * 60)
    logger.info("Incremental Index Update")
    logger.info("=" * 60)
    
    # Initialize cache
    cache = OriginalEmbeddingsCache()
    
    # Load model config
    model_config = load_fingerprint_model(fingerprint_config_path)
    
    # Load existing index
    logger.info(f"Loading existing index from {existing_index_path}")
    existing_index, existing_metadata = load_index(existing_index_path)
    existing_ids = existing_metadata.get("ids", [])
    logger.info(f"Existing index contains {existing_index.ntotal} vectors")
    
    # Load new files manifest
    new_files_df = pd.read_csv(new_files_manifest_path)
    logger.info(f"Processing {len(new_files_df)} new files")
    
    # Process new files
    new_embeddings = []
    new_ids = []
    skipped_count = 0
    added_count = 0
    
    for _, row in new_files_df.iterrows():
        file_id = row["id"]
        file_path_str = row.get("file_path") or row.get("path")
        if not file_path_str:
            logger.warning(f"Row missing file_path: {row}")
            continue
        
        file_path = Path(file_path_str)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Check if already in index
        if any(f"{file_id}_seg" in id_str for id_str in existing_ids):
            logger.info(f"File {file_id} already in index, skipping")
            skipped_count += 1
            continue
        
        # Get or generate embeddings
        cached_embeddings, cached_segments = cache.get(file_id, file_path, model_config)
        
        if cached_embeddings is None:
            # Generate and cache
            logger.info(f"Generating embeddings for new file: {file_id}")
            overlap_ratio = model_config.get("overlap_ratio", None)
            segments = segment_audio(
                file_path,
                segment_length=model_config["segment_length"],
                sample_rate=model_config["sample_rate"],
                overlap_ratio=overlap_ratio
            )
            embeddings = extract_embeddings(
                segments,
                model_config,
                output_dir=None,
                save_embeddings=False
            )
            embeddings = normalize_embeddings(embeddings, method="l2")
            
            # Cache for future use
            cache.set(file_id, file_path, model_config, embeddings, segments)
        else:
            logger.info(f"Using cached embeddings for new file: {file_id}")
            embeddings = cached_embeddings
        
        # Add to new embeddings list
        for i, emb in enumerate(embeddings):
            seg_id = f"{file_id}_seg_{i:04d}"
            new_embeddings.append(emb)
            new_ids.append(seg_id)
            added_count += 1
    
    if not new_embeddings:
        logger.info("No new files to add to index")
        return existing_index, existing_metadata
    
    # Add to existing index
    logger.info(f"Adding {len(new_ids)} new vectors to index")
    new_embeddings_array = np.vstack(new_embeddings).astype(np.float32)
    
    # Check if index supports incremental addition
    if hasattr(existing_index, 'add'):
        existing_index.add(new_embeddings_array)
    else:
        logger.error("Index type does not support incremental addition")
        raise ValueError("Index type does not support incremental addition. Use rebuild_index instead.")
    
    # Update metadata
    updated_ids = existing_ids + new_ids
    updated_metadata = existing_metadata.copy()
    updated_metadata["ids"] = updated_ids
    updated_metadata["num_vectors"] = existing_index.ntotal
    updated_metadata["last_updated"] = time.time()
    
    # Save updated index
    output_index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(existing_index, str(output_index_path))
    logger.info(f"Saved updated index to {output_index_path}")
    
    # Save updated metadata
    metadata_path = output_index_path.with_suffix(".json")
    with open(metadata_path, 'w') as f:
        json.dump(updated_metadata, f, indent=2)
    logger.info(f"Saved updated metadata to {metadata_path}")
    
    logger.info(f"Incremental update complete: {added_count} vectors added, {skipped_count} files skipped")
    logger.info(f"Total vectors in index: {existing_index.ntotal}")
    
    return existing_index, updated_metadata


def rebuild_index_if_needed(
    files_manifest_path: Path,
    index_path: Path,
    fingerprint_config_path: Path,
    index_config_path: Path,
    force_rebuild: bool = False
) -> Path:
    """
    Rebuild index if needed, or use existing.
    
    Args:
        files_manifest_path: Path to files manifest
        index_path: Path to index file
        fingerprint_config_path: Path to fingerprint config
        index_config_path: Path to index config
        force_rebuild: Force rebuild even if index exists
        
    Returns:
        Path to index file (existing or newly built)
    """
    if force_rebuild or not index_path.exists():
        logger.info("Building new index...")
        # This would call the index building logic from run_experiment.py
        # For now, return the path - actual rebuild should be done via run_experiment
        return index_path
    else:
        logger.info(f"Using existing index: {index_path}")
        return index_path

