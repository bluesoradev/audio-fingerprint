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
        from .speed import time_stretch, speed_change
        from .encode import re_encode
        from .chop import slice_chop
        from .overlay import overlay_vocals
        from .noise import add_noise
        from .eq import (
            high_pass_filter,
            low_pass_filter,
            boost_highs,
            boost_lows,
            telephone_filter
        )
        from .dynamics import (
            apply_compression,
            apply_limiting,
            apply_multiband_compression
        )
        
        # Map transform types to functions
        transform_map = {
            "pitch_shift": pitch_shift,
            "time_stretch": time_stretch,
            "speed_change": speed_change,
            "re_encode": re_encode,
            "slice_chop": slice_chop,
            "overlay_vocals": overlay_vocals,
            "add_noise": add_noise,
            "high_pass_filter": high_pass_filter,
            "low_pass_filter": low_pass_filter,
            "boost_highs": boost_highs,
            "boost_lows": boost_lows,
            "telephone_filter": telephone_filter,
            "apply_compression": apply_compression,
            "apply_limiting": apply_limiting,
            "apply_multiband_compression": apply_multiband_compression,
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
                
                # Apply transform - handle different function signatures
                try:
                    # Filter out any invalid kwargs that might cause issues
                    valid_params = {k: v for k, v in params.items() if k not in ["rate", "speed", "semitones", "remove_start", "remove_end", 
                                                                                  "overlay_path", "level_db", "gain_db", "snr_db", "noise_type",
                                                                                  "codec", "bitrate", "preserve_pitch", "out_path"]}
                    
                    if transform_type == "time_stretch":
                        # time_stretch(input_path, rate, out_path, **kwargs)
                        rate = params.get("rate") or params.get("speed")
                        if rate is None:
                            raise ValueError("time_stretch requires 'rate' or 'speed' parameter")
                        # Filter out any remaining speed-related params to avoid passing to librosa
                        clean_params = {k: v for k, v in valid_params.items() if k not in ["speed", "preserve_pitch"]}
                        current_path = transform_fn(current_path, rate, next_path, **clean_params)
                    elif transform_type == "speed_change":
                        # Use the same logic as the individual speed endpoint
                        from .speed import time_stretch, speed_change
                        speed = params.get("speed") or params.get("rate")
                        if speed is None:
                            raise ValueError("speed_change requires 'speed' or 'rate' parameter")
                        # Ensure speed is a float
                        try:
                            speed = float(speed)
                        except (ValueError, TypeError):
                            raise ValueError(f"speed_change: invalid speed value: {speed}")
                        preserve_pitch = params.get("preserve_pitch", False)
                        # Convert preserve_pitch to boolean if it's a string
                        if isinstance(preserve_pitch, str):
                            preserve_pitch = preserve_pitch.lower() in ("true", "1", "yes", "on")
                        preserve_pitch = bool(preserve_pitch)
                        logger.debug(f"Applying speed_change: speed={speed}, preserve_pitch={preserve_pitch}, input={current_path}, output={next_path}")
                        # Use the same logic as manipulate_speed endpoint: time_stretch if preserve_pitch, else speed_change
                        if preserve_pitch:
                            current_path = time_stretch(current_path, speed, next_path)
                        else:
                            current_path = speed_change(current_path, speed, next_path, preserve_pitch=False)
                    elif transform_type == "pitch_shift":
                        # pitch_shift(input_path, semitones, out_path, **kwargs)
                        semitones = params.get("semitones")
                        if semitones is None:
                            raise ValueError("pitch_shift requires 'semitones' parameter")
                        current_path = transform_fn(current_path, semitones, next_path, **valid_params)
                    elif transform_type == "slice_chop":
                        # slice_chop(input_path, remove_start, remove_end, out_path=..., **kwargs)
                        remove_start = params.get("remove_start", 0.0)
                        remove_end = params.get("remove_end", 0.0)
                        current_path = transform_fn(current_path, remove_start, remove_end, out_path=next_path, **valid_params)
                    elif transform_type == "overlay_vocals":
                        # overlay_vocals(input_path, vocal_file, level_db, out_path=..., **kwargs)
                        overlay_path = params.get("overlay_path")
                        gain_db = params.get("level_db") or params.get("gain_db", -6.0)
                        current_path = transform_fn(current_path, overlay_path, gain_db, out_path=next_path, **valid_params)
                    elif transform_type == "add_noise":
                        # add_noise(input_path, snr_db, noise_type, out_path=..., **kwargs)
                        snr_db = params.get("snr_db", 20.0)
                        noise_type = params.get("noise_type", "white")
                        current_path = transform_fn(current_path, snr_db, noise_type, out_path=next_path, **valid_params)
                    elif transform_type == "re_encode":
                        # re_encode(input_path, codec, bitrate, out_path, **kwargs)
                        codec = params.get("codec", "mp3")
                        bitrate = params.get("bitrate", "128k")
                        current_path = transform_fn(current_path, codec, bitrate, next_path, **valid_params)
                    elif transform_type == "high_pass_filter":
                        # high_pass_filter(input_path, freq_hz, out_path, **kwargs)
                        freq_hz = params.get("freq_hz", 150.0)
                        current_path = transform_fn(current_path, freq_hz, next_path, **valid_params)
                    elif transform_type == "low_pass_filter":
                        # low_pass_filter(input_path, freq_hz, out_path, **kwargs)
                        freq_hz = params.get("freq_hz", 6000.0)
                        current_path = transform_fn(current_path, freq_hz, next_path, **valid_params)
                    elif transform_type == "boost_highs":
                        # boost_highs(input_path, gain_db, out_path, **kwargs)
                        gain_db = params.get("gain_db", 6.0)
                        current_path = transform_fn(current_path, gain_db, next_path, **valid_params)
                    elif transform_type == "boost_lows":
                        # boost_lows(input_path, gain_db, out_path, **kwargs)
                        gain_db = params.get("gain_db", 6.0)
                        current_path = transform_fn(current_path, gain_db, next_path, **valid_params)
                    elif transform_type == "telephone_filter":
                        # telephone_filter(input_path, out_path, **kwargs)
                        current_path = transform_fn(current_path, next_path, **valid_params)
                    elif transform_type == "apply_compression":
                        # apply_compression(input_path, threshold_db, ratio, out_path, **kwargs)
                        threshold_db = params.get("threshold_db", -10.0)
                        ratio = params.get("ratio", 10.0)
                        current_path = transform_fn(current_path, threshold_db, ratio, next_path, **valid_params)
                    elif transform_type == "apply_limiting":
                        # apply_limiting(input_path, ceiling_db, out_path, **kwargs)
                        ceiling_db = params.get("ceiling_db", -1.0)
                        current_path = transform_fn(current_path, ceiling_db, next_path, **valid_params)
                    elif transform_type == "apply_multiband_compression":
                        # apply_multiband_compression(input_path, out_path, **kwargs)
                        current_path = transform_fn(current_path, next_path, **valid_params)
                    else:
                        # Generic fallback - try calling with out_path as kwarg
                        current_path = transform_fn(current_path, out_path=next_path, **valid_params)
                except Exception as e:
                    logger.error(f"Error applying {transform_type} (step {i+1}/{len(transforms)}) with params {params}: {e}")
                    logger.error(f"Input file: {current_path}, Output file: {next_path}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise ValueError(f"Failed to apply {transform_type} in chain: {str(e)}") from e
                
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
