"""Audio overlay/mixing transformations."""
import logging
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


def overlay_vocals(
    input_path: Path,
    vocal_file: Path = None,
    level_db: float = -6.0,
    out_path: Path = None,
    sample_rate: int = 44100
) -> Path:
    """
    Overlay vocals or other audio on top of input.
    
    Args:
        input_path: Input audio file (background)
        vocal_file: Path to vocal/overlay audio file (if None, generates silence)
        level_db: Gain in dB for overlay (-6.0 = 6dB quieter)
        out_path: Output file path
        sample_rate: Sample rate for processing
        
    Returns:
        Path to output file
    """
    try:
        # Load main audio
        y_main, sr = librosa.load(str(input_path), sr=sample_rate, mono=True)
        
        # Load or generate overlay
        if vocal_file and vocal_file.exists():
            y_overlay, sr_overlay = librosa.load(str(vocal_file), sr=sample_rate, mono=True)
        else:
            # Generate white noise as placeholder overlay
            y_overlay = np.random.normal(0, 0.1, len(y_main))
        
        # Ensure same length
        min_len = min(len(y_main), len(y_overlay))
        y_main = y_main[:min_len]
        y_overlay = y_overlay[:min_len]
        
        # Convert dB to linear gain
        gain = 10 ** (level_db / 20.0)
        y_overlay = y_overlay * gain
        
        # Mix
        y_mixed = y_main + y_overlay
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(y_mixed))
        if max_val > 1.0:
            y_mixed = y_mixed / max_val
        
        # Save
        if out_path is None:
            out_path = input_path.parent / f"{input_path.stem}_overlay.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), y_mixed, sr)
        
        logger.debug(f"Overlayed {input_path} with vocals (gain {level_db}dB) -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Overlay failed: {e}")
        raise
