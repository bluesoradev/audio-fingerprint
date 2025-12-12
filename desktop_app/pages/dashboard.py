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
            # White circle outline with white checkmark
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # White checkmark
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Draw checkmark
            painter.drawLine(center.x() - 4, center.y(), center.x() - 1, center.y() + 3)
            painter.drawLine(center.x() - 1, center.y() + 3, center.x() + 4, center.y() - 3)
        
        elif self.icon_type == "info":
            # White circle outline with white 'i'
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawEllipse(center.x() - radius + 1, center.y() - radius + 1, radius * 2, radius * 2)
            
            # White 'i' - properly centered and smaller
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = QFont()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            # Use drawText with alignment flags for proper centering
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
            # Red circle outline with red 'x'
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(239, 68, 68), 1.5))  # Red outline
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # Red 'x'
            painter.setPen(QPen(QColor(239, 68, 68), 1.5))
            painter.drawLine(center.x() - 4, center.y() - 4, center.x() + 4, center.y() + 4)
            painter.drawLine(center.x() - 4, center.y() + 4, center.x() + 4, center.y() - 4)


class TrendGraph(QWidget):
    """Small trend line graph widget."""
    
    def __init__(self, values=None, color="blue"):
        super().__init__()
        self.values = values or [random.randint(80, 120) for _ in range(7)]
        self.color = color
        self.setMinimumHeight(40)
        self.setStyleSheet("background-color: transparent;")
    
    def paintEvent(self, event):
        """Draw the trend line."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set color based on parameter
        if self.color == "green":
            line_color = QColor(16, 185, 129)  # #10b981
        else:  # blue
            line_color = QColor(66, 126, 234)  # #427eea
        
        # Draw line
        pen = QPen(line_color, 2)
        painter.setPen(pen)
        
        if len(self.values) > 1:
            width = self.width()
            height = self.height()
            min_val = min(self.values)
            max_val = max(self.values)
            range_val = max_val - min_val if max_val != min_val else 1
            
            points = []
            for i, val in enumerate(self.values):
                # Use full width for the graph
                x = int((i / (len(self.values) - 1)) * width) if len(self.values) > 1 else width // 2
                y = int(height - ((val - min_val) / range_val) * height)
                points.append((x, y))
            
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])


class BarChartWidget(QWidget):
    """Bar chart widget matching the design."""
    
    def __init__(self, labels, values, color):
        super().__init__()
        self.labels = labels
        self.values = values
        self.color = color
        self.setStyleSheet("background-color: transparent;")
    
    def paintEvent(self, event):
        """Draw the bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw axes
        margin_left = 30
        margin_right = 10
        margin_top = 20
        margin_bottom = 30
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        # Y-axis labels (0, 25, 50, 75, 100)
        painter.setPen(QPen(QColor(156, 163, 175), 1))
        painter.setFont(QFont("Arial", 9))
        for i, y_label in enumerate([0, 25, 50, 75, 100]):
            y_pos = margin_top + chart_height - (i * chart_height / 4)
            painter.drawText(5, int(y_pos + 5), f"{y_label}")
            # Draw grid line
            painter.setPen(QPen(QColor(61, 61, 61), 1))
            painter.drawLine(margin_left, int(y_pos), width - margin_right, int(y_pos))
            painter.setPen(QPen(QColor(156, 163, 175), 1))
        
        # Draw bars
        if len(self.labels) > 0 and len(self.values) > 0:
            bar_width = chart_width / len(self.labels) * 0.6
            bar_spacing = chart_width / len(self.labels) * 0.4
            
            max_value = max(self.values) if self.values else 100
            if max_value == 0:
                max_value = 100
            
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            for i, (label, value) in enumerate(zip(self.labels, self.values)):
                bar_height = (value / max_value) * chart_height
                x = margin_left + i * (bar_width + bar_spacing) + bar_spacing / 2
                y = margin_top + chart_height - bar_height
                
                # Draw rounded rectangle bar
                painter.drawRoundedRect(
                    int(x), int(y), int(bar_width), int(bar_height),
                    4, 4
                )
                
                # Draw label
                painter.setPen(QPen(QColor(200, 200, 200), 1))
                painter.setFont(QFont("Arial", 10))
                label_width = painter.fontMetrics().horizontalAdvance(label)
                painter.drawText(
                    int(x + bar_width / 2 - label_width / 2),
                    int(height - margin_bottom + 20),
                    label
                )
                painter.setPen(Qt.PenStyle.NoPen)


