# Fingerprint Robustness Test - Deliverables Guide

## Overview

This project provides comprehensive deliverables for **Phase 1** (Core Manipulation Tests) and **Phase 2** (Structural Manipulation Tests) of fingerprint robustness testing.

## Quick Start

### Generate All Deliverables

```bash
python generate_deliverables.py --originals data/manifests/files_manifest.csv
```

This will:
1. Run Phase 1 tests (Core Manipulation)
2. Run Phase 2 tests (Structural Manipulation)
3. Generate comprehensive reports for both phases
4. Create comparison analysis
5. Package everything into a ZIP file

### Generate Individual Phase Deliverables

**Phase 1 only:**
```bash
python run_experiment.py --config config/test_matrix_phase1.yaml --originals data/manifests/files_manifest.csv
```

**Phase 2 only:**
```bash
python run_experiment.py --config config/test_matrix_phase2.yaml --originals data/manifests/files_manifest.csv
```

## Deliverables Structure

After running `generate_deliverables.py`, you'll receive:

```
fingerprint_robustness_deliverables_YYYYMMDD_HHMMSS.zip
├── README.txt
├── phase1_deliverables/
│   ├── final_report/
│   │   ├── report.html          # Main HTML report
│   │   ├── suite_summary.csv    # Detailed CSV results
│   │   ├── metrics.json         # Complete metrics data
│   │   └── plots/               # Visualizations
│   └── proofs/                  # Failure cases (if any)
├── phase2_deliverables/
│   ├── final_report/
│   │   ├── report.html
│   │   ├── suite_summary.csv
│   │   ├── metrics.json
│   │   └── plots/
│   └── proofs/
└── comparison/
    ├── phase_comparison.json    # Phase 1 vs Phase 2 metrics
    └── phase_comparison.csv     # Comparison CSV
```

## Phase 1 Test Coverage

### 1. Tempo (Speed) Changes
- ±3% (mild)
- ±6% (moderate)
- ±10% (severe)

### 2. Pitch Shifts
- ±1 semitone (mild)
- ±2 semitones (moderate)
- ±3 semitones (moderate)

### 3. Combined Pitch + Tempo
- Positive combination (+3% speed, +1 semitone)
- Negative combination (-4% speed, -2 semitones)

### 4. EQ Manipulations
- High-pass filter (150 Hz)
- Low-pass filter (6 kHz)
- Boost highs (+6 dB @ 3 kHz)
- Boost lows (+6 dB @ 200 Hz)
- Telephone filter (300 Hz - 3 kHz)

### 5. Compression / Limiting
- Compression (threshold -10 dB, ratio 10:1)
- Limiting (ceiling -1 dB)
- Multiband compression

## Phase 2 Test Coverage

### 6. Add Percussion Layers
- Basic drum loop (10% volume)
- Trap drums (20% volume)
- Boom-bap drums (20% volume)
- Percussion loop (20% volume)

### 7. Add Melodic Layers
- Pad/chords
- Simple lead melody
- Countermelody

### 8. Remove Elements
- Bass-only (low-pass 200 Hz)
- Remove highs (low-pass 2 kHz)

### 9. Noise & Room Effects
- White noise (-20 dB)
- Vinyl crackle
- Reverb (small room)
- Reverb (large hall)

### 10. Cropping
- 10-second clip (from start)
- 5-second clip (from start)
- Middle segment (10 seconds)
- End segment (10 seconds)

## Report Contents

### HTML Report (`report.html`)

Each phase report includes:

1. **Executive Summary**
   - Total tests run
   - Overall pass/fail rate
   - Key findings

2. **Per-Transform Results**
   - Recall@1, Recall@5, Recall@10
   - Mean rank distribution
   - Similarity score statistics
   - Latency metrics

3. **Visualizations**
   - Recall by severity
   - Recall by transform type
   - Latency distribution
   - Similarity distribution

4. **Failure Case Analysis**
   - Failed transforms
   - Audio samples and spectrograms
   - Detailed failure reasons

