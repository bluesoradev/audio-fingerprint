"""
Dark theme styling for the desktop application.
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor


def apply_dark_theme(app_or_widget):
    """Apply dark theme to the application."""
    palette = QPalette()
    
    # Color scheme (dark theme)
    dark_gray = QColor(45, 45, 45)
    darker_gray = QColor(30, 30, 30)
    darkest_gray = QColor(20, 20, 20)
    light_gray = QColor(200, 200, 200)
    blue = QColor(66, 126, 234)
    blue_dark = QColor(52, 100, 186)
    
    # Base colors
    palette.setColor(QPalette.ColorRole.Window, darker_gray)
    palette.setColor(QPalette.ColorRole.WindowText, light_gray)
    palette.setColor(QPalette.ColorRole.Base, dark_gray)
    palette.setColor(QPalette.ColorRole.AlternateBase, darkest_gray)
    palette.setColor(QPalette.ColorRole.ToolTipBase, light_gray)
    palette.setColor(QPalette.ColorRole.ToolTipText, darker_gray)
    palette.setColor(QPalette.ColorRole.Text, light_gray)
    palette.setColor(QPalette.ColorRole.Button, dark_gray)
    palette.setColor(QPalette.ColorRole.ButtonText, light_gray)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, blue)
    palette.setColor(QPalette.ColorRole.Highlight, blue)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    # Disabled colors
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
    
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setPalette(palette)
    else:
        app_or_widget.setPalette(palette)
        # Also apply stylesheet for additional styling
        app_or_widget.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: none;
                color: #c8c8c8;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #427eea;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
            QPushButton {
                background-color: #427eea;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
            QPushButton:pressed {
                background-color: #2a5098;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #787878;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #c8c8c8;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #427eea;
            }
            QLabel {
                color: #c8c8c8;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #c8c8c8;
            }
            QComboBox:hover {
                border: 1px solid #427eea;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                selection-background-color: #427eea;
                color: #c8c8c8;
            }
            QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #c8c8c8;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #427eea;
                color: white;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #c8c8c8;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #3d3d3d;
            }
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                color: #c8c8c8;
            }
            QProgressBar::chunk {
                background-color: #427eea;
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d4d4d;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #3d3d3d;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #4d4d4d;
            }
            QStatusBar {
                background-color: #252525;
                color: #c8c8c8;
                border-top: 1px solid #3d3d3d;
            }
        """)

