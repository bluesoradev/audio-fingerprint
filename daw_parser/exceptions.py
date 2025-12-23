"""Custom exceptions for DAW parsing."""
import logging

logger = logging.getLogger(__name__)


class DAWParseError(Exception):
    """Base exception for DAW parsing errors."""
    def __init__(self, message: str, file_path: str = None):
        self.message = message
        self.file_path = file_path
        super().__init__(self.message)
        if file_path:
            logger.error(f"DAW parse error in {file_path}: {message}")


class UnsupportedDAWError(DAWParseError):
    """Exception for unsupported DAW formats."""
    pass


class CorruptedFileError(DAWParseError):
    """Exception for corrupted or invalid DAW files."""
    pass


class MissingDataError(DAWParseError):
    """Exception for missing required data in DAW file."""
    pass
