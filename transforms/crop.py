"""Audio cropping transformations for Phase 2 testing."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def crop_segment(
    input_path: Path,
    start_time: float = 0.0,
    duration: float = None,
    out_path: Path = None,
    sample_rate: int = 44100
) -> Path:
    """
    Crop audio to a specific segment.
    
    Args:
        input_path: Input audio file
        start_time: Start time in seconds
        duration: Duration in seconds (None = to end)
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        total_duration = len(y) / sr
        
        # Calculate start and end samples
        start_samples = int(start_time * sr)
        start_samples = max(0, min(start_samples, len(y) - 1))
        
        if duration is None:
            end_samples = len(y)
        else:
            end_samples = start_samples + int(duration * sr)
            end_samples = min(end_samples, len(y))
        
        # Extract segment
        y_cropped = y[start_samples:end_samples]
        
        # Ensure minimum length
        if len(y_cropped) < sr * 0.5:  # Less than 0.5 seconds
            logger.warning(f"Cropped segment too short, using original")
            y_cropped = y
        
        # Save
        if out_path is None:
            duration_str = f"{duration:.1f}s" if duration else "end"
            out_path = input_path.parent / f"{input_path.stem}_crop_{start_time:.1f}s_{duration_str}.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_cropped, sr)
        
        duration_str = f"{duration:.1f}s" if duration else "to end"
        logger.debug(f"Cropped {input_path} (start={start_time:.1f}s, duration={duration_str}) -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Crop failed: {e}")
        raise


def crop_10_seconds(input_path: Path, out_path: Path = None, sample_rate: int = 44100) -> Path:
    """Crop to 10-second clip from start."""
    return crop_segment(input_path, start_time=0.0, duration=10.0, out_path=out_path, sample_rate=sample_rate)


def crop_5_seconds(input_path: Path, out_path: Path = None, sample_rate: int = 44100) -> Path:
    """Crop to 5-second clip from start."""
    return crop_segment(input_path, start_time=0.0, duration=5.0, out_path=out_path, sample_rate=sample_rate)


def crop_middle_segment(input_path: Path, duration: float = 10.0, out_path: Path = None, sample_rate: int = 44100) -> Path:
    """Crop middle segment of specified duration."""
    try:
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        total_duration = len(y) / sr
        
        if total_duration < duration:
            logger.warning(f"Audio shorter than {duration}s, using full audio")
            start_time = 0.0
        else:
            start_time = (total_duration - duration) / 2.0
        
        return crop_segment(input_path, start_time=start_time, duration=duration, out_path=out_path, sample_rate=sample_rate)
    except Exception as e:
        logger.error(f"Crop middle segment failed: {e}")
        raise


def crop_end_segment(input_path: Path, duration: float = 10.0, out_path: Path = None, sample_rate: int = 44100) -> Path:
    """Crop end segment of specified duration."""
    try:
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        total_duration = len(y) / sr
        
        if total_duration < duration:
            logger.warning(f"Audio shorter than {duration}s, using full audio")
            start_time = 0.0
        else:
            start_time = total_duration - duration
        
        return crop_segment(input_path, start_time=start_time, duration=duration, out_path=out_path, sample_rate=sample_rate)
    except Exception as e:
        logger.error(f"Crop end segment failed: {e}")
        raise

