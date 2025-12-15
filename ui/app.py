"""Comprehensive FastAPI web UI for Audio Fingerprint Robustness Lab."""
from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks, Form, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
try:
    from fastapi.templating import Jinja2Templates
except ImportError:
    from starlette.templating import Jinja2Templates
from pathlib import Path
import json
import logging
import subprocess
import sys
import asyncio
import shutil
import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime
import yaml
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Fingerprint Robustness Lab - Web Interface")

# Add exception handler to ensure JSON responses
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and return JSON."""
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": errors
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions and return JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to return JSON errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    import traceback
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc)
        }
    )

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Setup static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Project root paths
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"

# Add project root to Python path for imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Process management
running_processes = {}
process_logs = {}
process_queues = {}


def run_command_async(command_id: str, command: List[str], log_queue: queue.Queue):
    """Run a command and capture output in real-time."""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        running_processes[command_id] = process
        
        for line in iter(process.stdout.readline, ''):
            if line:
                log_queue.put(('stdout', line.strip()))
        
        process.wait()
        log_queue.put(('status', 'completed'))
        log_queue.put(('exit_code', process.returncode))
        
    except Exception as e:
        log_queue.put(('error', str(e)))
        log_queue.put(('status', 'failed'))
    finally:
        if command_id in running_processes:
            del running_processes[command_id]


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status():
    """Get system status."""
    status = {
        "project_root": str(PROJECT_ROOT),
        "data_dir_exists": DATA_DIR.exists(),
        "reports_dir_exists": REPORTS_DIR.exists(),
        "config_files": {
            "fingerprint": (CONFIG_DIR / "fingerprint_v1.yaml").exists(),
            "test_matrix": (CONFIG_DIR / "test_matrix.yaml").exists(),
            "index": (CONFIG_DIR / "index_config.json").exists(),
        },
        "running_processes": list(running_processes.keys()),
    }
    return JSONResponse(status)


@app.post("/api/process/create-test-audio")
async def create_test_audio(
    num_files: int = Form(2),
    duration: float = Form(5.0),
    output_dir: str = Form("data/test_audio"),
    background_tasks: BackgroundTasks = None
):
    """Create test audio files."""
    command_id = f"create_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_queue = queue.Queue()
    process_logs[command_id] = []
    process_queues[command_id] = log_queue
    
    output_path = PROJECT_ROOT / output_dir
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "create_test_audio.py"),
        "--output-dir", str(output_path),
        "--num-files", str(num_files),
        "--duration", str(duration)
    ]
    
    thread = threading.Thread(
        target=run_command_async,
        args=(command_id, command, log_queue),
        daemon=True
    )
    thread.start()
    
    return JSONResponse({
        "command_id": command_id,
        "status": "started",
        "message": "Creating test audio files..."
    })


@app.post("/api/process/create-manifest")
async def create_manifest(
    audio_dir: str = Form(...),
    output: str = Form("data/manifests/test_manifest.csv")
):
    """Create manifest from audio directory."""
    command_id = f"create_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_queue = queue.Queue()
    process_logs[command_id] = []
    process_queues[command_id] = log_queue
    
    audio_path = PROJECT_ROOT / audio_dir
    output_path = PROJECT_ROOT / output
    
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "create_test_manifest.py"),
        "--audio-dir", str(audio_path),
        "--output", str(output_path)
    ]
    
    thread = threading.Thread(
        target=run_command_async,
        args=(command_id, command, log_queue),
        daemon=True
    )
    thread.start()
    
    return JSONResponse({
        "command_id": command_id,
        "status": "started",
        "message": "Creating manifest..."
    })


@app.post("/api/process/ingest")
async def ingest_files(
    manifest_path: str = Form(...),
    output_dir: str = Form("data"),
    sample_rate: int = Form(44100)
):
    """Ingest and normalize audio files."""
    command_id = f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_queue = queue.Queue()
    process_logs[command_id] = []
    process_queues[command_id] = log_queue
    
    manifest_file = PROJECT_ROOT / manifest_path
    output_path = PROJECT_ROOT / output_dir
    
    command = [
        sys.executable,
        str(PROJECT_ROOT / "data_ingest.py"),
        "--manifest", str(manifest_file),
        "--output", str(output_path),
        "--sample-rate", str(sample_rate)
    ]
    
    thread = threading.Thread(
        target=run_command_async,
        args=(command_id, command, log_queue),
        daemon=True
    )
    thread.start()
    
    return JSONResponse({
        "command_id": command_id,
        "status": "started",
        "message": "Ingesting files..."
    })


@app.post("/api/process/generate-transforms")
async def generate_transforms(
    manifest_path: str = Form(...),
    test_matrix_path: str = Form("config/test_matrix.yaml"),
    output_dir: str = Form("data")
):
    """Generate transformed audio files."""
    command_id = f"transforms_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_queue = queue.Queue()
    process_logs[command_id] = []
    process_queues[command_id] = log_queue
    
    manifest_file = PROJECT_ROOT / manifest_path
    test_matrix = PROJECT_ROOT / test_matrix_path
    output_path = PROJECT_ROOT / output_dir
    
    command = [
        sys.executable,
        str(PROJECT_ROOT / "transforms" / "generate_transforms.py"),
        "--manifest", str(manifest_file),
        "--test-matrix", str(test_matrix),
        "--output", str(output_path)
    ]
    
    thread = threading.Thread(
        target=run_command_async,
        args=(command_id, command, log_queue),
        daemon=True
    )
    thread.start()
    
    return JSONResponse({
        "command_id": command_id,
        "status": "started",
        "message": "Generating transforms..."
    })


@app.post("/api/process/run-experiment")
async def run_experiment(
    config_path: str = Form("config/test_matrix.yaml"),
    originals_path: str = Form(...),
    skip_steps: Optional[str] = Form(None)
):
    """Run full experiment."""
    command_id = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_queue = queue.Queue()
    process_logs[command_id] = []
    process_queues[command_id] = log_queue
    
    config_file = PROJECT_ROOT / config_path
    originals_file = PROJECT_ROOT / originals_path
    
    command = [
        sys.executable,
        str(PROJECT_ROOT / "run_experiment.py"),
        "--config", str(config_file),
        "--originals", str(originals_file)
    ]
    
    if skip_steps:
        command.extend(["--skip"] + skip_steps.split())
    
    thread = threading.Thread(
        target=run_command_async,
        args=(command_id, command, log_queue),
        daemon=True
    )
    thread.start()
    
    return JSONResponse({
        "command_id": command_id,
        "status": "started",
        "message": "Running experiment..."
    })


@app.post("/api/process/generate-deliverables")
async def generate_deliverables_api(
    manifest_path: str = Form("data/files_manifest.csv"),
    phase: str = Form("both")  # "both", "phase1", "phase2"
):
    """Generate Phase 1 and/or Phase 2 deliverables."""
    command_id = f"deliverables_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_queue = queue.Queue()
    process_logs[command_id] = []
    process_queues[command_id] = log_queue
    
    manifest_file = PROJECT_ROOT / manifest_path
    
    if not manifest_file.exists():
        return JSONResponse({
            "status": "error",
            "message": f"Manifest file not found: {manifest_path}"
        }, status_code=404)
    
    if phase == "both":
        # Generate both phases
        command = [
            sys.executable,
            str(PROJECT_ROOT / "generate_deliverables.py"),
            "--originals", str(manifest_file)
        ]
    elif phase == "phase1":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "run_experiment.py"),
            "--config", str(PROJECT_ROOT / "config/test_matrix_phase1.yaml"),
            "--originals", str(manifest_file)
        ]
    elif phase == "phase2":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "run_experiment.py"),
            "--config", str(PROJECT_ROOT / "config/test_matrix_phase2.yaml"),
            "--originals", str(manifest_file)
        ]
    else:
        return JSONResponse({
            "status": "error",
            "message": f"Invalid phase: {phase}. Must be 'both', 'phase1', or 'phase2'"
        }, status_code=400)
    
    thread = threading.Thread(
        target=run_command_async,
        args=(command_id, command, log_queue),
        daemon=True
    )
    thread.start()
    
    return JSONResponse({
        "command_id": command_id,
        "status": "started",
        "message": f"Generating {phase} deliverables..."
    })


@app.get("/api/process/{command_id}/logs")
async def get_logs(command_id: str):
    """Get logs for a process."""
    if command_id not in process_queues:
        return JSONResponse({"error": "Process not found"}, status_code=404)
    
    log_queue = process_queues[command_id]
    logs = []
    
    # Get new logs from queue
    try:
        while True:
            try:
                log_type, message = log_queue.get_nowait()
                logs.append({"type": log_type, "message": message})
                process_logs[command_id].append({"type": log_type, "message": message})
            except queue.Empty:
                break
    except:
        pass
    
    # Get all logs if queue is empty
    if not logs and command_id in process_logs:
        logs = process_logs[command_id][-100:]  # Last 100 lines
    
    return JSONResponse({"logs": logs})


@app.get("/api/process/{command_id}/status")
async def get_process_status(command_id: str):
    """Get process status."""
    # Check if process is currently running
    if command_id in running_processes:
        process = running_processes[command_id]
        return_code = process.poll()  # Returns None if still running, otherwise return code
        if return_code is None:
            return JSONResponse({
                "status": "running",
                "pid": process.pid
            })
        else:
            # Process just finished, update logs
            if command_id in process_queues:
                process_queues[command_id].put(('status', 'completed'))
                process_queues[command_id].put(('exit_code', return_code))
            return JSONResponse({
                "status": "completed" if return_code == 0 else "failed",
                "returncode": return_code
            })
    
    # Check if process exists in logs (completed or failed)
    if command_id in process_logs:
        logs = process_logs[command_id]
        if logs:
            # Look for status message in logs
            for log in reversed(logs):  # Check from most recent
                if log.get("type") == "status":
                    status_msg = log.get("message", "unknown")
                    return JSONResponse({
                        "status": status_msg,
                        "returncode": logs[-1].get("exit_code") if status_msg == "completed" else None
                    })
        
        # If logs exist but no status yet, process is starting
        return JSONResponse({
            "status": "starting"
        })
    
    # Check if process is queued (starting soon)
    if command_id in process_queues:
        return JSONResponse({
            "status": "starting"
        })
    
    # Process not found
    return JSONResponse({"status": "not_found"}, status_code=404)


@app.post("/api/process/{command_id}/cancel")
async def cancel_process(command_id: str):
    """Cancel a running process."""
    if command_id in running_processes:
        process = running_processes[command_id]
        process.terminate()
        del running_processes[command_id]
        if command_id in process_queues:
            process_queues[command_id].put(('status', 'cancelled'))
        return JSONResponse({"status": "cancelled"})
    
    return JSONResponse({"error": "Process not found"}, status_code=404)


@app.get("/api/files/manifests")
async def list_manifests():
    """List available manifest files."""
    manifests_dir = DATA_DIR / "manifests"
    manifests = []
    
    if manifests_dir.exists():
        for file in manifests_dir.glob("*.csv"):
            manifests.append({
                "name": file.name,
                "path": str(file.relative_to(PROJECT_ROOT)),
                "size": file.stat().st_size,
                "modified": file.stat().st_mtime
            })
    
    return JSONResponse({"manifests": sorted(manifests, key=lambda x: x["modified"], reverse=True)})


@app.get("/api/files/audio")
async def list_audio_files(directory: str = "originals"):
    """List audio files in a directory."""
    audio_dir = DATA_DIR / directory
    files = []
    
    if audio_dir.exists():
        for file in audio_dir.glob("*.wav"):
            files.append({
                "name": file.name,
                "path": str(file.relative_to(PROJECT_ROOT)),
                "size": file.stat().st_size,
                "modified": file.stat().st_mtime
            })
        # Also include MP3 files
        for file in audio_dir.glob("*.mp3"):
            files.append({
                "name": file.name,
                "path": str(file.relative_to(PROJECT_ROOT)),
                "size": file.stat().st_size,
                "modified": file.stat().st_mtime
            })
    
    return JSONResponse({"files": sorted(files, key=lambda x: x["modified"], reverse=True)})


@app.get("/api/files/audio-file")
async def serve_audio_file(path: str):
    """Serve audio file for preview."""
    logger.info(f"[Audio File API] Requested path: {path}")
    file_path = PROJECT_ROOT / path
    logger.info(f"[Audio File API] Full file path: {file_path}")
    logger.info(f"[Audio File API] File exists: {file_path.exists()}")
    
    if file_path.exists():
        logger.info(f"[Audio File API] File suffix: {file_path.suffix}")
        if file_path.suffix in [".wav", ".mp3", ".m4a", ".flac", ".ogg"]:
            logger.info(f"[Audio File API] Serving file: {file_path}")
            return FileResponse(file_path, media_type="audio/wav")
        else:
            logger.warning(f"[Audio File API] Unsupported file type: {file_path.suffix}")
            return JSONResponse({"error": f"Unsupported file type: {file_path.suffix}"}, status_code=400)
    else:
        logger.error(f"[Audio File API] File not found: {file_path}")
        return JSONResponse({"error": f"Audio file not found: {path}"}, status_code=404)


@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), directory: str = Form("originals")):
    """Upload audio file."""
    upload_dir = DATA_DIR / directory
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return JSONResponse({
        "status": "success",
        "filename": file.filename,
        "path": str(file_path.relative_to(PROJECT_ROOT)),
        "size": file_path.stat().st_size
    })


@app.post("/api/manipulate/speed")
async def manipulate_speed(
    input_path: str = Form(...),
    speed_ratio: str = Form(...),  # Accept as string first
    preserve_pitch: str = Form("false"),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply speed change transform."""
    try:
        # Parse parameters
        try:
            speed_ratio = float(speed_ratio)
        except (ValueError, TypeError):
            return JSONResponse({
                "status": "error",
                "message": f"Invalid speed_ratio: {speed_ratio}"
            }, status_code=400)
        
        preserve_pitch = preserve_pitch.lower() in ("true", "1", "yes", "on")
        
        from transforms.speed import time_stretch, speed_change
        
        input_file = PROJECT_ROOT / input_path
        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            return JSONResponse({
                "status": "error",
                "message": f"Input file not found: {input_path}"
            }, status_code=404)
        
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_speed_{speed_ratio}x.wav"
        
        logger.info(f"Applying speed transform: {input_file} -> {out_file} (ratio={speed_ratio}, preserve_pitch={preserve_pitch})")
        
        if preserve_pitch:
            time_stretch(input_file, speed_ratio, out_file)
        else:
            speed_change(input_file, speed_ratio, out_file, preserve_pitch=False)
        
        if not out_file.exists():
            raise Exception("Output file was not created")
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Speed change applied: {speed_ratio}x"
        })
    except ImportError as e:
        logger.error(f"Import error in speed transform: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "status": "error",
            "message": f"Import error: {str(e)}"
        }, status_code=500)
    except Exception as e:
        logger.error(f"Speed transform failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@app.post("/api/manipulate/pitch")
async def manipulate_pitch(
    input_path: str = Form(...),
    semitones: float = Form(...),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply pitch shift transform."""
    try:
        from transforms.pitch import pitch_shift
        
        logger.info(f"[Pitch Transform API] Received request: input_path={input_path}, semitones={semitones}, output_dir={output_dir}, output_name={output_name}")
        
        input_file = PROJECT_ROOT / input_path
        if not input_file.exists():
            logger.error(f"[Pitch Transform API] Input file not found: {input_path}")
            return JSONResponse({
                "status": "error",
                "message": f"Input file not found: {input_path}"
            }, status_code=404)
        
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_pitch_{semitones:+g}st.wav"
        
        logger.info(f"[Pitch Transform API] Applying pitch transform: {input_file} -> {out_file} (semitones={semitones})")
        logger.info(f"[Pitch Transform API] Semitones value type: {type(semitones)}, value: {semitones}")
        
        pitch_shift(input_file, semitones, out_file)
        
        logger.info(f"[Pitch Transform API] Pitch shift completed. Output file exists: {out_file.exists()}, size: {out_file.stat().st_size if out_file.exists() else 0} bytes")
        
        if not out_file.exists():
            logger.error(f"[Pitch Transform API] Output file was not created: {out_file}")
            raise Exception("Output file was not created")
        
        file_size = out_file.stat().st_size
        logger.info(f"[Pitch Transform API] Success! Output file: {out_file} ({file_size} bytes)")
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Pitch shift applied: {semitones:+g} semitones"
        })
    except Exception as e:
        logger.error(f"[Pitch Transform API] Pitch transform failed: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@app.post("/api/manipulate/overlay")
async def manipulate_overlay(
    input_path: str = Form(...),
    overlay_path: str = Form(None),
    gain_db: float = Form(-6.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply overlay/vocals transform."""
    try:
        from transforms.overlay import overlay_vocals
        
        input_file = PROJECT_ROOT / input_path
        if not input_file.exists():
            return JSONResponse({
                "status": "error",
                "message": f"Input file not found: {input_path}"
            }, status_code=404)
        
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_overlay.wav"
        
        overlay_file = None
        if overlay_path and overlay_path.strip():
            overlay_file = PROJECT_ROOT / overlay_path
            if not overlay_file.exists():
                overlay_file = None
        
        logger.info(f"Applying overlay transform: {input_file} -> {out_file}")
        # overlay_vocals signature: (input_path, vocal_file, level_db, out_path)
        overlay_vocals(input_file, overlay_file, gain_db, out_file)
        
        if not out_file.exists():
            raise Exception("Output file was not created")
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Overlay applied with {gain_db}dB gain"
        })
    except Exception as e:
        logger.error(f"Overlay transform failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@app.post("/api/manipulate/reverb")
async def manipulate_reverb(
    input_path: str = Form(...),
    delay_ms: float = Form(50.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply reverb delay transform."""
    from transforms.reverb import apply_reverb
    
    input_file = PROJECT_ROOT / input_path
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        out_file = output_path / output_name
    else:
        out_file = output_path / f"{input_file.stem}_reverb_{delay_ms}ms.wav"
    
    try:
        apply_reverb(input_file, delay_ms, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Reverb applied: {delay_ms}ms delay"
        })
    except Exception as e:
        logger.error(f"Reverb transform failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/noise-reduction")
async def manipulate_noise_reduction(
    input_path: str = Form(...),
    reduction_strength: float = Form(0.5),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply noise reduction transform."""
    from transforms.noise import reduce_noise
    
    input_file = PROJECT_ROOT / input_path
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        out_file = output_path / output_name
    else:
        out_file = output_path / f"{input_file.stem}_noise_reduced_{int(reduction_strength*100)}pct.wav"
    
    try:
        logger.info(f"[Noise Reduction API] Applying noise reduction: {input_file} -> {out_file}")
        reduce_noise(input_file, reduction_strength, out_file)
        
        if not out_file.exists():
            raise Exception(f"Output file was not created: {out_file}")
        
        output_path_str = str(out_file.relative_to(PROJECT_ROOT))
        file_size = out_file.stat().st_size
        logger.info(f"[Noise Reduction API] Success! Output: {output_path_str} ({file_size} bytes)")
        
        return JSONResponse({
            "status": "success",
            "output_path": output_path_str,
            "message": f"Noise reduction applied: {int(reduction_strength*100)}%"
        })
    except Exception as e:
        logger.error(f"[Noise Reduction API] Noise reduction failed: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/noise")
async def manipulate_noise(
    input_path: str = Form(...),
    snr_db: float = Form(20.0),
    noise_type: str = Form("white"),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply noise addition transform."""
    from transforms.noise import add_noise
    
    input_file = PROJECT_ROOT / input_path
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        out_file = output_path / output_name
    else:
        out_file = output_path / f"{input_file.stem}_noise_{snr_db}db.wav"
    
    try:
        add_noise(input_file, snr_db, noise_type, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Noise added: {noise_type} at {snr_db}dB SNR"
        })
    except Exception as e:
        logger.error(f"Noise transform failed: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/encode")
async def manipulate_encode(
    input_path: str = Form(...),
    codec: str = Form("mp3"),
    bitrate: str = Form("128k"),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply re-encoding transform."""
    from transforms.encode import re_encode
    
    logger.info(f"[Encode API] Received request: input_path={input_path}, codec={codec}, bitrate={bitrate}")
    
    input_file = PROJECT_ROOT / input_path
    if not input_file.exists():
        logger.error(f"[Encode API] Input file not found: {input_path}")
        return JSONResponse({
            "status": "error",
            "message": f"Input file not found: {input_path}"
        }, status_code=404)
    
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        out_file = output_path / output_name
    else:
        # Determine file extension based on codec
        ext_map = {
            "mp3": "mp3",
            "aac": "m4a",  # AAC typically uses .m4a extension
            "ogg": "ogg",
            "opus": "opus",
            "flac": "flac"
        }
        ext = ext_map.get(codec.lower(), codec.lower())
        out_file = output_path / f"{input_file.stem}_{codec}_{bitrate}.{ext}"
    
    logger.info(f"[Encode API] Applying encode: {input_file} -> {out_file}")
    
    try:
        re_encode(input_file, codec, bitrate, out_file)
        
        if not out_file.exists():
            raise Exception(f"Output file was not created: {out_file}")
        
        output_path_str = str(out_file.relative_to(PROJECT_ROOT))
        file_size = out_file.stat().st_size
        logger.info(f"[Encode API] Success! Output: {output_path_str} ({file_size} bytes)")
        
        return JSONResponse({
            "status": "success",
            "output_path": output_path_str,
            "message": f"Re-encoded: {codec} @ {bitrate}"
        })
    except Exception as e:
        logger.error(f"[Encode API] Encode transform failed: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/chop")
async def manipulate_chop(
    input_path: str = Form(...),
    remove_start: float = Form(0.0),
    remove_end: float = Form(0.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply slice/chop transform."""
    from transforms.chop import slice_chop
    
    input_file = PROJECT_ROOT / input_path
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        out_file = output_path / output_name
    else:
        out_file = output_path / f"{input_file.stem}_chopped.wav"
    
    try:
        slice_chop(input_file, remove_start, remove_end, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Sliced: removed {remove_start}s start, {remove_end}s end"
        })
    except Exception as e:
        logger.error(f"Chop transform failed: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/eq")
async def manipulate_eq(
    input_path: str = Form(...),
    gain_db: float = Form(0.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply EQ adjustment (boost highs or lows based on gain)."""
    try:
        from transforms.eq import boost_highs, boost_lows
        
        input_file = PROJECT_ROOT / input_path
        if not input_file.exists():
            return JSONResponse({
                "status": "error",
                "message": f"Input file not found: {input_path}"
            }, status_code=404)
        
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            # Convert gain_db to int for filename, or use float format
            gain_str = f"{int(gain_db):+d}" if gain_db == int(gain_db) else f"{gain_db:+.1f}"
            out_file = output_path / f"{input_file.stem}_eq_{gain_str}db.wav"
        
        logger.info(f"[EQ Transform API] Applying EQ: input={input_file}, gain_db={gain_db}, output={out_file}")
        
        # Apply boost based on gain sign
        if gain_db > 0:
            boost_highs(input_file, gain_db, out_file)
            message = f"High frequencies boosted by {gain_db} dB"
        elif gain_db < 0:
            boost_lows(input_file, abs(gain_db), out_file)
            message = f"Low frequencies boosted by {abs(gain_db)} dB"
        else:
            # No change, just copy file
            import shutil
            shutil.copy2(input_file, out_file)
            message = "No EQ adjustment (0 dB)"
        
        if not out_file.exists():
            raise Exception(f"Output file was not created: {out_file}")
        
        output_path_str = str(out_file.relative_to(PROJECT_ROOT))
        file_size = out_file.stat().st_size
        logger.info(f"[EQ Transform API] Success! Output: {output_path_str} ({file_size} bytes)")
        logger.info(f"[EQ Transform API] Output path relative to PROJECT_ROOT: {output_path_str}")
        
        return JSONResponse({
            "status": "success",
            "output_path": output_path_str,
            "message": message
        })
    except Exception as e:
        logger.error(f"[EQ Transform API] EQ transform failed: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/eq/highpass")
async def manipulate_eq_highpass(
    input_path: str = Form(...),
    freq_hz: float = Form(150.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply high-pass filter."""
    try:
        from transforms.eq import high_pass_filter
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_highpass_{freq_hz}hz.wav"
        
        high_pass_filter(input_file, freq_hz, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"High-pass filter applied at {freq_hz} Hz"
        })
    except Exception as e:
        logger.error(f"High-pass filter failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/eq/lowpass")
async def manipulate_eq_lowpass(
    input_path: str = Form(...),
    freq_hz: float = Form(6000.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply low-pass filter."""
    try:
        from transforms.eq import low_pass_filter
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_lowpass_{freq_hz}hz.wav"
        
        low_pass_filter(input_file, freq_hz, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Low-pass filter applied at {freq_hz} Hz"
        })
    except Exception as e:
        logger.error(f"Low-pass filter failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/eq/boost-highs")
async def manipulate_eq_boost_highs(
    input_path: str = Form(...),
    gain_db: float = Form(6.0),
    freq_hz: float = Form(3000.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply high-frequency boost."""
    try:
        from transforms.eq import boost_highs
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_boost_highs_{gain_db}db.wav"
        
        boost_highs(input_file, gain_db, out_file, freq_hz=freq_hz)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"High frequencies boosted by {gain_db} dB"
        })
    except Exception as e:
        logger.error(f"Boost highs failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/eq/boost-lows")
async def manipulate_eq_boost_lows(
    input_path: str = Form(...),
    gain_db: float = Form(6.0),
    freq_hz: float = Form(200.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply low-frequency boost."""
    try:
        from transforms.eq import boost_lows
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_boost_lows_{gain_db}db.wav"
        
        boost_lows(input_file, gain_db, out_file, freq_hz=freq_hz)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Low frequencies boosted by {gain_db} dB"
        })
    except Exception as e:
        logger.error(f"Boost lows failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/eq/telephone")
async def manipulate_eq_telephone(
    input_path: str = Form(...),
    low_freq: float = Form(300.0),
    high_freq: float = Form(3000.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply telephone/band-pass filter."""
    try:
        from transforms.eq import telephone_filter
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_telephone.wav"
        
        telephone_filter(input_file, out_file, low_freq=low_freq, high_freq=high_freq)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Telephone filter applied ({low_freq}-{high_freq} Hz)"
        })
    except Exception as e:
        logger.error(f"Telephone filter failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/dynamics/compression")
async def manipulate_compression(
    input_path: str = Form(...),
    threshold_db: float = Form(-10.0),
    ratio: float = Form(10.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply compression."""
    try:
        from transforms.dynamics import apply_compression
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_compressed_{threshold_db}db_{ratio}x.wav"
        
        apply_compression(input_file, threshold_db, ratio, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Compression applied: {threshold_db} dB threshold, {ratio}:1 ratio"
        })
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/dynamics/limiting")
async def manipulate_limiting(
    input_path: str = Form(...),
    ceiling_db: float = Form(-1.0),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply brickwall limiting."""
    try:
        from transforms.dynamics import apply_limiting
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_limited_{ceiling_db}db.wav"
        
        apply_limiting(input_file, ceiling_db, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Brickwall limiting applied at {ceiling_db} dB"
        })
    except Exception as e:
        logger.error(f"Limiting failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/dynamics/multiband")
async def manipulate_multiband(
    input_path: str = Form(...),
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply multiband compression."""
    try:
        from transforms.dynamics import apply_multiband_compression
        
        input_file = PROJECT_ROOT / input_path
        output_path = PROJECT_ROOT / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            out_file = output_path / output_name
        else:
            out_file = output_path / f"{input_file.stem}_multiband.wav"
        
        apply_multiband_compression(input_file, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": "Multiband compression applied"
        })
    except Exception as e:
        logger.error(f"Multiband compression failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/manipulate/chain")
async def manipulate_chain(
    input_path: str = Form(...),
    transforms: str = Form(...),  # JSON string of transform list
    output_dir: str = Form("data/manipulated"),
    output_name: str = Form(None)
):
    """Apply chain of transforms."""
    from transforms.chain import combine_chain
    
    input_file = PROJECT_ROOT / input_path
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_name:
        out_file = output_path / output_name
    else:
        out_file = output_path / f"{input_file.stem}_chain.wav"
    
    try:
        transform_list = json.loads(transforms)
        combine_chain(input_file, transform_list, out_file)
        
        return JSONResponse({
            "status": "success",
            "output_path": str(out_file.relative_to(PROJECT_ROOT)),
            "message": f"Chain of {len(transform_list)} transforms applied"
        })
    except Exception as e:
        logger.error(f"Chain transform failed: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/test/fingerprint")
async def test_fingerprint(
    original_path: str = Form(...),
    manipulated_path: str = Form(...)
):
    """Test if fingerprint can match manipulated audio to original."""
    from fingerprint.load_model import load_fingerprint_model
    from fingerprint.embed import segment_audio, extract_embeddings, normalize_embeddings
    from fingerprint.query_index import build_index, load_index, query_index
    import tempfile
    
    original_file = PROJECT_ROOT / original_path
    manipulated_file = PROJECT_ROOT / manipulated_path
    
    if not original_file.exists():
        return JSONResponse({"status": "error", "message": "Original file not found"}, status_code=404)
    if not manipulated_file.exists():
        return JSONResponse({"status": "error", "message": "Manipulated file not found"}, status_code=404)
    
    try:
        # Load fingerprint model
        fingerprint_config = CONFIG_DIR / "fingerprint_v1.yaml"
        model_config = load_fingerprint_model(fingerprint_config)
        
        # Extract embeddings from both files
        segments_orig = segment_audio(original_file, 
                                     segment_length=model_config["segment_length"],
                                     sample_rate=model_config["sample_rate"])
        embeddings_orig = extract_embeddings(segments_orig, model_config, save_embeddings=False)
        embeddings_orig = normalize_embeddings(embeddings_orig, method="l2")
        
        segments_manip = segment_audio(manipulated_file,
                                      segment_length=model_config["segment_length"],
                                      sample_rate=model_config["sample_rate"])
        embeddings_manip = extract_embeddings(segments_manip, model_config, save_embeddings=False)
        embeddings_manip = normalize_embeddings(embeddings_manip, method="l2")
        
        # Create a temporary index with original embeddings
        index_config_path = CONFIG_DIR / "index_config.json"
        with open(index_config_path, 'r') as f:
            index_config = json.load(f)
        
        # Use original file stem as ID
        orig_id = original_file.stem
        orig_ids = [f"{orig_id}_seg_{i}" for i in range(len(embeddings_orig))]
        
        # Build temporary index
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp_index:
            tmp_index_path = Path(tmp_index.name)
        
        build_index(embeddings_orig, orig_ids, tmp_index_path, index_config, save_metadata=False)
        
        # Load index and query
        index, _ = load_index(tmp_index_path)
        
        # Query with manipulated embeddings (use mean of all segments)
        query_emb = np.mean(embeddings_manip, axis=0) if len(embeddings_manip) > 1 else embeddings_manip[0]
        results = query_index(index, query_emb, topk=10, ids=orig_ids, normalize=True)
        
        # Clean up temp index
        try:
            tmp_index_path.unlink()
        except:
            pass
        
        # Check if original is in results
        matched = False
        rank = None
        similarity = 0.0
        top_match = None
        
        if results and len(results) > 0:
            top_match = results[0].get("id", "")
            similarity = results[0].get("similarity", 0.0)
            
            # Check if any result matches original
            for i, result in enumerate(results):
                result_id = result.get("id", "")
                if orig_id in result_id:
                    matched = True
                    rank = i + 1
                    similarity = result.get("similarity", similarity)
                    break
        
        # Also compute direct cosine similarity
        orig_mean = np.mean(embeddings_orig, axis=0) if len(embeddings_orig) > 1 else embeddings_orig[0]
        direct_similarity = float(np.dot(query_emb, orig_mean))  # Cosine similarity for normalized vectors
        
        return JSONResponse({
            "status": "success",
            "matched": matched or direct_similarity > 0.7,  # Consider matched if similarity > 0.7
            "similarity": float(max(similarity, direct_similarity)),
            "direct_similarity": float(direct_similarity),
            "rank": rank,
            "top_match": top_match,
            "message": f"Fingerprint test: {'MATCHED ✓' if (matched or direct_similarity > 0.7) else 'NOT MATCHED ✗'} (similarity: {max(similarity, direct_similarity):.3f})"
        })
        
    except Exception as e:
        logger.error(f"Fingerprint test failed: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/runs")
async def list_runs():
    """List all test runs."""
    runs = []
    
    if REPORTS_DIR.exists():
        for report_dir in REPORTS_DIR.iterdir():
            if report_dir.is_dir() and report_dir.name.startswith("run_"):
                metrics_file = report_dir / "metrics.json"
                summary_file = report_dir / "suite_summary.csv"
                
                run_info = {
                    "id": report_dir.name,
                    "path": str(report_dir.relative_to(PROJECT_ROOT)),
                    "has_metrics": metrics_file.exists(),
                    "has_summary": summary_file.exists(),
                    "timestamp": report_dir.stat().st_mtime
                }
                
                if metrics_file.exists():
                    try:
                        with open(metrics_file, 'r') as f:
                            metrics = json.load(f)
                            run_info["summary"] = metrics.get("summary", {})
                    except:
                        pass
                
                runs.append(run_info)
    
    return JSONResponse({"runs": sorted(runs, key=lambda x: x["timestamp"], reverse=True)})


@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get detailed run information."""
    report_dir = REPORTS_DIR / run_id
    
    if not report_dir.exists():
        return JSONResponse({"error": "Run not found"}, status_code=404)
    
    details = {
        "id": run_id,
        "path": str(report_dir.relative_to(PROJECT_ROOT)),
        "files": {}
    }
    
    # Load metrics
    metrics_file = report_dir / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            details["metrics"] = json.load(f)
    
    # Load summary
    summary_file = report_dir / "suite_summary.csv"
    if summary_file.exists():
        df = pd.read_csv(summary_file)
        details["summary"] = df.to_dict('records')
    
    return JSONResponse(details)


@app.get("/api/config/test-matrix")
async def get_test_matrix():
    """Get test matrix configuration."""
    config_file = CONFIG_DIR / "test_matrix.yaml"
    
    if not config_file.exists():
        return JSONResponse({"error": "Config not found"}, status_code=404)
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return JSONResponse(config)


@app.post("/api/config/test-matrix")
async def update_test_matrix(config: dict = Body(...)):
    """Update test matrix configuration."""
    config_file = CONFIG_DIR / "test_matrix.yaml"
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    return JSONResponse({"status": "success", "message": "Configuration updated"})


# Legacy endpoints for backward compatibility
@app.get("/runs")
async def list_runs_legacy():
    """Legacy endpoint for listing runs."""
    return await list_runs()


@app.get("/api/files/report")
async def serve_report_html(path: str):
    """Serve report HTML file."""
    file_path = PROJECT_ROOT / path
    
    logger.info(f"[Report API] Requested path: {path}")
    logger.info(f"[Report API] Full file path: {file_path}")
    
    if file_path.exists() and file_path.suffix == ".html":
        logger.info(f"[Report API] Serving report: {file_path}")
        return FileResponse(file_path, media_type="text/html")
    else:
        logger.warning(f"[Report API] Report file not found: {file_path}")
        return JSONResponse({"error": "Report file not found"}, status_code=404)


@app.get("/report/{run_id}")
async def view_report_legacy(request: Request, run_id: str):
    """Legacy endpoint for viewing report."""
    report_dir = REPORTS_DIR / run_id
    
    if not report_dir.exists():
        return JSONResponse({"error": "Report not found"}, status_code=404)
    
    metrics_file = report_dir / "metrics.json"
    metrics = {}
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
    
    summary_file = report_dir / "suite_summary.csv"
    summary_data = None
    if summary_file.exists():
        df = pd.read_csv(summary_file)
        summary_data = df.to_dict('records')
    
    return templates.TemplateResponse("report.html", {
        "request": request,
        "run_id": run_id,
        "metrics": metrics,
        "summary": summary_data
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)