@echo off
REM Start the web interface for network access

echo Starting Audio Fingerprint Robustness Lab Web Interface...
echo.
echo Server will be accessible at: http://148.251.88.48:8080
echo.

cd ui
python -m uvicorn app:app --host 0.0.0.0 --port 8080