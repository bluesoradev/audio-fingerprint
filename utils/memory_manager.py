"""Memory management utilities for efficient resource usage."""
import logging
import gc
from typing import Optional, List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    HAS_TORCH = True
except (ImportError, OSError) as e:
    HAS_TORCH = False
    logger.warning(f"PyTorch not available (error: {type(e).__name__}: {e}), GPU memory management disabled")


class MemoryManager:
    """Utilities for memory management and optimization."""
    
    @staticmethod
    def get_gpu_memory_info() -> Optional[Dict[str, float]]:
        """
        Get current GPU memory usage information.
        
        Returns:
            Dictionary with memory info in GB, or None if GPU unavailable
        """
        if not HAS_TORCH or not torch.cuda.is_available():
            return None
        
        try:
            device = torch.device("cuda")
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            allocated_memory = torch.cuda.memory_allocated(0) / 1e9
            reserved_memory = torch.cuda.memory_reserved(0) / 1e9
            free_memory = total_memory - reserved_memory
            
            return {
                "total_gb": total_memory,
                "allocated_gb": allocated_memory,
                "reserved_gb": reserved_memory,
                "free_gb": free_memory,
                "utilization_percent": (reserved_memory / total_memory) * 100 if total_memory > 0 else 0
            }
        except Exception as e:
            logger.warning(f"Failed to get GPU memory info: {e}")
            return None
    
    @staticmethod
    def clear_gpu_cache():
        """Clear GPU cache to free memory."""
        if HAS_TORCH and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                logger.debug("Cleared GPU cache")
            except Exception as e:
                logger.warning(f"Failed to clear GPU cache: {e}")
    
    @staticmethod
    def clear_python_cache():
        """Clear Python garbage collection cache."""
        collected = gc.collect()
        logger.debug(f"Garbage collection: freed {collected} objects")
    
    @staticmethod
    def optimize_batch_size(
        current_batch_size: int,
        target_memory_usage: float = 0.7,
        embedding_dim: int = 512
    ) -> int:
        """
        Optimize batch size based on available GPU memory.
        
        Args:
            current_batch_size: Current batch size
            target_memory_usage: Target memory usage ratio (0.0-1.0)
            embedding_dim: Embedding dimension
            
        Returns:
            Optimized batch size
        """
        memory_info = MemoryManager.get_gpu_memory_info()
        if not memory_info:
            return current_batch_size
        
        free_memory_gb = memory_info["free_gb"]
        target_memory_gb = free_memory_gb * target_memory_usage
        
        # Estimate: each embedding ~2KB (FP32), batch overhead ~50MB
        memory_per_sample_gb = (embedding_dim * 4) / 1e9  # FP32 = 4 bytes
        batch_overhead_gb = 0.05  # 50MB overhead
        
        # Calculate optimal batch size
        optimal_batch = int((target_memory_gb - batch_overhead_gb) / memory_per_sample_gb)
        
        # Clamp to reasonable bounds
        optimal_batch = max(16, min(optimal_batch, 256))
        
        if optimal_batch != current_batch_size:
            logger.info(
                f"Optimized batch size: {current_batch_size} -> {optimal_batch} "
                f"(free memory: {free_memory_gb:.2f}GB, target: {target_memory_gb:.2f}GB)"
            )
        
        return optimal_batch
    
    @staticmethod
    def monitor_memory_usage(
        operation_name: str,
        before_callback: Optional[callable] = None,
        after_callback: Optional[callable] = None
    ):
        """
        Context manager for monitoring memory usage during operations.
        
        Args:
            operation_name: Name of the operation being monitored
            before_callback: Optional callback before operation
            after_callback: Optional callback after operation
        """
        class MemoryMonitor:
            def __init__(self, name, before_cb, after_cb):
                self.name = name
                self.before_cb = before_cb
                self.after_cb = after_cb
                self.before_memory = None
            
            def __enter__(self):
                self.before_memory = MemoryManager.get_gpu_memory_info()
                if self.before_cb:
                    self.before_cb(self.before_memory)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                after_memory = MemoryManager.get_gpu_memory_info()
                if after_memory and self.before_memory:
                    memory_delta = (
                        after_memory["allocated_gb"] - self.before_memory["allocated_gb"]
                    )
                    logger.debug(
                        f"{self.name}: Memory delta: {memory_delta:+.3f}GB "
                        f"(before: {self.before_memory['allocated_gb']:.3f}GB, "
                        f"after: {after_memory['allocated_gb']:.3f}GB)"
                    )
                if self.after_cb:
                    self.after_cb(after_memory)
                return False
        
        return MemoryMonitor(operation_name, before_callback, after_callback)
    
    @staticmethod
    def cleanup_large_arrays(arrays: List[np.ndarray]):
        """
        Explicitly cleanup large numpy arrays.
        
        Args:
            arrays: List of numpy arrays to cleanup
        """
        for arr in arrays:
            del arr
        gc.collect()
        logger.debug(f"Cleaned up {len(arrays)} large arrays")
