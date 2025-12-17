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
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749612775939x780107747552101200/CLUE%21_DARK_TIMES_CMIN_140.wav",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747851031931x771872613364962000/Lil%20Uzi%20Vert%20x%20Nav%20Type%20beat%20back%20it%20up.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749612400355x175279102581866980/CLUE%21_AINT_GON_TELL_YA_TWICE_GMIN_140.wav",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745806805744x223599312519719970/DonKody_Back_It_Up_GMin_100.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1756822094119x481931140740412540/andygrvcia_onna_leash_Ebm_99.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1746623240873x894900354125553800/Gunna%20x%20Wheezy%20Type%20Beat%20overload.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745513376088x728755823795510000/Gunna%20x%20MetroBoomin%20Type%20Beat%20hard%20time%20ahead.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1746957198446x861865177965427800/Future%20x%20Travis%20Scott%20Type%20Beat%20last%20summer.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749329035421x457929540755830400/ThaRealShmoke_Another%20One_112Bpm.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747841878105x895315601689473300/DonKody__GoonsGoblins_Cm_101.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749265808200x244760233085663740/Nudaze_bm_144bpm%2012%3A21%3A23%20.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747443977369x387161607576075500/Chirpy%20Stroll.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747851235393x845632052956082800/Gunna%20x%20Turbo%20Type%20Beat%20knight.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747842505807x596342583796064100/DonKody__NostagicYoungMoney_Dm_150.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745577256859x543450879482659140/BENZMUZIK_ALL_MY_LIFE_AMIN_175.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1759102069478x336571846663648900/andygrvcia_Ex_Thing_Gbmin_122.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745600159329x899074353206163300/Rode%20126%20Amin%20jacasikk%20x%20wyddux.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745600372134x165832858659962430/Foster%20165%20Gmin%20jacasikk.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747311841998x649781600684352600/Playboi%20Carti%20x%20Future%20Type%20Beat%20drop%20top.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745948511665x826559856764833200/Future%20x%20MetroBoomin%20Type%20Beat%20exposure.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1746721171793x153425141656362100/Ottodidit_Changes_Bbmin_160.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1750100843751x859414109240482300/Blank_Eden_Outta%20here_Abm%20143bpm.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745962267857x425157157924546560/Gunna%20x%20Future%20x%20MetroBoomin%20Type%20Beat%20boss.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745615408298x879716015032071800/Lil%20Uzi%20Vert%20Type%20Beat%20kamera.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1758738105831x439308604648967360/andygrvcia_this_aint_love_Bbmin_167.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745853870594x615915047915744000/Young%20Thug%20x%20Pierre%20Bourne%20Type%20beat%20field%20trip.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1749266260598x207809512862219500/rain_f%23m_96bpm%20%5B%401kblondre%20%2B%20%40Nadda1k%5D%20.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1746206369971x201475828090782000/Sparkle%20155%20Emin%20jacasikk.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745614953051x946467505606539600/DonKody_Yellow_FbMin_75.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1760472850958x477367860354341440/Mista%20_Neva%20Play_.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1750167968278x735129027480165900/DonKody_BeatsNRhymes_Dbm_92.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1745814533656x277437984843410750/DonKody_Chamber_EbMin_92.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1747842399390x882536378534454700/DonKody__Motivated_G_149.mp3",
        "https://05e8f6d066ebc9c5b0e49ae1ae6cb5d4.cdn.bubble.io/f1748408359941x784154937638290300/DonKody__BlindingLights_Gbm_87.mp3",
        
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

