"""Repository for FAISS index operations."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.interfaces import IIndexRepository
from core.models import IndexMetadata
from fingerprint.query_index import load_index as _load_index, query_index as _query_index

logger = logging.getLogger(__name__)


class IndexRepository(IIndexRepository):
    """Repository for FAISS index operations."""
    
    def load_index(self, index_path: Path) -> tuple[Any, IndexMetadata]:
        """Load FAISS index and metadata."""
        logger.info(f"Loading index from {index_path}")
        index, metadata_dict = _load_index(index_path)
        
        # Convert metadata dict to IndexMetadata
        index_metadata = IndexMetadata(
            ids=metadata_dict.get("ids"),
            file_paths=[Path(p) for p in metadata_dict.get("file_paths", [])] if metadata_dict.get("file_paths") else None,
            embedding_dim=metadata_dict.get("embedding_dim"),
            index_type=metadata_dict.get("index_type"),
            metadata=metadata_dict.get("metadata", {})
        )
        
        return index, index_metadata
    
    def query_index(
        self,
        index: Any,
        embedding: Any,
        topk: int,
        index_metadata: Optional[IndexMetadata] = None
    ) -> List[Dict[str, Any]]:
        """Query index with embedding."""
        metadata_dict = None
        if index_metadata:
            metadata_dict = {
                "ids": index_metadata.ids,
                "file_paths": [str(p) for p in index_metadata.file_paths] if index_metadata.file_paths else None,
                "embedding_dim": index_metadata.embedding_dim,
                "index_type": index_metadata.index_type,
                **index_metadata.metadata
            }
        
        return _query_index(
            index=index,
            query_vectors=embedding,
            topk=topk,
            ids=index_metadata.ids if index_metadata else None,
            normalize=True,
            index_metadata=metadata_dict
        )
