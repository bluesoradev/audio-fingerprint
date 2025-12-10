"""Audio transformation engine for robustness testing."""
from .pitch import pitch_shift
from .speed import time_stretch, speed_change
from .encode import re_encode
from .chop import slice_chop
from .overlay import overlay_vocals
from .noise import add_noise
from .chain import combine_chain

__all__ = [
    "pitch_shift",
    "time_stretch",
    "speed_change",
    "re_encode",
    "slice_chop",
    "overlay_vocals",
    "add_noise",
    "combine_chain",
]