### CSV Summary (`suite_summary.csv`)

Columns:
- `severity`: mild, moderate, severe
- `count`: Number of tests
- `recall_at_1`: Recall@1 score
- `recall_at_5`: Recall@5 score
- `recall_at_10`: Recall@10 score
- `mean_rank`: Average rank of correct match
- `mean_similarity`: Average similarity score
- `mean_latency_ms`: Average query latency

### JSON Metrics (`metrics.json`)

Complete structured data including:
- Overall metrics
- Per-transform analysis
- Per-severity analysis
- Pass/fail status
- Detailed statistics

## Comparison Report

The comparison report (`phase_comparison.json`) includes:

- Phase 1 vs Phase 2 overall metrics
- Differences in recall rates
- Differences in mean rank
- Differences in similarity scores
- Performance analysis

## Requirements

### Python Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `librosa` - Audio processing
- `soundfile` - Audio I/O
- `numpy`, `scipy` - Numerical operations
- `pandas` - Data manipulation
- `faiss-cpu` or `faiss-gpu` - Similarity search
- `transformers`, `torch` - MERT model (optional)
- `pyyaml` - Configuration parsing
- `tqdm` - Progress bars

### External Tools

- **FFmpeg** - Required for audio encoding/decoding
  - Install: `apt-get install ffmpeg` (Linux) or download from ffmpeg.org

## Usage Examples

### Example 1: Generate Full Deliverables

```bash
# With original files CSV
python generate_deliverables.py --originals data/manifests/files_manifest.csv

# Skip Phase 1 if already completed
python generate_deliverables.py --skip-phase1 --originals data/manifests/files_manifest.csv

# Skip specific steps (e.g., if transforms already generated)
python generate_deliverables.py --originals data/manifests/files_manifest.csv --skip-steps transforms index
```

### Example 2: Run Individual Phase

```bash
# Phase 1 only
python run_experiment.py \
    --config config/test_matrix_phase1.yaml \
    --originals data/manifests/files_manifest.csv

# Phase 2 only
python run_experiment.py \
    --config config/test_matrix_phase2.yaml \
    --originals data/manifests/files_manifest.csv
```

### Example 3: Skip Steps (Resume from Checkpoint)

```bash
# Skip ingestion and transforms (already done)
python run_experiment.py \
    --config config/test_matrix_phase1.yaml \
    --skip ingest transforms
```

## Output Locations

- **Reports**: `reports/run_YYYYMMDD_HHMMSS/`
- **Final Reports**: `reports/run_YYYYMMDD_HHMMSS/final_report/`
- **Deliverables Package**: `deliverables/fingerprint_robustness_deliverables_YYYYMMDD_HHMMSS.zip`

## Troubleshooting

### Issue: "No embeddings were extracted"

**Solution**: Ensure MERT model dependencies are installed:
```bash
pip install transformers torch torchaudio
```

### Issue: "FFmpeg not found"

**Solution**: Install FFmpeg:
```bash
# Linux
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Issue: "Original file not found"

**Solution**: Ensure original files are in `data/originals/` or update manifest paths.

## Customer Submission Checklist

Before submitting to customer, ensure:

- [ ] Phase 1 report generated (`phase1_deliverables/final_report/report.html`)
- [ ] Phase 2 report generated (`phase2_deliverables/final_report/report.html`)
- [ ] Comparison report generated (`comparison/phase_comparison.json`)
- [ ] All CSV and JSON files included
- [ ] All plots/visualizations included
- [ ] Failure case proofs included (if any failures)
- [ ] README.txt included in package
- [ ] ZIP file successfully created and tested

## Support

For questions or issues:
1. Check logs in `reports/run_*/` directories
2. Review error messages in console output
3. Verify all dependencies are installed
4. Ensure original audio files are accessible

## Version

- **Version**: 1.0
- **Last Updated**: 2024
- **Compatible with**: Python 3.8+

