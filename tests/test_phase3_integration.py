"""Integration tests for Phase 3 optimizations."""
import unittest
import tempfile
from pathlib import Path
import numpy as np
from unittest.mock import Mock, patch

from utils.performance_tuner import PerformanceTuner
from utils.memory_manager import MemoryManager
from utils.error_handler import (
    handle_query_errors,
    safe_execute,
    EmbeddingError,
    IndexQueryError
)


class TestPerformanceTuner(unittest.TestCase):
    """Test performance tuning utilities."""
    
    def test_optimize_memory_usage(self):
        """Test memory usage optimization."""
        optimal_batch = PerformanceTuner.optimize_memory_usage(
            current_batch_size=32,
            available_memory_gb=8.0,
            embedding_dim=512
        )
        self.assertGreaterEqual(optimal_batch, 16)
        self.assertLessEqual(optimal_batch, 256)
    
    def test_analyze_bottlenecks(self):
        """Test bottleneck analysis."""
        query_results = [
            {"latency_ms": 100},
            {"latency_ms": 200},
            {"latency_ms": 300},
            {"latency_ms": 400},
            {"latency_ms": 500}
        ]
        analysis = PerformanceTuner.analyze_bottlenecks(query_results)
        self.assertIn("mean_latency_ms", analysis)
        self.assertIn("p95_latency_ms", analysis)
        self.assertGreater(analysis["mean_latency_ms"], 0)


class TestMemoryManager(unittest.TestCase):
    """Test memory management utilities."""
    
    def test_get_gpu_memory_info(self):
        """Test GPU memory info retrieval."""
        memory_info = MemoryManager.get_gpu_memory_info()
        # Should return None if GPU unavailable, or dict if available
        self.assertTrue(memory_info is None or isinstance(memory_info, dict))
    
    def test_clear_gpu_cache(self):
        """Test GPU cache clearing."""
        # Should not raise exception
        MemoryManager.clear_gpu_cache()
    
    def test_clear_python_cache(self):
        """Test Python cache clearing."""
        # Should not raise exception
        MemoryManager.clear_python_cache()
    
    def test_optimize_batch_size(self):
        """Test batch size optimization."""
        optimal_batch = MemoryManager.optimize_batch_size(
            current_batch_size=32,
            target_memory_usage=0.7,
            embedding_dim=512
        )
        self.assertGreaterEqual(optimal_batch, 16)
        self.assertLessEqual(optimal_batch, 256)
    
    def test_memory_monitor(self):
        """Test memory monitoring context manager."""
        with MemoryManager.monitor_memory_usage("test_operation") as monitor:
            # Create some arrays
            arr1 = np.random.rand(1000, 1000)
            arr2 = np.random.rand(1000, 1000)
            del arr1, arr2
        # Should complete without error


class TestErrorHandler(unittest.TestCase):
    """Test error handling utilities."""
    
    def test_handle_query_errors_decorator(self):
        """Test error handling decorator."""
        @handle_query_errors(fallback_result={"error": "test"})
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        self.assertEqual(result["error"], "test")
    
    def test_safe_execute_with_fallback(self):
        """Test safe execution with fallback."""
        def failing_func():
            raise ValueError("Test error")
        
        def fallback_func():
            return "fallback_result"
        
        result = safe_execute(
            failing_func,
            fallback=fallback_func
        )
        self.assertEqual(result, "fallback_result")
    
    def test_safe_execute_success(self):
        """Test safe execution with success."""
        def success_func():
            return "success_result"
        
        result = safe_execute(success_func)
        self.assertEqual(result, "success_result")
    
    def test_custom_exceptions(self):
        """Test custom exception classes."""
        self.assertIsInstance(EmbeddingError("test"), Exception)
        self.assertIsInstance(IndexQueryError("test"), Exception)


if __name__ == "__main__":
    unittest.main()
