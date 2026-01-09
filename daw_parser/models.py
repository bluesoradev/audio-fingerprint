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
    
    def to_dict(self, detailed: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.
        
        Args:
            detailed: If True, includes full detailed data. If False, returns summary counts only.
        """
        base_dict = {
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
        
        if detailed:
            # Include full detailed data
            # Note: Keep count fields (tempo_changes, plugin_chains, sample_sources) as numbers
            # Use separate keys for detailed arrays to avoid overwriting counts
            base_dict.update({
                "midi_data": [
                    {
                        "track_name": track.track_name,
                        "track_index": track.track_index,
                        "instrument": track.instrument,
                        "volume": track.volume,
                        "pan": track.pan,
                        "note_count": len(track.notes),
                        "notes": [
                            {
                                "note": note.note,
                                "velocity": note.velocity,
                                "start_time": note.start_time,
                                "duration": note.duration,
                                "channel": note.channel,
                                "track_name": note.track_name
                            }
                            for note in track.notes
                        ]
                    }
                    for track in self.midi_data
                ],
                "arrangement": {
                    "clips": [
                        {
                            "clip_name": clip.clip_name,
                            "start_time": clip.start_time,
                            "end_time": clip.end_time,
                            "track_name": clip.track_name,
                            "clip_type": clip.clip_type,
                            "file_path": str(clip.file_path) if clip.file_path else None
                        }
                        for clip in self.arrangement.clips
                    ],
                    "tracks": self.arrangement.tracks,
                    "total_length": self.arrangement.total_length
                },
                # Use separate keys for detailed arrays to preserve count fields
                "tempo_changes_data": [
                    {
                        "time": tc.time,
                        "tempo": tc.tempo,
                        "time_signature": tc.time_signature
                    }
                    for tc in self.tempo_changes
                ],
                "key_changes_data": [
                    {
                        "time": kc.time,
                        "key": kc.key,
                        "scale": kc.scale
                    }
                    for kc in self.key_changes
                ],
                "plugin_chains_data": [
                    {
                        "track_name": chain.track_name,
                        "chain_position": chain.chain_position,
                        "device_count": len(chain.devices),
                        "devices": [
                            {
                                "device_name": device.device_name,
                                "device_type": device.device_type,
                                "device_id": device.device_id,
                                "enabled": device.enabled,
                                "parameter_count": len(device.parameters),
                                "parameters": [
                                    {
                                        "parameter_name": param.parameter_name,
                                        "value": param.value,
                                        "unit": param.unit
                                    }
                                    for param in device.parameters
                                ]
                            }
                            for device in chain.devices
                        ]
                    }
                    for chain in self.plugin_chains
                ],
                "sample_sources_data": [
                    {
                        "file_path": str(sample.file_path),
                        "sample_name": sample.sample_name,
                        "track_name": sample.track_name,
                        "start_time": sample.start_time,
                        "duration": sample.duration,
                        "file_hash": sample.file_hash
                    }
                    for sample in self.sample_sources
                ],
                "automation_data": [
                    {
                        "parameter_name": auto.parameter_name,
                        "track_name": auto.track_name,
                        "parameter_id": auto.parameter_id,
                        "point_count": len(auto.points),
                        "points": [
                            {
                                "time": point.time,
                                "value": point.value,
                                "curve_type": point.curve_type
                            }
                            for point in auto.points
                        ]
                    }
                    for auto in self.automation
                ]
            })
        
        return base_dict