"""
Master script to generate comprehensive Phase 1 and Phase 2 deliverables.

This script:
1. Runs Phase 1 tests (Core Manipulation)
2. Runs Phase 2 tests (Structural Manipulation)
3. Generates comprehensive reports for both phases
4. Creates comparison analysis
5. Packages all deliverables for customer submission
"""
import argparse
import logging
import shutil
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import yaml

from run_experiment import run_full_experiment

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_phase_deliverables(
    phase: str,
    config_path: Path,
    original_files_csv: Path = None,
    skip_steps: list = None
) -> Path:
    """
    Generate deliverables for a specific phase.
    
    Args:
        phase: "phase1" or "phase2"
        config_path: Path to test matrix YAML
        original_files_csv: Optional CSV with original files
        skip_steps: Steps to skip
        
    Returns:
        Path to phase report directory
    """
    logger.info("=" * 80)
    logger.info(f"GENERATING {phase.upper()} DELIVERABLES")
    logger.info("=" * 80)
    
    # Run full experiment for this phase
    run_full_experiment(
        config_path,
        original_files_csv=original_files_csv,
        skip_steps=skip_steps or []
    )
    
    # Find the most recent report directory
    reports_dir = Path("reports")
    run_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir() and d.name.startswith("run_")], reverse=True)
    
    if not run_dirs:
        raise FileNotFoundError(f"No report directory found for {phase}")
    
    latest_run_dir = run_dirs[0]
    logger.info(f"{phase.upper()} deliverables generated in: {latest_run_dir}")
    
    return latest_run_dir


