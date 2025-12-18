"""Custom exceptions for the application."""
from typing import Optional


class AudioFingerprintError(Exception):
    """Base exception for audio fingerprinting errors."""
    pass


class ConfigurationError(AudioFingerprintError):
    """Configuration-related errors."""
    pass


class IndexError(AudioFingerprintError):
    """Index-related errors."""
    pass


class QueryError(AudioFingerprintError):
    """Query execution errors."""
    pass


class TransformError(AudioFingerprintError):
    """Transform-related errors."""
    pass


class FileNotFoundError(AudioFingerprintError):
    """File not found errors."""
    def __init__(self, file_path: str, message: Optional[str] = None):
        self.file_path = file_path
        self.message = message or f"File not found: {file_path}"
        super().__init__(self.message)
