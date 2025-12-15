"""Audio transformation engine for robustness testing."""
from .pitch import pitch_shift
from .speed import time_stretch, speed_change
from .encode import re_encode
from .chop import slice_chop
from .overlay import overlay_vocals
from .noise import add_noise, reduce_noise
from .reverb import apply_reverb
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
from .chain import combine_chain
from .crop import crop_segment, crop_10_seconds, crop_5_seconds, crop_middle_segment, crop_end_segment

__all__ = [
    "pitch_shift",
    "time_stretch",
    "speed_change",
    "re_encode",
    "slice_chop",
    "overlay_vocals",
    "add_noise",
    "reduce_noise",
    "apply_reverb",
    "high_pass_filter",
    "low_pass_filter",
    "boost_highs",
    "boost_lows",
    "telephone_filter",
    "apply_compression",
    "apply_limiting",
    "apply_multiband_compression",
    "combine_chain",
    "crop_segment",
    "crop_10_seconds",
    "crop_5_seconds",
    "crop_middle_segment",
    "crop_end_segment",
]
