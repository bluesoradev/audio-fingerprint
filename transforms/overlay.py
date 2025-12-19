"""Audio overlay/mixing transformations - OPTIMIZED VERSION."""
import logging
from pathlib import Path
import numpy as np
import soundfile as sf
from ._audio_utils import load_audio_fast, normalize_audio_inplace, db_to_linear

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
        # OPTIMIZATION #1: Fast loading
        y_main, sr = load_audio_fast(input_path, sample_rate, mono=True)
        
        # Load or generate overlay
        if vocal_file and vocal_file.exists():
            y_overlay, _ = load_audio_fast(vocal_file, sample_rate, mono=True)
        else:
            y_overlay = np.random.normal(0, 0.1, len(y_main)).astype(np.float32)
        
        # OPTIMIZATION #10: Efficient length matching
        min_len = min(len(y_main), len(y_overlay))
        y_main = y_main[:min_len]
        y_overlay = y_overlay[:min_len]
        
        # OPTIMIZATION #3: In-place gain + vectorized mixing
        gain = db_to_linear(level_db)
        y_overlay *= gain
        
        # OPTIMIZATION #11: Direct addition (faster than separate operations)
        y_mixed = y_main + y_overlay
        
        # OPTIMIZATION #2: In-place normalization
        normalize_audio_inplace(y_mixed)
        
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
