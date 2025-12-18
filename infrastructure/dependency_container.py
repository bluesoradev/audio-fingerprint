"""Dependency injection container."""
import logging
from pathlib import Path
from typing import Optional

from repositories import IndexRepository, FileRepository, ConfigRepository
from services import QueryService, TransformService
from core.models import ModelConfig, IndexMetadata

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Dependency injection container for managing service dependencies."""
    
    def __init__(self):
        """Initialize container."""
        self._index_repository: Optional[IndexRepository] = None
        self._file_repository: Optional[FileRepository] = None
        self._config_repository: Optional[ConfigRepository] = None
        self._transform_service: Optional[TransformService] = None
        self._query_service: Optional[QueryService] = None
        
        self._index = None
        self._index_metadata: Optional[IndexMetadata] = None
        self._model_config: Optional[ModelConfig] = None
    
    def initialize_repositories(self):
        """Initialize repository instances."""
        if self._index_repository is None:
            self._index_repository = IndexRepository()
        if self._file_repository is None:
            self._file_repository = FileRepository()
        if self._config_repository is None:
            self._config_repository = ConfigRepository()
        if self._transform_service is None:
            self._transform_service = TransformService()
    
    def load_index(self, index_path: Path):
        """Load FAISS index."""
        if self._index_repository is None:
            self.initialize_repositories()
        
        logger.info(f"Loading index from {index_path}")
        self._index, self._index_metadata = self._index_repository.load_index(index_path)
    
    def load_model_config(self, config_path: Path):
        """Load model configuration."""
        if self._config_repository is None:
            self.initialize_repositories()
        
        logger.info(f"Loading model config from {config_path}")
        self._model_config = self._config_repository.load_model_config(config_path)
    
    def get_query_service(self) -> QueryService:
        """Get or create QueryService instance."""
        if self._query_service is None:
            if self._index_repository is None:
                self.initialize_repositories()
            
            if self._index is None:
                raise ValueError("Index must be loaded before creating QueryService")
            if self._model_config is None:
                raise ValueError("Model config must be loaded before creating QueryService")
            
            self._query_service = QueryService(
                index_repository=self._index_repository,
                file_repository=self._file_repository,
                config_repository=self._config_repository,
                transform_service=self._transform_service,
                index=self._index,
                index_metadata=self._index_metadata,
                model_config=self._model_config
            )
        
        return self._query_service
    
    def get_file_repository(self) -> FileRepository:
        """Get FileRepository instance."""
        if self._file_repository is None:
            self.initialize_repositories()
        return self._file_repository
    
    def get_config_repository(self) -> ConfigRepository:
        """Get ConfigRepository instance."""
        if self._config_repository is None:
            self.initialize_repositories()
        return self._config_repository
    
    def get_transform_service(self) -> TransformService:
        """Get TransformService instance."""
        if self._transform_service is None:
            self.initialize_repositories()
        return self._transform_service


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get global dependency container instance."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container