class StatCard(QWidget):
    """Statistics card with value, change, and trend graph."""
    
    def __init__(self, title, value, change, change_type="positive", graph_color="blue", trend_values=None):
        super().__init__()
        self.title = title
        self.value = value
        self.change = change
        self.change_type = change_type
        self.graph_color = graph_color
        self.trend_values = trend_values
        self.value_label = None
        self.change_label = None
        self.init_ui()
    
    def paintEvent(self, event):
        """Paint the gray background covering the entire card."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw gray background covering entire widget
        rect = self.rect()
        painter.setBrush(QBrush(QColor(45, 45, 45)))  # #2d2d2d
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        
        super().paintEvent(event)
    
    def init_ui(self):
        """Initialize the stat card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)
        
        # Set minimum size for consistent card dimensions
        self.setMinimumHeight(180)
        self.setMinimumWidth(200)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #9ca3af; font-size: 13px; background-color: transparent;")
        layout.addWidget(title_label)
        
        # Value and change row
        value_layout = QHBoxLayout()
        value_layout.setSpacing(10)
        
        # Format value with commas if it's a number
        if isinstance(self.value, (int, float)):
            formatted_value = f"{self.value:,}"
        else:
            formatted_value = str(self.value)
        
        # Value - plain text, no background box
        self.value_label = QLabel(formatted_value)
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                background-color: transparent;
            }
        """)
        value_layout.addWidget(self.value_label)
        
        # Change - with dark gray background box
        change_color = "#10b981" if self.change_type == "positive" else "#ef4444"
        change_text = f"{self.change:+.1f}%"
        self.change_label = QLabel(change_text)
        self.change_label.setStyleSheet(f"""
            QLabel {{
                color: {change_color};
                font-size: 12px;
                font-weight: 500;
                background-color: #2d2d2d;
                border-radius: 6px;
                padding: 4px 10px;
            }}
        """)
        value_layout.addWidget(self.change_label)
        
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        # Trend graph with specified color - make it fill full width
        trend = TrendGraph(self.trend_values, self.graph_color)
        layout.addWidget(trend, 1)  # Add stretch factor to fill available space
    
    def update_value(self, value, change=None):
        """Update the displayed value and change."""
        # Format value with commas if it's a number
        if isinstance(value, (int, float)):
            formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        self.value_label.setText(formatted_value)
        if change is not None:
            self.change = change
            change_color = "#10b981" if self.change_type == "positive" else "#ef4444"
            self.change_label.setText(f"{change:+.1f}%")
            self.change_label.setStyleSheet(f"""
                QLabel {{
                    color: {change_color};
                    font-size: 12px;
                    font-weight: 500;
                    background-color: #2d2d2d;
                    border-radius: 6px;
                    padding: 4px 10px;
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
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 20, 30, 20)
        
        # Header
        title = QLabel("Dashboard Overview")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px; background-color: transparent;")
        layout.addWidget(title)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        # Total Runs - blue graph, upward trend
        total_runs_trend = [60, 75, 70, 85, 80, 90, 95]
        self.total_runs_card = StatCard("Total Runs", 0, 0, "positive", "blue", total_runs_trend)
        stats_layout.addWidget(self.total_runs_card, 1)
        
        # Active Experiments - blue graph, upward trend with oscillation
        active_exp_trend = [50, 70, 65, 80, 75, 85, 88]
        self.active_exp_card = StatCard("Active Experiments", 0, 0, "positive", "blue", active_exp_trend)
        stats_layout.addWidget(self.active_exp_card, 1)
        
        # Failed Runs - green graph, downward trend
        failed_runs_trend = [90, 85, 80, 60, 55, 50, 45]
        self.failed_runs_card = StatCard("Failed Runs", 0, 0, "negative", "green", failed_runs_trend)
        stats_layout.addWidget(self.failed_runs_card, 1)
        
        # Average Latency - green graph, upward trend
        latency_trend = [40, 45, 42, 50, 48, 55, 60]
        self.latency_card = StatCard("Average Latency", "0 ms", 0, "positive", "green", latency_trend)
        stats_layout.addWidget(self.latency_card, 1)
        
        layout.addLayout(stats_layout)
        
        # Main content area (table + notifications + charts)
        main_content = QHBoxLayout()
        main_content.setSpacing(15)
        
        # Left side: Table and Charts
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        
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
        self.runs_table.horizontalHeader().setStretchLastSection(False)
        self.runs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.runs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set static column widths (smaller)
        self.runs_table.setColumnWidth(0, 80)   # Run ID
        self.runs_table.setColumnWidth(1, 200)  # Experiment Name
        self.runs_table.setColumnWidth(2, 130)  # Status (expanded for "Completed")
        self.runs_table.setColumnWidth(3, 120)  # Metrics
        self.runs_table.setColumnWidth(4, 100)  # Start Date
        self.runs_table.setColumnWidth(5, 80)   # Actions
        self.runs_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                gridline-color: #3d3d3d;
                alternate-background-color: #2d2d2d;
            }
            QTableWidget::item {
                padding: 8px;
                color: #c8c8c8;
                background-color: #2d2d2d;
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
            QTableCornerButton::section {
                background-color: #252525;
                border: none;
            }
            QHeaderView {
                background-color: #252525;
            }
            QTableCornerButton {
                background-color: #252525;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                border: none;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 5px;
                min-height: 40px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #6d6d6d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)
        self.runs_table.verticalHeader().setVisible(False)
        self.runs_table.setShowGrid(False)
        self.runs_table.verticalHeader().setDefaultSectionSize(50)
        # Hide the corner button (white square in header)
        self.runs_table.setCornerButtonEnabled(False)
        self.runs_table.setRowHeight(0, 50)
        self.runs_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.runs_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table_layout.addWidget(self.runs_table)
        left_layout.addWidget(table_group, 2)
        
        # Charts row
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(12)
        
        # Recall by Transform chart
        recall_chart_group = QGroupBox("Recall by Transform")
        recall_chart_group.setStyleSheet(table_group.styleSheet())
        recall_chart_layout = QVBoxLayout(recall_chart_group)
        recall_subtitle = QLabel("Average recall scores for different audio transformations.")
        recall_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        recall_chart_layout.addWidget(recall_subtitle)
        recall_chart = BarChartWidget(
            labels=["Raw", "Noi", "Rev", "EQ", "Pit"],
            values=[75, 80, 70, 65, 72],
            color=QColor(251, 146, 60)  # Orange
        )
        recall_chart.setMinimumHeight(180)
        recall_chart.setMaximumHeight(180)
        recall_chart_layout.addWidget(recall_chart)
        charts_layout.addWidget(recall_chart_group, 1)
        
        # Rank Distribution chart
        rank_chart_group = QGroupBox("Rank Distribution")
        rank_chart_group.setStyleSheet(table_group.styleSheet())
        rank_chart_layout = QVBoxLayout(rank_chart_group)
        rank_subtitle = QLabel("Trend of rank scores over recent experiment batches.")
        rank_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        rank_chart_layout.addWidget(rank_subtitle)
        rank_chart = BarChartWidget(
            labels=["Rat", "Rat", "Rat", "Rat", "Rat"],
            values=[78, 80, 79, 81, 77],
            color=QColor(168, 85, 247)  # Purple
        )
        rank_chart.setMinimumHeight(180)
        rank_chart.setMaximumHeight(180)
        rank_chart_layout.addWidget(rank_chart)
        charts_layout.addWidget(rank_chart_group, 1)
        
        left_layout.addLayout(charts_layout, 1)
        
        main_content.addLayout(left_layout, 2)
        
        # Right side: Notifications and Quick Actions
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        
        # Recent Notifications
        notif_group = QGroupBox("Recent Notifications")
        notif_group.setStyleSheet(table_group.styleSheet())
        notif_layout = QVBoxLayout(notif_group)
        notif_subtitle = QLabel("Important system alerts and activity")
        notif_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        notif_layout.addWidget(notif_subtitle)
        
        self.notif_list = QWidget()
        self.notif_list.setStyleSheet("background-color: #1e1e1e;")
        self.notif_list_layout = QVBoxLayout(self.notif_list)
        self.notif_list_layout.setSpacing(8)
        self.notif_list_layout.setContentsMargins(0, 0, 0, 0)
        self.notif_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.notif_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidget(self.notif_list)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                border: none;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 5px;
                min-height: 40px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #6d6d6d;
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
    
    def _create_notification_item(self, icon_type, message, time_ago, is_last=False):
        """Create a notification item."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Notification item
        item = QWidget()
        item.setStyleSheet("background-color: transparent;")
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(15, 8, 15, 8)
        item_layout.setSpacing(18)
        
        # Custom icon widget - vertically centered with text
        icon_widget = NotificationIconWidget(icon_type)
        item_layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text_layout.addWidget(message_label)
        
        time_label = QLabel(time_ago)
        time_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text_layout.addWidget(time_label)
        
        item_layout.addLayout(text_layout, 1)
        container_layout.addWidget(item)
        
        # Separator line (not for last item)
        if not is_last:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("""
                QFrame {
                    background-color: #3d3d3d;
                    border: none;
                    max-height: 1px;
                }
            """)
            container_layout.addWidget(separator)
        
        return container
    
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
        
        # Update stat cards with mock data to match design
        self.total_runs_card.update_value(1234, 12.5)
        self.active_exp_card.update_value(15, 0.0)
        self.failed_runs_card.update_value(3, -5.2)
        self.latency_card.update_value("235 ms", 1.1)
        
        # Add mock table data to match design
        mock_runs = [
            {"id": "EXP-001", "name": "Voice Isolation Filter Test", "status": "Completed", "metrics": "SNR: 25dB", "date": "2023-10-26"},
            {"id": "EXP-002", "name": "Noise Reduction Algorithm V2", "status": "Running", "metrics": "Progress: 75%", "date": "2023-10-27"},
            {"id": "EXP-003", "name": "Reverb Delay Parameter Tuning", "status": "Failed", "metrics": "Error: No Input", "date": "2023-10-27"},
            {"id": "EXP-004", "name": "Equalization Preset", "status": "Completed", "metrics": "Accuracy: 92%", "date": "2023-10-28"},
        ]
        
        # Combine mock data with real data
        all_runs = mock_runs + recent_runs[:6]  # Show mock first, then real
        
        self.runs_table.setRowCount(len(all_runs))
        for i, run in enumerate(all_runs):
            # Set row height first
            self.runs_table.setRowHeight(i, 50)
            
            self.runs_table.setItem(i, 0, QTableWidgetItem(run.get("id", "N/A")))
            self.runs_table.setItem(i, 1, QTableWidgetItem(run.get("name", "N/A")))
            
            # Create status badge widget (pill-shaped)
            status_widget = QWidget()
            status_widget.setStyleSheet("background-color: transparent;")
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(2, 2, 2, 2)
            status_layout.setSpacing(0)
            
            status_label = QLabel(run.get("status", "Unknown"))
            status = run.get("status", "")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if status == "Completed":
                status_label.setStyleSheet("""
                    QLabel {
                        background-color: #2d2d2d;
                        color: #ffffff;
                        border: 1px solid #9ca3af;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                """)
            elif status == "Running":
                status_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(147, 197, 253, 0.1);
                        color: #3b82f6;
                        border: 1px solid #60a5fa;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                """)
            elif status == "Failed":
                status_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(255, 0, 0, 0.1);
                        color: #ef4444;
                        border: 1px solid #ef4444;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                """)
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            
            status_item = QTableWidgetItem("")
            status_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.runs_table.setItem(i, 2, status_item)
            self.runs_table.setCellWidget(i, 2, status_widget)
            
            self.runs_table.setItem(i, 3, QTableWidgetItem(run.get("metrics", "N/A")))
            self.runs_table.setItem(i, 4, QTableWidgetItem(run.get("date", "N/A")))
            
            view_btn = QPushButton("View Log")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #427eea;
                    padding: 0px;
                    border: none;
                    font-size: 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    color: #3464ba;
                    text-decoration: underline;
                }
            """)
            self.runs_table.setCellWidget(i, 5, view_btn)
        
        # Don't resize columns - use static widths set above
        
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
        
        # Add mock notifications to match design
        notifications = [
            ("success", "Experiment 'Voice Isolation Filter Test' completed successfully.", "2 minutes ago"),
            ("info", "New audio file 'speech_sample.wav' uploaded.", "15 minutes ago"),
            ("error", "Workflow 'Noise Reduction Algorithm V2' failed at preprocessing stage.", "30 minutes ago"),
            ("info", "Scheduled maintenance window: 2023-10-28 02:00-04:00 UTC", "1 hour ago"),
            ("success", "System backup completed.", "2 hours ago"),
        ]
        
        for i, (icon_type, message, time_ago) in enumerate(notifications):
            is_last = (i == len(notifications) - 1)
            notif_item = self._create_notification_item(icon_type, message, time_ago, is_last)
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
