"""API route handlers using dependency injection."""
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import logging
import tempfile
import shutil
from typing import Optional, List, Dict, Any

from infrastructure.dependency_container import get_container
from core.models import QueryResult, QueryConfig

logger = logging.getLogger(__name__)

router = APIRouter()


def extract_track_uuid_from_fingerprint_id(fingerprint_id: str) -> str:
    """
    Extract track UUID from fingerprint ID.
    
    Current implementation: Assumes fingerprint_id format is "{track_uuid}_seg_{number}"
    This can be updated when we get actual mapping details from Ian/Sam.
    
    Args:
        fingerprint_id: Fingerprint ID from query results (e.g., "track_123_seg_0000")
        
    Returns:
        Track UUID (e.g., "track_123")
    """
    if "_seg_" in fingerprint_id:
        return fingerprint_id.split("_seg_")[0]
    return fingerprint_id


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


@router.post("/api/fingerprint/match")
async def match_fingerprint(
    file: UploadFile = File(...),
    min_score: Optional[float] = Form(0.5),
    max_matches: Optional[int] = Form(10),
    query_service=Depends(get_query_service)
):
    """
    Match an uploaded audio file against the fingerprint index.
    Returns matches with track UUIDs and match scores for beatlibrary.io integration.
    
    This endpoint is designed for Supabase edge function integration:
    - Accepts file uploads (multipart/form-data)
    - Returns matches in format: {"matches": [{"track_uuid": "...", "match_score": 0.95}]}
    - Track UUIDs are extracted from fingerprint IDs (can be updated with actual mapping)
    
    Args:
        file: Audio file to match (supports common audio formats: mp3, wav, m4a, ogg, etc.)
        min_score: Minimum match score threshold (0.0-1.0, default: 0.5)
        max_matches: Maximum number of matches to return (default: 10)
        
    Returns:
        JSON response with matches:
        {
            "matches": [
                {"track_uuid": "uuid-from-tracks.id", "match_score": 0.95},
                ...
            ],
            "total_matches": 5,
            "query_time_ms": 123.45
        }
    """
    temp_file_path = None
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma'}
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Validate parameters
        if min_score is not None and (min_score < 0.0 or min_score > 1.0):
            raise HTTPException(status_code=400, detail="min_score must be between 0.0 and 1.0")
        
        if max_matches is not None and max_matches < 1:
            raise HTTPException(status_code=400, detail="max_matches must be at least 1")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = Path(temp_file.name)
        
        logger.info(f"Processing fingerprint match for uploaded file: {file.filename}")
        
        # Create production-optimized query configuration
        # This matches the settings that achieved 97% accuracy in testing
        # Key optimizations:
        # - Higher topk (30-50) for better recall
        # - Multi-scale enabled if configured
        # - Lower similarity threshold for better coverage
        # - Temporal consistency enabled
        container = get_container()
        model_config = container._model_config
        
        if model_config:
            # Get aggregation config from model config
            aggregation = model_config.aggregation if hasattr(model_config, 'aggregation') else {}
            multi_scale = model_config.multi_scale if hasattr(model_config, 'multi_scale') else {}
            segmentation = model_config.segmentation if hasattr(model_config, 'segmentation') else {}
            
            # Production-optimized query config
            # Use higher topk for better recall (30-50 instead of default 10-20)
            production_topk = 40  # Higher topk for production matching
            
            # Enable multi-scale if configured (improves accuracy significantly)
            use_multi_scale = multi_scale.get("enabled", False)
            multi_scale_lengths = multi_scale.get("segment_lengths", [])
            multi_scale_weights = multi_scale.get("weights", [])
            
            # Get overlap ratio from segmentation config
            overlap_ratio = (
                model_config.overlap_ratio or 
                segmentation.get("overlap_ratio") or 
                0.1  # Default 10% overlap
            )
            
            # Use optimized aggregation settings from config
            query_config = QueryConfig(
                topk=production_topk,  # Higher topk for better recall
                use_multi_scale=use_multi_scale,  # Enable multi-scale if available
                multi_scale_lengths=multi_scale_lengths,
                multi_scale_weights=multi_scale_weights,
                overlap_ratio=overlap_ratio,
                min_similarity_threshold=aggregation.get("min_similarity_threshold", 0.08),  # Lower threshold for better recall
                use_adaptive_threshold=aggregation.get("use_adaptive_threshold", False),
                use_temporal_consistency=aggregation.get("use_temporal_consistency", True),  # Enable temporal consistency
                temporal_consistency_weight=aggregation.get("temporal_consistency_weight", 0.15),
                top_k_fusion_ratio=aggregation.get("top_k_fusion_ratio", 0.75)  # Use top 75% of segments
            )
            
            logger.info(f"Using production-optimized query config: topk={production_topk}, multi_scale={use_multi_scale}, overlap={overlap_ratio}, min_threshold={aggregation.get('min_similarity_threshold', 0.08)}")
        else:
            # Fallback: use default config if model config not available
            query_config = None
            logger.warning("Model config not available, using default query config")
        
        # Query the fingerprint index with optimized configuration
        # Note: query_service.query_file may override topk based on transform_type
        # For production (transform_type=None), it uses "mild" severity which has default topk=20
        # Our production_topk=40 should be higher, so it should be preserved
        logger.info(f"Querying fingerprint index for {file.filename} with topk={query_config.topk if query_config else 'default'}")
        result = query_service.query_file(
            file_path=temp_file_path,
            transform_type=None,  # No transform for production matching
            expected_orig_id=None,
            query_config=query_config  # Use production-optimized config
        )
        
        # Log query results for debugging
        if result.top_candidates:
            top_similarity = result.top_candidates[0].get('similarity', 0.0)
            logger.info(f"Query completed: found {len(result.top_candidates)} candidates, top similarity={top_similarity:.4f}, top_id={result.top_candidates[0].get('id', 'N/A')}")
        else:
            logger.warning(f"Query completed but found 0 candidates for {file.filename}")
        
        # Extract matches and format for beatlibrary.io
        matches: List[Dict[str, Any]] = []
        
        # Use both similarity and score fields for better matching
        # similarity = max_similarity (best segment match)
        # score = aggregated total_score (weighted across all segments)
        for candidate in result.top_candidates:
            # Try similarity first (max_similarity), fallback to score if available
            similarity = candidate.get("similarity", 0.0)
            score = candidate.get("score", 0.0)
            
            # Use the higher of similarity or normalized score for filtering
            # Score is weighted and can be > 1.0, so normalize it for comparison
            # For production, we use similarity (max_similarity) as it's more reliable
            match_score = similarity
            
            # Filter by minimum score
            if match_score < min_score:
                continue
            
            # Extract track UUID from fingerprint ID
            fingerprint_id = candidate.get("id", "")
            if not fingerprint_id:
                continue
            
            track_uuid = extract_track_uuid_from_fingerprint_id(fingerprint_id)
            
            matches.append({
                "track_uuid": track_uuid,
                "match_score": round(match_score, 4)  # Round to 4 decimal places
            })
            
            # Limit to max_matches
            if len(matches) >= max_matches:
                break
        
        # Format response
        response = {
            "matches": matches,
            "total_matches": len(matches),
            "query_time_ms": round(result.latency_ms, 2)
        }
        
        logger.info(f"Found {len(matches)} matches for {file.filename}")
        return JSONResponse(response)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error matching fingerprint for {file.filename if file else 'unknown'}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
