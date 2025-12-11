"""Dynamic range compression and limiting transformations for robustness testing."""
import logging
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_compression(
    input_path: Path,
    threshold_db: float,
    ratio: float,
    out_path: Path,
    sample_rate: int = 44100,
    attack_ms: float = 10.0,
    release_ms: float = 100.0
) -> Path:
    """
    Apply heavy compression.
    
    Args:
        input_path: Input audio file
        threshold_db: Threshold in dB (e.g., -10 dB)
        ratio: Compression ratio (e.g., 10:1 = 10.0)
        out_path: Output file path
        sample_rate: Sample rate for processing
        attack_ms: Attack time in milliseconds
        release_ms: Release time in milliseconds
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Convert threshold from dB to linear
        threshold_linear = 10 ** (threshold_db / 20.0)
        
        # Calculate envelope using simple attack/release envelope follower
        attack_coeff = np.exp(-1.0 / (attack_ms * sr / 1000.0))
        release_coeff = np.exp(-1.0 / (release_ms * sr / 1000.0))
        
        envelope = np.zeros_like(y)
        for i in range(1, len(y)):
            abs_sample = abs(y[i])
            if abs_sample > envelope[i-1]:
                envelope[i] = abs_sample + (envelope[i-1] - abs_sample) * attack_coeff
            else:
                envelope[i] = abs_sample + (envelope[i-1] - abs_sample) * release_coeff
        
        # Apply compression
        y_compressed = np.zeros_like(y)
        for i in range(len(y)):
            if envelope[i] > threshold_linear:
                # Signal exceeds threshold: compress
                excess = envelope[i] - threshold_linear
                compressed_excess = excess / ratio
                new_level = threshold_linear + compressed_excess
                
                # Apply gain reduction
                if envelope[i] > 0:
                    gain_reduction = new_level / envelope[i]
                    y_compressed[i] = y[i] * gain_reduction
                else:
                    y_compressed[i] = y[i]
            else:
                # Signal below threshold: no compression
                y_compressed[i] = y[i]
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_compressed))
        if max_val > 1.0:
            y_compressed = y_compressed / max_val * 0.99
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_compressed, sr)
        
        logger.debug(f"Applied compression (threshold={threshold_db}dB, ratio={ratio}:1) to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def apply_limiting(
    input_path: Path,
    ceiling_db: float,
    out_path: Path,
    sample_rate: int = 44100
) -> Path:
    """
    Apply brickwall limiting to specified ceiling level.
    
    Args:
        input_path: Input audio file
        ceiling_db: Ceiling level in dB (e.g., -1 dB)
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Convert ceiling from dB to linear
        ceiling_linear = 10 ** (ceiling_db / 20.0)
        
        # Hard clip at ceiling
        y_limited = np.clip(y, -ceiling_linear, ceiling_linear)
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_limited, sr)
        
        logger.debug(f"Applied brickwall limiting at {ceiling_db} dB to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Limiting failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def apply_multiband_compression(
    input_path: Path,
    out_path: Path,
    sample_rate: int = 44100
) -> Path:
    """
    Apply OTT-style multiband compression.
    
    This splits the audio into low, mid, and high frequency bands,
    compresses each band independently, then recombines them.
    
    Args:
        input_path: Input audio file
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        from scipy import signal
        
        # Split into 3 bands: low (0-400 Hz), mid (400-4000 Hz), high (4000+ Hz)
        nyquist = sr / 2.0
        
        # Low band: 0-400 Hz
        low_freq = 400 / nyquist
        b_low, a_low = signal.butter(4, low_freq, btype='low', analog=False)
        y_low = signal.filtfilt(b_low, a_low, y)
        
        # High band: 4000+ Hz
        high_freq = 4000 / nyquist
        b_high, a_high = signal.butter(4, high_freq, btype='high', analog=False)
        y_high = signal.filtfilt(b_high, a_high, y)
        
        # Mid band: difference (400-4000 Hz)
        y_mid = y - y_low - y_high
        
        # Apply compression to each band
        # Low band: moderate compression
        threshold_low = -15.0  # dB
        ratio_low = 4.0
        y_low_compressed = _apply_simple_compression(y_low, threshold_low, ratio_low, sr)
        
        # Mid band: heavy compression (OTT-style)
        threshold_mid = -12.0  # dB
        ratio_mid = 8.0
        y_mid_compressed = _apply_simple_compression(y_mid, threshold_mid, ratio_mid, sr)
        
        # High band: light compression
        threshold_high = -18.0  # dB
        ratio_high = 3.0
        y_high_compressed = _apply_simple_compression(y_high, threshold_high, ratio_high, sr)
        
        # Recombine bands
        y_multiband = y_low_compressed + y_mid_compressed + y_high_compressed
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_multiband))
        if max_val > 1.0:
            y_multiband = y_multiband / max_val * 0.99
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_multiband, sr)
        
        logger.debug(f"Applied multiband compression to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Multiband compression failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def _apply_simple_compression(
    y: np.ndarray,
    threshold_db: float,
    ratio: float,
    sr: int,
    attack_ms: float = 5.0,
    release_ms: float = 50.0
) -> np.ndarray:
    """Helper function for simple compression."""
    threshold_linear = 10 ** (threshold_db / 20.0)
    
    # Envelope follower
    attack_coeff = np.exp(-1.0 / (attack_ms * sr / 1000.0))
    release_coeff = np.exp(-1.0 / (release_ms * sr / 1000.0))
    
    envelope = np.zeros_like(y)
    for i in range(1, len(y)):
        abs_sample = abs(y[i])
        if abs_sample > envelope[i-1]:
            envelope[i] = abs_sample + (envelope[i-1] - abs_sample) * attack_coeff
        else:
            envelope[i] = abs_sample + (envelope[i-1] - abs_sample) * release_coeff
    
    # Apply compression
    y_compressed = np.zeros_like(y)
    for i in range(len(y)):
        if envelope[i] > threshold_linear:
            excess = envelope[i] - threshold_linear
            compressed_excess = excess / ratio
            new_level = threshold_linear + compressed_excess
            
            if envelope[i] > 0:
                gain_reduction = new_level / envelope[i]
                y_compressed[i] = y[i] * gain_reduction
            else:
                y_compressed[i] = y[i]
        else:
            y_compressed[i] = y[i]
    
    return y_compressed

