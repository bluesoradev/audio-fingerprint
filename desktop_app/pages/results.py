"""
Results page showing experiment runs and metrics.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QGroupBox, QLineEdit, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from pathlib import Path
import json
from datetime import datetime
from desktop_app.pages.dashboard import BarChartWidget


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
        title = QLabel("Results")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)
        
        # Main content area (left + right)
        main_content = QHBoxLayout()
        main_content.setSpacing(20)
        
        # Left side
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        
        # Results Overview
        overview_group = QGroupBox("Results Overview")
        overview_group.setStyleSheet("""
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
        overview_layout = QVBoxLayout(overview_group)
        overview_subtitle = QLabel("Summary of audio processing workflow results over the last 30 days.")
        overview_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 15px;")
        overview_layout.addWidget(overview_subtitle)
        
        # Metrics grid
        metrics_layout = QHBoxLayout()
        metrics = [
            ("Total Runs", "1,245", "+12%", "#10b981"),
            ("Successful Runs", "1,198", "+10%", "#10b981"),
            ("Failed Runs", "47", "-5%", "#ef4444"),
            ("Avg. Duration", "2m 15s", "+3s", "#10b981"),
        ]
        for label, value, change, color in metrics:
            metric_widget = QWidget()
            metric_widget.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; padding: 10px;")
            metric_layout = QVBoxLayout(metric_widget)
            metric_layout.setSpacing(5)
            
            metric_label = QLabel(label)
            metric_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
            metric_layout.addWidget(metric_label)
            
            value_layout = QHBoxLayout()
            value_label = QLabel(value)
            value_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
            value_layout.addWidget(value_label)
            
            change_label = QLabel(change)
            change_label.setStyleSheet(f"color: {color}; font-size: 12px;")
            value_layout.addWidget(change_label)
            value_layout.addStretch()
            
            metric_layout.addLayout(value_layout)
            metrics_layout.addWidget(metric_widget, 1)
        
        overview_layout.addLayout(metrics_layout)
        left_layout.addWidget(overview_group)
        
        # Filter & Search
        filter_group = QGroupBox("Filter & Search")
        filter_group.setStyleSheet(overview_group.styleSheet())
        filter_layout = QVBoxLayout(filter_group)
        
        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search results...")
        search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #9ca3af;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
            }
        """)
        search_layout.addWidget(search_input, 1)
        
        category_combo = QComboBox()
        category_combo.addItems(["Category", "All", "Audio", "Video", "Document"])
        category_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c8c8c8;
                min-width: 120px;
            }
        """)
        search_layout.addWidget(category_combo)
        
        date_combo = QComboBox()
        date_combo.addItems(["Date Range", "Last 7 days", "Last 30 days", "Last 90 days"])
        date_combo.setStyleSheet(category_combo.styleSheet())
        search_layout.addWidget(date_combo)
        
        apply_btn = QPushButton("Apply Filters")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        search_layout.addWidget(apply_btn)
        
        filter_layout.addLayout(search_layout)
        left_layout.addWidget(filter_group)
        
        # Detailed Results
        results_group = QGroupBox("Detailed Results")
        results_group.setStyleSheet(overview_group.styleSheet())
        results_layout = QVBoxLayout(results_group)
        
        self.runs_table = QTableWidget()
        self.runs_table.setColumnCount(6)
        self.runs_table.setHorizontalHeaderLabels(["Name", "Status", "Duration", "Error Rate", "Completed At", "Actions"])
        self.runs_table.horizontalHeader().setStretchLastSection(False)
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
        self.runs_table.verticalHeader().setVisible(False)
        self.runs_table.setShowGrid(False)
        # Hide the corner button (white square in header)
        self.runs_table.setCornerButtonEnabled(False)
        
        # Disable scrollbars
        self.runs_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.runs_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Make table responsive - use stretch factors for columns
        header = self.runs_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name - stretchable
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Status - fit content
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Duration - fit content
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Error Rate - fit content
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Completed At - fit content
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Actions - fit content
        
        # Set minimum column widths to ensure text is visible
        self.runs_table.setColumnWidth(1, 260)  # Status minimum (for "Completed")
        self.runs_table.setColumnWidth(2, 100)  # Duration minimum (for "2m 3s")
        self.runs_table.setColumnWidth(3, 110)  # Error Rate minimum (for header and "100%")
        self.runs_table.setColumnWidth(4, 180)  # Completed At minimum (for "2024-03-10 14:30")
        self.runs_table.setColumnWidth(5, 130)  # Actions minimum (for "View Details")
        
        # Set minimum widths on header to prevent text cutoff
        header.setMinimumSectionSize(100)  # Minimum for all columns
        self.runs_table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        results_layout.addWidget(self.runs_table)
        left_layout.addWidget(results_group, 2)
        
        main_content.addLayout(left_layout, 2)
        
        # Right side: Result Details
        right_layout = QVBoxLayout()
        
        details_group = QGroupBox("Result Details")
        details_group.setStyleSheet(overview_group.styleSheet())
        details_layout = QVBoxLayout(details_group)
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #c8c8c8;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #427eea;
                color: white;
            }
        """)
        details_layout.addWidget(edit_btn)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                color: #c8c8c8;
                min-height: 200px;
            }
        """)
        details_layout.addWidget(self.details_text)
        
        right_layout.addWidget(details_group, 1)
        
        # Performance Visualizations
        viz_group = QGroupBox("Performance Visualizations")
        viz_group.setStyleSheet(overview_group.styleSheet())
        viz_layout = QVBoxLayout(viz_group)
        
        # Charts
        charts_layout = QVBoxLayout()
        
        # Recall by Metric chart
        recall_chart = BarChartWidget(
            labels=["Precision", "F1 Score", "Accuracy", "Recall"],
            values=[75, 80, 90, 70],
            color=QColor(59, 130, 246)  # Blue
        )
        recall_chart.setMinimumHeight(150)
        charts_layout.addWidget(recall_chart)
        
        # Rank Distribution chart (line chart placeholder)
        rank_placeholder = QLabel("Rank Distribution Chart")
        rank_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_placeholder.setMinimumHeight(150)
        rank_placeholder.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; color: #9ca3af;")
        charts_layout.addWidget(rank_placeholder)
        
        viz_layout.addLayout(charts_layout)
        right_layout.addWidget(viz_group, 1)
        
        main_content.addLayout(right_layout, 1)
        
        layout.addLayout(main_content, 1)
    
    def _on_selection_changed(self):
        """Update details when selection changes."""
        selected_rows = self.runs_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            name_item = self.runs_table.item(row, 0)
            if name_item:
                details = f"""Result Name: {name_item.text()}
Status: Completed
Duration: 2m 3s
Error Rate: 0.5%
Completed At: 2024-03-10 14:30
Output Path: /outputs/cleanup_v2.1_001.wav
Notes: Reduced background noise significantly. Minor reverb detected."""
                self.details_text.setPlainText(details)
    
    def load_results(self):
        """Load experiment results."""
        # Mock data to match design
        mock_runs = [
            {"name": "Audio Cleanup v2.1", "status": "Completed", "duration": "2m 3s", "error_rate": "0.5%", "completed_at": "2024-03-10 14:30"},
            {"name": "Voice Enhancement Alpha", "status": "Completed", "duration": "1m 58s", "error_rate": "1.2%", "completed_at": "2024-03-10 14:25"},
            {"name": "Music Mastering Beta", "status": "Failed", "duration": "0m 10s", "error_rate": "100%", "completed_at": "2024-03-10 14:20"},
        ]
        
        self.runs_table.setRowCount(len(mock_runs))
        for i, run in enumerate(mock_runs):
            # Set row height first
            self.runs_table.setRowHeight(i, 50)
            
            self.runs_table.setItem(i, 0, QTableWidgetItem(run["name"]))
            
            # Create status badge widget (pill-shaped)
            status_widget = QWidget()
            status_widget.setStyleSheet("background-color: transparent;")
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(5, 2, 20, 2)  # Increased left/right margins
            status_layout.setSpacing(0)
            
            status_label = QLabel(run["status"])
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if run["status"] == "Completed":
                status_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(147, 197, 253, 0.1);
                        color: #3b82f6;
                        border: 1px solid #60a5fa;
                        padding: 4px 3px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 500;
                        min-width: 90px;
                    }
                """)
            elif run["status"] == "Failed":
                status_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        color: #ef4444;
                        border: 1px solid #ef4444;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 500;
                        min-width: 70px;
                    }
                """)
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            
            status_item = QTableWidgetItem("")
            status_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.runs_table.setItem(i, 1, status_item)
            self.runs_table.setCellWidget(i, 1, status_widget)
            
            self.runs_table.setItem(i, 2, QTableWidgetItem(run["duration"]))
            self.runs_table.setItem(i, 3, QTableWidgetItem(run["error_rate"]))
            self.runs_table.setItem(i, 4, QTableWidgetItem(run["completed_at"]))
            
            view_btn = QPushButton("View Details")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #c8c8c8;
                    padding: 6px 4px;
                    border-radius: 4px;
                    font-size: 12px;
                    min-width: 100px;
                    margin-right: 10px;
                }
                QPushButton:hover {
                    background-color: #427eea;
                    color: white;
                }
            """)
            self.runs_table.setCellWidget(i, 5, view_btn)
        
        # Don't resize columns - use fixed widths set above
        
        # Select first row by default
        if self.runs_table.rowCount() > 0:
            self.runs_table.selectRow(0)
            self._on_selection_changed()
