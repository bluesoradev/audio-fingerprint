# Changelog

## Version 1.0.0 - Initial Release

### Features
- Complete audio transformation engine (pitch, speed, encoding, noise, slicing, overlay)
- Frozen fingerprint model support (MERT/OpenL3 fallback)
- FAISS indexing and querying (HNSW, Flat, IVF)
- Comprehensive evaluation metrics (Recall@K, rank distribution, similarity stats)
- Failure case capture with audio and spectrograms
- HTML/CSV/JSON report generation
- Web UI for viewing results (FastAPI)
- Full experiment orchestration pipeline

### Configuration
- YAML-based test matrix configuration
- Configurable pass/fail thresholds
- Support for combined transform chains
- Reproducible experiments with seed control

### Documentation
- Complete README with usage examples
- Step-by-step workflow documentation
- Troubleshooting guide
