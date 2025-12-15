# Audio Dataset Setup Guide

This guide explains how to set up the audio dataset from URLs provided by the client.

## Quick Start

### Option 1: Automated Setup (Recommended)

Run the complete setup script that creates the manifest, downloads, and processes all files:

```bash
python scripts/download_and_setup_dataset.py
```

This will:
1. ✅ Create a CSV manifest from the URLs
2. ✅ Download all audio files from URLs
3. ✅ Normalize audio files (convert to WAV, 44.1kHz, mono)
4. ✅ Create processed manifest ready for experiments

### Option 2: Manual Setup

#### Step 1: Create Manifest

```bash
python scripts/setup_audio_dataset.py
```

This creates `data/manifests/audio_dataset_manifest.csv` with all URLs.

#### Step 2: Download and Process

```bash
python data_ingest.py --manifest data/manifests/audio_dataset_manifest.csv --output data
```

This downloads files, normalizes them, and creates `data/files_manifest.csv`.

#### Step 3: Copy Manifest

```bash
# Windows
copy data\files_manifest.csv data\manifests\files_manifest.csv

# Linux/Mac
cp data/files_manifest.csv data/manifests/files_manifest.csv
```

## Dataset Information

- **Total Tracks**: ~100 audio files
- **Genre**: Hip Hop / Rap Beats
- **Sources**: 
  - Bubble.io CDN
  - AWS S3 (beatlibrary)
- **Formats**: MP3, WAV (will be normalized to WAV)

## File Structure After Setup

```
data/
├── originals/              # Downloaded and normalized audio files
│   ├── track001.wav
│   ├── track002.wav
│   └── ...
├── manifests/
│   ├── audio_dataset_manifest.csv    # Original manifest with URLs
│   └── files_manifest.csv            # Processed manifest (used by experiments)
└── files_manifest.csv                # Also created here by data_ingest.py
```

## Running Experiments

After setup, you can run Phase 1 and Phase 2 tests:

```bash
# Phase 1: Core Manipulations
python run_experiment.py --config config/test_matrix_phase1.yaml --originals data/manifests/files_manifest.csv

# Phase 2: Structural Manipulations
python run_experiment.py --config config/test_matrix_phase2.yaml --originals data/manifests/files_manifest.csv
```

## Troubleshooting

### Download Failures

If some files fail to download:
- Check internet connection
- Verify URLs are accessible
- Check server logs for specific errors

### Manifest Issues

If manifest is empty or has errors:
- Verify CSV format (id, title, url, genre)
- Check that URLs are valid
- Ensure `data/manifests/` directory exists

### Storage Space

With ~100 tracks, expect:
- **Downloaded files**: ~500MB - 2GB (depending on original formats)
- **Normalized files**: ~1GB - 3GB (all WAV, 44.1kHz, mono)

Ensure you have at least **5GB free space** before starting.

## Web UI Usage

After setup, you can also use the web UI:

1. Start the web UI:
   ```bash
   cd ui
   uvicorn app:app --reload --port 8080 --host 0.0.0.0
   ```

2. Navigate to "Deliverables" section
3. Select audio files from the dropdown
4. Apply transformations and generate reports

The web UI will automatically use files from `data/originals/` and `data/test_audio/`.

## Notes

- **Normalization**: All files are converted to WAV, 44.1kHz, mono for consistency
- **File IDs**: Generated from filenames, cleaned for filesystem compatibility
- **Titles**: Extracted from URLs, URL-decoded and cleaned
- **Processing Time**: Expect 30-60 minutes for full download and processing of ~100 files

