"""Noise addition transformations - OPTIMIZED VERSION."""

import logging
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from scipy import signal
from ._audio_utils import load_audio_fast, normalize_audio_inplace

logger = logging.getLogger(__name__)

# OPTIMIZATION #13: Pre-computed pink noise filter coefficients
_PINK_NOISE_B = np.array(
    [0.049922035, -0.095993537, 0.050612699, -0.004408786], dtype=np.float32
)
_PINK_NOISE_A = np.array([1, -2.494956002, 2.017265875, -0.522189400], dtype=np.float32)


def _generate_pink_noise_fast(length: int) -> np.ndarray:
    """
    OPTIMIZATION #13: Fast pink noise using pre-computed IIR filter.
    Avoids FFT overhead while maintaining spectral characteristics.
    """
    white_noise = np.random.normal(0, 1, length).astype(np.float32)
    pink = signal.lfilter(_PINK_NOISE_B, _PINK_NOISE_A, white_noise)
    # Normalize to match white noise power
    return pink / np.std(pink) * np.std(white_noise)


def add_noise(
    input_path: Path,
    snr_db: float,
    noise_type: str = "white",
    out_path: Path = None,
    sample_rate: int = 44100,
    random_seed: int = None,
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

        # OPTIMIZATION #1: Fast loading
        y, sr = load_audio_fast(input_path, sample_rate, mono=True)

        # OPTIMIZATION #14: Vectorized power calculation
        signal_power = np.mean(y**2)

        # Calculate noise power
        snr_linear = 10 ** (snr_db / 10.0)
        noise_power = signal_power / snr_linear
        noise_std = np.sqrt(noise_power)

        # Generate noise
        noise_type_lower = noise_type.lower()
        if noise_type_lower == "white":
            noise = np.random.normal(0, noise_std, len(y)).astype(np.float32)
        elif noise_type_lower == "pink":
            # OPTIMIZATION #13: Fast pink noise
            noise = _generate_pink_noise_fast(len(y))
            noise *= noise_std / np.std(noise)
        elif noise_type_lower in ("vinyl", "crackle"):
            # OPTIMIZATION #15: Vectorized click generation
            noise = np.zeros(len(y), dtype=np.float32)
            num_clicks = int(len(y) / sr * 2)
            if num_clicks > 0:
                click_indices = np.random.choice(
                    len(y), size=min(num_clicks, len(y)), replace=False
                )
                click_length = int(sr * 0.001)

            for idx in click_indices:
                start_idx = max(0, idx - click_length // 2)
                end_idx = min(len(y), idx + click_length // 2)
                click_samples = end_idx - start_idx
                if click_samples > 0:
                    t = np.linspace(0, 1, click_samples, dtype=np.float32)
                click = (
                    np.exp(-t * 50)
                    * np.sin(2 * np.pi * 8000 * t)
                    * np.random.uniform(0.5, 1.5)
                )
                noise[start_idx:end_idx] += click.astype(np.float32)

            # High-pass filtered hiss
            hiss = np.random.normal(0, np.sqrt(noise_power * 0.3), len(y)).astype(
                np.float32
            )
            nyquist = sr * 0.5
            normalized_freq = max(0.01, min(0.99, 5000 / nyquist))
            b, a = signal.butter(4, normalized_freq, btype="high", analog=False)
            hiss = signal.filtfilt(b, a, hiss)
            noise += hiss

            # Scale to desired power
            current_power = np.mean(noise**2)
            if current_power > 0:
                noise *= np.sqrt(noise_power / current_power)
        else:
            noise = np.random.normal(0, noise_std, len(y)).astype(np.float32)

        # OPTIMIZATION #11: Direct addition
        y_noisy = y + noise

        # OPTIMIZATION #2: In-place normalization
        normalize_audio_inplace(y_noisy)

        # Save
        if out_path is None:
            out_path = input_path.parent / f"{input_path.stem}_noise_{snr_db}db.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_noisy, sr)

        logger.debug(
            f"Added {noise_type} noise to {input_path} (SNR {snr_db}dB) -> {out_path}"
        )
        return out_path

    except Exception as e:
        logger.error(f"Add noise failed: {e}")
        raise


def reduce_noise(
    input_path: Path,
    reduction_strength: float,
    out_path: Path = None,
    sample_rate: int = 44100,
    noise_gate_threshold: float = None,
) -> Path:
    """
    Reduce noise from audio using spectral subtraction.

    Args:
        input_path: Input audio file
        reduction_strength: Noise reduction strength (0.0 to 1.0)
                          0.0 = no reduction, 1.0 = maximum reduction
        out_path: Output file path
        sample_rate: Sample rate for processing
        noise_gate_threshold: Optional noise gate threshold in dB (None = auto)

    Returns:
        Path to output file
    """
    try:
        # OPTIMIZATION #1: Fast loading
        y, sr = load_audio_fast(input_path, sample_rate, mono=True)

        # Estimate noise from the first 0.5 seconds (assuming quiet start)
        noise_sample_length = min(int(0.5 * sr), len(y) // 10)
        if noise_sample_length < 1024:
            noise_sample_length = min(1024, len(y))

        noise_sample = y[:noise_sample_length]

        # Compute STFT
        n_fft = 2048
        hop_length = n_fft // 4

        # Get STFT of full signal
        stft = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
        magnitude = np.abs(stft)
        phase = np.angle(stft)

        # Get STFT of noise sample
        noise_stft = librosa.stft(noise_sample, n_fft=n_fft, hop_length=hop_length)
        noise_magnitude = np.abs(noise_stft)

        # Estimate noise power spectrum (average across time)
        noise_power = np.mean(noise_magnitude**2, axis=1, keepdims=True)

        # Estimate signal power spectrum
        signal_power = magnitude**2

        # Spectral subtraction with over-subtraction factor
        # Higher reduction_strength = more aggressive noise removal
        alpha = 1.0 + (reduction_strength * 2.0)  # 1.0 to 3.0
        beta = 0.1 * reduction_strength  # 0.0 to 0.1

        # Subtract noise power from signal power
        enhanced_power = signal_power - alpha * noise_power

        # Apply spectral floor to prevent over-subtraction artifacts
        spectral_floor = beta * noise_power
        enhanced_power = np.maximum(enhanced_power, spectral_floor)

        # Reconstruct magnitude
        enhanced_magnitude = np.sqrt(enhanced_power)

        # Apply noise gate if threshold is provided
        if noise_gate_threshold is not None:
            # Convert threshold from dB to linear
            gate_threshold_linear = 10 ** (noise_gate_threshold / 20.0)
            # Apply gate: set to zero if below threshold
            mask = enhanced_magnitude > (
                gate_threshold_linear * np.max(enhanced_magnitude)
            )
            enhanced_magnitude = enhanced_magnitude * mask

        # Reconstruct STFT
        enhanced_stft = enhanced_magnitude * np.exp(1j * phase)

        # Convert back to time domain
        y_enhanced = librosa.istft(enhanced_stft, hop_length=hop_length, length=len(y))

        # OPTIMIZATION #2: In-place normalization
        normalize_audio_inplace(y_enhanced)

        # Save
        if out_path is None:
            out_path = (
                input_path.parent
                / f"{input_path.stem}_noise_reduced_{reduction_strength:.2f}.wav"
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_enhanced, sr)

        logger.debug(
            f"Reduced noise in {input_path} (strength: {reduction_strength:.2f}) -> {out_path}"
        )
        return out_path

    except Exception as e:
        logger.error(f"Noise reduction failed: {e}")
        raise
