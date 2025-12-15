@echo off
REM Setup audio dataset from URLs
REM This script creates manifest, downloads, and processes all audio files

echo ============================================================
echo Audio Dataset Setup
echo ============================================================
echo.

python scripts\download_and_setup_dataset.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo Setup completed successfully!
    echo ============================================================
    echo.
    echo Next steps:
    echo   1. Verify files in data\originals\
    echo   2. Run Phase 1 test:
    echo      python run_experiment.py --config config\test_matrix_phase1.yaml --originals data\manifests\files_manifest.csv
    echo   3. Run Phase 2 test:
    echo      python run_experiment.py --config config\test_matrix_phase2.yaml --originals data\manifests\files_manifest.csv
    echo.
) else (
    echo.
    echo ============================================================
    echo Setup failed! Check errors above.
    echo ============================================================
)

pause

