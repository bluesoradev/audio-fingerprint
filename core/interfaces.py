"""Interfaces for dependency injection and abstraction."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import (
    QueryResult,
    QueryConfig,
    TransformConfig,
    IndexMetadata,
    ModelConfig
)


class IIndexRepository(ABC):
    """Interface for index operations."""
    
    @abstractmethod
    def load_index(self, index_path: Path) -> tuple[Any, IndexMetadata]:
        """Load FAISS index and metadata."""
        pass
    
    @abstractmethod
    def query_index(
        self,
        index: Any,
        embedding: Any,
        topk: int,
        index_metadata: Optional[IndexMetadata] = None
    ) -> List[Dict[str, Any]]:
        """Query index with embedding."""
        pass


class IFileRepository(ABC):
    """Interface for file operations."""
    
    @abstractmethod
    def read_manifest(self, manifest_path: Path) -> Any:
        """Read manifest file (CSV)."""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get file metadata."""
        pass


class IConfigRepository(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def load_model_config(self, config_path: Path) -> ModelConfig:
        """Load model configuration."""
        pass
    
    @abstractmethod
    def load_transform_config(self, config_path: Path) -> List[TransformConfig]:
        """Load transform configuration."""
        pass
    
    @abstractmethod
    def get_query_config(self, model_config: ModelConfig, transform_type: Optional[str] = None) -> QueryConfig:
        """Get query configuration for transform type."""
        pass


class IQueryService(ABC):
    """Interface for query execution."""
    
    @abstractmethod
    def query_file(
        self,
        file_path: Path,
        transform_type: Optional[str] = None,
        expected_orig_id: Optional[str] = None,
        query_config: Optional[QueryConfig] = None
    ) -> QueryResult:
        """Execute query on audio file."""
        pass
    
    @abstractmethod
    def query_batch(
        self,
        file_paths: List[Path],
        transform_types: Optional[List[Optional[str]]] = None,
        expected_orig_ids: Optional[List[Optional[str]]] = None
    ) -> List[QueryResult]:
        """Execute batch queries."""
        pass


class ITransformService(ABC):
    """Interface for transform operations."""
    
    @abstractmethod
    def detect_severity(self, transform_type: str, file_path: Path) -> str:
        """Detect transform severity from type and file path."""
        pass
    
    @abstractmethod
    def get_optimal_topk(self, transform_type: Optional[str], severity: Optional[str]) -> int:
        """Get optimal topk for transform type."""
        pass


class IReportService(ABC):
    """Interface for report generation."""
    
    @abstractmethod
    def generate_report(
        self,
        results: List[QueryResult],
        output_path: Path,
        phase: str = "phase1"
    ) -> Path:
        """Generate HTML report."""
        pass
    
    @abstractmethod
    def calculate_metrics(self, results: List[QueryResult]) -> Dict[str, Any]:
        """Calculate aggregate metrics."""
        pass
