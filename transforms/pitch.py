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
        logger.info(f"[Pitch Shift Transform] Starting pitch shift: input={input_path}, semitones={semitones}, output={out_path}")
        logger.info(f"[Pitch Shift Transform] Semitones value type: {type(semitones)}, value: {semitones}")
        
        # Load audio
        logger.info(f"[Pitch Shift Transform] Loading audio from {input_path}")
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        logger.info(f"[Pitch Shift Transform] Audio loaded: shape={y.shape}, sample_rate={sr}, duration={len(y)/sr:.2f}s")
        
        # Check if semitones is 0 (no change)
        if abs(semitones) < 0.01:
            logger.warning(f"[Pitch Shift Transform] Semitones value is {semitones} (essentially 0). No pitch change will be applied!")
        
        # Apply pitch shift
        logger.info(f"[Pitch Shift Transform] Applying pitch shift with n_steps={semitones}")
        y_shifted = librosa.effects.pitch_shift(
            y=y,
            sr=sr,
            n_steps=semitones,
            **kwargs
        )
        logger.info(f"[Pitch Shift Transform] Pitch shift applied. Output shape: {y_shifted.shape}")
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"[Pitch Shift Transform] Saving to {out_path}")
        sf.write(str(out_path), y_shifted, sr)
        
        # Verify output file
        if out_path.exists():
            file_size = out_path.stat().st_size
            logger.info(f"[Pitch Shift Transform] Output file saved successfully: {out_path} ({file_size} bytes)")
        else:
            logger.error(f"[Pitch Shift Transform] Output file was not created: {out_path}")
            raise Exception(f"Output file was not created: {out_path}")
        
        logger.info(f"[Pitch Shift Transform] Pitch shifted {input_path} by {semitones} semitones -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"[Pitch Shift Transform] Pitch shift failed: {e}", exc_info=True)
        raise
