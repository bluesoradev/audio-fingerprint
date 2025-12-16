"""Song A inside Song B scenario transformations.

Tests reverse lookup: Song A is in database, Song B is a NEW track
that samples 1-2 seconds from Song A. Can we detect that Song B
contains material from Song A?
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def song_a_in_song_b(
    song_a_path: Path,  # Original song in database
    song_b_base_path: Optional[Path] = None,  # Optional base track for Song B (if None, generates new track)
    sample_start_time: float = 0.0,  # Where to sample from Song A (seconds)
    sample_duration: float = 1.5,  # Duration of sample (1-2 seconds)
    song_b_duration: float = 30.0,  # Duration of new Song B track
    apply_transform: Optional[str] = None,  # Transform to apply to sample ("pitch", "speed", "eq", "compression")
    transform_params: Optional[dict] = None,
    mix_volume_db: float = 0.0,  # Volume of sample in mix (0 = matched, negative = quieter)
    out_path: Optional[Path] = None,
    sample_rate: int = 44100
) -> Path:
    """
    Create Song B by sampling 1-2 seconds from Song A and mixing into a new track.
    
    This simulates a new track (Song B) that samples material from an existing
    track (Song A) in the database.
    
    Args:
        song_a_path: Path to Song A (original track in database)
        song_b_base_path: Optional path to base track for Song B (if None, generates synthetic background)
        sample_start_time: Where to sample from Song A (seconds)
        sample_duration: Duration of sample to extract (1-2 seconds)
        song_b_duration: Total duration of Song B track
        apply_transform: Optional transform to apply to sample
        transform_params: Parameters for the transform
        mix_volume_db: Volume adjustment for sample in mix
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file (Song B)
    """
    try:
        # Load Song A
        y_song_a, sr_a = librosa.load(str(song_a_path), sr=sample_rate, mono=True)
        song_a_duration = len(y_song_a) / sr_a
        
        # Extract sample from Song A
        start_sample = int(sample_start_time * sr_a)
        start_sample = max(0, min(start_sample, len(y_song_a) - 1))
        end_sample = start_sample + int(sample_duration * sr_a)
        end_sample = min(end_sample, len(y_song_a))
        
        y_sample = y_song_a[start_sample:end_sample]
        
        # Ensure sample is exactly sample_duration
        target_samples = int(sample_duration * sr_a)
        if len(y_sample) < target_samples:
            # Pad with silence or loop
            y_sample = np.pad(y_sample, (0, target_samples - len(y_sample)), mode='constant')
        elif len(y_sample) > target_samples:
            y_sample = y_sample[:target_samples]
        
        # Apply optional transform to sample
        if apply_transform == "pitch":
            semitones = transform_params.get("semitones", 0) if transform_params else 0
            if semitones != 0:
                y_sample = librosa.effects.pitch_shift(y_sample, sr=sample_rate, n_steps=semitones)
        elif apply_transform == "speed":
            speed_ratio = transform_params.get("speed", 1.0) if transform_params else 1.0
            if speed_ratio != 1.0:
                y_sample = librosa.effects.time_stretch(y_sample, rate=speed_ratio)
                # Adjust length back
                target_samples = int(sample_duration * sr_a)
                if len(y_sample) > target_samples:
                    y_sample = y_sample[:target_samples]
                elif len(y_sample) < target_samples:
                    y_sample = np.pad(y_sample, (0, target_samples - len(y_sample)), mode='constant')
        elif apply_transform == "eq":
            gain_db = transform_params.get("gain_db", 0.0) if transform_params else 0.0
            if gain_db != 0.0:
                gain_linear = 10 ** (gain_db / 20.0)
                y_sample = y_sample * gain_linear
        elif apply_transform == "compression":
            threshold_db = transform_params.get("threshold_db", -10.0) if transform_params else -10.0
            ratio = transform_params.get("ratio", 4.0) if transform_params else 4.0
            threshold_linear = 10 ** (threshold_db / 20.0)
            compressed = np.copy(y_sample)
            mask = np.abs(compressed) > threshold_linear
            compressed[mask] = np.sign(compressed[mask]) * (
                threshold_linear + (np.abs(compressed[mask]) - threshold_linear) / ratio
            )
            y_sample = compressed
        
        # Create Song B background
        if song_b_base_path and song_b_base_path.exists():
            # Use provided base track
            y_song_b, sr_b = librosa.load(str(song_b_base_path), sr=sample_rate, mono=True)
            song_b_duration_actual = len(y_song_b) / sr_b
            
            # Trim or loop to desired duration
            target_samples_b = int(song_b_duration * sr_b)
            if len(y_song_b) >= target_samples_b:
                y_song_b = y_song_b[:target_samples_b]
            else:
                # Loop to fill duration
                repeats = int(np.ceil(target_samples_b / len(y_song_b)))
                y_song_b = np.tile(y_song_b, repeats)[:target_samples_b]
        else:
            # Generate synthetic background (simple tone + noise)
            target_samples_b = int(song_b_duration * sample_rate)
            # Create a simple background: low-frequency tone + noise
            t = np.linspace(0, song_b_duration, target_samples_b)
            tone_freq = 220.0  # A3 note
            background_tone = 0.3 * np.sin(2 * np.pi * tone_freq * t)
            background_noise = 0.1 * np.random.normal(0, 1, target_samples_b)
            y_song_b = background_tone + background_noise
            # Normalize
            y_song_b = y_song_b / np.max(np.abs(y_song_b)) * 0.5
            sr_b = sample_rate
        
        # Determine where to place sample in Song B (random or start/middle/end)
        # For testing, place at start, middle, or end
        sample_position = transform_params.get("position", "start") if transform_params else "start"
        
        if sample_position == "start":
            mix_start = 0
        elif sample_position == "middle":
            mix_start = int((song_b_duration - sample_duration) / 2 * sample_rate)
        elif sample_position == "end":
            mix_start = int((song_b_duration - sample_duration) * sample_rate)
        else:
            mix_start = 0
        
        mix_start = max(0, min(mix_start, len(y_song_b) - len(y_sample)))
        mix_end = mix_start + len(y_sample)
        
        # Mix sample into Song B
        y_mixed = y_song_b.copy()
        
        # Apply volume adjustment
        volume_gain = 10 ** (mix_volume_db / 20.0)
        y_sample_scaled = y_sample * volume_gain
        
        # Mix
        y_mixed[mix_start:mix_end] = y_mixed[mix_start:mix_end] + y_sample_scaled
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_mixed))
        if max_val > 1.0:
            y_mixed = y_mixed / max_val
        
        # Save
        if out_path is None:
            transform_str = f"_{apply_transform}" if apply_transform else ""
            volume_str = f"_vol{mix_volume_db:.1f}db" if mix_volume_db != 0.0 else ""
            out_path = song_a_path.parent / f"{song_a_path.stem}_sampled_in_song_b_{sample_duration:.1f}s{transform_str}{volume_str}.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_mixed, sr_b)
        
        logger.debug(f"Created Song B from Song A ({song_a_path}): sampled {sample_duration:.1f}s at {sample_start_time:.1f}s -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Song A in Song B failed: {e}")
        raise

