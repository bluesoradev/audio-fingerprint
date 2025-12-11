"""
Dashboard page showing overview statistics and recent experiments.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QScrollArea,
    QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygon
from pathlib import Path
import json
from datetime import datetime, timedelta
import random


class NotificationIconWidget(QWidget):
    """Custom notification icon widget."""
    
    def __init__(self, icon_type):
        super().__init__()
        self.icon_type = icon_type  # "success", "info", "warning", "error"
        self.setFixedSize(24, 24)
    
    def paintEvent(self, event):
        """Draw the notification icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = 10
        
        if self.icon_type == "success":
            # Green circle with white checkmark
            painter.setBrush(QBrush(QColor(34, 197, 94)))  # Green
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # White checkmark
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Draw checkmark
            painter.drawLine(center.x() - 4, center.y(), center.x() - 1, center.y() + 3)
            painter.drawLine(center.x() - 1, center.y() + 3, center.x() + 4, center.y() - 3)
        
        elif self.icon_type == "info":
            # Light gray circle with white 'i'
            painter.setBrush(QBrush(QColor(156, 163, 175)))  # Light gray
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # White 'i'
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "i")
        
        elif self.icon_type == "warning":
            # Yellow triangle with black exclamation
            painter.setBrush(QBrush(QColor(234, 179, 8)))  # Yellow
            painter.setPen(QPen(QColor(161, 98, 7), 1))  # Dark yellow border
            # Draw triangle
            triangle = [
                QPoint(center.x(), center.y() - radius),
                QPoint(center.x() - radius, center.y() + radius),
                QPoint(center.x() + radius, center.y() + radius)
            ]
            polygon = QPolygon(triangle)
            painter.drawPolygon(polygon)
            
            # Black exclamation mark
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(center.x(), center.y() - 4, center.x(), center.y() + 2)
            painter.drawEllipse(center.x() - 1, center.y() + 4, 2, 2)
        
        elif self.icon_type == "error":
            # Red circle with white 'x'
            painter.setBrush(QBrush(QColor(239, 68, 68)))  # Red
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # White 'x'
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawLine(center.x() - 4, center.y() - 4, center.x() + 4, center.y() + 4)
            painter.drawLine(center.x() - 4, center.y() + 4, center.x() + 4, center.y() - 4)


class TrendGraph(QWidget):
    """Small trend line graph widget."""
    
    def __init__(self, values=None):
        super().__init__()
        self.values = values or [random.randint(80, 120) for _ in range(7)]
        self.setFixedSize(80, 40)
        self.setStyleSheet("background-color: transparent;")
    
    def paintEvent(self, event):
        """Draw the trend line."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw line
        pen = QPen(QColor(66, 126, 234), 2)
        painter.setPen(pen)
        
        if len(self.values) > 1:
            width = self.width()
            height = self.height()
            min_val = min(self.values)
            max_val = max(self.values)
            range_val = max_val - min_val if max_val != min_val else 1
            
            points = []
            for i, val in enumerate(self.values):
                x = int((i / (len(self.values) - 1)) * width) if len(self.values) > 1 else width // 2
                y = int(height - ((val - min_val) / range_val) * height)
                points.append((x, y))
            
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])


class StatCard(QWidget):
    """Statistics card with value, change, and trend graph."""
    
    def __init__(self, title, value, change, change_type="positive"):
        super().__init__()
        self.title = title
        self.value = value
        self.change = change
        self.change_type = change_type
        self.value_label = None
        self.change_label = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the stat card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
            }
        """)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        layout.addWidget(title_label)
        
        # Value and change row
        value_layout = QHBoxLayout()
        value_layout.setSpacing(10)
        
        # Value
        self.value_label = QLabel(str(self.value))
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        value_layout.addWidget(self.value_label)
        
        # Change
        change_color = "#10b981" if self.change_type == "positive" else "#ef4444"
        change_text = f"{self.change:+.1f}%"
        self.change_label = QLabel(change_text)
        self.change_label.setStyleSheet(f"""
            QLabel {{
                color: {change_color};
                font-size: 12px;
                font-weight: 500;
            }}
        """)
        value_layout.addWidget(self.change_label)
        
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        # Trend graph
        trend = TrendGraph()
        layout.addWidget(trend)
    
    def update_value(self, value, change=None):
        """Update the displayed value and change."""
        self.value_label.setText(str(value))
        if change is not None:
            self.change = change
            change_color = "#10b981" if self.change_type == "positive" else "#ef4444"
            self.change_label.setText(f"{change:+.1f}%")
            self.change_label.setStyleSheet(f"""
                QLabel {{
                    color: {change_color};
                    font-size: 12px;
                    font-weight: 500;
                }}
            """)


