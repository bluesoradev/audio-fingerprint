"""EQ (Equalization) audio transformations for robustness testing."""
import logging
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
from scipy import signal

logger = logging.getLogger(__name__)


def high_pass_filter(
    input_path: Path,
    freq_hz: float,
    out_path: Path,
    sample_rate: int = 44100,
    order: int = 4
) -> Path:
    """
    Apply high-pass filter at specified frequency.
    
    Args:
        input_path: Input audio file
        freq_hz: Cutoff frequency in Hz
        out_path: Output file path
        sample_rate: Sample rate for processing
        order: Filter order (default: 4)
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Design Butterworth high-pass filter
        nyquist = sr / 2.0
        normalized_freq = freq_hz / nyquist
        
        # Ensure frequency is in valid range
        normalized_freq = max(0.01, min(0.99, normalized_freq))
        
        b, a = signal.butter(order, normalized_freq, btype='high', analog=False)
        
        # Apply filter
        y_filtered = signal.filtfilt(b, a, y)
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_filtered, sr)
        
        logger.debug(f"Applied high-pass filter at {freq_hz} Hz to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"High-pass filter failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def low_pass_filter(
    input_path: Path,
    freq_hz: float,
    out_path: Path,
    sample_rate: int = 44100,
    order: int = 4
) -> Path:
    """
    Apply low-pass filter at specified frequency.
    
    Args:
        input_path: Input audio file
        freq_hz: Cutoff frequency in Hz
        out_path: Output file path
        sample_rate: Sample rate for processing
        order: Filter order (default: 4)
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Design Butterworth low-pass filter
        nyquist = sr / 2.0
        normalized_freq = freq_hz / nyquist
        
        # Ensure frequency is in valid range
        normalized_freq = max(0.01, min(0.99, normalized_freq))
        
        b, a = signal.butter(order, normalized_freq, btype='low', analog=False)
        
        # Apply filter
        y_filtered = signal.filtfilt(b, a, y)
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_filtered, sr)
        
        logger.debug(f"Applied low-pass filter at {freq_hz} Hz to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Low-pass filter failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def boost_highs(
    input_path: Path,
    gain_db: float,
    out_path: Path,
    sample_rate: int = 44100,
    freq_hz: float = 3000
) -> Path:
    """
    Boost high frequencies by specified gain in dB.
    
    Args:
        input_path: Input audio file
        gain_db: Gain in dB (positive = boost)
        out_path: Output file path
        sample_rate: Sample rate for processing
        freq_hz: Shelf frequency in Hz (default: 3000)
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Convert dB to linear gain
        linear_gain = 10 ** (gain_db / 20.0)
        
        # Design high-shelving filter
        nyquist = sr / 2.0
        normalized_freq = freq_hz / nyquist
        normalized_freq = max(0.01, min(0.99, normalized_freq))
        
        # Use a simple approach: apply high-pass and blend
        # Create a high-pass filter
        b_hp, a_hp = signal.butter(2, normalized_freq, btype='high', analog=False)
        y_highs = signal.filtfilt(b_hp, a_hp, y)
        
        # Blend original with boosted highs
        y_filtered = y + (y_highs * (linear_gain - 1.0))
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_filtered))
        if max_val > 1.0:
            y_filtered = y_filtered / max_val * 0.99
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_filtered, sr)
        
        logger.debug(f"Boosted highs by {gain_db} dB at {freq_hz} Hz: {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Boost highs failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def boost_lows(
    input_path: Path,
    gain_db: float,
    out_path: Path,
    sample_rate: int = 44100,
    freq_hz: float = 200
) -> Path:
    """
    Boost low frequencies by specified gain in dB.
    
    Args:
        input_path: Input audio file
        gain_db: Gain in dB (positive = boost)
        out_path: Output file path
        sample_rate: Sample rate for processing
        freq_hz: Shelf frequency in Hz (default: 200)
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Convert dB to linear gain
        linear_gain = 10 ** (gain_db / 20.0)
        
        # Design low-shelving filter
        nyquist = sr / 2.0
        normalized_freq = freq_hz / nyquist
        normalized_freq = max(0.01, min(0.99, normalized_freq))
        
        # Use a simple approach: apply low-pass and blend
        # Create a low-pass filter
        b_lp, a_lp = signal.butter(2, normalized_freq, btype='low', analog=False)
        y_lows = signal.filtfilt(b_lp, a_lp, y)
        
        # Blend original with boosted lows
        y_filtered = y + (y_lows * (linear_gain - 1.0))
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_filtered))
        if max_val > 1.0:
            y_filtered = y_filtered / max_val * 0.99
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_filtered, sr)
        
        logger.debug(f"Boosted lows by {gain_db} dB at {freq_hz} Hz: {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Boost lows failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def telephone_filter(
    input_path: Path,
    out_path: Path,
    sample_rate: int = 44100,
    low_freq: float = 300,
    high_freq: float = 3000
) -> Path:
    """
    Apply telephone/band-pass filter (simulates telephone effect).
    
    Args:
        input_path: Input audio file
        out_path: Output file path
        sample_rate: Sample rate for processing
        low_freq: Low cutoff frequency in Hz (default: 300)
        high_freq: High cutoff frequency in Hz (default: 3000)
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Design Butterworth band-pass filter
        nyquist = sr / 2.0
        low_norm = low_freq / nyquist
        high_norm = high_freq / nyquist
        
        # Ensure frequencies are in valid range
        low_norm = max(0.01, min(0.98, low_norm))
        high_norm = max(low_norm + 0.01, min(0.99, high_norm))
        
        b, a = signal.butter(4, [low_norm, high_norm], btype='band', analog=False)
        
        # Apply filter
        y_filtered = signal.filtfilt(b, a, y)
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_filtered, sr)
        
        logger.debug(f"Applied telephone filter ({low_freq}-{high_freq} Hz) to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Telephone filter failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

