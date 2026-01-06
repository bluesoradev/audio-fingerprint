# Audio Fingerprint Robustness Lab

A comprehensive testing suite for evaluating the robustness of audio fingerprinting models against various transformations (pitch shifts, time stretches, compression, noise, etc.) with integrated DAW project file parsing and web-based interface.

## Overview

This project provides a complete pipeline for:

1. **Transforming audio** with various effects (pitch, speed, encoding, noise, etc.)
2. **Running fingerprint queries** using Music Foundation Models (MERT/MuQ)
3. **Evaluating performance** with metrics (Recall@K, rank distribution, similarity scores)
4. **Parsing DAW project files** (.als, .flp, .logicx) to extract compositional metadata
5. **Capturing failure cases** with audio, spectrograms, and analysis
6. **Generating reports** (CSV, JSON, HTML, plots)
7. **Web-based interface** for managing experiments and viewing results

## Project Structure

```
testm3/
├── config/
│   ├── fingerprint_v1.yaml      # Fingerprint model configuration
│   ├── test_matrix.yaml       # Test transforms and parameters
│   └── index_config.json       # FAISS index configuration
├── data/
│   ├── originals/              # Original audio files
│   ├── transformed/            # Generated transformed audio
│   ├── manifests/              # CSV manifests
│   └── daw_files/              # DAW project files
├── transforms/                 # Audio transformation modules
├── fingerprint/               # Embedding extraction and indexing
├── daw_parser/                # DAW project file parsers
├── evaluation/                # Metrics and analysis
├── reports/                   # Generated reports and proofs
├── ui/                        # FastAPI web interface
├── embeddings/                # Cached embeddings
├── indexes/                   # FAISS index files
├── run_experiment.py          # Main experiment runner
└── requirements.txt
```

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or for Python 3 specifically:

```bash
pip3 install -r requirements.txt
```

### 2. Install System Dependencies

**ffmpeg** (required for audio encoding transforms):

- **Windows**:

  - Download from https://ffmpeg.org/download.html
  - Extract to `C:\ffmpeg` (or your preferred location)
  - Add `C:\ffmpeg\bin` to System PATH
  - Verify: `ffmpeg -version`

- **Linux**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

### 3. Verify Installation

```bash
python verify_installation.py
```

## Quick Start

### 1. Download Audio Files and Generate Embeddings

**Automated Setup (Recommended):**

```bash
# Windows
setup_dataset.bat

# Linux/Mac
bash setup_dataset.sh
```

This will:

- Download audio files from URLs (configured in `scripts/setup_audio_dataset.py`)
- Create manifest CSV at `data/manifests/files_manifest.csv`
- Normalize audio files (44.1kHz, mono)
- Generate embeddings automatically when building index

**Manual Setup:**

```bash
# Step 1: Create manifest from URLs
python scripts/setup_audio_dataset.py

# Step 2: Download and normalize audio
python data_ingest.py --manifest data/manifests/audio_dataset_manifest.csv --output data

# Step 3: Generate embeddings (happens automatically during index build)
python run_experiment.py --config config/test_matrix.yaml --originals data/manifests/files_manifest.csv --skip transforms queries analyze report
```

### 2. Run Full Experiment

```bash
python run_experiment.py --config config/test_matrix.yaml --originals data/manifests/files_manifest.csv
```

This will:

1. Ingest and normalize original files
2. Generate all transformed variants
3. Build FAISS index from originals (generates embeddings)
4. Query transformed files against the index
5. Analyze results and compute metrics
6. Capture failure cases
7. Generate final report

### 3. Start Web Interface

**Local Development:**

```bash
# Windows
START_UI.bat

# Linux/Mac
bash START_UI.sh

# Or manually
cd ui
uvicorn app:app --reload --port 8080
```

Then open: **http://localhost:8080**

**Production Deployment (Windows Server):**

1. Update `START_UI.bat` to bind to all interfaces:

   ```batch
   python -m uvicorn app:app --host 0.0.0.0 --port 8080
   ```

2. Configure Windows Firewall:

   ```powershell
   New-NetFirewallRule -DisplayName "Audio Lab API" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
   ```

3. Access at: `http://148.251.88.48:8080`

## Features

### Audio Transformations

