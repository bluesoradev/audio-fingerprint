#!/bin/bash
# Example script to run a full experiment

# Step 1: Ingest original files
python data_ingest.py \
    --manifest data/manifests/example_manifest.csv \
    --output data \
    --sample-rate 44100

# Step 2: Run full experiment
python run_experiment.py \
    --config config/test_matrix.yaml \
    --originals data/manifests/files_manifest.csv

# Step 3: Start UI to view results
cd ui
uvicorn app:app --reload --port 8080
