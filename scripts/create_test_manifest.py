"""Create a test manifest CSV from audio files in a directory."""
import argparse
from pathlib import Path
import pandas as pd


def create_manifest_from_directory(audio_dir: Path, output_csv: Path):
    """Create manifest CSV from audio files in directory."""
    audio_dir = Path(audio_dir)
    output_csv = Path(output_csv)
    
    audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3"))
    
    if not audio_files:
        print(f"No audio files found in {audio_dir}")
        return
    
    records = []
    for i, audio_file in enumerate(audio_files, 1):
        records.append({
            "id": audio_file.stem,
            "title": audio_file.stem.replace("_", " ").title(),
            "url": str(audio_file.absolute()),
            "genre": "test"
        })
    
    df = pd.DataFrame(records)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    
    print(f"Created manifest with {len(records)} files: {output_csv}")
    print("\nFiles included:")
    for record in records:
        print(f"  - {record['id']}: {record['title']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create manifest CSV from audio directory")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        required=True,
        help="Directory containing audio files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/test_manifest.csv"),
        help="Output manifest CSV path"
    )
    
    args = parser.parse_args()
    
    create_manifest_from_directory(args.audio_dir, args.output)
