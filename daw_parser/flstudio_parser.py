"""FL Studio (.flp) project file parser."""
import struct
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    import pyflp
    PYFLP_AVAILABLE = True
except ImportError:
    PYFLP_AVAILABLE = False
    pyflp = None

from .base_parser import BaseDAWParser
from .models import (
    DAWMetadata, DAWType, MIDINote, MIDITrack, ArrangementData,
    ClipData, TempoChange, KeyChange, PluginChain, PluginDevice,
    PluginParameter, SampleSource, AutomationData, AutomationPoint
)
from .exceptions import DAWParseError, CorruptedFileError

logger = logging.getLogger(__name__)




class FLStudioParser(BaseDAWParser):
    """Parser for FL Studio .flp project files."""
    
    def __init__(self, file_path: Path):
        """
        Initialize FL Studio parser.
        
        Args:
            file_path: Path to .flp file
        """
        super().__init__(file_path)
        self.file_data = None
        self.file_version = None
        self.project = None
        self._load_file()
    
    def _detect_daw_type(self) -> DAWType:
        """Detect if file is FL Studio project."""
        if self.file_path.suffix.lower() != '.flp':
            raise ValueError(f"Expected .flp file, got {self.file_path.suffix}")
        return DAWType.FLSTUDIO
    
    def _load_file(self):
        """Load FL Studio project using pyflp."""
        if not PYFLP_AVAILABLE:
            raise DAWParseError(
                "pyflp library not installed. Install with: pip install pyflp",
                str(self.file_path)
            )
        
        try:
            # Load project using pyflp
            self.project = pyflp.parse(str(self.file_path))
            
            # Also keep raw file data for backward compatibility
            with open(self.file_path, 'rb') as f:
                self.file_data = f.read()
            
            if len(self.file_data) < 4:
                raise CorruptedFileError(
                    "File too small to be valid .flp",
                    str(self.file_path)
                )
            
            # Extract version from project
            self.file_version = self._extract_version()
            
        except Exception as e:
            raise DAWParseError(
                f"Failed to load .flp file: {e}",
                str(self.file_path)
            ) from e
    
    def _read_uint8(self, offset: int) -> int:
        """Read 8-bit unsigned integer."""
        if offset + 1 > len(self.file_data):
            raise IndexError(f"Offset {offset} out of bounds")
        return struct.unpack('<B', self.file_data[offset:offset+1])[0]
    
    def _read_uint16(self, offset: int) -> int:
        """Read 16-bit unsigned integer."""
        if offset + 2 > len(self.file_data):
            raise IndexError(f"Offset {offset} out of bounds")
        return struct.unpack('<H', self.file_data[offset:offset+2])[0]
    
    def _read_uint32(self, offset: int) -> int:
        """Read 32-bit unsigned integer."""
        if offset + 4 > len(self.file_data):
            raise IndexError(f"Offset {offset} out of bounds")
        return struct.unpack('<I', self.file_data[offset:offset+4])[0]
    
    def _read_float(self, offset: int) -> float:
        """Read 32-bit float."""
        if offset + 4 > len(self.file_data):
            raise IndexError(f"Offset {offset} out of bounds")
        return struct.unpack('<f', self.file_data[offset:offset+4])[0]
    
    def _read_double(self, offset: int) -> float:
        """Read 64-bit double."""
        if offset + 8 > len(self.file_data):
            raise IndexError(f"Offset {offset} out of bounds")
        return struct.unpack('<d', self.file_data[offset:offset+8])[0]
    
    def _read_string(self, offset: int, length: Optional[int] = None) -> str:
        """Read string from binary data."""
        if length is None:
            # Read null-terminated string
            end = offset
            while end < len(self.file_data) and self.file_data[end] != 0:
                end += 1
            length = end - offset
        else:
            if offset + length > len(self.file_data):
                raise IndexError(f"Offset {offset} out of bounds")
        
        try:
            return self.file_data[offset:offset+length].decode('utf-8', errors='ignore').rstrip('\x00')
        except Exception:
            return ""
    
    def _find_chunk(self, chunk_id: bytes) -> Optional[int]:
        """Find chunk by ID in file."""
        if len(chunk_id) == 0:
            return None
        
        for i in range(len(self.file_data) - len(chunk_id)):
            if self.file_data[i:i+len(chunk_id)] == chunk_id:
                return i
        return None
    
    def _extract_version(self) -> str:
        """Extract FL Studio version from project."""
        if not self.project:
            return "Unknown"
        
        try:
            # Try multiple ways to get version from pyflp
            if hasattr(self.project, 'version'):
                version = self.project.version
                if version:
                    return str(version)
            
            # Try project properties
            if hasattr(self.project, 'project'):
                proj = self.project.project
                if hasattr(proj, 'version'):
                    version = proj.version
                    if version:
                        return str(version)
            
            # Try header/format version
            if hasattr(self.project, 'format_version'):
                return str(self.project.format_version)
            
            # Try to get from file header if available
            if hasattr(self.project, 'header'):
                header = self.project.header
                if hasattr(header, 'version'):
                    return str(header.version)
            
        except Exception as e:
            logger.debug(f"Error extracting version: {e}")
        
            return "Unknown"
    
    def _inspect_pyflp_structure(self):
        """Inspect actual pyflp structure for debugging."""
        if not self.project:
            logger.warning("No project loaded for inspection")
            return
        
        logger.info("=== PYFLP STRUCTURE INSPECTION ===")
        logger.info(f"Project type: {type(self.project)}")
        logger.info(f"Project attributes: {[x for x in dir(self.project) if not x.startswith('_')]}")
        
        # Inspect patterns
        if hasattr(self.project, 'patterns'):
            patterns = self.project.patterns
            try:
                pattern_count = len(patterns) if patterns else 0
                logger.info(f"\nPatterns: {pattern_count}")
                if patterns and pattern_count > 0:
                    # Convert to list to avoid slicing issues with pyflp custom objects
                    try:
                        patterns_list = list(patterns)
                        max_patterns = min(3, len(patterns_list))
                        for i in range(max_patterns):
                            pattern = patterns_list[i]
                            logger.info(f"\n  Pattern {i}:")
                            logger.info(f"    Type: {type(pattern)}")
                            logger.info(f"    Name: {getattr(pattern, 'name', 'N/A')}")
                            pattern_attrs = [x for x in dir(pattern) if not x.startswith('_')]
                            logger.info(f"    Attributes: {pattern_attrs}")
                            
                            # Check for channels
                            if hasattr(pattern, 'channels'):
                                channels = pattern.channels
                                try:
                                    channel_count = len(channels) if channels else 0
                                    logger.info(f"    Channels: {channel_count}")
                                    if channels and channel_count > 0:
                                        # Convert to list to avoid slicing issues
                                        try:
                                            channels_list = list(channels)
                                            max_channels = min(2, len(channels_list))
                                            for j in range(max_channels):
                                                channel = channels_list[j]
                                                logger.info(f"      Channel {j}:")
                                                logger.info(f"        Type: {type(channel)}")
                                                channel_attrs = [x for x in dir(channel) if not x.startswith('_')]
                                                logger.info(f"        Attributes: {channel_attrs}")
                                                
                                                # Check for notes in various attributes
                                                for attr in ['notes', 'events', 'midi_events', 'items', 'data', 'note_events']:
                                                    if hasattr(channel, attr):
                                                        try:
                                                            notes = getattr(channel, attr)
                                                            if notes is not None:
                                                                try:
                                                                    note_count = len(notes) if hasattr(notes, '__len__') else 'N/A'
                                                                    logger.info(f"        {attr}: {note_count} items")
                                                                    if hasattr(notes, '__len__') and note_count != 'N/A' and note_count > 0:
                                                                        # Convert to list to access first item
                                                                        try:
                                                                            notes_list = list(notes)
                                                                            if notes_list:
                                                                                logger.info(f"          First item type: {type(notes_list[0])}")
                                                                                first_item_attrs = [x for x in dir(notes_list[0]) if not x.startswith('_')]
                                                                                logger.info(f"          First item attributes: {first_item_attrs}")
                                                                                # Try to get actual values
                                                                                item = notes_list[0]
                                                                                for attr_name in ['key', 'note', 'pitch', 'start', 'time', 'velocity', 'vel', 'end', 'duration', 'length']:
                                                                                    if hasattr(item, attr_name):
                                                                                        try:
                                                                                            val = getattr(item, attr_name)
                                                                                            logger.info(f"            {attr_name}: {val}")
                                                                                        except:
                                                                                            pass
                                                                        except Exception as e:
                                                                            logger.info(f"          Error converting notes to list: {e}")
                                                                except Exception as e:
                                                                    logger.info(f"        {attr}: Error getting length - {e}")
                                                        except Exception as e:
                                                            logger.info(f"        {attr}: Error accessing - {e}")
                                        except Exception as e:
                                            logger.info(f"    Channels: Error converting to list - {e}")
                                except Exception as e:
                                    logger.info(f"    Channels: Error accessing - {e}")
                            
                            # Check direct pattern notes - IT'S A GENERATOR!
                            if hasattr(pattern, 'notes'):
                                try:
                                    pattern_notes = pattern.notes
                                    logger.info(f"    Pattern.notes type: {type(pattern_notes)}")
                                    
                                    # Check if it's a generator or iterable
                                    if hasattr(pattern_notes, '__iter__') and not isinstance(pattern_notes, (str, dict)):
                                        logger.info(f"    Pattern.notes is iterable (generator/list)")
                                        try:
                                            # Convert generator to list to inspect
                                            notes_list = list(pattern_notes)
                                            logger.info(f"    Pattern.notes count: {len(notes_list)}")
                                            if notes_list:
                                                first_note = notes_list[0]
                                                logger.info(f"      First note type: {type(first_note)}")
                                                first_note_attrs = [x for x in dir(first_note) if not x.startswith('_')]
                                                logger.info(f"      First note attributes: {first_note_attrs}")
                                                # Try to get actual values
                                                for attr_name in ['key', 'note', 'pitch', 'start', 'time', 'velocity', 'vel', 'end', 'duration', 'length', 'pos', 'position', 'channel']:
                                                    if hasattr(first_note, attr_name):
                                                        try:
                                                            val = getattr(first_note, attr_name)
                                                            logger.info(f"        {attr_name}: {val}")
                                                        except:
                                                            pass
                                        except Exception as e:
                                            logger.info(f"    Error converting pattern.notes generator: {e}")
                                    # Check if it's a dict (channel -> notes mapping) - fallback
                                    elif isinstance(pattern_notes, dict) or hasattr(pattern_notes, 'keys'):
                                        logger.info(f"    Pattern.notes is dict-like")
                                        try:
                                            if hasattr(pattern_notes, 'keys'):
                                                keys = list(pattern_notes.keys())
                                            else:
                                                keys = list(pattern_notes.keys())
                                            logger.info(f"    Pattern.notes keys (channels): {keys[:5] if len(keys) > 5 else keys}")
                                            if keys:
                                                first_key = keys[0]
                                                first_channel_notes = pattern_notes[first_key]
                                                logger.info(f"    Channel {first_key} notes type: {type(first_channel_notes)}")
                                                if hasattr(first_channel_notes, '__len__'):
                                                    logger.info(f"    Channel {first_key} notes count: {len(first_channel_notes)}")
                                        except Exception as e:
                                            logger.info(f"    Error inspecting pattern.notes dict: {e}")
                                    else:
                                        logger.info(f"    Pattern.notes: Unknown type or not accessible")
                                except Exception as e:
                                    logger.info(f"    Pattern.notes: Error accessing - {e}")
                            
                            # Check other pattern attributes
                            for attr in ['events', 'midi_events', 'items', 'data']:
                                if hasattr(pattern, attr):
                                    try:
                                        items = getattr(pattern, attr)
                                        if items is not None:
                                            try:
                                                item_count = len(items) if hasattr(items, '__len__') else 'N/A'
                                                logger.info(f"    Pattern.{attr}: {item_count} items")
                                                if hasattr(items, '__len__') and item_count != 'N/A' and item_count > 0:
                                                    try:
                                                        items_list = list(items)
                                                        if items_list:
                                                            logger.info(f"      First item type: {type(items_list[0])}")
                                                            first_item_attrs = [x for x in dir(items_list[0]) if not x.startswith('_')]
                                                            logger.info(f"      First item attributes: {first_item_attrs}")
                                                    except Exception as e:
                                                        logger.info(f"      Error converting items to list: {e}")
                                            except Exception as e:
                                                logger.info(f"    Pattern.{attr}: Error getting length - {e}")
                                    except Exception as e:
                                        logger.info(f"    Pattern.{attr}: Error accessing - {e}")
                    except Exception as e:
                        logger.warning(f"Error converting patterns to list: {e}")
            except Exception as e:
                logger.warning(f"Error inspecting patterns: {e}")
        
        # Inspect playlist (may fail to parse due to pyflp warning)
        if hasattr(self.project, 'playlist'):
            try:
                playlist = self.project.playlist
                logger.info(f"\nPlaylist:")
                logger.info(f"  Type: {type(playlist)}")
                playlist_attrs = [x for x in dir(playlist) if not x.startswith('_')]
                logger.info(f"  Attributes: {playlist_attrs}")
                
                if hasattr(playlist, 'tracks'):
                    tracks = playlist.tracks
                    try:
                        track_count = len(tracks) if tracks else 0
                        logger.info(f"  Tracks: {track_count}")
                        if tracks and track_count > 0:
                            try:
                                tracks_list = list(tracks)
                                max_tracks = min(2, len(tracks_list))
                                for i in range(max_tracks):
                                    track = tracks_list[i]
                                    logger.info(f"    Track {i}:")
                                    logger.info(f"      Type: {type(track)}")
                                    track_attrs = [x for x in dir(track) if not x.startswith('_')]
                                    logger.info(f"      Attributes: {track_attrs}")
                                    if hasattr(track, 'clips'):
                                        clips = track.clips
                                        try:
                                            clip_count = len(clips) if clips else 0
                                            logger.info(f"      Clips: {clip_count}")
                                            if clips and clip_count > 0:
                                                try:
                                                    clips_list = list(clips)
                                                    if clips_list:
                                                        logger.info(f"        First clip type: {type(clips_list[0])}")
                                                        logger.info(f"        First clip attributes: {[x for x in dir(clips_list[0]) if not x.startswith('_')]}")
                                                except Exception as e:
                                                    logger.info(f"        Error converting clips to list: {e}")
                                        except Exception as e:
                                            logger.info(f"      Clips: Error accessing - {e}")
                            except Exception as e:
                                logger.info(f"  Tracks: Error converting to list - {e}")
                    except Exception as e:
                        logger.info(f"  Tracks: Error accessing - {e}")
                
                # Check for direct clips
                if hasattr(playlist, 'clips'):
                    try:
                        clips = playlist.clips
                        clip_count = len(clips) if clips else 0
                        logger.info(f"  Direct clips: {clip_count}")
                    except Exception as e:
                        logger.info(f"  Direct clips: Error accessing - {e}")
            except Exception as e:
                logger.warning(f"Error inspecting playlist (may be due to parsing warning): {e}")
        
        # Also check arrangements (alternative to playlist - more reliable)
        if hasattr(self.project, 'arrangements'):
            try:
                arrangements = self.project.arrangements
                if arrangements:
                    arr_list = list(arrangements)
                    logger.info(f"\nArrangements: {len(arr_list)}")
                    if arr_list:
                        arr = arr_list[0]
                        logger.info(f"  First arrangement type: {type(arr)}")
                        arr_attrs = [x for x in dir(arr) if not x.startswith('_')]
                        logger.info(f"  First arrangement attributes: {arr_attrs}")
                        
                        # Method 1: Try arrangement.events (may be more accessible than tracks)
                        if hasattr(arr, 'events'):
                            try:
                                arr_events = arr.events
                                logger.info(f"  Arrangement events: {type(arr_events)}")
                                if arr_events:
                                    # Try to iterate events
                                    try:
                                        if hasattr(arr_events, '__iter__') and not isinstance(arr_events, (str, dict)):
                                            events_iter = iter(arr_events)
                                            try:
                                                first_event = next(events_iter)
                                                logger.info(f"    First event type: {type(first_event)}")
                                                event_attrs = [x for x in dir(first_event) if not x.startswith('_')]
                                                logger.info(f"    First event attributes: {event_attrs[:10]}")  # Limit to first 10
                                                # Try to get key attributes
                                                for attr in ['pattern', 'pattern_id', 'start', 'position', 'time', 'length', 'track', 'channel']:
                                                    if hasattr(first_event, attr):
                                                        try:
                                                            val = getattr(first_event, attr)
                                                            logger.info(f"      Event.{attr}: {val}")
                                                        except:
                                                            pass
                                            except StopIteration:
                                                logger.info(f"    Arrangement events: empty")
                                            except Exception as e:
                                                logger.info(f"    Error accessing first event: {e}")
                                    except Exception as e:
                                        logger.info(f"    Error iterating arrangement events: {e}")
                            except Exception as e:
                                logger.info(f"    Error accessing arrangement.events: {e}")
                        
                        # Method 2: Check tracks in arrangement (it's a generator! May be PlaylistEvent objects)
                        # NOTE: This may fail due to pyflp limitation with PlaylistEvent.data attribute
                        if hasattr(arr, 'tracks'):
                            arr_tracks = arr.tracks
                            try:
                                # Try to access tracks, but catch the iteration error
                                if hasattr(arr_tracks, '__iter__') and not isinstance(arr_tracks, (str, dict)):
                                    # Try to get first item, but expect it might fail
                                    try:
                                        tracks_iter = iter(arr_tracks)
                                        first_track = next(tracks_iter)
                                        track_count = 1
                                        # Count remaining items
                                        try:
                                            for _ in tracks_iter:
                                                track_count += 1
                                        except Exception as e:
                                            pass  # Stop counting if iteration fails
                                        
                                        logger.info(f"  Arrangement tracks: {track_count}")
                                        logger.info(f"    First track type: {type(first_track)}")
                                        track_attrs = [x for x in dir(first_track) if not x.startswith('_')]
                                        logger.info(f"    First track attributes: {track_attrs[:10]}")  # Limit to first 10
                                        
                                        # Check if it's a PlaylistEvent (not a Track)
                                        if 'PlaylistEvent' in str(type(first_track)) or 'Event' in str(type(first_track)):
                                            logger.info(f"    NOTE: Tracks are PlaylistEvent objects, not Track objects")
                                            # Try to extract clip data from event
                                            for attr in ['pattern', 'pattern_id', 'start', 'position', 'time', 'length', 'duration', 'end', 'clip', 'item', 'track', 'track_id', 'channel']:
                                                if hasattr(first_track, attr):
                                                    try:
                                                        val = getattr(first_track, attr)
                                                        logger.info(f"      Event.{attr}: {val}")
                                                    except:
                                                        pass
                                        else:
                                            # It's a Track object
                                            if hasattr(first_track, 'clips'):
                                                track_clips = first_track.clips
                                                try:
                                                    # Clips might also be a generator - iterate directly
                                                    if hasattr(track_clips, '__iter__') and not isinstance(track_clips, (str, dict)):
                                                        clips_iter = iter(track_clips)
                                                        try:
                                                            first_clip = next(clips_iter)
                                                            clip_count = 1
                                                            for _ in clips_iter:
                                                                clip_count += 1
                                                            logger.info(f"    First track clips: {clip_count}")
                                                            logger.info(f"      First clip type: {type(first_clip)}")
                                                            logger.info(f"      First clip attributes: {[x for x in dir(first_clip) if not x.startswith('_')][:10]}")
                                                        except StopIteration:
                                                            logger.info(f"    First track clips: 0")
                                                        except Exception as e:
                                                            logger.info(f"    Error iterating track clips: {e}")
                                                    else:
                                                        clip_count = len(track_clips) if track_clips else 0
                                                        logger.info(f"    First track clips: {clip_count}")
                                                except Exception as e:
                                                    logger.info(f"    Error accessing track clips: {e}")
                                    except Exception as e:
                                        error_msg = str(e)
                                        if "'data'" in error_msg or "PlaylistEvent" in error_msg:
                                            logger.info(f"    NOTE: Cannot iterate arrangement.tracks due to pyflp limitation: {error_msg}")
                                            logger.info(f"    Will try alternative methods (arrangement.events or project.playlist)")
                                        else:
                                            logger.info(f"    Error iterating arrangement tracks: {e}")
                                else:
                                    track_count = len(arr_tracks) if arr_tracks else 0
                                    logger.info(f"  Arrangement tracks: {track_count}")
                            except Exception as e:
                                logger.info(f"    Error accessing arrangement tracks: {e}")
            except Exception as e:
                logger.info(f"  Arrangements: Error accessing - {e}")
        
        # Inspect automation - check multiple locations
        logger.info("\n=== AUTOMATION INSPECTION ===")
        
        # Method 1: Check project-level automation attributes
        for attr in ['automation_clips', 'automation', 'auto_clips', 'automation_tracks', 'envelopes', 'modulation']:
            if hasattr(self.project, attr):
                try:
                    auto = getattr(self.project, attr)
                    if isinstance(auto, (list, tuple)):
                        logger.info(f"project.{attr}: {len(auto)} items")
                        if len(auto) > 0:
                            logger.info(f"  First item type: {type(auto[0])}")
                            logger.info(f"  First item attributes: {[x for x in dir(auto[0]) if not x.startswith('_')][:10]}")
                    else:
                        logger.info(f"project.{attr}: {type(auto)}")
                        if hasattr(auto, 'clips'):
                            try:
                                clips = auto.clips
                                if hasattr(clips, '__len__'):
                                    logger.info(f"  {attr}.clips: {len(clips)} items")
                                else:
                                    logger.info(f"  {attr}.clips: {type(clips)}")
                            except:
                                pass
                except Exception as e:
                    logger.info(f"project.{attr}: Error accessing - {e}")
        
        # Method 2: Check arrangement.events for automation events
        if hasattr(self.project, 'arrangements'):
            try:
                arrangements = self.project.arrangements
                if arrangements:
                    arr_list = list(arrangements) if hasattr(arrangements, '__iter__') else [arrangements]
                    if arr_list:
                        arr = arr_list[0]
                        if hasattr(arr, 'events'):
                            try:
                                arr_events = arr.events
                                logger.info(f"arrangement.events: {type(arr_events)}")
                                # Check for automation-related events
                                if hasattr(arr_events, '__iter__'):
                                    try:
                                        auto_event_count = 0
                                        event_types_found = {}
                                        event_ids_found = set()
                                        sample_events = []
                                        
                                        for event in arr_events:
                                            try:
                                                event_type = str(type(event))
                                                event_id = getattr(event, 'id', None)
                                                
                                                # Track all event types
                                                event_type_name = event_type.split("'")[1] if "'" in event_type else event_type
                                                event_types_found[event_type_name] = event_types_found.get(event_type_name, 0) + 1
                                                
                                                if event_id is not None:
                                                    event_ids_found.add(str(event_id))
                                                
                                                # Check for automation-related keywords (broader search)
                                                is_automation = (
                                                    'Automation' in event_type or 
                                                    'Auto' in event_type or 
                                                    'Envelope' in event_type or
                                                    'Modulation' in event_type or
                                                    'Controller' in event_type or
                                                    (event_id and ('Auto' in str(event_id) or 'Env' in str(event_id) or 'Mod' in str(event_id)))
                                                )
                                                
                                                if is_automation:
                                                    auto_event_count += 1
                                                    if auto_event_count <= 3:  # Show first 3 automation events
                                                        logger.info(f"  Found automation event #{auto_event_count}: {event_type}")
                                                        logger.info(f"    Event ID: {event_id}")
                                                        event_attrs = [x for x in dir(event) if not x.startswith('_')]
                                                        logger.info(f"    Event attributes: {event_attrs[:15]}")
                                                        # Try to get key values
                                                        for attr in ['parameter', 'parameter_name', 'name', 'target', 'value', 'time', 'position']:
                                                            if hasattr(event, attr):
                                                                try:
                                                                    val = getattr(event, attr)
                                                                    logger.info(f"    {attr}: {val}")
                                                                except:
                                                                    pass
                                                
                                                # Collect sample events for analysis
                                                if len(sample_events) < 5:
                                                    sample_events.append({
                                                        'type': event_type_name,
                                                        'id': event_id,
                                                        'attrs': [x for x in dir(event) if not x.startswith('_')][:10]
                                                    })
                                            except Exception as e:
                                                logger.debug(f"  Error processing event: {e}")
                                                continue
                                        
                                        # Log summary
                                        if auto_event_count > 0:
                                            logger.info(f"  Automation events found: {auto_event_count}")
                                        else:
                                            logger.info(f"  No automation events found with current filters")
                                        
                                        # Log all event types found (for debugging)
                                        if event_types_found:
                                            logger.info(f"  Event types in arrangement.events: {len(event_types_found)} unique types")
                                            for etype, count in sorted(event_types_found.items(), key=lambda x: x[1], reverse=True)[:10]:
                                                logger.info(f"    {etype}: {count} events")
                                        
                                        # Log sample events
                                        if sample_events:
                                            logger.info(f"  Sample events (first 5):")
                                            for i, evt in enumerate(sample_events[:5], 1):
                                                logger.info(f"    Event {i}: {evt['type']}, ID: {evt['id']}, Attrs: {evt['attrs'][:5]}")
                                        
                                    except Exception as e:
                                        logger.info(f"  Error checking arrangement events: {e}")
                            except Exception as e:
                                logger.info(f"arrangement.events: Error accessing - {e}")
            except Exception as e:
                logger.info(f"Error checking arrangements for automation: {e}")
        
        # Method 3: Check channels for automation
        if hasattr(self.project, 'channels'):
            try:
                channels = self.project.channels
                if channels:
                    channels_list = list(channels) if hasattr(channels, '__iter__') else [channels]
                    auto_channel_count = 0
                    for channel in channels_list[:3]:  # Check first 3 channels
                        try:
                            # Check for automation-related attributes
                            for attr in ['automation', 'automation_clips', 'envelope', 'modulation', 'auto']:
                                if hasattr(channel, attr):
                                    auto_channel_count += 1
                                    logger.info(f"channel.{attr} found in channel: {getattr(channel, 'name', 'Unknown')}")
                                    break
                        except:
                            continue
                    if auto_channel_count == 0:
                        logger.info("No automation found in channels")
            except Exception as e:
                logger.info(f"Error checking channels for automation: {e}")
        
        # Method 4: Check plugins for parameter automation
        if hasattr(self.project, 'channels'):
            try:
                channels = self.project.channels
                if channels:
                    channels_list = list(channels) if hasattr(channels, '__iter__') else [channels]
                    for channel in channels_list[:2]:  # Check first 2 channels
                        try:
                            if hasattr(channel, 'plugin') and channel.plugin:
                                plugin = channel.plugin
                                if hasattr(plugin, 'parameters'):
                                    params = plugin.parameters
                                    if params:
                                        logger.info(f"Plugin parameters found in channel: {getattr(channel, 'name', 'Unknown')}")
                                        # Check if parameters have automation
                                        try:
                                            params_list = list(params) if hasattr(params, '__iter__') else [params]
                                            for param in params_list[:2]:  # Check first 2 params
                                                if hasattr(param, 'automation') or hasattr(param, 'envelope'):
                                                    logger.info(f"  Parameter automation found: {getattr(param, 'name', 'Unknown')}")
                                        except:
                                            pass
                        except:
                            continue
            except Exception as e:
                logger.info(f"Error checking plugins for automation: {e}")
        
        # Method 5: Check project.events for automation events
        if hasattr(self.project, 'events'):
            try:
                project_events = self.project.events
                logger.info(f"project.events: {type(project_events)}")
                if hasattr(project_events, '__iter__'):
                    try:
                        auto_event_count = 0
                        event_types_found = {}
                        
                        for event in project_events:
                            try:
                                event_type = str(type(event))
                                event_id = getattr(event, 'id', None)
                                
                                # Track event types
                                event_type_name = event_type.split("'")[1] if "'" in event_type else event_type
                                event_types_found[event_type_name] = event_types_found.get(event_type_name, 0) + 1
                                
                                # Broader automation detection
                                is_automation = (
                                    'Automation' in event_type or 
                                    'Auto' in event_type or 
                                    'Envelope' in event_type or
                                    'Modulation' in event_type or
                                    'Controller' in event_type or
                                    (event_id and ('Auto' in str(event_id) or 'Env' in str(event_id) or 'Mod' in str(event_id)))
                                )
                                
                                if is_automation:
                                    auto_event_count += 1
                                    if auto_event_count == 1:
                                        logger.info(f"  Found automation event in project.events: {event_type}")
                                        logger.info(f"    Event ID: {event_id}")
                            except:
                                continue
                        
                        if auto_event_count > 0:
                            logger.info(f"  Automation events in project.events: {auto_event_count}")
                        else:
                            logger.info(f"  No automation events found in project.events")
                            if event_types_found:
                                logger.info(f"  Event types in project.events: {len(event_types_found)} unique types")
                                for etype, count in sorted(event_types_found.items(), key=lambda x: x[1], reverse=True)[:5]:
                                    logger.info(f"    {etype}: {count} events")
                    except Exception as e:
                        logger.info(f"  Error checking project.events: {e}")
            except Exception as e:
                logger.info(f"project.events: Error accessing - {e}")
        
        logger.info("=== END AUTOMATION INSPECTION ===")
        logger.info("=== END INSPECTION ===")
    
    def _debug_project_structure(self):
        """Debug helper to inspect pyflp project structure (alias for _inspect_pyflp_structure)."""
        self._inspect_pyflp_structure()
    
    def parse(self) -> DAWMetadata:
        """Parse FL Studio project and extract all metadata."""
        try:
            version = self._extract_version()
            
            # Inspect project structure for debugging (always run to understand structure)
            self._inspect_pyflp_structure()
            
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
                daw_type=DAWType.FLSTUDIO,
                version=version,
                midi_data=midi_data,
                arrangement=arrangement,
                tempo_changes=tempo_changes,
                key_changes=key_changes,
                plugin_chains=plugin_chains,
                sample_sources=sample_sources,
                automation=automation
            )
            
            logger.info(f"Successfully parsed {self.file_path.name}: "
                       f"{len(midi_data)} tracks, {sum(len(t.notes) for t in midi_data)} notes, "
                       f"{len(arrangement.clips)} clips, {len(automation)} automation")
            return metadata
            
        except Exception as e:
            raise DAWParseError(
                f"Failed to parse FL Studio project: {e}",
                str(self.file_path)
            ) from e
    
    def _convert_note_name_to_midi(self, note_name) -> Optional[int]:
        """Convert note name like 'C5' to MIDI note number (0-127)."""
        if note_name is None:
            return None
        
        # If it's already an integer, return it
        if isinstance(note_name, int):
            if 0 <= note_name <= 127:
                return note_name
            return None
        
        # If it's not a string, try to convert
        if not isinstance(note_name, str):
            try:
                return int(note_name)
            except (ValueError, TypeError):
                return None
        
        # Note name format: "C5", "C#5", "Db5", etc.
        # C4 = 60 (middle C), C5 = 72, etc.
        
        note_map = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
            'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
        }
        
        # Parse note name
        note_name = note_name.strip()
        if not note_name:
            return None
        
        # Extract note and octave
        if len(note_name) >= 2 and note_name[1] in ['#', 'b']:
            note = note_name[:2]  # C#, Db, etc.
            octave_str = note_name[2:]
        else:
            note = note_name[0]  # C, D, E, etc.
            octave_str = note_name[1:]
        
        # Get base note value
        base_note = note_map.get(note)
        if base_note is None:
            return None
        
        # Get octave
        try:
            octave = int(octave_str)
        except (ValueError, TypeError):
            # Default to octave 4 if not specified
            octave = 4
        
        # Calculate MIDI note number
        # MIDI note = base_note + (octave + 1) * 12
        # C4 = 60, so: base_note (0) + (4 + 1) * 12 = 60
        midi_note = base_note + (octave + 1) * 12
        
        # Clamp to valid MIDI range (0-127)
        if midi_note < 0:
            midi_note = 0
        elif midi_note > 127:
            midi_note = 127
        
        return midi_note
    
    def _parse_midi_note(self, note_event, track_name: str, channel_num: int = 0) -> Optional[MIDINote]:
        """Helper to parse a single MIDI note event."""
        try:
            # Handle pyflp.pattern.Note objects specifically
            note_type_name = type(note_event).__name__
            is_pyflp_note = 'Note' in note_type_name or hasattr(note_event, 'key') and hasattr(note_event, 'position')
            
            if is_pyflp_note:
                # pyflp Note object structure
                # key is a string like "C5" - need to convert to MIDI note number
                key = getattr(note_event, 'key', None)
                if key is None:
                    return None
                
                # Convert note name to MIDI note number
                note_num = self._convert_note_name_to_midi(key)
                if note_num is None:
                    return None
                
                # Get velocity
                velocity = getattr(note_event, 'velocity', 100)
                
                # Get position (start time in ticks)
                position = getattr(note_event, 'position', 0)
                
                # Get length (duration in ticks)
                length = getattr(note_event, 'length', 0)
                
                # Convert ticks to beats (FL Studio uses PPQ - Pulses Per Quarter note)
                # Get PPQ from project (default 96 for FL Studio)
                ppq = getattr(self.project, 'ppq', 96) if hasattr(self, 'project') and self.project else 96
                
                start_time = float(position) / ppq  # Convert ticks to beats
                duration = float(length) / ppq if length > 0 else 0.25  # Default to quarter note if 0
                
                # Get channel
                channel = getattr(note_event, 'rack_channel', None)
                if channel is None:
                    channel = getattr(note_event, 'midi_channel', channel_num)
                if channel is None:
                    channel = channel_num
                
                return MIDINote(
                    note=note_num,
                    velocity=int(velocity),
                    start_time=start_time,
                    duration=duration,
                    channel=int(channel) if channel is not None else channel_num,
                    track_name=track_name
                )
            
            # Fallback: Try original method for other note formats
            # Try multiple attribute names for note number
            note_num = None
            for attr in ['key', 'note', 'pitch', 'midi_note', 'note_number']:
                if hasattr(note_event, attr):
                    val = getattr(note_event, attr)
                    if val is not None:
                        # Try converting note name string to MIDI number
                        note_num = self._convert_note_name_to_midi(val)
                        if note_num is not None:
                            break
                        # Try as integer
                        try:
                            note_num = int(val)
                            if 0 <= note_num <= 127:
                                break
                        except (ValueError, TypeError):
                            continue
            
            if note_num is None:
                return None
            
            # Get velocity
            velocity = 100
            for attr in ['velocity', 'vel', 'v']:
                if hasattr(note_event, attr):
                    val = getattr(note_event, attr)
                    if val is not None:
                        try:
                            velocity = int(val)
                            break
                        except (ValueError, TypeError):
                            continue
            
            # Get start time
            start_time = 0.0
            for attr in ['start', 'time', 'position', 't', 'pos']:
                if hasattr(note_event, attr):
                    val = getattr(note_event, attr)
                    if val is not None:
                        try:
                            start_time = float(val)
                            break
                        except (ValueError, TypeError):
                            continue
            
            # Get duration
            duration = 1.0
            if hasattr(note_event, 'end') and hasattr(note_event, 'start'):
                try:
                    end_val = float(getattr(note_event, 'end', 0))
                    start_val = float(getattr(note_event, 'start', 0))
                    duration = end_val - start_val
                    if duration <= 0:
                        duration = 1.0
                except (ValueError, TypeError):
                    pass
            
            if duration == 1.0:  # If end-start didn't work, try other attributes
                for attr in ['duration', 'length', 'dur', 'len']:
                    if hasattr(note_event, attr):
                        val = getattr(note_event, attr)
                        if val is not None:
                            try:
                                duration = float(val)
                                if duration > 0:
                                    break
                            except (ValueError, TypeError):
                                continue
            
            # Get channel
            if hasattr(note_event, 'channel'):
                try:
                    channel_num = int(note_event.channel)
                except (ValueError, TypeError):
                    pass
            
            return MIDINote(
                note=note_num,
                velocity=velocity,
                start_time=start_time,
                duration=duration,
                channel=channel_num,
                track_name=track_name
            )
        except Exception as e:
            logger.debug(f"Failed to parse MIDI note: {e}")
            return None
    
    def _extract_midi_data(self) -> List[MIDITrack]:
        """Extract MIDI data from patterns."""
        tracks = []
        
        if not self.project:
            return tracks
        
        try:
            track_map = {}
            track_index = 0
            
            # Get patterns from project - pyflp structure: project.patterns
            patterns = None
            if hasattr(self.project, 'patterns'):
                patterns = self.project.patterns
            elif hasattr(self.project, 'pattern'):
                patterns = [self.project.pattern] if self.project.pattern else []
            
            if patterns:
                # Convert to list to avoid iteration issues
                patterns_list = list(patterns)
                
                for pattern_idx, pattern in enumerate(patterns_list):
                    try:
                        # Get pattern name
                        pattern_name = getattr(pattern, 'name', f'Pattern {pattern_idx + 1}')
                        if not pattern_name:
                            pattern_name = f'Pattern {pattern_idx + 1}'
                        
                        notes = []
                        
                        # Method 1: pattern.notes is a GENERATOR (most common in pyflp)
                        if hasattr(pattern, 'notes'):
                            try:
                                pattern_notes = pattern.notes
                                
                                # It's a generator - iterate it directly
                                if hasattr(pattern_notes, '__iter__') and not isinstance(pattern_notes, (str, dict)):
                                    try:
                                        # Convert generator to list and iterate
                                        notes_list = list(pattern_notes)
                                        for note_event in notes_list:
                                            note = self._parse_midi_note(note_event, pattern_name)
                                            if note:
                                                notes.append(note)
                                    except Exception as e:
                                        logger.debug(f"Error iterating pattern.notes generator: {e}")
                                
                                # Fallback: Check if it's a dict (some versions might use dict)
                                elif isinstance(pattern_notes, dict) or (hasattr(pattern_notes, 'keys') and hasattr(pattern_notes, '__getitem__')):
                                    # Iterate through channels
                                    try:
                                        if hasattr(pattern_notes, 'keys'):
                                            channel_keys = list(pattern_notes.keys())
                                        else:
                                            channel_keys = list(pattern_notes.keys())
                                        
                                        for channel_idx in channel_keys:
                                            try:
                                                channel_notes = pattern_notes[channel_idx]
                                                if channel_notes is not None:
                                                    # Convert to list if needed
                                                    if hasattr(channel_notes, '__iter__') and not isinstance(channel_notes, str):
                                                        try:
                                                            notes_list = list(channel_notes)
                                                            for note_event in notes_list:
                                                                note = self._parse_midi_note(note_event, pattern_name, int(channel_idx))
                                                                if note:
                                                                    notes.append(note)
                                                        except Exception as e:
                                                            logger.debug(f"Error processing channel {channel_idx} notes: {e}")
                                            except Exception as e:
                                                logger.debug(f"Error accessing channel {channel_idx}: {e}")
                                    except Exception as e:
                                        logger.debug(f"Error iterating pattern.notes dict: {e}")
                            except Exception as e:
                                logger.debug(f"Error accessing pattern.notes: {e}")
                        
                        # Method 2: Check project-level channels (notes might be stored there)
                        if not notes and hasattr(self.project, 'channels'):
                            try:
                                project_channels = self.project.channels
                                if project_channels:
                                    channels_list = list(project_channels)
                                    for channel in channels_list:
                                        channel_idx = getattr(channel, 'index', None)
                                        # Check if channel has notes for this pattern
                                        if hasattr(channel, 'notes'):
                                            channel_notes = channel.notes
                                            # Might be pattern-specific or a dict
                                            if isinstance(channel_notes, dict) or (hasattr(channel_notes, 'keys') and hasattr(channel_notes, '__getitem__')):
                                                # Check if this pattern's notes are in the dict
                                                if hasattr(channel_notes, 'keys'):
                                                    pattern_keys = list(channel_notes.keys())
                                                else:
                                                    pattern_keys = list(channel_notes.keys())
                                                # Try pattern index or pattern name
                                                if pattern_idx in pattern_keys:
                                                    notes_data = channel_notes[pattern_idx]
                                                    if notes_data and hasattr(notes_data, '__iter__'):
                                                        try:
                                                            notes_list = list(notes_data)
                                                            for note_event in notes_list:
                                                                note = self._parse_midi_note(note_event, pattern_name, channel_idx or 0)
                                                                if note:
                                                                    notes.append(note)
                                                        except Exception:
                                                            pass
                                            elif hasattr(channel_notes, '__iter__') and not isinstance(channel_notes, str):
                                                try:
                                                    notes_list = list(channel_notes)
                                                    for note_event in notes_list:
                                                        note = self._parse_midi_note(note_event, pattern_name, channel_idx or 0)
                                                        if note:
                                                            notes.append(note)
                                                except Exception:
                                                    pass
                            except Exception as e:
                                logger.debug(f"Error checking project channels: {e}")
                        
                        # Method 3: Try pattern.events (but filter for note events)
                        if not notes and hasattr(pattern, 'events'):
                            try:
                                events = pattern.events
                                if events:
                                    events_list = list(events)
                                    for event in events_list:
                                        # Check if it's a note event
                                        event_type = type(event).__name__
                                        if 'note' in event_type.lower() or 'Note' in event_type:
                                            note = self._parse_midi_note(event, pattern_name)
                                            if note:
                                                notes.append(note)
                            except Exception as e:
                                logger.debug(f"Error checking pattern.events: {e}")
                        
                        # Create track if it has notes or is a new pattern
                        if notes or pattern_name not in track_map:
                            track = MIDITrack(
                                track_name=str(pattern_name),
                                track_index=track_index,
                                notes=notes
                            )
                            tracks.append(track)
                            track_map[pattern_name] = track_index
                            track_index += 1
                            
                    except Exception as e:
                        logger.debug(f"Error processing pattern {pattern_idx}: {e}")
                        continue
            
            logger.info(f"Extracted {len(tracks)} MIDI tracks with {sum(len(t.notes) for t in tracks)} notes")
            
        except Exception as e:
            logger.warning(f"Error extracting MIDI data: {e}")
        
        return tracks
    
    def _parse_clip(self, clip_item, track_name: str) -> Optional[ClipData]:
        """Helper to parse a single clip."""
        try:
            clip_name = getattr(clip_item, 'name', 'Unnamed Clip')
            if not clip_name:
                clip_name = 'Unnamed Clip'
            
            # Get start time
            start_time = 0.0
            for attr in ['start', 'position', 'time', 'pos', 't']:
                if hasattr(clip_item, attr):
                    val = getattr(clip_item, attr)
                    if val is not None:
                        try:
                            start_time = float(val)
                            break
                        except (ValueError, TypeError):
                            continue
            
            # Get duration
            duration = 0.0
            if hasattr(clip_item, 'end') and hasattr(clip_item, 'start'):
                try:
                    end_val = float(getattr(clip_item, 'end', 0))
                    start_val = float(getattr(clip_item, 'start', 0))
                    duration = end_val - start_val
                except (ValueError, TypeError):
                    pass
            
            if duration == 0.0:
                for attr in ['length', 'duration', 'dur', 'len']:
                    if hasattr(clip_item, attr):
                        val = getattr(clip_item, attr)
                        if val is not None:
                            try:
                                duration = float(val)
                                if duration > 0:
                                    break
                            except (ValueError, TypeError):
                                continue
            
            # Determine clip type
            clip_type = 'midi'  # Default
            if hasattr(clip_item, 'type'):
                clip_type = str(clip_item.type).lower()
            elif hasattr(clip_item, 'clip_type'):
                clip_type = str(clip_item.clip_type).lower()
            elif hasattr(clip_item, 'pattern'):
                clip_type = 'midi'
            elif hasattr(clip_item, 'audio') or hasattr(clip_item, 'sample'):
                clip_type = 'audio'
            
            return ClipData(
                clip_name=str(clip_name),
                start_time=start_time,
                end_time=start_time + duration,
                track_name=str(track_name),
                clip_type=clip_type
            )
        except Exception as e:
            logger.debug(f"Failed to parse clip: {e}")
            return None
    
    def _parse_playlist_event(self, event, track_name: str = 'Unknown Track') -> Optional[ClipData]:
        """Parse a PlaylistEvent object into a ClipData."""
        try:
            # PlaylistEvent objects represent clips in the playlist
            # They contain pattern references, timing, and track info
            
            # Get pattern reference - try multiple attribute names
            pattern_id = None
            pattern_name = None
            pattern_obj = None
            
            # Try to get pattern object directly first
            for attr in ['pattern', 'pattern_obj', 'pattern_ref', 'pat', 'p']:
                if hasattr(event, attr):
                    try:
                        val = getattr(event, attr)
                        if val is not None:
                            # Check if it's a pattern object (has name attribute)
                            if hasattr(val, 'name'):
                                pattern_obj = val
                                pattern_name = getattr(val, 'name', None)
                                if pattern_name:
                                    break
                            # Otherwise treat as pattern_id
                            elif isinstance(val, int):
                                pattern_id = val
                    except:
                        continue
            
            # If we don't have pattern_obj, try to get pattern_id
            if pattern_obj is None:
                for attr in ['pattern_id', 'pattern_index', 'pat_id', 'pat_index', 'id', 'index']:
                    if hasattr(event, attr):
                        try:
                            val = getattr(event, attr)
                            if val is not None and isinstance(val, int):
                                pattern_id = val
                                break
                        except:
                            continue
            
            # Try to get pattern name from project.patterns using pattern_id
            if pattern_name is None and pattern_id is not None and hasattr(self, 'project') and self.project:
                if hasattr(self.project, 'patterns'):
                    try:
                        patterns_list = list(self.project.patterns)
                        # Handle both 0-based and 1-based pattern IDs
                        # If pattern_id is large (like 234), it might be 1-based or an absolute index
                        if isinstance(pattern_id, int):
                            # Try direct index first
                            if 0 <= pattern_id < len(patterns_list):
                                pattern_obj = patterns_list[pattern_id]
                                pattern_name = getattr(pattern_obj, 'name', None)
                                if not pattern_name:
                                    # Try alternative name attributes
                                    for name_attr in ['name', 'title', 'label', 'display_name']:
                                        if hasattr(pattern_obj, name_attr):
                                            pattern_name = getattr(pattern_obj, name_attr)
                                            if pattern_name:
                                                break
                            # If pattern_id is larger than list length, it might be 1-based
                            elif pattern_id > 0:
                                # Try pattern_id - 1 (convert from 1-based to 0-based)
                                adjusted_id = pattern_id - 1
                                if 0 <= adjusted_id < len(patterns_list):
                                    pattern_obj = patterns_list[adjusted_id]
                                    pattern_name = getattr(pattern_obj, 'name', None)
                                    if not pattern_name:
                                        for name_attr in ['name', 'title', 'label', 'display_name']:
                                            if hasattr(pattern_obj, name_attr):
                                                pattern_name = getattr(pattern_obj, name_attr)
                                                if pattern_name:
                                                    break
                    except Exception as e:
                        logger.debug(f"Error looking up pattern {pattern_id}: {e}")
            
            # Fallback pattern name
            if pattern_name is None:
                if pattern_id is not None:
                    # If pattern_id is out of bounds, it might be an IID or absolute index
                    # Try to find pattern by IID if available
                    if hasattr(self, 'project') and self.project and hasattr(self.project, 'patterns'):
                        try:
                            patterns_list = list(self.project.patterns)
                            # Try to find pattern by IID
                            for idx, pattern in enumerate(patterns_list):
                                if hasattr(pattern, 'iid'):
                                    pattern_iid = getattr(pattern, 'iid', None)
                                    if pattern_iid == pattern_id:
                                        pattern_name = getattr(pattern, 'name', f'Pattern {idx + 1}')
                                        if not pattern_name:
                                            pattern_name = f'Pattern {idx + 1}'
                                        logger.debug(f"Found pattern by IID {pattern_id}: {pattern_name}")
                                        break
                        except Exception as e:
                            logger.debug(f"Error looking up pattern by IID: {e}")
                    
                    # If still not found, use pattern_id directly (might be a pattern number, not index)
                    # Note: FL Studio might use pattern numbers that don't correspond to indices
                    if pattern_name is None:
                        pattern_name = f'Pattern {pattern_id}'
                        logger.debug(f"Using pattern_id directly as pattern name: {pattern_name}")
                else:
                    # Try to get any identifier from the event
                    for attr in ['id', 'index', 'name', 'label', 'iid']:
                        if hasattr(event, attr):
                            try:
                                val = getattr(event, attr)
                                if val is not None:
                                    # If it's an IID, try to find pattern by IID
                                    if attr == 'iid' and hasattr(self, 'project') and self.project and hasattr(self.project, 'patterns'):
                                        try:
                                            patterns_list = list(self.project.patterns)
                                            for idx, pattern in enumerate(patterns_list):
                                                if hasattr(pattern, 'iid') and getattr(pattern, 'iid', None) == val:
                                                    pattern_name = getattr(pattern, 'name', f'Pattern {idx + 1}')
                                                    if not pattern_name:
                                                        pattern_name = f'Pattern {idx + 1}'
                                                    break
                                        except:
                                            pass
                                    
                                    if pattern_name is None:
                                        pattern_name = f'Pattern {val}'
                                    break
                            except:
                                continue
                    if pattern_name is None:
                        # Last resort: inspect all attributes of the event
                        try:
                            event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
                            logger.debug(f"PlaylistEvent attributes: {event_attrs[:20]}")  # Log first 20
                            # Try common pyflp pattern-related attributes
                            for attr in event_attrs:
                                if 'pattern' in attr.lower() or 'pat' in attr.lower():
                                    try:
                                        val = getattr(event, attr)
                                        if val is not None:
                                            if isinstance(val, int):
                                                # Try IID lookup first
                                                if hasattr(self, 'project') and self.project and hasattr(self.project, 'patterns'):
                                                    try:
                                                        patterns_list = list(self.project.patterns)
                                                        for idx, pattern in enumerate(patterns_list):
                                                            if hasattr(pattern, 'iid') and getattr(pattern, 'iid', None) == val:
                                                                pattern_name = getattr(pattern, 'name', f'Pattern {idx + 1}')
                                                                if not pattern_name:
                                                                    pattern_name = f'Pattern {idx + 1}'
                                                                break
                                                    except:
                                                        pass
                                                
                                                if pattern_name is None:
                                                    pattern_id = val
                                                    pattern_name = f'Pattern {val}'
                                                break
                                            elif isinstance(val, str):
                                                pattern_name = val
                                                break
                                    except:
                                        continue
                        except:
                            pass
                        if pattern_name is None:
                            pattern_name = 'Unknown Pattern'
            
            # Get start time (in ticks or beats)
            start_time = 0.0
            for attr in ['start', 'position', 'time', 'pos', 't', 'start_time']:
                if hasattr(event, attr):
                    try:
                        val = getattr(event, attr)
                        if val is not None:
                            # Convert ticks to beats if needed
                            ppq = getattr(self.project, 'ppq', 96) if hasattr(self, 'project') and self.project else 96
                            if isinstance(val, (int, float)) and val > 1000:  # Likely ticks
                                start_time = float(val) / ppq
                            else:
                                start_time = float(val)
                            break
                    except:
                        continue
            
            # Get duration/length
            duration = 0.0
            # Try end - start
            if hasattr(event, 'end') and hasattr(event, 'start'):
                try:
                    end_val = getattr(event, 'end', 0)
                    start_val = getattr(event, 'start', 0)
                    ppq = getattr(self.project, 'ppq', 96) if hasattr(self, 'project') and self.project else 96
                    if isinstance(end_val, (int, float)) and isinstance(start_val, (int, float)):
                        if end_val > 1000 or start_val > 1000:  # Likely ticks
                            duration = (float(end_val) - float(start_val)) / ppq
                        else:
                            duration = float(end_val) - float(start_val)
                except:
                    pass
            
            # If duration is still 0, try length/duration attributes
            if duration == 0.0:
                for attr in ['length', 'duration', 'dur', 'len', 'clip_length']:
                    if hasattr(event, attr):
                        try:
                            val = getattr(event, attr)
                            if val is not None:
                                ppq = getattr(self.project, 'ppq', 96) if hasattr(self, 'project') and self.project else 96
                                if isinstance(val, (int, float)) and val > 1000:  # Likely ticks
                                    duration = float(val) / ppq
                                else:
                                    duration = float(val)
                                if duration > 0:
                                    break
                        except:
                            continue
            
            # Default duration if still 0
            if duration == 0.0:
                duration = 4.0  # Default to 4 beats
            
            # Get track name from event if available - try multiple approaches
            event_track_name = track_name
            
            # First, try to get track object directly
            track_obj = None
            for attr in ['track', 'track_obj', 'track_ref', 'channel', 'channel_obj']:
                if hasattr(event, attr):
                    try:
                        val = getattr(event, attr)
                        if val is not None:
                            # Check if it's a track/channel object (has name attribute)
                            if hasattr(val, 'name'):
                                track_obj = val
                                track_name_from_obj = getattr(val, 'name', None)
                                if track_name_from_obj:
                                    event_track_name = str(track_name_from_obj)
                                    break
                            # Otherwise treat as track name/id
                            elif isinstance(val, (str, int)):
                                event_track_name = str(val)
                                break
                    except:
                        continue
            
            # If we don't have track_obj, try track name/id attributes
            if track_obj is None:
                for attr in ['track_name', 'track_id', 'channel_name', 'channel_id', 'name', 'label', 'title']:
                    if hasattr(event, attr):
                        try:
                            val = getattr(event, attr)
                            if val is not None:
                                event_track_name = str(val)
                                # If it's a numeric ID, try to look up the track name
                                if isinstance(val, int) and hasattr(self, 'project') and self.project:
                                    # Try to get track name from arrangement or project
                                    if hasattr(self.project, 'arrangements'):
                                        try:
                                            arrangements = list(self.project.arrangements)
                                            for arr in arrangements:
                                                if hasattr(arr, 'tracks'):
                                                    tracks_list = list(arr.tracks) if hasattr(arr.tracks, '__iter__') else [arr.tracks]
                                                    if 0 <= val < len(tracks_list):
                                                        track = tracks_list[val]
                                                        if hasattr(track, 'name'):
                                                            event_track_name = str(getattr(track, 'name', f'Track {val + 1}'))
                                                            break
                                        except:
                                            pass
                                break
                        except:
                            continue
            
            # Final fallback - use provided track_name if event_track_name is still default
            if event_track_name == 'Unknown Track' and track_name != 'Unknown Track':
                event_track_name = track_name
            
            # Last resort: inspect all attributes of the event for track info
            if event_track_name == 'Unknown Track':
                try:
                    event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
                    # Try common pyflp track/channel-related attributes
                    for attr in event_attrs:
                        if any(keyword in attr.lower() for keyword in ['track', 'channel', 'lane', 'row']):
                            try:
                                val = getattr(event, attr)
                                if val is not None:
                                    if isinstance(val, (str, int)):
                                        event_track_name = str(val)
                                        break
                                    elif hasattr(val, 'name'):
                                        event_track_name = str(getattr(val, 'name', str(val)))
                                        break
                            except:
                                continue
                except:
                    pass
            
            # Determine clip type
            clip_type = 'midi'  # Default for pattern-based clips
            if hasattr(event, 'type') or hasattr(event, 'clip_type'):
                try:
                    clip_type_val = getattr(event, 'type', None) or getattr(event, 'clip_type', None)
                    if clip_type_val:
                        clip_type = str(clip_type_val).lower()
                except:
                    pass
            
            return ClipData(
                clip_name=str(pattern_name),
                start_time=start_time,
                end_time=start_time + duration,
                track_name=str(event_track_name),
                clip_type=clip_type
            )
        except Exception as e:
            logger.debug(f"Failed to parse PlaylistEvent: {e}")
            return None
    
    def _extract_arrangement(self) -> ArrangementData:
        """Extract arrangement from Arrangements (playlist parsing may fail)."""
        clips = []
        tracks = []
        
        if not self.project:
            return ArrangementData(clips=clips, total_length=0.0, tracks=tracks)
        
        try:
            # Method 1: Use arrangements (pyflp structure - more reliable than playlist)
            if hasattr(self.project, 'arrangements'):
                try:
                    arrangements = self.project.arrangements
                    if arrangements:
                        # Convert to list if it's a generator
                        if hasattr(arrangements, '__iter__') and not isinstance(arrangements, (str, dict)):
                            arrangements_list = list(arrangements)
                        else:
                            arrangements_list = [arrangements] if arrangements else []
                        
                        for arrangement in arrangements_list:
                            arrangement_name = getattr(arrangement, 'name', 'Main Arrangement')
                            
                            # First, try to build a track index from arrangement.tracks
                            track_index_map = {}  # Maps track index/ID to track name
                            track_list = []
                            try:
                                if hasattr(arrangement, 'tracks'):
                                    tracks_data = arrangement.tracks
                                    if tracks_data:
                                        if hasattr(tracks_data, '__iter__') and not isinstance(tracks_data, (str, dict)):
                                            try:
                                                tracks_iter = iter(tracks_data)
                                                for track_idx, track_item in enumerate(tracks_iter):
                                                    try:
                                                        # Check if it's a Track object or PlaylistEvent
                                                        if hasattr(track_item, 'name'):
                                                            track_name = getattr(track_item, 'name', f'Track {track_idx + 1}')
                                                            if not track_name:
                                                                track_name = f'Track {track_idx + 1}'
                                                            track_index_map[track_idx] = track_name
                                                            track_list.append(track_name)
                                                            if track_name not in tracks:
                                                                tracks.append(track_name)
                                                        else:
                                                            # Might be a PlaylistEvent - try to get track info
                                                            track_name = f'Track {track_idx + 1}'
                                                            for attr in ['track', 'track_name', 'track_id', 'lane', 'row']:
                                                                if hasattr(track_item, attr):
                                                                    try:
                                                                        val = getattr(track_item, attr)
                                                                        if val is not None:
                                                                            if isinstance(val, int):
                                                                                track_name = f'Track {val + 1}'
                                                                            else:
                                                                                track_name = str(val)
                                                                            break
                                                                    except:
                                                                        continue
                                                            track_index_map[track_idx] = track_name
                                                            track_list.append(track_name)
                                                            if track_name not in tracks:
                                                                tracks.append(track_name)
                                                    except Exception as e:
                                                        logger.debug(f"Error processing track {track_idx}: {e}")
                                                        continue
                                            except Exception as e:
                                                error_msg = str(e)
                                                if "'data'" not in error_msg:
                                                    logger.debug(f"Error iterating arrangement.tracks: {e}")
                            except Exception as e:
                                logger.debug(f"Error accessing arrangement.tracks for track index: {e}")
                            
                            # Method 1: Try arrangement.events first (may be more accessible)
                            if hasattr(arrangement, 'events') and not clips:
                                try:
                                    arr_events = arrangement.events
                                    if arr_events:
                                        logger.debug("Trying to extract clips from arrangement.events")
                                        # Try to iterate events
                                        if hasattr(arr_events, '__iter__') and not isinstance(arr_events, (str, dict)):
                                            try:
                                                event_index = 0
                                                for event in arr_events:
                                                    try:
                                                        event_type = str(type(event))
                                                        
                                                        # Check if it's a TrackEvent (contains track data and playlist events)
                                                        if 'TrackEvent' in event_type:
                                                            # TrackEvent objects contain track information and playlist events in .data
                                                            track_name = 'Unknown Track'
                                                            
                                                            # Try to get track name from TrackEvent
                                                            # TrackEvent might have track index in its ID or attributes
                                                            event_id = getattr(event, 'id', None)
                                                            if event_id:
                                                                event_id_str = str(event_id)
                                                                logger.debug(f"TrackEvent ID: {event_id_str}")
                                                            
                                                            # Inspect TrackEvent attributes to find track info
                                                            try:
                                                                track_event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
                                                                logger.debug(f"TrackEvent attributes: {track_event_attrs[:15]}")
                                                                # Try common track-related attributes
                                                                for attr in track_event_attrs:
                                                                    if any(keyword in attr.lower() for keyword in ['track', 'channel', 'lane', 'row', 'index']):
                                                                        try:
                                                                            val = getattr(event, attr)
                                                                            if val is not None:
                                                                                if isinstance(val, str) and val:
                                                                                    track_name = str(val)
                                                                                    break
                                                                                elif isinstance(val, int):
                                                                                    # Use track index map if available
                                                                                    if val in track_index_map:
                                                                                        track_name = track_index_map[val]
                                                                                    else:
                                                                                        track_name = f'Track {val + 1}'
                                                                                    break
                                                                        except:
                                                                            continue
                                                            except:
                                                                pass
                                                            
                                                            # Try standard attributes
                                                            if track_name == 'Unknown Track':
                                                                for attr in ['track', 'track_name', 'track_id', 'name', 'channel', 'channel_name', 'index']:
                                                                    if hasattr(event, attr):
                                                                        try:
                                                                            val = getattr(event, attr)
                                                                            if val is not None:
                                                                                if isinstance(val, str) and val:
                                                                                    track_name = str(val)
                                                                                    break
                                                                                elif isinstance(val, int):
                                                                                    if val in track_index_map:
                                                                                        track_name = track_index_map[val]
                                                                                    else:
                                                                                        track_name = f'Track {val + 1}'
                                                                                    break
                                                                        except:
                                                                            continue
                                                            
                                                            # If still unknown, use event index as track index
                                                            # Note: event_index starts at 0, so first track is "Track 1"
                                                            if track_name == 'Unknown Track':
                                                                # Try track_index_map first
                                                                if event_index in track_index_map:
                                                                    track_name = track_index_map[event_index]
                                                                # Then try track_list
                                                                elif event_index < len(track_list):
                                                                    track_name = track_list[event_index]
                                                                # Final fallback: use event_index + 1 (0 -> Track 1, 1 -> Track 2, etc.)
                                                                else:
                                                                    track_name = f'Track {event_index + 1}'
                                                                logger.debug(f"TrackEvent at index {event_index} assigned track name: {track_name}")
                                                            
                                                            if track_name not in tracks:
                                                                tracks.append(track_name)
                                                            
                                                            # Access .data attribute to get playlist events
                                                            if hasattr(event, 'data'):
                                                                try:
                                                                    track_data = event.data
                                                                    if track_data:
                                                                        # track_data might be a list or iterable of playlist events
                                                                        if hasattr(track_data, '__iter__') and not isinstance(track_data, (str, dict)):
                                                                            playlist_event_list = list(track_data) if hasattr(track_data, '__iter__') else [track_data]
                                                                            logger.debug(f"TrackEvent.data contains {len(playlist_event_list)} playlist events")
                                                                            for playlist_event in playlist_event_list:
                                                                                try:
                                                                                    # Log playlist event type and attributes for debugging
                                                                                    playlist_event_type = str(type(playlist_event))
                                                                                    logger.debug(f"PlaylistEvent type: {playlist_event_type}")
                                                                                    playlist_attrs = [a for a in dir(playlist_event) if not a.startswith('_')]
                                                                                    logger.debug(f"PlaylistEvent attributes: {playlist_attrs[:15]}")
                                                                                    
                                                                                    # Log pattern-related attributes
                                                                                    for attr in playlist_attrs:
                                                                                        if 'pattern' in attr.lower() or 'pat' in attr.lower() or attr in ['id', 'iid', 'index']:
                                                                                            try:
                                                                                                val = getattr(playlist_event, attr, None)
                                                                                                logger.debug(f"  PlaylistEvent.{attr}: {val} (type: {type(val)})")
                                                                                            except:
                                                                                                pass
                                                                                    
                                                                                    clip = self._parse_playlist_event(playlist_event, track_name)
                                                                                    if clip:
                                                                                        clips.append(clip)
                                                                                except Exception as e:
                                                                                    logger.debug(f"Error parsing playlist event from TrackEvent.data: {e}")
                                                                                    continue
                                                                        else:
                                                                            # Single playlist event
                                                                            clip = self._parse_playlist_event(track_data, track_name)
                                                                            if clip:
                                                                                clips.append(clip)
                                                                except Exception as e:
                                                                    logger.debug(f"Error accessing TrackEvent.data: {e}")
                                                            
                                                            event_index += 1
                                                        
                                                        # Check if it's a direct PlaylistEvent
                                                        elif 'PlaylistEvent' in event_type:
                                                            # Direct PlaylistEvent - process as before
                                                            track_name = 'Unknown Track'
                                                            
                                                            # Try to get track index/lane/row from event
                                                            track_idx = None
                                                            for attr in ['track', 'track_id', 'lane', 'row', 'track_index', 'lane_index']:
                                                                if hasattr(event, attr):
                                                                    try:
                                                                        val = getattr(event, attr)
                                                                        if val is not None and isinstance(val, int):
                                                                            track_idx = val
                                                                            if track_idx in track_index_map:
                                                                                track_name = track_index_map[track_idx]
                                                                            else:
                                                                                track_name = f'Track {track_idx + 1}'
                                                                            break
                                                                    except:
                                                                        continue
                                                            
                                                            if track_name == 'Unknown Track':
                                                                for attr in ['track_name', 'channel_name', 'name']:
                                                                    if hasattr(event, attr):
                                                                        try:
                                                                            val = getattr(event, attr)
                                                                            if val is not None:
                                                                                track_name = str(val)
                                                                                break
                                                                        except:
                                                                            continue
                                                            
                                                            if track_name == 'Unknown Track' and track_list:
                                                                if event_index < len(track_list):
                                                                    track_name = track_list[event_index]
                                                            
                                                            if track_name not in tracks:
                                                                tracks.append(track_name)
                                                            
                                                            clip = self._parse_playlist_event(event, track_name)
                                                            if clip:
                                                                clips.append(clip)
                                                            event_index += 1
                                                    except Exception as e:
                                                        logger.debug(f"Error processing arrangement event: {e}")
                                                        event_index += 1
                                                        continue
                                            except Exception as e:
                                                logger.debug(f"Error iterating arrangement.events: {e}")
                                except Exception as e:
                                    logger.debug(f"Error accessing arrangement.events: {e}")
                            
                            # Method 2: Try arrangement.tracks (may fail due to pyflp limitation)
                            if not clips and hasattr(arrangement, 'tracks'):
                                tracks_data = arrangement.tracks
                                if tracks_data:
                                    # Try to iterate, but expect it might fail
                                    try:
                                        if hasattr(tracks_data, '__iter__') and not isinstance(tracks_data, (str, dict)):
                                            tracks_iter = iter(tracks_data)
                                            first_item = None
                                            is_playlist_event = False
                                            
                                            try:
                                                first_item = next(tracks_iter)
                                                # Check if it's a PlaylistEvent
                                                is_playlist_event = ('PlaylistEvent' in str(type(first_item)) or 
                                                                   'Event' in str(type(first_item)) or
                                                                   not hasattr(first_item, 'clips'))
                                                
                                                if is_playlist_event:
                                                    # Items are PlaylistEvent objects - parse them directly as clips
                                                    logger.debug(f"Arrangement tracks are PlaylistEvent objects, parsing as clips")
                                                    # Process first item
                                                    try:
                                                        track_name = f'Track 1'
                                                        for attr in ['track', 'track_name', 'track_id', 'channel', 'channel_name']:
                                                            if hasattr(first_item, attr):
                                                                try:
                                                                    val = getattr(first_item, attr)
                                                                    if val is not None:
                                                                        track_name = str(val)
                                                                        break
                                                                except:
                                                                    continue
                                                        
                                                        if track_name not in tracks:
                                                            tracks.append(track_name)
                                                        
                                                        clip = self._parse_playlist_event(first_item, track_name)
                                                        if clip:
                                                            clips.append(clip)
                                                    except Exception as e:
                                                        logger.debug(f"Error processing first PlaylistEvent: {e}")
                                                    
                                                    # Process remaining items
                                                    for event_idx, event in enumerate(tracks_iter, start=2):
                                                        try:
                                                            track_name = f'Track {event_idx}'
                                                            for attr in ['track', 'track_name', 'track_id', 'channel', 'channel_name']:
                                                                if hasattr(event, attr):
                                                                    try:
                                                                        val = getattr(event, attr)
                                                                        if val is not None:
                                                                            track_name = str(val)
                                                                            break
                                                                    except:
                                                                        continue
                                                            
                                                            if track_name not in tracks:
                                                                tracks.append(track_name)
                                                            
                                                            clip = self._parse_playlist_event(event, track_name)
                                                            if clip:
                                                                clips.append(clip)
                                                        except Exception as e:
                                                            logger.debug(f"Error processing PlaylistEvent {event_idx}: {e}")
                                                            continue
                                                else:
                                                    # Items are Track objects - extract clips from tracks
                                                    # Process first track
                                                    try:
                                                        track_name = getattr(first_item, 'name', 'Track 1')
                                                        if not track_name:
                                                            track_name = 'Track 1'
                                                        
                                                        if track_name not in tracks:
                                                            tracks.append(track_name)
                                                        
                                                        # Get clips from track
                                                        track_clips = None
                                                        for attr in ['clips', 'items', 'clip_items', 'events']:
                                                            if hasattr(first_item, attr):
                                                                try:
                                                                    track_clips = getattr(first_item, attr)
                                                                    if track_clips:
                                                                        break
                                                                except Exception:
                                                                    continue
                                                        
                                                        if not track_clips and hasattr(first_item, 'clip'):
                                                            track_clips = [first_item.clip] if first_item.clip else []
                                                        
                                                        if track_clips:
                                                            # Iterate clips directly if generator
                                                            if hasattr(track_clips, '__iter__') and not isinstance(track_clips, (str, dict)):
                                                                for clip_item in track_clips:
                                                                    if 'PlaylistEvent' in str(type(clip_item)) or 'Event' in str(type(clip_item)):
                                                                        clip = self._parse_playlist_event(clip_item, track_name)
                                                                    else:
                                                                        clip = self._parse_clip(clip_item, track_name)
                                                                    if clip:
                                                                        clips.append(clip)
                                                            else:
                                                                clips_list = [track_clips] if track_clips else []
                                                                for clip_item in clips_list:
                                                                    if 'PlaylistEvent' in str(type(clip_item)) or 'Event' in str(type(clip_item)):
                                                                        clip = self._parse_playlist_event(clip_item, track_name)
                                                                    else:
                                                                        clip = self._parse_clip(clip_item, track_name)
                                                                    if clip:
                                                                        clips.append(clip)
                                                    except Exception as e:
                                                        logger.debug(f"Error processing first arrangement track: {e}")
                                                    
                                                    # Process remaining tracks
                                                    for track_idx, track in enumerate(tracks_iter, start=2):
                                                        try:
                                                            track_name = getattr(track, 'name', f'Track {track_idx}')
                                                            if not track_name:
                                                                track_name = f'Track {track_idx}'
                                                            
                                                            if track_name not in tracks:
                                                                tracks.append(track_name)
                                                            
                                                            # Get clips from track
                                                            track_clips = None
                                                            for attr in ['clips', 'items', 'clip_items', 'events']:
                                                                if hasattr(track, attr):
                                                                    try:
                                                                        track_clips = getattr(track, attr)
                                                                        if track_clips:
                                                                            break
                                                                    except Exception:
                                                                        continue
                                                            
                                                            if not track_clips and hasattr(track, 'clip'):
                                                                track_clips = [track.clip] if track.clip else []
                                                            
                                                            if track_clips:
                                                                # Iterate clips directly if generator
                                                                if hasattr(track_clips, '__iter__') and not isinstance(track_clips, (str, dict)):
                                                                    for clip_item in track_clips:
                                                                        if 'PlaylistEvent' in str(type(clip_item)) or 'Event' in str(type(clip_item)):
                                                                            clip = self._parse_playlist_event(clip_item, track_name)
                                                                        else:
                                                                            clip = self._parse_clip(clip_item, track_name)
                                                                        if clip:
                                                                            clips.append(clip)
                                                                else:
                                                                    clips_list = [track_clips] if track_clips else []
                                                                    for clip_item in clips_list:
                                                                        if 'PlaylistEvent' in str(type(clip_item)) or 'Event' in str(type(clip_item)):
                                                                            clip = self._parse_playlist_event(clip_item, track_name)
                                                                        else:
                                                                            clip = self._parse_clip(clip_item, track_name)
                                                                        if clip:
                                                                            clips.append(clip)
                                                        except Exception as e:
                                                            logger.debug(f"Error processing arrangement track {track_idx}: {e}")
                                                            continue
                                            except StopIteration:
                                                # Generator is empty
                                                pass
                                            except Exception as e:
                                                error_msg = str(e)
                                                if "'data'" in error_msg or "PlaylistEvent" in error_msg:
                                                    logger.debug(f"Cannot iterate arrangement.tracks due to pyflp limitation: {error_msg}")
                                                    logger.debug("Will try alternative methods")
                                                else:
                                                    logger.debug(f"Error iterating arrangement tracks: {e}")
                                        else:
                                            # Not iterable, treat as single item
                                            if tracks_data:
                                                track_name = getattr(tracks_data, 'name', 'Track 1')
                                                if track_name not in tracks:
                                                    tracks.append(track_name)
                                                # Try to get clips
                                                if hasattr(tracks_data, 'clips'):
                                                    for clip_item in tracks_data.clips:
                                                        clip = self._parse_clip(clip_item, track_name)
                                                        if clip:
                                                            clips.append(clip)
                                    except Exception as e:
                                        error_msg = str(e)
                                        if "'data'" in error_msg or "PlaylistEvent" in error_msg:
                                            logger.debug(f"Cannot access arrangement.tracks due to pyflp limitation: {error_msg}")
                                        else:
                                            logger.debug(f"Error accessing arrangement tracks: {e}")
                except Exception as e:
                    logger.debug(f"Error accessing arrangements: {e}")
            
            # Method 3: Try project.events for playlist-related events
            if not clips and hasattr(self.project, 'events'):
                try:
                    project_events = self.project.events
                    if project_events:
                        logger.debug("Trying to extract clips from project.events")
                        # Filter for playlist/arrangement events
                        if hasattr(project_events, '__iter__') and not isinstance(project_events, (str, dict)):
                            try:
                                for event in project_events:
                                    try:
                                        event_type = str(type(event))
                                        event_id = getattr(event, 'id', None)
                                        # Check if it's a playlist-related event
                                        if 'Playlist' in event_type or (event_id and 'Playlist' in str(event_id)):
                                            # Try to parse as clip
                                            track_name = 'Unknown Track'
                                            for attr in ['track', 'track_name', 'track_id', 'channel', 'channel_name']:
                                                if hasattr(event, attr):
                                                    try:
                                                        val = getattr(event, attr)
                                                        if val is not None:
                                                            track_name = str(val)
                                                            break
                                                    except:
                                                        continue
                                            
                                            if track_name not in tracks:
                                                tracks.append(track_name)
                                            
                                            clip = self._parse_playlist_event(event, track_name)
                                            if clip:
                                                clips.append(clip)
                                    except Exception as e:
                                        logger.debug(f"Error processing project event: {e}")
                                        continue
                            except Exception as e:
                                logger.debug(f"Error iterating project.events: {e}")
                except Exception as e:
                    logger.debug(f"Error accessing project.events: {e}")
            
            # Method 4: Try playlist (may fail to parse, but try anyway)
            if not clips and hasattr(self.project, 'playlist'):
                try:
                    playlist = self.project.playlist
                    # Get tracks from playlist
                    playlist_tracks = None
                    if hasattr(playlist, 'tracks'):
                        playlist_tracks = playlist.tracks
                    elif hasattr(playlist, 'track'):
                        playlist_tracks = [playlist.track] if playlist.track else []
                    
                    if playlist_tracks:
                        tracks_list = list(playlist_tracks)
                        for track_idx, track in enumerate(tracks_list):
                            try:
                                track_name = getattr(track, 'name', f'Track {track_idx + 1}')
                                if track_name not in tracks:
                                    tracks.append(track_name)
                                
                                # Get clips from track
                                if hasattr(track, 'clips'):
                                    track_clips = track.clips
                                    if track_clips:
                                        clips_list = list(track_clips)
                                        for clip_item in clips_list:
                                            clip = self._parse_clip(clip_item, track_name)
                                            if clip:
                                                clips.append(clip)
                            except Exception as e:
                                logger.debug(f"Error processing playlist track: {e}")
                                continue
                    
                    # Direct playlist clips
                    if not clips and hasattr(playlist, 'clips'):
                        try:
                            playlist_clips = playlist.clips
                            if playlist_clips:
                                clips_list = list(playlist_clips)
                                for clip_item in clips_list:
                                    clip = self._parse_clip(clip_item, 'Unknown')
                                    if clip:
                                        clips.append(clip)
                                        if clip.track_name not in tracks:
                                            tracks.append(clip.track_name)
                        except Exception as e:
                            logger.debug(f"Error accessing direct playlist clips: {e}")
                except Exception as e:
                    logger.debug(f"Error accessing playlist (may be due to parsing warning): {e}")
            
            total_length = max((c.end_time for c in clips), default=0.0)
            logger.info(f"Extracted {len(clips)} clips from {len(tracks)} tracks")
            
        except Exception as e:
            logger.warning(f"Error extracting arrangement: {e}")
        
        return ArrangementData(clips=clips, total_length=total_length, tracks=tracks)
    
    def _extract_tempo_changes(self) -> List[TempoChange]:
        """Extract tempo changes."""
        tempo_changes = []
        
        if not self.project:
            return tempo_changes
        
        try:
            # Get tempo from project
            tempo = None
            if hasattr(self.project, 'tempo'):
                tempo = self.project.tempo
            elif hasattr(self.project, 'bpm'):
                tempo = self.project.bpm
            elif hasattr(self.project, 'project'):
                proj = self.project.project
                if hasattr(proj, 'tempo'):
                    tempo = proj.tempo
                elif hasattr(proj, 'bpm'):
                    tempo = proj.bpm
            
            # Try to get time signature
            time_signature = None
            # Check various possible attributes for time signature
            for attr in ['time_signature', 'time_sig', 'timeSignature', 'timeSig', 
                        'beats_per_bar', 'beatsPerBar', 'numerator', 'denominator']:
                if hasattr(self.project, attr):
                    try:
                        val = getattr(self.project, attr)
                        if val is not None:
                            if isinstance(val, str):
                                time_signature = val
                            elif isinstance(val, (int, float)):
                                # If it's a single number, assume it's numerator (4/4)
                                if attr in ['numerator', 'beats_per_bar', 'beatsPerBar']:
                                    time_signature = f"{int(val)}/4"
                                else:
                                    time_signature = str(val)
                            elif isinstance(val, (tuple, list)) and len(val) >= 2:
                                # If it's a tuple/list, assume (numerator, denominator)
                                time_signature = f"{int(val[0])}/{int(val[1])}"
                            break
                    except:
                        continue
            
            # If no time signature found, check project.project
            if not time_signature and hasattr(self.project, 'project'):
                proj = self.project.project
                for attr in ['time_signature', 'time_sig', 'timeSignature', 'timeSig', 
                            'beats_per_bar', 'beatsPerBar', 'numerator', 'denominator']:
                    if hasattr(proj, attr):
                        try:
                            val = getattr(proj, attr)
                            if val is not None:
                                if isinstance(val, str):
                                    time_signature = val
                                elif isinstance(val, (int, float)):
                                    if attr in ['numerator', 'beats_per_bar', 'beatsPerBar']:
                                        time_signature = f"{int(val)}/4"
                                    else:
                                        time_signature = str(val)
                                elif isinstance(val, (tuple, list)) and len(val) >= 2:
                                    time_signature = f"{int(val[0])}/{int(val[1])}"
                                break
                        except:
                            continue
            
            # Default to 4/4 if not found (FL Studio default)
            if not time_signature:
                time_signature = "4/4"
            
            if tempo is not None:
                try:
                    tempo_value = float(tempo)
                    tempo_change = TempoChange(
                        time=0.0,
                        tempo=tempo_value,
                        time_signature=time_signature
                    )
                    tempo_changes.append(tempo_change)
                except (ValueError, TypeError):
                    pass
            
            # Check for tempo automation/events
            tempo_events = None
            if hasattr(self.project, 'tempo_events'):
                tempo_events = self.project.tempo_events
            elif hasattr(self.project, 'tempo_automation'):
                tempo_events = self.project.tempo_automation
            elif hasattr(self.project, 'automation'):
                automation = self.project.automation
                if hasattr(automation, 'tempo'):
                    tempo_events = automation.tempo
            
            if tempo_events:
                for event in tempo_events:
                    try:
                        time = 0.0
                        if hasattr(event, 'time'):
                            time = event.time
                        elif hasattr(event, 'position'):
                            time = event.position
                        
                        tempo_value = 120.0
                        if hasattr(event, 'tempo'):
                            tempo_value = event.tempo
                        elif hasattr(event, 'value'):
                            tempo_value = event.value
                        elif hasattr(event, 'bpm'):
                            tempo_value = event.bpm
                        
                        # Try to get time signature from event if available
                        event_time_sig = None
                        if hasattr(event, 'time_signature'):
                            event_time_sig = str(event.time_signature)
                        elif hasattr(event, 'time_sig'):
                            event_time_sig = str(event.time_sig)
                        
                        tempo_change = TempoChange(
                            time=float(time),
                            tempo=float(tempo_value),
                            time_signature=event_time_sig or time_signature
                        )
                        tempo_changes.append(tempo_change)
                    except (ValueError, TypeError, AttributeError):
                        continue
            
            logger.info(f"Extracted {len(tempo_changes)} tempo changes")
            
        except Exception as e:
            logger.warning(f"Error extracting tempo changes: {e}")
        
        return tempo_changes
    
    def _extract_key_changes(self) -> List[KeyChange]:
        """Extract key signature changes."""
        key_changes = []
        
        if not self.project:
            return key_changes
        
        try:
            # FL Studio typically doesn't store key changes explicitly in .flp files
            # But let's check multiple possible locations
            
            # Method 1: Check project attributes
            key_info = None
            for attr in ['key_signature', 'keySignature', 'key', 'key_sig', 'keySig',
                        'tonic', 'scale', 'mode', 'musical_key', 'musicalKey']:
                if hasattr(self.project, attr):
                    try:
                        val = getattr(self.project, attr)
                        if val is not None:
                            key_info = str(val)
                            break
                    except:
                        continue
            
            # Method 2: Check project.project
            if not key_info and hasattr(self.project, 'project'):
                proj = self.project.project
                for attr in ['key_signature', 'keySignature', 'key', 'key_sig', 'keySig',
                            'tonic', 'scale', 'mode', 'musical_key', 'musicalKey']:
                    if hasattr(proj, attr):
                        try:
                            val = getattr(proj, attr)
                            if val is not None:
                                key_info = str(val)
                                break
                        except:
                            continue
            
            # Method 3: Check project metadata/comments
            if not key_info:
                # Sometimes key info is in comments or title
                if hasattr(self.project, 'comments'):
                    comments = self.project.comments
                    if comments and isinstance(comments, str):
                        # Try to extract key from comments (e.g., "Key: E major")
                        import re
                        key_match = re.search(r'(?:key|tonic)[:\s]+([A-G][#b]?\s*(?:major|minor|maj|min))', 
                                            comments, re.IGNORECASE)
                        if key_match:
                            key_info = key_match.group(1)
            
            # Method 4: Check project title
            if not key_info and hasattr(self.project, 'title'):
                title = self.project.title
                if title and isinstance(title, str):
                    # Try to extract key from title (e.g., "Song_E_Major.flp")
                    import re
                    key_match = re.search(r'([A-G][#b]?)\s*(?:major|minor|maj|min)', 
                                        title, re.IGNORECASE)
                    if key_match:
                        key_info = key_match.group(0)
            
            # Method 5: Check filename itself (e.g., "Song_EMAJ.flp" or "Song_E_Major.flp")
            if not key_info:
                import re
                filename = self.file_path.stem  # Get filename without extension
                
                # Pattern 1: Full format like "E Major", "A minor", "C# major" (with spaces or underscores)
                key_match = re.search(r'([A-G][#b]?)[_\s]+(major|minor|maj|min)', 
                                    filename, re.IGNORECASE)
                if key_match:
                    note = key_match.group(1)
                    scale = key_match.group(2).lower()
                    # Normalize scale
                    if scale in ['maj', 'major']:
                        key_info = f"{note} major"
                    elif scale in ['min', 'minor']:
                        key_info = f"{note} minor"
                
                # Pattern 2: Abbreviated format like "EMAJ", "AMIN", "C#MAJ" (no separator)
                if not key_info:
                    key_match = re.search(r'([A-G][#b]?)(MAJ|MIN|MAJOR|MINOR)', 
                                        filename, re.IGNORECASE)
                    if key_match:
                        note = key_match.group(1)
                        scale_abbr = key_match.group(2).upper()
                        if scale_abbr in ['MAJ', 'MAJOR']:
                            key_info = f"{note} major"
                        elif scale_abbr in ['MIN', 'MINOR']:
                            key_info = f"{note} minor"
                
                # Pattern 3: Just the note with underscore separator (e.g., "Song_E_155.flp")
                # This is less reliable, so we check if it's followed by a number (BPM) or other indicators
                if not key_info:
                    # Look for pattern like "_E_" or "_E_" followed by number (BPM)
                    key_match = re.search(r'_([A-G][#b]?)_', filename, re.IGNORECASE)
                    if key_match:
                        note = key_match.group(1)
                        # Check if there's a number after it (likely BPM, suggesting it's a key)
                        after_match = re.search(rf'_{note}_\d+', filename, re.IGNORECASE)
                        if after_match:
                            # Default to major if not specified
                            key_info = f"{note} major"
            
            # Method 6: Check for key events in automation
            if hasattr(self.project, 'key_events'):
                for event in self.project.key_events:
                    try:
                        time = getattr(event, 'time', getattr(event, 'position', 0.0))
                        key = getattr(event, 'key', getattr(event, 'value', None))
                        if not key:
                            key = key_info or 'C major'
                        
                        key_change = KeyChange(
                            time=float(time),
                            key=str(key)
                        )
                        key_changes.append(key_change)
                    except (ValueError, TypeError, AttributeError):
                        continue
            
            # If we found a key but no events, create a single key change at time 0
            if key_info and not key_changes:
                try:
                    # Normalize key format (capitalize first letter, lowercase rest)
                    key_parts = key_info.split()
                    if len(key_parts) >= 2:
                        note = key_parts[0].capitalize()
                        scale = key_parts[1].lower()
                        key_info = f"{note} {scale}"
                    
                    key_change = KeyChange(
                        time=0.0,
                        key=key_info
                    )
                    key_changes.append(key_change)
                except Exception:
                    pass
            
            if key_changes:
                logger.info(f"Extracted {len(key_changes)} key changes")
            else:
                logger.debug("No key signature information found in FL Studio project (this is normal - FL Studio .flp files typically don't store key information)")
            
        except Exception as e:
            logger.debug(f"Error extracting key changes: {e}")
        
        return key_changes
    
    def _extract_plugin_chains(self) -> List[PluginChain]:
        """Extract plugin chains from Channel Rack."""
        chains = []
        
        if not self.project:
            return chains
        
        try:
            # Access channels
            channels = None
            if hasattr(self.project, 'channels'):
                channels = self.project.channels
            elif hasattr(self.project, 'channel_rack'):
                channel_rack = self.project.channel_rack
                if hasattr(channel_rack, 'channels'):
                    channels = channel_rack.channels
            
            if channels:
                for channel in channels:
                    try:
                        channel_name = getattr(channel, 'name', 'Unknown Channel')
                        if not channel_name:
                            channel_name = f'Channel {len(chains) + 1}'
                        
                        devices = []
                        
                        # Get plugins/effects from channel
                        plugins = None
                        if hasattr(channel, 'plugins'):
                            plugins = channel.plugins
                        elif hasattr(channel, 'effects'):
                            plugins = channel.effects
                        elif hasattr(channel, 'inserts'):
                            plugins = channel.inserts
                        elif hasattr(channel, 'devices'):
                            plugins = channel.devices
                        
                        if plugins:
                            for plugin in plugins:
                                try:
                                    # Try multiple ways to get plugin name
                                    device_name = None
                                    
                                    # Method 1: Try plugin.name
                                    if hasattr(plugin, 'name'):
                                        device_name = getattr(plugin, 'name', None)
                                    
                                    # Method 2: Try alternative name attributes
                                    if not device_name:
                                        for attr in ['plugin_name', 'display_name', 'title', 'label', 'id', 'plugin_id']:
                                            if hasattr(plugin, attr):
                                                try:
                                                    val = getattr(plugin, attr)
                                                    if val is not None and isinstance(val, str) and val:
                                                        device_name = str(val)
                                                        break
                                                except:
                                                    continue
                                    
                                    # Method 3: Inspect all plugin attributes
                                    if not device_name:
                                        try:
                                            plugin_attrs = [attr for attr in dir(plugin) if not attr.startswith('_')]
                                            logger.debug(f"Plugin attributes: {plugin_attrs[:20]}")
                                            for attr in plugin_attrs:
                                                if any(keyword in attr.lower() for keyword in ['name', 'title', 'label', 'id']):
                                                    try:
                                                        val = getattr(plugin, attr)
                                                        if val is not None and isinstance(val, str) and val:
                                                            device_name = str(val)
                                                            break
                                                    except:
                                                        continue
                                        except:
                                            pass
                                    
                                    # Final fallback
                                    if not device_name:
                                        device_name = 'Unknown Plugin'
                                    
                                    device_type = 'native'  # Default
                                    if hasattr(plugin, 'type'):
                                        device_type = str(plugin.type).lower()
                                    elif hasattr(plugin, 'plugin_type'):
                                        device_type = str(plugin.plugin_type).lower()
                                    
                                    # Extract parameters
                                    parameters = []
                                    if hasattr(plugin, 'parameters'):
                                        for param in plugin.parameters:
                                            try:
                                                param_name = getattr(param, 'name', 'Unknown')
                                                param_value = getattr(param, 'value', 0.0)
                                                
                                                plugin_param = PluginParameter(
                                                    parameter_name=str(param_name),
                                                    value=float(param_value)
                                                )
                                                parameters.append(plugin_param)
                                            except (ValueError, TypeError, AttributeError):
                                                continue
                                    
                                    device = PluginDevice(
                                        device_name=str(device_name),
                                        device_type=str(device_type),
                                        parameters=parameters
                                    )
                                    devices.append(device)
                                except (ValueError, TypeError, AttributeError) as e:
                                    logger.debug(f"Failed to parse plugin: {e}")
                                    continue
                        
                        # Also check if channel itself is a plugin/instrument
                        if hasattr(channel, 'plugin') and channel.plugin:
                            try:
                                plugin = channel.plugin
                                
                                # Try multiple ways to get plugin name
                                device_name = None
                                
                                # Method 1: Try plugin.name
                                if hasattr(plugin, 'name'):
                                    device_name = getattr(plugin, 'name', None)
                                
                                # Method 2: Try alternative name attributes
                                if not device_name:
                                    for attr in ['plugin_name', 'display_name', 'title', 'label', 'id', 'plugin_id']:
                                        if hasattr(plugin, attr):
                                            try:
                                                val = getattr(plugin, attr)
                                                if val is not None and isinstance(val, str) and val:
                                                    device_name = str(val)
                                                    break
                                            except:
                                                continue
                                
                                # Method 3: Use channel name if it looks like a plugin name
                                # In FL Studio, channel names often match plugin names (e.g., "FLEX Bass")
                                if not device_name and channel_name and channel_name != 'Unknown Channel':
                                    # Check if channel name looks like a plugin name (not generic like "Channel 1")
                                    if not channel_name.startswith('Channel ') and not channel_name.startswith('Track '):
                                        device_name = channel_name
                                        logger.debug(f"Using channel name as plugin name: {device_name}")
                                
                                # Method 4: Inspect all plugin attributes
                                if not device_name:
                                    try:
                                        plugin_attrs = [attr for attr in dir(plugin) if not attr.startswith('_')]
                                        logger.debug(f"Channel plugin attributes: {plugin_attrs[:20]}")
                                        for attr in plugin_attrs:
                                            if any(keyword in attr.lower() for keyword in ['name', 'title', 'label', 'id']):
                                                try:
                                                    val = getattr(plugin, attr)
                                                    if val is not None and isinstance(val, str) and val:
                                                        device_name = str(val)
                                                        logger.debug(f"Found plugin name from attribute {attr}: {device_name}")
                                                        break
                                                except:
                                                    continue
                                    except:
                                        pass
                                
                                # Final fallback
                                if not device_name:
                                    device_name = 'Unknown Plugin'
                                
                                device_type = 'native'  # Default
                                if hasattr(plugin, 'type'):
                                    device_type = str(plugin.type).lower()
                                elif hasattr(plugin, 'plugin_type'):
                                    device_type = str(plugin.plugin_type).lower()
                                
                                parameters = []
                                if hasattr(plugin, 'parameters'):
                                    for param in plugin.parameters:
                                        try:
                                            param_name = getattr(param, 'name', 'Unknown')
                                            param_value = getattr(param, 'value', 0.0)
                                            plugin_param = PluginParameter(
                                                parameter_name=str(param_name),
                                                value=float(param_value)
                                            )
                                            parameters.append(plugin_param)
                                        except (ValueError, TypeError, AttributeError):
                                            continue
                                
                                device = PluginDevice(
                                    device_name=str(device_name),
                                    device_type=str(device_type),
                                    parameters=parameters
                                )
                                devices.append(device)
                            except (ValueError, TypeError, AttributeError) as e:
                                logger.debug(f"Failed to parse channel plugin: {e}")
                        
                        if devices:
                            chain = PluginChain(
                                track_name=str(channel_name),
                                devices=devices
                            )
                            chains.append(chain)
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse channel: {e}")
                        continue
            
            logger.info(f"Extracted {len(chains)} plugin chains")
            
        except Exception as e:
            logger.warning(f"Error extracting plugin chains: {e}")
        
        return chains
    
    def _extract_sample_sources(self) -> List[SampleSource]:
        """Extract sample references."""
        samples = []
        
        if not self.project:
            return samples
        
        try:
            # Access channels and their samples
            channels = None
            if hasattr(self.project, 'channels'):
                channels = self.project.channels
            elif hasattr(self.project, 'channel_rack'):
                channel_rack = self.project.channel_rack
                if hasattr(channel_rack, 'channels'):
                    channels = channel_rack.channels
            
            if channels:
                for channel in channels:
                    try:
                        channel_name = getattr(channel, 'name', 'Unknown')
                        if not channel_name:
                            channel_name = f'Channel {len(samples) + 1}'
                        
                        # Get sample from channel
                        sample_path = None
                        if hasattr(channel, 'sample_path'):
                            sample_path = channel.sample_path
                        elif hasattr(channel, 'file_path'):
                            sample_path = channel.file_path
                        elif hasattr(channel, 'sample'):
                            sample = channel.sample
                            if hasattr(sample, 'path'):
                                sample_path = sample.path
                            elif hasattr(sample, 'file_path'):
                                sample_path = sample.file_path
                        elif hasattr(channel, 'plugin'):
                            # Some plugins may reference samples
                            plugin = channel.plugin
                            if hasattr(plugin, 'sample_path'):
                                sample_path = plugin.sample_path
                        
                        if sample_path:
                            file_path = Path(str(sample_path))
                            if not file_path.is_absolute():
                                # Try relative to project directory
                                file_path = self.file_path.parent / file_path
                            
                            sample = SampleSource(
                                file_path=file_path,
                                sample_name=file_path.name,
                                track_name=str(channel_name)
                            )
                            samples.append(sample)
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse sample: {e}")
                        continue
            
            # Also check for samples in project-level sample list
            if hasattr(self.project, 'samples'):
                for sample in self.project.samples:
                    try:
                        sample_path = None
                        if hasattr(sample, 'path'):
                            sample_path = sample.path
                        elif hasattr(sample, 'file_path'):
                            sample_path = sample.file_path
                        
                        if sample_path:
                            file_path = Path(str(sample_path))
                            if not file_path.is_absolute():
                                file_path = self.file_path.parent / file_path
                            
                            sample_source = SampleSource(
                                file_path=file_path,
                                sample_name=file_path.name
                            )
                            samples.append(sample_source)
                    except (ValueError, TypeError, AttributeError):
                        continue
            
            logger.info(f"Extracted {len(samples)} sample sources")
            
        except Exception as e:
            logger.warning(f"Error extracting sample sources: {e}")
        
        return samples
    
    def _extract_curve_type_from_event(self, event, automation_clip=None, envelope=None) -> Optional[str]:
        """Extract curve type from an automation event.
        
        Args:
            event: The automation event object (could be U16TupleEvent, point, etc.)
            automation_clip: Optional automation clip object that might contain curve info
            envelope: Optional envelope object that might contain curve info
            
        Returns:
            Curve type string (e.g., 'linear', 'bezier', 'step') or 'linear' as default
        """
        curve_type = None
        
        # Method 1: Check automation clip for curve type (FL Studio stores it at clip level)
        if automation_clip:
            for attr in ['curve_type', 'curve', 'interpolation', 'interp', 'smooth', 'bezier', 'type', 'mode', 'shape']:
                if hasattr(automation_clip, attr):
                    try:
                        val = getattr(automation_clip, attr)
                        if val is not None:
                            val_str = str(val).lower()
                            if 'bezier' in val_str or 'cubic' in val_str:
                                return 'bezier'
                            elif 'linear' in val_str:
                                return 'linear'
                            elif 'step' in val_str or 'hold' in val_str:
                                return 'step'
                            elif 'smooth' in val_str:
                                return 'smooth'
                            elif 'sine' in val_str or 'sin' in val_str:
                                return 'sine'
                            else:
                                return val_str
                    except:
                        continue
        
        # Method 2: Check envelope for curve type
        if envelope:
            for attr in ['curve_type', 'curve', 'interpolation', 'interp', 'smooth', 'bezier', 'type', 'mode', 'shape']:
                if hasattr(envelope, attr):
                    try:
                        val = getattr(envelope, attr)
                        if val is not None:
                            val_str = str(val).lower()
                            if 'bezier' in val_str or 'cubic' in val_str:
                                return 'bezier'
                            elif 'linear' in val_str:
                                return 'linear'
                            elif 'step' in val_str or 'hold' in val_str:
                                return 'step'
                            elif 'smooth' in val_str:
                                return 'smooth'
                            elif 'sine' in val_str or 'sin' in val_str:
                                return 'sine'
                            else:
                                return val_str
                    except:
                        continue
        
        # Method 3: Check event object itself
        for attr in ['curve_type', 'curve', 'interpolation', 'interp', 'smooth', 'bezier', 'type', 'mode', 'shape']:
            if hasattr(event, attr):
                try:
                    val = getattr(event, attr)
                    if val is not None:
                        val_str = str(val).lower()
                        if 'bezier' in val_str or 'cubic' in val_str:
                            return 'bezier'
                        elif 'linear' in val_str:
                            return 'linear'
                        elif 'step' in val_str or 'hold' in val_str:
                            return 'step'
                        elif 'smooth' in val_str:
                            return 'smooth'
                        elif 'sine' in val_str or 'sin' in val_str:
                            return 'sine'
                        else:
                            return val_str
                except:
                    continue
        
        # Method 4: Pattern-based inference (analyze point values to guess curve type)
        # This is a fallback when curve type is not explicitly stored
        if hasattr(event, 'value') or (hasattr(event, '__iter__') and not isinstance(event, (str, dict))):
            try:
                # Try to get multiple points to analyze pattern
                points_to_analyze = []
                if hasattr(event, 'value'):
                    value = event.value
                    if isinstance(value, tuple) and len(value) >= 2:
                        points_to_analyze.append((float(value[0]) if len(value) > 0 else 0.0, 
                                                 float(value[1]) if len(value) > 1 else 0.0))
                
                # If we have multiple points, analyze the pattern
                if len(points_to_analyze) >= 2:
                    # Calculate differences between consecutive points
                    diffs = []
                    for i in range(1, len(points_to_analyze)):
                        time_diff = points_to_analyze[i][0] - points_to_analyze[i-1][0]
                        value_diff = abs(points_to_analyze[i][1] - points_to_analyze[i-1][1])
                        if time_diff > 0:
                            rate = value_diff / time_diff
                            diffs.append(rate)
                    
                    if diffs:
                        # Check for step pattern (sudden jumps)
                        max_diff = max(diffs) if diffs else 0
                        if max_diff > 10:  # Large sudden changes suggest step
                            return 'step'
                        
                        # Check for smooth/bezier pattern (gradual changes)
                        avg_diff = sum(diffs) / len(diffs) if diffs else 0
                        if avg_diff < 1.0 and max_diff < 5.0:
                            return 'smooth'
            except:
                pass
        
        # Default to linear (FL Studio's default automation curve)
        return 'linear'
    
    def _extract_automation(self) -> List[AutomationData]:
        """Extract automation data."""
        automation_list = []
        
        if not self.project:
            return automation_list
        
        try:
            # Access automation clips - pyflp structure: project.automation_clips
            automation_clips = None
            if hasattr(self.project, 'automation_clips'):
                automation_clips = self.project.automation_clips
            elif hasattr(self.project, 'automation'):
                automation = self.project.automation
                if hasattr(automation, 'clips'):
                    automation_clips = automation.clips
                elif isinstance(automation, (list, tuple)):
                    automation_clips = automation
            
            if automation_clips:
                # Convert to list if it's a generator
                if hasattr(automation_clips, '__iter__') and not isinstance(automation_clips, (str, dict)):
                    try:
                        automation_clips = list(automation_clips)
                    except Exception as e:
                        logger.debug(f"Error converting automation_clips to list: {e}")
                        automation_clips = []
                
                for auto_clip in automation_clips:
                    try:
                        # Get parameter name
                        parameter_name = 'Unknown'
                        if hasattr(auto_clip, 'parameter'):
                            param = auto_clip.parameter
                            if isinstance(param, str):
                                parameter_name = param
                            elif hasattr(param, 'name'):
                                parameter_name = param.name
                        elif hasattr(auto_clip, 'parameter_name'):
                            parameter_name = str(auto_clip.parameter_name)
                        elif hasattr(auto_clip, 'name'):
                            parameter_name = str(auto_clip.name)
                        
                        # Get track/channel name
                        track_name = 'Unknown'
                        if hasattr(auto_clip, 'track'):
                            track = auto_clip.track
                            if isinstance(track, str):
                                track_name = track
                            elif hasattr(track, 'name'):
                                track_name = track.name
                        elif hasattr(auto_clip, 'channel'):
                            channel = auto_clip.channel
                            if isinstance(channel, str):
                                track_name = channel
                            elif hasattr(channel, 'name'):
                                track_name = channel.name
                        elif hasattr(auto_clip, 'track_name'):
                            track_name = str(auto_clip.track_name)
                        
                        # Extract automation points - pyflp structure: automation_clip.points
                        points = []
                        if hasattr(auto_clip, 'points'):
                            points_data = auto_clip.points
                            # Convert to list if it's a generator
                            if hasattr(points_data, '__iter__') and not isinstance(points_data, (str, dict)):
                                try:
                                    points_data = list(points_data)
                                except Exception:
                                    points_data = []
                            
                            if isinstance(points_data, (list, tuple)):
                                for point in points_data:
                                    try:
                                        time = getattr(point, 'time', getattr(point, 'position', 0.0))
                                        value = getattr(point, 'value', 0.0)
                                        
                                        # Get envelope if available
                                        envelope = None
                                        if hasattr(auto_clip, 'envelope'):
                                            envelope = auto_clip.envelope
                                        
                                        curve_type = self._extract_curve_type_from_event(point, automation_clip=auto_clip, envelope=envelope)
                                        
                                        auto_point = AutomationPoint(
                                            time=float(time),
                                            value=float(value),
                                            curve_type=curve_type
                                        )
                                        points.append(auto_point)
                                    except (ValueError, TypeError, AttributeError):
                                        continue
                        
                        # Also check for envelope data
                        if not points and hasattr(auto_clip, 'envelope'):
                            try:
                                envelope = auto_clip.envelope
                                if hasattr(envelope, 'points'):
                                    for point in envelope.points:
                                        try:
                                            time = getattr(point, 'time', 0.0)
                                            value = getattr(point, 'value', 0.0)
                                            curve_type = self._extract_curve_type_from_event(point, automation_clip=auto_clip, envelope=envelope)
                                            points.append(AutomationPoint(
                                                time=float(time),
                                                value=float(value),
                                                curve_type=curve_type
                                            ))
                                        except (ValueError, TypeError, AttributeError):
                                            continue
                            except Exception:
                                pass
                        
                        if points:
                            automation_data = AutomationData(
                                parameter_name=str(parameter_name),
                                track_name=str(track_name),
                                points=points
                            )
                            automation_list.append(automation_data)
                    
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse automation clip: {e}")
                        continue
            
            # Method 2: Check arrangement.events for automation events
            if not automation_list and hasattr(self.project, 'arrangements'):
                try:
                    arrangements = self.project.arrangements
                    if arrangements:
                        if hasattr(arrangements, '__iter__') and not isinstance(arrangements, (str, dict)):
                            arrangements = list(arrangements)
                        else:
                            arrangements = [arrangements] if arrangements else []
                        
                        for arrangement in arrangements:
                            # Try arrangement.events (similar to how we extract clips)
                            if hasattr(arrangement, 'events'):
                                try:
                                    arr_events = arrangement.events
                                    if arr_events and hasattr(arr_events, '__iter__'):
                                        logger.debug("Checking arrangement.events for automation")
                                        for event in arr_events:
                                            try:
                                                event_type = str(type(event))
                                                event_id = getattr(event, 'id', None)
                                                
                                                # Check if it's an automation event (broader detection)
                                                is_automation = (
                                                    'Automation' in event_type or 
                                                    'Auto' in event_type or 
                                                    'Envelope' in event_type or
                                                    'Modulation' in event_type or
                                                    'Controller' in event_type or
                                                    (event_id and ('Auto' in str(event_id) or 'Env' in str(event_id) or 'Mod' in str(event_id) or 'Ctrl' in str(event_id)))
                                                )
                                                
                                                # Also check event attributes for automation indicators
                                                if not is_automation:
                                                    event_attrs = [x.lower() for x in dir(event) if not x.startswith('_')]
                                                    if any(keyword in ' '.join(event_attrs) for keyword in ['automation', 'envelope', 'modulation', 'controller', 'parameter']):
                                                        is_automation = True
                                                
                                                if is_automation:
                                                    # Special handling for U16TupleEvent (same as project.events)
                                                    if 'U16TupleEvent' in event_type:
                                                        try:
                                                            # Extract parameter name from event ID
                                                            parameter_name = 'Unknown'
                                                            if event_id:
                                                                event_id_str = str(event_id)
                                                                if '.' in event_id_str:
                                                                    parameter_name = event_id_str.split('.')[-1]
                                                                else:
                                                                    parameter_name = event_id_str
                                                            
                                                            # Extract channel information
                                                            track_name = 'Unknown'
                                                            channel_index = None
                                                            
                                                            if event_id:
                                                                event_id_str = str(event_id)
                                                                if 'ChannelID' in event_id_str:
                                                                    for attr in ['channel', 'channel_index', 'channel_id', 'index']:
                                                                        if hasattr(event, attr):
                                                                            try:
                                                                                val = getattr(event, attr)
                                                                                if val is not None:
                                                                                    channel_index = int(val) if isinstance(val, (int, float)) else None
                                                                                    break
                                                                            except:
                                                                                continue
                                                                    
                                                                    if channel_index is not None and hasattr(self.project, 'channels'):
                                                                        try:
                                                                            channels = self.project.channels
                                                                            if channels:
                                                                                channels_list = list(channels) if hasattr(channels, '__iter__') else [channels]
                                                                                if isinstance(channel_index, int) and 0 <= channel_index < len(channels_list):
                                                                                    channel = channels_list[channel_index]
                                                                                    track_name = getattr(channel, 'name', f'Channel {channel_index + 1}')
                                                                                else:
                                                                                    track_name = f'Channel {channel_index + 1}'
                                                                        except:
                                                                            track_name = f'Channel {channel_index + 1}' if channel_index is not None else 'Unknown'
                                                            
                                                            # Extract automation value from tuple
                                                            points = []
                                                            if hasattr(event, 'value'):
                                                                try:
                                                                    value_tuple = event.value
                                                                    if isinstance(value_tuple, tuple):
                                                                        if len(value_tuple) >= 2:
                                                                            try:
                                                                                time_val = float(value_tuple[0])
                                                                                value_val = float(value_tuple[1])
                                                                                curve_type = self._extract_curve_type_from_event(event)
                                                                                points.append(AutomationPoint(time=time_val, value=value_val, curve_type=curve_type))
                                                                            except:
                                                                                try:
                                                                                    value_val = float(value_tuple[0])
                                                                                    curve_type = self._extract_curve_type_from_event(event)
                                                                                    points.append(AutomationPoint(time=0.0, value=value_val, curve_type=curve_type))
                                                                                except:
                                                                                    pass
                                                                        elif len(value_tuple) == 1:
                                                                            try:
                                                                                value_val = float(value_tuple[0])
                                                                                points.append(AutomationPoint(time=0.0, value=value_val))
                                                                            except:
                                                                                pass
                                                                    elif isinstance(value_tuple, (int, float)):
                                                                        curve_type = self._extract_curve_type_from_event(event)
                                                                        points.append(AutomationPoint(time=0.0, value=float(value_tuple), curve_type=curve_type))
                                                                except Exception as e:
                                                                    logger.debug(f"Error extracting value from U16TupleEvent: {e}")
                                                            
                                                            if not points:
                                                                for attr in ['points', 'envelope', 'data', 'values', 'xy', 'modulation']:
                                                                    if hasattr(event, attr):
                                                                        try:
                                                                            points_data = getattr(event, attr)
                                                                            if isinstance(points_data, tuple) and len(points_data) >= 2:
                                                                                try:
                                                                                    time_val = float(points_data[0])
                                                                                    value_val = float(points_data[1])
                                                                                    curve_type = self._extract_curve_type_from_event(event)
                                                                                    points.append(AutomationPoint(time=time_val, value=value_val, curve_type=curve_type))
                                                                                except:
                                                                                    pass
                                                                        except:
                                                                            continue
                                                            
                                                            if parameter_name != 'Unknown' or points:
                                                                default_curve = self._extract_curve_type_from_event(event) if hasattr(event, '__class__') else 'linear'
                                                                automation_data = AutomationData(
                                                                    parameter_name=str(parameter_name),
                                                                    track_name=str(track_name),
                                                                    points=points if points else [AutomationPoint(time=0.0, value=0.0, curve_type=default_curve)]
                                                                )
                                                                automation_list.append(automation_data)
                                                        except Exception as e:
                                                            logger.debug(f"Error processing U16TupleEvent in arrangement: {e}")
                                                    else:
                                                        # Standard automation event handling
                                                        # Try to extract automation data from event
                                                        parameter_name = 'Unknown'
                                                        for attr in ['parameter', 'parameter_name', 'name', 'target']:
                                                            if hasattr(event, attr):
                                                                try:
                                                                    val = getattr(event, attr)
                                                                    if val is not None:
                                                                        parameter_name = str(val)
                                                                        break
                                                                except:
                                                                    continue
                                                        
                                                        # Extract from event ID if not found
                                                        if parameter_name == 'Unknown' and event_id:
                                                            event_id_str = str(event_id)
                                                            if '.' in event_id_str:
                                                                parameter_name = event_id_str.split('.')[-1]
                                                            else:
                                                                parameter_name = event_id_str
                                                        
                                                        track_name = 'Unknown'
                                                        for attr in ['track', 'track_name', 'channel', 'channel_name']:
                                                            if hasattr(event, attr):
                                                                try:
                                                                    val = getattr(event, attr)
                                                                    if val is not None:
                                                                        track_name = str(val)
                                                                        break
                                                                except:
                                                                    continue
                                                        
                                                        # Extract points from event
                                                        points = []
                                                        for attr in ['points', 'envelope', 'data', 'values']:
                                                            if hasattr(event, attr):
                                                                try:
                                                                    points_data = getattr(event, attr)
                                                                    if hasattr(points_data, '__iter__') and not isinstance(points_data, (str, dict)):
                                                                        try:
                                                                            points_data = list(points_data)
                                                                        except:
                                                                            continue
                                                                    
                                                                    if isinstance(points_data, (list, tuple)):
                                                                        for point in points_data:
                                                                            try:
                                                                                time = getattr(point, 'time', getattr(point, 'position', getattr(point, 't', 0.0)))
                                                                                value = getattr(point, 'value', getattr(point, 'v', 0.0))
                                                                                curve_type = self._extract_curve_type_from_event(point) if hasattr(point, '__class__') else 'linear'
                                                                                points.append(AutomationPoint(time=float(time), value=float(value), curve_type=curve_type))
                                                                            except:
                                                                                continue
                                                                except:
                                                                    continue
                                                        
                                                        if points or parameter_name != 'Unknown':
                                                            default_curve = self._extract_curve_type_from_event(event) if hasattr(event, '__class__') else 'linear'
                                                            automation_data = AutomationData(
                                                                parameter_name=str(parameter_name),
                                                                track_name=str(track_name),
                                                                points=points if points else [AutomationPoint(time=0.0, value=0.0, curve_type=default_curve)]
                                                            )
                                                            automation_list.append(automation_data)
                                            except Exception as e:
                                                logger.debug(f"Error processing automation event: {e}")
                                                continue
                                except Exception as e:
                                    logger.debug(f"Error accessing arrangement.events for automation: {e}")
                            
                            # Also try arrangement.tracks (may fail due to PlaylistEvent issue)
                            if not automation_list and hasattr(arrangement, 'tracks'):
                                try:
                                    tracks_data = arrangement.tracks
                                    if tracks_data:
                                        if hasattr(tracks_data, '__iter__') and not isinstance(tracks_data, (str, dict)):
                                            try:
                                                tracks_data = list(tracks_data)
                                            except Exception:
                                                # Skip if it fails (PlaylistEvent issue)
                                                continue
                                        else:
                                            tracks_data = [tracks_data] if tracks_data else []
                                        
                                        for track in tracks_data:
                                            # Check if track has automation clips
                                            if hasattr(track, 'automation_clips') or hasattr(track, 'automation'):
                                                auto_clips = getattr(track, 'automation_clips', None) or getattr(track, 'automation', None)
                                                if auto_clips:
                                                    if hasattr(auto_clips, '__iter__') and not isinstance(auto_clips, (str, dict)):
                                                        auto_clips = list(auto_clips)
                                                    else:
                                                        auto_clips = [auto_clips] if auto_clips else []
                                                    
                                                    for auto_clip in auto_clips:
                                                        try:
                                                            parameter_name = getattr(auto_clip, 'parameter', getattr(auto_clip, 'name', 'Unknown'))
                                                            track_name = getattr(track, 'name', 'Unknown')
                                                            
                                                            points = []
                                                            if hasattr(auto_clip, 'points'):
                                                                points_data = getattr(auto_clip, 'points')
                                                                if hasattr(points_data, '__iter__') and not isinstance(points_data, (str, dict)):
                                                                    points_data = list(points_data)
                                                                if isinstance(points_data, (list, tuple)):
                                                                    for point in points_data:
                                                                        try:
                                                                            time = getattr(point, 'time', getattr(point, 'position', 0.0))
                                                                            value = getattr(point, 'value', 0.0)
                                                                            curve_type = self._extract_curve_type_from_event(point) if hasattr(point, '__class__') else 'linear'
                                                                            points.append(AutomationPoint(time=float(time), value=float(value), curve_type=curve_type))
                                                                        except:
                                                                            continue
                                                            
                                                            if points:
                                                                automation_data = AutomationData(
                                                                    parameter_name=str(parameter_name),
                                                                    track_name=str(track_name),
                                                                    points=points
                                                                )
                                                                automation_list.append(automation_data)
                                                        except:
                                                            continue
                                except Exception as e:
                                    logger.debug(f"Error checking arrangement.tracks for automation: {e}")
                except Exception as e:
                    logger.debug(f"Error checking arrangements for automation: {e}")
            
            # Method 3: Check channels for automation
            if not automation_list and hasattr(self.project, 'channels'):
                try:
                    channels = self.project.channels
                    if channels:
                        channels_list = list(channels) if hasattr(channels, '__iter__') else [channels]
                        for channel in channels_list:
                            try:
                                channel_name = getattr(channel, 'name', 'Unknown Channel')
                                
                                # Check for automation attributes
                                for attr in ['automation', 'automation_clips', 'envelope', 'modulation']:
                                    if hasattr(channel, attr):
                                        try:
                                            auto_data = getattr(channel, attr)
                                            if auto_data:
                                                # Try to extract automation points
                                                points = []
                                                if hasattr(auto_data, 'points'):
                                                    points_data = getattr(auto_data, 'points')
                                                    if hasattr(points_data, '__iter__'):
                                                        try:
                                                            points_data = list(points_data)
                                                            for point in points_data:
                                                                try:
                                                                    time = getattr(point, 'time', 0.0)
                                                                    value = getattr(point, 'value', 0.0)
                                                                    points.append(AutomationPoint(time=float(time), value=float(value)))
                                                                except:
                                                                    continue
                                                        except:
                                                            pass
                                                
                                                if points:
                                                    automation_data = AutomationData(
                                                        parameter_name=f"Channel {attr}",
                                                        track_name=str(channel_name),
                                                        points=points
                                                    )
                                                    automation_list.append(automation_data)
                                        except:
                                            continue
                                
                                # Check plugin parameters for automation
                                if hasattr(channel, 'plugin') and channel.plugin:
                                    try:
                                        plugin = channel.plugin
                                        if hasattr(plugin, 'parameters'):
                                            params = plugin.parameters
                                            if params:
                                                params_list = list(params) if hasattr(params, '__iter__') else [params]
                                                for param in params_list:
                                                    try:
                                                        param_name = getattr(param, 'name', 'Unknown Parameter')
                                                        # Check if parameter has automation
                                                        if hasattr(param, 'automation') or hasattr(param, 'envelope'):
                                                            auto_data = getattr(param, 'automation', None) or getattr(param, 'envelope', None)
                                                            if auto_data:
                                                                points = []
                                                                if hasattr(auto_data, 'points'):
                                                                    points_data = getattr(auto_data, 'points')
                                                                    if hasattr(points_data, '__iter__'):
                                                                        try:
                                                                            points_data = list(points_data)
                                                                            for point in points_data:
                                                                                try:
                                                                                    time = getattr(point, 'time', 0.0)
                                                                                    value = getattr(point, 'value', 0.0)
                                                                                    curve_type = self._extract_curve_type_from_event(point) if hasattr(point, '__class__') else 'linear'
                                                                                    points.append(AutomationPoint(time=float(time), value=float(value), curve_type=curve_type))
                                                                                except:
                                                                                    continue
                                                                        except:
                                                                            pass
                                                                
                                                                if points:
                                                                    automation_data = AutomationData(
                                                                        parameter_name=str(param_name),
                                                                        track_name=str(channel_name),
                                                                        points=points
                                                                    )
                                                                    automation_list.append(automation_data)
                                                    except:
                                                        continue
                                    except:
                                        pass
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"Error checking channels for automation: {e}")
            
            # Method 4: Check project.events for automation events
            if not automation_list and hasattr(self.project, 'events'):
                try:
                    project_events = self.project.events
                    if project_events and hasattr(project_events, '__iter__'):
                        logger.debug("Checking project.events for automation")
                        for event in project_events:
                            try:
                                event_type = str(type(event))
                                event_id = getattr(event, 'id', None)
                                
                                # Check if it's an automation event (broader detection)
                                is_automation = (
                                    'Automation' in event_type or 
                                    'Auto' in event_type or 
                                    'Envelope' in event_type or
                                    'Modulation' in event_type or
                                    'Controller' in event_type or
                                    (event_id and ('Auto' in str(event_id) or 'Env' in str(event_id) or 'Mod' in str(event_id) or 'Ctrl' in str(event_id)))
                                )
                                
                                # Also check event attributes for automation indicators
                                if not is_automation:
                                    try:
                                        event_attrs = [x.lower() for x in dir(event) if not x.startswith('_')]
                                        if any(keyword in ' '.join(event_attrs) for keyword in ['automation', 'envelope', 'modulation', 'controller', 'parameter']):
                                            is_automation = True
                                    except:
                                        pass
                                
                                if is_automation:
                                    # Special handling for U16TupleEvent (channel automation events)
                                    if 'U16TupleEvent' in event_type:
                                        try:
                                            # Extract parameter name from event ID (e.g., ChannelID.DelayModXY -> "DelayModXY")
                                            parameter_name = 'Unknown'
                                            if event_id:
                                                event_id_str = str(event_id)
                                                # Extract parameter name from ID (last part after dot)
                                                if '.' in event_id_str:
                                                    parameter_name = event_id_str.split('.')[-1]
                                                else:
                                                    parameter_name = event_id_str
                                            
                                            # Extract channel information
                                            track_name = 'Unknown'
                                            channel_index = None
                                            
                                            # Try to get channel from event ID (ChannelID.XXX)
                                            if event_id:
                                                event_id_str = str(event_id)
                                                if 'ChannelID' in event_id_str:
                                                    # Try to extract channel index from event structure
                                                    # Check for channel-related attributes
                                                    for attr in ['channel', 'channel_index', 'channel_id', 'index']:
                                                        if hasattr(event, attr):
                                                            try:
                                                                val = getattr(event, attr)
                                                                if val is not None:
                                                                    channel_index = int(val) if isinstance(val, (int, float)) else None
                                                                    break
                                                            except:
                                                                continue
                                                    
                                                    # Try to get channel name from project
                                                    if channel_index is not None and hasattr(self.project, 'channels'):
                                                        try:
                                                            channels = self.project.channels
                                                            if channels:
                                                                channels_list = list(channels) if hasattr(channels, '__iter__') else [channels]
                                                                if isinstance(channel_index, int) and 0 <= channel_index < len(channels_list):
                                                                    channel = channels_list[channel_index]
                                                                    track_name = getattr(channel, 'name', f'Channel {channel_index + 1}')
                                                                else:
                                                                    track_name = f'Channel {channel_index + 1}'
                                                        except:
                                                            track_name = f'Channel {channel_index + 1}' if channel_index is not None else 'Unknown'
                                            
                                            # Extract automation value from tuple
                                            points = []
                                            if hasattr(event, 'value'):
                                                try:
                                                    value_tuple = event.value
                                                    # U16TupleEvent.value is typically a tuple of (time, value) or similar
                                                    if isinstance(value_tuple, tuple):
                                                        # Try different tuple interpretations
                                                        if len(value_tuple) >= 2:
                                                            # Assume (time, value) or (x, y) format
                                                            try:
                                                                time_val = float(value_tuple[0]) if len(value_tuple) > 0 else 0.0
                                                                value_val = float(value_tuple[1]) if len(value_tuple) > 1 else 0.0
                                                                curve_type = self._extract_curve_type_from_event(event)
                                                                points.append(AutomationPoint(time=time_val, value=value_val, curve_type=curve_type))
                                                            except:
                                                                # Try as single value
                                                                try:
                                                                    value_val = float(value_tuple[0]) if len(value_tuple) > 0 else 0.0
                                                                    curve_type = self._extract_curve_type_from_event(event)
                                                                    points.append(AutomationPoint(time=0.0, value=value_val, curve_type=curve_type))
                                                                except:
                                                                    pass
                                                        elif len(value_tuple) == 1:
                                                            # Single value
                                                            try:
                                                                value_val = float(value_tuple[0])
                                                                curve_type = self._extract_curve_type_from_event(event)
                                                                points.append(AutomationPoint(time=0.0, value=value_val, curve_type=curve_type))
                                                            except:
                                                                pass
                                                    elif isinstance(value_tuple, (int, float)):
                                                        # Direct numeric value
                                                        curve_type = self._extract_curve_type_from_event(event)
                                                        points.append(AutomationPoint(time=0.0, value=float(value_tuple), curve_type=curve_type))
                                                except Exception as e:
                                                    logger.debug(f"Error extracting value from U16TupleEvent: {e}")
                                            
                                            # Also check for other automation data attributes
                                            if not points:
                                                for attr in ['points', 'envelope', 'data', 'values', 'xy', 'modulation']:
                                                    if hasattr(event, attr):
                                                        try:
                                                            points_data = getattr(event, attr)
                                                            if isinstance(points_data, tuple):
                                                                if len(points_data) >= 2:
                                                                    try:
                                                                        time_val = float(points_data[0])
                                                                        value_val = float(points_data[1])
                                                                        curve_type = self._extract_curve_type_from_event(event)
                                                                        points.append(AutomationPoint(time=time_val, value=value_val, curve_type=curve_type))
                                                                    except:
                                                                        pass
                                                            elif hasattr(points_data, '__iter__') and not isinstance(points_data, (str, dict)):
                                                                try:
                                                                    points_data = list(points_data)
                                                                    if isinstance(points_data, list) and len(points_data) > 0:
                                                                        for point in points_data:
                                                                            try:
                                                                                if isinstance(point, tuple) and len(point) >= 2:
                                                                                    time_val = float(point[0])
                                                                                    value_val = float(point[1])
                                                                                    curve_type = self._extract_curve_type_from_event(event)
                                                                                    points.append(AutomationPoint(time=time_val, value=value_val, curve_type=curve_type))
                                                                                elif hasattr(point, 'time') and hasattr(point, 'value'):
                                                                                    time_val = float(getattr(point, 'time', 0.0))
                                                                                    value_val = float(getattr(point, 'value', 0.0))
                                                                                    curve_type = self._extract_curve_type_from_event(point) if hasattr(point, '__class__') else self._extract_curve_type_from_event(event)
                                                                                    points.append(AutomationPoint(time=time_val, value=value_val, curve_type=curve_type))
                                                                            except:
                                                                                continue
                                                                except:
                                                                    pass
                                                        except:
                                                            continue
                                            
                                            # Create automation data if we have at least parameter name or points
                                            if parameter_name != 'Unknown' or points:
                                                automation_data = AutomationData(
                                                    parameter_name=str(parameter_name),
                                                    track_name=str(track_name),
                                                    points=points if points else [AutomationPoint(time=0.0, value=0.0)]  # At least one point
                                                )
                                                automation_list.append(automation_data)
                                        except Exception as e:
                                            logger.debug(f"Error processing U16TupleEvent: {e}")
                                    else:
                                        # Standard automation event handling
                                        # Extract automation data (similar to arrangement.events)
                                        parameter_name = 'Unknown'
                                        for attr in ['parameter', 'parameter_name', 'name', 'target']:
                                            if hasattr(event, attr):
                                                try:
                                                    val = getattr(event, attr)
                                                    if val is not None:
                                                        parameter_name = str(val)
                                                        break
                                                except:
                                                    continue
                                        
                                        # If parameter name not found, try to extract from event ID
                                        if parameter_name == 'Unknown' and event_id:
                                            event_id_str = str(event_id)
                                            if '.' in event_id_str:
                                                parameter_name = event_id_str.split('.')[-1]
                                            else:
                                                parameter_name = event_id_str
                                        
                                        track_name = 'Unknown'
                                        for attr in ['track', 'track_name', 'channel', 'channel_name']:
                                            if hasattr(event, attr):
                                                try:
                                                    val = getattr(event, attr)
                                                    if val is not None:
                                                        track_name = str(val)
                                                        break
                                                except:
                                                    continue
                                        
                                        # Extract points
                                        points = []
                                        for attr in ['points', 'envelope', 'data', 'values']:
                                            if hasattr(event, attr):
                                                try:
                                                    points_data = getattr(event, attr)
                                                    if hasattr(points_data, '__iter__') and not isinstance(points_data, (str, dict)):
                                                        try:
                                                            points_data = list(points_data)
                                                        except:
                                                            continue
                                                    
                                                    if isinstance(points_data, (list, tuple)):
                                                        for point in points_data:
                                                            try:
                                                                time = getattr(point, 'time', getattr(point, 'position', getattr(point, 't', 0.0)))
                                                                value = getattr(point, 'value', getattr(point, 'v', 0.0))
                                                                curve_type = self._extract_curve_type_from_event(point) if hasattr(point, '__class__') else 'linear'
                                                                points.append(AutomationPoint(time=float(time), value=float(value), curve_type=curve_type))
                                                            except:
                                                                continue
                                                except:
                                                    continue
                                        
                                        if points or parameter_name != 'Unknown':
                                            automation_data = AutomationData(
                                                parameter_name=str(parameter_name),
                                                track_name=str(track_name),
                                                points=points if points else [AutomationPoint(time=0.0, value=0.0)]
                                            )
                                            automation_list.append(automation_data)
                            except Exception as e:
                                logger.debug(f"Error processing project automation event: {e}")
                                continue
                except Exception as e:
                    logger.debug(f"Error checking project.events for automation: {e}")
            
            # Also check playlist for automation clips
            if not automation_list and hasattr(self.project, 'playlist'):
                try:
                    playlist = self.project.playlist
                    if hasattr(playlist, 'tracks'):
                        tracks_data = playlist.tracks
                        if hasattr(tracks_data, '__iter__') and not isinstance(tracks_data, (str, dict)):
                            tracks_data = list(tracks_data)
                        else:
                            tracks_data = [tracks_data] if tracks_data else []
                        
                        for track in tracks_data:
                            if hasattr(track, 'clips'):
                                for clip in track.clips:
                                    # Check if clip is automation
                                    if hasattr(clip, 'automation') or hasattr(clip, 'is_automation'):
                                        try:
                                            parameter_name = getattr(clip, 'parameter', 'Unknown')
                                            track_name = getattr(track, 'name', 'Unknown')
                                            
                                            points = []
                                            if hasattr(clip, 'points'):
                                                for point in clip.points:
                                                    try:
                                                        time = getattr(point, 'time', 0.0)
                                                        value = getattr(point, 'value', 0.0)
                                                        points.append(AutomationPoint(
                                                            time=float(time),
                                                            value=float(value)
                                                        ))
                                                    except (ValueError, TypeError, AttributeError):
                                                        continue
                                            
                                            if points:
                                                automation_data = AutomationData(
                                                    parameter_name=str(parameter_name),
                                                    track_name=str(track_name),
                                                    points=points
                                                )
                                                automation_list.append(automation_data)
                                        except (ValueError, TypeError, AttributeError):
                                            continue
                except Exception:
                    pass
            
            logger.info(f"Extracted {len(automation_list)} automation tracks")
            
        except Exception as e:
            logger.warning(f"Error extracting automation: {e}")
        
        return automation_list
