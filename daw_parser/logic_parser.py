"""Logic Pro (.logicx) project file parser."""
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

from .base_parser import BaseDAWParser
from .models import (
    DAWMetadata, DAWType, MIDINote, MIDITrack, ArrangementData,
    ClipData, TempoChange, KeyChange, PluginChain, PluginDevice,
    PluginParameter, SampleSource, AutomationData, AutomationPoint
)
from .exceptions import DAWParseError, CorruptedFileError

logger = logging.getLogger(__name__)


class LogicParser(BaseDAWParser):
    """Parser for Logic Pro .logicx project files."""
    
    def __init__(self, file_path: Path):
        """
        Initialize Logic Pro parser.
        
        Args:
            file_path: Path to .logicx file (directory/package)
        """
        super().__init__(file_path)
        self.project_dir = None
        self.xml_root = None
        self._load_project()
    
    def _detect_daw_type(self) -> DAWType:
        """Detect if file is Logic Pro project."""
        if self.file_path.suffix.lower() not in ['.logicx', '.logic']:
            raise ValueError(f"Expected .logicx file, got {self.file_path.suffix}")
        
        # Check if it's a directory (package)
        if not self.file_path.is_dir():
            raise ValueError(f".logicx file must be a directory/package")
        
        return DAWType.LOGIC
    
    def _load_project(self):
        """Load Logic Pro project files."""
        try:
            self.project_dir = Path(self.file_path)
            
            # Find main project XML file
            # Logic Pro stores project data in various XML files
            xml_files = list(self.project_dir.rglob("*.xml"))
            
            if not xml_files:
                # Try alternative locations
                project_data_dir = self.project_dir / "projectdata"
                if project_data_dir.exists():
                    xml_files = list(project_data_dir.rglob("*.xml"))
            
            # Also check for .logic files (older format)
            if not xml_files:
                logic_files = list(self.project_dir.rglob("*.logic"))
                if logic_files:
                    # .logic files might be XML or binary
                    for lf in logic_files:
                        try:
                            tree = ET.parse(lf)
                            xml_files.append(lf)
                            break
                        except ET.ParseError:
                            continue
            
            if not xml_files:
                raise CorruptedFileError(
                    "No XML files found in Logic Pro project",
                    str(self.file_path)
                )
            
            # Load main project file (usually the largest or first)
            # Try to find the main project file
            main_xml = None
            for xml_file in xml_files:
                # Look for common project file names
                if any(name in xml_file.name.lower() for name in ['project', 'main', 'song']):
                    main_xml = xml_file
                    break
            
            # If no main file found, use the first one
            if main_xml is None:
                main_xml = xml_files[0]
            
            tree = ET.parse(main_xml)
            self.xml_root = tree.getroot()
            
            logger.debug(f"Loaded XML from {main_xml}")
            
        except ET.ParseError as e:
            raise CorruptedFileError(
                f"Failed to parse XML: {e}",
                str(self.file_path)
            )
        except Exception as e:
            raise DAWParseError(
                f"Failed to load Logic Pro project: {e}",
                str(self.file_path)
            ) from e
    
    def _extract_version(self) -> str:
        """Extract Logic Pro version."""
        try:
            if self.xml_root is not None:
                # Try various version attributes
                version = (self.xml_root.get('version') or 
                          self.xml_root.get('appVersion') or
                          self.xml_root.get('LogicVersion'))
                
                if version:
                    return version
                
                # Try to find version in document info
                doc_info = self.xml_root.find('.//DocumentInfo') or \
                          self.xml_root.find('.//Version')
                if doc_info is not None:
                    version = doc_info.get('version') or doc_info.text
                    if version:
                        return version
        except Exception:
            pass
        return "Unknown"
    
    def parse(self) -> DAWMetadata:
        """Parse Logic Pro project and extract all metadata."""
        try:
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
                daw_type=DAWType.LOGIC,
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
                f"Failed to parse Logic Pro project: {e}",
                str(self.file_path)
            ) from e
    
    def _extract_midi_data(self) -> List[MIDITrack]:
        """Extract MIDI data from regions."""
        tracks = []
        
        try:
            # Logic Pro stores MIDI in regions
            # Try multiple XPath patterns for different Logic versions
            midi_regions = (self.xml_root.findall('.//MIDIRegion') or
                          self.xml_root.findall('.//Region[@type="MIDI"]') or
                          self.xml_root.findall('.//Region[contains(@class, "MIDI")]') or
                          self.xml_root.findall('.//MIDI'))
            
            track_map = {}
            
            for region in midi_regions:
                # Get track name
                track_name = (region.get('name') or 
                             region.get('trackName') or
                             'Unknown Track')
                
                # Get parent track if available
                parent = region.getparent() if hasattr(region, 'getparent') else None
                if parent is not None:
                    parent_name = parent.get('name')
                    if parent_name:
                        track_name = parent_name
                
                # Extract MIDI notes from region
                notes = []
                note_elements = (region.findall('.//Note') or
                               region.findall('.//MIDINote') or
                               region.findall('.//note'))
                
                for note_elem in note_elements:
                    try:
                        # Try different attribute names
                        note_num = (int(note_elem.get('pitch')) if note_elem.get('pitch') else
                                   int(note_elem.get('note')) if note_elem.get('note') else
                                   int(note_elem.get('key')) if note_elem.get('key') else 60)
                        
                        velocity = (int(note_elem.get('velocity')) if note_elem.get('velocity') else
                                   int(note_elem.get('vel')) if note_elem.get('vel') else 100)
                        
                        start_time = (float(note_elem.get('startTime')) if note_elem.get('startTime') else
                                     float(note_elem.get('start')) if note_elem.get('start') else
                                     float(note_elem.get('time')) if note_elem.get('time') else 0.0)
                        
                        duration = (float(note_elem.get('duration')) if note_elem.get('duration') else
                                  float(note_elem.get('length')) if note_elem.get('length') else
                                  float(note_elem.get('dur')) if note_elem.get('dur') else 1.0)
                        
                        note = MIDINote(
                            note=note_num,
                            velocity=velocity,
                            start_time=start_time,
                            duration=duration,
                            track_name=track_name
                        )
                        notes.append(note)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse MIDI note: {e}")
                        continue
                
                # Group notes by track
                if track_name not in track_map:
                    track_map[track_name] = []
                track_map[track_name].extend(notes)
            
            # Create MIDI tracks
            for track_idx, (track_name, notes) in enumerate(track_map.items()):
                if notes:  # Only create track if it has notes
                    track = MIDITrack(
                        track_name=track_name,
                        track_index=track_idx,
                        notes=notes
                    )
                    tracks.append(track)
            
            logger.info(f"Extracted {len(tracks)} MIDI tracks with {sum(len(t.notes) for t in tracks)} notes")
            
        except Exception as e:
            logger.warning(f"Error extracting MIDI data: {e}")
        
        return tracks
    
    def _extract_arrangement(self) -> ArrangementData:
        """Extract arrangement from Main Sequence."""
        clips = []
        tracks = []
        
        try:
            # Find main sequence/timeline
            sequence = (self.xml_root.find('.//Sequence') or
                       self.xml_root.find('.//MainSequence') or
                       self.xml_root.find('.//Timeline') or
                       self.xml_root)
            
            if sequence is not None:
                # Find tracks
                track_elements = (sequence.findall('.//Track') or
                                sequence.findall('.//AudioTrack') or
                                sequence.findall('.//MIDITrack'))
                
                for track_elem in track_elements:
                    track_name = (track_elem.get('name') or
                                 track_elem.get('trackName') or
                                 'Unknown Track')
                    tracks.append(track_name)
                    
                    # Find regions/clips
                    regions = track_elem.findall('.//Region')
                    
                    for region in regions:
                        try:
                            clip_name = (region.get('name') or
                                        region.get('regionName') or
                                        'Unnamed Clip')
                            
                            start_time = (float(region.get('start')) if region.get('start') else
                                         float(region.get('startTime')) if region.get('startTime') else
                                         float(region.get('position')) if region.get('position') else 0.0)
                            
                            length = (float(region.get('length')) if region.get('length') else
                                     float(region.get('duration')) if region.get('duration') else
                                     float(region.get('regionLength')) if region.get('regionLength') else 0.0)
                            
                            clip_type = (region.get('type') or
                                        region.get('regionType') or
                                        'audio')
                            
                            clip = ClipData(
                                clip_name=clip_name,
                                start_time=start_time,
                                end_time=start_time + length,
                                track_name=track_name,
                                clip_type=clip_type
                            )
                            clips.append(clip)
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Failed to parse clip: {e}")
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
        """Extract tempo changes from Tempo List."""
        tempo_changes = []
        
        try:
            # Find tempo list
            tempo_list = (self.xml_root.find('.//TempoList') or
                         self.xml_root.find('.//Tempo') or
                         self.xml_root.find('.//TempoTrack'))
            
            if tempo_list is not None:
                tempo_events = tempo_list.findall('.//TempoEvent') or tempo_list.findall('.//Event')
                
                for event in tempo_events:
                    try:
                        time = (float(event.get('time')) if event.get('time') else
                               float(event.get('position')) if event.get('position') else 0.0)
                        
                        tempo = (float(event.get('bpm')) if event.get('bpm') else
                                float(event.get('tempo')) if event.get('tempo') else
                                float(event.get('value')) if event.get('value') else 120.0)
                        
                        time_sig = (event.get('timeSignature') or
                                   event.get('timeSig') or
                                   None)
                        
                        tempo_change = TempoChange(
                            time=time,
                            tempo=tempo,
                            time_signature=time_sig
                        )
                        tempo_changes.append(tempo_change)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse tempo change: {e}")
                        continue
            
            # If no tempo changes found, try to get default tempo
            if not tempo_changes:
                default_tempo = (self.xml_root.find('.//Tempo') or
                                self.xml_root.find('.//DefaultTempo'))
                if default_tempo is not None:
                    tempo_value = (float(default_tempo.get('bpm')) if default_tempo.get('bpm') else
                                  float(default_tempo.get('value')) if default_tempo.get('value') else
                                  float(default_tempo.text) if default_tempo.text else 120.0)
                    tempo_changes.append(TempoChange(
                        time=0.0,
                        tempo=tempo_value
                    ))
            
            logger.info(f"Extracted {len(tempo_changes)} tempo changes")
            
        except Exception as e:
            logger.warning(f"Error extracting tempo changes: {e}")
        
        return tempo_changes
    
    def _extract_key_changes(self) -> List[KeyChange]:
        """Extract key signature changes."""
        key_changes = []
        
        try:
            # Logic Pro may store key changes
            key_elements = (self.xml_root.findall('.//KeySignature') or
                          self.xml_root.findall('.//Key') or
                          self.xml_root.findall('.//KeyChange'))
            
            for key_elem in key_elements:
                try:
                    time = (float(key_elem.get('time')) if key_elem.get('time') else
                           float(key_elem.get('position')) if key_elem.get('position') else 0.0)
                    
                    key = (key_elem.get('key') or
                          key_elem.get('value') or
                          key_elem.text or
                          'C major')
                    
                    scale = key_elem.get('scale')
                    
                    key_change = KeyChange(
                        time=time,
                        key=key,
                        scale=scale
                    )
                    key_changes.append(key_change)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse key change: {e}")
                    continue
            
            logger.info(f"Extracted {len(key_changes)} key changes")
            
        except Exception as e:
            logger.warning(f"Error extracting key changes: {e}")
        
        return key_changes
    
    def _extract_plugin_chains(self) -> List[PluginChain]:
        """Extract plugin chains from tracks."""
        chains = []
        
        try:
            # Find all tracks
            tracks = (self.xml_root.findall('.//Track') or
                     self.xml_root.findall('.//AudioTrack') or
                     self.xml_root.findall('.//MIDITrack'))
            
            for track_elem in tracks:
                track_name = (track_elem.get('name') or
                             track_elem.get('trackName') or
                             'Unknown Track')
                devices = []
                
                # Find plugins (AU plugins in Logic)
                plugins = (track_elem.findall('.//Plugin') or
                          track_elem.findall('.//AUPlugin') or
                          track_elem.findall('.//Effect') or
                          track_elem.findall('.//Insert'))
                
                for plugin_elem in plugins:
                    try:
                        device_name = (plugin_elem.get('name') or
                                     plugin_elem.get('pluginName') or
                                     plugin_elem.get('effectName') or
                                     'Unknown Plugin')
                        
                        device_type = (plugin_elem.get('type') or
                                      plugin_elem.get('pluginType') or
                                      'au')
                        
                        # Extract parameters
                        parameters = []
                        param_elements = plugin_elem.findall('.//Parameter')
                        
                        for param_elem in param_elements:
                            try:
                                param_name = (param_elem.get('name') or
                                            param_elem.get('parameterName') or
                                            'Unknown')
                                
                                param_value = (float(param_elem.get('value')) if param_elem.get('value') else
                                             float(param_elem.text) if param_elem.text else 0.0)
                                
                                param = PluginParameter(
                                    parameter_name=param_name,
                                    value=param_value
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
                        logger.debug(f"Failed to parse plugin: {e}")
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
        """Extract audio file references."""
        samples = []
        
        try:
            # Find audio file references
            file_elements = (self.xml_root.findall('.//AudioFile') or
                           self.xml_root.findall('.//FileRef') or
                           self.xml_root.findall('.//Sample') or
                           self.xml_root.findall('.//AudioSample'))
            
            for file_elem in file_elements:
                try:
                    # Try different attribute names for file path
                    file_path_str = (file_elem.get('path') or
                                    file_elem.get('filePath') or
                                    file_elem.get('url') or
                                    file_elem.get('location') or
                                    file_elem.text)
                    
                    if file_path_str:
                        file_path = Path(file_path_str)
                        if not file_path.is_absolute():
                            # Try relative to project directory
                            file_path = self.project_dir / file_path
                        
                        sample_name = file_path.name
                        
                        # Get track name if available
                        parent = file_elem.getparent() if hasattr(file_elem, 'getparent') else None
                        track_name = None
                        if parent is not None:
                            track_name = parent.get('name')
                        
                        sample = SampleSource(
                            file_path=file_path,
                            sample_name=sample_name,
                            track_name=track_name
                        )
                        samples.append(sample)
                except Exception as e:
                    logger.debug(f"Failed to parse sample reference: {e}")
                    continue
            
            logger.info(f"Extracted {len(samples)} sample sources")
            
        except Exception as e:
            logger.warning(f"Error extracting sample sources: {e}")
        
        return samples
    
    def _extract_automation(self) -> List[AutomationData]:
        """Extract automation data."""
        automation_list = []
        
        try:
            # Find automation tracks
            automation_tracks = (self.xml_root.findall('.//AutomationTrack') or
                                self.xml_root.findall('.//Automation') or
                                self.xml_root.findall('.//Envelope'))
            
            for auto_track in automation_tracks:
                try:
                    parameter_name = (auto_track.get('parameterName') or
                                 auto_track.get('parameter') or
                                 auto_track.get('name') or
                                 'Unknown')
                    
                    # Get track name
                    parent = auto_track.getparent() if hasattr(auto_track, 'getparent') else None
                    track_name = 'Unknown'
                    if parent is not None:
                        track_name = (parent.get('name') or
                                     parent.get('trackName') or
                                     'Unknown')
                    
                    # Extract automation points
                    points = []
                    point_elements = (auto_track.findall('.//AutomationPoint') or
                                    auto_track.findall('.//Point') or
                                    auto_track.findall('.//Event'))
                    
                    for point_elem in point_elements:
                        try:
                            time = (float(point_elem.get('time')) if point_elem.get('time') else
                                   float(point_elem.get('position')) if point_elem.get('position') else 0.0)
                            
                            value = (float(point_elem.get('value')) if point_elem.get('value') else
                                    float(point_elem.text) if point_elem.text else 0.0)
                            
                            curve_type = point_elem.get('curveType')
                            
                            point = AutomationPoint(
                                time=time,
                                value=value,
                                curve_type=curve_type
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
                    logger.debug(f"Failed to parse automation: {e}")
                    continue
            
            logger.info(f"Extracted {len(automation_list)} automation tracks")
            
        except Exception as e:
            logger.warning(f"Error extracting automation: {e}")
        
        return automation_list
