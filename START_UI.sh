#!/bin/bash
# Start the web interface

echo "Starting Audio Fingerprint Robustness Lab Web Interface..."
echo ""
echo "Opening browser at http://localhost:8080"
echo ""

cd ui

# Try to open browser (Linux/Mac)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8080 &
elif command -v open &> /dev/null; then
    open http://localhost:8080 &
fi

python -m uvicorn app:app --reload --port 8080
