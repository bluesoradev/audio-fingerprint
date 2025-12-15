"""Analyze evaluation results and generate metrics."""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict
import pandas as pd
import yaml

from .metrics import (
    compute_recall_at_k,
    compute_rank_distribution,
    compute_similarity_stats,
    compute_latency_stats
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_results(
    query_results_path: Path,
    transform_manifest_path: Path,
    test_matrix_path: Path,
    output_dir: Path
) -> Dict:
    """
    Analyze query results and compute all metrics.
    
    Returns:
        Dictionary with all metrics and analysis
    """
    # Load data
    query_df = pd.read_csv(query_results_path)
    transform_df = pd.read_csv(transform_manifest_path)
    
    with open(test_matrix_path, 'r') as f:
        test_config = yaml.safe_load(f)
    
    thresholds = test_config.get("thresholds", {})
    
    logger.info(f"Analyzing {len(query_df)} query results")
    
    # Build ground truth mapping
    ground_truth_map = dict(zip(transform_df["transformed_id"], transform_df["orig_id"]))
    
    # Compute overall metrics
    k_values = test_config.get("evaluation", {}).get("top_k_values", [1, 5, 10])
    recalls = compute_recall_at_k(query_df, ground_truth_map, k_values)
    rank_stats = compute_rank_distribution(query_df, ground_truth_map)
    similarity_stats = compute_similarity_stats(query_df, ground_truth_map)
    latency_stats = compute_latency_stats(query_df)
    
    # Compute per-transform-type metrics
    per_transform = {}
    for transform_type in query_df["transform_type"].unique():
        subset = query_df[query_df["transform_type"] == transform_type]
        per_transform[transform_type] = {
            "recall": compute_recall_at_k(subset, ground_truth_map, k_values),
            "rank": compute_rank_distribution(subset, ground_truth_map),
            "similarity": compute_similarity_stats(subset, ground_truth_map),
            "latency": compute_latency_stats(subset),
            "count": len(subset),
        }
    
    # Compute per-severity metrics
    per_severity = {}
    for severity in query_df["severity"].unique():
        subset = query_df[query_df["severity"] == severity]
        per_severity[severity] = {
            "recall": compute_recall_at_k(subset, ground_truth_map, k_values),
            "rank": compute_rank_distribution(subset, ground_truth_map),
            "similarity": compute_similarity_stats(subset, ground_truth_map),
            "latency": compute_latency_stats(subset),
            "count": len(subset),
        }
    
    # Determine pass/fail status
    pass_fail = {}
    recall_thresholds = thresholds.get("recall_at_k", {})
    
    for severity, thresh_config in recall_thresholds.items():
        if severity in per_severity:
            severity_recalls = per_severity[severity]["recall"]
            
            # Compute recall values and thresholds, ensuring they're floats
            recall_1_actual = float(severity_recalls.get("recall_at_1", 0.0))
            recall_1_threshold = float(thresh_config.get("recall_at_1", 0.9))
            
            recall_5_actual = float(severity_recalls.get("recall_at_5", 0.0))
            recall_5_threshold = float(thresh_config.get("recall_at_5", 0.95))
            
            recall_10_actual = float(severity_recalls.get("recall_at_10", 0.0))
            recall_10_threshold = float(thresh_config.get("recall_at_10", 0.98))
            
            pass_fail[severity] = {
                "recall_at_1": {
                    "threshold": recall_1_threshold,
                    "actual": recall_1_actual,
                    "passed": recall_1_actual >= recall_1_threshold,
                },
                "recall_at_5": {
                    "threshold": recall_5_threshold,
                    "actual": recall_5_actual,
                    "passed": recall_5_actual >= recall_5_threshold,
                },
                "recall_at_10": {
                    "threshold": recall_10_threshold,
                    "actual": recall_10_actual,
                    "passed": recall_10_actual >= recall_10_threshold,
                },
            }
    
    # Evaluate similarity thresholds (per-severity)
    similarity_thresholds = thresholds.get("similarity", {})
    for severity in pass_fail.keys():
        if severity in per_severity:
            severity_similarity = per_severity[severity]["similarity"]
            mean_sim = float(severity_similarity.get("mean_similarity_correct", 0.0))
            sim_threshold = float(similarity_thresholds.get(f"min_score_{severity}", 0.0))
            
            pass_fail[severity]["similarity"] = {
                "threshold": sim_threshold,
                "actual": mean_sim,
                "passed": mean_sim >= sim_threshold,
            }
    
    # Evaluate latency thresholds (overall, not per-severity)
    latency_thresholds = thresholds.get("latency", {})
    pass_fail["overall"] = pass_fail.get("overall", {})
    
    # Compute latency values and thresholds, ensuring they're floats
    mean_latency_actual = float(latency_stats.get("mean_latency_ms", 0.0))
    mean_latency_threshold = float(latency_thresholds.get("max_mean_ms", 1000))
    
    p95_latency_actual = float(latency_stats.get("p95_latency_ms", 0.0))
    p95_latency_threshold = float(latency_thresholds.get("max_p95_ms", 2000))
    
    pass_fail["overall"]["latency"] = {
        "mean_ms": {
            "threshold": mean_latency_threshold,
            "actual": mean_latency_actual,
            "passed": mean_latency_actual <= mean_latency_threshold,  # Latency: lower is better
        },
        "p95_ms": {
            "threshold": p95_latency_threshold,
            "actual": p95_latency_actual,
            "passed": p95_latency_actual <= p95_latency_threshold,  # Latency: lower is better
        },
    }
    
    # Compile full results
    results = {
        "overall": {
            "recall": recalls,
            "rank": rank_stats,
            "similarity": similarity_stats,
            "latency": latency_stats,
        },
        "per_transform": per_transform,
        "per_severity": per_severity,
        "pass_fail": pass_fail,
        "summary": {
            "total_queries": len(query_df),
            "total_transforms": len(transform_df),
            "transform_types": list(query_df["transform_type"].unique()),
            "severities": list(query_df["severity"].unique()),
        }
    }
    
    # Save results
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    json_path = output_dir / "metrics.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save CSV summary
    summary_rows = []
    for severity, data in per_severity.items():
        summary_rows.append({
            "severity": severity,
            "count": data["count"],
            "recall_at_1": data["recall"].get("recall_at_1", 0.0),
            "recall_at_5": data["recall"].get("recall_at_5", 0.0),
            "recall_at_10": data["recall"].get("recall_at_10", 0.0),
            "mean_rank": data["rank"]["mean_rank"],
            "mean_similarity": data["similarity"]["mean_similarity_correct"],
            "mean_latency_ms": data["latency"]["mean_latency_ms"],
        })
    
    summary_df = pd.DataFrame(summary_rows)
    csv_path = output_dir / "suite_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    
    logger.info(f"Analysis complete. Results saved to {output_dir}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze query results")
    parser.add_argument("--results", type=Path, required=True, help="Query results directory")
    parser.add_argument("--manifest", type=Path, required=True, help="Transform manifest CSV")
    parser.add_argument("--test-matrix", type=Path, required=True, help="Test matrix YAML")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    
    args = parser.parse_args()
    
    query_summary_path = args.results / "query_summary.csv"
    if not query_summary_path.exists():
        query_summary_path = args.results
    
    analyze_results(
        query_summary_path,
        args.manifest,
        args.test_matrix,
        args.output
    )
