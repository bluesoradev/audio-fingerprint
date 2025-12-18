"""API route handlers using dependency injection."""
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import logging
from typing import Optional

from infrastructure.dependency_container import get_container
from core.models import QueryResult

logger = logging.getLogger(__name__)

router = APIRouter()


def get_query_service():
    """Dependency to get QueryService."""
    container = get_container()
    return container.get_query_service()


def get_file_repository():
    """Dependency to get FileRepository."""
    container = get_container()
    return container.get_file_repository()


@router.post("/api/query")
async def query_audio_file(
    file_path: str = Form(...),
    transform_type: Optional[str] = Form(None),
    expected_orig_id: Optional[str] = Form(None),
    query_service=Depends(get_query_service)
):
    """
    Query an audio file using the fingerprint system.
    
    Args:
        file_path: Path to audio file to query
        transform_type: Optional transform type
        expected_orig_id: Optional expected original ID
        
    Returns:
        Query results with top candidates
    """
    try:
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        result = query_service.query_file(
            file_path=file_path_obj,
            transform_type=transform_type,
            expected_orig_id=expected_orig_id
        )
        
        # Convert QueryResult to dict for JSON response
        response = {
            "file_path": str(result.file_path),
            "transform_type": result.transform_type,
            "expected_orig_id": result.expected_orig_id,
            "top_candidates": result.top_candidates[:10],  # Top 10
            "latency_ms": result.latency_ms,
            "metadata": result.metadata,
            "recall_at_5": result.get_recall_at_k(5),
            "recall_at_10": result.get_recall_at_k(10),
            "mean_similarity": result.get_mean_similarity()
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"Error querying file {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/query/batch")
async def query_batch(
    file_paths: list[str] = Form(...),
    transform_types: Optional[list[Optional[str]]] = Form(None),
    expected_orig_ids: Optional[list[Optional[str]]] = Form(None),
    query_service=Depends(get_query_service)
):
    """
    Query multiple audio files in batch.
    
    Args:
        file_paths: List of audio file paths
        transform_types: Optional list of transform types
        expected_orig_ids: Optional list of expected original IDs
        
    Returns:
        List of query results
    """
    try:
        file_path_objs = [Path(fp) for fp in file_paths]
        
        # Validate files exist
        for fp in file_path_objs:
            if not fp.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {fp}")
        
        results = query_service.query_batch(
            file_paths=file_path_objs,
            transform_types=transform_types,
            expected_orig_ids=expected_orig_ids
        )
        
        # Convert to dicts
        response = []
        for result in results:
            response.append({
                "file_path": str(result.file_path),
                "transform_type": result.transform_type,
                "expected_orig_id": result.expected_orig_id,
                "top_candidates": result.top_candidates[:10],
                "latency_ms": result.latency_ms,
                "metadata": result.metadata,
                "recall_at_5": result.get_recall_at_k(5),
                "recall_at_10": result.get_recall_at_k(10),
                "mean_similarity": result.get_mean_similarity()
            })
        
        return JSONResponse({"results": response})
        
    except Exception as e:
        logger.error(f"Error in batch query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/query/status")
async def get_query_status():
    """Get query service status."""
    try:
        container = get_container()
        status = {
            "index_loaded": container._index is not None,
            "model_config_loaded": container._model_config is not None,
            "index_metadata": {
                "embedding_dim": container._index_metadata.embedding_dim if container._index_metadata else None,
                "index_type": container._index_metadata.index_type if container._index_metadata else None,
            } if container._index_metadata else None,
            "model_config": {
                "model_name": container._model_config.model_name if container._model_config else None,
                "embedding_dim": container._model_config.embedding_dim if container._model_config else None,
                "sample_rate": container._model_config.sample_rate if container._model_config else None,
            } if container._model_config else None
        }
        return JSONResponse(status)
    except Exception as e:
        logger.error(f"Error getting query status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
