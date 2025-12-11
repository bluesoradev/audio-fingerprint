"""
Main window for the Audio Fingerprint Robustness Lab desktop application.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QPen
from pathlib import Path
import sys

# Import page widgets
from desktop_app.pages.dashboard import DashboardPage
from desktop_app.pages.workflow import WorkflowPage
from desktop_app.pages.manipulate import ManipulatePage
from desktop_app.pages.files import FilesPage
from desktop_app.pages.results import ResultsPage
from desktop_app.pages.config import ConfigPage
from desktop_app.theme import apply_dark_theme


class BellIconButton(QPushButton):
    """Custom bell icon button with yellow/orange styling."""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
    
    def paintEvent(self, event):
        """Draw the bell icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw bell shape in yellow/orange gradient
        bell_rect = self.rect().adjusted(10, 10, -10, -10)
        
        # Bell body (gradient effect with yellow/orange)
        bell_color = QColor(251, 191, 36)  # Yellow
        painter.setBrush(QBrush(bell_color))
        painter.setPen(QPen(QColor(234, 179, 8), 1))  # Darker yellow border
        
        # Simple bell shape
        center_x = bell_rect.center().x()
        center_y = bell_rect.center().y()
        
        # Bell body (rounded rectangle for bell shape)
        from PyQt6.QtCore import QRect
        bell_body = QRect(center_x - 8, center_y - 6, 16, 12)
        painter.drawRoundedRect(bell_body, 4, 4)
        
        # Clapper (small circle at bottom)
        clapper_color = QColor(217, 119, 6)  # Orange
        painter.setBrush(QBrush(clapper_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - 2, center_y + 6, 4, 4)


class ProfileIconButton(QPushButton):
    """Custom profile button with blue circle and green border."""
    
    def __init__(self, initial="J"):
        super().__init__()
        self.initial = initial
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(61, 61, 61, 0.3);
            }
        """)
    
    def paintEvent(self, event):
        """Draw the profile icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw blue circle with green border
        circle_rect = self.rect().adjusted(4, 4, -4, -4)
        
        # Outer green border
        painter.setBrush(QBrush(QColor(16, 185, 129)))  # Green
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)
        
        # Inner blue circle
        inner_rect = circle_rect.adjusted(2, 2, -2, -2)
        painter.setBrush(QBrush(QColor(59, 130, 246)))  # Blue
        painter.drawEllipse(inner_rect)
        
        # Letter
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        
        painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, self.initial)


class HeaderBar(QWidget):
    """Top header bar with search, notifications, and user profile."""
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        """Initialize header UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Q Search...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #9ca3af;
                font-size: 14px;
                min-width: 300px;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
            }
        """)
        layout.addWidget(self.search_input)
        
        layout.addStretch()
        
        # Notifications button - custom bell icon
        self.notif_btn = BellIconButton()
        layout.addWidget(self.notif_btn)
        
        # User profile button - custom blue circle with green border
        self.profile_btn = ProfileIconButton("J")
        layout.addWidget(self.profile_btn)