class DashboardPage(QWidget):
    """Dashboard overview page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.reports_dir = project_root / "reports"
        self.init_ui()
        self.load_data()
        
        # Auto-refresh every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(5000)
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        title = QLabel("Dashboard Overview")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.total_runs_card = StatCard("Total Runs", 0, 0)
        stats_layout.addWidget(self.total_runs_card, 1)
        
        self.active_exp_card = StatCard("Active Experiments", 0, 0)
        stats_layout.addWidget(self.active_exp_card, 1)
        
        self.failed_runs_card = StatCard("Failed Runs", 0, 0, "negative")
        stats_layout.addWidget(self.failed_runs_card, 1)
        
        self.latency_card = StatCard("Average Latency", "0 ms", 0)
        stats_layout.addWidget(self.latency_card, 1)
        
        layout.addLayout(stats_layout)
        
        # Main content area (table + notifications + charts)
        main_content = QHBoxLayout()
        main_content.setSpacing(20)
        
        # Left side: Table and Charts
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        
        # Recent Experiments Table
        table_group = QGroupBox("Recent Experiments")
        table_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #c8c8c8;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #c8c8c8;
            }
        """)
        table_layout = QVBoxLayout(table_group)
        
        subtitle = QLabel("Overview of the latest experiment outcomes.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        table_layout.addWidget(subtitle)
        
        self.runs_table = QTableWidget()
        self.runs_table.setColumnCount(6)
        self.runs_table.setHorizontalHeaderLabels(["Run ID", "Experiment Name", "Status", "Metrics", "Start Date", "Actions"])
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
        left_layout.addWidget(table_group, 2)
        
        # Charts row
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(15)
        
        # Recall by Transform chart
        recall_chart_group = QGroupBox("Recall by Transform")
        recall_chart_group.setStyleSheet(table_group.styleSheet())
        recall_chart_layout = QVBoxLayout(recall_chart_group)
        recall_subtitle = QLabel("Average recall scores for different audio transformations.")
        recall_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        recall_chart_layout.addWidget(recall_subtitle)
        recall_placeholder = QLabel("Chart: Average recall scores across different audio transformations")
        recall_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recall_placeholder.setMinimumHeight(200)
        recall_placeholder.setStyleSheet("background-color: #2d2d2d; border-radius: 4px; color: #9ca3af;")
        recall_chart_layout.addWidget(recall_placeholder)
        charts_layout.addWidget(recall_chart_group, 1)
        
        # Rank Distribution chart
        rank_chart_group = QGroupBox("Rank Distribution")
        rank_chart_group.setStyleSheet(table_group.styleSheet())
        rank_chart_layout = QVBoxLayout(rank_chart_group)
        rank_subtitle = QLabel("Trend of rank scores over recent experiment batches.")
        rank_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        rank_chart_layout.addWidget(rank_subtitle)
        rank_placeholder = QLabel("Chart: Trend of rank scores over recent experiment batches")
        rank_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_placeholder.setMinimumHeight(200)
        rank_placeholder.setStyleSheet("background-color: #2d2d2d; border-radius: 4px; color: #9ca3af;")
        rank_chart_layout.addWidget(rank_placeholder)
        charts_layout.addWidget(rank_chart_group, 1)
        
        left_layout.addLayout(charts_layout, 1)
        
        main_content.addLayout(left_layout, 2)
        
        # Right side: Notifications and Quick Actions
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        
        # Recent Notifications
        notif_group = QGroupBox("Recent Notifications")
        notif_group.setStyleSheet(table_group.styleSheet())
        notif_layout = QVBoxLayout(notif_group)
        notif_subtitle = QLabel("Important system alerts and activity")
        notif_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        notif_layout.addWidget(notif_subtitle)
        
        self.notif_list = QWidget()
        self.notif_list_layout = QVBoxLayout(self.notif_list)
        self.notif_list_layout.setSpacing(8)
        self.notif_list_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidget(self.notif_list)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
                border: none;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 4px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d4d4d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        notif_layout.addWidget(scroll)
        right_layout.addWidget(notif_group, 1)
        
        main_content.addLayout(right_layout, 1)
        
        layout.addLayout(main_content, 1)
    
    def _create_notification_item(self, icon_type, message, time_ago):
        """Create a notification item."""
        item = QWidget()
        item.setStyleSheet("background-color: #2d2d2d; border-radius: 4px; padding: 10px;")
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(10, 8, 10, 8)
        item_layout.setSpacing(10)
        
        # Custom icon widget
        icon_widget = NotificationIconWidget(icon_type)
        item_layout.addWidget(icon_widget)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        message_label.setWordWrap(True)
        text_layout.addWidget(message_label)
        
        time_label = QLabel(time_ago)
        time_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        text_layout.addWidget(time_label)
        
        item_layout.addLayout(text_layout, 1)
        
        return item
    
    def load_data(self):
        """Load dashboard data."""
        # Count total runs
        total_runs = 0
        active_exps = 0
        failed_runs = 0
        recent_runs = []
        
        if self.reports_dir.exists():
            for run_dir in sorted(self.reports_dir.glob("run_*"), reverse=True):
                total_runs += 1
                
                # Check if run is complete
                metrics_file = run_dir / "metrics.json"
                if metrics_file.exists():
                    recent_runs.append({
                        "id": run_dir.name,
                        "name": run_dir.name.replace("run_", "Experiment "),
                        "status": "Completed",
                        "date": datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "metrics": self._get_metrics_summary(metrics_file)
                    })
                else:
                    active_exps += 1
                    recent_runs.append({
                        "id": run_dir.name,
                        "name": run_dir.name.replace("run_", "Experiment "),
                        "status": "Running",
                        "date": datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "metrics": "N/A"
                    })
                
                if len(recent_runs) >= 10:
                    break
        
        # Update stat cards - update labels directly
        # Update stat cards
        self.total_runs_card.update_value(total_runs, 12.5)
        self.active_exp_card.update_value(active_exps, 0)
        self.failed_runs_card.update_value(failed_runs, -5.2)
        self.latency_card.update_value("235 ms", 1.1)
        
        # Update table
        self.runs_table.setRowCount(len(recent_runs))
        for i, run in enumerate(recent_runs):
            self.runs_table.setItem(i, 0, QTableWidgetItem(run["id"]))
            self.runs_table.setItem(i, 1, QTableWidgetItem(run["name"]))
            
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
            self.runs_table.setItem(i, 2, status_item)
            
            self.runs_table.setItem(i, 3, QTableWidgetItem(run["metrics"]))
            self.runs_table.setItem(i, 4, QTableWidgetItem(run["date"]))
            
            view_btn = QPushButton("👁 View Logs")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #c8c8c8;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #427eea;
                    color: white;
                }
            """)
            self.runs_table.setCellWidget(i, 5, view_btn)
        
        self.runs_table.resizeColumnsToContents()
        
        # Update notifications
        # Clear existing notifications
        for i in reversed(range(self.notif_list_layout.count())):
            item = self.notif_list_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    # Remove layout items like stretch
                    self.notif_list_layout.removeItem(item)
        
        # Add mock notifications
        notifications = [
            ("success", "Experiment 'Voice Isolation Filter Test' completed successfully.", "2 minutes ago"),
            ("info", "New audio file 'speech_sample.wav' uploaded.", "15 minutes ago"),
            ("error", "Workflow 'Noise Reduction Algorithm V2' failed at preprocessing stage.", "30 minutes ago"),
            ("info", "Scheduled maintenance window: 2023-10-28 02:00-04:00 UTC", "1 hour ago"),
            ("info", "Configuration saved: test_matrix.yaml", "2 hours ago"),
            ("error", "Database connection lost. Data sync paused.", "4 hours ago"),
        ]
        
        for icon_type, message, time_ago in notifications:
            notif_item = self._create_notification_item(icon_type, message, time_ago)
            self.notif_list_layout.addWidget(notif_item)
        
        self.notif_list_layout.addStretch()
    
    def _get_metrics_summary(self, metrics_file: Path) -> str:
        """Get summary metrics from metrics.json."""
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
                recall = metrics.get("overall", {}).get("recall", {}).get("recall_at_1", 0)
                latency = metrics.get("overall", {}).get("latency", {}).get("mean_ms", 0)
                return f"{recall:.2f} / {latency:.0f}ms"
        except:
            return "N/A"
