"""Repository for file operations."""
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd

from core.interfaces import IFileRepository

logger = logging.getLogger(__name__)


class FileRepository(IFileRepository):
    """Repository for file operations."""
    
    def read_manifest(self, manifest_path: Path) -> pd.DataFrame:
        """Read manifest file (CSV)."""
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        logger.info(f"Reading manifest from {manifest_path}")
        return pd.read_csv(manifest_path)
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists."""
        return file_path.exists()
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get file metadata."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "size_bytes": stat.st_size,
            "exists": True,
            "is_file": file_path.is_file(),
        }
