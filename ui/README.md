# Web Interface - Audio Fingerprint Robustness Lab

Comprehensive web-based interface for managing and monitoring the robustness lab workflow.

## Features

### 🎛️ Workflow Management
- **Step-by-step workflow control**: Run individual steps or the complete pipeline
- **Process monitoring**: Real-time log streaming and status updates
- **Process control**: Start, monitor, and cancel processes

### 📁 File Management
- **Audio file upload**: Drag-and-drop or browse to upload audio files
- **Manifest management**: Create and manage CSV manifests
- **File browser**: View audio files in different directories

### 📊 Results & Analytics
- **Dashboard**: Overview of system status and recent runs
- **Experiment results**: View detailed metrics and reports
- **Failure analysis**: Examine failure cases with audio/spectrograms

### ⚙️ Configuration
- **Test matrix editor**: Edit transform configurations through the UI
- **Configuration management**: Save and load configurations

## Starting the Server

```bash
cd ui
uvicorn app:app --reload --port 8080
```

Or from project root:
```bash
python -m uvicorn ui.app:app --reload --port 8080
```

Then open: http://localhost:8080

## API Endpoints

### Process Management
- `POST /api/process/create-test-audio` - Create synthetic test audio
- `POST /api/process/create-manifest` - Create manifest from directory
- `POST /api/process/ingest` - Ingest and normalize files
- `POST /api/process/generate-transforms` - Generate transformed audio
- `POST /api/process/run-experiment` - Run full experiment
- `GET /api/process/{id}/logs` - Get process logs
- `GET /api/process/{id}/status` - Get process status
- `POST /api/process/{id}/cancel` - Cancel running process

### File Management
- `GET /api/files/manifests` - List manifest files
- `GET /api/files/audio` - List audio files
- `POST /api/upload/audio` - Upload audio file

### Results
- `GET /api/runs` - List all experiment runs
- `GET /api/runs/{id}` - Get run details
- `GET /download/{id}` - Download report ZIP

### Configuration
- `GET /api/config/test-matrix` - Get test matrix config
- `POST /api/config/test-matrix` - Update test matrix config

## Usage Workflow

1. **Start Server**: `uvicorn app:app --reload --port 8080`
2. **Open Browser**: Navigate to http://localhost:8080
3. **Create Test Audio**: Go to Workflow → Step 1 → Create Test Audio
4. **Create Manifest**: Go to Workflow → Step 2 → Create Manifest
5. **Run Experiment**: Go to Workflow → Step 5 → Run Full Experiment
6. **View Results**: Go to Results section to see experiment outputs

## Interface Sections

### Dashboard
- System status overview
- Recent experiment runs
- Quick statistics

### Workflow
- Complete step-by-step workflow control
- Real-time process monitoring with logs
- Individual step execution or full pipeline

### Files
- Upload audio files via drag-and-drop
- Browse manifests and audio files
- Manage file directories

### Results
- View all experiment runs
- Access detailed metrics and reports
- Download report packages

### Configuration
- Edit test matrix YAML configuration
- Save/load configurations

### Logs
- View system logs
- Monitor process outputs in real-time

## Architecture

- **Backend**: FastAPI with async support
- **Frontend**: Vanilla JavaScript with modern ES6+
- **Communication**: RESTful API with real-time log polling
- **Process Management**: Background tasks with subprocess handling

## Development

To modify the interface:
- **HTML**: Edit `templates/index.html`
- **JavaScript**: Edit `static/app.js`
- **Backend**: Edit `app.py`

The interface uses vanilla JavaScript (no frameworks) for simplicity and fast loading.
