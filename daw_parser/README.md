# DAW Project File Parser

This module provides functionality to parse DAW (Digital Audio Workstation) project files and extract compositional metadata for use with the audio fingerprinting system.

## Supported Formats

### Phase 1 (Current)
- **Ableton Live (.als)** - Full support

### Phase 2 (Planned)
- **FL Studio (.flp)** - In development
- **Logic Pro (.logicx)** - In development

## Features

The parser extracts the following metadata from DAW project files:

1. **MIDI Data**: Notes, velocities, timing, note lengths
2. **Arrangement**: Track entry/exit times, clip positions, timeline structure
3. **Tempo/Key Changes**: Tempo map, key signature changes, time signature changes
4. **Plugin Chains**: VST/AU plugins per track, plugin parameters, effect routing
5. **Sample Sources**: Audio file references, sample paths, sample metadata
6. **Automation Data**: Parameter automation curves, envelope data, modulation

## Usage

### Basic Usage

```python
from pathlib import Path
from daw_parser import AbletonParser

# Parse an Ableton Live project
parser = AbletonParser(Path("project.als"))
metadata = parser.parse()

# Access extracted data
print(f"MIDI Tracks: {len(metadata.midi_data)}")
print(f"Total Notes: {sum(len(track.notes) for track in metadata.midi_data)}")
print(f"Tempo Changes: {len(metadata.tempo_changes)}")
print(f"Plugin Chains: {len(metadata.plugin_chains)}")

# Convert to dictionary for JSON serialization
metadata_dict = metadata.to_dict()
```

### Using the CLI Tool

Process a single file:
```bash
python scripts/process_daw_files.py project.als -o data/daw_metadata
```

Process all .als files in a directory:
```bash
python scripts/process_daw_files.py /path/to/projects -o data/daw_metadata
```

### Integration with Data Ingestion

The DAW metadata can be linked to audio files during the data ingestion process:

```python
from daw_parser import AbletonParser
from pathlib import Path

# Parse DAW file
daw_file = Path("project.als")
parser = AbletonParser(daw_file)
daw_metadata = parser.parse()

# Link to audio file
audio_file = Path("project_export.wav")
# Store metadata alongside audio file
# (Integration with data_ingest.py will be added in Phase 3)
```

## Data Models

### DAWMetadata

Main container for all extracted metadata:

```python
@dataclass
class DAWMetadata:
    project_path: Path
    daw_type: DAWType
    version: str
    midi_data: List[MIDITrack]
    arrangement: ArrangementData
    tempo_changes: List[TempoChange]
    key_changes: List[KeyChange]
    plugin_chains: List[PluginChain]
    sample_sources: List[SampleSource]
    automation: List[AutomationData]
    extracted_at: datetime
    extraction_version: str
```

### MIDITrack

Represents a MIDI track with notes:

```python
@dataclass
class MIDITrack:
    track_name: str
    track_index: int
    notes: List[MIDINote]
    instrument: Optional[str] = None
    volume: float = 1.0
    pan: float = 0.0
```

### ArrangementData

Timeline arrangement information:

```python
@dataclass
class ArrangementData:
    clips: List[ClipData]
    total_length: float
    tracks: List[str]
```

## Error Handling

The parser includes comprehensive error handling:

```python
from daw_parser import AbletonParser, DAWParseError, CorruptedFileError
from pathlib import Path

try:
    parser = AbletonParser(Path("project.als"))
    metadata = parser.parse()
except CorruptedFileError as e:
    print(f"File is corrupted: {e}")
except DAWParseError as e:
    print(f"Parse error: {e}")
except FileNotFoundError:
    print("File not found")
```

## Testing

Run the test suite:

```bash
python -m pytest daw_parser/tests/
```

Or run specific tests:

```bash
python -m unittest daw_parser.tests.test_ableton
```

## File Structure

```
daw_parser/
├── __init__.py           # Module exports
├── models.py             # Data models
├── base_parser.py        # Abstract base parser
├── ableton_parser.py    # Ableton Live parser
├── exceptions.py         # Custom exceptions
├── schema.py            # JSON schemas
├── README.md            # This file
└── tests/
    ├── __init__.py
    ├── test_ableton.py  # Ableton parser tests
    └── fixtures/        # Test .als files
```

## Limitations

### Current Limitations (Phase 1)

- Only Ableton Live (.als) files are supported
- Some complex Ableton features may not be fully extracted
- Encrypted or password-protected projects are not supported
- Very large projects may take significant time to parse

### Known Issues

- Some Ableton Live versions may have slightly different XML structures
- Plugin parameter extraction depends on how plugins store their data
- Sample paths may be relative and need resolution

## Future Enhancements

- FL Studio (.flp) parser (Phase 2)
- Logic Pro (.logicx) parser (Phase 2)
- Integration with fingerprinting pipeline (Phase 3)
- Metadata-based query filtering (Phase 3)
- Enhanced visualization in reports (Phase 3)

## Contributing

When adding support for new DAW formats:

1. Create a new parser class inheriting from `BaseDAWParser`
2. Implement all abstract methods
3. Add comprehensive tests
4. Update this README
5. Add example files to `tests/fixtures/`
