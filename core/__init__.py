"""Core domain models and interfaces."""
from .models import (
    QueryResult,
    SegmentResult,
    TransformConfig,
    QueryConfig,
    IndexMetadata,
    ModelConfig
)
from .interfaces import (
    IQueryService,
    IIndexRepository,
    IFileRepository,
    IConfigRepository,
    ITransformService,
    IReportService
)

__all__ = [
    "QueryResult",
    "SegmentResult",
    "TransformConfig",
    "QueryConfig",
    "IndexMetadata",
    "ModelConfig",
    "IQueryService",
    "IIndexRepository",
    "IFileRepository",
    "IConfigRepository",
    "ITransformService",
    "IReportService",
]
