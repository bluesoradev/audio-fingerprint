#!/usr/bin/env python3
"""
Quick helper script to add a single audio file to the index.

Usage:
    python scripts/add_file_to_index.py 111.wav
    python scripts/add_file_to_index.py data/test_audio/111.wav --file-id my_track_111
"""
import argparse
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.create_index import create_or_update_index

def main():
    parser = argparse.ArgumentParser(
        description="Add a single audio file to the fingerprint index"
    )
    parser.add_argument(
        "audio_file",
        type=Path,
        help="Path to audio file to add"
    )
    parser.add_argument(
        "--file-id",
        type=str,
        help="File ID (default: filename without extension)"
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("indexes/faiss_index.bin"),
        help="Path to index file (default: indexes/faiss_index.bin)"
    )
    parser.add_argument(
        "--output-index",
        type=Path,
        help="Path to save updated index (default: same as --index)"
    )
    
    args = parser.parse_args()
    
    # Validate audio file
    audio_file = Path(args.audio_file)
    if not audio_file.exists():
        print(f"Error: Audio file not found: {audio_file}")
        return 1
    
    # Determine file ID
    file_id = args.file_id or audio_file.stem
    
    # Create temporary manifest
    manifest_data = {
        "id": [file_id],
        "file_path": [str(audio_file.absolute())],
        "title": [audio_file.stem.replace("_", " ").title()]
    }
    files_df = pd.DataFrame(manifest_data)
    
    # Create manifest CSV in temp location
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        files_df.to_csv(f.name, index=False)
        manifest_path = Path(f.name)
    
    try:
        # Determine output index path
        output_index = args.output_index or args.index
        
        print(f"Adding {audio_file.name} (ID: {file_id}) to index...")
        print(f"Index: {args.index}")
        print(f"Output: {output_index}")
        
        # Create or update index
        index, metadata = create_or_update_index(
            files_input=manifest_path,
            output_index=output_index,
            existing_index=args.index if args.index.exists() else None
        )
        
        print(f"\n✓ Successfully added {audio_file.name} to index!")
        print(f"  Total vectors in index: {index.ntotal}")
        print(f"\n⚠ Remember to restart the API server to load the updated index!")
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up temp manifest
        if manifest_path.exists():
            manifest_path.unlink()

if __name__ == "__main__":
    sys.exit(main())
