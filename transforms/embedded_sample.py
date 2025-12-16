"""Embedded sample detection transformations.

Tests detecting a 1-2 second sample embedded inside a full track.
Supports various positions, volumes, and transformations.
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def embedded_sample(
    sample_path: Path,
    background_path: Path,
    position: str = "start",  # "start", "middle", "end"
    sample_duration: float = 1.5,  # Duration in seconds (1-2 seconds)
    volume_db: float = 0.0,  # Volume relative to background (0 = matched, negative = quieter, positive = louder)
    apply_transform: Optional[str] = None,  # "pitch", "speed", "eq", "compression", None
    transform_params: Optional[dict] = None,
    out_path: Optional[Path] = None,
    sample_rate: int = 44100
) -> Path:
    """
    Embed a 1-2 second sample from sample_path into background_path.
    
    Args:
        sample_path: Path to the sample audio file (Song A segment)
        background_path: Path to the background audio file (full track)
        position: Where to embed ("start", "middle", "end")
        sample_duration: Duration of sample to extract (1-2 seconds)
        volume_db: Volume adjustment in dB (0 = matched, -6 = quieter, +6 = louder)
        apply_transform: Optional transform to apply to sample ("pitch", "speed", "eq", "compression")
        transform_params: Parameters for the transform
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load sample audio
        y_sample, sr_sample = librosa.load(str(sample_path), sr=sample_rate, mono=True)
        sample_duration_actual = len(y_sample) / sr_sample
        
        # Extract segment of desired duration
        if sample_duration_actual > sample_duration:
            # Take first sample_duration seconds
            sample_samples = int(sample_duration * sr_sample)
            y_sample = y_sample[:sample_samples]
        elif sample_duration_actual < sample_duration:
            # Loop or pad if sample is shorter
            repeats = int(np.ceil(sample_duration / sample_duration_actual))
            y_sample = np.tile(y_sample, repeats)[:int(sample_duration * sr_sample)]
        
        # Apply optional transform to sample
        if apply_transform == "pitch":
            semitones = transform_params.get("semitones", 0) if transform_params else 0
            if semitones != 0:
                y_sample = librosa.effects.pitch_shift(y_sample, sr=sample_rate, n_steps=semitones)
        elif apply_transform == "speed":
            speed_ratio = transform_params.get("speed", 1.0) if transform_params else 1.0
            if speed_ratio != 1.0:
                y_sample = librosa.effects.time_stretch(y_sample, rate=speed_ratio)
                # Adjust length back to original duration
                target_samples = int(sample_duration * sr_sample)
                if len(y_sample) > target_samples:
                    y_sample = y_sample[:target_samples]
                elif len(y_sample) < target_samples:
                    y_sample = np.pad(y_sample, (0, target_samples - len(y_sample)), mode='constant')
        elif apply_transform == "eq":
            gain_db = transform_params.get("gain_db", 0.0) if transform_params else 0.0
            if gain_db != 0.0:
                # Simple EQ boost/cut
                gain_linear = 10 ** (gain_db / 20.0)
                y_sample = y_sample * gain_linear
        elif apply_transform == "compression":
            # Apply simple compression
            threshold_db = transform_params.get("threshold_db", -10.0) if transform_params else -10.0
            ratio = transform_params.get("ratio", 4.0) if transform_params else 4.0
            # Simple compression simulation
            threshold_linear = 10 ** (threshold_db / 20.0)
            compressed = np.copy(y_sample)
            mask = np.abs(compressed) > threshold_linear
            compressed[mask] = np.sign(compressed[mask]) * (
                threshold_linear + (np.abs(compressed[mask]) - threshold_linear) / ratio
            )
            y_sample = compressed
        
        # Load background audio
        y_background, sr_background = librosa.load(str(background_path), sr=sample_rate, mono=True)
        
        # Calculate position in background
        background_duration = len(y_background) / sr_background
        sample_samples = len(y_sample)
        
        if position == "start":
            start_sample = 0
        elif position == "middle":
            start_sample = int((background_duration - sample_duration) / 2 * sr_background)
        elif position == "end":
            start_sample = int((background_duration - sample_duration) * sr_background)
        else:
            start_sample = 0
        
        # Ensure we don't exceed background length
        start_sample = max(0, min(start_sample, len(y_background) - sample_samples))
        end_sample = start_sample + sample_samples
        
        # Mix sample into background
        y_mixed = y_background.copy()
        
        # Apply volume adjustment
        volume_gain = 10 ** (volume_db / 20.0)
        y_sample_scaled = y_sample * volume_gain
        
        # Mix
        y_mixed[start_sample:end_sample] = y_mixed[start_sample:end_sample] + y_sample_scaled
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_mixed))
        if max_val > 1.0:
            y_mixed = y_mixed / max_val
        
        # Save
        if out_path is None:
            transform_str = f"_{apply_transform}" if apply_transform else ""
            volume_str = f"_vol{volume_db:.1f}db" if volume_db != 0.0 else ""
            out_path = background_path.parent / f"{background_path.stem}_embedded_{position}_{sample_duration:.1f}s{transform_str}{volume_str}.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_mixed, sr_background)
        
        logger.debug(f"Embedded sample from {sample_path} into {background_path} at {position} (duration={sample_duration:.1f}s, volume={volume_db:.1f}dB) -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Embedded sample failed: {e}")
        raise

