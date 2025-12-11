@echo off
REM Windows launcher for Audio Robustness Lab Desktop Application

cd /d "%~dp0"
python desktop_app\main.py

if errorlevel 1 (
    echo.
    echo Error: Failed to start the application.
    echo Please make sure PyQt6 is installed: pip install PyQt6
    pause
)

