"""Utility functions for DAW parser."""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .models import DAWMetadata
from .exceptions import DAWParseError

logger = logging.getLogger(__name__)


def save_metadata(metadata: DAWMetadata, output_path: Path) -> Path:
    """
    Save DAW metadata to JSON file.
    
    Args:
        metadata: DAWMetadata object to save
        output_path: Path to save JSON file
        
    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    metadata_dict = metadata.to_dict()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_dict, f, indent=2, default=str)
    
    logger.info(f"Saved metadata to {output_path}")
    return output_path


def load_metadata(json_path: Path) -> Dict[str, Any]:
    """
    Load DAW metadata from JSON file.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Dictionary with metadata
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def detect_daw_type(file_path: Path) -> Optional[str]:
    """
    Detect DAW type from file extension.
    
    Args:
        file_path: Path to DAW project file
        
    Returns:
        DAW type string or None if unknown
    """
    extension = file_path.suffix.lower()
    
    daw_types = {
        '.als': 'ableton',
        '.flp': 'flstudio',
        '.logicx': 'logic',
        '.logic': 'logic'
    }
    
    return daw_types.get(extension)


def find_daw_files(directory: Path, extensions: list = None) -> list:
    """
    Find all DAW project files in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of extensions to search for (default: ['.als', '.flp', '.logicx'])
        
    Returns:
        List of Path objects for found DAW files
    """
    if extensions is None:
        extensions = ['.als', '.flp', '.logicx', '.logic']
    
    daw_files = []
    for ext in extensions:
        daw_files.extend(directory.rglob(f"*{ext}"))
    
    return sorted(daw_files)


def get_parser_for_file(file_path: Path):
    """
    Get appropriate parser for file based on extension.
    
    Args:
        file_path: Path to DAW project file
        
    Returns:
        Parser instance
        
    Raises:
        UnsupportedDAWError: If file type is not supported
    """
    from .ableton_parser import AbletonParser
    from .flstudio_parser import FLStudioParser
    from .logic_parser import LogicParser
    from .exceptions import UnsupportedDAWError
    
    ext = file_path.suffix.lower()
    
    if ext == '.als':
        return AbletonParser(file_path)
    elif ext == '.flp':
        return FLStudioParser(file_path)
    elif ext in ['.logicx', '.logic']:
        return LogicParser(file_path)
    else:
        raise UnsupportedDAWError(
            f"Unsupported file type: {ext}",
            str(file_path)
        )


def link_daw_to_audio(daw_file: Path, audio_file: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Link DAW project file to audio file and save metadata.
    
    Args:
        daw_file: Path to DAW project file
        audio_file: Path to corresponding audio file
        output_dir: Directory to save linked metadata
        
    Returns:
        Dictionary with linking information
    """
    try:
        # Get appropriate parser
        parser = get_parser_for_file(daw_file)
        metadata = parser.parse()
        
        # Create link data
        link_data = {
            "daw_file": str(daw_file),
            "audio_file": str(audio_file),
            "daw_type": metadata.daw_type.value,
            "metadata": metadata.to_dict()
        }
        
        # Save link
        output_dir.mkdir(parents=True, exist_ok=True)
        link_file = output_dir / f"{audio_file.stem}_daw_link.json"
        
        with open(link_file, 'w', encoding='utf-8') as f:
            json.dump(link_data, f, indent=2, default=str)
        
        logger.info(f"Linked {daw_file.name} to {audio_file.name}")
        return link_data
        
    except DAWParseError as e:
        logger.error(f"Failed to link DAW file: {e}")
        return {
            "daw_file": str(daw_file),
            "audio_file": str(audio_file),
            "error": str(e)
        }
