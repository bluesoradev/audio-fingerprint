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
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749612400355x175279102581866980/CLUE%21_AINT_GON_TELL_YA_TWICE_GMIN_140.wav",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MIXED+TAPE/BENZMUZIK_WARZONE_DMAJ_146/BENZMUZIK_WARZONE_DMAJ_146.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MIXED+TAPE/BENZMUZIK_CONTROL_ME_DMAJ_120/BENZMUZIK_CONTROL_ME_DMAJ_120.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745806805744x223599312519719970/DonKody_Back_It_Up_GMin_100.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1756822094119x481931140740412540/andygrvcia_onna_leash_Ebm_99.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_CHANGE_UR_LIFE_BMIN_152/NNOVAD_CHANGE_UR_LIFE_BMIN_152.wav",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MXDWAVE_NOSUGAR_EMIN_135/MXDWAVE_NOSUGAR_EMIN_135.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1746623240873x894900354125553800/Gunna%20x%20Wheezy%20Type%20Beat%20overload.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD+BULK+UPLOADS+3/NNOVAD_BLEVELAND_AMIN_126/NNOVAD_BLEVELAND_AMIN_126.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_TRESPASS_BbMIN_140/NNOVAD_TRESPASS_BbMIN_140.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/CANVA+BACK+UP/D4/MP3/D4_THE_DON_G%23MIN_162.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD_CONTRACT_MONEY_GMIN_144/NNOVAD_CONTRACT_MONEY_GMIN_144.wav",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/MXDWAVE_HIGHSANDLOWS_EMIN_136/MXDWAVE_HIGHSANDLOWS_EMIN_136.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/THAT+MODE/EDDIE_PRIEST_THE_ARCHIVE_BMIN_140/EDDIE_PRIEST_THE_ARCHIVE_Bm_140.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745513376088x728755823795510000/Gunna%20x%20MetroBoomin%20Type%20Beat%20hard%20time%20ahead.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1746957198446x861865177965427800/Future%20x%20Travis%20Scott%20Type%20Beat%20last%20summer.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749329035421x457929540755830400/ThaRealShmoke_Another%20One_112Bpm.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747841878105x895315601689473300/DonKody__GoonsGoblins_Cm_101.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/JACASIKK_FLOWERS_DMIN_115/JACASIKK_FLOWERS_DMIN_115.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/LOTUSVHS_BLESS_AMIN_145/LOTUSVHS_BLESS_AMIN_145.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/JUSTHANDMETHEKE_SMOOTH_CRIMINAL_GMAJ_134/JUSTHANDMETHEKE_SMOOTH_CRIMINAL_GMAJ_134.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/TOP+SPEED/PROD_BREEZYBEATS_POISON_FMINOR_164/PROD_BREEZYBEATS_POISON_FMINOR_164.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NVRHME+BEATS/LUXXX_NOIRE_D%23MIN_79/LUXXX_NOIRE_D%23MIN_79.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749265808200x244760233085663740/Nudaze_bm_144bpm%2012%3A21%3A23%20.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/NNOVAD+BULK+UPLOAD/NNOVAD_DEADLY_BMIN_80/NNOVAD_DEADLY_BMIN_80.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/DR3VMZ_BEAUTY_BMIN_95/DR3VMZ_BEAUTY_BMIN_95.wav",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747443977369x387161607576075500/Chirpy%20Stroll.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/BEAT+TAPE/BENZMUZIK_ROLLING_STONES_BbMIN_195/BENZMUZIK_ROLLING_STONES_BbMIN_195.mp3",
        "https://beatlibrary.s3.us-east-1.amazonaws.com/beats/LOTUSVHS_PARIS_EMIN_134/LOTUSVHS_PARIS_EMIN_134.mp3",
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

