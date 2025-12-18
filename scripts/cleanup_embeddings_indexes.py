#!/usr/bin/env python3
"""
Cleanup script to remove embeddings, indexes, and cache files.
This allows for a fresh regeneration of all data.
"""
import argparse
import logging
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def remove_directory(path: Path, description: str) -> bool:
    """Remove a directory if it exists."""
    path = Path(path)
    if path.exists():
        try:
            shutil.rmtree(path)
            logger.info(f"✅ Removed {description}: {path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to remove {description} ({path}): {e}")
            return False
    else:
        logger.debug(f"⏭️  {description} does not exist: {path}")
        return False


def remove_file(path: Path, description: str) -> bool:
    """Remove a file if it exists."""
    path = Path(path)
    if path.exists():
        try:
            path.unlink()
            logger.info(f"✅ Removed {description}: {path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to remove {description} ({path}): {e}")
            return False
    else:
        logger.debug(f"⏭️  {description} does not exist: {path}")
        return False


def cleanup_all(
    remove_indexes: bool = True,
    remove_cache: bool = True,
    remove_embeddings: bool = True,
    remove_transformed: bool = False,
    remove_transform_manifest: bool = False
):
    """
    Remove embeddings, indexes, and cache files.
    
    Args:
        remove_indexes: Remove indexes directory
        remove_cache: Remove embeddings cache directory
        remove_embeddings: Remove embeddings directory (if exists)
        remove_transformed: Remove transformed audio files (optional)
        remove_transform_manifest: Remove transform manifest CSV (optional)
    """
    project_root = Path(__file__).parent.parent
    
    logger.info("=" * 70)
    logger.info("🧹 Starting cleanup of embeddings, indexes, and cache files")
    logger.info("=" * 70)
    
    removed_count = 0
    
    # Remove indexes directory
    if remove_indexes:
        indexes_dir = project_root / "indexes"
        if remove_directory(indexes_dir, "Indexes directory"):
            removed_count += 1
    
    # Remove embeddings cache
    if remove_cache:
        cache_dir = project_root / "data" / "cache" / "original_embeddings"
        if remove_directory(cache_dir, "Embeddings cache"):
            removed_count += 1
        
        # Also remove parent cache directory if empty
        cache_parent = project_root / "data" / "cache"
        if cache_parent.exists() and not any(cache_parent.iterdir()):
            remove_directory(cache_parent, "Empty cache directory")
    
    # Remove embeddings directory (if exists)
    if remove_embeddings:
        embeddings_dir = project_root / "embeddings"
        if remove_directory(embeddings_dir, "Embeddings directory"):
            removed_count += 1
    
    # Optional: Remove transformed files
    if remove_transformed:
        transformed_dir = project_root / "data" / "transformed"
        if remove_directory(transformed_dir, "Transformed files directory"):
            removed_count += 1
    
    # Optional: Remove transform manifest
    if remove_transform_manifest:
        transform_manifest = project_root / "data" / "manifests" / "transform_manifest.csv"
        if remove_file(transform_manifest, "Transform manifest"):
            removed_count += 1
    
    logger.info("=" * 70)
    logger.info(f"✅ Cleanup complete! Removed {removed_count} items")
    logger.info("=" * 70)
    
    logger.info("\n📝 Next steps to regenerate:")
    logger.info("   1. Create/update manifest:")
    logger.info("      python scripts/setup_audio_dataset.py")
    logger.info("   2. Ingest original files:")
    logger.info("      python data_ingest.py --manifest data/manifests/audio_dataset_manifest.csv --output data")
    logger.info("   3. Run full experiment (regenerates everything):")
    logger.info("      python run_experiment.py --config config/test_matrix.yaml --originals data/manifests/files_manifest.csv")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup embeddings, indexes, and cache files for fresh regeneration"
    )
    parser.add_argument(
        "--no-indexes",
        action="store_true",
        help="Keep indexes directory (don't remove)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Keep embeddings cache (don't remove)"
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Keep embeddings directory (don't remove)"
    )
    parser.add_argument(
        "--remove-transformed",
        action="store_true",
        help="Also remove transformed audio files"
    )
    parser.add_argument(
        "--remove-transform-manifest",
        action="store_true",
        help="Also remove transform manifest CSV"
    )
    
    args = parser.parse_args()
    
    cleanup_all(
        remove_indexes=not args.no_indexes,
        remove_cache=not args.no_cache,
        remove_embeddings=not args.no_embeddings,
        remove_transformed=args.remove_transformed,
        remove_transform_manifest=args.remove_transform_manifest
    )


if __name__ == "__main__":
    main()
