#!/usr/bin/env python3
"""
Setup audio dataset from URLs.
This script creates a manifest CSV from URLs and optionally downloads/processes them.
"""
import csv
import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_filename_from_url(url: str) -> str:
    """Extract filename from URL, handling URL encoding."""
    parsed = urlparse(url)
    filename = Path(parsed.path).name
    # Decode URL encoding
    filename = unquote(filename)
    # Clean up filename (remove special chars, keep extension)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename


def generate_track_id(url: str, index: int) -> str:
    """Generate a unique track ID from URL or index."""
    filename = extract_filename_from_url(url)
    # Remove extension
    base_name = Path(filename).stem
    # Clean up and create ID
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)[:50]  # Limit length
    if not clean_id or clean_id == '_':
        clean_id = f"track_{index:03d}"
    return clean_id


def generate_title_from_url(url: str) -> str:
    """Generate a readable title from URL filename."""
    filename = extract_filename_from_url(url)
    base_name = Path(filename).stem
    # Replace underscores and clean up
    title = base_name.replace('_', ' ').replace('%20', ' ')
    # Decode URL encoding
    title = unquote(title)
    return title


def create_manifest_from_urls(urls: list, output_path: Path, genre: str = "hip hop") -> None:
    """Create a CSV manifest file from a list of URLs."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Delete old CSV file if it exists
    if output_path.exists():
        output_path.unlink()
        logger.info(f"🗑️ Deleted old manifest: {output_path}")
    
    logger.info(f"Creating manifest with {len(urls)} URLs...")
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['id', 'title', 'url', 'genre'])
        
        # Write each URL as a row
        for idx, url in enumerate(urls, start=1):
            track_id = generate_track_id(url, idx)
            title = generate_title_from_url(url)
            
            writer.writerow([track_id, title, url, genre])
            logger.debug(f"Added: {track_id} - {title}")
    
    logger.info(f"✅ Manifest created: {output_path}")
    logger.info(f"   Total tracks: {len(urls)}")


def main():
    """Main function to set up audio dataset."""
    # URLs provided by the user
    urls = [
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1748918151770x614307980889769600/DonKody__SlowJam_Bbm_98.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BEATBOI_GEM_IN_EYE_CMIN_145/BEATBOI_GEM_IN_EYE_CMIN_145.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749612775939x780107747552101200/CLUE%21_DARK_TIMES_CMIN_140.wav",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747851031931x771872613364962000/Lil%20Uzi%20Vert%20x%20Nav%20Type%20beat%20back%20it%20up.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BENZMUZIK_WARZONE_DMAJ_140/BENZMUZIK_WARZONE_DMAJ_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/JACASIKK_CONTROL_ME_GMin_150/JACASIKK_CONTROL_ME_GMin_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MXDWAVE_BACK_IT_UP_Ebm_145/MXDWAVE_BACK_IT_UP_Ebm_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_CHANGE_UR_LIFE_BMIN_160/NNOVAD_CHANGE_UR_LIFE_BMIN_160.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BREEZYBEATS_NOSUGAR_EMIN_140/BREEZYBEATS_NOSUGAR_EMIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/LUXXX_NOIRE_TRESPASS_BbMIN_155/LUXXX_NOIRE_TRESPASS_BbMIN_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DR3VMZ_CONTRACT_MONEY_C%23MIN_145/DR3VMZ_CONTRACT_MONEY_C%23MIN_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/KINGDAVIDHIPHOP_HIGHSANDLOWS_D%23MIN_150/KINGDAVIDHIPHOP_HIGHSANDLOWS_D%23MIN_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/OTTO_FLOWERS_AbMAJ_140/OTTO_FLOWERS_AbMAJ_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/Ottodidit_BLESS_FMAJ_145/Ottodidit_BLESS_FMAJ_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MANNYMANTWV_SMOOTH_CRIMINAL_AMIN_150/MANNYMANTWV_SMOOTH_CRIMINAL_AMIN_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DXRKMATTER_POISON_FMINOR_155/DXRKMATTER_POISON_FMINOR_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/RONALD_MANTHEI_DEADLY_C+MINOR_140/RONALD_MANTHEI_DEADLY_C+MINOR_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/TOKIOWAHL_BEAUTY_F%23MIN_145/TOKIOWAHL_BEAUTY_F%23MIN_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BENZMUZIK_ROLLING_STONES_Abm_150/BENZMUZIK_ROLLING_STONES_Abm_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/JACASIKK_PARIS_Dbm_140/JACASIKK_PARIS_Dbm_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MXDWAVE_HEARTS_Gbm_145/MXDWAVE_HEARTS_Gbm_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_CITY_VIBES_DMAJ_160/NNOVAD_CITY_VIBES_DMAJ_160.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BREEZYBEATS_HOUSTON_GMin_140/BREEZYBEATS_HOUSTON_GMin_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/LUXXX_NOIRE_BETTER_DAY_Ebm_155/LUXXX_NOIRE_BETTER_DAY_Ebm_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DR3VMZ_PLUGS_BMIN_145/DR3VMZ_PLUGS_BMIN_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/KINGDAVIDHIPHOP_COUSINS_C%23MIN_150/KINGDAVIDHIPHOP_COUSINS_C%23MIN_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/OTTO_STARGIRL_D%23MIN_140/OTTO_STARGIRL_D%23MIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/Ottodidit_HEARTLESS_AbMAJ_145/Ottodidit_HEARTLESS_AbMAJ_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MANNYMANTWV_Luminescent_FMAJ_150/MANNYMANTWV_Luminescent_FMAJ_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DXRKMATTER_EXHAUSTED_AMIN_155/DXRKMATTER_EXHAUSTED_AMIN_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/RONALD_MANTHEI_MY+PEOPLE_FMINOR_140/RONALD_MANTHEI_MY+PEOPLE_FMINOR_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/TOKIOWAHL_GOODCREDIT_C+MINOR_145/TOKIOWAHL_GOODCREDIT_C+MINOR_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BENZMUZIK_CONFIRM_F%23MIN_150/BENZMUZIK_CONFIRM_F%23MIN_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/JACASIKK_LOOPY_Abm_140/JACASIKK_LOOPY_Abm_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MXDWAVE_TRIM_Dbm_145/MXDWAVE_TRIM_Dbm_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_MONOXID_Gbm_160/NNOVAD_MONOXID_Gbm_160.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BREEZYBEATS_CRAZY_HOME_DMAJ_140/BREEZYBEATS_CRAZY_HOME_DMAJ_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/LUXXX_NOIRE_EFEMI_GMin_155/LUXXX_NOIRE_EFEMI_GMin_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DR3VMZ_WINE_Ebm_145/DR3VMZ_WINE_Ebm_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/KINGDAVIDHIPHOP_GUITAR_HEROS_BMIN_150/KINGDAVIDHIPHOP_GUITAR_HEROS_BMIN_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/OTTO_TEN_TOES_C%23MIN_140/OTTO_TEN_TOES_C%23MIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/Ottodidit_TRANQUILITY_D%23MIN_145/Ottodidit_TRANQUILITY_D%23MIN_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MANNYMANTWV_NO_LOVE_AbMAJ_150/MANNYMANTWV_NO_LOVE_AbMAJ_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DXRKMATTER_PAPER_ROUTE_FMAJ_155/DXRKMATTER_PAPER_ROUTE_FMAJ_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/RONALD_MANTHEI_PILLS_AMIN_140/RONALD_MANTHEI_PILLS_AMIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/TOKIOWAHL_FALLOUTS_FMINOR_145/TOKIOWAHL_FALLOUTS_FMINOR_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BENZMUZIK_WHO_HARDER_C+MINOR_150/BENZMUZIK_WHO_HARDER_C+MINOR_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/JACASIKK_STORM_F%23MIN_140/JACASIKK_STORM_F%23MIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MXDWAVE_HATING_ON_ME_Abm_145/MXDWAVE_HATING_ON_ME_Abm_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_THINK_OF_ME_Dbm_160/NNOVAD_THINK_OF_ME_Dbm_160.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BREEZYBEATS_CAT_IN_A_HAT_Gbm_140/BREEZYBEATS_CAT_IN_A_HAT_Gbm_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/LUXXX_NOIRE_JET_DMAJ_155/LUXXX_NOIRE_JET_DMAJ_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DR3VMZ_PROCESS_GMin_145/DR3VMZ_PROCESS_GMin_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/KINGDAVIDHIPHOP_PIANOMAN_Ebm_150/KINGDAVIDHIPHOP_PIANOMAN_Ebm_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/OTTO_ORANGES_BMIN_140/OTTO_ORANGES_BMIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/Ottodidit_STALK_EM_C%23MIN_145/Ottodidit_STALK_EM_C%23MIN_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MANNYMANTWV_DASH_D%23MIN_150/MANNYMANTWV_DASH_D%23MIN_150.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DXRKMATTER_NICKED_AbMAJ_155/DXRKMATTER_NICKED_AbMAJ_155.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/RONALD_MANTHEI_BlindingLights_FMAJ_140/RONALD_MANTHEI_BlindingLights_FMAJ_140.mp3",
    ]
    
    # Project root
    project_root = Path(__file__).parent.parent
    manifest_path = project_root / "data" / "manifests" / "audio_dataset_manifest.csv"
    
    # Create manifest
    create_manifest_from_urls(urls, manifest_path, genre="hip hop")
    
    logger.info("\n" + "="*70)
    logger.info("✅ Manifest created successfully!")
    logger.info("="*70)
    logger.info(f"\n📁 Manifest location: {manifest_path}")
    logger.info(f"📊 Total tracks: {len(urls)}")
    logger.info("\n📝 Next steps:")
    logger.info("   1. Review the manifest file")
    logger.info("   2. Run data ingestion:")
    logger.info(f"      python data_ingest.py --manifest {manifest_path} --output data")
    logger.info("   3. After ingestion, update the main manifest:")
    logger.info(f"      Copy data/files_manifest.csv to data/manifests/files_manifest.csv")
    logger.info("\n" + "="*70)


if __name__ == "__main__":
    main()

