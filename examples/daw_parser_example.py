"""Example usage of DAW parser."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from daw_parser import AbletonParser, DAWParseError, CorruptedFileError
from daw_parser.utils import save_metadata, detect_daw_type, find_daw_files
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_parse_single_file():
    """Example: Parse a single Ableton Live project file."""
    print("\n=== Example 1: Parse Single File ===")
    
    # Replace with path to your .als file
    als_file = Path("path/to/your/project.als")
    
    if not als_file.exists():
        print(f"File not found: {als_file}")
        print("Please update the path to point to a valid .als file")
        return
    
    try:
        # Create parser
        parser = AbletonParser(als_file)
        
        # Parse the file
        metadata = parser.parse()
        
        # Print summary
        print(f"\nProject: {metadata.project_path.name}")
        print(f"DAW Type: {metadata.daw_type.value}")
        print(f"Version: {metadata.version}")
        print(f"\nMIDI Tracks: {len(metadata.midi_data)}")
        print(f"Total Notes: {sum(len(track.notes) for track in metadata.midi_data)}")
        print(f"Arrangement Clips: {len(metadata.arrangement.clips)}")
        print(f"Tempo Changes: {len(metadata.tempo_changes)}")
        print(f"Plugin Chains: {len(metadata.plugin_chains)}")
        print(f"Sample Sources: {len(metadata.sample_sources)}")
        print(f"Automation Tracks: {len(metadata.automation)}")
        
        # Access specific data
        if metadata.midi_data:
            first_track = metadata.midi_data[0]
            print(f"\nFirst MIDI Track: {first_track.track_name}")
            print(f"  Notes: {len(first_track.notes)}")
            if first_track.notes:
                first_note = first_track.notes[0]
                print(f"  First Note: MIDI {first_note.note}, "
                      f"Velocity {first_note.velocity}, "
                      f"Time {first_note.start_time}")
        
        if metadata.tempo_changes:
            first_tempo = metadata.tempo_changes[0]
            print(f"\nFirst Tempo: {first_tempo.tempo} BPM at {first_tempo.time}s")
        
        # Save metadata to JSON
        output_file = Path("data/daw_metadata") / f"{als_file.stem}_metadata.json"
        save_metadata(metadata, output_file)
        print(f"\nMetadata saved to: {output_file}")
        
    except CorruptedFileError as e:
        print(f"Error: File is corrupted - {e}")
    except DAWParseError as e:
        print(f"Error: Failed to parse file - {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def example_detect_daw_type():
    """Example: Detect DAW type from file."""
    print("\n=== Example 2: Detect DAW Type ===")
    
    test_files = [
        Path("project.als"),
        Path("project.flp"),
        Path("project.logicx"),
        Path("project.txt")
    ]
    
    for file_path in test_files:
        daw_type = detect_daw_type(file_path)
        if daw_type:
            print(f"{file_path.name}: {daw_type}")
        else:
            print(f"{file_path.name}: Unknown/Unsupported")


def example_find_daw_files():
    """Example: Find all DAW files in a directory."""
    print("\n=== Example 3: Find DAW Files ===")
    
    # Replace with your projects directory
    projects_dir = Path("path/to/projects")
    
    if not projects_dir.exists():
        print(f"Directory not found: {projects_dir}")
        print("Please update the path to point to a valid directory")
        return
    
    daw_files = find_daw_files(projects_dir)
    
    print(f"\nFound {len(daw_files)} DAW files:")
    for file_path in daw_files:
        daw_type = detect_daw_type(file_path)
        print(f"  {file_path.name} ({daw_type})")


def example_validate_file():
    """Example: Validate a DAW file without full parsing."""
    print("\n=== Example 4: Validate File ===")
    
    als_file = Path("path/to/your/project.als")
    
    if not als_file.exists():
        print(f"File not found: {als_file}")
        return
    
    try:
        parser = AbletonParser(als_file)
        is_valid = parser.validate()
        
        if is_valid:
            print(f"✓ {als_file.name} is valid and can be parsed")
        else:
            print(f"✗ {als_file.name} appears to be invalid or corrupted")
    except Exception as e:
        print(f"Error validating file: {e}")


if __name__ == "__main__":
    print("DAW Parser Examples")
    print("=" * 50)
    
    # Run examples
    example_detect_daw_type()
    example_find_daw_files()
    example_validate_file()
    example_parse_single_file()
    
    print("\n" + "=" * 50)
    print("Examples complete!")
    print("\nNote: Update file paths in the examples to point to actual DAW files")
