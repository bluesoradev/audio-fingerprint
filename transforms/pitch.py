"""Pitch shifting transformations."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def pitch_shift(
    input_path: Path,
    semitones: float,
    out_path: Path,
    sample_rate: int = 44100,
    **kwargs
) -> Path:
    """
    Shift pitch by specified semitones.
    
    Args:
        input_path: Input audio file
        semitones: Semitones to shift (positive = higher, negative = lower)
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Apply pitch shift
        y_shifted = librosa.effects.pitch_shift(
            y=y,
            sr=sr,
            n_steps=semitones,
            **kwargs
        )
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_shifted, sr)
        
        logger.debug(f"Pitch shifted {input_path} by {semitones} semitones -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Pitch shift failed: {e}")
        raise
