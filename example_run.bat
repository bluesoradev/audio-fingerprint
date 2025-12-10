@echo off
REM Example script to run a full experiment on Windows

REM Step 1: Ingest original files
python data_ingest.py --manifest data/manifests/example_manifest.csv --output data --sample-rate 44100

REM Step 2: Run full experiment
python run_experiment.py --config config/test_matrix.yaml --originals data/manifests/files_manifest.csv

REM Step 3: Start UI to view results
cd ui
uvicorn app:app --reload --port 8080
