@echo off
REM Quick test script for Windows - runs a minimal end-to-end test

echo ============================================================
echo Quick Test - Audio Fingerprint Robustness Lab
echo ============================================================
echo.

REM Step 1: Create test audio files
echo [1/5] Creating test audio files...
python scripts/create_test_audio.py --output-dir data/test_audio --num-files 2 --duration 5
if errorlevel 1 (
    echo ERROR: Failed to create test audio files
    exit /b 1
)

REM Step 2: Create manifest
echo.
echo [2/5] Creating manifest...
python scripts/create_test_manifest.py --audio-dir data/test_audio --output data/manifests/test_manifest.csv
if errorlevel 1 (
    echo ERROR: Failed to create manifest
    exit /b 1
)

REM Step 3: Run experiment (with minimal transforms for speed)
echo.
echo [3/5] Running experiment (this may take a few minutes)...
python run_experiment.py --config config/test_matrix.yaml --originals data/manifests/test_manifest.csv
if errorlevel 1 (
    echo ERROR: Experiment failed
    exit /b 1
)

REM Step 4: Check results
echo.
echo [4/5] Experiment completed! Checking results...
if exist "reports\run_*\suite_summary.csv" (
    echo SUCCESS: Results found in reports/run_*/
) else (
    echo WARNING: Results not found
)

REM Step 5: Summary
echo.
echo [5/5] Test Summary
echo ============================================================
echo.
echo Test completed! To view results:
echo   1. Check reports/run_YYYYMMDD_HHMMSS/final_report/report.html
echo   2. Or start the web UI: cd ui ^&^& uvicorn app:app --port 8080
echo.
pause
