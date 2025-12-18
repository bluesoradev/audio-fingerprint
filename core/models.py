"""Domain models for audio fingerprinting system."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from enum import Enum


class TransformSeverity(Enum):
    """Transform severity levels."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class TransformType(Enum):
    """Transform types."""
    OVERLAY_VOCALS = "overlay_vocals"
    LOW_PASS_FILTER = "low_pass_filter"
    ADD_NOISE = "add_noise"
    APPLY_REVERB = "apply_reverb"
    CROP_10_SECONDS = "crop_10_seconds"
    CROP_5_SECONDS = "crop_5_seconds"
    CROP_MIDDLE_SEGMENT = "crop_middle_segment"
    CROP_END_SEGMENT = "crop_end_segment"
    EMBEDDED_SAMPLE = "embedded_sample"
    SONG_A_IN_SONG_B = "song_a_in_song_b"


@dataclass
class SegmentResult:
    """Result from querying a single audio segment."""
    segment_id: str
    start: float
    end: float
    segment_idx: int
    scale_length: float
    scale_weight: float
    results: List[Dict[str, Any]]
    
    def get_top_k(self, k: int) -> List[Dict[str, Any]]:
        """Get top K results."""
        return self.results[:k] if self.results else []


@dataclass
class QueryResult:
    """Result from querying an audio file."""
    file_path: Path
    transform_type: Optional[str]
    expected_orig_id: Optional[str]
    top_candidates: List[Dict[str, Any]]
    segment_results: List[SegmentResult]
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_recall_at_k(self, k: int, expected_id: Optional[str] = None) -> float:
        """Calculate Recall@K."""
        if not expected_id:
            expected_id = self.expected_orig_id
        if not expected_id or not self.top_candidates:
            return 0.0
        
        # Check if expected ID is in top K
        for candidate in self.top_candidates[:k]:
            candidate_id = candidate.get("id", "")
            if expected_id in str(candidate_id):
                return 1.0
        return 0.0
    
    def get_mean_similarity(self, expected_id: Optional[str] = None) -> float:
        """Calculate mean similarity for correct matches."""
        if not expected_id:
            expected_id = self.expected_orig_id
        if not expected_id or not self.top_candidates:
            return 0.0
        
        similarities = []
        for candidate in self.top_candidates:
            candidate_id = candidate.get("id", "")
            if expected_id in str(candidate_id):
                similarities.append(candidate.get("similarity", 0.0))
        
        return sum(similarities) / len(similarities) if similarities else 0.0


@dataclass
class TransformConfig:
    """Configuration for audio transforms."""
    transform_type: TransformType
    severity: TransformSeverity
    parameters: Dict[str, Any]
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformConfig":
        """Create from dictionary."""
        return cls(
            transform_type=TransformType(data.get("type", "")),
            severity=TransformSeverity(data.get("severity", "mild")),
            parameters=data.get("parameters", {}),
            description=data.get("description", "")
        )


@dataclass
class QueryConfig:
    """Configuration for query execution."""
    topk: int = 30
    use_multi_scale: bool = False
    multi_scale_lengths: List[float] = field(default_factory=list)
    multi_scale_weights: List[float] = field(default_factory=list)
    overlap_ratio: Optional[float] = None
    min_similarity_threshold: float = 0.2
    use_adaptive_threshold: bool = False
    use_temporal_consistency: bool = True
    temporal_consistency_weight: float = 0.15
    top_k_fusion_ratio: float = 0.6
    
    def get_segment_lengths(self, default_length: float) -> List[float]:
        """Get segment lengths to use."""
        if self.use_multi_scale and self.multi_scale_lengths:
            return self.multi_scale_lengths
        return [default_length]
    
    def get_scale_weights(self) -> List[float]:
        """Get normalized scale weights."""
        if self.use_multi_scale and self.multi_scale_weights:
            weights = self.multi_scale_weights
            total = sum(weights)
            return [w / total for w in weights] if total > 0 else [1.0 / len(weights)] * len(weights)
        return [1.0]


@dataclass
class IndexMetadata:
    """Metadata for FAISS index."""
    ids: Optional[List[str]] = None
    file_paths: Optional[List[Path]] = None
    embedding_dim: Optional[int] = None
    index_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    """Configuration for fingerprint model."""
    model_name: str
    embedding_dim: int
    sample_rate: int
    segment_length: float
    overlap_ratio: Optional[float] = None
    device: str = "cuda"
    batch_size: int = 32
    aggregation: Dict[str, Any] = field(default_factory=dict)
    multi_scale: Dict[str, Any] = field(default_factory=dict)
    segmentation: Dict[str, Any] = field(default_factory=dict)
