"""Data models for DAW metadata extraction."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum


class DAWType(Enum):
    """Supported DAW types."""
    ABLETON = "ableton"
    FLSTUDIO = "flstudio"
    LOGIC = "logic"


@dataclass
class MIDINote:
    """Single MIDI note."""
    note: int  # MIDI note number (0-127)
    velocity: int  # MIDI velocity (0-127)
    start_time: float  # Start time in beats or seconds
    duration: float  # Duration in beats or seconds
    channel: int = 0  # MIDI channel (0-15)
    track_name: Optional[str] = None


@dataclass
class MIDITrack:
    """MIDI track with notes."""
    track_name: str
    track_index: int
    notes: List[MIDINote] = field(default_factory=list)
    instrument: Optional[str] = None
    volume: float = 1.0
    pan: float = 0.0


@dataclass
class ClipData:
    """Audio/MIDI clip in arrangement."""
    clip_name: str
    start_time: float  # Start position in timeline
    end_time: float  # End position in timeline
    track_name: str
    clip_type: str  # "audio", "midi", "automation"
    file_path: Optional[Path] = None


@dataclass
class ArrangementData:
    """Arrangement timeline data."""
    clips: List[ClipData] = field(default_factory=list)
    total_length: float = 0.0  # Total length in seconds
    tracks: List[str] = field(default_factory=list)  # Track names


@dataclass
class TempoChange:
    """Tempo change event."""
    time: float  # Time position in timeline
    tempo: float  # BPM
    time_signature: Optional[str] = None  # e.g., "4/4"


@dataclass
class KeyChange:
    """Key signature change."""
    time: float  # Time position in timeline
    key: str  # e.g., "C major", "A minor"
    scale: Optional[str] = None


@dataclass
class PluginParameter:
    """Plugin parameter value."""
    parameter_name: str
    value: float
    unit: Optional[str] = None


@dataclass
class PluginDevice:
    """Single plugin/device in chain."""
    device_name: str
    device_type: str  # "vst", "au", "native", etc.
    parameters: List[PluginParameter] = field(default_factory=list)
    enabled: bool = True
    device_id: Optional[str] = None


@dataclass
class PluginChain:
    """Plugin chain for a track."""
    track_name: str
    devices: List[PluginDevice] = field(default_factory=list)
    chain_position: int = 0  # Position in signal chain


@dataclass
class SampleSource:
    """Audio sample reference."""
    file_path: Path
    sample_name: str
    track_name: Optional[str] = None
    start_time: Optional[float] = None
    duration: Optional[float] = None
    file_hash: Optional[str] = None


@dataclass
class AutomationPoint:
    """Automation point."""
    time: float
    value: float
    curve_type: Optional[str] = None  # "linear", "bezier", etc.


@dataclass
class AutomationData:
    """Automation data for a parameter."""
    parameter_name: str
    track_name: str
    points: List[AutomationPoint] = field(default_factory=list)
    parameter_id: Optional[str] = None


@dataclass
class DAWMetadata:
    """Complete DAW project metadata."""
    project_path: Path
    daw_type: DAWType
    version: str
    midi_data: List[MIDITrack] = field(default_factory=list)
    arrangement: ArrangementData = field(default_factory=ArrangementData)
    tempo_changes: List[TempoChange] = field(default_factory=list)
    key_changes: List[KeyChange] = field(default_factory=list)
    plugin_chains: List[PluginChain] = field(default_factory=list)
    sample_sources: List[SampleSource] = field(default_factory=list)
    automation: List[AutomationData] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_version: str = "1.0.0"
    raw_metadata: Dict[str, Any] = field(default_factory=dict)  # Store raw extracted data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_path": str(self.project_path),
            "daw_type": self.daw_type.value,
            "version": self.version,
            "midi_tracks": len(self.midi_data),
            "total_notes": sum(len(track.notes) for track in self.midi_data),
            "arrangement_clips": len(self.arrangement.clips),
            "tempo_changes": len(self.tempo_changes),
            "key_changes": len(self.key_changes),
            "plugin_chains": len(self.plugin_chains),
            "sample_sources": len(self.sample_sources),
            "automation_tracks": len(self.automation),
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_version": self.extraction_version
        }
