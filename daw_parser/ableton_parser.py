"""Ableton Live (.als) project file parser."""
import xml.etree.ElementTree as ET
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from .base_parser import BaseDAWParser
from .models import (
    DAWMetadata, DAWType, MIDINote, MIDITrack, ArrangementData,
    ClipData, TempoChange, KeyChange, PluginChain, PluginDevice,
    PluginParameter, SampleSource, AutomationData, AutomationPoint
)
from .exceptions import DAWParseError, CorruptedFileError

logger = logging.getLogger(__name__)


class AbletonParser(BaseDAWParser):
    """Parser for Ableton Live .als project files."""
    
    def __init__(self, file_path: Path):
        """
        Initialize Ableton parser.
        
        Args:
            file_path: Path to .als file
        """
        super().__init__(file_path)
        self.xml_root = None
        self._load_xml()
    
    def _detect_daw_type(self) -> DAWType:
        """Detect if file is Ableton Live project."""
        if self.file_path.suffix.lower() != '.als':
            raise ValueError(f"Expected .als file, got {self.file_path.suffix}")
        return DAWType.ABLETON
    
    def _load_xml(self):
        """Load XML from .als file (which is a zip file)."""
        try:
            # .als files are actually zip archives containing XML
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                # Find the main XML file (usually "AbletonProject.xml" or similar)
                xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
                if not xml_files:
                    raise CorruptedFileError(
                        "No XML file found in .als archive",
                        str(self.file_path)
                    )
                
                # Use the first XML file (usually the main project file)
                xml_content = zip_ref.read(xml_files[0])
                self.xml_root = ET.fromstring(xml_content)
                logger.debug(f"Loaded XML from {xml_files[0]}")
                
        except zipfile.BadZipFile:
            # Some .als files might be plain XML (older versions)
            try:
                tree = ET.parse(self.file_path)
                self.xml_root = tree.getroot()
                logger.debug("Loaded plain XML file")
            except ET.ParseError as e:
                raise CorruptedFileError(
                    f"Failed to parse XML: {e}",
                    str(self.file_path)
                )
        except Exception as e:
            raise DAWParseError(
                f"Failed to load .als file: {e}",
                str(self.file_path)
            )
    
    def parse(self) -> DAWMetadata:
        """Parse Ableton Live project and extract all metadata."""
        try:
            # Extract version
            version = self._extract_version()
            
            # Extract all data types
            midi_data = self._extract_midi_data()
            arrangement = self._extract_arrangement()
            tempo_changes = self._extract_tempo_changes()
            key_changes = self._extract_key_changes()
            plugin_chains = self._extract_plugin_chains()
            sample_sources = self._extract_sample_sources()
            automation = self._extract_automation()
            
            metadata = DAWMetadata(
                project_path=self.file_path,
                daw_type=DAWType.ABLETON,
                version=version,
                midi_data=midi_data,
                arrangement=arrangement,
                tempo_changes=tempo_changes,
                key_changes=key_changes,
                plugin_chains=plugin_chains,
                sample_sources=sample_sources,
                automation=automation
            )
            
            logger.info(f"Successfully parsed {self.file_path.name}")
            return metadata
            
        except Exception as e:
            raise DAWParseError(
                f"Failed to parse Ableton project: {e}",
                str(self.file_path)
            ) from e
    
    def _extract_version(self) -> str:
        """Extract Ableton Live version."""
        try:
            # Look for version in XML attributes
            if self.xml_root is not None:
                version = self.xml_root.get('Creator', 'Unknown')
                # Extract version number if present
                if 'Ableton Live' in version:
                    # Try to extract version number
                    import re
                    match = re.search(r'(\d+\.\d+)', version)
                    if match:
                        return match.group(1)
                return version
        except Exception:
            pass
        return "Unknown"
    
    def _extract_midi_data(self) -> List[MIDITrack]:
        """Extract MIDI data from Live Clips."""
        tracks = []
        
        try:
            # Find all MIDI tracks
            # In Ableton XML: LiveSet -> Tracks -> MidiTrack
            namespace = {'': 'http://www.ableton.com/schemas/als'}
            
            # Try with namespace first
            midi_tracks = self.xml_root.findall('.//MidiTrack', namespace)
            if not midi_tracks:
                # Try without namespace
                midi_tracks = self.xml_root.findall('.//MidiTrack')
            
            for track_idx, track_elem in enumerate(midi_tracks):
                track_name = track_elem.get('Name', f"Track {track_idx}")
                
                # Extract MIDI notes from clips
                notes = []
                
                # Find clips in this track
                clips = track_elem.findall('.//MidiClip') or track_elem.findall('.//ClipSlot')
                
                for clip in clips:
                    # Extract notes from clip
                    note_elements = clip.findall('.//Note') or clip.findall('.//MidiNote')
                    
                    for note_elem in note_elements:
                        try:
                            note = MIDINote(
                                note=int(note_elem.get('Note', 60)),
                                velocity=int(note_elem.get('Velocity', 100)),
                                start_time=float(note_elem.get('Time', 0.0)),
                                duration=float(note_elem.get('Duration', 1.0)),
                                channel=int(note_elem.get('Channel', 0)),
                                track_name=track_name
                            )
                            notes.append(note)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse MIDI note: {e}")
                            continue
                
                if notes or track_elem is not None:  # Include track even if no notes
                    midi_track = MIDITrack(
                        track_name=track_name,
                        track_index=track_idx,
                        notes=notes
                    )
                    tracks.append(midi_track)
            
            logger.info(f"Extracted {len(tracks)} MIDI tracks with {sum(len(t.notes) for t in tracks)} notes")
            
        except Exception as e:
            logger.warning(f"Error extracting MIDI data: {e}")
        
        return tracks
    
    def _extract_arrangement(self) -> ArrangementData:
        """Extract arrangement timeline data."""
        clips = []
        tracks = []
        
        try:
            # Find ArrangementTracks
            arrangement_tracks = self.xml_root.findall('.//ArrangementTrack') or \
                                 self.xml_root.findall('.//Track')
            
            for track_elem in arrangement_tracks:
                track_name = track_elem.get('Name', 'Unknown Track')
                tracks.append(track_name)
                
                # Find clips in arrangement
                clip_elements = track_elem.findall('.//Clip') or \
                               track_elem.findall('.//AudioClip') or \
                               track_elem.findall('.//MidiClip')
                
                for clip_elem in clip_elements:
                    try:
                        clip = ClipData(
                            clip_name=clip_elem.get('Name', 'Unnamed Clip'),
                            start_time=float(clip_elem.get('Time', 0.0)),
                            end_time=float(clip_elem.get('Time', 0.0)) + float(clip_elem.get('Duration', 0.0)),
                            track_name=track_name,
                            clip_type=clip_elem.tag.replace('Clip', '').lower() or 'audio'
                        )
                        clips.append(clip)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse clip: {e}")
                        continue
            
            # Calculate total length
            total_length = max((c.end_time for c in clips), default=0.0)
            
            logger.info(f"Extracted {len(clips)} clips from {len(tracks)} tracks")
            
        except Exception as e:
            logger.warning(f"Error extracting arrangement: {e}")
        
        return ArrangementData(
            clips=clips,
            total_length=total_length,
            tracks=tracks
        )
    
    def _extract_tempo_changes(self) -> List[TempoChange]:
        """Extract tempo and time signature changes."""
        tempo_changes = []
        
        try:
            # Find tempo automation or tempo master
            tempo_elements = self.xml_root.findall('.//Tempo') or \
                            self.xml_root.findall('.//TempoMasterTimeSignature')
            
            for tempo_elem in tempo_elements:
                try:
                    tempo_change = TempoChange(
                        time=float(tempo_elem.get('Time', 0.0)),
                        tempo=float(tempo_elem.get('Value', 120.0)),
                        time_signature=tempo_elem.get('Numerator') and \
                                      f"{tempo_elem.get('Numerator')}/{tempo_elem.get('Denominator', 4)}"
                    )
                    tempo_changes.append(tempo_change)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse tempo change: {e}")
                    continue
            
            # If no tempo changes found, try to get default tempo
            if not tempo_changes:
                default_tempo = self.xml_root.find('.//Tempo')
                if default_tempo is not None:
                    tempo_changes.append(TempoChange(
                        time=0.0,
                        tempo=float(default_tempo.get('Value', 120.0))
                    ))
            
            logger.info(f"Extracted {len(tempo_changes)} tempo changes")
            
        except Exception as e:
            logger.warning(f"Error extracting tempo changes: {e}")
        
        return tempo_changes
    
    def _extract_key_changes(self) -> List[KeyChange]:
        """Extract key signature changes."""
        key_changes = []
        
        try:
            # Ableton doesn't always store key changes explicitly
            # Look for key-related elements
            key_elements = self.xml_root.findall('.//Key') or \
                          self.xml_root.findall('.//KeySignature')
            
            for key_elem in key_elements:
                try:
                    key_change = KeyChange(
                        time=float(key_elem.get('Time', 0.0)),
                        key=key_elem.get('Value', 'C major')
                    )
                    key_changes.append(key_change)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse key change: {e}")
                    continue
            
            logger.info(f"Extracted {len(key_changes)} key changes")
            
        except Exception as e:
            logger.warning(f"Error extracting key changes: {e}")
        
        return key_changes
    
    def _extract_plugin_chains(self) -> List[PluginChain]:
        """Extract plugin/device chains."""
        chains = []
        
        try:
            # Find all tracks
            tracks = self.xml_root.findall('.//Track') or \
                    self.xml_root.findall('.//MidiTrack') or \
                    self.xml_root.findall('.//AudioTrack')
            
            for track_elem in tracks:
                track_name = track_elem.get('Name', 'Unknown Track')
                devices = []
                
                # Find devices in track
                device_elements = track_elem.findall('.//DeviceChain') or \
                                 track_elem.findall('.//Device')
                
                for device_elem in device_elements:
                    try:
                        device_name = device_elem.get('Name', 'Unknown Device')
                        device_type = device_elem.tag or 'native'
                        
                        # Extract parameters
                        parameters = []
                        param_elements = device_elem.findall('.//Parameter') or \
                                        device_elem.findall('.//Value')
                        
                        for param_elem in param_elements:
                            try:
                                param = PluginParameter(
                                    parameter_name=param_elem.get('Name', 'Unknown'),
                                    value=float(param_elem.get('Value', 0.0))
                                )
                                parameters.append(param)
                            except (ValueError, TypeError):
                                continue
                        
                        device = PluginDevice(
                            device_name=device_name,
                            device_type=device_type,
                            parameters=parameters
                        )
                        devices.append(device)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse device: {e}")
                        continue
                
                if devices:
                    chain = PluginChain(
                        track_name=track_name,
                        devices=devices
                    )
                    chains.append(chain)
            
            logger.info(f"Extracted {len(chains)} plugin chains")
            
        except Exception as e:
            logger.warning(f"Error extracting plugin chains: {e}")
        
        return chains
    
    def _extract_sample_sources(self) -> List[SampleSource]:
        """Extract audio sample references."""
        samples = []
        
        try:
            # Find audio file references
            # Look for SampleRef, AudioFile, or file paths in clips
            file_elements = self.xml_root.findall('.//SampleRef') or \
                          self.xml_root.findall('.//AudioFile') or \
                          self.xml_root.findall('.//FileRef')
            
            for file_elem in file_elements:
                try:
                    # Get file path (could be relative or absolute)
                    file_path_str = file_elem.get('Path') or \
                                   file_elem.get('RelativePath') or \
                                   file_elem.text
                    
                    if file_path_str:
                        # Try to resolve path
                        file_path = Path(file_path_str)
                        if not file_path.is_absolute():
                            # Try relative to project directory
                            file_path = self.file_path.parent / file_path
                        
                        sample = SampleSource(
                            file_path=file_path,
                            sample_name=file_path.name,
                            track_name=file_elem.getparent().get('Name') if hasattr(file_elem, 'getparent') else None
                        )
                        samples.append(sample)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse sample reference: {e}")
                    continue
            
            logger.info(f"Extracted {len(samples)} sample sources")
            
        except Exception as e:
            logger.warning(f"Error extracting sample sources: {e}")
        
        return samples
    
    def _extract_automation(self) -> List[AutomationData]:
        """Extract automation data."""
        automation_list = []
        
        try:
            # Find automation envelopes
            automation_elements = self.xml_root.findall('.//AutomationEnvelope') or \
                                 self.xml_root.findall('.//Envelope')
            
            for auto_elem in automation_elements:
                try:
                    parameter_name = auto_elem.get('ParameterName', 'Unknown')
                    # Get parent track name
                    parent = auto_elem.getparent() if hasattr(auto_elem, 'getparent') else None
                    track_name = parent.get('Name') if parent is not None else 'Unknown'
                    
                    # Extract automation points
                    points = []
                    point_elements = auto_elem.findall('.//Point') or \
                                    auto_elem.findall('.//AutomationPoint')
                    
                    for point_elem in point_elements:
                        try:
                            point = AutomationPoint(
                                time=float(point_elem.get('Time', 0.0)),
                                value=float(point_elem.get('Value', 0.0))
                            )
                            points.append(point)
                        except (ValueError, TypeError):
                            continue
                    
                    if points:
                        automation = AutomationData(
                            parameter_name=parameter_name,
                            track_name=track_name,
                            points=points
                        )
                        automation_list.append(automation)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse automation: {e}")
                    continue
            
            logger.info(f"Extracted {len(automation_list)} automation tracks")
            
        except Exception as e:
            logger.warning(f"Error extracting automation: {e}")
        
        return automation_list
