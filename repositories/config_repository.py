"""Repository for configuration management."""
import logging
import yaml
from pathlib import Path
from typing import List, Optional

from core.interfaces import IConfigRepository
from core.models import ModelConfig, TransformConfig, QueryConfig, TransformType, TransformSeverity
from fingerprint.load_model import load_fingerprint_model as _load_fingerprint_model

logger = logging.getLogger(__name__)


class ConfigRepository(IConfigRepository):
    """Repository for configuration management."""
    
    def load_model_config(self, config_path: Path) -> ModelConfig:
        """Load model configuration."""
        logger.info(f"Loading model config from {config_path}")
        config_dict = _load_fingerprint_model(config_path)
        
        return ModelConfig(
            model_name=config_dict.get("model_name", "mert"),
            embedding_dim=config_dict.get("embedding_dim", 768),
            sample_rate=config_dict.get("sample_rate", 44100),
            segment_length=config_dict.get("segment_length", 10.0),
            overlap_ratio=config_dict.get("overlap_ratio"),
            device=config_dict.get("device", "cuda"),
            batch_size=config_dict.get("batch_size", 32),
            aggregation=config_dict.get("aggregation", {}),
            multi_scale=config_dict.get("multi_scale", {}),
            segmentation=config_dict.get("segmentation", {})
        )
    
    def load_transform_config(self, config_path: Path) -> List[TransformConfig]:
        """Load transform configuration."""
        logger.info(f"Loading transform config from {config_path}")
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        transforms = []
        transforms_section = config_dict.get("transforms", {})
        
        for transform_name, transform_data in transforms_section.items():
            if not transform_data.get("enabled", False):
                continue
            
            for param_set in transform_data.get("parameters", []):
                severity_str = param_set.get("severity", "mild")
                try:
                    severity = TransformSeverity(severity_str)
                except ValueError:
                    severity = TransformSeverity.MILD
                
                try:
                    transform_type = TransformType(transform_name)
                except ValueError:
                    continue
                
                transforms.append(TransformConfig(
                    transform_type=transform_type,
                    severity=severity,
                    parameters=param_set,
                    description=param_set.get("description", "")
                ))
        
        return transforms
    
    def get_query_config(
        self,
        model_config: ModelConfig,
        transform_type: Optional[str] = None
    ) -> QueryConfig:
        """Get query configuration for transform type."""
        multi_scale = model_config.multi_scale
        
        # Determine if multi-scale should be used
        use_multi_scale = multi_scale.get("enabled", False)
        multi_scale_lengths = multi_scale.get("segment_lengths", [])
        multi_scale_weights = multi_scale.get("weights", [])
        
        # Get aggregation config
        aggregation = model_config.aggregation
        
        return QueryConfig(
            topk=30,  # Default, can be overridden
            use_multi_scale=use_multi_scale,
            multi_scale_lengths=multi_scale_lengths,
            multi_scale_weights=multi_scale_weights,
            overlap_ratio=model_config.overlap_ratio or model_config.segmentation.get("overlap_ratio"),
            min_similarity_threshold=aggregation.get("min_similarity_threshold", 0.2),
            use_adaptive_threshold=aggregation.get("use_adaptive_threshold", False),
            use_temporal_consistency=aggregation.get("use_temporal_consistency", True),
            temporal_consistency_weight=aggregation.get("temporal_consistency_weight", 0.15),
            top_k_fusion_ratio=aggregation.get("top_k_fusion_ratio", 0.6)
        )