class FooterBar(QWidget):
    """Bottom footer bar with copyright and branding."""
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-top: 1px solid #3d3d3d;
            }
            QLabel {
                color: #9ca3af;
                font-size: 12px;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        """Initialize footer UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)
        
        # Made with V logo
        made_with = QLabel("Made with")
        made_with.setStyleSheet("color: #9ca3af;")
        layout.addWidget(made_with)
        
        # V logo (purple square)
        v_logo = QLabel("V")
        v_logo.setStyleSheet("""
            QLabel {
                background-color: #8b5cf6;
                color: white;
                border-radius: 3px;
                padding: 2px 6px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(v_logo)
        
        layout.addStretch()
        
        # Copyright
        copyright_label = QLabel("© 2025 Audio Robustness Lab. All rights reserved.")
        layout.addWidget(copyright_label)


class NavigationIconWidget(QWidget):
    """Custom icon widget for navigation items."""
    
    def __init__(self, icon_type):
        super().__init__()
        self.icon_type = icon_type
        self.setFixedSize(20, 20)
        self.is_selected = False
    
    def set_selected(self, selected):
        """Set selection state."""
        self.is_selected = selected
        self.update()
    
    def paintEvent(self, event):
        """Draw the icon based on type."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.icon_type == "dashboard":
            # Three colored bars (green, yellow, red)
            bar_width = 4
            bar_spacing = 2
            x_start = 2
            y_base = 18
            
            # Green bar (tallest)
            painter.setBrush(QBrush(QColor(34, 197, 94)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x_start, y_base - 12, bar_width, 12)
            
            # Yellow bar (medium)
            painter.setBrush(QBrush(QColor(234, 179, 8)))
            painter.drawRect(x_start + bar_width + bar_spacing, y_base - 8, bar_width, 8)
            
            # Red bar (shortest)
            painter.setBrush(QBrush(QColor(239, 68, 68)))
            painter.drawRect(x_start + (bar_width + bar_spacing) * 2, y_base - 6, bar_width, 6)
        
        elif self.icon_type == "workflow":
            # Gray gear icon
            painter.setPen(QPen(QColor(156, 163, 175), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = self.rect().center()
            painter.translate(center)
            # Simple gear shape
            for i in range(8):
                painter.rotate(45)
                painter.drawRect(-1, -8, 2, 6)
            painter.resetTransform()
        
        elif self.icon_type == "manipulate":
            # Purple musical note
            painter.setBrush(QBrush(QColor(147, 51, 234)))  # Purple
            painter.setPen(Qt.PenStyle.NoPen)
            # Note head
            painter.drawEllipse(8, 8, 6, 6)
            # Note stem
            painter.drawRect(13, 2, 2, 10)
        
        elif self.icon_type == "files":
            # Yellow folder
            folder_color = QColor(234, 179, 8)  # Yellow
            painter.setBrush(QBrush(folder_color))
            painter.setPen(QPen(QColor(217, 119, 6), 1))
            # Folder shape
            painter.drawRect(4, 6, 12, 10)
            # Folder tab
            painter.drawRect(4, 6, 8, 3)
        
        elif self.icon_type == "results":
            # White line graph with red trending line
            # Axes
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawLine(2, 16, 18, 16)  # X-axis
            painter.drawLine(2, 4, 2, 16)    # Y-axis
            # Red trending line
            painter.setPen(QPen(QColor(239, 68, 68), 2))
            painter.drawLine(2, 14, 6, 10)
            painter.drawLine(6, 10, 10, 8)
            painter.drawLine(10, 8, 14, 6)
            painter.drawLine(14, 6, 18, 4)
        
        elif self.icon_type == "config":
            # Gray gear icon (same as workflow)
            painter.setPen(QPen(QColor(156, 163, 175), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = self.rect().center()
            painter.translate(center)
            for i in range(8):
                painter.rotate(45)
                painter.drawRect(-1, -8, 2, 6)
            painter.resetTransform()
        
        elif self.icon_type == "logout":
            # Brown door/logout icon
            door_color = QColor(161, 98, 7)  # Brown
            painter.setBrush(QBrush(door_color))
            painter.setPen(QPen(door_color, 1))
            # Door shape
            painter.drawRect(4, 4, 8, 12)
            # Door handle
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.drawEllipse(10, 10, 2, 2)


class NavigationItem(QWidget):
    """Custom navigation item with icon and text."""
    
    def __init__(self, icon_type, text):
        super().__init__()
        self.icon_type = icon_type
        self.text = text
        self.is_selected = False
        self.init_ui()
    
    def init_ui(self):
        """Initialize the navigation item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        self.icon = NavigationIconWidget(self.icon_type)
        layout.addWidget(self.icon)
        
        self.label = QLabel(self.text)
        self.label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
        layout.addWidget(self.label)
        
        layout.addStretch()
    
    def set_selected(self, selected):
        """Set selection state."""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("background-color: #427eea; border: 1px dashed #9ca3af; border-radius: 4px;")
            self.label.setStyleSheet("color: white; font-size: 14px;")
            self.icon.is_selected = True
        else:
            self.setStyleSheet("background-color: transparent; border: none;")
            self.label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
            self.icon.is_selected = False
        self.icon.update()


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("Audio Robustness Lab")
        self.setMinimumSize(1400, 900)
        
        # Project root
        self.project_root = Path(__file__).parent.parent
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create header bar
        self.header_bar = HeaderBar()
        main_layout.addWidget(self.header_bar)
        
        # Content area (sidebar + pages)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = self._create_sidebar()
        content_layout.addWidget(self.sidebar, 0)
        
        # Create content area with stacked widget
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # Create footer bar
        self.footer_bar = FooterBar()
        main_layout.addWidget(self.footer_bar)
        
        # Create pages
        self.pages = {}
        self._create_pages()
        
        # Apply dark theme
        apply_dark_theme(self)
        
        # Set initial page
        self.current_nav_index = 0
        self._update_navigation_selection(0)
        self._on_navigation_changed(0)
        
        # Create status bar
        status_bar = self.statusBar()
        status_bar.showMessage("Ready")
    
    def _create_sidebar(self):
        """Create the left sidebar navigation."""
        sidebar = QWidget()
        sidebar.setMaximumWidth(220)
        sidebar.setMinimumWidth(200)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(4)
        
        # Navigation items
        nav_items = [
            ("dashboard", "Dashboard"),
            ("workflow", "Workflow"),
            ("manipulate", "Manipulate Audio"),
            ("files", "Files"),
            ("results", "Results"),
            ("config", "Configuration"),
        ]
        
        self.nav_items = []
        for icon_type, text in nav_items:
            item = NavigationItem(icon_type, text)
            item.mousePressEvent = lambda e, idx=len(self.nav_items): self._on_nav_item_clicked(idx)
            layout.addWidget(item)
            self.nav_items.append(item)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #3d3d3d;")
        separator.setFixedHeight(10)
        layout.addWidget(separator)
        
        # Logout
        logout_item = NavigationItem("logout", "Logout")
        logout_item.mousePressEvent = lambda e: self._on_logout_clicked()
        layout.addWidget(logout_item)
        self.nav_items.append(logout_item)
        
        layout.addStretch()
        
        return sidebar
    
    def _on_nav_item_clicked(self, index):
        """Handle navigation item click."""
        self.current_nav_index = index
        self._update_navigation_selection(index)
        self._on_navigation_changed(index)
    
    def _update_navigation_selection(self, selected_index):
        """Update visual selection of navigation items."""
        for i, item in enumerate(self.nav_items):
            item.set_selected(i == selected_index)
    
    def _on_logout_clicked(self):
        """Handle logout button click."""
        self.close()
    
    def _on_navigation_changed(self, index):
        """Handle navigation item selection."""
        if index >= 6:  # Help or Logout
            return
        
        page_map = {
            0: "dashboard",
            1: "workflow",
            2: "manipulate",
            3: "files",
            4: "results",
            5: "config",
        }
        
        if index in page_map:
            page_key = page_map[index]
            page_index = list(self.pages.keys()).index(page_key)
            self.stacked_widget.setCurrentIndex(page_index)
            
            # Update status bar
            page_names = {
                "dashboard": "Dashboard Overview",
                "workflow": "Workflow Management",
                "manipulate": "Audio Manipulation",
                "files": "File Management",
                "results": "Experiment Results",
                "config": "Configuration",
            }
            self.statusBar().showMessage(f"{page_names[page_key]} - Ready")
    
    def _create_pages(self):
        """Create all application pages."""
        self.pages["dashboard"] = DashboardPage(self.project_root)
        self.pages["workflow"] = WorkflowPage(self.project_root)
        self.pages["manipulate"] = ManipulatePage(self.project_root)
        self.pages["files"] = FilesPage(self.project_root)
        self.pages["results"] = ResultsPage(self.project_root)
        self.pages["config"] = ConfigPage(self.project_root)
        
        # Add pages to stacked widget
        page_order = ["dashboard", "workflow", "manipulate", "files", "results", "config"]
        for page_key in page_order:
            self.stacked_widget.addWidget(self.pages[page_key])
    
    def _on_navigation_changed(self, index):
        """Handle navigation item selection."""
        # Skip separator and help/logout items
        if index >= 6:  # After Configuration
            if index == 7:  # Help & Support
                # TODO: Show help dialog
                return
            elif index == 8:  # Logout
                # TODO: Handle logout
                self.close()
                return
            return
        
        page_map = {
            0: "dashboard",
            1: "workflow",
            2: "manipulate",
            3: "files",
            4: "results",
            5: "config",
        }
        
        if index in page_map:
            page_key = page_map[index]
            page_index = list(self.pages.keys()).index(page_key)
            self.stacked_widget.setCurrentIndex(page_index)
            
            # Update status bar
            page_names = {
                "dashboard": "Dashboard Overview",
                "workflow": "Workflow Management",
                "manipulate": "Audio Manipulation",
                "files": "File Management",
                "results": "Experiment Results",
                "config": "Configuration",
            }
            self.statusBar().showMessage(f"{page_names[page_key]} - Ready")
