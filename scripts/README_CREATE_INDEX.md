# Create Audio Fingerprint Index

This script creates or updates an audio fingerprint index for the fingerprint matching API.

## Quick Start

### Create Index from Directory

```bash
python scripts/create_index.py \
    --input data/originals \
    --output indexes/faiss_index.bin
```

### Create Index from Manifest CSV

```bash
python scripts/create_index.py \
    --input data/manifests/files_manifest.csv \
    --output indexes/faiss_index.bin
```

### Update Existing Index

```bash
python scripts/create_index.py \
    --input data/manifests/new_files.csv \
    --output indexes/faiss_index.bin \
    --existing-index indexes/faiss_index.bin
```

### Force Rebuild Index

```bash
python scripts/create_index.py \
    --input data/originals \
    --output indexes/faiss_index.bin \
    --force-rebuild
```

## Manifest CSV Format

The manifest CSV should have at least these columns:
- `id`: Unique identifier for the audio file (e.g., "track_001")
- `file_path` or `path` or `url`: Path to the audio file

Example:
```csv
id,file_path,title,genre
track_001,data/originals/track_001.wav,My Track,hip-hop
track_002,data/originals/track_002.mp3,Another Track,electronic
```

## Options

- `--input`: Path to manifest CSV or directory of audio files (required)
- `--output`: Path to save index file (required)
- `--fingerprint-config`: Path to fingerprint config YAML (default: `config/fingerprint_v1.yaml`)
- `--index-config`: Path to index config JSON (default: `config/index_config.json`)
- `--existing-index`: Path to existing index (for incremental update)
- `--force-rebuild`: Force rebuild even if index exists
- `--embeddings-dir`: Optional directory to save embeddings
- `--create-manifest`: If input is directory, create manifest CSV

## How It Works

1. **Load Configuration**: Reads fingerprint model config and index config
2. **Process Files**: 
   - Checks cache for existing embeddings (fast!)
   - Generates embeddings for new files
   - Segments audio into 3.5s chunks
   - Extracts embeddings using MERT model
3. **Build/Update Index**:
   - Creates new FAISS index, or
   - Updates existing index incrementally
4. **Save**: Saves index and metadata to disk

## Caching

The script uses an embeddings cache to speed up processing:
- First run: Generates embeddings (slower)
- Subsequent runs: Uses cached embeddings (much faster!)

Cache location: `data/cache/original_embeddings/`

## Example: Adding 111.wav to Index

### Step 1: Create Manifest

```python
import pandas as pd
from pathlib import Path

records = [{
    "id": "111",
    "file_path": str(Path("111.wav").absolute()),
    "title": "111 Test File"
}]

df = pd.DataFrame(records)
df.to_csv("data/manifests/111_manifest.csv", index=False)
```

### Step 2: Add to Index

```bash
python scripts/create_index.py \
    --input data/manifests/111_manifest.csv \
    --output indexes/faiss_index.bin \
    --existing-index indexes/faiss_index.bin
```

### Step 3: Restart API Server

After updating the index, restart the API server to load the new index:

```bash
# Stop server (Ctrl+C)
# Then restart
python -m uvicorn ui.app:app --host 0.0.0.0 --port 8080
```

## Troubleshooting

### "File not found" errors
- Check that file paths in manifest are correct
- Use absolute paths or paths relative to project root
- Verify files exist before running script

### "No embeddings generated"
- Check that audio files are in supported formats (wav, mp3, m4a, etc.)
- Verify fingerprint config is correct
- Check logs for specific error messages

### "Index type does not support incremental addition"
- Use `--force-rebuild` to rebuild the entire index
- Or check index config to ensure it supports incremental updates

## Performance Tips

1. **Use Cache**: The script automatically caches embeddings - subsequent runs are much faster
2. **Batch Processing**: Process multiple files at once rather than one at a time
3. **Incremental Updates**: Use `--existing-index` to add files without rebuilding
4. **GPU**: If available, embeddings generation will use GPU automatically
