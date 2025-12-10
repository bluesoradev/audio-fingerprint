# Quick Reference Card

## 🚀 Fastest Start

```bash
# Windows
run_quick_test.bat

# Linux/Mac  
./run_quick_test.sh
```

---

## ✅ Verification

```bash
# Check installation
python verify_installation.py

# Run unit tests
python test_quick.py
```

---

## 📝 Common Commands

### Create Test Audio
```bash
python scripts/create_test_audio.py --num-files 3 --duration 10
```

### Create Manifest from Audio Directory
```bash
python scripts/create_test_manifest.py \
    --audio-dir path/to/audio \
    --output data/manifests/my_manifest.csv
```

### Run Full Experiment
```bash
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/my_manifest.csv
```

### Start Web UI
```bash
cd ui
uvicorn app:app --reload --port 8080
```

### View Results
- HTML: `reports/run_YYYYMMDD_HHMMSS/final_report/report.html`
- CSV: `reports/run_YYYYMMDD_HHMMSS/suite_summary.csv`
- JSON: `reports/run_YYYYMMDD_HHMMSS/metrics.json`

---

## 🔧 Step-by-Step (Manual)

```bash
# 1. Create test files
python scripts/create_test_audio.py --output-dir data/test_audio --num-files 2

# 2. Create manifest
python scripts/create_test_manifest.py \
    --audio-dir data/test_audio \
    --output data/manifests/test_manifest.csv

# 3. Ingest (if needed)
python data_ingest.py --manifest data/manifests/test_manifest.csv --output data

# 4. Generate transforms
python transforms/generate_transforms.py \
    --manifest data/manifests/files_manifest.csv \
    --test-matrix config/test_matrix.yaml \
    --output data

# 5. Run queries
python fingerprint/run_queries.py \
    --manifest data/manifests/transform_manifest.csv \
    --index indexes/faiss_index.bin \
    --config config/fingerprint_v1.yaml \
    --output reports/query_results

# 6. Analyze
python evaluation/analyze.py \
    --results reports/query_results \
    --manifest data/manifests/transform_manifest.csv \
    --test-matrix config/test_matrix.yaml \
    --output reports/analysis

# 7. Generate report
python reports/render_report.py \
    --metrics reports/analysis/metrics.json \
    --summary reports/analysis/suite_summary.csv \
    --output reports/final_report
```

---

## 📊 Key Metrics to Check

- **Recall@1** - Should be ≥ 0.9 for mild transforms
- **Recall@5** - Should be ≥ 0.95 for mild transforms
- **Mean Rank** - Lower is better (1 = perfect)
- **Similarity Score** - Higher is better (0.7-0.95 typical)
- **Latency** - Should be < 1000ms per file

---

## 📁 Important Directories

- `data/originals/` - Original audio files
- `data/transformed/` - Generated transformed variants
- `data/manifests/` - CSV manifest files
- `embeddings/` - Extracted embeddings
- `indexes/` - FAISS index files
- `reports/` - All test results and reports
- `reports/proofs/` - Failure case artifacts

---

## ⚙️ Configuration Files

- `config/fingerprint_v1.yaml` - Model configuration
- `config/test_matrix.yaml` - Transform definitions & thresholds
- `config/index_config.json` - FAISS index settings

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| ModuleNotFoundError | `pip install -r requirements.txt` |
| ffmpeg not found | Install ffmpeg, add to PATH |
| Model loading failed | Check PyTorch/transformers installed |
| Out of memory | Reduce files/transforms, use smaller index |
| No audio files | Check manifest CSV paths |

---

## 📚 Documentation

- `README.md` - Project overview
- `BUILD_AND_RUN.md` - Detailed build/run guide
- `TEST_GUIDE.md` - Testing procedures
- `QUICKSTART.md` - Quick start guide
