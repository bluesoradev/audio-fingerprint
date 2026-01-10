"""Generate final report (HTML, plots, etc.)."""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import yaml
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional imports for plotting (requires matplotlib/PIL)
HAS_PLOTTING = False
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError as e:
    logger.warning(f"Could not import plotting libraries (matplotlib/seaborn): {e}. Plot generation will be disabled.")
    plt = None
    sns = None


def generate_plots(metrics_path: Path, output_dir: Path, test_matrix_path: Path = None):
    """Generate visualization plots."""
    logger.info("=" * 60)
    logger.info("=== Starting plot generation ===")
    logger.info(f"Metrics path: {metrics_path}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Test matrix path: {test_matrix_path}")
    logger.info(f"HAS_PLOTTING: {HAS_PLOTTING}")
    
    if not HAS_PLOTTING:
        logger.error("Plot generation is disabled (matplotlib/PIL not available). Skipping plot generation.")
        logger.error("To enable plots, install: pip install matplotlib pillow seaborn")
        # Create empty plots directory so the structure exists
        plots_dir = output_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created empty plots directory")
        return
    
    # Load metrics
    try:
        logger.info("Loading metrics.json...")
        if not metrics_path.exists():
            logger.error(f"Metrics file does not exist: {metrics_path}")
            return
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        logger.info("Successfully loaded metrics.json")
    except Exception as e:
        logger.error(f"Failed to load metrics.json for plot generation: {e}", exc_info=True)
        return
    
    # Create plots directory
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Plots directory: {plots_dir}")
    
    try:
        # Set style
        logger.info("Configuring matplotlib style...")
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        logger.info("Matplotlib configured successfully")
    
        # Load thresholds if available
        similarity_thresholds = {}
        if test_matrix_path and test_matrix_path.exists():
            try:
                with open(test_matrix_path, 'r') as f:
                    test_config = yaml.safe_load(f)
                thresholds = test_config.get("thresholds", {})
                similarity_thresholds = thresholds.get("similarity", {})
                logger.info("Loaded similarity thresholds from test matrix")
            except Exception as e:
                logger.warning(f"Failed to load test matrix for thresholds: {e}")
        
        # Extract per_transform and per_severity early (needed for multiple plots)
        per_transform = metrics.get("per_transform", {})
        per_severity = metrics.get("per_severity", {})
        logger.info(f"Found {len(per_transform)} transform types and {len(per_severity)} severity levels")
    
        # Plot 1: Recall@K by severity
        logger.info("Generating plot 1: Recall@K by Transform Severity...")
        fig, ax = plt.subplots()
        
        severities = []
        recall_1 = []
        recall_5 = []
        recall_10 = []
        
        for severity in ["mild", "moderate", "severe", "none"]:
            if severity in per_severity:
                severities.append(severity)
                rec = per_severity[severity].get("recall", {})
                recall_1.append(rec.get("recall_at_1", 0.0))
                recall_5.append(rec.get("recall_at_5", 0.0))
                recall_10.append(rec.get("recall_at_10", 0.0))
        
        if severities:
            x = range(len(severities))
            width = 0.25
            
            ax.bar([i - width for i in x], recall_1, width, label='Recall@1')
            ax.bar(x, recall_5, width, label='Recall@5')
            ax.bar([i + width for i in x], recall_10, width, label='Recall@10')
            
            ax.set_xlabel('Severity')
            ax.set_ylabel('Recall')
            ax.set_title('Recall@K by Transform Severity')
            ax.set_xticks(x)
            ax.set_xticklabels(severities)
            ax.legend()
            ax.set_ylim(0, 1.1)
            logger.info(f"Plot 1: Found data for {len(severities)} severity levels")
        else:
            ax.text(0.5, 0.5, 'No severity data available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=14)
            ax.set_title('Recall@K by Transform Severity')
            logger.warning("Plot 1: No severity data available")
        
        try:
            plt.tight_layout(pad=2.0)
            plot_path = plots_dir / "recall_by_severity.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', pad_inches=0.2)
            plt.close()
            if plot_path.exists():
                logger.info(f"✓ Successfully generated: recall_by_severity.png ({plot_path.stat().st_size} bytes)")
            else:
                logger.error(f"✗ Plot file was not created: {plot_path}")
        except Exception as e:
            logger.error(f"✗ Failed to generate recall_by_severity.png: {e}", exc_info=True)
            try:
                plt.close()
            except:
                pass
    
        # Plot 2: Similarity score distribution by severity
        logger.info("Generating plot 2: Similarity Score by Severity...")
        fig, ax = plt.subplots()
        severities = []
        similarity_scores = []
        thresholds_list = []
        
        for severity in ["mild", "moderate", "severe"]:
            if severity in per_severity:
                severities.append(severity)
                sim_data = per_severity[severity].get("similarity", {})
                similarity_scores.append(sim_data.get("mean_similarity_correct", 0.0))
                thresholds_list.append(similarity_thresholds.get(f"min_score_{severity}", 0.0))
        
        if severities:
            x = range(len(severities))
            width = 0.35
            ax.bar([i - width/2 for i in x], similarity_scores, width, label='Actual Similarity', color='steelblue')
            ax.bar([i + width/2 for i in x], thresholds_list, width, label='Threshold', color='lightcoral', alpha=0.7)
            ax.set_xlabel('Severity')
            ax.set_ylabel('Similarity Score')
            ax.set_title('Similarity Scores vs Thresholds by Severity')
            ax.set_xticks(x)
            ax.set_xticklabels(severities)
            ax.legend()
            ax.set_ylim(0, 1.0)
            logger.info(f"Plot 2: Found data for {len(severities)} severity levels")
        else:
            ax.text(0.5, 0.5, 'No similarity data available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=14)
            ax.set_title('Similarity Scores vs Thresholds by Severity')
            logger.warning("Plot 2: No similarity data available")
        
        try:
            plt.tight_layout(pad=2.0)
            plot_path = plots_dir / "similarity_by_severity.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', pad_inches=0.2)
            plt.close()
            if plot_path.exists():
                logger.info(f"✓ Successfully generated: similarity_by_severity.png ({plot_path.stat().st_size} bytes)")
            else:
                logger.error(f"✗ Plot file was not created: {plot_path}")
        except Exception as e:
            logger.error(f"✗ Failed to generate similarity_by_severity.png: {e}", exc_info=True)
            try:
                plt.close()
            except:
                pass
    
        # Plot 3: Recall by transform type
        logger.info("Generating plot 3: Recall@K by Transform Type...")
        fig, ax = plt.subplots(figsize=(14, 6))
        
        if per_transform:
            transform_types = list(per_transform.keys())
            recall_1 = [per_transform[t].get("recall", {}).get("recall_at_1", 0.0) for t in transform_types]
            recall_5 = [per_transform[t].get("recall", {}).get("recall_at_5", 0.0) for t in transform_types]
            recall_10 = [per_transform[t].get("recall", {}).get("recall_at_10", 0.0) for t in transform_types]
            
            if transform_types:
                x = range(len(transform_types))
                width = 0.25
                ax.bar([i - width for i in x], recall_1, width, label='Recall@1')
                ax.bar(x, recall_5, width, label='Recall@5')
                ax.bar([i + width for i in x], recall_10, width, label='Recall@10')
                ax.set_xlabel('Transform Type')
                ax.set_ylabel('Recall')
                ax.set_title('Recall@K by Transform Type')
                ax.set_xticks(x)
                ax.set_xticklabels(transform_types, rotation=45, ha='right')
                ax.legend()
                ax.set_ylim(0, 1.1)
                logger.info(f"Plot 3: Found data for {len(transform_types)} transform types")
            else:
                ax.text(0.5, 0.5, 'No transform data available', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes, fontsize=14)
                ax.set_title('Recall@K by Transform Type')
                logger.warning("Plot 3: No transform types found")
        else:
            ax.text(0.5, 0.5, 'No transform data available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=14)
            ax.set_title('Recall@K by Transform Type')
            logger.warning("Plot 3: No transform data available")
        
        try:
            plt.tight_layout(pad=2.0)
            plot_path = plots_dir / "recall_by_transform.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', pad_inches=0.2)
            plt.close()
            if plot_path.exists():
                logger.info(f"✓ Successfully generated: recall_by_transform.png ({plot_path.stat().st_size} bytes)")
            else:
                logger.error(f"✗ Plot file was not created: {plot_path}")
        except Exception as e:
            logger.error(f"✗ Failed to generate recall_by_transform.png: {e}", exc_info=True)
            try:
                plt.close()
            except:
                pass
    
        # Plot 4: Latency by transform type
        logger.info("Generating plot 4: Latency by Transform Type...")
        fig, ax = plt.subplots()
        
        if per_transform:
            transform_types = []
            latencies = []
            
            for transform_type, data in per_transform.items():
                transform_types.append(transform_type)
                latency_data = data.get("latency", {})
                latencies.append(latency_data.get("mean_latency_ms", 0.0))
            
            if transform_types:
                ax.bar(transform_types, latencies)
                ax.set_xlabel('Transform Type')
                ax.set_ylabel('Mean Latency (ms)')
                ax.set_title('Processing Latency by Transform Type')
                plt.xticks(rotation=45, ha='right')
                logger.info(f"Plot 4: Found latency data for {len(transform_types)} transform types")
            else:
                ax.text(0.5, 0.5, 'No latency data available', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes, fontsize=14)
                ax.set_title('Processing Latency by Transform Type')
                logger.warning("Plot 4: No transform types found")
        else:
            ax.text(0.5, 0.5, 'No latency data available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=14)
            ax.set_title('Processing Latency by Transform Type')
            logger.warning("Plot 4: No transform data available")
        
        try:
            plt.tight_layout(pad=2.0)
            plot_path = plots_dir / "latency_by_transform.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', pad_inches=0.2)
            plt.close()
            if plot_path.exists():
                logger.info(f"✓ Successfully generated: latency_by_transform.png ({plot_path.stat().st_size} bytes)")
            else:
                logger.error(f"✗ Plot file was not created: {plot_path}")
        except Exception as e:
            logger.error(f"✗ Failed to generate latency_by_transform.png: {e}", exc_info=True)
            try:
                plt.close()
            except:
                pass
        
        # Verify plots were created
        logger.info("=" * 60)
        logger.info("=== Plot Generation Summary ===")
        plot_files = list(plots_dir.glob("*.png"))
        if plot_files:
            logger.info(f"✓ Successfully generated {len(plot_files)} plot(s) in {plots_dir}")
            for plot_file in sorted(plot_files):
                size = plot_file.stat().st_size
                logger.info(f"  ✓ {plot_file.name} ({size:,} bytes)")
        else:
            logger.error(f"✗ WARNING: No plot files were generated in {plots_dir}")
            logger.error("Check logs above for errors during plot generation.")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in plot generation: {e}", exc_info=True)
        logger.error("Plot generation failed completely. Check error above.")
        raise  # Re-raise so run_experiment.py can catch it


def calculate_daw_statistics(files_manifest_path: Optional[Path] = None) -> Dict:
    """
    Calculate DAW-related statistics from manifest.
    
    Args:
        files_manifest_path: Path to files manifest CSV
        
    Returns:
        Dictionary with DAW statistics
    """
    stats = {
        "total_with_daw": 0,
        "daw_types": {},
        "avg_notes_per_track": 0.0,
        "avg_tempo": 0.0,
        "total_files": 0
    }
    
    if not files_manifest_path or not files_manifest_path.exists():
        return stats
    
    try:
        from daw_parser.integration import load_daw_metadata_from_manifest
        
        df = pd.read_csv(files_manifest_path)
        stats["total_files"] = len(df)
        
        daw_metadata = load_daw_metadata_from_manifest(files_manifest_path)
        stats["total_with_daw"] = len(daw_metadata)
        
        if daw_metadata:
            total_notes = 0
            total_tracks = 0
            total_tempo = 0
            tempo_count = 0
            
            for file_id, metadata in daw_metadata.items():
                # Count DAW types
                daw_type = metadata.get("daw_type", "unknown")
                stats["daw_types"][daw_type] = stats["daw_types"].get(daw_type, 0) + 1
                
                # Calculate averages
                total_notes += metadata.get("total_notes", 0)
                total_tracks += metadata.get("midi_tracks", 0)
                
                # Get tempo (if available in metadata)
                # Note: This would need to be stored in metadata for accurate calculation
            
            if total_tracks > 0:
                stats["avg_notes_per_track"] = total_notes / total_tracks
        
    except Exception as e:
        logger.warning(f"Failed to calculate DAW statistics: {e}")
    
    return stats


def render_daw_statistics_section(stats: Dict) -> str:
    """
    Render DAW statistics HTML section.
    
    Args:
        stats: DAW statistics dictionary
        
    Returns:
        HTML string for DAW statistics section
    """
    if stats["total_with_daw"] == 0:
        return ""
    
    html = """
    <div class='metric-card'>
        <h3 class='card-title'>DAW Metadata Statistics</h3>
        <div class='stats-grid'>
            <div class='stat-item'>
                <div class='stat-label'>Files with DAW Data</div>
                <div class='stat-value'>{total_with_daw} / {total_files}</div>
            </div>
    """.format(
        total_with_daw=stats["total_with_daw"],
        total_files=stats["total_files"]
    )
    
    # DAW types breakdown
    if stats["daw_types"]:
        html += "<div class='stat-item'><div class='stat-label'>DAW Types</div><div class='stat-value'>"
        type_list = []
        for daw_type, count in stats["daw_types"].items():
            type_list.append(f"{daw_type}: {count}")
        html += ", ".join(type_list)
        html += "</div></div>"
    
    if stats["avg_notes_per_track"] > 0:
        html += """
            <div class='stat-item'>
                <div class='stat-label'>Avg Notes per Track</div>
                <div class='stat-value'>{:.1f}</div>
            </div>
        """.format(stats["avg_notes_per_track"])
    
    html += """
        </div>
    </div>
    """
    
    return html


def render_html_report(
    metrics_path: Path,
    summary_csv_path: Path,
    output_path: Path,
    test_matrix_path: Path = None,
    files_manifest_path: Optional[Path] = None,
    include_daw_stats: bool = True
):
    """Generate HTML report."""
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    
    summary_df = pd.read_csv(summary_csv_path)
    
    # Load test matrix for thresholds
    thresholds_info = ""
    if test_matrix_path and test_matrix_path.exists():
        with open(test_matrix_path, 'r') as f:
            test_config = yaml.safe_load(f)
        thresholds = test_config.get("thresholds", {})
        thresholds_info = f"<h3>Thresholds</h3><pre>{json.dumps(thresholds, indent=2)}</pre>"
    
    # Build pass/fail summary with modern design
    pass_fail = metrics.get("pass_fail", {})
    
    # Calculate overall pass rate
    total_checks = 0
    passed_checks = 0
    
    # Recall table (per-severity)
    recall_rows = []
    for severity in ["mild", "moderate", "severe"]:
        if severity in pass_fail:
            pf_data = pass_fail[severity]
            row_data = {"severity": severity.capitalize()}
            for k in [1, 5, 10]:
                k_data = pf_data.get(f"recall_at_{k}", {})
                passed = k_data.get("passed", False)
                actual = k_data.get("actual", 0.0)
                threshold = k_data.get("threshold", 0.0)
                total_checks += 1
                if passed:
                    passed_checks += 1
                row_data[f"recall_{k}"] = {
                    "passed": passed,
                    "actual": actual,
                    "threshold": threshold
                }
            recall_rows.append(row_data)
    
    # Similarity table (per-severity)
    similarity_rows = []
    for severity in ["mild", "moderate", "severe"]:
        if severity in pass_fail and "similarity" in pass_fail[severity]:
            sim_data = pass_fail[severity]["similarity"]
            passed = sim_data.get("passed", False)
            actual = sim_data.get("actual", 0.0)
            threshold = sim_data.get("threshold", 0.0)
            total_checks += 1
            if passed:
                passed_checks += 1
            similarity_rows.append({
                "severity": severity.capitalize(),
                "passed": passed,
                "actual": actual,
                "threshold": threshold
            })
    
    # Latency table (overall)
    latency_rows = []
    if "overall" in pass_fail and "latency" in pass_fail["overall"]:
        latency_data = pass_fail["overall"]["latency"]
        
        mean_data = latency_data.get("mean_ms", {})
        mean_passed = mean_data.get("passed", False)
        total_checks += 1
        if mean_passed:
            passed_checks += 1
        latency_rows.append({
            "metric": "Mean Latency",
            "passed": mean_passed,
            "actual": mean_data.get('actual', 0.0),
            "threshold": mean_data.get('threshold', 0.0),
            "unit": "ms"
        })
        
        p95_data = latency_data.get("p95_ms", {})
        p95_passed = p95_data.get("passed", False)
        total_checks += 1
        if p95_passed:
            passed_checks += 1
        latency_rows.append({
            "metric": "P95 Latency",
            "passed": p95_passed,
            "actual": p95_data.get('actual', 0.0),
            "threshold": p95_data.get('threshold', 0.0),
            "unit": "ms"
        })
    
    overall_pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    # Determine overall status color - Match image: Orange for WARNING
    status_color = "#10b981" if overall_pass_rate >= 80 else "#f59e0b" if overall_pass_rate >= 50 else "#f87171"
    status_text = "PASS" if overall_pass_rate >= 80 else "WARNING" if overall_pass_rate >= 50 else "FAIL"
    
    # Build recall table HTML - Match image: "Recall Metrics" with columns: Metric, Recall@1, Recall@5, Recall@10
    recall_table_html = ""
    if recall_rows:
        recall_table_html = "<div class='metric-card'><h3 class='card-title'>Recall Metrics</h3><table class='data-table'><thead><tr><th>Metric</th><th>Recall@1</th><th>Recall@5</th><th>Recall@10</th></tr></thead><tbody>"
        for row in recall_rows:
            recall_1_data = row["recall_1"]
            recall_5_data = row["recall_5"]
            recall_10_data = row["recall_10"]
            status_icon_1 = "✓" if recall_1_data["passed"] else "✗"
            status_icon_5 = "✓" if recall_5_data["passed"] else "✗"
            status_icon_10 = "✓" if recall_10_data["passed"] else "✗"
            recall_table_html += f"<tr><td class='severity-cell'>{row['severity']}</td><td class='metric-value-large'>{recall_1_data['actual']:.3f} <span class='status-badge-small'>{status_icon_1}</span></td><td class='metric-value-large'>{recall_5_data['actual']:.3f} <span class='status-badge-small'>{status_icon_5}</span></td><td class='metric-value-large'>{recall_10_data['actual']:.3f} <span class='status-badge-small'>{status_icon_10}</span></td></tr>"
        recall_table_html += "</tbody></table></div>"
    
    # Build similarity table HTML - Match image: "Similarity Metrics" with columns: Metric, Mean Similarity, Threshold, Status
    similarity_table_html = ""
    if similarity_rows:
        similarity_table_html = "<div class='metric-card'><h3 class='card-title'>Similarity Metrics</h3><table class='data-table'><thead><tr><th>Metric</th><th>Mean Similarity</th><th>Threshold</th><th>Status</th></tr></thead><tbody>"
        for row in similarity_rows:
            status_class = "status-pass" if row["passed"] else "status-fail"
            status_icon = "✓" if row["passed"] else "✗"
            similarity_table_html += f"<tr><td class='severity-cell'>{row['severity']}</td><td class='metric-value-large'>{row['actual']:.3f}</td><td class='metric-threshold-large'>{row['threshold']:.3f}</td><td class='{status_class}'><span class='status-badge'>{status_icon}</span></td></tr>"
        similarity_table_html += "</tbody></table></div>"
    
    # Build latency table HTML - Match image: "Latency Metrics" with columns: Metric, Value, Threshold, Status
    latency_table_html = ""
    if latency_rows:
        latency_table_html = "<div class='metric-card'><h3 class='card-title'>Latency Metrics</h3><table class='data-table'><thead><tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr></thead><tbody>"
        for row in latency_rows:
            status_class = "status-pass" if row["passed"] else "status-fail"
            status_icon = "✓" if row["passed"] else "✗"
            latency_table_html += f"<tr><td class='metric-name'>{row['metric']}</td><td class='metric-value-large'>{row['actual']:.1f}{row['unit']}</td><td class='metric-threshold-large'>{row['threshold']:.1f}{row['unit']}</td><td class='{status_class}'><span class='status-badge'>{status_icon}</span></td></tr>"
        latency_table_html += "</tbody></table></div>"
    
    # Build per-transform table HTML - Match image: "Per-Transform Analysis" with columns: Transform, Queries, Recall@1, Recall@5, Recall@10, Mean Similarity, Mean Latency
    per_transform_html = ""
    per_transform_data = metrics.get('per_transform', {})
    if per_transform_data:
        per_transform_html = "<div class='metric-card'><h3 class='card-title'>Per-Transform Analysis</h3><table class='data-table transform-table'><thead><tr><th>Transform</th><th>Queries</th><th>Recall@1</th><th>Recall@5</th><th>Recall@10</th><th>Mean Similarity</th><th>Mean Latency</th></tr></thead><tbody>"
        for transform_type, data in per_transform_data.items():
            per_transform_html += f"""<tr>
                <td class='transform-name'>{transform_type}</td>
                <td class='metric-count'>{data.get('count', 0)}</td>
                <td class='metric-value'>{data.get('recall', {}).get('recall_at_1', 0.0):.3f}</td>
                <td class='metric-value'>{data.get('recall', {}).get('recall_at_5', 0.0):.3f}</td>
                <td class='metric-value'>{data.get('recall', {}).get('recall_at_10', 0.0):.3f}</td>
                <td class='metric-value'>{data.get('similarity', {}).get('mean_similarity_correct', 0.0):.3f}</td>
                <td class='metric-value'>{data.get('latency', {}).get('mean_latency_ms', 0.0):.1f}ms</td>
            </tr>"""
        per_transform_html += "</tbody></table></div>"
    
    # Build summary table HTML - Match image: "Detailed Test Results"
    summary_table_html = ""
    if not summary_df.empty:
        # Format the summary table to match the image format
        summary_table_html = "<div class='metric-card'><h3 class='card-title'>Detailed Test Results</h3><table class='data-table'><thead><tr><th>Metric</th><th>Queries</th><th>Recall@1</th><th>Recall@5</th><th>Recall@10</th><th>Mean Rank</th><th>Mean Similarity</th><th>Mean Latency</th></tr></thead><tbody>"
        for _, row in summary_df.iterrows():
            summary_table_html += f"""<tr>
                <td class='severity-cell'>{row.get('severity', 'N/A')}</td>
                <td class='metric-count'>{int(row.get('count', 0))}</td>
                <td class='metric-value'>{row.get('recall_at_1', 0.0):.6f}</td>
                <td class='metric-value'>{row.get('recall_at_5', 0.0):.6f}</td>
                <td class='metric-value'>{row.get('recall_at_10', 0.0):.6f}</td>
                <td class='metric-value'>{row.get('mean_rank', 0.0):.1f}</td>
                <td class='metric-value'>{row.get('mean_similarity', 0.0):.6f}</td>
                <td class='metric-value'>{row.get('mean_latency_ms', 0.0):.6f}</td>
            </tr>"""
        summary_table_html += "</tbody></table></div>"
    
    # Get overall metrics for display
    overall_metrics = metrics.get('overall', {})
    overall_recall = overall_metrics.get('recall', {})
    overall_similarity = overall_metrics.get('similarity', {})
    overall_rank = overall_metrics.get('rank', {})
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Audio Fingerprint Robustness Report</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #f3f4f6;
                color: #1f2937;
                line-height: 1.6;
                padding: 20px;
                min-height: 100vh;
            }}
            
            .report-container {{
                max-width: 1400px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                overflow: hidden;
            }}
            
            .report-header {{
                background: linear-gradient(to right, #4c1d95 0%, #5b21b6 50%, #6366f1 100%);
                color: #ffffff;
                padding: 40px;
                text-align: center;
            }}
            
            .report-header h1 {{
                font-size: 2.5em;
                font-weight: 700;
                margin-bottom: 10px;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }}
            
            .report-header .subtitle {{
                font-size: 1.1em;
                opacity: 0.95;
                margin-bottom: 20px;
            }}
            
            .report-header .meta-info {{
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}
            
            .meta-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.95em;
            }}
            
            .status-banner {{
                background: #ffffff;
                color: #374151;
                padding: 20px 40px;
                text-align: center;
                font-size: 1.3em;
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                margin: 20px auto;
                max-width: 600px;
            }}
            
            .status-banner .pass-rate {{
                font-size: 1.5em;
                font-weight: 700;
                color: #374151;
            }}
            
            .status-icon {{
                width: 24px;
                height: 24px;
                border-radius: 50%;
                border: 2px solid #374151;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                color: #374151;
                flex-shrink: 0;
            }}
            
            .status-banner.pass .status-icon {{
                border-color: #374151;
                color: #374151;
            }}
            
            .status-banner.warning .status-icon {{
                border-color: #374151;
                color: #374151;
            }}
            
            .status-banner.fail .status-icon {{
                border-color: #374151;
                color: #374151;
            }}
            
            .report-content {{
                padding: 40px;
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }}
            
            .summary-card {{
                background: linear-gradient(135deg, #e9d5ff 0%, #ddd6fe 100%);
                border-radius: 12px;
                padding: 24px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            
            .summary-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }}
            
            .summary-card .value {{
                font-size: 2.5em;
                font-weight: 700;
                color: #6b21a8;
                margin-bottom: 8px;
            }}
            
            .summary-card .label {{
                font-size: 0.95em;
                color: #d1d5db;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .metric-card {{
                background: #ffffff;
                border-radius: 12px;
                padding: 28px;
                margin-bottom: 30px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border: 1px solid #e5e7eb;
            }}
            
            .card-title {{
                font-size: 1.4em;
                font-weight: 600;
                color: #374151;
                margin-bottom: 20px;
                padding-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .card-title img {{
                width: 24px;
                height: 24px;
                object-fit: contain;
                flex-shrink: 0;
                border-bottom: 2px solid #e5e7eb;
            }}
            
            .data-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            
            .data-table thead {{
                background: linear-gradient(to right, #4c1d95 0%, #5b21b6 50%, #6366f1 100%);
                color: #ffffff;
            }}
            
            .data-table th {{
                padding: 14px 16px;
                text-align: left;
                font-weight: 600;
                font-size: 0.95em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .data-table td {{
                padding: 14px 16px;
                border-bottom: 1px solid #e5e7eb;
            }}
            
            .data-table tbody tr {{
                transition: background-color 0.2s;
            }}
            
            .data-table tbody tr:hover {{
                background-color: #f9fafb;
            }}
            
            .data-table tbody tr:last-child td {{
                border-bottom: none;
            }}
            
            .status-pass {{
                color: #10b981;
                font-weight: 600;
            }}
            
            .status-fail {{
                color: #f87171;
                font-weight: 600;
            }}
            
            .status-badge {{
                display: inline-block;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: currentColor;
                color: #ffffff;
                text-align: center;
                line-height: 24px;
                font-size: 0.85em;
                margin-right: 8px;
                vertical-align: middle;
            }}
            
            .status-badge-small {{
                display: inline-block;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #10b981;
                color: #ffffff;
                text-align: center;
                line-height: 18px;
                font-size: 0.75em;
                margin-left: 8px;
                vertical-align: middle;
            }}
            
            .status-pass .status-badge {{
                background: #10b981;
            }}
            
            .status-fail .status-badge {{
                background: #f87171;
            }}
            
            .status-fail .status-badge-small {{
                background: #f87171;
            }}
            
            .severity-cell {{
                font-weight: 600;
                color: #374151;
                text-transform: capitalize;
            }}
            
            .metric-value {{
                font-weight: 500;
                color: #1f2937;
            }}
            
            .metric-value-large {{
                font-size: 1.1em;
                font-weight: 600;
                color: #1f2937;
            }}
            
            .metric-threshold {{
                font-size: 0.85em;
                color: #6b7280;
            }}
            
            .metric-threshold-large {{
                font-size: 0.95em;
                color: #6b7280;
            }}
            
            .metric-count {{
                text-align: center;
                font-weight: 600;
                color: #667eea;
            }}
            
            .transform-name {{
                font-weight: 600;
                color: #374151;
            }}
            
            .metric-name {{
                font-weight: 600;
                color: #374151;
            }}
            
            .plots-section {{
                margin: 40px 0;
            }}
            
            .plots-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 24px;
                margin-top: 20px;
            }}
            
            @media (max-width: 1200px) {{
                .plots-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            .plot-card {{
                background: #ffffff;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border: 1px solid #e5e7eb;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }}
            
            .plot-card img {{
                width: 100%;
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                display: block;
                margin: 0 auto;
            }}
            
            .plot-title {{
                font-size: 1.1em;
                font-weight: 600;
                color: #374151;
                margin-bottom: 12px;
                text-align: center;
            }}
            
            .table-wrapper {{
                overflow-x: auto;
            }}
            
            .overall-metrics {{
                background: linear-gradient(135deg, #f6f8fb 0%, #e9ecef 100%);
                border-radius: 12px;
                padding: 24px;
                margin-top: 30px;
            }}
            
            .overall-metrics h3 {{
                font-size: 1.3em;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 16px;
            }}
            
            .overall-metrics pre {{
                background: #ffffff;
                padding: 16px;
                border-radius: 8px;
                overflow-x: auto;
                font-size: 0.9em;
                border: 1px solid #e5e7eb;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-top: 16px;
            }}
            
            .stat-item {{
                background: #f9fafb;
                padding: 16px;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }}
            
            .stat-label {{
                font-size: 0.9em;
                color: #6b7280;
                margin-bottom: 8px;
            }}
            
            .stat-value {{
                font-size: 1.5em;
                font-weight: 600;
                color: #1f2937;
            }}
            
            @media (max-width: 768px) {{
                .report-header h1 {{
                    font-size: 1.8em;
                }}
                
                .report-content {{
                    padding: 20px;
                }}
                
                .summary-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .plots-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .data-table {{
                    font-size: 0.9em;
                }}
                
                .data-table th,
                .data-table td {{
                    padding: 10px 8px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="report-header">
                <h1> Audio Fingerprint Robustness Report</h1>
                <div class="subtitle">Comprehensive Analysis & Performance Metrics</div>
                <div class="meta-info">
                    <span>{datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</span>
                    <span style="margin: 0 15px;">|</span>
                    <span>{metrics['summary'].get('total_queries', 0)} Total Queries</span>
                    <span style="margin: 0 15px;">|</span>
                    <span>{len(metrics['summary'].get('transform_types', []))} Transform Types</span>
                </div>
            </div>
            
            <div class="status-banner {'pass' if overall_pass_rate >= 80 else 'warning' if overall_pass_rate >= 50 else 'fail'}">
                <span class="status-icon">✓</span>
                <span>Overall Status:</span>
                <span class="pass-rate">{overall_pass_rate:.1f}%</span>
                <span>({status_text})</span>
            </div>
            
            <div class="report-content">
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="value">{metrics['summary'].get('total_queries', 0)}</div>
                        <div class="label">Total Queries</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{overall_recall.get('recall_at_1', 0.0):.1%}</div>
                        <div class="label">Overall Recall@1</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{overall_similarity.get('mean_similarity_correct', 0.0):.3f}</div>
                        <div class="label">Mean Similarity</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{overall_rank.get('mean_rank', 0.0):.1f}</div>
                        <div class="label">Mean Rank</div>
                    </div>
                </div>
                
                <h2 style="font-size: 1.8em; font-weight: 600; color: #374151; margin: 40px 0 20px 0; padding-bottom: 12px; border-bottom: 2px solid #e5e7eb;">Pass/Fail Status</h2>
                
                {recall_table_html}
                {similarity_table_html}
                {latency_table_html}
                
                {per_transform_html}
                
                <div class="plots-section">
                    <h2 style="font-size: 1.8em; font-weight: 600; color: #374151; margin: 40px 0 20px 0; padding-bottom: 12px; border-bottom: 2px solid #e5e7eb;">Visualizations</h2>
                    <div class="plots-grid">
                        <div class="plot-card">
                            <div class="plot-title">Recall@K by Transform Severity</div>
                            <img src="plots/recall_by_severity.png" alt="Recall@K by Transform Severity" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div style="display:none; padding:40px; text-align:center; color:#6b7280;">Chart not available</div>
                        </div>
                        <div class="plot-card">
                            <div class="plot-title">Similarity Score by Severity</div>
                            <img src="plots/similarity_by_severity.png" alt="Similarity Score by Severity" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div style="display:none; padding:40px; text-align:center; color:#6b7280;">Chart not available</div>
                        </div>
                        <div class="plot-card">
                            <div class="plot-title">Recall@K by Transform Type</div>
                            <img src="plots/recall_by_transform.png" alt="Recall@K by Transform Type" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div style="display:none; padding:40px; text-align:center; color:#6b7280;">Chart not available</div>
                        </div>
                        <div class="plot-card">
                            <div class="plot-title">Latency by Transform Type</div>
                            <img src="plots/latency_by_transform.png" alt="Latency by Transform Type" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div style="display:none; padding:40px; text-align:center; color:#6b7280;">Chart not available</div>
                        </div>
                    </div>
                </div>
                
                {summary_table_html}
                
                {render_daw_statistics_section(calculate_daw_statistics(files_manifest_path)) if include_daw_stats and files_manifest_path else ""}
                
                
                
                <div class="overall-metrics">
                    <h3>Overall Metrics</h3>
                    <pre>{json.dumps(metrics['overall'], indent=2, default=str)}</pre>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"Generated HTML report: {output_path}")


def package_report(report_dir: Path, output_zip: Path):
    """Package report directory into ZIP file."""
    import zipfile
    
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in report_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(report_dir)
                zipf.write(file_path, arcname)
    
    logger.info(f"Packaged report to {output_zip}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate final report")
    parser.add_argument("--metrics", type=Path, required=True, help="Metrics JSON file")
    parser.add_argument("--summary", type=Path, required=True, help="Summary CSV file")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--test-matrix", type=Path, help="Test matrix YAML (for thresholds)")
    parser.add_argument("--package", action="store_true", help="Create ZIP package")
    
    args = parser.parse_args()
    
    # Generate plots
    generate_plots(args.metrics, args.output, args.test_matrix)
    
    # Generate HTML
    html_path = args.output / "report.html"
    render_html_report(args.metrics, args.summary, html_path, args.test_matrix)
    
    # Package if requested
    if args.package:
        zip_path = args.output.parent / f"{args.output.name}.zip"
        package_report(args.output, zip_path)
