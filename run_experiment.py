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
    from reports.render_report import generate_plots, render_html_report, package_report
    HAS_REPORT_GENERATION = True
except ImportError as e:
    logger.warning(f"Could not import report generation module: {e}. Report generation will be skipped.")
    HAS_REPORT_GENERATION = False
    generate_plots = None
    render_html_report = None
    package_report = None


def run_full_experiment(
    config_path: Path,
    original_files_csv: Path = None,
    skip_steps: list = None
):
    """
    Run the complete robustness experiment pipeline.
    
    Steps:
    1. Ingest original files (if CSV provided)
    2. Generate transforms
    3. Build index from originals
    4. Run queries on transforms
    5. Analyze results
    6. Capture failures
    7. Generate report
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
    
    # Step 3: Build index from originals
    if "index" not in skip_steps:
        logger.info("=" * 60)
        logger.info("Step 3: Building FAISS index from originals")
        logger.info("=" * 60)
        
        import pandas as pd
        from fingerprint.load_model import load_fingerprint_model
        
        # Load fingerprint config
        fingerprint_config_path = Path("config/fingerprint_v1.yaml")
        model_config = load_fingerprint_model(fingerprint_config_path)
        
        # Process all original files
        files_df = pd.read_csv(files_manifest_path)
        logger.info(f"Loaded manifest with {len(files_df)} files. Columns: {list(files_df.columns)}")
        all_embeddings = []
        all_ids = []
        
        for _, row in files_df.iterrows():
            # Handle both "file_path" and "path" column names for compatibility
            file_path_str = row.get("file_path") or row.get("path")
            if not file_path_str:
                logger.error(f"Manifest row missing 'file_path' or 'path' column. Available columns: {list(row.index)}")
                continue
            
            file_path = Path(file_path_str)
            file_id = row["id"]
            
            # Resolve relative paths
            if not file_path.is_absolute():
                if not file_path.exists():
                    # Try resolving relative to project root (current working directory)
                    potential_path = Path.cwd() / file_path
                    if potential_path.exists():
                        file_path = potential_path
                        logger.info(f"Resolved relative path: {file_path_str} -> {file_path}")
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path} (from manifest: {file_path_str})")
                continue
            
            logger.info(f"Processing {file_id} -> {file_path}")
            
            # Segment and extract embeddings
            segments = segment_audio(
                file_path,
                segment_length=model_config["segment_length"],
                sample_rate=model_config["sample_rate"]
            )
            
            embeddings = extract_embeddings(
                segments,
                model_config,
                output_dir=embeddings_dir / file_id,
                save_embeddings=True
            )
            
            # Normalize
            embeddings = normalize_embeddings(embeddings, method="l2")
            
            # Store with IDs
            for i, seg in enumerate(segments):
                seg_id = f"{file_id}_seg_{i:04d}"
                all_embeddings.append(embeddings[i])
                all_ids.append(seg_id)
        
        # Build index
        import numpy as np
        embeddings_array = np.vstack(all_embeddings)
        
        # Load index config
        index_config_path = Path("config/index_config.json")
        import json
        with open(index_config_path, 'r') as f:
            index_config = json.load(f)
        
        index_path = indexes_dir / "faiss_index.bin"
        build_index(embeddings_array, all_ids, index_path, index_config)
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
        
        query_df = run_queries(
            transform_manifest_path,
            index_path,
            fingerprint_config_path,
            query_results_dir,
            topk=10
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
                generate_plots(metrics_path, final_report_dir, config_path)
                
                # Generate HTML
                html_path = final_report_dir / "report.html"
                render_html_report(metrics_path, summary_path, html_path, config_path)
                
                # Copy proofs if they exist
                proofs_dir = reports_dir / "proofs"
                if proofs_dir.exists():
                    import shutil
                    final_proofs_dir = final_report_dir / "proofs"
                    if proofs_dir.exists():
                        shutil.copytree(proofs_dir, final_proofs_dir, dirs_exist_ok=True)
                
                logger.info(f"Report generated: {final_report_dir / 'report.html'}")
                
                # Package report
                package_report(final_report_dir, run_dir.parent / f"final_report_{run_timestamp}.zip")
    
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
    
    args = parser.parse_args()
    
    run_full_experiment(
        args.config,
        original_files_csv=args.originals,
        skip_steps=args.skip or []
    )
