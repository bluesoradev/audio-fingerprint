# Testing Guide - Audio Fingerprint Robustness Lab

This guide walks you through building, running, and testing the robustness lab.

## Step 1: Verify Installation

```bash
python verify_installation.py
```

This checks:
- Python version (3.10+)
- Required packages
- Directory structure
- Configuration files

## Step 2: Run Quick Tests

Run the quick test suite to verify basic functionality:

```bash
python test_quick.py
```

This tests:
- Module imports
- Configuration loading
- Audio file creation
- Transform functions
- Audio segmentation

## Step 3: Create Test Audio Files

You have two options:

### Option A: Generate Synthetic Test Audio

```bash
python scripts/create_test_audio.py --output-dir data/test_audio --num-files 3
```

This creates 3 synthetic test audio files (10 seconds each) with different frequencies.

### Option B: Use Your Own Audio Files

Place your audio files (WAV or MP3) in a directory, then create a manifest:

```bash
python scripts/create_test_manifest.py --audio-dir path/to/your/audio --output data/manifests/test_manifest.csv
```

Or create a manifest CSV manually:

```csv
id,title,url,genre
track1,My Track 1,path/to/track1.wav,pop
track2,My Track 2,path/to/track2.wav,rock
```

## Step 4: Configure Test Matrix (Optional)

Edit `config/test_matrix.yaml` to customize:
- Which transforms to test
- Parameter ranges
- Pass/fail thresholds

For a quick test, you can reduce the number of transforms by setting `enabled: false` for some transform types.

## Step 5: Run Full Experiment

### Option A: Complete Pipeline (Recommended for first run)

```bash
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/test_manifest.csv
```

This runs all steps:
1. Ingests and normalizes audio files
2. Generates transformed variants
3. Builds FAISS index from originals
4. Runs queries on transformed files
5. Analyzes results and computes metrics
6. Captures failure cases
7. Generates final report

### Option B: Step-by-Step Execution

If you want to run steps individually:

```bash
# 1. Ingest files
python data_ingest.py \
    --manifest data/manifests/test_manifest.csv \
    --output data

# 2. Generate transforms
python transforms/generate_transforms.py \
    --manifest data/manifests/files_manifest.csv \
    --test-matrix config/test_matrix.yaml \
    --output data

# 3. Build index and run queries (use run_experiment.py for this)

# 4. Analyze results
python evaluation/analyze.py \
    --results reports/run_YYYYMMDD_HHMMSS/query_results \
    --manifest data/manifests/transform_manifest.csv \
    --test-matrix config/test_matrix.yaml \
    --output reports/analysis

# 5. Generate report
python reports/render_report.py \
    --metrics reports/analysis/metrics.json \
    --summary reports/analysis/suite_summary.csv \
    --output reports/final_report
```

## Step 6: View Results

### Option A: Web UI

```bash
cd ui
uvicorn app:app --reload --port 8080
```

Then open http://localhost:8080 in your browser.

### Option B: HTML Report

Open the generated HTML report:
```
reports/run_YYYYMMDD_HHMMSS/final_report/report.html
```

### Option C: CSV/JSON Files

Check the generated files:
- `reports/run_*/suite_summary.csv` - Summary metrics
- `reports/run_*/metrics.json` - Detailed metrics
- `reports/run_*/query_results/` - Individual query results
- `reports/proofs/` - Failure case artifacts

## Step 7: Interpret Results

### Key Metrics

1. **Recall@K**: Fraction of queries where the correct match is in top-K results
   - Recall@1 ≥ 0.9 = Good (correct match is top result 90% of the time)
   - Recall@5 ≥ 0.95 = Very good
   - Recall@10 ≥ 0.98 = Excellent

2. **Mean Rank**: Average rank of correct matches
   - Lower is better (rank 1 = perfect)

3. **Similarity Score**: Embedding similarity for correct matches
   - Higher is better (typically 0.7-0.95 range)

4. **Latency**: Processing time per file
   - Should be < 1000ms per file

### Pass/Fail Criteria

The test matrix defines thresholds. Check:
- `reports/run_*/metrics.json` → `pass_fail` section
- Green ✅ = Pass, Red ❌ = Fail

### Failure Cases

Examine failure cases in:
- `reports/proofs/[case_id]/`
  - `original.wav` - Original audio
  - `transformed.wav` - Transformed version
  - `spectrogram_*.png` - Visual comparisons
  - `failure_details.json` - Query results

## Troubleshooting

### "No audio files found"
- Check your manifest CSV paths are correct
- Verify audio files exist and are readable

### "ffmpeg not found"
- Install ffmpeg: https://ffmpeg.org/download.html
- Add to PATH, or the encoding transforms will fail

### "Model loading failed"
- Check `config/fingerprint_v1.yaml`
- Verify PyTorch/transformers are installed
- For MERT, ensure internet connection (downloads from HuggingFace)

### "Out of memory"
- Reduce number of transforms in test matrix
- Use fewer test files
- Process in smaller batches

### "FAISS index build fails"
- Check you have enough disk space
- Reduce index type complexity (use "flat" instead of "hnsw")

## Quick Test Workflow

For the fastest test:

```bash
# 1. Create test audio
python scripts/create_test_audio.py --num-files 2 --duration 5

# 2. Create manifest
python scripts/create_test_manifest.py \
    --audio-dir data/test_audio \
    --output data/manifests/test_manifest.csv

# 3. Run experiment (reduced transforms)
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/test_manifest.csv

# 4. View results
cd ui && uvicorn app:app --port 8080
```

## Expected Output

After a successful run, you should see:
- `data/originals/` - 2 normalized audio files
- `data/transformed/` - Many transformed variants (depending on test matrix)
- `data/manifests/transform_manifest.csv` - Transform mapping
- `embeddings/` - Extracted embeddings
- `indexes/faiss_index.bin` - FAISS index
- `reports/run_YYYYMMDD_HHMMSS/` - Complete results

## Next Steps

1. Review metrics in the HTML report
2. Examine failure cases if any
3. Adjust thresholds in `config/test_matrix.yaml`
4. Run with your actual production audio files
5. Customize transforms based on your use case
