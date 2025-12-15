# Dataset Setup - Summary

## What Was Created

I've created a complete solution for setting up your audio dataset from the URLs you provided:

### 1. **Scripts**

- **`scripts/setup_audio_dataset.py`**
  - Creates a CSV manifest file from the URLs you provided
  - Generates track IDs and titles from filenames
  - Handles URL encoding and special characters
  - Creates `data/manifests/audio_dataset_manifest.csv`

- **`scripts/download_and_setup_dataset.py`**
  - Complete automated setup script
  - Calls `setup_audio_dataset.py` to create manifest
  - Downloads all audio files from URLs
  - Normalizes audio (WAV, 44.1kHz, mono)
  - Sets up manifests for experiments

### 2. **Convenience Scripts**

- **`setup_dataset.bat`** (Windows)
- **`setup_dataset.sh`** (Linux/Mac)

Simple batch/shell scripts to run the complete setup.

### 3. **Documentation**

- **`SETUP_DATASET.md`** - Complete guide with troubleshooting

## How to Use

### Quick Start (Recommended)

**Windows:**
```bash
setup_dataset.bat
```

**Linux/Mac:**
```bash
chmod +x setup_dataset.sh
./setup_dataset.sh
```

**Or directly with Python:**
```bash
python scripts/download_and_setup_dataset.py
```

### What Happens

1. ✅ **Creates manifest** (`data/manifests/audio_dataset_manifest.csv`)
   - Extracts track IDs from URLs
   - Generates readable titles
   - Handles ~100 tracks

2. ✅ **Downloads audio files**
   - Downloads from Bubble.io CDN and AWS S3
   - Saves to temporary location

3. ✅ **Normalizes audio**
   - Converts to WAV format
   - Resamples to 44.1kHz
   - Converts to mono
   - Saves to `data/originals/`

4. ✅ **Creates processed manifest**
   - Generates `data/files_manifest.csv`
   - Copies to `data/manifests/files_manifest.csv`
   - Ready for experiments

### After Setup

Run Phase 1 and Phase 2 tests:

```bash
# Phase 1
python run_experiment.py --config config/test_matrix_phase1.yaml --originals data/manifests/files_manifest.csv

# Phase 2
python run_experiment.py --config config/test_matrix_phase2.yaml --originals data/manifests/files_manifest.csv
```

## Dataset Details

- **Total Tracks**: ~100 audio files
- **Genre**: Hip Hop / Rap Beats
- **Formats**: MP3, WAV (normalized to WAV)
- **Storage**: ~5GB recommended free space

## Benefits

✅ **Larger Dataset**: ~100 tracks vs current 3  
✅ **Realistic Testing**: Tests search-based identification  
✅ **Better Evaluation**: More accurate Recall@K metrics  
✅ **Automated**: One command setup  
✅ **Ready to Use**: Immediately available for experiments

## Files Created

```
data/
├── originals/                          # Normalized audio files
│   ├── track001.wav
│   ├── track002.wav
│   └── ... (~100 files)
├── manifests/
│   ├── audio_dataset_manifest.csv      # Original manifest with URLs
│   └── files_manifest.csv              # Processed manifest (for experiments)
└── files_manifest.csv                  # Also here (created by data_ingest.py)
```

## Next Steps

1. Run `setup_dataset.bat` (or `setup_dataset.sh`)
2. Wait for download and processing (~30-60 minutes)
3. Verify files in `data/originals/`
4. Run Phase 1 and Phase 2 experiments
5. View results in web UI or reports directory

## Troubleshooting

See `SETUP_DATASET.md` for detailed troubleshooting guide.

Common issues:
- **Download failures**: Check internet connection, verify URLs
- **Storage space**: Ensure ~5GB free space
- **Manifest errors**: Verify CSV format and file paths

