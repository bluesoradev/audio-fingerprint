"""FAISS index building and querying."""
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import numpy as np
import faiss

logger = logging.getLogger(__name__)


def build_index(
    embeddings: np.ndarray,
    ids: List[str],
    index_path: Path,
    index_config: Dict,
    save_metadata: bool = True,
    daw_metadata: Optional[Dict[str, Dict]] = None
) -> faiss.Index:
    """
    Build FAISS index from embeddings.
    
    Args:
        embeddings: Array of embeddings (N, D)
        ids: List of IDs corresponding to embeddings
        index_path: Path to save index
        index_config: Index configuration dictionary
        save_metadata: Whether to save ID mapping
        
    Returns:
        FAISS index object
    """
    n_vectors, dim = embeddings.shape
    index_type = index_config.get("index_type", "hnsw")
    metric = index_config.get("metric", "cosine")
    
    logger.info(f"Building {index_type} index with {n_vectors} vectors of dimension {dim}")
    
    # Normalize embeddings for cosine similarity
    if index_config.get("normalize", True) or metric == "cosine":
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms
        metric = faiss.METRIC_INNER_PRODUCT  # Cosine = inner product on normalized vectors
    else:
        if metric == "cosine":
            metric = faiss.METRIC_INNER_PRODUCT
        elif metric == "l2":
            metric = faiss.METRIC_L2
        elif metric == "ip":
            metric = faiss.METRIC_INNER_PRODUCT
    
    # Create index based on type
    if index_type == "flat":
        if metric == faiss.METRIC_INNER_PRODUCT:
            index = faiss.IndexFlatIP(dim)
        else:
            index = faiss.IndexFlatL2(dim)
    
    elif index_type == "hnsw":
        params = index_config.get("parameters", {})
        M = params.get("M", 32)
        ef_construction = params.get("ef_construction", 200)
        
        if metric == faiss.METRIC_INNER_PRODUCT:
            index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_INNER_PRODUCT)
        else:
            index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_L2)
        
        index.hnsw.efConstruction = ef_construction
    
    elif index_type == "ivf":
        params = index_config.get("parameters", {})
        nlist = params.get("nlist", 100)
        nprobe = params.get("nprobe", 10)
        
        quantizer = faiss.IndexFlatL2(dim) if metric == faiss.METRIC_L2 else faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist, metric)
        index.nprobe = nprobe
        
        # Train index
        logger.info("Training IVF index...")
        index.train(embeddings)
    
    else:
        raise ValueError(f"Unknown index type: {index_type}")
    
    # Add vectors to index
    logger.info("Adding vectors to index...")
    index.add(embeddings.astype(np.float32))
    
    # Save index
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    logger.info(f"Saved index to {index_path}")
    
    # Save metadata (ID mapping)
    if save_metadata:
        metadata_path = index_path.with_suffix(".json")
        metadata = {
            "ids": ids,
            "num_vectors": n_vectors,
            "dimension": dim,
            "index_type": index_type,
            "metric": metric,
            "config": index_config,
            "daw_metadata": daw_metadata or {},  # Store DAW metadata
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"Saved metadata to {metadata_path}")
        if daw_metadata:
            logger.info(f"Included DAW metadata for {len(daw_metadata)} files")
    
    return index


def load_index(index_path: Path) -> Tuple[faiss.Index, Dict]:
    """Load FAISS index and metadata."""
    index = faiss.read_index(str(index_path))
    
    metadata_path = index_path.with_suffix(".json")
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {"ids": None}
    
    logger.info(f"Loaded index from {index_path}")
    return index, metadata


