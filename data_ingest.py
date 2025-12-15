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
    """Download audio file from URL."""
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
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
    
    # Read manifest
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded manifest with {len(df)} entries")
    
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
