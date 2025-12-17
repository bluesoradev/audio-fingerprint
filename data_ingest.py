"""Data ingestion and manifesting for robustness lab."""
import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import soundfile as sf
import librosa
import pandas as pd
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute hash of file."""
    hash_obj = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def download_track(url: str, dest: Path, timeout: int = 30) -> bool:
    """Download audio file from URL with proper headers to handle S3 access restrictions."""
    try:
        # Add headers to mimic browser request (helps with S3 access restrictions)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://beatlibrary.com/',  # Common referer for S3 buckets
            'Origin': 'https://beatlibrary.com',
            'Sec-Fetch-Dest': 'audio',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
        response.raise_for_status()
        
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(f"403 Forbidden: {url} - File may require authentication or is not publicly accessible")
            logger.warning(f"  This is common with S3 buckets that have access restrictions")
            logger.warning(f"  Options: 1) Contact provider for access, 2) Use local files, 3) Skip this file")
        elif e.response.status_code == 404:
            logger.warning(f"404 Not Found: {url} - File does not exist on server")
        else:
            logger.error(f"HTTP {e.response.status_code} error downloading {url}: {e}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading {url} (timeout={timeout}s)")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def normalize_audio(
    input_path: Path,
    out_path: Path,
    sample_rate: int = 44100,
    mono: bool = True,
    bitdepth: int = 16
) -> Dict:
    """Normalize audio: resample, convert to mono/stereo, ensure bitdepth."""
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=mono)
        
        # Get duration
        duration = len(y) / sample_rate
        
        # Save normalized audio
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use soundfile for saving (supports bitdepth via subtype)
        subtype_map = {
            16: "PCM_16",
            24: "PCM_24",
            32: "PCM_32"
        }
        subtype = subtype_map.get(bitdepth, "PCM_16")
        
        sf.write(str(out_path), y, sample_rate, subtype=subtype)
        
        return {
            "duration": duration,
            "sample_rate": sample_rate,
            "channels": 1 if mono else 2,
            "samples": len(y)
        }
    except Exception as e:
        logger.error(f"Failed to normalize {input_path}: {e}")
        raise


def ingest_manifest(
    csv_path: Path,
    output_dir: Path,
    normalize: bool = True,
    sample_rate: int = 44100
) -> pd.DataFrame:
    """
    Ingest manifest CSV and download/normalize audio files.
    
    Expected CSV columns: id, title, url (or path), genre (optional), ...
    """
    output_dir = Path(output_dir)
    originals_dir = output_dir / "originals"
    originals_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate manifest file exists and is not empty
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {csv_path}")
    
    # Check if file is empty
    file_size = csv_path.stat().st_size
    if file_size == 0:
        raise ValueError(
            f"Manifest file is empty: {csv_path}\n"
            f"The manifest file exists but contains no data.\n"
            f"This means no audio files were found or the file was corrupted.\n\n"
            f"Please ensure audio files exist in:\n"
            f"  - data/originals/\n"
            f"  - data/test_audio/\n\n"
            f"Or manually create a valid manifest with at least one audio file entry."
        )
    
    # Read manifest with exception handling
    try:
        df = pd.read_csv(csv_path)
        if len(df) == 0:
            raise ValueError(
                f"Manifest file has no data rows: {csv_path}\n"
                f"The file exists but contains only headers or is empty.\n"
                f"Please ensure the manifest has at least one row with audio file information."
            )
    except pd.errors.EmptyDataError as e:
        raise ValueError(
            f"Manifest file is empty or corrupted: {csv_path}\n"
            f"Cannot proceed with empty manifest.\n"
            f"Please ensure audio files exist and recreate the manifest."
        ) from e
    
    logger.info(f"Loaded manifest with {len(df)} entries from {csv_path}")
    logger.info(f"Manifest columns: {list(df.columns)}")
    
    results = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Ingesting files"):
        file_id = row.get("id", f"file_{idx}")
        title = row.get("title", f"Track {idx}")
        # Handle multiple column name variations: url, path, file_path
        url_or_path = row.get("url") or row.get("path") or row.get("file_path")
        
        if not url_or_path:
            logger.warning(f"Skipping {file_id}: no url, path, or file_path. Available columns: {list(row.index)}")
            continue
        
        # Determine if URL or local path
        source_path = Path(url_or_path)
        is_url = str(url_or_path).startswith(("http://", "https://"))
        
        # Download if URL, otherwise use local path
        if is_url:
            temp_file = originals_dir / f"{file_id}_temp.wav"
            if not download_track(url_or_path, temp_file):
                continue
            source_path = temp_file
        else:
            # Resolve relative paths relative to current working directory (should be project root)
            if not source_path.is_absolute():
                if not source_path.exists():
                    # Try resolving relative to current directory
                    potential_path = Path.cwd() / source_path
                    if potential_path.exists():
                        source_path = potential_path
                        logger.info(f"Resolved relative path: {url_or_path} -> {source_path}")
            
            if not source_path.exists():
                logger.warning(f"File not found: {source_path} (from manifest: {url_or_path})")
                continue
        
        # Normalize and save
        if normalize:
            output_file = originals_dir / f"{file_id}.wav"
            try:
                audio_info = normalize_audio(
                    source_path,
                    output_file,
                    sample_rate=sample_rate,
                    mono=True
                )
                
                # Compute checksum
                checksum = compute_file_hash(output_file)
                
                results.append({
                    "id": file_id,
                    "title": title,
                    "source_url": url_or_path if is_url else None,
                    "source_path": str(source_path) if not is_url else None,
                    "file_path": str(output_file),
                    "duration": audio_info["duration"],
                    "sample_rate": audio_info["sample_rate"],
                    "channels": audio_info["channels"],
                    "checksum": checksum,
                    "genre": row.get("genre", ""),
                })
                
                # Clean up temp file if downloaded
                if is_url and temp_file.exists():
                    temp_file.unlink()
                    
            except Exception as e:
                logger.error(f"Failed to process {file_id}: {e}")
                continue
        else:
            # Just copy/validate without normalization
            output_file = originals_dir / f"{file_id}.wav"
            if source_path != output_file:
                import shutil
                shutil.copy2(source_path, output_file)
            
            # Get audio info
            try:
                info = sf.info(output_file)
                checksum = compute_file_hash(output_file)
                results.append({
                    "id": file_id,
                    "title": title,
                    "source_url": url_or_path if is_url else None,
                    "source_path": str(source_path) if not is_url else None,
                    "file_path": str(output_file),
                    "duration": info.duration,
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "checksum": checksum,
                    "genre": row.get("genre", ""),
                })
            except Exception as e:
                logger.error(f"Failed to get info for {file_id}: {e}")
                continue
    
    # Create manifest DataFrame
    manifest_df = pd.DataFrame(results)
    
    if len(manifest_df) == 0:
        logger.error("No files were successfully ingested! Check that:")
        logger.error("  1. Manifest has 'url', 'path', or 'file_path' column")
        logger.error("  2. File paths in manifest are correct and files exist")
        logger.error("  3. Files are readable")
        raise ValueError("No files were ingested. Cannot proceed with empty manifest.")
    
    # Save manifest
    manifest_path = output_dir / "files_manifest.csv"
    manifest_df.to_csv(manifest_path, index=False)
    logger.info(f"Saved manifest to {manifest_path} with {len(manifest_df)} entries")
    
    return manifest_df


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Ingest audio files from manifest")
    parser.add_argument("--manifest", type=Path, required=True, help="Input CSV manifest")
    parser.add_argument("--output", type=Path, default=Path("data"), help="Output directory")
    parser.add_argument("--no-normalize", action="store_true", help="Skip normalization")
    parser.add_argument("--sample-rate", type=int, default=44100, help="Target sample rate")
    
    args = parser.parse_args()
    
    ingest_manifest(
        args.manifest,
        args.output,
        normalize=not args.no_normalize,
        sample_rate=args.sample_rate
    )
