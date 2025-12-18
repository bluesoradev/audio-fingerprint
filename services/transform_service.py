"""Service for transform-related operations."""
import logging
from pathlib import Path
from typing import Optional

from core.interfaces import ITransformService
from core.models import TransformSeverity

logger = logging.getLogger(__name__)


class TransformService(ITransformService):
    """Service for transform operations."""
    
    # Transform severity detection rules
    SEVERE_TRANSFORMS = {
        "song_a_in_song_b",
        "embedded_sample"
    }
    
    MODERATE_TRANSFORMS = {
        "overlay_vocals",
        "low_pass_filter"  # Can be severe if freq_hz=200
    }
    
    # Optimal topk values by transform type
    OPTIMAL_TOPK = {
        "low_pass_filter": 35,  # Increased for better recall
        "overlay_vocals": 15,
        "song_a_in_song_b": 20,
        "embedded_sample": 20,
    }
    
    DEFAULT_TOPK = 30
    
    def detect_severity(self, transform_type: str, file_path: Path) -> str:
        """
        Detect transform severity from type and file path.
        
        Args:
            transform_type: Transform type string
            file_path: Path to transformed file (may contain severity info)
            
        Returns:
            Severity string: "mild", "moderate", or "severe"
        """
        transform_lower = transform_type.lower() if transform_type else ""
        file_path_str = str(file_path).lower() if file_path else ""
        
        # Check for severe transforms
        if any(severe_type in transform_lower for severe_type in self.SEVERE_TRANSFORMS):
            return TransformSeverity.SEVERE.value
        
        # Check for moderate transforms with special cases
        if 'low_pass_filter' in transform_lower:
            # Check file path/description for freq_hz=200 (severe)
            if 'freq_hz_200' in file_path_str or 'bass-only' in file_path_str:
                return TransformSeverity.SEVERE.value
            return TransformSeverity.MODERATE.value
        
        if any(moderate_type in transform_lower for moderate_type in self.MODERATE_TRANSFORMS):
            return TransformSeverity.MODERATE.value
        
        # Default to mild
        return TransformSeverity.MILD.value
    
    def get_optimal_topk(self, transform_type: Optional[str], severity: Optional[str] = None) -> int:
        """
        Get optimal topk for transform type.
        
        Args:
            transform_type: Transform type string
            severity: Optional severity (if None, will be detected)
            
        Returns:
            Optimal topk value
        """
        if not transform_type:
            return self.DEFAULT_TOPK
        
        transform_lower = transform_type.lower()
        
        # Check specific transform types
        for transform_key, topk_value in self.OPTIMAL_TOPK.items():
            if transform_key in transform_lower:
                return topk_value
        
        # Adjust based on severity if provided
        if severity:
            if severity == TransformSeverity.SEVERE.value:
                return max(self.DEFAULT_TOPK, 25)
            elif severity == TransformSeverity.MODERATE.value:
                return max(self.DEFAULT_TOPK, 20)
        
        return self.DEFAULT_TOPK
