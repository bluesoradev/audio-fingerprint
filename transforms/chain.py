"""Chain multiple transformations together."""
import logging
from pathlib import Path
from typing import List, Dict
import tempfile

logger = logging.getLogger(__name__)


def combine_chain(
    input_path: Path,
    transforms: List[Dict],
    out_path: Path,
    **kwargs
) -> Path:
    """
    Apply multiple transforms in sequence.
    
    Args:
        input_path: Input audio file
        transforms: List of transform dictionaries, each with 'type' and 'params'
        out_path: Final output file path
        **kwargs: Additional parameters
        
    Returns:
        Path to output file
    """
    try:
        from .pitch import pitch_shift
        from .speed import time_stretch
        from .encode import re_encode
        from .chop import slice_chop
        from .overlay import overlay_vocals
        from .noise import add_noise
        
        # Map transform types to functions
        transform_map = {
            "pitch_shift": pitch_shift,
            "time_stretch": time_stretch,
            "re_encode": re_encode,
            "slice_chop": slice_chop,
            "overlay_vocals": overlay_vocals,
            "add_noise": add_noise,
        }
        
        current_path = input_path
        
        # Apply each transform in sequence
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            for i, transform_def in enumerate(transforms):
                transform_type = transform_def.get("type")
                params = transform_def.get("params", {})
                
                if transform_type not in transform_map:
                    logger.warning(f"Unknown transform type: {transform_type}, skipping")
                    continue
                
                transform_fn = transform_map[transform_type]
                
                # Use temp file for intermediate results (except last)
                if i == len(transforms) - 1:
                    next_path = out_path
                else:
                    next_path = tmpdir / f"chain_step_{i}.wav"
                
                # Apply transform
                current_path = transform_fn(current_path, out_path=next_path, **params, **kwargs)
                
                # Update current path for next iteration
                if i < len(transforms) - 1:
                    current_path = next_path
            
            # Ensure final file is in place
            if current_path != out_path and current_path.exists():
                import shutil
                shutil.copy2(current_path, out_path)
        
        logger.debug(f"Applied chain of {len(transforms)} transforms to {input_path} -> {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Chain transform failed: {e}")
        raise
