"""DAW project file parser module."""
from .models import (
    DAWMetadata,
    MIDINote,
    MIDITrack,
    ArrangementData,
    TempoChange,
    KeyChange,
    PluginChain,
    SampleSource,
    AutomationData,
    DAWType
)
from .base_parser import BaseDAWParser
from .ableton_parser import AbletonParser
from .flstudio_parser import FLStudioParser
from .logic_parser import LogicParser
from .exceptions import (
    DAWParseError,
    UnsupportedDAWError,
    CorruptedFileError,
    MissingDataError
)

__all__ = [
    "DAWMetadata",
    "MIDINote",
    "MIDITrack",
    "ArrangementData",
    "TempoChange",
    "KeyChange",
    "PluginChain",
    "SampleSource",
    "AutomationData",
    "DAWType",
    "BaseDAWParser",
    "AbletonParser",
    "FLStudioParser",
    "LogicParser",
    "DAWParseError",
    "UnsupportedDAWError",
    "CorruptedFileError",
    "MissingDataError",
]
