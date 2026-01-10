"""Main experiment runner - orchestrates the full robustness test pipeline."""
import argparse
import logging
from pathlib import Path
import yaml
from datetime import datetime

# Import all pipeline modules
from data_ingest import ingest_manifest
from transforms.generate_transforms import generate_transforms
from fingerprint.embed import segment_audio, extract_embeddings, normalize_embeddings
from fingerprint.query_index import build_index, load_index
from fingerprint.run_queries import run_queries
from evaluation.analyze import analyze_results
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional import for failure capture (requires matplotlib/PIL)
try:
    from evaluation.failure_capture import capture_failures
    HAS_FAILURE_CAPTURE = True
except ImportError as e:
    logger.warning(f"Could not import failure_capture module: {e}. Failure capture will be skipped.")
    HAS_FAILURE_CAPTURE = False
    capture_failures = None

# Optional import for report generation (requires matplotlib/PIL)
try:
    from reports.render_report import generate_plots, render_html_report
    HAS_REPORT_GENERATION = True
except ImportError as e:
    logger.warning(f"Could not import report generation module: {e}. Report generation will be skipped.")
    HAS_REPORT_GENERATION = False
    generate_plots = None
    render_html_report = None


def run_full_experiment(
    config_path: Path,
    original_files_csv: Path = None,
    skip_steps: list = None,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
    use_parallel: bool = True
):
    """
    Run the complete robustness experiment pipeline (OPTIMIZED WITH PARALLEL PROCESSING).
    
    Steps:
    1. Ingest original files (if CSV provided)
    2. Generate transforms
    3. Build index from originals (parallel processing enabled)
    4. Run queries on transforms
    5. Analyze results
    6. Capture failures
    7. Generate report
    
    Args:
        config_path: Path to test matrix config YAML
        original_files_csv: Optional CSV with original files
        skip_steps: List of steps to skip
        max_workers: Number of parallel workers for indexing (None = auto-detect)
        batch_size: Batch size for segment processing (None = auto-detect)
        use_parallel: Whether to use parallel processing (default: True)
    """
    skip_steps = skip_steps or []
    
    # Load test matrix config
    with open(config_path, 'r') as f:
        test_config = yaml.safe_load(f)
    
    # Setup paths
    base_dir = Path("data")
    originals_dir = base_dir / "originals"
    transformed_dir = base_dir / "transformed"
    manifests_dir = base_dir / "manifests"
    embeddings_dir = Path("embeddings")
    indexes_dir = Path("indexes")
    reports_dir = Path("reports")
    
    # Create timestamped run directory
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = reports_dir / f"run_{run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting experiment run: {run_timestamp}")
    
    # Step 1: Ingest original files
    if "ingest" not in skip_steps and original_files_csv:
        logger.info("=" * 60)
        logger.info("Step 1: Ingesting original files")
        logger.info("=" * 60)
        
        try:
            files_manifest = ingest_manifest(
                original_files_csv,
                base_dir,
                normalize=True,
                sample_rate=test_config.get("originals", {}).get("sample_rate", 44100)
            )
            files_manifest_path = manifests_dir / "files_manifest.csv"
            files_manifest.to_csv(files_manifest_path, index=False)
            logger.info(f"Ingestion completed. Processed {len(files_manifest)} files.")
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise
    else:
        files_manifest_path = manifests_dir / "files_manifest.csv"
        if not files_manifest_path.exists():
            raise FileNotFoundError(f"Files manifest not found: {files_manifest_path}")
        
        # Verify manifest is not empty
        import pandas as pd
        check_df = pd.read_csv(files_manifest_path)
        if len(check_df) == 0:
            raise ValueError(f"Files manifest {files_manifest_path} is empty! Cannot proceed.")
        
        logger.info(f"Using existing files manifest: {files_manifest_path} ({len(check_df)} entries)")
    
    # Step 2: Generate transforms
    if "transforms" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 2: Generating transformed audio files")
        logger.info("=" * 60)
        
        transform_manifest = generate_transforms(
            files_manifest_path,
            config_path,
            base_dir,
            random_seed=test_config.get("global", {}).get("random_seed", 42)
        )
        transform_manifest_path = manifests_dir / "transform_manifest.csv"
    else:
        transform_manifest_path = manifests_dir / "transform_manifest.csv"
        if not transform_manifest_path.exists():
            raise FileNotFoundError(f"Transform manifest not found: {transform_manifest_path}")
        logger.info(f"Using existing transform manifest: {transform_manifest_path}")
    
    # Step 3: Build index from originals (OPTIMIZED WITH PARALLEL PROCESSING)
    if "index" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 3: Building FAISS index from originals (Parallel Processing Enabled)")
        logger.info("=" * 60)
        
        import pandas as pd
        import numpy as np
        import json
        from scripts.create_index import create_or_update_index
        from daw_parser.integration import load_daw_metadata_from_manifest
        
        # Use optimized create_or_update_index function (with parallel processing)
        index_path = indexes_dir / "faiss_index.bin"
        fingerprint_config_path = Path("config/fingerprint_v1.yaml")
        index_config_path = Path("config/index_config.json")
        
        # Check if we need to rebuild (force rebuild if requested in config)
        force_rebuild = test_config.get("index", {}).get("force_rebuild", False)
        
        # Get parallel processing parameters from function args, config, or use defaults
        # Function parameters take precedence over config
        index_config = test_config.get("index", {})
        index_max_workers = max_workers if max_workers is not None else index_config.get("max_workers", None)
        index_batch_size = batch_size if batch_size is not None else index_config.get("batch_size", None)
        index_use_parallel = use_parallel if use_parallel is not None else index_config.get("use_parallel", True)
        
        # Load DAW metadata from manifest (before indexing)
        daw_metadata = {}
        try:
            if files_manifest_path.exists():
                daw_metadata = load_daw_metadata_from_manifest(files_manifest_path)
                logger.info(f"Loaded DAW metadata for {len(daw_metadata)} files")
        except Exception as e:
            logger.warning(f"Failed to load DAW metadata: {e}")
        
        # Use optimized create_or_update_index function
        # This will use parallel processing automatically
        index_obj, index_metadata = create_or_update_index(
            files_input=files_manifest_path,
            output_index=index_path,
            fingerprint_config=fingerprint_config_path,
            index_config=index_config_path,
            existing_index=index_path if not force_rebuild else None,
            force_rebuild=force_rebuild,
            embeddings_dir=embeddings_dir,
            create_manifest=False,  # Already have manifest
            max_workers=index_max_workers,
            batch_size=index_batch_size,
            use_parallel=index_use_parallel
        )
        
        # Add DAW metadata to index metadata if not already present
        if daw_metadata and "daw_metadata" not in index_metadata:
            try:
                # Reload metadata and add DAW data
                metadata_path = index_path.with_suffix(".json")
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        existing_metadata = json.load(f)
                    existing_metadata["daw_metadata"] = daw_metadata
                    with open(metadata_path, 'w') as f:
                        json.dump(existing_metadata, f, indent=2, default=str)
                    logger.info(f"Added DAW metadata to index metadata file")
            except Exception as e:
                logger.warning(f"Failed to add DAW metadata to index metadata: {e}")
        
        logger.info(f"✓ Index built/updated with {index_obj.ntotal} vectors")
    else:
        index_path = indexes_dir / "faiss_index.bin"
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")
        logger.info(f"Using existing index: {index_path}")
    
    # Step 4: Run queries
    if "queries" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 4: Running queries on transformed files")
        logger.info("=" * 60)
        
        fingerprint_config_path = Path("config/fingerprint_v1.yaml")
        query_results_dir = run_dir / "query_results"
        query_results_dir.mkdir(parents=True, exist_ok=True)
        
        # Get parallel processing parameters from config or function args
        query_config = test_config.get("queries", {})
        query_max_workers = max_workers if max_workers is not None else query_config.get("max_workers", None)
        query_use_parallel = use_parallel if use_parallel is not None else query_config.get("use_parallel", True)
        
        query_df = run_queries(
            transform_manifest_path,
            index_path,
            fingerprint_config_path,
            query_results_dir,
            topk=query_config.get("topk", 10),  # Use config topk or default to 10
            max_workers=query_max_workers,
            use_parallel=query_use_parallel
        )
        query_summary_path = query_results_dir / "query_summary.csv"
    else:
        query_summary_path = run_dir / "query_results" / "query_summary.csv"
        if not query_summary_path.exists():
            raise FileNotFoundError(f"Query results not found: {query_summary_path}")
        logger.info(f"Using existing query results: {query_summary_path}")
    
    # Step 5: Analyze results
    if "analysis" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 5: Analyzing results")
        logger.info("=" * 60)
        
        metrics = analyze_results(
            query_summary_path,
            transform_manifest_path,
            config_path,
            run_dir
        )
    else:
        logger.info("Skipping analysis step")
    
    # Step 6: Capture failures
    if "failures" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 6: Capturing failure cases")
        logger.info("=" * 60)
        
        failure_config = test_config.get("failure_capture", {})
        if failure_config.get("enabled", True):
            if not HAS_FAILURE_CAPTURE or capture_failures is None:
                logger.warning("Failure capture is enabled but the module is not available (missing matplotlib/PIL). Skipping failure capture.")
            else:
                proofs_dir = reports_dir / "proofs"
                query_results_json_dir = run_dir / "query_results"
                
                capture_failures(
                    query_summary_path,
                    transform_manifest_path,
                    files_manifest_path,
                    query_results_json_dir,
                    proofs_dir,
                    max_failures_per_transform=failure_config.get("max_failures_per_transform", 10)
                )
    
    # Step 7: Generate report
    if "report" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 7: Generating final report")
        logger.info("=" * 60)
        
        metrics_path = run_dir / "metrics.json"
        summary_path = run_dir / "suite_summary.csv"
        
        if metrics_path.exists() and summary_path.exists():
            final_report_dir = run_dir / "final_report"
            final_report_dir.mkdir(parents=True, exist_ok=True)
            
            if not HAS_REPORT_GENERATION:
                logger.warning("Report generation is disabled (matplotlib/PIL not available). Skipping plot and HTML report generation.")
                logger.info("Metrics and summary files are available in the run directory.")
            else:
                # Generate plots
                try:
                    logger.info("Generating plots...")
                    generate_plots(metrics_path, final_report_dir, config_path)
                    # Verify plots directory exists
                    plots_dir = final_report_dir / "plots"
                    if plots_dir.exists():
                        plot_count = len(list(plots_dir.glob("*.png")))
                        if plot_count > 0:
                            logger.info(f"✓ Successfully generated {plot_count} plot(s)")
                        else:
                            logger.warning(f"⚠ Plots directory exists but contains no PNG files")
                    else:
                        logger.warning(f"⚠ Plots directory was not created: {plots_dir}")
                except Exception as e:
                    logger.error(f"Error during plot generation: {e}", exc_info=True)
                    logger.error("Continuing with HTML report generation despite plot errors...")
                
                # Generate HTML
                html_path = final_report_dir / "report.html"
                render_html_report(
                    metrics_path, 
                    summary_path, 
                    html_path, 
                    config_path,
                    files_manifest_path=files_manifest_path,
                    include_daw_stats=True
                )
                
                # Copy proofs if they exist
                proofs_dir = reports_dir / "proofs"
                if proofs_dir.exists():
                    import shutil
                    final_proofs_dir = final_report_dir / "proofs"
                    if proofs_dir.exists():
                        shutil.copytree(proofs_dir, final_proofs_dir, dirs_exist_ok=True)
                
                logger.info(f"Report generated: {final_report_dir / 'report.html'}")
                
                # ZIP packaging disabled - report files are available directly in {final_report_dir}
    
    logger.info("=" * 60)
    logger.info("Experiment complete!")
    logger.info(f"Results saved to: {run_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full robustness experiment")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/test_matrix.yaml"),
        help="Test matrix config YAML"
    )
    parser.add_argument(
        "--originals",
        type=Path,
        help="CSV file with original audio files (optional if already ingested)"
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=["ingest", "transforms", "index", "queries", "analysis", "failures", "report"],
        help="Steps to skip"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers for indexing (default: auto-detect, 4-6 for GPU, CPU_count-1 for CPU)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for segment processing (default: 64-128 for GPU, 32 for CPU)"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing for indexing (use sequential)"
    )
    
    args = parser.parse_args()
    
    run_full_experiment(
        args.config,
        original_files_csv=args.originals,
        skip_steps=args.skip or [],
        max_workers=args.workers,
        batch_size=args.batch_size,
        use_parallel=not args.no_parallel
    )
