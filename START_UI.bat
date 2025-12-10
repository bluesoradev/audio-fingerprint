@echo off
REM Start the web interface

echo Starting Audio Fingerprint Robustness Lab Web Interface...
echo.
echo Opening browser at http://localhost:8080
echo.

cd ui
start http://localhost:8080
python -m uvicorn app:app --reload --port 8080
