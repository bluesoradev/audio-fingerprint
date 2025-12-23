"""Abstract base class for DAW parsers."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

from .models import DAWMetadata, DAWType
from .exceptions import DAWParseError, UnsupportedDAWError

logger = logging.getLogger(__name__)


class BaseDAWParser(ABC):
    """Abstract base class for DAW file parsers."""
    
    def __init__(self, file_path: Path):
        """
        Initialize parser.
        
        Args:
            file_path: Path to DAW project file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"DAW file not found: {file_path}")
        
        self.daw_type = self._detect_daw_type()
        logger.info(f"Initialized {self.daw_type.value} parser for {file_path}")
    
    @abstractmethod
    def _detect_daw_type(self) -> DAWType:
        """Detect DAW type from file."""
        pass
    
    @abstractmethod
    def parse(self) -> DAWMetadata:
        """
        Parse DAW file and extract metadata.
        
        Returns:
            DAWMetadata object with extracted data
            
        Raises:
            DAWParseError: If parsing fails
        """
        pass
    
    @abstractmethod
    def _extract_midi_data(self) -> list:
        """Extract MIDI data from project."""
        pass
    
    @abstractmethod
    def _extract_arrangement(self):
        """Extract arrangement timeline data."""
        pass
    
    @abstractmethod
    def _extract_tempo_changes(self) -> list:
        """Extract tempo and time signature changes."""
        pass
    
    @abstractmethod
    def _extract_key_changes(self) -> list:
        """Extract key signature changes."""
        pass
    
    @abstractmethod
    def _extract_plugin_chains(self) -> list:
        """Extract plugin/device chains."""
        pass
    
    @abstractmethod
    def _extract_sample_sources(self) -> list:
        """Extract audio sample references."""
        pass
    
    @abstractmethod
    def _extract_automation(self) -> list:
        """Extract automation data."""
        pass
    
    def validate(self) -> bool:
        """
        Validate that file can be parsed.
        
        Returns:
            True if file is valid, False otherwise
        """
        try:
            metadata = self.parse()
            return metadata is not None
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return False
