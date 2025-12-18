"""Infrastructure layer for dependency injection and setup."""
from .dependency_container import DependencyContainer, get_container

__all__ = [
    "DependencyContainer",
    "get_container",
]
