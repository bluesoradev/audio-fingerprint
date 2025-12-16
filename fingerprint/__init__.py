"""Fingerprint extraction and indexing."""
from .load_model import load_fingerprint_model
from .embed import segment_audio, extract_embeddings, normalize_embeddings
from .query_index import build_index, load_index, query_index
from .original_embeddings_cache import OriginalEmbeddingsCache
from .incremental_index import update_index_incremental

__all__ = [
    "load_fingerprint_model",
    "segment_audio",
    "extract_embeddings",
    "normalize_embeddings",
    "build_index",
    "load_index",
    "query_index",
    "OriginalEmbeddingsCache",
    "update_index_incremental",
]
