"""Main query service for audio fingerprinting."""
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.interfaces import (
    IQueryService,
    IIndexRepository,
    IFileRepository,
    IConfigRepository,
    ITransformService
)
from core.models import (
    QueryResult,
    QueryConfig,
    SegmentResult,
    ModelConfig,
    IndexMetadata
)
from fingerprint.embed import segment_audio, extract_embeddings, normalize_embeddings
from services.aggregation_service import AggregationService
from services.recall_estimator import RecallEstimator

logger = logging.getLogger(__name__)


class QueryService(IQueryService):
    """Service for executing audio fingerprint queries."""
    
    def __init__(
        self,
        index_repository: IIndexRepository,
        file_repository: IFileRepository,
        config_repository: IConfigRepository,
        transform_service: ITransformService,
        index: Any = None,
        index_metadata: Optional[IndexMetadata] = None,
        model_config: Optional[ModelConfig] = None
    ):
        """
        Initialize query service.
        
        Args:
            index_repository: Repository for index operations
            file_repository: Repository for file operations
            config_repository: Repository for configuration
            transform_service: Service for transform operations
            index: Pre-loaded FAISS index (optional)
            index_metadata: Pre-loaded index metadata (optional)
            model_config: Pre-loaded model config (optional)
        """
        self.index_repository = index_repository
        self.file_repository = file_repository
        self.config_repository = config_repository
        self.transform_service = transform_service
        self.aggregation_service = AggregationService()
        self.recall_estimator = RecallEstimator()
        
        self._index = index
        self._index_metadata = index_metadata
        self._model_config = model_config
    
    def query_file(
        self,
        file_path: Path,
        transform_type: Optional[str] = None,
        expected_orig_id: Optional[str] = None,
        query_config: Optional[QueryConfig] = None,
        daw_filter: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Execute query on audio file.
        
        Args:
            file_path: Path to audio file to query
            transform_type: Optional transform type
            expected_orig_id: Optional expected original ID
            query_config: Optional query configuration (uses default if None)
            
        Returns:
            QueryResult with top candidates and metadata
        """
        start_time = time.time()
        
        # Ensure file exists
        if not self.file_repository.file_exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Get model config if not already loaded
        if not self._model_config:
            raise ValueError("Model config must be provided or loaded")
        
        model_config = self._model_config
        
        # Get query config
        if not query_config:
            query_config = self.config_repository.get_query_config(model_config, transform_type)
        
        # Detect transform severity
        severity = self.transform_service.detect_severity(transform_type, file_path) if transform_type else "mild"
        
        # Get optimal topk for transform type
        optimal_topk = self.transform_service.get_optimal_topk(transform_type, severity)
        query_config.topk = max(query_config.topk, optimal_topk)
        
        # Determine segment lengths and weights
        segment_lengths = query_config.get_segment_lengths(model_config.segment_length)
        scale_weights = query_config.get_scale_weights()
        
        # Normalize weights
        total_weight = sum(scale_weights)
        if total_weight > 0:
            scale_weights = [w / total_weight for w in scale_weights]
        
        # STAGE 1: Process first scale (fast path)
        all_segment_results = []
        first_scale_len = segment_lengths[0]
        first_scale_weight = scale_weights[0]
        
        segments = segment_audio(
            file_path,
            segment_length=first_scale_len,
            sample_rate=model_config.sample_rate,
            overlap_ratio=query_config.overlap_ratio
        )
        
        embeddings = extract_embeddings(segments, model_config.__dict__, save_embeddings=False)
        embeddings = normalize_embeddings(embeddings, method="l2")
        
        # Query first scale
        first_scale_results = self._query_segments(
            segments,
            embeddings,
            query_config.topk,
            first_scale_len,
            first_scale_weight
        )
        all_segment_results.extend(first_scale_results)
        
        # Estimate Recall@5 from first scale
        estimated_recall_5 = 0.0
        if expected_orig_id and first_scale_results:
            estimated_recall_5 = self.recall_estimator.estimate_recall_at_k(
                first_scale_results,
                expected_orig_id,
                k=5
            )
        
        # Determine requirements based on severity
        requirement_recall_5 = self._get_requirement_recall_5(severity)
        
        # ADAPTIVE DECISION: Add scales if needed
        needs_multi_scale = self.recall_estimator.should_activate_multi_scale(
            estimated_recall_5,
            severity,
            requirement_recall_5
        )
        
        # STAGE 2: Add additional scales if needed
        if needs_multi_scale and len(segment_lengths) > 1:
            logger.debug(f"Activating multi-scale for {transform_type} (estimated Recall@5: {estimated_recall_5:.3f})")
            
            # Process additional scales
            expanded_topk = query_config.topk * 2 if severity == "severe" else query_config.topk
            
            # Cap topk for latency
            if transform_type and 'low_pass_filter' in transform_type.lower():
                expanded_topk = min(expanded_topk, 50)
            else:
                expanded_topk = min(expanded_topk, 30)
            
            for scale_len, scale_weight in zip(segment_lengths[1:], scale_weights[1:]):
                segments = segment_audio(
                    file_path,
                    segment_length=scale_len,
                    sample_rate=model_config.sample_rate,
                    overlap_ratio=query_config.overlap_ratio
                )
                
                embeddings = extract_embeddings(segments, model_config.__dict__, save_embeddings=False)
                embeddings = normalize_embeddings(embeddings, method="l2")
                
                scale_results = self._query_segments(
                    segments,
                    embeddings,
                    expanded_topk,
                    scale_len,
                    scale_weight
                )
                all_segment_results.extend(scale_results)
        else:
            logger.debug(f"Single-scale sufficient for {transform_type} (estimated Recall@5: {estimated_recall_5:.3f})")
        
        # Adjust query config based on severity
        adjusted_config = self._adjust_config_for_severity(query_config, severity, transform_type)
        
        # Aggregate segment results
        top_candidates = self.aggregation_service.aggregate_segment_results(
            all_segment_results,
            adjusted_config,
            expected_orig_id
        )
        
        # Apply DAW metadata filtering if provided
        if daw_filter and self._index_metadata:
            try:
                from daw_parser.integration import filter_by_daw_metadata
                top_candidates = filter_by_daw_metadata(
                    top_candidates,
                    self._index_metadata,
                    daw_filter
                )
                logger.debug(f"Applied DAW filter: {len(top_candidates)} candidates remaining")
            except ImportError:
                logger.debug("DAW parser not available, skipping DAW filtering")
            except Exception as e:
                logger.warning(f"Error applying DAW filter: {e}")
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        return QueryResult(
            file_path=file_path,
            transform_type=transform_type,
            expected_orig_id=expected_orig_id,
            top_candidates=top_candidates,
            segment_results=all_segment_results,
            latency_ms=latency_ms,
            metadata={
                "severity": severity,
                "estimated_recall_5": estimated_recall_5,
                "scales_used": len(set(s.scale_length for s in all_segment_results)),
                "total_segments": len(all_segment_results),
                "daw_filter_applied": daw_filter is not None
            }
        )
    
    def query_batch(
        self,
        file_paths: List[Path],
        transform_types: Optional[List[Optional[str]]] = None,
        expected_orig_ids: Optional[List[Optional[str]]] = None
    ) -> List[QueryResult]:
        """
        Execute batch queries.
        
        Args:
            file_paths: List of audio file paths
            transform_types: Optional list of transform types (one per file)
            expected_orig_ids: Optional list of expected original IDs (one per file)
            
        Returns:
            List of QueryResults
        """
        if transform_types is None:
            transform_types = [None] * len(file_paths)
        if expected_orig_ids is None:
            expected_orig_ids = [None] * len(file_paths)
        
        results = []
        for file_path, transform_type, expected_id in zip(file_paths, transform_types, expected_orig_ids):
            try:
                result = self.query_file(file_path, transform_type, expected_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error querying {file_path}: {e}")
                # Create error result
                results.append(QueryResult(
                    file_path=file_path,
                    transform_type=transform_type,
                    expected_orig_id=expected_id,
                    top_candidates=[],
                    segment_results=[],
                    latency_ms=0.0,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def _query_segments(
        self,
        segments: List[Dict],
        embeddings: Any,
        topk: int,
        scale_length: float,
        scale_weight: float
    ) -> List[SegmentResult]:
        """Query segments and return SegmentResults."""
        if not self._index:
            raise ValueError("Index must be provided")
        
        segment_results = []
        for seg, emb in zip(segments, embeddings):
            results = self.index_repository.query_index(
                self._index,
                emb,
                topk,
                self._index_metadata
            )
            
            segment_results.append(SegmentResult(
                segment_id=seg["segment_id"],
                start=seg["start"],
                end=seg["end"],
                segment_idx=len(segment_results),
                scale_length=scale_length,
                scale_weight=scale_weight,
                results=results
            ))
        
        return segment_results
    
    def _get_requirement_recall_5(self, severity: str) -> float:
        """Get required Recall@5 for severity level."""
        requirements = {
            "severe": 0.70,
            "moderate": 0.85,
            "mild": 0.90
        }
        return requirements.get(severity, 0.90)
    
    def _adjust_config_for_severity(
        self,
        config: QueryConfig,
        severity: str,
        transform_type: Optional[str]
    ) -> QueryConfig:
        """Adjust query config based on severity."""
        # Create a copy to avoid mutating original
        adjusted = QueryConfig(
            topk=config.topk,
            use_multi_scale=config.use_multi_scale,
            multi_scale_lengths=config.multi_scale_lengths,
            multi_scale_weights=config.multi_scale_weights,
            overlap_ratio=config.overlap_ratio,
            min_similarity_threshold=config.min_similarity_threshold,
            use_adaptive_threshold=config.use_adaptive_threshold,
            use_temporal_consistency=config.use_temporal_consistency,
            temporal_consistency_weight=config.temporal_consistency_weight,
            top_k_fusion_ratio=config.top_k_fusion_ratio
        )
        
        # Adjust thresholds based on severity
        if severity == "moderate":
            adjusted.min_similarity_threshold = max(0.22, adjusted.min_similarity_threshold)
            adjusted.top_k_fusion_ratio = min(1.0, adjusted.top_k_fusion_ratio + 0.15)
            adjusted.temporal_consistency_weight = min(0.25, adjusted.temporal_consistency_weight + 0.05)
        elif severity == "severe":
            adjusted.min_similarity_threshold = max(0.18, adjusted.min_similarity_threshold)
            adjusted.top_k_fusion_ratio = min(1.0, adjusted.top_k_fusion_ratio + 0.25)
            adjusted.temporal_consistency_weight = min(0.30, adjusted.temporal_consistency_weight + 0.08)
        
        return adjusted
