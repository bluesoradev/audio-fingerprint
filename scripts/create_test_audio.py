"""Create synthetic test audio files for testing the robustness lab."""
import soundfile as sf
import numpy as np
from pathlib import Path
import argparse


def create_test_audio(
    output_path: Path,
    duration_sec: float = 10.0,
    sample_rate: int = 44100,
    frequency: float = 440.0,
    noise_level: float = 0.05
):
    """
    Create a simple test audio file with a sine wave and noise.
    
    Args:
        output_path: Output file path
        duration_sec: Duration in seconds
        sample_rate: Sample rate (Hz)
        frequency: Base frequency (Hz) - defaults to A4 (440Hz)
        noise_level: Noise amplitude (0-1)
    """
    samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, samples)
    
    # Generate a tone with some harmonic content
    signal = np.sin(2 * np.pi * frequency * t) * 0.3
    signal += np.sin(2 * np.pi * frequency * 2 * t) * 0.1  # 2nd harmonic
    signal += np.sin(2 * np.pi * frequency * 3 * t) * 0.05  # 3rd harmonic
    
    # Add some variation in amplitude
    envelope = 1.0 + 0.2 * np.sin(2 * np.pi * 0.5 * t)  # Slow amplitude modulation
    signal *= envelope
    
    # Add noise
    if noise_level > 0:
        signal += np.random.randn(samples) * noise_level
    
    # Normalize to prevent clipping
    max_val = np.max(np.abs(signal))
    if max_val > 1.0:
        signal = signal / max_val * 0.95
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file
    sf.write(str(output_path), signal.astype(np.float32), sample_rate)
    print(f"Created test audio: {output_path}")
    print(f"  Duration: {duration_sec}s")
    print(f"  Sample rate: {sample_rate}Hz")
    print(f"  Frequency: {frequency}Hz")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")


def create_multiple_test_files(output_dir: Path, num_files: int = 3):
    """Create multiple test audio files with different characteristics."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    frequencies = [220, 440, 880]  # A3, A4, A5
    durations = [8.0, 10.0, 12.0]
    
    files_created = []
    
    for i in range(num_files):
        file_id = f"test_track_{i+1}"
        output_path = output_dir / f"{file_id}.wav"
        
        create_test_audio(
            output_path,
            duration_sec=durations[i % len(durations)],
            frequency=frequencies[i % len(frequencies)],
            noise_level=0.03 + (i * 0.02)
        )
        
        files_created.append({
            "id": file_id,
            "title": f"Test Track {i+1}",
            "url": str(output_path),
            "genre": "test"
        })
    
    return files_created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create test audio files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/test_audio"),
        help="Output directory for test audio files"
    )
    parser.add_argument(
        "--num-files",
        type=int,
        default=3,
        help="Number of test files to create"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Duration per file in seconds"
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=440.0,
        help="Base frequency in Hz"
    )
    
    args = parser.parse_args()
    
    if args.num_files > 1:
        files = create_multiple_test_files(args.output_dir, args.num_files)
        print(f"\nCreated {len(files)} test audio files in {args.output_dir}")
    else:
        output_path = args.output_dir / "test_audio.wav"
        create_test_audio(
            output_path,
            duration_sec=args.duration,
            frequency=args.frequency
        )
