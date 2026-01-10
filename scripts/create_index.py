#!/usr/bin/env python3
"""
Script to create or update audio fingerprint index.

This script can:
- Create a new index from audio files
- Update an existing index with new files
- Accept either a manifest CSV or a directory of audio files
- Use cached embeddings for faster processing
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
import faiss
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from functools import partial

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fingerprint.load_model import load_fingerprint_model
from fingerprint.embed import segment_audio, extract_embeddings, normalize_embeddings
from fingerprint.original_embeddings_cache import OriginalEmbeddingsCache
from fingerprint.query_index import build_index, load_index

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_manifest_from_directory(audio_dir: Path, output_csv: Path) -> pd.DataFrame:
    """
    Create manifest CSV from audio files in directory.
    
    Args:
        audio_dir: Directory containing audio files
        output_csv: Path to save manifest CSV
        
    Returns:
        DataFrame with manifest data
    """
    audio_dir = Path(audio_dir)
    output_csv = Path(output_csv)
    
    # Find audio files
    audio_extensions = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac', '.wma']
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(audio_dir.glob(f"*{ext}"))
        audio_files.extend(audio_dir.glob(f"*{ext.upper()}"))
    
    if not audio_files:
        raise ValueError(f"No audio files found in {audio_dir}")
    
    # Create manifest records
    records = []
    for audio_file in sorted(audio_files):
        records.append({
            "id": audio_file.stem,
            "title": audio_file.stem.replace("_", " ").title(),
            "file_path": str(audio_file.absolute()),
            "genre": "unknown"
        })
    
    df = pd.DataFrame(records)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    
    logger.info(f"Created manifest with {len(records)} files: {output_csv}")
    return df


def _process_single_file(
    row_data: Tuple[int, Dict, Dict, Optional[Path], Optional[int], OriginalEmbeddingsCache]
) -> Tuple[bool, str, Optional[List[np.ndarray]], Optional[List[str]], Dict]:
    """
    Process a single file (for parallel execution).
    
    Args:
        row_data: Tuple of (idx, row_dict, model_config, embeddings_dir, batch_size, cache)
    
    Returns:
        Tuple of (success: bool, file_id, embeddings, seg_ids, stats_dict)
    """
    # Import here for thread safety (module-level imports should work, but explicit is better)
    from fingerprint.embed import segment_audio, extract_embeddings, normalize_embeddings
    
    idx, row, model_config, embeddings_dir, batch_size, cache = row_data
    
    file_id = row["id"]
    file_path_str = row.get("file_path") or row.get("path") or row.get("url")
    
    stats = {"cached": 0, "generated": 0, "error": None}
    
    try:
        if not file_path_str:
            stats["error"] = f"Missing file_path/path/url"
            return (False, file_id, None, None, stats)
        
        file_path = Path(file_path_str)
        
        # Resolve relative paths
        if not file_path.is_absolute():
            potential_path = Path.cwd() / file_path
            if potential_path.exists():
                file_path = potential_path
        
        if not file_path.exists():
            stats["error"] = f"File not found: {file_path}"
            return (False, file_id, None, None, stats)
        
        # Check cache first
        cached_embeddings, cached_segments = cache.get(file_id, file_path, model_config)
        
        if cached_embeddings is not None:
            # Use cached embeddings
            embeddings = cached_embeddings
            stats["cached"] = 1
        else:
            # Generate new embeddings
            overlap_ratio = model_config.get("overlap_ratio", None)
            segments = segment_audio(
                file_path,
                segment_length=model_config["segment_length"],
                sample_rate=model_config["sample_rate"],
                overlap_ratio=overlap_ratio
            )
            
            output_dir = None
            if embeddings_dir:
                output_dir = embeddings_dir / file_id
            
            # Use optimized batch size (default: 64 for GPU, 32 for CPU)
            if batch_size is None:
                # Auto-detect optimal batch size
                try:
                    import torch
                    if torch.cuda.is_available():
                        batch_size = 64  # Larger batch for GPU
                    else:
                        batch_size = 32
                except ImportError:
                    batch_size = 32
            
            embeddings = extract_embeddings(
                segments,
                model_config,
                output_dir=output_dir,
                save_embeddings=output_dir is not None,
                batch_size=batch_size
            )
            
            # Normalize
            embeddings = normalize_embeddings(embeddings, method="l2")
            
            # Cache for future use
            cache.set(file_id, file_path, model_config, embeddings, segments)
            stats["generated"] = 1
        
        # Create segment IDs
        seg_ids = [f"{file_id}_seg_{i:04d}" for i in range(len(embeddings))]
        
        return (True, file_id, embeddings, seg_ids, stats)
        
    except Exception as e:
        stats["error"] = str(e)
        logger.error(f"Failed to process {file_id}: {e}", exc_info=True)
        return (False, file_id, None, None, stats)


def process_files_for_index(
    files_df: pd.DataFrame,
    model_config: Dict,
    cache: OriginalEmbeddingsCache,
    embeddings_dir: Optional[Path] = None,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
    use_parallel: bool = True
) -> tuple[List[np.ndarray], List[str], Dict[str, int]]:
    """
    Process files and generate embeddings for index (OPTIMIZED WITH PARALLEL PROCESSING).
    
    Args:
        files_df: DataFrame with file information (must have 'id' and 'file_path' columns)
        model_config: Model configuration dictionary (with loaded model)
        cache: Embeddings cache instance
        embeddings_dir: Optional directory to save embeddings
        max_workers: Number of parallel workers (None = auto-detect)
        batch_size: Batch size for segment processing (None = auto-detect, 64 for GPU, 32 for CPU)
        use_parallel: Whether to use parallel processing (default: True)
        
    Returns:
        Tuple of (embeddings_list, ids_list, stats_dict)
    """
    all_embeddings = []
    all_ids = []
    stats = {
        "total_files": len(files_df),
        "cached": 0,
        "generated": 0,
        "failed": 0,
        "total_segments": 0
    }
    
    logger.info(f"Processing {stats['total_files']} files...")
    
    # Prepare file data for processing
    file_data = []
    for idx, row in files_df.iterrows():
        file_data.append((idx, row.to_dict(), model_config, embeddings_dir, batch_size, cache))
    
    if not file_data:
        return all_embeddings, all_ids, stats
    
    # Determine optimal number of workers
    if max_workers is None:
        # For GPU: Use fewer workers (4-6) to avoid GPU memory contention
        # For CPU: Use more workers (CPU count - 1)
        try:
            import torch
            if torch.cuda.is_available():
                # GPU available: use fewer workers to share GPU efficiently
                max_workers = min(4, len(file_data), multiprocessing.cpu_count())
                logger.info(f"GPU detected: using {max_workers} workers for optimal GPU utilization")
            else:
                # CPU only: use more workers
                max_workers = min(8, len(file_data), multiprocessing.cpu_count() - 1)
                logger.info(f"CPU only: using {max_workers} workers")
        except ImportError:
            max_workers = min(4, len(file_data), multiprocessing.cpu_count())
    
    # Auto-detect batch size if not specified
    if batch_size is None:
        try:
            import torch
            if torch.cuda.is_available():
                batch_size = 64  # Larger batch for GPU
            else:
                batch_size = 32
        except ImportError:
            batch_size = 32
    
    logger.info(f"Configuration: {max_workers} workers, batch_size={batch_size}")
    
    # Process files in parallel using ThreadPoolExecutor (better for GPU sharing)
    if use_parallel and len(file_data) > 1 and max_workers > 1:
        logger.info(f"Using parallel processing with {max_workers} workers...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(_process_single_file, data): i 
                      for i, data in enumerate(file_data)}
            
            completed = 0
            for future in as_completed(futures):
                idx = futures[future]
                completed += 1
                
                try:
                    success, file_id, embeddings, seg_ids, file_stats = future.result()
                    
                    if success and embeddings is not None:
                        all_embeddings.extend(embeddings)
                        all_ids.extend(seg_ids)
                        stats["total_segments"] += len(embeddings)
                        
                        stats["cached"] += file_stats.get("cached", 0)
                        stats["generated"] += file_stats.get("generated", 0)
                        
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (stats["total_files"] - completed) / rate if rate > 0 else 0
                        
                        logger.info(
                            f"[{completed}/{stats['total_files']}] "
                            f"Processed {file_id} ({len(embeddings)} segments) | "
                            f"Rate: {rate:.2f} files/sec | ETA: {eta:.0f}s"
                        )
                    else:
                        stats["failed"] += 1
                        error_msg = file_stats.get("error", "Unknown error")
                        logger.error(f"Failed to process {file_id}: {error_msg}")
                        
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"Error processing file {idx}: {e}", exc_info=True)
        
        total_time = time.time() - start_time
        logger.info(f"Parallel processing completed in {total_time:.1f}s ({stats['total_files']/total_time:.2f} files/sec)")
        
    else:
        # SEQUENTIAL PROCESSING (fallback)
        logger.info("Using sequential processing...")
        start_time = time.time()
        
        for idx, row in files_df.iterrows():
            file_id = row["id"]
            file_path_str = row.get("file_path") or row.get("path") or row.get("url")
            
            if not file_path_str:
                logger.error(f"Row {idx} missing file_path/path/url. Available columns: {list(row.index)}")
                stats["failed"] += 1
                continue
            
            file_path = Path(file_path_str)
            
            # Resolve relative paths
            if not file_path.is_absolute():
                potential_path = Path.cwd() / file_path
                if potential_path.exists():
                    file_path = potential_path
                elif not file_path.exists():
                    logger.error(f"File not found: {file_path_str}")
                    stats["failed"] += 1
                    continue
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                stats["failed"] += 1
                continue
            
            try:
                # Check cache first
                cached_embeddings, cached_segments = cache.get(file_id, file_path, model_config)
                
                if cached_embeddings is not None:
                    # Use cached embeddings
                    logger.info(f"[{idx+1}/{stats['total_files']}] Using cached embeddings for {file_id} ({len(cached_embeddings)} segments)")
                    embeddings = cached_embeddings
                    stats["cached"] += 1
                else:
                    # Generate new embeddings
                    logger.info(f"[{idx+1}/{stats['total_files']}] Generating embeddings for {file_id} -> {file_path.name}")
                    
                    overlap_ratio = model_config.get("overlap_ratio", None)
                    segments = segment_audio(
                        file_path,
                        segment_length=model_config["segment_length"],
                        sample_rate=model_config["sample_rate"],
                        overlap_ratio=overlap_ratio
                    )
                    
                    output_dir = None
                    if embeddings_dir:
                        output_dir = embeddings_dir / file_id
                    
                    embeddings = extract_embeddings(
                        segments,
                        model_config,
                        output_dir=output_dir,
                        save_embeddings=output_dir is not None,
                        batch_size=batch_size
                    )
                    
                    # Normalize
                    embeddings = normalize_embeddings(embeddings, method="l2")
                    
                    # Cache for future use
                    cache.set(file_id, file_path, model_config, embeddings, segments)
                    stats["generated"] += 1
                
                # Store with segment IDs
                for i, emb in enumerate(embeddings):
                    seg_id = f"{file_id}_seg_{i:04d}"
                    all_embeddings.append(emb)
                    all_ids.append(seg_id)
                    stats["total_segments"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process {file_id}: {e}", exc_info=True)
                stats["failed"] += 1
                continue
        
        total_time = time.time() - start_time
        logger.info(f"Sequential processing completed in {total_time:.1f}s ({stats['total_files']/total_time:.2f} files/sec)")
    
    return all_embeddings, all_ids, stats


def create_or_update_index(
    files_input: Path,
    output_index: Path,
    fingerprint_config: Path = Path("config/fingerprint_v1.yaml"),
    index_config: Path = Path("config/index_config.json"),
    existing_index: Optional[Path] = None,
    force_rebuild: bool = False,
    embeddings_dir: Optional[Path] = None,
    create_manifest: bool = False,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
    use_parallel: bool = True
) -> tuple[faiss.Index, Dict]:
    """
    Create or update audio fingerprint index.
    
    Args:
        files_input: Path to manifest CSV or directory of audio files
        output_index: Path to save index
        fingerprint_config: Path to fingerprint config YAML
        index_config: Path to index config JSON
        existing_index: Path to existing index (for incremental update)
        force_rebuild: Force rebuild even if index exists
        embeddings_dir: Optional directory to save embeddings
        create_manifest: If True and files_input is a directory, create manifest CSV
        
    Returns:
        Tuple of (index, metadata)
    """
    logger.info("=" * 70)
    logger.info("Audio Fingerprint Index Creation/Update")
    logger.info("=" * 70)
    
    # Validate inputs
    files_input = Path(files_input)
    output_index = Path(output_index)
    fingerprint_config = Path(fingerprint_config)
    index_config = Path(index_config)
    
    if not fingerprint_config.exists():
        raise FileNotFoundError(f"Fingerprint config not found: {fingerprint_config}")
    
    if not index_config.exists():
        raise FileNotFoundError(f"Index config not found: {index_config}")
    
    # Load configurations
    logger.info(f"Loading fingerprint config from {fingerprint_config}")
    model_config = load_fingerprint_model(fingerprint_config)
    
    logger.info(f"Loading index config from {index_config}")
    with open(index_config, 'r') as f:
        index_config_dict = json.load(f)
    
    # Initialize cache
    cache = OriginalEmbeddingsCache()
    cache_stats = cache.get_cache_stats()
    logger.info(f"Cache stats: {cache_stats['num_cached_files']} files cached ({cache_stats['total_cache_size_mb']:.2f} MB)")
    
    # Load or create manifest
    if files_input.is_dir():
        # Directory of audio files
        logger.info(f"Input is directory: {files_input}")
        if create_manifest:
            manifest_path = files_input.parent / f"{files_input.name}_manifest.csv"
            files_df = create_manifest_from_directory(files_input, manifest_path)
            logger.info(f"Created manifest: {manifest_path}")
        else:
            # Create temporary manifest in memory
            files_df = create_manifest_from_directory(files_input, Path("/tmp/temp_manifest.csv"))
    elif files_input.suffix.lower() == '.csv':
        # Manifest CSV
        logger.info(f"Loading manifest from {files_input}")
        files_df = pd.read_csv(files_input)
        logger.info(f"Loaded manifest with {len(files_df)} files")
    else:
        raise ValueError(f"Invalid input: {files_input}. Must be a directory or CSV file.")
    
    # Validate manifest columns
    required_columns = ["id"]
    if "file_path" not in files_df.columns and "path" not in files_df.columns and "url" not in files_df.columns:
        raise ValueError("Manifest must have 'file_path', 'path', or 'url' column")
    
    # Check for existing index
    existing_index_path = existing_index or output_index
    existing_index_obj = None
    existing_metadata = None
    existing_file_ids = set()
    
    if existing_index_path.exists() and not force_rebuild:
        try:
            logger.info(f"Found existing index: {existing_index_path}")
            existing_index_obj, existing_metadata = load_index(existing_index_path)
            existing_ids = existing_metadata.get("ids", [])
            # Extract file IDs from segment IDs (format: "file_id_seg_0000")
            existing_file_ids = {id_str.split("_seg_")[0] for id_str in existing_ids if "_seg_" in id_str}
            logger.info(f"Existing index contains {existing_index_obj.ntotal} vectors from {len(existing_file_ids)} files")
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}, will create new index")
            existing_index_obj = None
    
    # Determine which files need to be processed
    current_file_ids = set(files_df["id"].tolist())
    files_to_index_rows = []
    files_already_indexed = []
    
    if existing_index_obj is not None and not force_rebuild:
        # Check which files are already indexed
        for _, row in files_df.iterrows():
            file_id = row["id"]
            if file_id in existing_file_ids:
                files_already_indexed.append(file_id)
            else:
                files_to_index_rows.append(row)
    else:
        # No existing index or force rebuild - process all files
        files_to_index_rows = [row for _, row in files_df.iterrows()]
    
    logger.info(f"Files already in index: {len(files_already_indexed)}")
    logger.info(f"Files to add: {len(files_to_index_rows)}")
    
    if len(files_to_index_rows) == 0:
        logger.info("✓ All files already indexed. No update needed.")
        return existing_index_obj, existing_metadata
    
    # Process files
    files_to_index_df = pd.DataFrame(files_to_index_rows)
    
    all_embeddings, all_ids, stats = process_files_for_index(
        files_to_index_df,
        model_config,
        cache,
        embeddings_dir,
        max_workers=max_workers,
        batch_size=batch_size,
        use_parallel=use_parallel
    )
    
    logger.info("=" * 70)
    logger.info("Processing Summary:")
    logger.info(f"  Total files: {stats['total_files']}")
    logger.info(f"  Cached: {stats['cached']}")
    logger.info(f"  Generated: {stats['generated']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  Total segments: {stats['total_segments']}")
    logger.info("=" * 70)
    
    if not all_embeddings:
        raise ValueError("No embeddings generated. Check file paths and format.")
    
    # Convert to numpy array
    embeddings_array = np.vstack(all_embeddings).astype(np.float32)
    logger.info(f"Embeddings array shape: {embeddings_array.shape}")
    
    # Build or update index
    if existing_index_obj is not None and not force_rebuild:
        # Incremental update
        logger.info("Updating existing index incrementally...")
        
        # Check if index supports incremental addition
        if not hasattr(existing_index_obj, 'add'):
            raise ValueError("Index type does not support incremental addition. Use --force-rebuild to rebuild.")
        
        existing_index_obj.add(embeddings_array)
        
        # Update metadata
        updated_ids = existing_metadata.get("ids", []) + all_ids
        updated_metadata = existing_metadata.copy()
        updated_metadata["ids"] = updated_ids
        updated_metadata["num_vectors"] = existing_index_obj.ntotal
        updated_metadata["last_updated"] = time.time()
        
        logger.info(f"Added {len(all_ids)} new vectors to existing index")
        logger.info(f"Total vectors in index: {existing_index_obj.ntotal}")
        
        index_obj = existing_index_obj
        metadata = updated_metadata
    else:
        # Build new index
        logger.info("Building new index...")
        
        index_obj = build_index(
            embeddings=embeddings_array,
            ids=all_ids,
            index_path=output_index,
            index_config=index_config_dict,
            save_metadata=True
        )
        
        # Load metadata to return
        metadata_path = output_index.with_suffix(".json")
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"Built new index with {len(all_ids)} vectors")
    
    # Save index
    output_index.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index_obj, str(output_index))
    logger.info(f"Saved index to {output_index}")
    
    # Save metadata
    metadata_path = output_index.with_suffix(".json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"Saved metadata to {metadata_path}")
    
    # Final summary
    logger.info("=" * 70)
    logger.info("Index Creation/Update Complete!")
    logger.info(f"  Index path: {output_index}")
    logger.info(f"  Total vectors: {index_obj.ntotal}")
    logger.info(f"  Total files indexed: {len(existing_file_ids) + len(files_to_index_rows)}")
    logger.info("=" * 70)
    
    return index_obj, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Create or update audio fingerprint index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create index from directory of audio files
  python scripts/create_index.py --input data/originals --output indexes/faiss_index.bin
  
  # Create index from manifest CSV
  python scripts/create_index.py --input data/manifests/files_manifest.csv --output indexes/faiss_index.bin
  
  # Update existing index with new files
  python scripts/create_index.py --input data/manifests/new_files.csv --output indexes/faiss_index.bin --existing-index indexes/faiss_index.bin
  
  # Force rebuild index
  python scripts/create_index.py --input data/originals --output indexes/faiss_index.bin --force-rebuild
        """
    )
    
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to manifest CSV file or directory containing audio files"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to save index file (e.g., indexes/faiss_index.bin)"
    )
    
    parser.add_argument(
        "--fingerprint-config",
        type=Path,
        default=Path("config/fingerprint_v1.yaml"),
        help="Path to fingerprint configuration YAML (default: config/fingerprint_v1.yaml)"
    )
    
    parser.add_argument(
        "--index-config",
        type=Path,
        default=Path("config/index_config.json"),
        help="Path to index configuration JSON (default: config/index_config.json)"
    )
    
    parser.add_argument(
        "--existing-index",
        type=Path,
        help="Path to existing index (for incremental update). If not provided, uses --output path."
    )
    
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild index even if it exists"
    )
    
    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        help="Optional directory to save embeddings (for debugging)"
    )
    
    parser.add_argument(
        "--create-manifest",
        action="store_true",
        help="If input is a directory, create a manifest CSV file"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: auto-detect, 4 for GPU, CPU_count-1 for CPU)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for segment processing (default: 64 for GPU, 32 for CPU)"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (use sequential)"
    )
    
    args = parser.parse_args()
    
    try:
        index, metadata = create_or_update_index(
            files_input=args.input,
            output_index=args.output,
            fingerprint_config=args.fingerprint_config,
            index_config=args.index_config,
            existing_index=args.existing_index,
            force_rebuild=args.force_rebuild,
            embeddings_dir=args.embeddings_dir,
            create_manifest=args.create_manifest,
            max_workers=args.workers,
            batch_size=args.batch_size,
            use_parallel=not args.no_parallel
        )
        
        logger.info("✓ Success!")
        return 0
        
    except Exception as e:
        logger.error(f"✗ Failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
