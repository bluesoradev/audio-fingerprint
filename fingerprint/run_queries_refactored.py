"""Refactored run_queries using component-based architecture."""
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from tqdm import tqdm

from repositories import IndexRepository, FileRepository, ConfigRepository
from services import QueryService, TransformService
from infrastructure.dependency_container import DependencyContainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_queries(
    transform_manifest_path: Path,
    index_path: Path,
    fingerprint_config_path: Path,
    output_dir: Path,
    topk: int = 30
) -> pd.DataFrame:
    """
    Run queries on all transformed files using refactored component architecture.
    
    Args:
        transform_manifest_path: Path to transform manifest CSV
        index_path: Path to FAISS index
        fingerprint_config_path: Path to fingerprint config YAML
        output_dir: Output directory for results
        topk: Top-K for queries
        
    Returns:
        DataFrame with query results
    """
    # Initialize dependency container
    container = DependencyContainer()
    container.initialize_repositories()
    
    # Load index and model config
    container.load_index(index_path)
    container.load_model_config(fingerprint_config_path)
    
    # Get services
    query_service = container.get_query_service()
    file_repository = container.get_file_repository()
    
    # Load transform manifest
    transform_df = file_repository.read_manifest(transform_manifest_path)
    logger.info(f"Loaded {len(transform_df)} transformed files")
    
    # Try to find files manifest for original file paths
    files_manifest_path = None
    possible_manifest_paths = [
        transform_manifest_path.parent / "files_manifest.csv",
        transform_manifest_path.parent.parent / "manifests" / "files_manifest.csv",
        Path("data") / "manifests" / "files_manifest.csv",
        Path("manifests") / "files_manifest.csv"
    ]
    for manifest_path in possible_manifest_paths:
        if manifest_path.exists():
            files_manifest_path = manifest_path
            logger.info(f"Found files manifest: {files_manifest_path}")
            break
    
    # Load files manifest if found
    files_manifest_df = None
    if files_manifest_path:
        files_manifest_df = file_repository.read_manifest(files_manifest_path)
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    query_records = []
    
    # Process each transformed file
    for _, row in tqdm(transform_df.iterrows(), total=len(transform_df), desc="Running queries"):
        file_path = Path(row["output_path"])
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}, skipping")
            continue
        
        # Extract transform type and expected original ID
        transform_type = row.get("transform_type", None)
        expected_orig_id = None
        
        # Try to find expected original ID from files manifest
        if files_manifest_df is not None and "original_id" in row:
            orig_id = row.get("original_id")
            if orig_id:
                expected_orig_id = orig_id
        
        # Run query
        try:
            result = query_service.query_file(
                file_path=file_path,
                transform_type=transform_type,
                expected_orig_id=expected_orig_id
            )
            
            # Extract top candidate
            top_candidate = result.top_candidates[0] if result.top_candidates else None
            
            # Build record
            record = {
                "file_path": str(file_path),
                "transform_type": transform_type,
                "expected_orig_id": expected_orig_id,
                "matched": top_candidate is not None,
                "top_rank": top_candidate.get("rank", None) if top_candidate else None,
                "top_similarity": top_candidate.get("similarity", None) if top_candidate else None,
                "top_id": top_candidate.get("id", None) if top_candidate else None,
                "recall_at_5": result.get_recall_at_k(5),
                "recall_at_10": result.get_recall_at_k(10),
                "mean_similarity": result.get_mean_similarity(),
                "latency_ms": result.latency_ms,
                "total_segments": len(result.segment_results),
                "scales_used": result.metadata.get("scales_used", 1)
            }
            
            query_records.append(record)
            
        except Exception as e:
            logger.error(f"Error querying {file_path}: {e}", exc_info=True)
            query_records.append({
                "file_path": str(file_path),
                "transform_type": transform_type,
                "expected_orig_id": expected_orig_id,
                "matched": False,
                "error": str(e)
            })
    
    # Create DataFrame
    results_df = pd.DataFrame(query_records)
    
    # Save results
    results_csv = results_dir / "query_results.csv"
    results_df.to_csv(results_csv, index=False)
    logger.info(f"Saved results to {results_csv}")
    
    return results_df


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run queries on transformed audio files")
    parser.add_argument("--transform-manifest", type=Path, required=True,
                        help="Path to transform manifest CSV")
    parser.add_argument("--index", type=Path, required=True,
                        help="Path to FAISS index")
    parser.add_argument("--fingerprint-config", type=Path, required=True,
                        help="Path to fingerprint config YAML")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Output directory for results")
    parser.add_argument("--topk", type=int, default=30,
                        help="Top-K for queries")
    
    args = parser.parse_args()
    
    results_df = run_queries(
        transform_manifest_path=args.transform_manifest,
        index_path=args.index,
        fingerprint_config_path=args.fingerprint_config,
        output_dir=args.output_dir,
        topk=args.topk
    )
    
    logger.info(f"Query completed. Processed {len(results_df)} files.")
    logger.info(f"Recall@5: {results_df['recall_at_5'].mean():.3f}")
    logger.info(f"Recall@10: {results_df['recall_at_10'].mean():.3f}")


if __name__ == "__main__":
    main()
