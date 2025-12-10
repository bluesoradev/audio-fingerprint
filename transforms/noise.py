"""Noise addition transformations."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def add_noise(
    input_path: Path,
    snr_db: float,
    noise_type: str = "white",
    out_path: Path = None,
    sample_rate: int = 44100,
    random_seed: int = None
) -> Path:
    """
    Add noise to audio at specified SNR.
    
    Args:
        input_path: Input audio file
        snr_db: Signal-to-noise ratio in dB
        noise_type: Type of noise ("white", "pink")
        out_path: Output file path
        sample_rate: Sample rate for processing
        random_seed: Random seed for reproducibility
        
    Returns:
        Path to output file
    """
    try:
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Calculate signal power
        signal_power = np.mean(y ** 2)
        
        # Calculate noise power for desired SNR
        snr_linear = 10 ** (snr_db / 10.0)
        noise_power = signal_power / snr_linear
        
        # Generate noise
        if noise_type.lower() == "white":
            noise = np.random.normal(0, np.sqrt(noise_power), len(y))
        elif noise_type.lower() == "pink":
            # Simplified pink noise generation
            white_noise = np.random.normal(0, 1, len(y))
            # Apply simple 1/f filter approximation
            fft = np.fft.fft(white_noise)
            freqs = np.fft.fftfreq(len(y))
            fft_pink = fft / np.sqrt(np.maximum(np.abs(freqs), 1e-10))
            noise = np.real(np.fft.ifft(fft_pink))
            # Scale to desired power
            noise = noise * np.sqrt(noise_power / np.mean(noise ** 2))
        else:
            # Default to white noise
            noise = np.random.normal(0, np.sqrt(noise_power), len(y))
        
        # Add noise
        y_noisy = y + noise
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_noisy))
        if max_val > 1.0:
            y_noisy = y_noisy / max_val
        
        # Save
        if out_path is None:
            out_path = input_path.parent / f"{input_path.stem}_noise_{snr_db}db.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_noisy, sr)
        
        logger.debug(f"Added {noise_type} noise to {input_path} (SNR {snr_db}dB) -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Add noise failed: {e}")
        raise
