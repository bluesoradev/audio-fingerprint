"""
Results page showing experiment runs and metrics.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from pathlib import Path
import json
from datetime import datetime


class ResultsPage(QWidget):
    """Experiment results page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.reports_dir = project_root / "reports"
        self.init_ui()
        self.load_results()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Experiment Results")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter dropdown
        filter_label = QLabel("All Statuses")
        filter_label.setStyleSheet("color: #9ca3af; font-size: 14px;")
        header_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Statuses", "Completed", "Running", "Failed"])
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px 12px;
                color: #c8c8c8;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid #427eea;
            }
        """)
        header_layout.addWidget(self.filter_combo)
        
        # Sort dropdown
        sort_label = QLabel("Newest")
        sort_label.setStyleSheet("color: #9ca3af; font-size: 14px; margin-left: 15px;")
        header_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Newest", "Oldest", "Status"])
        self.sort_combo.setStyleSheet(self.filter_combo.styleSheet())
        header_layout.addWidget(self.sort_combo)
        
        # Download button
        download_btn = QPushButton("📥 Download Report")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                margin-left: 15px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        header_layout.addWidget(download_btn)
        
        layout.addLayout(header_layout)
        
        # Recent Experiment Runs
        table_group = QGroupBox("Recent Experiment Runs")
        table_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        table_layout = QVBoxLayout(table_group)
        
        subtitle = QLabel("Overview of the latest experiment outcomes.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        table_layout.addWidget(subtitle)
        
        self.runs_table = QTableWidget()
        self.runs_table.setColumnCount(5)
        self.runs_table.setHorizontalHeaderLabels(["Run ID", "Status", "Metrics", "Date", "Actions"])
        self.runs_table.horizontalHeader().setStretchLastSection(True)
        self.runs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.runs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.runs_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                padding: 8px;
                color: #c8c8c8;
            }
            QTableWidget::item:selected {
                background-color: #427eea;
                color: white;
            }
        """)
        table_layout.addWidget(self.runs_table)
        layout.addWidget(table_group)
        
        # Charts section
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(15)
        
        # Recall by Audio Transform chart
        recall_chart_group = QGroupBox("Recall by Audio Transform")
        recall_chart_group.setStyleSheet(table_group.styleSheet())
        recall_chart_layout = QVBoxLayout(recall_chart_group)
        recall_subtitle = QLabel("Performance of different audio transformation methods.")
        recall_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        recall_chart_layout.addWidget(recall_subtitle)
        recall_placeholder = QLabel("Bar Chart: Average recall scores for different audio transformations")
        recall_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recall_placeholder.setMinimumHeight(250)
        recall_placeholder.setStyleSheet("background-color: #2d2d2d; border-radius: 4px; color: #9ca3af;")
        recall_chart_layout.addWidget(recall_placeholder)
        charts_layout.addWidget(recall_chart_group, 1)
        
        # Experiment Rank Distribution chart
        rank_chart_group = QGroupBox("Experiment Rank Distribution")
        rank_chart_group.setStyleSheet(table_group.styleSheet())
        rank_chart_layout = QVBoxLayout(rank_chart_group)
        rank_subtitle = QLabel("Frequency of different ranks in experiment outcomes.")
        rank_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        rank_chart_layout.addWidget(rank_subtitle)
        rank_placeholder = QLabel("Line Chart: Frequency of different ranks in experiment outcomes")
        rank_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_placeholder.setMinimumHeight(250)
        rank_placeholder.setStyleSheet("background-color: #2d2d2d; border-radius: 4px; color: #9ca3af;")
        rank_chart_layout.addWidget(rank_placeholder)
        charts_layout.addWidget(rank_chart_group, 1)
        
        layout.addLayout(charts_layout)
        
        layout.addStretch()
    
    def load_results(self):
        """Load experiment results."""
        self.runs_table.setRowCount(0)
        
        if not self.reports_dir.exists():
            return
        
        runs = []
        for run_dir in sorted(self.reports_dir.glob("run_*"), reverse=True):
            metrics_file = run_dir / "metrics.json"
            status = "Running"
            metrics = "N/A"
            
            if metrics_file.exists():
                status = "Completed"
                try:
                    with open(metrics_file, 'r') as f:
                        data = json.load(f)
                        recall = data.get("overall", {}).get("recall", {}).get("recall_at_1", 0)
                        latency = data.get("overall", {}).get("latency", {}).get("mean_ms", 0)
                        metrics = f"Recall@K: {recall:.2f}, Latency: {latency:.0f}ms"
                except:
                    pass
            
            runs.append({
                "id": run_dir.name,
                "status": status,
                "metrics": metrics,
                "date": datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            })
        
        self.runs_table.setRowCount(len(runs))
        for i, run in enumerate(runs):
            self.runs_table.setItem(i, 0, QTableWidgetItem(run["id"]))
            
            status_item = QTableWidgetItem(run["status"])
            if run["status"] == "Completed":
                status_item.setBackground(QColor(16, 185, 129))
                status_item.setForeground(QColor(255, 255, 255))
            elif run["status"] == "Running":
                status_item.setBackground(QColor(66, 126, 234))
                status_item.setForeground(QColor(255, 255, 255))
            elif run["status"] == "Failed":
                status_item.setBackground(QColor(239, 68, 68))
                status_item.setForeground(QColor(255, 255, 255))
            self.runs_table.setItem(i, 1, status_item)
            
            self.runs_table.setItem(i, 2, QTableWidgetItem(run["metrics"]))
            self.runs_table.setItem(i, 3, QTableWidgetItem(run["date"]))
            
            view_btn = QPushButton("👁")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #c8c8c8;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #427eea;
                    color: white;
                }
            """)
            self.runs_table.setCellWidget(i, 4, view_btn)
        
        self.runs_table.resizeColumnsToContents()
