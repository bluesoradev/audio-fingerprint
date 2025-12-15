#!/usr/bin/env python3
"""
Complete dataset setup: Create manifest, download, and process all audio files.
"""
import logging
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_ingest import ingest_manifest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main function to set up complete dataset."""
    project_root = Path(__file__).parent.parent
    
    # Step 1: Create manifest from URLs
    logger.info("="*70)
    logger.info("Step 1: Creating manifest from URLs...")
    logger.info("="*70)
    
    from scripts.setup_audio_dataset import main as create_manifest
    create_manifest()
    
    # Step 2: Download and process files
    logger.info("\n" + "="*70)
    logger.info("Step 2: Downloading and processing audio files...")
    logger.info("="*70)
    
    manifest_path = project_root / "data" / "manifests" / "audio_dataset_manifest.csv"
    output_dir = project_root / "data"
    
    if not manifest_path.exists():
        logger.error(f"❌ Manifest not found: {manifest_path}")
        logger.error("   Please run scripts/setup_audio_dataset.py first")
        return
    
    try:
        # Ingest manifest (downloads, normalizes, creates processed manifest)
        ingest_manifest(
            csv_path=manifest_path,
            output_dir=output_dir,
            normalize=True,
            sample_rate=44100
        )
        
        # Step 3: Copy processed manifest to the expected location
        logger.info("\n" + "="*70)
        logger.info("Step 3: Setting up manifest for experiments...")
        logger.info("="*70)
        
        processed_manifest = output_dir / "files_manifest.csv"
        target_manifest = output_dir / "manifests" / "files_manifest.csv"
        
        if processed_manifest.exists():
            target_manifest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(processed_manifest, target_manifest)
            logger.info(f"✅ Copied manifest to: {target_manifest}")
        else:
            logger.warning(f"⚠️  Processed manifest not found: {processed_manifest}")
        
        logger.info("\n" + "="*70)
        logger.info("✅ Dataset setup complete!")
        logger.info("="*70)
        logger.info(f"\n📁 Original files: {output_dir / 'originals'}")
        logger.info(f"📊 Processed manifest: {target_manifest}")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Verify files in data/originals/")
        logger.info("   2. Run Phase 1 test:")
        logger.info("      python run_experiment.py --config config/test_matrix_phase1.yaml --originals data/manifests/files_manifest.csv")
        logger.info("   3. Run Phase 2 test:")
        logger.info("      python run_experiment.py --config config/test_matrix_phase2.yaml --originals data/manifests/files_manifest.csv")
        logger.info("\n" + "="*70)
        
    except Exception as e:
        logger.error(f"❌ Error during ingestion: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

