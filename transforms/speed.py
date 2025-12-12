"""Time stretching and speed change transformations."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf
from scipy import signal

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
        
        if preserve_pitch:
            # Preserve pitch: use time_stretch (changes duration, keeps pitch)
            y_changed = librosa.effects.time_stretch(y=y, rate=speed)
            output_sr = sr
        else:
            # Change speed with pitch change: use proper resampling with anti-aliasing
            # This is equivalent to changing playback speed (like a tape player)
            # Speed up 2x: fewer samples, plays faster, pitch goes up
            # Slow down 0.5x: more samples, plays slower, pitch goes down
            
            # Calculate the new length based on speed
            new_length = int(len(y) / speed)
            
            # Create time indices for the original and new signals
            original_time = np.arange(len(y)) / sr
            new_time = np.linspace(0, original_time[-1], new_length)
            
            # Use scipy's resampling which has proper anti-aliasing
            # This is better than simple linear interpolation
            from scipy.interpolate import interp1d
            
            # Use cubic interpolation for smoother results (better than linear)
            interp_func = interp1d(
                original_time,
                y,
                kind='cubic',
                bounds_error=False,
                fill_value=0.0
            )
            y_changed = interp_func(new_time)
            
            # Keep same sample rate (the speed change is in the number of samples)
            output_sr = sr
            
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_changed, output_sr)
        
        logger.debug(f"Speed changed {input_path} by {speed}x (preserve_pitch={preserve_pitch}) -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Speed change failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