def create_comparison_report(phase1_dir: Path, phase2_dir: Path, output_dir: Path):
    """Create comparison report between Phase 1 and Phase 2."""
    logger.info("=" * 80)
    logger.info("CREATING PHASE 1 vs PHASE 2 COMPARISON REPORT")
    logger.info("=" * 80)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metrics from both phases
    phase1_metrics_path = phase1_dir / "metrics.json"
    phase2_metrics_path = phase2_dir / "metrics.json"
    
    phase1_summary_path = phase1_dir / "suite_summary.csv"
    phase2_summary_path = phase2_dir / "suite_summary.csv"
    
    if not phase1_metrics_path.exists() or not phase2_metrics_path.exists():
        logger.warning("Metrics files not found, skipping comparison")
        return
    
    with open(phase1_metrics_path, 'r') as f:
        phase1_metrics = json.load(f)
    
    with open(phase2_metrics_path, 'r') as f:
        phase2_metrics = json.load(f)
    
    phase1_summary = pd.read_csv(phase1_summary_path) if phase1_summary_path.exists() else None
    phase2_summary = pd.read_csv(phase2_summary_path) if phase2_summary_path.exists() else None
    
    # Create comparison data
    comparison = {
        "phase1": {
            "total_tests": phase1_metrics.get("summary", {}).get("total_queries", 0),
            "overall_recall_at_1": phase1_metrics.get("overall", {}).get("recall", {}).get("recall_at_1", 0.0),
            "overall_recall_at_5": phase1_metrics.get("overall", {}).get("recall", {}).get("recall_at_5", 0.0),
            "overall_recall_at_10": phase1_metrics.get("overall", {}).get("recall", {}).get("recall_at_10", 0.0),
            "mean_rank": phase1_metrics.get("overall", {}).get("rank", {}).get("mean_rank", 0.0),
            "mean_similarity": phase1_metrics.get("overall", {}).get("similarity", {}).get("mean_similarity_correct", 0.0),
        },
        "phase2": {
            "total_tests": phase2_metrics.get("summary", {}).get("total_queries", 0),
            "overall_recall_at_1": phase2_metrics.get("overall", {}).get("recall", {}).get("recall_at_1", 0.0),
            "overall_recall_at_5": phase2_metrics.get("overall", {}).get("recall", {}).get("recall_at_5", 0.0),
            "overall_recall_at_10": phase2_metrics.get("overall", {}).get("recall", {}).get("recall_at_10", 0.0),
            "mean_rank": phase2_metrics.get("overall", {}).get("rank", {}).get("mean_rank", 0.0),
            "mean_similarity": phase2_metrics.get("overall", {}).get("similarity", {}).get("mean_similarity_correct", 0.0),
        }
    }
    
    # Calculate differences
    comparison["differences"] = {
        "recall_at_1_diff": comparison["phase2"]["overall_recall_at_1"] - comparison["phase1"]["overall_recall_at_1"],
        "recall_at_5_diff": comparison["phase2"]["overall_recall_at_5"] - comparison["phase1"]["overall_recall_at_5"],
        "recall_at_10_diff": comparison["phase2"]["overall_recall_at_10"] - comparison["phase1"]["overall_recall_at_10"],
        "mean_rank_diff": comparison["phase2"]["mean_rank"] - comparison["phase1"]["mean_rank"],
        "mean_similarity_diff": comparison["phase2"]["mean_similarity"] - comparison["phase1"]["mean_similarity"],
    }
    
    # Save comparison JSON
    comparison_path = output_dir / "phase_comparison.json"
    with open(comparison_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    logger.info(f"Comparison report saved to: {comparison_path}")
    
    # Create comparison CSV if summaries exist
    if phase1_summary is not None and phase2_summary is not None:
        comparison_csv_path = output_dir / "phase_comparison.csv"
        
        # Merge summaries with phase labels
        phase1_summary["phase"] = "Phase 1"
        phase2_summary["phase"] = "Phase 2"
        
        combined = pd.concat([phase1_summary, phase2_summary], ignore_index=True)
        combined.to_csv(comparison_csv_path, index=False)
        
        logger.info(f"Comparison CSV saved to: {comparison_csv_path}")


def package_all_deliverables(
    phase1_dir: Path,
    phase2_dir: Path,
    comparison_dir: Path,
    output_zip: Path
):
    """Package all deliverables into a ZIP file."""
    logger.info("=" * 80)
    logger.info("PACKAGING ALL DELIVERABLES")
    logger.info("=" * 80)
    
    import zipfile
    
    output_zip = Path(output_zip)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add Phase 1 deliverables
        if phase1_dir.exists():
            for file_path in phase1_dir.rglob("*"):
                if file_path.is_file():
                    arcname = f"phase1_deliverables/{file_path.relative_to(phase1_dir)}"
                    zipf.write(file_path, arcname)
        
        # Add Phase 2 deliverables
        if phase2_dir.exists():
            for file_path in phase2_dir.rglob("*"):
                if file_path.is_file():
                    arcname = f"phase2_deliverables/{file_path.relative_to(phase2_dir)}"
                    zipf.write(file_path, arcname)
        
        # Add comparison report
        if comparison_dir.exists():
            for file_path in comparison_dir.rglob("*"):
                if file_path.is_file():
                    arcname = f"comparison/{file_path.relative_to(comparison_dir)}"
                    zipf.write(file_path, arcname)
        
        # Add README
        readme_content = f"""# Fingerprint Robustness Test Deliverables

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Contents

### Phase 1 Deliverables (Core Manipulation Tests)
- Comprehensive HTML report
- CSV summary with all metrics
- JSON metrics file
- Visualizations (plots)
- Failure case proofs (if any)

### Phase 2 Deliverables (Structural Manipulation Tests)
- Comprehensive HTML report
- CSV summary with all metrics
- JSON metrics file
- Visualizations (plots)
- Failure case proofs (if any)

### Comparison Report
- Phase 1 vs Phase 2 comparison metrics
- Performance differences analysis

## How to Use

1. Open `phase1_deliverables/final_report/report.html` for Phase 1 results
2. Open `phase2_deliverables/final_report/report.html` for Phase 2 results
3. Review `comparison/phase_comparison.json` for comparison metrics

## Test Coverage

### Phase 1 Tests:
- Tempo changes (±3%, ±6%, ±10%)
- Pitch shifts (±1, ±2, ±3 semitones)
- Combined Pitch + Tempo
- EQ manipulations (high-pass, low-pass, boost highs/lows, telephone filter)
- Compression/Limiting

### Phase 2 Tests:
- Add Percussion Layers (drum loops, trap, boom-bap)
- Add Melodic Layers (pad/chords, lead melody, countermelody)
- Remove Elements (bass-only, remove highs)
- Noise & Room Effects (white noise, vinyl crackle, reverb)
- Cropping (10s, 5s, middle segment, end segment)

## Questions?

Contact the development team for any questions about these deliverables.
"""
        zipf.writestr("README.txt", readme_content)
    
    logger.info(f"All deliverables packaged to: {output_zip}")
    logger.info(f"Package size: {output_zip.stat().st_size / (1024*1024):.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive Phase 1 and Phase 2 deliverables"
    )
    parser.add_argument(
        "--originals",
        type=Path,
        help="CSV file with original audio files (optional if already ingested)"
    )
    parser.add_argument(
        "--skip-phase1",
        action="store_true",
        help="Skip Phase 1 if already completed"
    )
    parser.add_argument(
        "--skip-phase2",
        action="store_true",
        help="Skip Phase 2 if already completed"
    )
    parser.add_argument(
        "--skip-steps",
        nargs="+",
        choices=["ingest", "transforms", "index", "queries", "analysis", "failures", "report"],
        help="Steps to skip for both phases"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("deliverables"),
        help="Output directory for packaged deliverables"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    phase1_config = Path("config/test_matrix_phase1.yaml")
    phase2_config = Path("config/test_matrix_phase2.yaml")
    
    if not phase1_config.exists():
        raise FileNotFoundError(f"Phase 1 config not found: {phase1_config}")
    if not phase2_config.exists():
        raise FileNotFoundError(f"Phase 2 config not found: {phase2_config}")
    
    # Generate Phase 1 deliverables
    phase1_dir = None
    if not args.skip_phase1:
        phase1_dir = generate_phase_deliverables(
            "phase1",
            phase1_config,
            original_files_csv=args.originals,
            skip_steps=args.skip_steps
        )
    else:
        # Find latest Phase 1 run
        reports_dir = Path("reports")
        run_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir() and d.name.startswith("run_")], reverse=True)
        if run_dirs:
            phase1_dir = run_dirs[0]
            logger.info(f"Using existing Phase 1 results: {phase1_dir}")
    
    # Generate Phase 2 deliverables
    phase2_dir = None
    if not args.skip_phase2:
        phase2_dir = generate_phase_deliverables(
            "phase2",
            phase2_config,
            original_files_csv=args.originals,
            skip_steps=args.skip_steps
        )
    else:
        # Find latest Phase 2 run
        reports_dir = Path("reports")
        run_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir() and d.name.startswith("run_")], reverse=True)
        if run_dirs:
            phase2_dir = run_dirs[0]
            logger.info(f"Using existing Phase 2 results: {phase2_dir}")
    
    if not phase1_dir or not phase2_dir:
        raise FileNotFoundError("Both Phase 1 and Phase 2 results are required")
    
    # Create comparison report
    comparison_dir = args.output_dir / "comparison"
    create_comparison_report(phase1_dir, phase2_dir, comparison_dir)
    
    # Package all deliverables
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_zip = args.output_dir / f"fingerprint_robustness_deliverables_{timestamp}.zip"
    package_all_deliverables(phase1_dir, phase2_dir, comparison_dir, output_zip)
    
    logger.info("=" * 80)
    logger.info("✅ ALL DELIVERABLES GENERATED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"📦 Package: {output_zip}")
    logger.info(f"📊 Phase 1 Report: {phase1_dir / 'final_report' / 'report.html'}")
    logger.info(f"📊 Phase 2 Report: {phase2_dir / 'final_report' / 'report.html'}")
    logger.info(f"📈 Comparison: {comparison_dir / 'phase_comparison.json'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

