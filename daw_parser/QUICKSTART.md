# DAW Parser - Quick Start Guide

## Installation

No additional dependencies required! The DAW parser uses only Python standard library.

## Quick Example

```python
from pathlib import Path
from daw_parser import AbletonParser

# Parse an Ableton Live project
parser = AbletonParser(Path("my_project.als"))
metadata = parser.parse()

# Print summary
print(f"MIDI Tracks: {len(metadata.midi_data)}")
print(f"Total Notes: {sum(len(t.notes) for t in metadata.midi_data)}")
print(f"Tempo Changes: {len(metadata.tempo_changes)}")
```

## Command Line Usage

Process a single file:
```bash
python scripts/process_daw_files.py project.als -o data/daw_metadata
```

Process all .als files in a directory:
```bash
python scripts/process_daw_files.py /path/to/projects -o data/daw_metadata
```

## What Gets Extracted

1. **MIDI Data**: All MIDI notes with velocities, timing, and track information
2. **Arrangement**: Clips, tracks, and timeline structure
3. **Tempo/Key Changes**: All tempo and key signature changes
4. **Plugin Chains**: All devices/plugins with their parameters
5. **Sample Sources**: All audio file references
6. **Automation**: All automation data for parameters

## Output Format

Metadata is saved as JSON with this structure:

```json
{
  "project_path": "project.als",
  "daw_type": "ableton",
  "version": "11.0",
  "midi_tracks": 5,
  "total_notes": 120,
  "arrangement_clips": 15,
  "tempo_changes": 2,
  "key_changes": 0,
  "plugin_chains": 8,
  "sample_sources": 12,
  "automation_tracks": 3
}
```

## Error Handling

```python
from daw_parser import DAWParseError, CorruptedFileError

try:
    parser = AbletonParser(Path("project.als"))
    metadata = parser.parse()
except CorruptedFileError:
    print("File is corrupted")
except DAWParseError as e:
    print(f"Parse error: {e}")
```

## Testing

Run the test suite:
```bash
python -m unittest daw_parser.tests.test_ableton
```

## Next Steps

- See `README.md` for detailed documentation
- See `examples/daw_parser_example.py` for more examples
- Phase 2 will add FL Studio and Logic Pro support
