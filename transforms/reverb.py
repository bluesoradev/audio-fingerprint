"""Reverb audio transformations for robustness testing - OPTIMIZED VERSION."""
import logging
import numpy as np
import soundfile as sf
from pathlib import Path
from scipy import signal
from ._audio_utils import load_audio_fast, normalize_audio_inplace

logger = logging.getLogger(__name__)


def apply_reverb(
    input_path: Path,
    delay_ms: float,
    out_path: Path = None,
    sample_rate: int = 44100,
    wet_mix: float = 0.3,
    decay: float = 0.5
) -> Path:
    """
    Apply reverb effect using delay lines.
    
    Args:
        input_path: Input audio file
        delay_ms: Reverb delay in milliseconds (0-500ms)
        out_path: Output file path
        sample_rate: Sample rate for processing
        wet_mix: Wet signal mix (0.0-1.0, default: 0.3)
        decay: Reverb decay factor (0.0-1.0, default: 0.5)
        
    Returns:
        Path to output file
    """
    try:
        # OPTIMIZATION #1: Fast loading
        y, sr = load_audio_fast(input_path, sample_rate, mono=True)
        
        if delay_ms <= 0:
            if out_path is None:
                out_path = input_path.parent / f"{input_path.stem}_reverb_0ms.wav"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(out_path), y, sr)
            logger.debug(f"No reverb applied (delay_ms={delay_ms})")
            return out_path
        
        # OPTIMIZATION #16: Pre-compute delay taps
        delay_samples = max(1, min(int((delay_ms / 1000.0) * sr), len(y) - 1))
        delay_taps = [
            delay_samples,
            int(delay_samples * 1.3),
            int(delay_samples * 1.7),
            int(delay_samples * 2.1),
            int(delay_samples * 2.7)
        ]
        delay_taps = [min(d, len(y) - 1) for d in delay_taps if d < len(y)]
        
        # OPTIMIZATION #17: Vectorized reverb application
        y_reverb = y.copy()
        tap_weight = wet_mix / len(delay_taps)
        
        for tap_delay in delay_taps:
            delayed = np.zeros_like(y)
            delayed[tap_delay:] = y[:-tap_delay] * decay
            y_reverb += delayed * tap_weight
        
        # Apply low-pass filter (filtfilt for quality)
        nyquist = sr * 0.5
        cutoff_freq = min(8000.0, nyquist * 0.8)
        normalized_freq = max(0.01, min(0.99, cutoff_freq / nyquist))
        
        b, a = signal.butter(2, normalized_freq, btype='low', analog=False)
        y_reverb = signal.filtfilt(b, a, y_reverb)
        
        # OPTIMIZATION #2: In-place normalization
        normalize_audio_inplace(y_reverb, threshold=0.99)
        
        # Save
        if out_path is None:
            out_path = input_path.parent / f"{input_path.stem}_reverb_{delay_ms:.0f}ms.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_reverb, sr)
        
        logger.debug(f"Applied reverb with {delay_ms}ms delay to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Reverb failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

