"""Reverb audio transformations for robustness testing."""
import logging
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
from scipy import signal

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
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        if delay_ms <= 0:
            # No reverb, just copy input to output
            if out_path is None:
                out_path = input_path.parent / f"{input_path.stem}_reverb_0ms.wav"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(out_path), y, sr)
            logger.debug(f"No reverb applied (delay_ms={delay_ms})")
            return out_path
        
        # Convert delay from milliseconds to samples
        delay_samples = int((delay_ms / 1000.0) * sr)
        
        # Ensure delay is at least 1 sample and not longer than audio
        delay_samples = max(1, min(delay_samples, len(y) - 1))
        
        # Create multiple delay taps for more realistic reverb
        # Use prime numbers for delays to avoid comb filtering
        delay_taps = [
            delay_samples,
            int(delay_samples * 1.3),
            int(delay_samples * 1.7),
            int(delay_samples * 2.1),
            int(delay_samples * 2.7)
        ]
        
        # Limit delay taps to audio length
        delay_taps = [min(d, len(y) - 1) for d in delay_taps if d < len(y)]
        
        # Initialize output with original signal (dry)
        y_reverb = y.copy()
        
        # Apply reverb using multiple delay taps with feedback
        for tap_delay in delay_taps:
            # Create delayed version
            delayed = np.zeros_like(y)
            delayed[tap_delay:] = y[:-tap_delay] * decay
            
            # Add delayed signal to output with reduced amplitude
            y_reverb += delayed * (wet_mix / len(delay_taps))
        
        # Apply low-pass filter to simulate high-frequency damping in reverb
        # This makes the reverb sound more natural
        nyquist = sr / 2.0
        cutoff_freq = min(8000.0, nyquist * 0.8)  # Dampen frequencies above 8kHz
        normalized_freq = cutoff_freq / nyquist
        normalized_freq = max(0.01, min(0.99, normalized_freq))
        
        b, a = signal.butter(2, normalized_freq, btype='low', analog=False)
        y_reverb = signal.filtfilt(b, a, y_reverb)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_reverb))
        if max_val > 1.0:
            y_reverb = y_reverb / max_val * 0.99
        
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

