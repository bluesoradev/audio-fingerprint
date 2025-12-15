# Audio Fingerprint Robustness Lab

A comprehensive testing suite for evaluating the robustness of audio fingerprinting models against various transformations (pitch shifts, time stretches, compression, noise, etc.).

## Overview

This project provides a complete pipeline for:
1. **Transforming audio** with various effects (pitch, speed, encoding, noise, etc.)
2. **Running fingerprint queries** using a frozen model
3. **Evaluating performance** with metrics (Recall@K, rank distribution, similarity scores)
4. **Capturing failure cases** with audio, spectrograms, and analysis
5. **Generating reports** (CSV, JSON, HTML, plots)

## Project Structure

```
testm3/
├── config/
│   ├── fingerprint_v1.yaml      # Fingerprint model configuration
│   ├── test_matrix.yaml         # Test transforms and parameters
│   └── index_config.json        # FAISS index configuration
├── data/
│   ├── originals/               # Original audio files
│   ├── transformed/             # Generated transformed audio
│   └── manifests/               # CSV manifests
├── transforms/                  # Audio transformation modules
├── fingerprint/                 # Embedding extraction and indexing
├── evaluation/                  # Metrics and analysis
├── reports/                     # Generated reports and proofs
├── ui/                          # FastAPI web interface
├── run_experiment.py            # Main experiment runner
└── requirements.txt
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install ffmpeg (required for audio encoding transforms):
- Windows: Download from https://ffmpeg.org/download.html
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

3. (Optional) If using MERT model, ensure PyTorch and transformers are installed:
```bash
pip install torch transformers
```

## Quick Start

### 1. Prepare Original Audio Files

Create a CSV file with your original audio files:

```csv
id,title,url,genre
track1,Song 1,path/to/track1.wav,pop
track2,Song 2,path/to/track2.wav,rock
```

Or use URLs:
```csv
id,title,url,genre
track1,Song 1,https://example.com/track1.mp3,pop
```

### 2. Configure Test Matrix

Edit `config/test_matrix.yaml` to define:
- Which transforms to apply
- Parameter ranges for each transform
- Pass/fail thresholds
- Evaluation settings

### 3. Run Full Experiment

```bash
python run_experiment.py --config config/test_matrix.yaml --originals your_files.csv
```

This will:
1. Ingest and normalize original files
2. Generate all transformed variants
3. Build FAISS index from originals
4. Query transformed files against the index
5. Analyze results and compute metrics
6. Capture failure cases
7. Generate final report

### 4. View Results

**Option A: Web UI**
```bash
cd ui
uvicorn app:app --reload --port 8080
```
Then open http://localhost:8080

**Option B: View HTML Report**
Open `reports/run_YYYYMMDD_HHMMSS/final_report/report.html` in a browser

## Usage Examples

### Step-by-Step Execution

If you want to run steps individually:

```bash
# 1. Ingest files
python data_ingest.py --manifest your_files.csv --output data

# 2. Generate transforms
python transforms/generate_transforms.py \
    --manifest data/manifests/files_manifest.csv \
    --test-matrix config/test_matrix.yaml \
    --output data

# 3. Build index (custom script needed, or use run_experiment.py)

# 4. Run queries
python fingerprint/run_queries.py \
    --manifest data/manifests/transform_manifest.csv \
    --index indexes/faiss_index.bin \
    --config config/fingerprint_v1.yaml \
    --output reports/query_results

# 5. Analyze
python evaluation/analyze.py \
    --results reports/query_results \
    --manifest data/manifests/transform_manifest.csv \
    --test-matrix config/test_matrix.yaml \
    --output reports/analysis

# 6. Generate report
python reports/render_report.py \
    --metrics reports/analysis/metrics.json \
    --summary reports/analysis/suite_summary.csv \
    --output reports/final_report
```

### Skipping Steps

To skip already-completed steps:

```bash
python run_experiment.py \
    --config config/test_matrix.yaml \
    --skip ingest transforms index \
    --originals data/manifests/files_manifest.csv
```

## Configuration

### Fingerprint Model (`config/fingerprint_v1.yaml`)

Configure your frozen fingerprint model:
- Model type (MERT, OpenL3, custom)
- Model path and checksum
- Audio processing parameters
- Embedding dimensions

### Test Matrix (`config/test_matrix.yaml`)

Define transforms and test parameters:
- Transform types (pitch_shift, time_stretch, re_encode, etc.)
- Parameter ranges
- Severity levels (mild, moderate, severe)
- Pass/fail thresholds
- Combined transform chains

### Index Config (`config/index_config.json`)

FAISS index settings:
- Index type (flat, hnsw, ivf)
- Metric (cosine, l2)
- Construction parameters

## Output Structure

After running an experiment, you'll find:

```
reports/run_YYYYMMDD_HHMMSS/
├── query_results/
│   ├── query_summary.csv
│   └── *_query.json (individual query results)
├── metrics.json
├── suite_summary.csv
└── final_report/
    ├── report.html
    ├── suite_summary.csv
    ├── suite_report.json
    ├── plots/
    │   ├── recall_by_severity.png
    │   └── latency_by_transform.png
    └── proofs/
        └── [failure_case_ids]/
            ├── original.wav
            ├── transformed.wav
            ├── spectrogram_*.png
            └── failure_details.json
```

## Metrics Explained

- **Recall@K**: Fraction of queries where correct match is in top-K results
- **Mean Rank**: Average rank of correct match
- **Similarity Score**: Embedding similarity (cosine) for correct matches
- **Latency**: Processing time per file (ms)

## Troubleshooting

### ffmpeg not found
Ensure ffmpeg is installed and in PATH. Test with: `ffmpeg -version`

### Model loading fails
- Check `config/fingerprint_v1.yaml` model path
- Verify PyTorch/transformers installed if using MERT
- Check model checksum if specified

### Out of memory
- Reduce number of transforms in test matrix
- Use smaller index type (e.g., IVF instead of HNSW)
- Process files in batches

### Audio format issues
The pipeline normalizes to 44.1kHz mono WAV. If source files have issues:
- Check file corruption
- Verify codec support in librosa/soundfile
- Pre-convert problematic files

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
