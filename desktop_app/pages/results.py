"""
Results page showing fingerprint robustness experiment metrics.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QGroupBox, QLineEdit, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from pathlib import Path
import json
from datetime import datetime
from desktop_app.pages.dashboard import LineChartWidget


class RankDistributionChart(QWidget):
    """Line chart showing rank distribution."""
    
    def __init__(self, rank_data=None):
        super().__init__()
        self.rank_data = rank_data or {}  # {rank: percentage}
        self.setMinimumHeight(200)
    
    def set_data(self, rank_data):
        """Set rank distribution data."""
        self.rank_data = rank_data
        self.update()
    
    def paintEvent(self, event):
        """Draw the rank distribution line chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        margin_left = 50
        margin_right = 20
        margin_top = 30
        margin_bottom = 40
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        # Background
        painter.setBrush(QBrush(QColor(30, 30, 30)))  # #1e1e1e
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, width, height, 4, 4)
        
        if not self.rank_data:
            # Draw placeholder text
            painter.setPen(QPen(QColor(156, 163, 175)))  # #9ca3af
            font = QFont("Arial", 12)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No rank distribution data available")
            return
        
        # Get max rank and max percentage
        max_rank = max(self.rank_data.keys()) if self.rank_data else 10
        max_percentage = max(self.rank_data.values()) if self.rank_data else 100
        
        # Draw axes
        painter.setPen(QPen(QColor(61, 61, 61), 1))  # #3d3d3d
        # X-axis
        painter.drawLine(margin_left, height - margin_bottom, width - margin_right, height - margin_bottom)
        # Y-axis
        painter.drawLine(margin_left, margin_top, margin_left, height - margin_bottom)
        
        # Draw Y-axis labels (0 to max_percentage)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        font = QFont("Arial", 9)
        painter.setFont(font)
        for i in range(6):
            y_val = max_percentage * (1 - i / 5)
            y_pos = margin_top + (chart_height * i / 5)
            label = f"{y_val:.0f}%"
            label_width = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(margin_left - label_width - 10, int(y_pos + 5), label)
            # Grid line
            painter.setPen(QPen(QColor(61, 61, 61), 1))
            painter.drawLine(margin_left, int(y_pos), width - margin_right, int(y_pos))
            painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Draw X-axis labels (ranks)
        for rank in range(1, min(max_rank + 1, 11)):
            x_pos = margin_left + (chart_width * (rank - 1) / (max_rank - 1 if max_rank > 1 else 1))
            label = str(rank)
            label_width = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(int(x_pos - label_width / 2), height - margin_bottom + 20, label)
        
        # Draw line chart
        if len(self.rank_data) > 1:
            points = []
            for rank in sorted(self.rank_data.keys()):
                x = margin_left + (chart_width * (rank - 1) / (max_rank - 1 if max_rank > 1 else 1))
                y = height - margin_bottom - (chart_height * self.rank_data[rank] / max_percentage)
                points.append((x, y))
            
            # Draw line
            painter.setPen(QPen(QColor(96, 165, 250), 2))  # #60a5fa
            for i in range(len(points) - 1):
                painter.drawLine(int(points[i][0]), int(points[i][1]), 
                               int(points[i+1][0]), int(points[i+1][1]))
            
            # Draw points
            painter.setBrush(QBrush(QColor(96, 165, 250)))
            painter.setPen(QPen(QColor(96, 165, 250), 1))
            for x, y in points:
                painter.drawEllipse(int(x - 4), int(y - 4), 8, 8)


