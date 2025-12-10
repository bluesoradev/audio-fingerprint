"""Audio slicing and chopping transformations."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def slice_chop(
    input_path: Path,
    remove_start: float = 0.0,
    remove_end: float = 0.0,
    out_path: Path = None,
    sample_rate: int = 44100
) -> Path:
    """
    Remove segments from start and/or end of audio.
    
    Args:
        input_path: Input audio file
        remove_start: Seconds to remove from start
        remove_end: Seconds to remove from end
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load audio
        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        duration = len(y) / sr
        
        # Calculate start and end sample indices
        start_samples = int(remove_start * sr)
        end_samples = int(remove_end * sr)
        
        # Remove segments
        if end_samples > 0:
            y_chopped = y[start_samples:-end_samples] if start_samples > 0 else y[:-end_samples]
        elif start_samples > 0:
            y_chopped = y[start_samples:]
        else:
            y_chopped = y
        
        # Ensure we have at least some audio
        if len(y_chopped) < sr * 0.5:  # Less than 0.5 seconds
            logger.warning(f"Chopped audio too short, using original")
            y_chopped = y
        
        # Save
        if out_path is None:
            out_path = input_path.parent / f"{input_path.stem}_chopped.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_chopped, sr)
        
        logger.debug(f"Chopped {input_path} (removed {remove_start}s start, {remove_end}s end) -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Slice chop failed: {e}")
        raise
