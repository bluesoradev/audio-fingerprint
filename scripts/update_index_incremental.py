#!/usr/bin/env python3
"""Script to incrementally update FAISS index with new files."""
import argparse
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fingerprint.incremental_index import update_index_incremental

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Incrementally update FAISS index with new files"
    )
    parser.add_argument(
        "--new-files",
        type=Path,
        required=True,
        help="CSV manifest with new files to add"
    )
    parser.add_argument(
        "--existing-index",
        type=Path,
        required=True,
        help="Path to existing FAISS index"
    )
    parser.add_argument(
        "--output-index",
        type=Path,
        required=True,
        help="Path to save updated index"
    )
    parser.add_argument(
        "--fingerprint-config",
        type=Path,
        default=Path("config/fingerprint_v1.yaml"),
        help="Fingerprint configuration YAML"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.new_files.exists():
        logger.error(f"New files manifest not found: {args.new_files}")
        return 1
    
    if not args.existing_index.exists():
        logger.error(f"Existing index not found: {args.existing_index}")
        return 1
    
    if not args.fingerprint_config.exists():
        logger.error(f"Fingerprint config not found: {args.fingerprint_config}")
        return 1
    
    # Update index
    try:
        updated_index, updated_metadata = update_index_incremental(
            args.new_files,
            args.existing_index,
            args.fingerprint_config,
            args.output_index
        )
        
        logger.info("=" * 60)
        logger.info("Incremental update completed successfully!")
        logger.info(f"Updated index saved to: {args.output_index}")
        logger.info(f"Total vectors: {updated_index.ntotal}")
        logger.info("=" * 60)
        
        return 0
    except Exception as e:
        logger.error(f"Failed to update index: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

