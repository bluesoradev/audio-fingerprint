"""Generate final report (HTML, plots, etc.)."""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import yaml
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_plots(metrics_path: Path, output_dir: Path, test_matrix_path: Path = None):
    """Generate visualization plots."""
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (10, 6)
    
    # Load thresholds if available
    similarity_thresholds = {}
    if test_matrix_path and test_matrix_path.exists():
        with open(test_matrix_path, 'r') as f:
            test_config = yaml.safe_load(f)
        thresholds = test_config.get("thresholds", {})
        similarity_thresholds = thresholds.get("similarity", {})
    
    # Plot 1: Recall@K by severity
    per_severity = metrics.get("per_severity", {})
    if per_severity:
        fig, ax = plt.subplots()
        
        severities = []
        recall_1 = []
        recall_5 = []
        recall_10 = []
        
        for severity in ["mild", "moderate", "severe", "none"]:
            if severity in per_severity:
                severities.append(severity)
                rec = per_severity[severity]["recall"]
                recall_1.append(rec.get("recall_at_1", 0.0))
                recall_5.append(rec.get("recall_at_5", 0.0))
                recall_10.append(rec.get("recall_at_10", 0.0))
        
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
        
        plt.tight_layout()
        plt.savefig(plots_dir / "recall_by_severity.png", dpi=150)
        plt.close()
    
    # Plot 2: Similarity score distribution by severity
    if per_severity:
        fig, ax = plt.subplots()
        severities = []
        similarity_scores = []
        thresholds_list = []
        
        for severity in ["mild", "moderate", "severe"]:
            if severity in per_severity:
                severities.append(severity)
                sim_data = per_severity[severity]["similarity"]
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
            plt.tight_layout()
            plt.savefig(plots_dir / "similarity_by_severity.png", dpi=150)
            plt.close()
    
    # Plot 3: Recall by transform type
    if per_transform:
        fig, ax = plt.subplots(figsize=(14, 6))
        transform_types = list(per_transform.keys())
        recall_1 = [per_transform[t]["recall"].get("recall_at_1", 0.0) for t in transform_types]
        recall_5 = [per_transform[t]["recall"].get("recall_at_5", 0.0) for t in transform_types]
        recall_10 = [per_transform[t]["recall"].get("recall_at_10", 0.0) for t in transform_types]
        
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
        plt.tight_layout()
        plt.savefig(plots_dir / "recall_by_transform.png", dpi=150)
        plt.close()
    
    # Plot 4: Latency by transform type
    per_transform = metrics.get("per_transform", {})
    if per_transform:
        fig, ax = plt.subplots()
        
        transform_types = []
        latencies = []
        
        for transform_type, data in per_transform.items():
            transform_types.append(transform_type)
            latencies.append(data["latency"]["mean_latency_ms"])
        
        ax.bar(transform_types, latencies)
        ax.set_xlabel('Transform Type')
        ax.set_ylabel('Mean Latency (ms)')
        ax.set_title('Processing Latency by Transform Type')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(plots_dir / "latency_by_transform.png", dpi=150)
        plt.close()
    
    logger.info(f"Generated plots in {plots_dir}")


