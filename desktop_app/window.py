"""
Main window for the Audio Fingerprint Robustness Lab desktop application.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QPen, QPolygon
from pathlib import Path
import sys

# Import page widgets
from desktop_app.pages.dashboard import DashboardPage
from desktop_app.pages.manipulate import ManipulatePage
from desktop_app.pages.files import FilesPage
from desktop_app.pages.results import ResultsPage
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
        copyright_label = QLabel("© 2025 Workflow Maestro. All rights reserved.")
        layout.addWidget(copyright_label)


class WorkflowMaestroLogo(QWidget):
    """Workflow Maestro logo - blue square with 4 white squares."""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(24, 24)
    
    def paintEvent(self, event):
        """Draw the logo."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Blue square background
        painter.setBrush(QBrush(QColor(66, 126, 234)))  # Blue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 24, 24, 4, 4)
        
        # Four white squares inside (2x2 grid)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        square_size = 6
        spacing = 2
        start_x = 5
        start_y = 5
        
        # Top left
        painter.drawRect(start_x, start_y, square_size, square_size)
        # Top right
        painter.drawRect(start_x + square_size + spacing, start_y, square_size, square_size)
        # Bottom left
        painter.drawRect(start_x, start_y + square_size + spacing, square_size, square_size)
        # Bottom right
        painter.drawRect(start_x + square_size + spacing, start_y + square_size + spacing, square_size, square_size)


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
            # Four rounded rectangles in a 2x2 grid (dashboard icon) - outline style
            rect_size = 7
            spacing = 2
            start_x = 3
            start_y = 3
            
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))  # White outline
            
            # Draw 2x2 grid of rounded rectangles
            for i in range(2):
                for j in range(2):
                    x = start_x + j * (rect_size + spacing)
                    y = start_y + i * (rect_size + spacing)
                    painter.drawRoundedRect(int(x), int(y), rect_size, rect_size, 2, 2)
        
        elif self.icon_type == "manipulate":
            # Musical note - outline style
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))  # White outline
            # Note head (oval outline)
            painter.drawEllipse(7, 9, 8, 6)
            # Note stem (vertical line)
            painter.drawLine(14, 3, 14, 9)
            # Note flag (curved line extending right)
            painter.drawLine(14, 3, 17, 1)
        
        elif self.icon_type == "files":
            # Folder icon - outline style
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Folder body (rectangle outline)
            painter.drawRect(4, 7, 12, 9)
            # Folder tab (smaller rectangle on top left, slightly open)
            painter.drawRect(4, 7, 8, 3)
            # Tab connection line
            painter.drawLine(12, 7, 12, 10)
        
        elif self.icon_type == "results":
            # Three vertical bars of increasing height (outline style)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Three bars from left to right with increasing height
            bar_width = 3
            bar_spacing = 3
            x_start = 4
            y_base = 16
            
            # First bar (shortest)
            bar1_height = 4
            painter.drawRect(x_start, y_base - bar1_height, bar_width, bar1_height)
            
            # Second bar (medium)
            bar2_height = 7
            painter.drawRect(x_start + (bar_width + bar_spacing), y_base - bar2_height, bar_width, bar2_height)
            
            # Third bar (tallest)
            bar3_height = 10
            painter.drawRect(x_start + (bar_width + bar_spacing) * 2, y_base - bar3_height, bar_width, bar3_height)


class NavigationItem(QWidget):
    """Custom navigation item with icon and text."""
    
    def __init__(self, icon_type, text):
        super().__init__()
        self.icon_type = icon_type
        self.text = text
        self.is_selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the navigation item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
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
            self.setStyleSheet("background-color: #3d3d3d; border-radius: 6px;")
            self.label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
            self.icon.is_selected = True
        else:
            self.setStyleSheet("background-color: transparent; border: none;")
            self.label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
            self.icon.is_selected = False
        self.icon.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("Workflow Maestro")
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
        sidebar.setMaximumWidth(250)
        sidebar.setMinimumWidth(220)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 15, 12, 15)
        layout.setSpacing(8)
        
        # Workflow Maestro title (no icon)
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(8)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("Workflow Maestro")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        logo_layout.addWidget(title_label)
        
        # Left arrow icon (for collapsing)
        arrow_label = QLabel("←")
        arrow_label.setStyleSheet("color: #9ca3af; font-size: 14px;")
        logo_layout.addWidget(arrow_label)
        logo_layout.addStretch()
        
        layout.addLayout(logo_layout)
        
        # Navigation items
        nav_items = [
            ("dashboard", "Dashboard"),
            ("manipulate", "Manipulate Audio"),
            ("files", "Files"),
            ("results", "Results"),
        ]
        
        self.nav_items = []
        for icon_type, text in nav_items:
            item = NavigationItem(icon_type, text)
            item.mousePressEvent = lambda e, idx=len(self.nav_items): self._on_nav_item_clicked(idx)
            layout.addWidget(item)
            self.nav_items.append(item)
        
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
    
    def _create_pages(self):
        """Create all application pages."""
        self.pages["dashboard"] = DashboardPage(self.project_root)
        self.pages["manipulate"] = ManipulatePage(self.project_root)
        self.pages["files"] = FilesPage(self.project_root)
        self.pages["results"] = ResultsPage(self.project_root)
        
        # Add pages to stacked widget
        page_order = ["dashboard", "manipulate", "files", "results"]
        for page_key in page_order:
            self.stacked_widget.addWidget(self.pages[page_key])
    
    def _on_navigation_changed(self, index):
        """Handle navigation item selection."""
        if index >= 4:  # Out of range
            return
        
        page_map = {
            0: "dashboard",
            1: "manipulate",
            2: "files",
            3: "results",
        }
        
        if index in page_map:
            page_key = page_map[index]
            page_index = list(self.pages.keys()).index(page_key)
            self.stacked_widget.setCurrentIndex(page_index)
            
            # Update status bar
            page_names = {
                "dashboard": "Dashboard Overview",
                "manipulate": "Audio Manipulation",
                "files": "File Management",
                "results": "Experiment Results",
            }
            self.statusBar().showMessage(f"{page_names[page_key]} - Ready")
