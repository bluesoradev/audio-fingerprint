"""Integration utilities for DAW parser with fingerprinting system."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
import pandas as pd

from .utils import get_parser_for_file, save_metadata
from .exceptions import DAWParseError

logger = logging.getLogger(__name__)


def find_daw_file_for_audio(audio_file: Path) -> Optional[Path]:
    """
    Find associated DAW project file for an audio file.
    
    Looks for .als, .flp, .logicx files with same name or in same directory.
    
    Args:
        audio_file: Path to audio file
        
    Returns:
        Path to DAW file if found, None otherwise
    """
    audio_stem = audio_file.stem
    audio_dir = audio_file.parent
    
    # Check for DAW files with same name in same directory
    for ext in ['.als', '.flp', '.logicx', '.logic']:
        daw_file = audio_dir / f"{audio_stem}{ext}"
        if daw_file.exists():
            return daw_file
    
    # Check for DAW files in parent directory
    parent_dir = audio_dir.parent
    for ext in ['.als', '.flp', '.logicx', '.logic']:
        daw_file = parent_dir / f"{audio_stem}{ext}"
        if daw_file.exists():
            return daw_file
    
    # Check for DAW files with similar names (common variations)
    for ext in ['.als', '.flp', '.logicx', '.logic']:
        # Try variations like "song", "song_final", "song_master"
        for suffix in ['', '_final', '_master', '_mix', '_export']:
            daw_file = audio_dir / f"{audio_stem}{suffix}{ext}"
            if daw_file.exists():
                return daw_file
    
    return None


def load_daw_metadata_from_manifest(manifest_path: Path) -> Dict[str, Dict]:
    """
    Load DAW metadata from manifest CSV.
    
    Args:
        manifest_path: Path to manifest CSV
        
    Returns:
        Dictionary mapping file_id to DAW metadata dict
    """
    daw_metadata = {}
    
    try:
        if not manifest_path.exists():
            logger.warning(f"Manifest file not found: {manifest_path}")
            return daw_metadata
        
        df = pd.read_csv(manifest_path)
        
        # Check if manifest has daw_metadata_path column
        if 'daw_metadata_path' in df.columns:
            for _, row in df.iterrows():
                file_id = row.get('id')
                metadata_path = row.get('daw_metadata_path')
                
                if file_id and metadata_path and pd.notna(metadata_path):
                    metadata_file = Path(metadata_path)
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                daw_metadata[file_id] = json.load(f)
                        except Exception as e:
                            logger.warning(f"Failed to load DAW metadata for {file_id}: {e}")
        
        # Also check for daw_file column and load if metadata doesn't exist
        if 'daw_file' in df.columns:
            for _, row in df.iterrows():
                file_id = row.get('id')
                daw_file_path = row.get('daw_file')
                
                if file_id and daw_file_path and pd.notna(daw_file_path):
                    # If metadata not already loaded, try to parse DAW file
                    if file_id not in daw_metadata:
                        try:
                            daw_file = Path(daw_file_path)
                            if daw_file.exists():
                                parser = get_parser_for_file(daw_file)
                                metadata = parser.parse()
                                daw_metadata[file_id] = metadata.to_dict()
                        except Exception as e:
                            logger.warning(f"Failed to parse DAW file {daw_file_path}: {e}")
        
        logger.info(f"Loaded DAW metadata for {len(daw_metadata)} files from manifest")
        
    except Exception as e:
        logger.warning(f"Failed to load DAW metadata from manifest: {e}")
    
    return daw_metadata


def filter_by_daw_metadata(
    candidates: List[Dict[str, Any]],
    index_metadata: Any,
    filter_criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Filter query candidates based on DAW metadata.
    
    Args:
        candidates: List of candidate results
        index_metadata: Index metadata containing DAW data (can be IndexMetadata or dict)
        filter_criteria: Filter criteria (e.g., {"daw_type": "ableton", "min_notes": 10})
        
    Returns:
        Filtered candidate list
    """
    if not filter_criteria:
        return candidates
    
    # Extract DAW metadata from index_metadata
    if hasattr(index_metadata, 'metadata'):
        # IndexMetadata object
        daw_metadata = index_metadata.metadata.get("daw_metadata", {})
    elif isinstance(index_metadata, dict):
        # Dictionary
        daw_metadata = index_metadata.get("daw_metadata", {})
    else:
        logger.warning("Invalid index_metadata type for DAW filtering")
        return candidates
    
    if not daw_metadata:
        return candidates
    
    filtered = []
    
    for candidate in candidates:
        candidate_id = candidate.get("id", "")
        
        # Extract base ID (remove segment suffix)
        base_id = candidate_id.split("_seg_")[0] if "_seg_" in candidate_id else candidate_id
        
        if base_id in daw_metadata:
            metadata = daw_metadata[base_id]
            
            # Apply filters
            if "daw_type" in filter_criteria:
                if metadata.get("daw_type") != filter_criteria["daw_type"]:
                    continue
            
            if "min_notes" in filter_criteria:
                if metadata.get("total_notes", 0) < filter_criteria["min_notes"]:
                    continue
            
            if "min_tracks" in filter_criteria:
                if metadata.get("midi_tracks", 0) < filter_criteria["min_tracks"]:
                    continue
            
            if "has_automation" in filter_criteria and filter_criteria["has_automation"]:
                if metadata.get("automation_tracks", 0) == 0:
                    continue
        
        filtered.append(candidate)
    
    return filtered


def get_daw_metadata_for_file(
    file_id: str,
    index_metadata: Any
) -> Optional[Dict[str, Any]]:
    """
    Get DAW metadata for a specific file ID.
    
    Args:
        file_id: File ID to look up
        index_metadata: Index metadata containing DAW data
        
    Returns:
        DAW metadata dict or None if not found
    """
    # Extract base ID (remove segment suffix)
    base_id = file_id.split("_seg_")[0] if "_seg_" in file_id else file_id
    
    # Extract DAW metadata from index_metadata
    if hasattr(index_metadata, 'metadata'):
        daw_metadata = index_metadata.metadata.get("daw_metadata", {})
    elif isinstance(index_metadata, dict):
        daw_metadata = index_metadata.get("daw_metadata", {})
    else:
        return None
    
    return daw_metadata.get(base_id)