def render_html_report(
    metrics_path: Path,
    summary_csv_path: Path,
    output_path: Path,
    test_matrix_path: Path = None
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
    
    # Build pass/fail summary
    pass_fail = metrics.get("pass_fail", {})
    
    # Recall table (per-severity)
    pf_html = "<h3>Pass/Fail Status</h3>"
    pf_html += "<h4>Recall Metrics</h4><table border='1'><tr><th>Severity</th><th>Recall@1</th><th>Recall@5</th><th>Recall@10</th></tr>"
    for severity in ["mild", "moderate", "severe"]:
        if severity in pass_fail:
            pf_data = pass_fail[severity]
            pf_html += f"<tr><td>{severity}</td>"
            for k in [1, 5, 10]:
                k_data = pf_data.get(f"recall_at_{k}", {})
                passed = k_data.get("passed", False)
                actual = k_data.get("actual", 0.0)
                threshold = k_data.get("threshold", 0.0)
                status = "✅ PASS" if passed else "❌ FAIL"
                pf_html += f"<td>{status}<br/>{actual:.3f} / {threshold:.3f}</td>"
            pf_html += "</tr>"
    pf_html += "</table>"
    
    # Similarity table (per-severity)
    pf_html += "<h4>Similarity Metrics</h4><table border='1'><tr><th>Severity</th><th>Mean Similarity</th><th>Threshold</th><th>Status</th></tr>"
    for severity in ["mild", "moderate", "severe"]:
        if severity in pass_fail and "similarity" in pass_fail[severity]:
            sim_data = pass_fail[severity]["similarity"]
            passed = sim_data.get("passed", False)
            actual = sim_data.get("actual", 0.0)
            threshold = sim_data.get("threshold", 0.0)
            status = "✅ PASS" if passed else "❌ FAIL"
            pf_html += f"<tr><td>{severity}</td><td>{actual:.3f}</td><td>{threshold:.3f}</td><td>{status}</td></tr>"
    pf_html += "</table>"
    
    # Latency table (overall)
    if "overall" in pass_fail and "latency" in pass_fail["overall"]:
        latency_data = pass_fail["overall"]["latency"]
        pf_html += "<h4>Latency Metrics</h4><table border='1'><tr><th>Metric</th><th>Actual</th><th>Threshold</th><th>Status</th></tr>"
        
        mean_data = latency_data.get("mean_ms", {})
        mean_passed = mean_data.get("passed", False)
        pf_html += f"<tr><td>Mean Latency</td><td>{mean_data.get('actual', 0.0):.1f}ms</td><td>{mean_data.get('threshold', 0.0):.1f}ms</td><td>{'✅ PASS' if mean_passed else '❌ FAIL'}</td></tr>"
        
        p95_data = latency_data.get("p95_ms", {})
        p95_passed = p95_data.get("passed", False)
        pf_html += f"<tr><td>P95 Latency</td><td>{p95_data.get('actual', 0.0):.1f}ms</td><td>{p95_data.get('threshold', 0.0):.1f}ms</td><td>{'✅ PASS' if p95_passed else '❌ FAIL'}</td></tr>"
        
        pf_html += "</table>"
    
    # Build summary table
    summary_html = summary_df.to_html(classes='table', table_id='summary-table', escape=False)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio Fingerprint Robustness Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #666; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .plots {{ margin: 20px 0; }}
            .plots img {{ max-width: 100%; height: auto; margin: 10px; }}
        </style>
    </head>
    <body>
        <h1>Audio Fingerprint Robustness Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Executive Summary</h2>
        <p>Total queries: {metrics['summary']['total_queries']}</p>
        <p>Transform types tested: {', '.join(metrics['summary']['transform_types'])}</p>
        
        {pf_html}
        
        <h2>Detailed Metrics</h2>
        {summary_html}
        
        {thresholds_info}
        
        <h2>Per-Transform Analysis</h2>
        <table border='1'>
            <tr>
                <th>Transform</th>
                <th>Count</th>
                <th>Recall@1</th>
                <th>Recall@5</th>
                <th>Recall@10</th>
                <th>Mean Similarity</th>
                <th>Mean Latency (ms)</th>
            </tr>
            {''.join([
                f'''<tr>
                    <td>{transform_type}</td>
                    <td>{data.get('count', 0)}</td>
                    <td>{data.get('recall', {}).get('recall_at_1', 0.0):.3f}</td>
                    <td>{data.get('recall', {}).get('recall_at_5', 0.0):.3f}</td>
                    <td>{data.get('recall', {}).get('recall_at_10', 0.0):.3f}</td>
                    <td>{data.get('similarity', {}).get('mean_similarity_correct', 0.0):.3f}</td>
                    <td>{data.get('latency', {}).get('mean_latency_ms', 0.0):.1f}</td>
                </tr>'''
                for transform_type, data in metrics.get('per_transform', {}).items()
            ])}
        </table>
        
        <h2>Visualizations</h2>
        <div class="plots">
            <img src="plots/recall_by_severity.png" alt="Recall by Severity" />
            <img src="plots/similarity_by_severity.png" alt="Similarity by Severity" />
            <img src="plots/recall_by_transform.png" alt="Recall by Transform Type" />
            <img src="plots/latency_by_transform.png" alt="Latency by Transform" />
        </div>
        
        <h2>Overall Metrics</h2>
        <pre>{json.dumps(metrics['overall'], indent=2, default=str)}</pre>
    </body>
    </html>
    """
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
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
