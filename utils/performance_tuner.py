"""Performance tuning utilities for query optimization."""
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class PerformanceTuner:
    """Utilities for performance tuning and optimization."""
    
    @staticmethod
    def tune_hyperparameters(
        query_results: List[Dict],
        ground_truth: Dict[str, str],
        config_space: Dict[str, List[float]]
    ) -> Dict[str, float]:
        """
        Tune hyperparameters based on query results.
        
        Args:
            query_results: List of query result dictionaries
            ground_truth: Dictionary mapping query_id -> expected_orig_id
            config_space: Dictionary of parameter names to lists of values to try
            
        Returns:
            Dictionary of optimal parameter values
        """
        best_config = {}
        best_score = 0.0
        
        # Grid search over parameter space
        # This is a simplified version - full implementation would use more sophisticated search
        logger.info("Starting hyperparameter tuning...")
        
        # Example: tune similarity threshold
        if "min_similarity_threshold" in config_space:
            thresholds = config_space["min_similarity_threshold"]
            for threshold in thresholds:
                # Evaluate this threshold
                score = PerformanceTuner._evaluate_config(
                    query_results, ground_truth, {"min_similarity_threshold": threshold}
                )
                if score > best_score:
                    best_score = score
                    best_config["min_similarity_threshold"] = threshold
        
        logger.info(f"Best configuration: {best_config} (score: {best_score:.3f})")
        return best_config
    
    @staticmethod
    def _evaluate_config(
        query_results: List[Dict],
        ground_truth: Dict[str, str],
        config: Dict[str, float]
    ) -> float:
        """Evaluate a configuration by computing recall@1."""
        correct = 0
        total = 0
        
        for result in query_results:
            query_id = result.get("query_id", "")
            if query_id not in ground_truth:
                continue
            
            expected_id = ground_truth[query_id]
            top_match = result.get("top_match_id", "")
            
            # Apply similarity threshold if specified
            if "min_similarity_threshold" in config:
                top_similarity = result.get("top_match_similarity", 0.0)
                if top_similarity < config["min_similarity_threshold"]:
                    continue  # Skip if below threshold
            
            if expected_id in str(top_match):
                correct += 1
            total += 1
        
        return correct / total if total > 0 else 0.0
    
    @staticmethod
    def optimize_memory_usage(
        current_batch_size: int,
        available_memory_gb: float,
        embedding_dim: int = 512
    ) -> int:
        """
        Optimize batch size based on available memory.
        
        Args:
            current_batch_size: Current batch size
            available_memory_gb: Available GPU memory in GB
            embedding_dim: Embedding dimension
            
        Returns:
            Optimized batch size
        """
        # Estimate memory per batch
        # Embeddings: batch_size * embedding_dim * 4 bytes (FP32)
        # Model overhead: ~100MB per batch
        memory_per_batch_gb = (current_batch_size * embedding_dim * 4) / 1e9 + 0.1
        
        # Use 70% of available memory
        safe_memory_gb = available_memory_gb * 0.7
        optimal_batch = int(safe_memory_gb / memory_per_batch_gb) if memory_per_batch_gb > 0 else current_batch_size
        
        # Clamp to reasonable bounds
        optimal_batch = max(16, min(optimal_batch, 256))
        
        logger.debug(
            f"Memory optimization: {current_batch_size} -> {optimal_batch} "
            f"(available: {available_memory_gb:.2f}GB)"
        )
        
        return optimal_batch
    
    @staticmethod
    def profile_query_performance(
        query_func,
        *args,
        **kwargs
    ) -> Dict[str, float]:
        """
        Profile query performance and return timing breakdown.
        
        Args:
            query_func: Query function to profile
            *args: Positional arguments for query function
            **kwargs: Keyword arguments for query function
            
        Returns:
            Dictionary with timing breakdown
        """
        timings = {}
        
        # Total time
        start_total = time.time()
        result = query_func(*args, **kwargs)
        timings["total_ms"] = (time.time() - start_total) * 1000
        
        # Extract timing from result if available
        if isinstance(result, dict):
            timings["latency_ms"] = result.get("latency_ms", timings["total_ms"])
            timings["num_segments"] = result.get("num_segments", 0)
            timings["segments_per_ms"] = (
                timings["num_segments"] / timings["latency_ms"]
                if timings["latency_ms"] > 0 else 0
            )
        
        return timings
    
    @staticmethod
    def analyze_bottlenecks(
        query_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze performance bottlenecks from query results.
        
        Args:
            query_results: List of query result dictionaries with timing info
            
        Returns:
            Dictionary with bottleneck analysis
        """
        latencies = [r.get("latency_ms", 0) for r in query_results if "latency_ms" in r]
        
        if not latencies:
            return {"error": "No timing data available"}
        
        analysis = {
            "mean_latency_ms": np.mean(latencies),
            "median_latency_ms": np.median(latencies),
            "p95_latency_ms": np.percentile(latencies, 95),
            "p99_latency_ms": np.percentile(latencies, 99),
            "min_latency_ms": np.min(latencies),
            "max_latency_ms": np.max(latencies),
            "std_latency_ms": np.std(latencies),
            "slow_queries": [
                r for r in query_results
                if r.get("latency_ms", 0) > np.percentile(latencies, 95)
            ]
        }
        
        return analysis