- **Core**: Speed change, pitch shift, reverb, overlay
- **Filtering**: Noise reduction, EQ adjustment, high/low-pass filters
- **Encoding**: MP3, AAC, OGG compression with configurable bitrates
- **Dynamics**: Compression, limiting, multiband compression
- **Advanced**: Embedded sample detection, song-in-song scenarios

### DAW Project File Parsing

Supports parsing of:

- **Ableton Live (.als)** - Full support
- **FL Studio (.flp)** - Full support
- **Logic Pro (.logicx)** - Full support

Extracts:

- MIDI data (notes, velocities, timing)
- Arrangement (track entry/exit times)
- Tempo/key changes
- Plugin chains
- Sample sources
- Automation data

### Web Interface

- **Manipulate Audio**: Two-column layout with transform controls and audio playback with frequency visualization
- **Deliverables**: Configure transformations and generate Phase 1/Phase 2 reports
- **Dashboard**: System status and recent experiment runs
- **DAW Parser**: Upload and parse DAW project files

## Configuration

### Fingerprint Model (`config/fingerprint_v1.yaml`)

- Model type: MERT (330M parameters), MuQ, or custom
- GPU acceleration enabled by default
- Segment length: 3.5 seconds (optimized for coverage)
- Embedding dimension: 512

### Test Matrix (`config/test_matrix.yaml`)

Define transforms and test parameters:

- Transform types and parameter ranges
- Severity levels (mild, moderate, severe)
- Pass/fail thresholds
- Combined transform chains

## API Endpoints

The web interface exposes RESTful API endpoints for:

- **Upload**: Audio files, DAW project files
- **Process Management**: Create test audio, ingest, generate transforms, run experiments
- **File Management**: List manifests, audio files, serve files
- **Audio Manipulation**: Apply transformations via API
- **DAW Parser**: Upload, parse, retrieve metadata
- **Results & Reports**: List runs, download reports
- **Configuration**: Get/update test matrix

Base URL: `http://localhost:8080/api` (or your server IP)

## Output Structure

After running an experiment:

```
reports/run_YYYYMMDD_HHMMSS/
├── query_results/
│   ├── query_summary.csv
│   └── *_query.json
├── metrics.json
├── suite_summary.csv
└── final_report/
    ├── report.html
    ├── suite_summary.csv
    ├── plots/
    └── proofs/
```

**Embeddings Location:**

- Cached embeddings: `embeddings/{file_id}/*.npy`
- FAISS index: `indexes/faiss_index.bin`

## Metrics Explained

- **Recall@K**: Fraction of queries where correct match is in top-K results
- **Mean Rank**: Average rank of correct match
- **Similarity Score**: Embedding similarity (cosine) for correct matches
- **Latency**: Processing time per file (ms)

## Troubleshooting

### ffmpeg not found

- Ensure ffmpeg is installed and in PATH
- Test with: `ffmpeg -version`
- Windows: Add `C:\ffmpeg\bin` to System PATH

### Model loading fails

- Check `config/fingerprint_v1.yaml` model path
- Verify PyTorch/transformers installed: `pip install torch transformers`
- Check model checksum if specified

### Out of memory

- Reduce number of transforms in test matrix
- Use smaller index type (e.g., IVF instead of HNSW)
- Process files in batches

### Audio format issues

- Pipeline normalizes to 44.1kHz mono WAV
- Check file corruption
- Verify codec support in librosa/soundfile
- Pre-convert problematic files

### Parameter errors

- **time_stretch**: Config uses `ratio`, function expects `rate` (auto-converted)
- **re_encode**: File extensions automatically adjusted based on codec (AAC → .m4a)

## Development

### Adding New Transforms

1. Create transform function in `transforms/`:

```python
def my_transform(input_path, param, out_path, **kwargs):
    # Your transform logic
    return out_path
```

2. Register in `transforms/__init__.py`
3. Add to `transforms/generate_transforms.py`
4. Add config in `config/test_matrix.yaml`

### Extending Metrics

Add functions in `evaluation/metrics.py` and call from `evaluation/analyze.py`.

## Recent Updates

- Fixed `time_stretch` parameter mapping (ratio → rate conversion)
- Fixed codec-based file extensions (AAC files now use .m4a extension)
- Redesigned Manipulate Audio UI with two-column layout and frequency visualization
- Added transport controls and waveform editor with free audio playback
- Integrated DAW parser with fingerprinting system for automatic metadata indexing
