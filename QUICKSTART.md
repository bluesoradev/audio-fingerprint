# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Make sure ffmpeg is installed for audio encoding transforms.

## 2. Prepare Your Audio Files

Create a CSV file listing your original audio files:

```csv
id,title,url,genre
track1,My Song 1,path/to/track1.wav,pop
track2,My Song 2,path/to/track2.wav,rock
```

Save it as `data/manifests/my_files.csv`

## 3. Configure Tests

Edit `config/test_matrix.yaml` to customize:
- Which transforms to test
- Parameter ranges
- Pass/fail thresholds

## 4. Run Experiment

```bash
python run_experiment.py --config config/test_matrix.yaml --originals data/manifests/my_files.csv
```

This will:
- Ingest and normalize your files
- Generate transformed variants
- Build FAISS index
- Run queries
- Analyze results
- Generate report

## 5. View Results

**Option A: Web UI**
```bash
cd ui
uvicorn app:app --reload --port 8080
```
Visit http://localhost:8080

**Option B: HTML Report**
Open `reports/run_YYYYMMDD_HHMMSS/final_report/report.html`

## What Gets Generated

- `data/originals/` - Normalized original audio files
- `data/transformed/` - All transformed variants
- `data/manifests/` - CSV files tracking files and transforms
- `embeddings/` - Extracted embeddings
- `indexes/` - FAISS index files
- `reports/run_*/` - Complete test results and reports

## Next Steps

- Review `config/test_matrix.yaml` for customization
- Check `reports/` for detailed metrics
- Examine `reports/proofs/` for failure case analysis
- Adjust thresholds in config based on your requirements
