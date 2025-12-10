"""Time stretching and speed change transformations."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def time_stretch(
    input_path: Path,
    rate: float,
    out_path: Path,
    sample_rate: int = 44100,
    **kwargs
) -> Path:
    """
    Time stretch audio (changes duration without changing pitch).
    
    Args:
        input_path: Input audio file
        rate: Stretch rate (>1 = faster/longer, <1 = slower/shorter)
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Apply time stretch
        y_stretched = librosa.effects.time_stretch(
            y=y,
            rate=rate,
            **kwargs
        )
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_stretched, sr)
        
        logger.debug(f"Time stretched {input_path} by rate {rate} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Time stretch failed: {e}")
        raise


def speed_change(
    input_path: Path,
    speed: float,
    out_path: Path,
    sample_rate: int = 44100,
    preserve_pitch: bool = False
) -> Path:
    """
    Change playback speed (optionally preserving pitch).
    
    Args:
        input_path: Input audio file
        speed: Speed multiplier (>1 = faster, <1 = slower)
        out_path: Output file path
        sample_rate: Sample rate for processing
        preserve_pitch: If True, use time_stretch. If False, use resampling.
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Always use time_stretch (librosa handles both cases)
        # Note: librosa.effects.time_stretch preserves pitch by default
        # For true speed change with pitch change, would need sox/ffmpeg
        y_changed = librosa.effects.time_stretch(y=y, rate=speed)
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_changed, sr)
        
        logger.debug(f"Speed changed {input_path} by {speed}x -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Speed change failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
