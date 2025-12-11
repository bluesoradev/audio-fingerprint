"""
Configuration page for application settings.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QComboBox, QGroupBox, QFormLayout,
    QFileDialog, QSlider, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path


class ToggleSwitch(QWidget):
    """Custom toggle switch widget matching the design."""
    
    def __init__(self, initial_state=False):
        super().__init__()
        self.state = initial_state
        self.setFixedSize(48, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def paintEvent(self, event):
        """Draw the toggle switch."""
        from PyQt6.QtGui import QPainter, QColor, QBrush
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background - blue when ON, dark gray when OFF
        if self.state:
            bg_color = QColor(66, 126, 234)  # Blue when ON
        else:
            bg_color = QColor(45, 45, 45)  # Dark gray when OFF
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        # Thumb (white circle)
        thumb_size = 18
        thumb_margin = 3
        if self.state:
            # Position on the right when ON
            thumb_x = self.width() - thumb_size - thumb_margin
        else:
            # Position on the left when OFF
            thumb_x = thumb_margin
        
        thumb_y = (self.height() - thumb_size) // 2
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(thumb_x, thumb_y, thumb_size, thumb_size)
    
    def mousePressEvent(self, event):
        """Toggle state on click."""
        self.state = not self.state
        self.update()
        self.stateChanged.emit(self.state)
    
    def isChecked(self):
        """Get current state."""
        return self.state
    
    def setChecked(self, state):
        """Set state."""
        self.state = state
        self.update()
    
    stateChanged = pyqtSignal(bool)


class ConfigPage(QWidget):
    """Configuration settings page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.setStyleSheet("background-color: #1e1e1e;")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header (fixed at top)
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #1e1e1e;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(30, 30, 30, 20)
        header_layout.setSpacing(0)
        
        title = QLabel("Configuration")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Manage your application settings and experiment defaults.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 14px; margin-top: 5px;")
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header_widget)
        
        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
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
        """)
        
        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #1e1e1e;")
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 0, 30, 30)
        
        # General Settings
        general_group = QGroupBox("General Settings")
        general_group.setStyleSheet("""
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
        general_layout = QVBoxLayout(general_group)
        
        general_subtitle = QLabel("Configure basic application preferences.")
        general_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        general_layout.addWidget(general_subtitle)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Style form labels
        form_label_style = "color: #c8c8c8; font-size: 14px;"
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 1px solid #427eea;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #427eea;
                selection-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
            }
        """)
        theme_label = QLabel("App Theme:")
        theme_label.setStyleSheet(form_label_style)
        form_layout.addRow(theme_label, self.theme_combo)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Spanish", "French", "German"])
        self.language_combo.setStyleSheet(self.theme_combo.styleSheet())
        language_label = QLabel("Language:")
        language_label.setStyleSheet(form_label_style)
        form_layout.addRow(language_label, self.language_combo)
        
        general_layout.addLayout(form_layout)
        layout.addWidget(general_group)
        
        # File Paths
        paths_group = QGroupBox("File Paths")
        paths_group.setStyleSheet(general_group.styleSheet())
        paths_layout = QVBoxLayout(paths_group)
        
        paths_subtitle = QLabel("Define directories for audio input and output.")
        paths_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        paths_layout.addWidget(paths_subtitle)
        
        paths_form = QFormLayout()
        paths_form.setSpacing(12)
        paths_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        input_dir_label = QLabel("Audio Input Directory:")
        input_dir_label.setStyleSheet(form_label_style)
        self.input_dir_edit = QLineEdit(str(self.project_root / "data" / "originals"))
        self.input_dir_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
                color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #9ca3af;
            }
        """)
        paths_form.addRow(input_dir_label, self.input_dir_edit)
        
        output_dir_label = QLabel("Output Directory:")
        output_dir_label.setStyleSheet(form_label_style)
        self.output_dir_edit = QLineEdit(str(self.project_root / "data" / "transformed"))
        self.output_dir_edit.setStyleSheet(self.input_dir_edit.styleSheet())
        paths_form.addRow(output_dir_label, self.output_dir_edit)
        
        paths_layout.addLayout(paths_form)
        layout.addWidget(paths_group)
        
        # Notification Preferences
        notif_group = QGroupBox("Notification Preferences")
        notif_group.setStyleSheet(general_group.styleSheet())
        notif_layout = QVBoxLayout(notif_group)
        
        notif_subtitle = QLabel("Manage how you receive alerts from the system.")
        notif_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 15px;")
        notif_layout.addWidget(notif_subtitle)
        
        # Email Notifications
        email_row = QHBoxLayout()
        email_label = QLabel("Email Notifications")
        email_label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
        email_row.addWidget(email_label)
        email_row.addStretch()
        self.email_notif_toggle = ToggleSwitch(True)
        email_row.addWidget(self.email_notif_toggle)
        notif_layout.addLayout(email_row)
        notif_layout.addSpacing(12)
        
        # Desktop Alerts
        desktop_row = QHBoxLayout()
        desktop_label = QLabel("Desktop Alerts")
        desktop_label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
        desktop_row.addWidget(desktop_label)
        desktop_row.addStretch()
        self.desktop_alert_toggle = ToggleSwitch(False)
        desktop_row.addWidget(self.desktop_alert_toggle)
        notif_layout.addLayout(desktop_row)
        notif_layout.addSpacing(12)
        
        # Play Sound for Alerts
        sound_row = QHBoxLayout()
        sound_label = QLabel("Play Sound for Alerts")
        sound_label.setStyleSheet("color: #c8c8c8; font-size: 14px;")
        sound_row.addWidget(sound_label)
        sound_row.addStretch()
        self.sound_alert_toggle = ToggleSwitch(True)
        sound_row.addWidget(self.sound_alert_toggle)
        notif_layout.addLayout(sound_row)
        
        layout.addWidget(notif_group)
        
        # Experiment Defaults
        exp_group = QGroupBox("Experiment Defaults")
        exp_group.setStyleSheet(general_group.styleSheet())
        exp_layout = QVBoxLayout(exp_group)
        
        exp_subtitle = QLabel("Set default values for new experiments.")
        exp_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        exp_layout.addWidget(exp_subtitle)
        
        exp_form = QFormLayout()
        exp_form.setSpacing(12)
        exp_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        prefix_label = QLabel("Experiment Name Prefix:")
        prefix_label.setStyleSheet(form_label_style)
        self.prefix_edit = QLineEdit("exp_run_")
        self.prefix_edit.setStyleSheet(self.input_dir_edit.styleSheet())
        exp_form.addRow(prefix_label, self.prefix_edit)
        
        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(8000, 192000)
        self.sample_rate_spin.setValue(44100)
        self.sample_rate_spin.setSuffix(" Hz")
        self.sample_rate_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                min-width: 200px;
            }
            QSpinBox:hover {
                border: 1px solid #427eea;
            }
            QSpinBox:focus {
                border: 1px solid #427eea;
                color: #ffffff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d3d3d;
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4d4d4d;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 0px;
                height: 0px;
            }
        """)
        sample_rate_label = QLabel("Default Sample Rate (Hz):")
        sample_rate_label.setStyleSheet(form_label_style)
        exp_form.addRow(sample_rate_label, self.sample_rate_spin)
        
        # Auto-save interval slider
        slider_layout = QHBoxLayout()
        self.autosave_slider = QSlider(Qt.Orientation.Horizontal)
        self.autosave_slider.setRange(1, 60)
        self.autosave_slider.setValue(15)
        self.autosave_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #2d2d2d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #427eea;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #3464ba;
            }
        """)
        self.autosave_label = QLabel("15 min")
        self.autosave_label.setStyleSheet("color: #c8c8c8; min-width: 60px;")
        self.autosave_slider.valueChanged.connect(
            lambda v: self.autosave_label.setText(f"{v} min")
        )
        slider_layout.addWidget(self.autosave_slider)
        slider_layout.addWidget(self.autosave_label)
        autosave_label = QLabel("Auto-save Interval (minutes):")
        autosave_label.setStyleSheet(form_label_style)
        exp_form.addRow(autosave_label, slider_layout)
        
        exp_layout.addLayout(exp_form)
        layout.addWidget(exp_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #c8c8c8;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)
        
        # Action buttons (fixed at bottom)
        button_widget = QWidget()
        button_widget.setStyleSheet("background-color: #1e1e1e;")
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(30, 15, 30, 30)
        button_layout.setSpacing(0)
        
        button_layout.addStretch()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #c8c8c8;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        main_layout.addWidget(button_widget)
    
    def load_settings(self):
        """Load settings from config file."""
        # TODO: Load from config file
        pass
    
    def save_settings(self):
        """Save settings to config file."""
        # TODO: Save to config file
        pass
    
    def reset_to_defaults(self):
        """Reset settings to defaults."""
        self.theme_combo.setCurrentText("Dark")
        self.language_combo.setCurrentText("English")
        self.input_dir_edit.setText(str(self.project_root / "data" / "originals"))
        self.output_dir_edit.setText(str(self.project_root / "data" / "transformed"))
        self.email_notif_toggle.setChecked(True)
        self.desktop_alert_toggle.setChecked(False)
        self.sound_alert_toggle.setChecked(True)
        self.prefix_edit.setText("exp_run_")
        self.sample_rate_spin.setValue(44100)
        self.autosave_slider.setValue(15)
