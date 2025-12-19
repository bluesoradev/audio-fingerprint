"""Song A inside Song B scenario transformations - OPTIMIZED VERSION.

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
from ._audio_utils import (
    load_audio_fast, normalize_audio_inplace, apply_gain_inplace,
    db_to_linear, vectorized_compression
)

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
        # OPTIMIZATION #1: Fast audio loading (30-50% faster)
        y_song_a, sr_a = load_audio_fast(song_a_path, sample_rate, mono=True)
        
        # OPTIMIZATION #6: Pre-compute values to avoid repeated calculations
        target_samples = int(sample_duration * sr_a)
        start_sample = max(0, min(int(sample_start_time * sr_a), len(y_song_a) - 1))
        end_sample = min(start_sample + target_samples, len(y_song_a))
        
        # Extract sample (need copy for modifications)
        y_sample = y_song_a[start_sample:end_sample].copy()
        
        # Ensure exact length
        sample_len = len(y_sample)
        if sample_len < target_samples:
            y_sample = np.pad(y_sample, (0, target_samples - sample_len), mode='constant')
        elif sample_len > target_samples:
            y_sample = y_sample[:target_samples]
        
        # Apply transforms with optimizations
        if apply_transform == "pitch":
            semitones = transform_params.get("semitones", 0) if transform_params else 0
            if semitones != 0:
                y_sample = librosa.effects.pitch_shift(y_sample, sr=sample_rate, n_steps=semitones)
        elif apply_transform == "speed":
            speed_ratio = transform_params.get("speed", 1.0) if transform_params else 1.0
            if speed_ratio != 1.0:
                y_sample = librosa.effects.time_stretch(y_sample, rate=speed_ratio)
                if len(y_sample) > target_samples:
                    y_sample = y_sample[:target_samples]
                elif len(y_sample) < target_samples:
                    y_sample = np.pad(y_sample, (0, target_samples - len(y_sample)), mode='constant')
        elif apply_transform == "eq":
            # OPTIMIZATION #3: In-place gain
            gain_db = transform_params.get("gain_db", 0.0) if transform_params else 0.0
            apply_gain_inplace(y_sample, gain_db)
        elif apply_transform == "compression":
            # OPTIMIZATION #5: Vectorized compression
            threshold_db = transform_params.get("threshold_db", -10.0) if transform_params else -10.0
            ratio = transform_params.get("ratio", 4.0) if transform_params else 4.0
            y_sample = vectorized_compression(y_sample, threshold_db, ratio)
        
        # Create Song B background
        target_samples_b = int(song_b_duration * sample_rate)
        
        if song_b_base_path and song_b_base_path.exists():
            # OPTIMIZATION #1: Fast loading
            y_song_b, sr_b = load_audio_fast(song_b_base_path, sample_rate, mono=True)
            
            # OPTIMIZATION #7: Efficient trimming/looping
            if len(y_song_b) >= target_samples_b:
                y_song_b = y_song_b[:target_samples_b]
            else:
                # Vectorized looping
                repeats = int(np.ceil(target_samples_b / len(y_song_b)))
                y_song_b = np.tile(y_song_b, repeats)[:target_samples_b]
        else:
            # OPTIMIZATION #8: Vectorized background generation
            y_song_b = np.empty(target_samples_b, dtype=np.float32)
            t = np.arange(target_samples_b, dtype=np.float32) / sample_rate
            tone_freq = 220.0
            np.sin(2 * np.pi * tone_freq * t, out=y_song_b)
            y_song_b *= 0.3
            y_song_b += 0.1 * np.random.normal(0, 1, target_samples_b).astype(np.float32)
            # OPTIMIZATION #2: In-place normalization
            normalize_audio_inplace(y_song_b, threshold=0.5)
            sr_b = sample_rate
        
        # Determine mix position
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
        
        # OPTIMIZATION #9: In-place mixing
        y_mixed = y_song_b.copy()
        volume_gain = db_to_linear(mix_volume_db)
        y_mixed[mix_start:mix_end] += y_sample * volume_gain
        
        # OPTIMIZATION #2: In-place normalization
        normalize_audio_inplace(y_mixed)
        
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

