"""JSON schema definitions for DAW metadata validation."""
from typing import Dict, Any

# JSON schema for DAW metadata
DAW_METADATA_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_path": {"type": "string"},
        "daw_type": {"type": "string", "enum": ["ableton", "flstudio", "logic"]},
        "version": {"type": "string"},
        "midi_tracks": {"type": "integer"},
        "total_notes": {"type": "integer"},
        "arrangement_clips": {"type": "integer"},
        "tempo_changes": {"type": "integer"},
        "key_changes": {"type": "integer"},
        "plugin_chains": {"type": "integer"},
        "sample_sources": {"type": "integer"},
        "automation_tracks": {"type": "integer"},
        "extracted_at": {"type": "string"},
        "extraction_version": {"type": "string"}
    },
    "required": ["project_path", "daw_type", "version"]
}
