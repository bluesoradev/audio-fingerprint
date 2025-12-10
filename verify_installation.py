"""Verify installation and dependencies."""
import sys
from pathlib import Path

print("Verifying Audio Fingerprint Robustness Lab installation...")
print("=" * 60)

errors = []
warnings = []

# Check Python version
if sys.version_info < (3, 10):
    errors.append(f"Python 3.10+ required, found {sys.version}")
else:
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# Check required packages
required_packages = [
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("librosa", "librosa"),
    ("soundfile", "soundfile"),
    ("matplotlib", "matplotlib"),
    ("yaml", "pyyaml"),
    ("faiss", "faiss-cpu"),
]

for module_name, package_name in required_packages:
    try:
        __import__(module_name)
        print(f"[OK] {package_name}")
    except ImportError:
        errors.append(f"Missing: {package_name} (pip install {package_name})")

# Check optional packages
optional_packages = [
    ("torch", "torch", "PyTorch (required for MERT)"),
    ("transformers", "transformers", "Transformers (required for MERT)"),
    ("fastapi", "fastapi", "FastAPI (required for UI)"),
    ("uvicorn", "uvicorn", "Uvicorn (required for UI)"),
]

for module_name, package_name, description in optional_packages:
    try:
        __import__(module_name)
        print(f"[OK] {package_name} (optional)")
    except ImportError:
        warnings.append(f"Optional: {package_name} - {description}")

# Check ffmpeg
import subprocess
try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("[OK] ffmpeg")
    else:
        warnings.append("ffmpeg not working properly")
except (FileNotFoundError, subprocess.TimeoutExpired):
    warnings.append("ffmpeg not found (required for encoding transforms)")

# Check directory structure
required_dirs = [
    "config",
    "data/originals",
    "data/transformed",
    "data/manifests",
    "transforms",
    "fingerprint",
    "evaluation",
    "reports",
]

for dir_path in required_dirs:
    path = Path(dir_path)
    if path.exists():
        print(f"[OK] Directory: {dir_path}")
    else:
        warnings.append(f"Directory missing (will be created): {dir_path}")

# Check config files
config_files = [
    "config/fingerprint_v1.yaml",
    "config/test_matrix.yaml",
    "config/index_config.json",
]

for config_file in config_files:
    path = Path(config_file)
    if path.exists():
        print(f"[OK] Config: {config_file}")
    else:
        errors.append(f"Config file missing: {config_file}")

print("=" * 60)

if errors:
    print("\n[ERROR] Issues that must be fixed:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)

if warnings:
    print("\n[WARNING] Optional but recommended:")
    for warning in warnings:
        print(f"  - {warning}")

print("\n[SUCCESS] Installation verified! Ready to run experiments.")
print("\nNext steps:")
print("  1. Prepare your audio files CSV")
print("  2. Configure test_matrix.yaml")
print("  3. Run: python run_experiment.py --config config/test_matrix.yaml --originals your_files.csv")