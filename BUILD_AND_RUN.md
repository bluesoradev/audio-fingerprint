# Build, Run & Test Guide

Complete guide to building, running, and testing the Audio Fingerprint Robustness Lab.

## ✅ Pre-flight Check

**Verify installation:**
```bash
python verify_installation.py
```

**Run quick tests:**
```bash
python test_quick.py
```

Both should show all tests passing.

---

## 🚀 Quick Start (Fastest Way)

### Option 1: Automated Script (Recommended)

**Windows:**
```bash
run_quick_test.bat
```

**Linux/Mac:**
```bash
chmod +x run_quick_test.sh
./run_quick_test.sh
```

This automatically:
1. Creates 2 test audio files (5 seconds each)
2. Creates manifest CSV
3. Runs full experiment
4. Shows where to find results

### Option 2: Manual Steps

```bash
# 1. Create test audio
python scripts/create_test_audio.py --num-files 2 --duration 5

# 2. Create manifest
python scripts/create_test_manifest.py \
    --audio-dir data/test_audio \
    --output data/manifests/test_manifest.csv

# 3. Run experiment
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/test_manifest.csv

# 4. View results
cd ui && uvicorn app:app --port 8080
# Open http://localhost:8080
```

---

## 📋 Detailed Workflow

### Step 1: Prepare Test Data

**Option A: Generate Synthetic Audio (for testing)**
```bash
python scripts/create_test_audio.py \
    --output-dir data/test_audio \
    --num-files 3 \
    --duration 10
```

**Option B: Use Your Own Audio Files**

1. Place audio files in a directory
2. Create manifest CSV:
```bash
python scripts/create_test_manifest.py \
    --audio-dir path/to/your/audio \
    --output data/manifests/my_manifest.csv
```

Or create manually:
```csv
id,title,url,genre
track1,My Song 1,C:/path/to/track1.wav,pop
track2,My Song 2,C:/path/to/track2.wav,rock
```

### Step 2: Configure Test Matrix

Edit `config/test_matrix.yaml`:
- Enable/disable specific transforms
- Adjust parameter ranges
- Set pass/fail thresholds

For quick testing, you can disable some transforms:
```yaml
transforms:
  pitch_shift:
    enabled: true  # Keep this
  time_stretch:
    enabled: true  # Keep this
  re_encode:
    enabled: false  # Disable for faster tests
  add_noise:
    enabled: false  # Disable for faster tests
```

### Step 3: Run Experiment

**Full pipeline (recommended):**
```bash
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/test_manifest.csv
```

**Skip already-completed steps:**
```bash
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/files_manifest.csv \
    --skip ingest transforms index
```

### Step 4: View Results

**Option A: Web UI**
```bash
cd ui
uvicorn app:app --reload --port 8080
```
Then open http://localhost:8080

**Option B: HTML Report**
Open: `reports/run_YYYYMMDD_HHMMSS/final_report/report.html`

**Option C: Check Files**
- `reports/run_*/suite_summary.csv` - Quick metrics
- `reports/run_*/metrics.json` - Detailed metrics
- `reports/proofs/` - Failure case artifacts

---

## 🧪 Testing Different Scenarios

### Test 1: Minimal Test (Fast)
```bash
# Create 1 file, 5 seconds
python scripts/create_test_audio.py --num-files 1 --duration 5

# Modify test_matrix.yaml to only test pitch_shift
# Then run experiment
```

### Test 2: Moderate Test
```bash
# Create 3 files, 10 seconds each
python scripts/create_test_audio.py --num-files 3 --duration 10

# Use default test_matrix.yaml
# Run full experiment
```

### Test 3: Full Test (Slow)
```bash
# Use 5+ real audio files (30+ seconds each)
# Enable all transforms in test_matrix.yaml
# Run full experiment (may take hours)
```

---

## 📊 Understanding Results

### Key Files

1. **suite_summary.csv** - Overview metrics by severity
   - Recall@1, Recall@5, Recall@10
   - Mean rank, similarity scores
   - Latency statistics

2. **metrics.json** - Detailed metrics
   - Per-transform-type breakdown
   - Per-severity breakdown
   - Pass/fail status

3. **query_results/** - Individual query results
   - One JSON per transformed file
   - Shows top-K matches and scores

4. **proofs/** - Failure case analysis
   - Original vs transformed audio
   - Spectrograms
   - Query result details

### Key Metrics

- **Recall@K**: Fraction of queries with correct match in top-K
  - Recall@1 ≥ 0.9 = Good
  - Recall@5 ≥ 0.95 = Very good
  
- **Mean Rank**: Average rank of correct matches (lower = better)

- **Similarity Score**: Embedding similarity (0.7-0.95 typical)

- **Latency**: Processing time per file (should be < 1000ms)

---

## 🔧 Troubleshooting

### Installation Issues

**Problem:** `ModuleNotFoundError`
**Solution:** `pip install -r requirements.txt`

**Problem:** `ffmpeg not found`
**Solution:** Install ffmpeg and add to PATH

### Runtime Issues

**Problem:** "No audio files found"
**Solution:** Check manifest CSV paths are absolute or relative correctly

**Problem:** "Model loading failed"
**Solution:** 
- Check `config/fingerprint_v1.yaml`
- Verify PyTorch installed: `pip install torch transformers`
- For MERT, ensure internet connection (downloads from HuggingFace)

**Problem:** "Out of memory"
**Solution:**
- Reduce number of files
- Disable some transforms
- Use smaller index type (flat vs hnsw)

### Performance Issues

**Problem:** Experiment takes too long
**Solution:**
- Reduce number of transforms in test_matrix.yaml
- Use fewer test files
- Reduce audio duration
- Skip steps already completed with `--skip`

---

## 📁 Expected Output Structure

After running an experiment:

```
testm3/
├── data/
│   ├── originals/
│   │   └── track1.wav, track2.wav, ...
│   ├── transformed/
│   │   └── track1__pitch_shift__semitones_1.wav, ...
│   └── manifests/
│       ├── files_manifest.csv
│       └── transform_manifest.csv
├── embeddings/
│   └── track1_seg_0000.npy, ...
├── indexes/
│   ├── faiss_index.bin
│   └── faiss_index.json
└── reports/
    ├── run_20250101_120000/
    │   ├── query_results/
    │   ├── metrics.json
    │   ├── suite_summary.csv
    │   └── final_report/
    │       ├── report.html
    │       ├── plots/
    │       └── proofs/
    └── proofs/
```

---

## 🎯 Next Steps

1. **Review Results**: Check metrics and identify weak points
2. **Examine Failures**: Look at failure cases in `reports/proofs/`
3. **Adjust Thresholds**: Update pass/fail criteria in `config/test_matrix.yaml`
4. **Test Production Data**: Run with your actual audio files
5. **Optimize**: Adjust transforms based on your use case

---

## 💡 Tips

- Start with 1-2 short audio files for initial testing
- Gradually increase complexity (more files, longer duration, more transforms)
- Use the web UI for interactive exploration of results
- Check failure cases to understand model limitations
- Adjust test matrix based on your specific requirements
- Save reports for comparison across different model versions

---

For more details, see:
- `README.md` - Project overview
- `TEST_GUIDE.md` - Detailed testing procedures
- `QUICKSTART.md` - Quick reference
