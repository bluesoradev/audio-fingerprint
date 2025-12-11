# Desktop Application - Audio Fingerprint Robustness Lab

A modern Windows desktop application built with PyQt6 for managing audio fingerprint robustness experiments.

## Features

- **Dark Theme**: Modern, easy-on-the-eyes dark interface
- **Dashboard**: Overview of experiments, statistics, and recent runs
- **Workflow Management**: Step-by-step experiment execution with real-time logs
- **Audio Manipulation**: Apply transforms (speed, pitch, noise, etc.) to audio files
- **File Management**: Browse, upload, and manage audio files
- **Results Viewer**: View experiment results, metrics, and charts
- **Configuration**: Customize application settings

## Installation

1. Install PyQt6:
```bash
pip install PyQt6
```

2. Install all other dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Windows:
Double-click `run_desktop_app.bat` or run:
```bash
python desktop_app\main.py
```

### From Command Line:
```bash
cd testm3
python desktop_app\main.py
```

## Application Structure

```
desktop_app/
├── __init__.py
├── main.py              # Application entry point
├── window.py            # Main window with navigation
├── theme.py             # Dark theme styling
└── pages/
    ├── __init__.py
    ├── dashboard.py     # Dashboard page
    ├── workflow.py      # Workflow management
    ├── manipulate.py    # Audio manipulation
    ├── files.py         # File browser
    ├── results.py       # Results viewer
    └── config.py        # Configuration settings
```

## Key Features

### Dashboard
- Total runs, active experiments, failed runs statistics
- Recent experiments table
- Quick access to start new experiments

### Workflow
- Step-by-step workflow controls
- Real-time log output
- Progress tracking
- Individual step execution

### Audio Manipulation
- Select audio files
- Apply transforms (speed, pitch, noise, reverb, EQ)
- Preview and save transformed audio

### Files
- Browse audio files by directory
- Upload files via drag-and-drop or browse
- View file details

### Results
- View all experiment runs
- Filter by status
- Download reports
- Charts for recall and rank distribution

### Configuration
- General settings (theme, prefixes, retention)
- File path configuration
- Experiment defaults (sample rate, bit depth, log level)

## Notes

- The desktop app uses the same backend logic as the web UI
- All transforms and workflows are identical
- Configuration is stored locally
- Charts will be enhanced in future versions