def query_index(
    index: faiss.Index,
    query_vectors: np.ndarray,
    topk: int = 10,
    ids: Optional[List[str]] = None,
    normalize: bool = True,
    index_metadata: Optional[Dict] = None
) -> List[Dict]:
    """
    Query FAISS index.
    
    Args:
        index: FAISS index
        query_vectors: Query embeddings (N, D) or (D,)
        topk: Number of results to return
        ids: List of IDs for index vectors (from metadata)
        normalize: Whether to normalize query vectors
        index_metadata: Index metadata dict (may contain ef_search parameter)
        
    Returns:
        List of result dictionaries
    """
    # Handle single vector
    if query_vectors.ndim == 1:
        query_vectors = query_vectors.reshape(1, -1)
    
    # Normalize query vectors
    if normalize:
        norms = np.linalg.norm(query_vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        query_vectors = query_vectors / norms
    
    # Set ef_search for HNSW indexes (improves recall)
    if isinstance(index, faiss.IndexHNSWFlat) or isinstance(index, faiss.IndexHNSW):
        ef_search = 50  # Default
        if index_metadata:
            config = index_metadata.get("config", {})
            params = config.get("parameters", {})
            ef_search = params.get("ef_search", 50)
        # Ensure ef_search is at least topk
        ef_search = max(ef_search, topk)
        index.hnsw.efSearch = ef_search
        logger.debug(f"Set HNSW ef_search to {ef_search} for topk={topk}")
    
    # Query
    distances, indices = index.search(query_vectors.astype(np.float32), topk)
    
    # Format results
    # Determine metric type from metadata for correct similarity calculation
    # CRITICAL: For cosine similarity with normalized vectors, FAISS uses METRIC_INNER_PRODUCT
    # In this case, the "distance" returned IS the cosine similarity (higher = more similar)
    metric_type = None
    if index_metadata:
        metric_type = index_metadata.get("metric")
        # Handle both integer enum (from JSON) and string representations
        if isinstance(metric_type, str):
            if metric_type.lower() in ["inner_product", "ip", "cosine"]:
                metric_type = faiss.METRIC_INNER_PRODUCT
            elif metric_type.lower() == "l2":
                metric_type = faiss.METRIC_L2
        elif isinstance(metric_type, int):
            # JSON loads enum as integer, compare directly
            pass  # Already an integer enum
    
    # For HNSW with inner product (cosine similarity), distance IS similarity
    # For L2 distance, convert to similarity
    is_inner_product = False
    if isinstance(index, faiss.IndexFlatIP):
        is_inner_product = True
    elif isinstance(index, (faiss.IndexHNSWFlat, faiss.IndexHNSW)):
        # Check metric from metadata
        # METRIC_INNER_PRODUCT = 0, METRIC_L2 = 1
        if metric_type == faiss.METRIC_INNER_PRODUCT or metric_type == 0:
            is_inner_product = True
        elif metric_type == faiss.METRIC_L2 or metric_type == 1:
            is_inner_product = False
        else:
            # Default: assume inner product for HNSW (most common case with normalized vectors)
            # Cosine similarity with normalized vectors uses inner product metric
            # This is safe because our config uses cosine similarity with normalization
            is_inner_product = True
            logger.debug(f"Metric type not found in metadata (got {metric_type}), assuming inner product (cosine similarity) for HNSW index")
    
    results = []
    for i, (dist_row, idx_row) in enumerate(zip(distances, indices)):
        query_results = []
        for dist, idx in zip(dist_row, idx_row):
            if idx < 0:  # Invalid index
                continue
            
            # Calculate similarity correctly based on metric type
            if is_inner_product:
                # Inner product (cosine similarity for normalized vectors): distance IS similarity
                # Higher distance = higher similarity (range typically 0-1 for normalized vectors)
                similarity = float(dist)
            else:
                # L2 distance: convert to similarity (lower distance = higher similarity)
                similarity = float(1.0 / (1.0 + dist))
            
            result = {
                "rank": len(query_results) + 1,
                "index": int(idx),
                "distance": float(dist),
                "similarity": similarity,
            }
            
            if ids and idx < len(ids):
                result["id"] = ids[idx]
            
            query_results.append(result)
        
        results.append(query_results)
    
    # Return single result if single query
    if len(results) == 1:
        return results[0]
    return results