class ResultsPage(QWidget):
    """Fingerprint robustness experiment results page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.reports_dir = project_root / "reports"
        self.current_metrics = None
        self.init_ui()
        self.load_results()
        
        # Auto-refresh every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_results)
        self.refresh_timer.start(5000)
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        title = QLabel("Results")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)
        
        # Overall Metrics (Recall@K)
        metrics_group = QGroupBox("Overall Fingerprint Robustness Metrics")
        metrics_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        metrics_layout = QVBoxLayout(metrics_group)
        
        subtitle = QLabel("Recall@K metrics showing fingerprint matching performance across all transforms.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 15px;")
        metrics_layout.addWidget(subtitle)
        
        # Recall@K stat cards
        recall_layout = QHBoxLayout()
        recall_layout.setSpacing(15)
        
        self.recall_at_1_card = self._create_metric_card("Recall@1", "0.00", "0%")
        self.recall_at_5_card = self._create_metric_card("Recall@5", "0.00", "0%")
        self.recall_at_10_card = self._create_metric_card("Recall@10", "0.00", "0%")
        self.mean_rank_card = self._create_metric_card("Mean Rank", "N/A", "-")
        
        recall_layout.addWidget(self.recall_at_1_card)
        recall_layout.addWidget(self.recall_at_5_card)
        recall_layout.addWidget(self.recall_at_10_card)
        recall_layout.addWidget(self.mean_rank_card)
        
        metrics_layout.addLayout(recall_layout)
        layout.addWidget(metrics_group)
        
        # Main content area (left + right)
        main_content = QHBoxLayout()
        main_content.setSpacing(20)
        
        # Left side: Per-Transform Breakdown
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        
        # Per-Transform Metrics Table
        transform_group = QGroupBox("Per-Transform Type Performance")
        transform_group.setStyleSheet(metrics_group.styleSheet())
        transform_layout = QVBoxLayout(transform_group)
        
        transform_subtitle = QLabel("Recall@K metrics broken down by transform type.")
        transform_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        transform_layout.addWidget(transform_subtitle)
        
        self.transform_table = QTableWidget()
        self.transform_table.setColumnCount(5)
        self.transform_table.setHorizontalHeaderLabels(["Transform Type", "Recall@1", "Recall@5", "Recall@10", "Mean Similarity"])
        self.transform_table.horizontalHeader().setStretchLastSection(False)
        self.transform_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transform_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.transform_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 10px;
                color: #c8c8c8;
            }
            QTableWidget::item:selected {
                background-color: #427eea;
                color: white;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #ffffff;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #3d3d3d;
                font-weight: bold;
            }
        """)
        self.transform_table.verticalHeader().setVisible(False)
        self.transform_table.setShowGrid(False)
        self.transform_table.setCornerButtonEnabled(False)
        
        # Make columns responsive
        header = self.transform_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Transform Type
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Recall@1
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Recall@5
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Recall@10
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Mean Similarity
        
        transform_layout.addWidget(self.transform_table)
        left_layout.addWidget(transform_group, 1)
        
        main_content.addLayout(left_layout, 1)
        
        # Right side: Charts
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        
        # Rank Distribution Chart
        rank_group = QGroupBox("Rank Distribution")
        rank_group.setStyleSheet(metrics_group.styleSheet())
        rank_layout = QVBoxLayout(rank_group)
        
        rank_subtitle = QLabel("Percentage of correct matches at each rank position.")
        rank_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        rank_layout.addWidget(rank_subtitle)
        
        self.rank_chart = RankDistributionChart()
        rank_layout.addWidget(self.rank_chart)
        right_layout.addWidget(rank_group, 1)
        
        # Similarity Distribution (if available)
        similarity_group = QGroupBox("Similarity Score Distribution")
        similarity_group.setStyleSheet(metrics_group.styleSheet())
        similarity_layout = QVBoxLayout(similarity_group)
        
        similarity_subtitle = QLabel("Distribution of similarity scores for correct matches.")
        similarity_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        similarity_layout.addWidget(similarity_subtitle)
        
        self.similarity_info = QTextEdit()
        self.similarity_info.setReadOnly(True)
        self.similarity_info.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 15px;
                color: #c8c8c8;
                min-height: 150px;
            }
        """)
        similarity_layout.addWidget(self.similarity_info)
        right_layout.addWidget(similarity_group, 1)
        
        main_content.addLayout(right_layout, 1)
        layout.addLayout(main_content, 1)
    
    def _create_metric_card(self, title, value, change):
        """Create a metric card widget."""
        card = QWidget()
        card.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; padding: 15px;")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        card_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        card_layout.addWidget(value_label)
        
        change_label = QLabel(change)
        change_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        card_layout.addWidget(change_label)
        
        card_layout.addStretch()
        return card
    
    def _update_metric_card(self, card, value, change=None):
        """Update a metric card's value."""
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            labels[1].setText(str(value))
            if change is not None and len(labels) >= 3:
                labels[2].setText(str(change))
    
    def load_results(self):
        """Load experiment results from the latest report."""
        # Find latest report directory
        if not self.reports_dir.exists():
            self._show_no_data()
            return
        
        # Get all report directories
        report_dirs = sorted([d for d in self.reports_dir.iterdir() if d.is_dir() and d.name.startswith("run_")], 
                           key=lambda x: x.name, reverse=True)
        
        if not report_dirs:
            self._show_no_data()
            return
        
        # Load metrics from latest report
        latest_report = report_dirs[0]
        metrics_file = latest_report / "metrics.json"
        
        if not metrics_file.exists():
            self._show_no_data()
            return
        
        try:
            with open(metrics_file, 'r') as f:
                self.current_metrics = json.load(f)
            
            self._display_metrics()
        except Exception as e:
            print(f"Error loading metrics: {e}")
            self._show_no_data()
    
    def _show_no_data(self):
        """Show placeholder when no data is available."""
        # Update metric cards
        self._update_metric_card(self.recall_at_1_card, "N/A", "No data")
        self._update_metric_card(self.recall_at_5_card, "N/A", "No data")
        self._update_metric_card(self.recall_at_10_card, "N/A", "No data")
        self._update_metric_card(self.mean_rank_card, "N/A", "No data")
        
        # Clear table
        self.transform_table.setRowCount(0)
        
        # Clear charts
        self.rank_chart.set_data({})
        self.similarity_info.setPlainText("No experiment results available. Run an experiment to see metrics here.")
    
    def _display_metrics(self):
        """Display loaded metrics."""
        if not self.current_metrics:
            return
        
        overall = self.current_metrics.get("overall", {})
        recall = overall.get("recall", {})
        rank = overall.get("rank", {})
        similarity = overall.get("similarity", {})
        
        # Update overall metric cards
        recall_at_1 = recall.get("recall_at_1", 0.0)
        recall_at_5 = recall.get("recall_at_5", 0.0)
        recall_at_10 = recall.get("recall_at_10", 0.0)
        mean_rank = rank.get("mean_rank", 0.0)
        
        self._update_metric_card(self.recall_at_1_card, f"{recall_at_1:.2%}", f"≥90% target")
        self._update_metric_card(self.recall_at_5_card, f"{recall_at_5:.2%}", f"≥95% target")
        self._update_metric_card(self.recall_at_10_card, f"{recall_at_10:.2%}", f"≥98% target")
        self._update_metric_card(self.mean_rank_card, f"{mean_rank:.2f}", "lower is better")
        
        # Update per-transform table
        per_transform = self.current_metrics.get("per_transform", {})
        self.transform_table.setRowCount(len(per_transform))
        
        for i, (transform_type, data) in enumerate(sorted(per_transform.items())):
            transform_recall = data.get("recall", {})
            transform_similarity = data.get("similarity", {})
            
            self.transform_table.setItem(i, 0, QTableWidgetItem(transform_type))
            self.transform_table.setItem(i, 1, QTableWidgetItem(f"{transform_recall.get('recall_at_1', 0.0):.2%}"))
            self.transform_table.setItem(i, 2, QTableWidgetItem(f"{transform_recall.get('recall_at_5', 0.0):.2%}"))
            self.transform_table.setItem(i, 3, QTableWidgetItem(f"{transform_recall.get('recall_at_10', 0.0):.2%}"))
            self.transform_table.setItem(i, 4, QTableWidgetItem(f"{transform_similarity.get('mean_similarity_correct', 0.0):.3f}"))
            
            self.transform_table.setRowHeight(i, 40)
        
        # Update rank distribution chart
        rank_dist = rank.get("distribution", {})
        if rank_dist:
            self.rank_chart.set_data(rank_dist)
        
        # Update similarity info
        mean_sim = similarity.get("mean_similarity_correct", 0.0)
        min_sim = similarity.get("min_similarity_correct", 0.0)
        max_sim = similarity.get("max_similarity_correct", 0.0)
        std_sim = similarity.get("std_similarity_correct", 0.0)
        
        similarity_text = f"""Mean Similarity: {mean_sim:.3f}
Min Similarity: {min_sim:.3f}
Max Similarity: {max_sim:.3f}
Std Deviation: {std_sim:.3f}

Typical range: 0.7-0.95
Higher values indicate better fingerprint matching."""
        
        self.similarity_info.setPlainText(similarity_text)
