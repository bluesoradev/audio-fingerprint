"""
Audio manipulation page for applying transforms.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QFileDialog, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygon
from pathlib import Path
import threading
import time
import logging
import subprocess
import platform
import os
from threading import Lock

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler if it doesn't exist
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Try to import audio playback libraries
try:
    import sounddevice as sd
    import soundfile as sf
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    try:
        from pydub import AudioSegment
        from pydub.playback import play
        HAS_PYDUB = True
    except ImportError:
        HAS_PYDUB = False


class CircularPlayButton(QPushButton):
    """Custom circular play button with outline triangle icon."""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(40, 40)
        self.is_playing = False
        self.setStyleSheet("""
            QPushButton {
                background-color: #6a5acd;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #5a4abd;
            }
        """)
    
    def paintEvent(self, event):
        """Draw the play/pause icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        if self.is_playing:
            # Draw pause icon (two vertical bars)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            # Left bar
            painter.drawRect(center_x - 6, center_y - 5, 2, 10)
            # Right bar
            painter.drawRect(center_x + 4, center_y - 5, 2, 10)
        else:
            # Draw play icon (outline triangle pointing right)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Triangle points (outline style)
            triangle_size = 8
            triangle_points = [
                QPoint(center_x - 3, center_y - triangle_size // 2),
                QPoint(center_x - 3, center_y + triangle_size // 2),
                QPoint(center_x + 5, center_y)
            ]
            triangle = QPolygon(triangle_points)
            painter.drawPolyline(triangle)
    
    def set_playing(self, playing):
        """Set playing state."""
        self.is_playing = playing
        self.update()


class ManipulatePage(QWidget):
    """Audio manipulation page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.original_audio_path = None
        self.transformed_audio_path = None
        self.original_playing = False
        self.transformed_playing = False
        self.original_thread = None
        self.transformed_thread = None
        self.original_stop_event = threading.Event()
        self.transformed_stop_event = threading.Event()
        self.original_stream = None
        self.transformed_stream = None
        self.original_stream_lock = threading.Lock()
        self.transformed_stream_lock = threading.Lock()
        self.original_process = None
        self.transformed_process = None
        self.original_process_lock = threading.Lock()
        self.transformed_process_lock = threading.Lock()
        self.original_position = 0
        self.transformed_position = 0
        self.original_duration = 0
        self.transformed_duration = 0
        self.original_start_time = 0
        self.transformed_start_time = 0
        self.original_position_lock = Lock()
        self.transformed_position_lock = Lock()
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_positions)
        self.position_timer.start(100)  # Update every 100ms
        self.transform_chain = []  # List of transform dictionaries
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        title = QLabel("Audio Manipulation")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Main content area with left and right columns
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left column for controls
        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        
        # File selection
        file_group = QGroupBox("Select Audio File")
        file_group.setStyleSheet("""
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
        file_layout = QHBoxLayout(file_group)
        file_layout.setSpacing(10)
        
        audio_source_label = QLabel("Audio Source:")
        audio_source_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        file_layout.addWidget(audio_source_label)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select an audio file...")
        self.file_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                min-width: 400px;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
            }
        """)
        file_layout.addWidget(self.file_path_edit, 1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #427eea;
            }
        """)
        browse_btn.clicked.connect(self.browse_audio_file)
        file_layout.addWidget(browse_btn)
        
        left_column.addWidget(file_group)
        
        # Transform controls
        transform_group = QGroupBox("Audio Transform Controls")
        transform_group.setStyleSheet("""
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
        transform_layout = QFormLayout(transform_group)
        transform_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        transform_layout.setSpacing(15)
        
        # Speed
        speed_label_text = QLabel("Speed:")
        speed_label_text.setStyleSheet("color: #ffffff;")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 1000)
        self.speed_slider.setValue(100)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #ffffff;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background-color: #60a5fa;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #ffffff;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #9ca3af;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #f0f0f0;
            }
        """)
        self.speed_label = QLabel("1.0x")
        self.speed_label.setStyleSheet("color: #ffffff; min-width: 50px;")
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.speed_slider, 1)
        speed_layout.addWidget(self.speed_label)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v/100:.1f}x")
        )
        transform_layout.addRow(speed_label_text, speed_layout)
        
        # Pitch
        pitch_label_text = QLabel("Pitch (semitones):")
        pitch_label_text.setStyleSheet("color: #ffffff;")
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #ffffff;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background-color: #60a5fa;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #ffffff;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #9ca3af;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #f0f0f0;
            }
        """)
        self.pitch_label = QLabel("0")
        self.pitch_label.setStyleSheet("color: #ffffff; min-width: 50px;")
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(self.pitch_slider, 1)
        pitch_layout.addWidget(self.pitch_label)
        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_label.setText(str(v))
        )
        transform_layout.addRow(pitch_label_text, pitch_layout)
        
        # Noise Reduction
        noise_label_text = QLabel("Noise Reduction:")
        noise_label_text.setStyleSheet("color: #ffffff;")
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setRange(0, 100)
        self.noise_slider.setValue(50)
        self.noise_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #ffffff;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background-color: #60a5fa;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #ffffff;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #9ca3af;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #f0f0f0;
            }
        """)
        self.noise_label = QLabel("50%")
        self.noise_label.setStyleSheet("color: #ffffff; min-width: 50px;")
        noise_layout = QHBoxLayout()
        noise_layout.addWidget(self.noise_slider, 1)
        noise_layout.addWidget(self.noise_label)
        self.noise_slider.valueChanged.connect(
            lambda v: self.noise_label.setText(f"{v}%")
        )
        transform_layout.addRow(noise_label_text, noise_layout)
        
        # Reverb
        reverb_label_text = QLabel("Reverb Delay (ms):")
        reverb_label_text.setStyleSheet("color: #ffffff;")
        self.reverb_slider = QSlider(Qt.Orientation.Horizontal)
        self.reverb_slider.setRange(0, 500)
        self.reverb_slider.setValue(50)
        self.reverb_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #ffffff;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background-color: #60a5fa;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #ffffff;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #9ca3af;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #f0f0f0;
            }
        """)
        self.reverb_label = QLabel("50")
        self.reverb_label.setStyleSheet("color: #ffffff; min-width: 50px;")
        reverb_layout = QHBoxLayout()
        reverb_layout.addWidget(self.reverb_slider, 1)
        reverb_layout.addWidget(self.reverb_label)
        self.reverb_slider.valueChanged.connect(
            lambda v: self.reverb_label.setText(str(v))
        )
        transform_layout.addRow(reverb_label_text, reverb_layout)
        
        # EQ
        eq_label_text = QLabel("EQ Adjustment (dB):")
        eq_label_text.setStyleSheet("color: #ffffff;")
        self.eq_slider = QSlider(Qt.Orientation.Horizontal)
        self.eq_slider.setRange(-20, 20)
        self.eq_slider.setValue(0)
        self.eq_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #ffffff;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background-color: #60a5fa;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #ffffff;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #9ca3af;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #f0f0f0;
            }
        """)
        self.eq_label = QLabel("0")
        self.eq_label.setStyleSheet("color: #ffffff; min-width: 50px;")
        eq_layout = QHBoxLayout()
        eq_layout.addWidget(self.eq_slider, 1)
        eq_layout.addWidget(self.eq_label)
        self.eq_slider.valueChanged.connect(
            lambda v: self.eq_label.setText(f"{v} dB" if v != 0 else "0")
        )
        transform_layout.addRow(eq_label_text, eq_layout)
        
        # Audio Compression
        compression_label_text = QLabel("Audio Compression:")
        compression_label_text.setStyleSheet("color: #ffffff;")
        compression_layout = QHBoxLayout()
        
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["None", "MP3", "AAC", "OGG"])
        self.codec_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                min-width: 80px;
            }
            QComboBox:hover {
                border: 1px solid #427eea;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #427eea;
            }
        """)
        compression_layout.addWidget(self.codec_combo)
        
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["64k", "128k", "192k", "256k", "320k"])
        self.bitrate_combo.setCurrentText("128k")
        self.bitrate_combo.setStyleSheet(self.codec_combo.styleSheet())
        self.bitrate_combo.setEnabled(False)
        compression_layout.addWidget(self.bitrate_combo)
        
        self.codec_combo.currentTextChanged.connect(
            lambda v: self.bitrate_combo.setEnabled(v != "None")
        )
        
        compression_layout.addStretch()
        transform_layout.addRow(compression_label_text, compression_layout)
        
        # Overlay/Mixing
        overlay_label_text = QLabel("Overlay/Mixing:")
        overlay_label_text.setStyleSheet("color: #ffffff;")
        overlay_layout = QVBoxLayout()
        overlay_layout.setSpacing(8)
        
        overlay_file_layout = QHBoxLayout()
        self.overlay_path = QLineEdit()
        self.overlay_path.setPlaceholderText("Select overlay file (vocals, drums, etc.)...")
        self.overlay_path.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
            }
        """)
        overlay_file_layout.addWidget(self.overlay_path, 1)
        
        overlay_browse_btn = QPushButton("Browse...")
        overlay_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #427eea;
            }
        """)
        overlay_browse_btn.clicked.connect(self.browse_overlay_file)
        overlay_file_layout.addWidget(overlay_browse_btn)
        overlay_layout.addLayout(overlay_file_layout)
        
        gain_label_text = QLabel("Overlay Gain (dB):")
        gain_label_text.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.overlay_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.overlay_gain_slider.setRange(-20, 0)
        self.overlay_gain_slider.setValue(-6)
        self.overlay_gain_slider.setStyleSheet(self.speed_slider.styleSheet())
        self.overlay_gain_label = QLabel("-6")
        self.overlay_gain_label.setStyleSheet("color: #ffffff; min-width: 40px; font-size: 12px;")
        overlay_gain_layout = QHBoxLayout()
        overlay_gain_layout.addWidget(gain_label_text)
        overlay_gain_layout.addWidget(self.overlay_gain_slider, 1)
        overlay_gain_layout.addWidget(self.overlay_gain_label)
        self.overlay_gain_slider.valueChanged.connect(
            lambda v: self.overlay_gain_label.setText(str(v))
        )
        overlay_layout.addLayout(overlay_gain_layout)
        
        transform_layout.addRow(overlay_label_text, overlay_layout)
        
        # Transform Chain Builder
        chain_label_text = QLabel("Transform Chain:")
        chain_label_text.setStyleSheet("color: #ffffff;")
        chain_layout = QVBoxLayout()
        chain_layout.setSpacing(8)
        
        self.chain_list = QTextEdit()
        self.chain_list.setReadOnly(True)
        self.chain_list.setMaximumHeight(100)
        self.chain_list.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                color: #9ca3af;
                font-size: 11px;
            }
        """)
        self.chain_list.setPlainText("No transforms in chain. Adjust settings above and click 'Add to Chain'.")
        chain_layout.addWidget(self.chain_list)
        
        chain_buttons_layout = QHBoxLayout()
        add_to_chain_btn = QPushButton("Add to Chain")
        add_to_chain_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #427eea;
            }
        """)
        add_to_chain_btn.clicked.connect(self.add_to_chain)
        chain_buttons_layout.addWidget(add_to_chain_btn)
        
        clear_chain_btn = QPushButton("Clear Chain")
        clear_chain_btn.setStyleSheet(add_to_chain_btn.styleSheet())
        clear_chain_btn.clicked.connect(self.clear_chain)
        chain_buttons_layout.addWidget(clear_chain_btn)
        chain_buttons_layout.addStretch()
        chain_layout.addLayout(chain_buttons_layout)
        
        transform_layout.addRow(chain_label_text, chain_layout)
        
        # Apply button
        apply_btn = QPushButton("Apply Transforms")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #60a5fa;
                color: #ffffff;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
        """)
        apply_btn_layout = QHBoxLayout()
        apply_btn_layout.addStretch()
        apply_btn_layout.addWidget(apply_btn)
        apply_btn_layout.addStretch()
        transform_layout.addRow("", apply_btn_layout)
        apply_btn.clicked.connect(self.apply_transforms)
        
        left_column.addWidget(transform_group)
        
        # Output path
        output_group = QGroupBox("Output Status")
        output_group.setStyleSheet(transform_group.styleSheet())
        output_layout = QFormLayout(output_group)
        output_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        output_path_label = QLabel("Output Path:")
        output_path_label.setStyleSheet("color: #ffffff;")
        self.output_path = QLineEdit("data/manipulated/transformed_audio.wav")
        self.output_path.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
            }
        """)
        output_layout.addRow(output_path_label, self.output_path)
        
        progress_label = QLabel("Processing Progress:")
        progress_label.setStyleSheet("color: #ffffff;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)  # Show 100% in design
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #427eea;
                border-radius: 3px;
            }
        """)
        output_layout.addRow(progress_label, self.progress_bar)
        
        left_column.addWidget(output_group)
        left_column.addStretch()
        
        # Right column for audio players
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        
        # Original Audio Player
        original_player_group = QGroupBox("Original Audio")
        original_player_group.setStyleSheet("""
            QGroupBox {
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
                color: #ffffff;
                font-weight: bold;
            }
        """)
        original_player_layout = QVBoxLayout(original_player_group)
        original_player_layout.setSpacing(10)
        
        self.original_file_label = QLabel("Loaded: test_track_1.wav")
        self.original_file_label.setStyleSheet("color: #4ade80; font-size: 12px;")
        original_player_layout.addWidget(self.original_file_label)
        
        original_controls = QHBoxLayout()
        original_controls.setSpacing(15)
        self.original_play_btn = CircularPlayButton()
        self.original_play_btn.clicked.connect(self.toggle_original_playback)
        original_controls.addWidget(self.original_play_btn)
        
        self.original_time_label = QLabel("00:01 / 00:08")
        self.original_time_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        original_controls.addWidget(self.original_time_label)
        original_controls.addStretch()
        
        original_player_layout.addLayout(original_controls)
        right_column.addWidget(original_player_group)
        
        # Transformed Audio Player
        transformed_player_group = QGroupBox("Transformed Audio")
        transformed_player_group.setStyleSheet(original_player_group.styleSheet())
        transformed_player_layout = QVBoxLayout(transformed_player_group)
        transformed_player_layout.setSpacing(10)
        
        self.transformed_file_label = QLabel("Loaded: transformed_audio.wav")
        self.transformed_file_label.setStyleSheet("color: #4ade80; font-size: 12px;")
        transformed_player_layout.addWidget(self.transformed_file_label)
        
        transformed_controls = QHBoxLayout()
        transformed_controls.setSpacing(15)
        self.transformed_play_btn = CircularPlayButton()
        self.transformed_play_btn.clicked.connect(self.toggle_transformed_playback)
        transformed_controls.addWidget(self.transformed_play_btn)
        
        self.transformed_time_label = QLabel("00:00 / 00:04")
        self.transformed_time_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        transformed_controls.addWidget(self.transformed_time_label)
        transformed_controls.addStretch()
        
        transformed_player_layout.addLayout(transformed_controls)
        right_column.addWidget(transformed_player_group)
        
        # Test Fingerprint Robustness Section
        test_group = QGroupBox("Test Fingerprint Robustness")
        test_group.setStyleSheet(original_player_group.styleSheet())
        test_layout = QVBoxLayout(test_group)
        test_layout.setSpacing(10)
        
        test_subtitle = QLabel("Test if transformed audio can be matched to original")
        test_subtitle.setStyleSheet("color: #9ca3af; font-size: 12px; margin-bottom: 10px;")
        test_layout.addWidget(test_subtitle)
        
        # Original audio display (read-only, shows current selection)
        original_test_label = QLabel("Original Audio:")
        original_test_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        test_layout.addWidget(original_test_label)
        
        self.original_test_display = QLineEdit()
        self.original_test_display.setReadOnly(True)
        self.original_test_display.setPlaceholderText("No original audio selected...")
        self.original_test_display.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #9ca3af;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        test_layout.addWidget(self.original_test_display)
        
        # Transformed audio display (read-only, shows current selection)
        transformed_test_label = QLabel("Transformed Audio:")
        transformed_test_label.setStyleSheet("color: #ffffff; font-size: 12px; margin-top: 10px;")
        test_layout.addWidget(transformed_test_label)
        
        self.transformed_test_display = QLineEdit()
        self.transformed_test_display.setReadOnly(True)
        self.transformed_test_display.setPlaceholderText("No transformed audio available. Apply transforms first...")
        self.transformed_test_display.setStyleSheet(self.original_test_display.styleSheet())
        test_layout.addWidget(self.transformed_test_display)
        
        # Test button
        self.test_btn = QPushButton(" Test Fingerprint Match")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-radius: 6px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #9ca3af;
            }
        """)
        self.test_btn.setEnabled(False)
        self.test_btn.clicked.connect(self.test_fingerprint_match)
        test_layout.addWidget(self.test_btn)
        
        # Test results display
        self.test_results = QTextEdit()
        self.test_results.setReadOnly(True)
        self.test_results.setMaximumHeight(150)
        self.test_results.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                color: #c8c8c8;
                font-size: 12px;
            }
        """)
        self.test_results.setPlainText("Select an audio file and apply transforms, then click 'Test Fingerprint Match'")
        test_layout.addWidget(self.test_results)
        
        right_column.addWidget(test_group)
        right_column.addStretch()
        
        # Add columns to main content layout
        left_widget = QWidget()
        left_widget.setLayout(left_column)
        content_layout.addWidget(left_widget, 2)
        
        right_widget = QWidget()
        right_widget.setLayout(right_column)
        content_layout.addWidget(right_widget, 1)
        
        main_layout.addLayout(content_layout)
        
        # Initialize audio players
        self.init_audio_players()
    
    def init_audio_players(self):
        """Initialize audio players."""
        # Audio players are initialized in init_ui
        # Sliders were removed to match design - only play buttons and time labels remain
        if not HAS_SOUNDDEVICE and not HAS_PYDUB:
            # Show warning if no audio library available
            self.original_file_label.setText("Audio playback not available - install sounddevice or pydub")
            self.original_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
            self.transformed_file_label.setText("Audio playback not available")
            self.transformed_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
    
    def load_original_audio(self, file_path: str):
        """Load original audio file for playback."""
        self.original_audio_path = Path(file_path)
        if self.original_audio_path.exists():
            # Get duration
            try:
                if HAS_SOUNDDEVICE:
                    data, sample_rate = sf.read(str(self.original_audio_path))
                    self.original_duration = len(data) / sample_rate
                elif HAS_PYDUB:
                    audio = AudioSegment.from_file(str(self.original_audio_path))
                    self.original_duration = len(audio) / 1000.0
                else:
                    self.original_duration = 0
                
                with self.original_position_lock:
                    self.original_position = 0
                self.original_file_label.setText(f"Loaded: {self.original_audio_path.name}")
                self.original_file_label.setStyleSheet("color: #4ade80; font-size: 12px;")
                
                # Update test display
                if hasattr(self, 'original_test_display'):
                    self.original_test_display.setText(str(self.original_audio_path))
                    self.original_test_display.setStyleSheet("""
                        QLineEdit {
                            background-color: #1e1e1e;
                            color: #4ade80;
                            border: 1px solid #3d3d3d;
                            border-radius: 4px;
                            padding: 6px;
                            font-size: 12px;
                        }
                    """)
                    self._update_test_button_state()
            except Exception as e:
                self.original_file_label.setText(f"Error loading: {str(e)[:30]}")
                self.original_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
                if hasattr(self, 'original_test_display'):
                    self.original_test_display.setText("")
                    self.original_test_display.setPlaceholderText("No original audio selected...")
                    self._update_test_button_state()
        else:
            self.original_file_label.setText("File not found")
            self.original_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
            if hasattr(self, 'original_test_display'):
                self.original_test_display.setText("")
                self.original_test_display.setPlaceholderText("No original audio selected...")
                self._update_test_button_state()
    
    def load_transformed_audio(self, file_path: str):
        """Load transformed audio file for playback."""
        self.transformed_audio_path = Path(file_path)
        if self.transformed_audio_path.exists():
            # Get duration
            try:
                if HAS_SOUNDDEVICE:
                    data, sample_rate = sf.read(str(self.transformed_audio_path))
                    self.transformed_duration = len(data) / sample_rate
                elif HAS_PYDUB:
                    audio = AudioSegment.from_file(str(self.transformed_audio_path))
                    self.transformed_duration = len(audio) / 1000.0
                else:
                    self.transformed_duration = 0
                
                with self.transformed_position_lock:
                    self.transformed_position = 0
                self.transformed_file_label.setText(f"Loaded: {self.transformed_audio_path.name}")
                self.transformed_file_label.setStyleSheet("color: #4ade80; font-size: 12px;")
                self.transformed_play_btn.setEnabled(True)
                
                # Update test display
                if hasattr(self, 'transformed_test_display'):
                    self.transformed_test_display.setText(str(self.transformed_audio_path))
                    self.transformed_test_display.setStyleSheet("""
                        QLineEdit {
                            background-color: #1e1e1e;
                            color: #4ade80;
                            border: 1px solid #3d3d3d;
                            border-radius: 4px;
                            padding: 6px;
                            font-size: 12px;
                        }
                    """)
                    self._update_test_button_state()
            except Exception as e:
                self.transformed_file_label.setText(f"Error loading: {str(e)[:30]}")
                self.transformed_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
                self.transformed_play_btn.setEnabled(False)
        else:
            self.transformed_file_label.setText("File not found")
            self.transformed_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
            self.transformed_play_btn.setEnabled(False)
            if hasattr(self, 'transformed_test_display'):
                self.transformed_test_display.setText("")
                self.transformed_test_display.setPlaceholderText("No transformed audio available. Apply transforms first...")
                self._update_test_button_state()
    
    def _play_audio_sounddevice(self, file_path: Path, stop_event: threading.Event, position_attr: str, duration: float, lock: Lock, stream_lock: threading.Lock, stream_attr: str):
        """Play audio using sounddevice with proper stream control."""
        logger.info(f"_play_audio_sounddevice: Starting playback for {position_attr}")
        stream = None
        try:
            # Read audio file
            logger.debug(f"_play_audio_sounddevice: Reading audio file: {file_path}")
            data, file_sample_rate = sf.read(str(file_path))
            logger.debug(f"_play_audio_sounddevice: Audio loaded - samples: {len(data)}, sample_rate: {file_sample_rate}Hz")
            
            # Convert to mono if stereo
            if len(data.shape) > 1 and data.shape[1] > 1:
                data = data.mean(axis=1)
            
            # Use file's sample rate for playback
            playback_sample_rate = int(file_sample_rate)
            
            with lock:
                start_pos = getattr(self, position_attr) / 1000.0  # Convert ms to seconds
            start_sample = int(start_pos * file_sample_rate)
            
            if start_sample < len(data):
                data_to_play = data[start_sample:]
                
                if len(data_to_play) == 0:
                    return
                
                # Get start time for position tracking
                playback_start_time = time.time()
                actual_start_pos = start_pos
                audio_length_seconds = len(data_to_play) / file_sample_rate
                
                # Check if we should still play (might have been stopped while loading)
                if stop_event.is_set():
                    logger.warning(f"_play_audio_sounddevice: Stop event already set before starting, aborting")
                    return
                
                # Create and start stream
                logger.debug(f"_play_audio_sounddevice: Creating output stream (rate={playback_sample_rate}Hz, channels=1)")
                with stream_lock:
                    # Stop any existing stream first
                    existing_stream = getattr(self, stream_attr, None)
                    if existing_stream is not None:
                        logger.warning(f"_play_audio_sounddevice: Stopping existing stream")
                        try:
                            existing_stream.stop()
                            existing_stream.close()
                        except:
                            pass
                    
                    # Create new stream
                    stream = sd.OutputStream(samplerate=playback_sample_rate, channels=1, dtype=data.dtype)
                    stream.start()
                    setattr(self, stream_attr, stream)
                    logger.info(f"_play_audio_sounddevice: Stream created and started successfully")
                
                # Check again after creating stream
                if stop_event.is_set():
                    logger.warning(f"_play_audio_sounddevice: Stop event set after creating stream, aborting")
                    with stream_lock:
                        if stream:
                            try:
                                stream.stop()
                                stream.close()
                            except:
                                pass
                            setattr(self, stream_attr, None)
                    return
                
                # Write audio data to stream
                logger.info(f"_play_audio_sounddevice: Writing {len(data_to_play)} samples to stream (audio length: {audio_length_seconds:.2f}s)")
                try:
                    stream.write(data_to_play)
                    logger.debug(f"_play_audio_sounddevice: Audio data written to stream, playback started")
                except Exception as e:
                    logger.error(f"_play_audio_sounddevice: Error writing to stream: {e}")
                
                # Track position while playing - check stop event very frequently
                logger.debug(f"_play_audio_sounddevice: Entering position tracking loop")
                while not stop_event.is_set():
                    if stop_event.is_set():
                        break
                    
                    # Calculate elapsed time
                    elapsed = time.time() - playback_start_time
                    current_pos = actual_start_pos + elapsed
                    
                    # Update position
                    with lock:
                        setattr(self, position_attr, min(current_pos * 1000, duration * 1000))
                    
                    # Check if playback finished (based on elapsed time)
                    if elapsed >= audio_length_seconds or current_pos >= duration:
                        logger.info(f"_play_audio_sounddevice: Audio finished naturally (elapsed: {elapsed:.2f}s, length: {audio_length_seconds:.2f}s)")
                        break
                    
                    # Check stop event very frequently (every 10ms)
                    time.sleep(0.01)
                    if stop_event.is_set():
                        logger.info(f"_play_audio_sounddevice: Stop event detected in tracking loop (elapsed: {elapsed:.2f}s)")
                        break
                
                # Save current position when stopping
                if stop_event.is_set():
                    with lock:
                        elapsed = time.time() - playback_start_time
                        current_pos = actual_start_pos + elapsed
                        saved_pos = min(current_pos * 1000, duration * 1000)
                        setattr(self, position_attr, saved_pos)
                    logger.info(f"_play_audio_sounddevice: Playback PAUSED - saved position: {saved_pos:.0f}ms")
                else:
                    # Audio finished naturally
                        with lock:
                            setattr(self, position_attr, duration * 1000)
                logger.info(f"_play_audio_sounddevice: Playback FINISHED - position set to end: {duration*1000:.0f}ms")
        except Exception as e:
            logger.error(f"_play_audio_sounddevice: Error playing audio: {e}")
            import traceback
            traceback.print_exc()
            try:
                sd.stop()
            except:
                pass
        finally:
            # Stop and close stream
            logger.debug(f"_play_audio_sounddevice: Cleaning up stream")
            with stream_lock:
                if stream:
                    try:
                        stream.stop()
                        stream.close()
                        logger.debug(f"_play_audio_sounddevice: Stream stopped and closed")
                    except Exception as e:
                        logger.error(f"_play_audio_sounddevice: Error closing stream: {e}")
                if getattr(self, stream_attr, None) == stream:
                    setattr(self, stream_attr, None)
                    logger.debug(f"_play_audio_sounddevice: Stream reference cleared")
            
            # Only reset playing state if stop_event was NOT set (audio finished naturally)
            if not stop_event.is_set():
                # Audio finished naturally - reset state
                logger.info(f"_play_audio_sounddevice: Audio finished naturally, resetting state")
                if position_attr == 'original_position':
                    self.original_playing = False
                    self.original_play_btn.set_playing(False)
                elif position_attr == 'transformed_position':
                    self.transformed_playing = False
                    self.transformed_play_btn.set_playing(False)
            else:
                logger.debug(f"_play_audio_sounddevice: Stop event was set (paused), not resetting state")
    
    def _play_audio_pydub(self, file_path: Path, stop_event: threading.Event, position_attr: str, duration: float, lock: Lock, stream_lock: threading.Lock, stream_attr: str):
        """Play audio using pydub with proper stream control."""
        logger.info(f"_play_audio_pydub: Starting playback for {position_attr}")
        stream = None
        temp_path = None
        try:
            logger.debug(f"_play_audio_pydub: Loading audio file: {file_path}")
            audio = AudioSegment.from_file(str(file_path))
            logger.debug(f"_play_audio_pydub: Audio loaded - length: {len(audio)}ms, frame_rate: {audio.frame_rate}Hz, channels: {audio.channels}")
            
            # Ensure correct sample rate (44100 Hz)
            if audio.frame_rate != 44100:
                logger.debug(f"_play_audio_pydub: Converting sample rate from {audio.frame_rate}Hz to 44100Hz")
                audio = audio.set_frame_rate(44100)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                logger.debug(f"_play_audio_pydub: Converting from {audio.channels} channels to mono")
                audio = audio.set_channels(1)
            
            with lock:
                start_pos_ms = getattr(self, position_attr)
            logger.info(f"_play_audio_pydub: Starting from position: {start_pos_ms}ms / {len(audio)}ms")
            
            if start_pos_ms < len(audio):
                audio_to_play = audio[start_pos_ms:]
                
                if len(audio_to_play) == 0:
                    logger.warning(f"_play_audio_pydub: No audio to play (start_pos: {start_pos_ms}ms, total: {len(audio)}ms)")
                    return
                
                # Export to temporary WAV file for playback
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                logger.debug(f"_play_audio_pydub: Exporting audio segment to temp file: {temp_path}")
                audio_to_play.export(temp_path, format="wav")
                
                # Use sounddevice with stream objects if available (better control)
                if HAS_SOUNDDEVICE:
                    logger.debug(f"_play_audio_pydub: Using sounddevice with stream objects")
                    data, sr = sf.read(temp_path)
                    if len(data.shape) > 1:
                        data = data.mean(axis=1)
                    
                    playback_start_time = time.time()
                    actual_start_pos = start_pos_ms / 1000.0
                    audio_length_seconds = len(data) / sr
                    logger.debug(f"_play_audio_pydub: Audio segment - samples: {len(data)}, sample_rate: {sr}Hz, length: {audio_length_seconds:.2f}s")
                    
                    # Check if we should still play (might have been stopped while loading)
                    if stop_event.is_set():
                        logger.warning(f"_play_audio_pydub: Stop event already set before starting, aborting")
                        return
                    
                    # Create and start stream
                    logger.debug(f"_play_audio_pydub: Creating output stream (rate={sr}Hz, channels=1)")
                    with stream_lock:
                        # Stop any existing stream first
                        existing_stream = getattr(self, stream_attr, None)
                        if existing_stream is not None:
                            logger.warning(f"_play_audio_pydub: Stopping existing stream")
                            try:
                                existing_stream.stop()
                                existing_stream.close()
                            except:
                                pass
                        
                        # Create new stream
                        stream = sd.OutputStream(samplerate=sr, channels=1, dtype=data.dtype)
                        stream.start()
                        setattr(self, stream_attr, stream)
                        logger.info(f"_play_audio_pydub: Stream created and started successfully")
                    
                    # Check again after creating stream
                    if stop_event.is_set():
                        logger.warning(f"_play_audio_pydub: Stop event set after creating stream, aborting")
                        with stream_lock:
                            if stream:
                                try:
                                    stream.stop()
                                    stream.close()
                                except:
                                    pass
                                setattr(self, stream_attr, None)
                        return
                    
                    # Write audio data to stream
                    logger.info(f"_play_audio_pydub: Writing {len(data)} samples to stream (audio length: {audio_length_seconds:.2f}s)")
                    try:
                        stream.write(data)
                        logger.debug(f"_play_audio_pydub: Audio data written to stream, playback started")
                    except Exception as e:
                        logger.error(f"_play_audio_pydub: Error writing to stream: {e}")
                    
                    # Track position while playing - check stop event very frequently
                    logger.debug(f"_play_audio_pydub: Entering position tracking loop")
                    while not stop_event.is_set():
                        elapsed = time.time() - playback_start_time
                        current_pos_ms = start_pos_ms + (elapsed * 1000)
                        
                        with lock:
                            setattr(self, position_attr, min(current_pos_ms, len(audio)))
                        
                        if elapsed >= audio_length_seconds:
                            logger.info(f"_play_audio_pydub: Audio finished naturally (elapsed: {elapsed:.2f}s, length: {audio_length_seconds:.2f}s)")
                            break
                        
                        # Check stop event very frequently (every 10ms)
                        time.sleep(0.01)
                    
                    # Save current position when stopping
                    if stop_event.is_set():
                        with lock:
                            elapsed = time.time() - playback_start_time
                            current_pos_ms = start_pos_ms + (elapsed * 1000)
                            saved_pos = min(current_pos_ms, len(audio))
                            setattr(self, position_attr, saved_pos)
                        logger.info(f"_play_audio_pydub: Playback PAUSED - saved position: {saved_pos:.0f}ms")
                    else:
                        # Audio finished naturally
                        with lock:
                            setattr(self, position_attr, len(audio))
                        logger.info(f"_play_audio_pydub: Playback FINISHED - position set to end: {len(audio)}ms")
                    
                    # Stop and close stream
                    logger.debug(f"_play_audio_pydub: Cleaning up stream")
                    with stream_lock:
                        if stream:
                            try:
                                stream.stop()
                                stream.close()
                                logger.debug(f"_play_audio_pydub: Stream stopped and closed")
                            except Exception as e:
                                logger.error(f"_play_audio_pydub: Error closing stream: {e}")
                        if getattr(self, stream_attr, None) == stream:
                            setattr(self, stream_attr, None)
                            logger.debug(f"_play_audio_pydub: Stream reference cleared")
                else:
                    # Fallback: use subprocess to play audio (can be killed)
                    logger.warning(f"_play_audio_pydub: Using subprocess fallback (no sounddevice)")

                    temp_play_path = None
                    process = None
                    try:
                        # Export to WAV file for playback
                        temp_play_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                        temp_play_path = temp_play_file.name
                        temp_play_file.close()
                        audio_to_play.export(temp_play_path, format="wav")

                        playback_start_time = time.time()
                        audio_length_seconds = len(audio_to_play) / 1000.0

                        # Play using system player (can be killed)
                        if platform.system() == "Windows":
                            # Use Windows Media Player or powershell
                            try:
                                # Try using ffplay if available (from ffmpeg)
                                process = subprocess.Popen(
                                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_play_path],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL
                                )
                                logger.debug(f"_play_audio_pydub: Using ffplay for playback")
                            except FileNotFoundError:
                                # Fallback to Windows Media Player via start command
                                process = subprocess.Popen(
                                    ["cmd", "/c", "start", "/min", "wmplayer.exe", "/play", "/close", temp_play_path],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    shell=True
                                )
                                logger.debug(f"_play_audio_pydub: Using Windows Media Player for playback")
                        elif platform.system() == "Darwin":  # macOS
                            process = subprocess.Popen(
                                ["afplay", temp_play_path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            logger.debug(f"_play_audio_pydub: Using afplay for playback")
                        else:  # Linux
                            process = subprocess.Popen(
                                ["aplay", temp_play_path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            logger.debug(f"_play_audio_pydub: Using aplay for playback")

                        # Store process reference so we can kill it
                        if stream_attr == 'original_stream':
                            process_attr = 'original_process'
                            process_lock = self.original_process_lock
                        else:
                            process_attr = 'transformed_process'
                            process_lock = self.transformed_process_lock

                        with process_lock:
                            setattr(self, process_attr, process)

                        logger.info(f"_play_audio_pydub: Subprocess started (PID: {process.pid})")

                        # Track position while playing - check stop event very frequently
                        logger.debug(f"_play_audio_pydub: Entering subprocess position tracking loop")
                        while process.poll() is None:  # Process still running
                            if stop_event.is_set():
                                logger.info(f"_play_audio_pydub: Stop event detected, terminating process")
                                try:
                                    process.terminate()
                                    process.wait(timeout=1.0)
                                    logger.debug(f"_play_audio_pydub: Process terminated successfully")
                                except subprocess.TimeoutExpired:
                                    logger.warning(f"_play_audio_pydub: Process didn't terminate, killing it")
                                    try:
                                        process.kill()
                                        process.wait(timeout=0.5)
                                    except Exception:
                                        pass
                                break
                            
                            # Calculate elapsed time
                            elapsed = time.time() - playback_start_time
                            current_pos_ms = start_pos_ms + (elapsed * 1000)
                            
                            # Update position
                            with lock:
                                setattr(self, position_attr, min(current_pos_ms, len(audio)))
                            
                            # Check if playback finished (based on elapsed time)
                            if elapsed >= audio_length_seconds:
                                logger.info(f"_play_audio_pydub: Audio finished naturally (elapsed: {elapsed:.2f}s, length: {audio_length_seconds:.2f}s)")
                                break
                            
                            # Check stop event very frequently (every 10ms)
                            time.sleep(0.01)

                        # Wait for process to finish if not stopped
                        if not stop_event.is_set() and process.poll() is None:
                            process.wait()

                        # Save current position when stopping
                        if stop_event.is_set():
                            with lock:
                                elapsed = time.time() - playback_start_time
                                current_pos_ms = start_pos_ms + (elapsed * 1000)
                                saved_pos = min(current_pos_ms, len(audio))
                                setattr(self, position_attr, saved_pos)
                            logger.info(f"_play_audio_pydub: Playback PAUSED - saved position: {saved_pos:.0f}ms")
                        else:
                            # Audio finished naturally
                            with lock:
                                setattr(self, position_attr, len(audio))
                            logger.info(f"_play_audio_pydub: Playback FINISHED - position set to end: {len(audio)}ms")
                    except Exception as e:
                        logger.error(f"_play_audio_pydub: Error in subprocess playback: {e}")
                        if process is not None:
                            try:
                                if process.poll() is None:
                                    process.terminate()
                                    process.wait(timeout=0.5)
                            except Exception:
                                try:
                                    process.kill()
                                except Exception:
                                    pass
                    finally:
                        # Clear process reference
                        if stream_attr == 'original_stream':
                            process_attr = 'original_process'
                            process_lock = self.original_process_lock
                        else:
                            process_attr = 'transformed_process'
                            process_lock = self.transformed_process_lock

                        with process_lock:
                            if getattr(self, process_attr, None) is process:
                                setattr(self, process_attr, None)
                                logger.debug(f"_play_audio_pydub: Process reference cleared")

                        # Clean up temp play file
                        if temp_play_path and os.path.exists(temp_play_path):
                            try:
                                os.unlink(temp_play_path)
                                logger.debug(f"_play_audio_pydub: Temp play file cleaned up: {temp_play_path}")
                            except Exception as e:
                                logger.warning(f"_play_audio_pydub: Error cleaning up temp play file: {e}")
        except Exception as e:
            logger.error(f"_play_audio_pydub: Error playing audio: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up temp file
            if temp_path:
                try:
                    os.unlink(temp_path)
                    logger.debug(f"_play_audio_pydub: Temp file cleaned up: {temp_path}")
                except Exception as e:
                    logger.warning(f"_play_audio_pydub: Error cleaning up temp file: {e}")
            
            # Clean up stream if using sounddevice
            if HAS_SOUNDDEVICE:
                logger.debug(f"_play_audio_pydub: Cleaning up stream in finally block")
                with stream_lock:
                    stream = getattr(self, stream_attr, None)
                    if stream is not None:
                        try:
                            stream.stop()
                            stream.close()
                            logger.debug(f"_play_audio_pydub: Stream stopped and closed in finally")
                        except Exception as e:
                            logger.error(f"_play_audio_pydub: Error closing stream in finally: {e}")
                        setattr(self, stream_attr, None)
                        logger.debug(f"_play_audio_pydub: Stream reference cleared in finally")
            
            # Clean up subprocess if using fallback
            if stream_attr == 'original_stream':
                process_attr = 'original_process'
                process_lock = self.original_process_lock
            else:
                process_attr = 'transformed_process'
                process_lock = self.transformed_process_lock
            
            logger.debug(f"_play_audio_pydub: Cleaning up subprocess in finally block")
            with process_lock:
                process = getattr(self, process_attr, None)
                if process is not None:
                    try:
                        if process.poll() is None:  # Process still running
                            process.terminate()
                            try:
                                process.wait(timeout=0.5)
                                logger.debug(f"_play_audio_pydub: Subprocess terminated in finally")
                            except subprocess.TimeoutExpired:
                                logger.warning(f"_play_audio_pydub: Subprocess didn't terminate, killing it")
                                try:
                                    process.kill()
                                    process.wait(timeout=0.2)
                                except:
                                    pass
                    except Exception as e:
                        logger.error(f"_play_audio_pydub: Error cleaning up subprocess: {e}")
                    setattr(self, process_attr, None)
                    logger.debug(f"_play_audio_pydub: Subprocess reference cleared in finally")
            
            # Only reset playing state if stop_event was NOT set (audio finished naturally)
            if not stop_event.is_set():
                # Audio finished naturally - reset state
                logger.info(f"_play_audio_pydub: Audio finished naturally, resetting state")
                if position_attr == 'original_position':
                    self.original_playing = False
                    self.original_play_btn.set_playing(False)
                elif position_attr == 'transformed_position':
                    self.transformed_playing = False
                    self.transformed_play_btn.set_playing(False)
            else:
                logger.debug(f"_play_audio_pydub: Stop event was set (paused), not resetting state")
    
    def toggle_original_playback(self):
        """Toggle original audio playback."""
        if not self.original_audio_path or not self.original_audio_path.exists():
            logger.warning("toggle_original_playback: No audio file loaded")
            return
        
        # Check current playing state - check flag first, then verify thread
        is_currently_playing = self.original_playing
        logger.info(f"toggle_original_playback: Button clicked. Current state: playing={is_currently_playing}, thread_alive={self.original_thread.is_alive() if self.original_thread else False}")
        
        if is_currently_playing:
            # PAUSE: Stop the audio immediately
            logger.info("toggle_original_playback: PAUSE button pressed - stopping audio")
            self.original_stop_event.set()
            logger.debug("toggle_original_playback: Stop event set")
            
            # Stop stream immediately if it exists
            stream_stopped = False
            with self.original_stream_lock:
                if self.original_stream is not None:
                    logger.debug("toggle_original_playback: Stopping and closing stream")
                    try:
                        self.original_stream.stop()
                        self.original_stream.close()
                        logger.debug("toggle_original_playback: Stream stopped and closed successfully")
                        stream_stopped = True
                    except Exception as e:
                        logger.error(f"toggle_original_playback: Error stopping stream: {e}")
                    self.original_stream = None
                else:
                    logger.debug("toggle_original_playback: No stream object found")
            
            # If no stream object, try to kill subprocess (for pydub fallback)
            if not stream_stopped:
                with self.original_process_lock:
                    if self.original_process is not None:
                        logger.debug("toggle_original_playback: Terminating subprocess")
                        try:
                            self.original_process.terminate()
                            self.original_process.wait(timeout=1.0)
                            logger.debug("toggle_original_playback: Subprocess terminated successfully")
                        except subprocess.TimeoutExpired:
                            logger.warning("toggle_original_playback: Subprocess didn't terminate, killing it")
                            try:
                                self.original_process.kill()
                                self.original_process.wait(timeout=0.5)
                            except:
                                pass
                        except Exception as e:
                            logger.error(f"toggle_original_playback: Error terminating subprocess: {e}")
                        self.original_process = None
                    elif HAS_SOUNDDEVICE:
                        # Try global stop as last resort
                        logger.debug("toggle_original_playback: Calling global sd.stop() as fallback")
                        try:
                            sd.stop()
                            logger.debug("toggle_original_playback: Global sd.stop() called")
                        except Exception as e:
                            logger.error(f"toggle_original_playback: Error calling global sd.stop(): {e}")
            
            # Update state immediately for UI responsiveness
            self.original_playing = False
            self.original_play_btn.set_playing(False)
            logger.info("toggle_original_playback: State updated - playing=False, button set to play icon")
            
            # Wait briefly for thread to finish (non-blocking with timeout)
            if self.original_thread and self.original_thread.is_alive():
                logger.debug("toggle_original_playback: Waiting for thread to finish (timeout=0.2s)")
                self.original_thread.join(timeout=0.2)
                if self.original_thread.is_alive():
                    logger.warning("toggle_original_playback: Thread still alive after timeout")
                else:
                    logger.debug("toggle_original_playback: Thread finished")
        else:
            # PLAY: Start or resume playback
            logger.info("toggle_original_playback: PLAY button pressed - starting audio")
            with self.original_position_lock:
                current_pos = self.original_position
            logger.info(f"toggle_original_playback: Resuming from position: {current_pos}ms / {self.original_duration*1000}ms")
            
            # First, ensure any previous thread is completely stopped
            if self.original_thread and self.original_thread.is_alive():
                logger.warning("toggle_original_playback: Previous thread still alive, forcing stop")
                # Force stop previous thread
                self.original_stop_event.set()
                
                # Stop stream if exists
                with self.original_stream_lock:
                    if self.original_stream is not None:
                        try:
                            self.original_stream.stop()
                            self.original_stream.close()
                        except:
                            pass
                        self.original_stream = None
                
                # Kill subprocess if exists
                with self.original_process_lock:
                    if self.original_process is not None:
                        try:
                            self.original_process.terminate()
                            self.original_process.wait(timeout=0.5)
                        except:
                            try:
                                self.original_process.kill()
                            except:
                                pass
                        self.original_process = None
                
                self.original_thread.join(timeout=0.2)
            
            # Stop transformed if playing
            if self.transformed_playing:
                logger.info("toggle_original_playback: Stopping transformed audio to play original")
                self.transformed_stop_event.set()
                self.transformed_playing = False
                self.transformed_play_btn.set_playing(False)
                
                # Stop stream if exists
                with self.transformed_stream_lock:
                    if self.transformed_stream is not None:
                        try:
                            self.transformed_stream.stop()
                            self.transformed_stream.close()
                        except:
                            pass
                        self.transformed_stream = None
                
                # Kill subprocess if exists
                with self.transformed_process_lock:
                    if self.transformed_process is not None:
                        try:
                            self.transformed_process.terminate()
                            self.transformed_process.wait(timeout=0.5)
                        except:
                            try:
                                self.transformed_process.kill()
                            except:
                                pass
                        self.transformed_process = None
                
                if self.transformed_thread and self.transformed_thread.is_alive():
                    self.transformed_thread.join(timeout=0.2)
            
            # Clear stop event before starting new playback
            self.original_stop_event.clear()
            logger.debug("toggle_original_playback: Stop event cleared")
            
            # Start playback - update state immediately
            self.original_playing = True
            self.original_play_btn.set_playing(True)
            self.original_start_time = time.time()
            logger.info("toggle_original_playback: State updated - playing=True, button set to pause icon")
            
            if HAS_SOUNDDEVICE:
                logger.info("toggle_original_playback: Starting playback thread with sounddevice")
                self.original_thread = threading.Thread(
                    target=self._play_audio_sounddevice,
                    args=(self.original_audio_path, self.original_stop_event, 'original_position', self.original_duration, self.original_position_lock, self.original_stream_lock, 'original_stream'),
                    daemon=True
                )
            elif HAS_PYDUB:
                logger.info("toggle_original_playback: Starting playback thread with pydub")
                self.original_thread = threading.Thread(
                    target=self._play_audio_pydub,
                    args=(self.original_audio_path, self.original_stop_event, 'original_position', self.original_duration, self.original_position_lock, self.original_stream_lock, 'original_stream'),
                    daemon=True
                )
            else:
                logger.error("toggle_original_playback: No audio library available!")
                self.original_playing = False
                self.original_play_btn.set_playing(False)
                return
            
            self.original_thread.start()
            logger.info("toggle_original_playback: Playback thread started")
    
    def toggle_transformed_playback(self):
        """Toggle transformed audio playback."""
        if not self.transformed_audio_path or not self.transformed_audio_path.exists():
            logger.warning("toggle_transformed_playback: No audio file loaded")
            return
        
        # Check current playing state - check flag first, then verify thread
        is_currently_playing = self.transformed_playing
        logger.info(f"toggle_transformed_playback: Button clicked. Current state: playing={is_currently_playing}, thread_alive={self.transformed_thread.is_alive() if self.transformed_thread else False}")
        
        if is_currently_playing:
            # PAUSE: Stop the audio immediately
            logger.info("toggle_transformed_playback: PAUSE button pressed - stopping audio")
            self.transformed_stop_event.set()
            logger.debug("toggle_transformed_playback: Stop event set")
            
            # Stop stream immediately if it exists
            stream_stopped = False
            with self.transformed_stream_lock:
                if self.transformed_stream is not None:
                    logger.debug("toggle_transformed_playback: Stopping and closing stream")
                    try:
                        self.transformed_stream.stop()
                        self.transformed_stream.close()
                        logger.debug("toggle_transformed_playback: Stream stopped and closed successfully")
                        stream_stopped = True
                    except Exception as e:
                        logger.error(f"toggle_transformed_playback: Error stopping stream: {e}")
                    self.transformed_stream = None
                else:
                    logger.debug("toggle_transformed_playback: No stream object found")
            
            # If no stream object, try to kill subprocess (for pydub fallback)
            if not stream_stopped:
                with self.transformed_process_lock:
                    if self.transformed_process is not None:
                        logger.debug("toggle_transformed_playback: Terminating subprocess")
                        try:
                            self.transformed_process.terminate()
                            self.transformed_process.wait(timeout=1.0)
                            logger.debug("toggle_transformed_playback: Subprocess terminated successfully")
                        except subprocess.TimeoutExpired:
                            logger.warning("toggle_transformed_playback: Subprocess didn't terminate, killing it")
                            try:
                                self.transformed_process.kill()
                                self.transformed_process.wait(timeout=0.5)
                            except:
                                pass
                        except Exception as e:
                            logger.error(f"toggle_transformed_playback: Error terminating subprocess: {e}")
                        self.transformed_process = None
                    elif HAS_SOUNDDEVICE:
                        # Try global stop as last resort
                        logger.debug("toggle_transformed_playback: Calling global sd.stop() as fallback")
                        try:
                            sd.stop()
                            logger.debug("toggle_transformed_playback: Global sd.stop() called")
                        except Exception as e:
                            logger.error(f"toggle_transformed_playback: Error calling global sd.stop(): {e}")
            
            # Update state immediately for UI responsiveness
            self.transformed_playing = False
            self.transformed_play_btn.set_playing(False)
            logger.info("toggle_transformed_playback: State updated - playing=False, button set to play icon")
            
            # Wait briefly for thread to finish (non-blocking with timeout)
            if self.transformed_thread and self.transformed_thread.is_alive():
                logger.debug("toggle_transformed_playback: Waiting for thread to finish (timeout=0.2s)")
                self.transformed_thread.join(timeout=0.2)
                if self.transformed_thread.is_alive():
                    logger.warning("toggle_transformed_playback: Thread still alive after timeout")
                else:
                    logger.debug("toggle_transformed_playback: Thread finished")
        else:
            # PLAY: Start or resume playback
            # First, ensure any previous thread is completely stopped
            if self.transformed_thread and self.transformed_thread.is_alive():
                logger.warning("toggle_transformed_playback: Previous thread still alive, forcing stop")
                # Force stop previous thread
                self.transformed_stop_event.set()
                
                # Stop stream if exists
                with self.transformed_stream_lock:
                    if self.transformed_stream is not None:
                        try:
                            self.transformed_stream.stop()
                            self.transformed_stream.close()
                        except:
                            pass
                        self.transformed_stream = None
                
                # Kill subprocess if exists
                with self.transformed_process_lock:
                    if self.transformed_process is not None:
                        try:
                            self.transformed_process.terminate()
                            self.transformed_process.wait(timeout=0.5)
                        except:
                            try:
                                self.transformed_process.kill()
                            except:
                                pass
                        self.transformed_process = None
                
                self.transformed_thread.join(timeout=0.2)
            
            # Stop original if playing
            if self.original_playing:
                self.original_stop_event.set()
                self.original_playing = False
                self.original_play_btn.set_playing(False)
                with self.original_stream_lock:
                    if self.original_stream is not None:
                        try:
                            self.original_stream.stop()
                            self.original_stream.close()
                        except:
                            pass
                        self.original_stream = None
                if self.original_thread and self.original_thread.is_alive():
                    self.original_thread.join(timeout=0.2)
            
            # Clear stop event before starting new playback
            self.transformed_stop_event.clear()
            logger.debug("toggle_transformed_playback: Stop event cleared")
            
            # Start playback - update state immediately
            self.transformed_playing = True
            self.transformed_play_btn.set_playing(True)
            self.transformed_start_time = time.time()
            with self.transformed_position_lock:
                current_pos = self.transformed_position
            logger.info(f"toggle_transformed_playback: State updated - playing=True, button set to pause icon, resuming from: {current_pos}ms")
            
            if HAS_SOUNDDEVICE:
                logger.info("toggle_transformed_playback: Starting playback thread with sounddevice")
                self.transformed_thread = threading.Thread(
                    target=self._play_audio_sounddevice,
                    args=(self.transformed_audio_path, self.transformed_stop_event, 'transformed_position', self.transformed_duration, self.transformed_position_lock, self.transformed_stream_lock, 'transformed_stream'),
                    daemon=True
                )
            elif HAS_PYDUB:
                logger.info("toggle_transformed_playback: Starting playback thread with pydub")
                self.transformed_thread = threading.Thread(
                    target=self._play_audio_pydub,
                    args=(self.transformed_audio_path, self.transformed_stop_event, 'transformed_position', self.transformed_duration, self.transformed_position_lock, self.transformed_stream_lock, 'transformed_stream'),
                    daemon=True
                )
            else:
                logger.error("toggle_transformed_playback: No audio library available!")
                self.transformed_playing = False
                self.transformed_play_btn.set_playing(False)
                return
            
            self.transformed_thread.start()
            logger.info("toggle_transformed_playback: Playback thread started")
    
    def update_positions(self):
        """Update position displays (called by timer)."""
        # Update original
        with self.original_position_lock:
            current_original_pos = self.original_position
        
        if self.original_duration > 0:
            current_time = self.format_time(int(current_original_pos))
            total_time = self.format_time(int(self.original_duration * 1000))
            self.original_time_label.setText(f"{current_time} / {total_time}")
        
        # Update transformed
        with self.transformed_position_lock:
            current_transformed_pos = self.transformed_position
        
        if self.transformed_duration > 0:
            current_time = self.format_time(int(current_transformed_pos))
            total_time = self.format_time(int(self.transformed_duration * 1000))
            self.transformed_time_label.setText(f"{current_time} / {total_time}")
        
        # Check if playback finished
        if self.original_playing and not (self.original_thread and self.original_thread.is_alive()):
            self.original_playing = False
            self.original_play_btn.set_playing(False)
            # Reset position if finished
            if current_original_pos >= self.original_duration * 1000:
                with self.original_position_lock:
                    self.original_position = 0
        
        if self.transformed_playing and not (self.transformed_thread and self.transformed_thread.is_alive()):
            self.transformed_playing = False
            self.transformed_play_btn.set_playing(False)
            # Reset position if finished
            if current_transformed_pos >= self.transformed_duration * 1000:
                with self.transformed_position_lock:
                    self.transformed_position = 0
    
    def set_original_position(self, position):
        """Set original audio position."""
        with self.original_position_lock:
            self.original_position = position
        if self.original_playing:
            # Stop and restart playback from new position
            was_playing = True
            self.toggle_original_playback()
            self.toggle_original_playback()
    
    def set_transformed_position(self, position):
        """Set transformed audio position."""
        with self.transformed_position_lock:
            self.transformed_position = position
        if self.transformed_playing:
            # Stop and restart playback from new position
            was_playing = True
            self.toggle_transformed_playback()
            self.toggle_transformed_playback()
    
    def format_time(self, milliseconds):
        """Format milliseconds to MM:SS."""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def browse_audio_file(self):
        """Browse for audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            str(self.project_root / "data" / "test_audio"),
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.aac *.ogg);;All Files (*.*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self.load_original_audio(file_path)
    
    def apply_transforms(self):
        """Apply the selected transforms."""
        input_file = self.file_path_edit.text()
        if not input_file:
            return
        
        input_path = Path(input_file)
        if not input_path.exists():
            return
        
        output_file = Path(self.output_path.text())
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.progress_bar.setValue(0)
            
            # Import transform functions
            from transforms.speed import speed_change, time_stretch
            from transforms.pitch import pitch_shift
            from transforms.noise import add_noise, reduce_noise
            from transforms.reverb import apply_reverb
            from transforms.eq import boost_highs, boost_lows
            from transforms.chain import combine_chain
            
            current_file = input_path
            transforms_applied = []
            
            # Apply speed transform
            speed_value = self.speed_slider.value() / 100.0  # Convert from 50-1000 to 0.5-10.0
            if speed_value != 1.0:
                self.progress_bar.setValue(10)
                temp_file = output_file.parent / f"temp_speed_{output_file.stem}.wav"
                # Use speed_change with preserve_pitch=True for better quality
                # This uses time_stretch internally which preserves pitch
                speed_change(
                    input_path=current_file,
                    speed=speed_value,
                    out_path=temp_file,
                    sample_rate=44100,
                    preserve_pitch=True  # Preserve pitch for better quality
                )
                current_file = temp_file
                transforms_applied.append(('speed_change', {'speed': speed_value, 'preserve_pitch': True}))
            
            # Apply pitch transform
            pitch_semitones = self.pitch_slider.value()
            if pitch_semitones != 0:
                self.progress_bar.setValue(30)
                temp_file2 = output_file.parent / f"temp_pitch_{output_file.stem}.wav"
                pitch_shift(
                    input_path=current_file,
                    semitones=pitch_semitones,
                    out_path=temp_file2,
                    sample_rate=44100
                )
                # Clean up previous temp file if it exists
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
                current_file = temp_file2
                transforms_applied.append(('pitch_shift', {'semitones': pitch_semitones}))
            
            # Apply reverb (if > 0)
            reverb_delay_ms = self.reverb_slider.value()
            if reverb_delay_ms > 0:
                self.progress_bar.setValue(40)
                temp_file_reverb = output_file.parent / f"temp_reverb_{output_file.stem}.wav"
                apply_reverb(
                    input_path=current_file,
                    delay_ms=float(reverb_delay_ms),
                    out_path=temp_file_reverb,
                    sample_rate=44100,
                    wet_mix=0.3,  # 30% wet signal
                    decay=0.5  # Decay factor
                )
                # Clean up previous temp file if it exists
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
                current_file = temp_file_reverb
                transforms_applied.append(('reverb', {'delay_ms': reverb_delay_ms}))
            
            # Apply noise reduction (if > 0)
            noise_value = self.noise_slider.value()
            if noise_value > 0:
                self.progress_bar.setValue(60)
                # Convert percentage to reduction strength (0.0 to 1.0)
                # 0% = no reduction, 100% = maximum reduction
                reduction_strength = noise_value / 100.0
                temp_file3 = output_file.parent / f"temp_noise_reduced_{output_file.stem}.wav"
                reduce_noise(
                    input_path=current_file,
                    reduction_strength=reduction_strength,
                    out_path=temp_file3,
                    sample_rate=44100
                )
                # Clean up previous temp file if it exists
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
                current_file = temp_file3
                transforms_applied.append(('noise_reduction', {'strength': reduction_strength}))
            
            # Apply EQ (if not 0)
            eq_value = self.eq_slider.value()
            if eq_value != 0:
                self.progress_bar.setValue(80)
                temp_file4 = output_file.parent / f"temp_eq_{output_file.stem}.wav"
                if eq_value > 0:
                    # Boost highs
                    boost_highs(
                        input_path=current_file,
                        gain_db=float(eq_value),
                        freq_hz=3000.0,
                        out_path=temp_file4,
                        sample_rate=44100
                    )
                else:
                    # Boost lows
                    boost_lows(
                        input_path=current_file,
                        gain_db=float(abs(eq_value)),
                        freq_hz=200.0,
                        out_path=temp_file4,
                        sample_rate=44100
                    )
                # Clean up previous temp file if it exists
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
                current_file = temp_file4
                transforms_applied.append(('eq', {'gain_db': eq_value}))
            
            # Apply audio compression (if codec selected)
            codec = self.codec_combo.currentText()
            if codec != "None":
                self.progress_bar.setValue(85)
                from transforms.encode import re_encode
                bitrate = self.bitrate_combo.currentText()
                temp_file5 = output_file.parent / f"temp_encode_{output_file.stem}.{codec.lower()}"
                re_encode(
                    input_path=current_file,
                    codec=codec.lower(),
                    bitrate=bitrate,
                    out_path=temp_file5
                )
                # Clean up previous temp file if it exists
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
                current_file = temp_file5
                transforms_applied.append(('re_encode', {'codec': codec.lower(), 'bitrate': bitrate}))
            
            # Apply overlay/mixing (if overlay file selected)
            overlay_path = self.overlay_path.text()
            if overlay_path and Path(overlay_path).exists():
                self.progress_bar.setValue(87)
                from transforms.overlay import overlay_vocals
                overlay_gain = self.overlay_gain_slider.value()
                temp_file6 = output_file.parent / f"temp_overlay_{output_file.stem}.wav"
                overlay_vocals(
                    input_path=current_file,
                    vocal_file=Path(overlay_path),
                    level_db=float(overlay_gain),
                    out_path=temp_file6,
                    sample_rate=44100
                )
                # Clean up previous temp file if it exists
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
                current_file = temp_file6
                transforms_applied.append(('overlay_vocals', {'level_db': overlay_gain, 'vocal_file': overlay_path}))
            
            # Copy final result to output file
            self.progress_bar.setValue(90)
            if current_file != output_file:
                import shutil
                shutil.copy2(current_file, output_file)
                # Clean up temp file
                if current_file != input_path and current_file.exists():
                    current_file.unlink()
            
            self.progress_bar.setValue(100)
            
            # Load transformed audio for playback
            self.load_transformed_audio(str(output_file))
            
        except Exception as e:
            self.progress_bar.setValue(0)
            import traceback
            print(f"Error applying transforms: {e}")
            print(traceback.format_exc())
            # Show error message to user
            self.test_results.setPlainText(f"Error applying transforms: {str(e)}")
            self.test_results.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #f87171;
                    border-radius: 4px;
                    padding: 10px;
                    color: #f87171;
                    font-size: 12px;
                }
            """)
    
    def _update_test_button_state(self):
        """Update the test button enabled state based on available audio files."""
        if hasattr(self, 'test_btn') and self.test_btn is not None:
            has_original = bool(self.original_audio_path is not None and self.original_audio_path.exists())
            has_transformed = bool(self.transformed_audio_path is not None and self.transformed_audio_path.exists())
            self.test_btn.setEnabled(has_original and has_transformed)
    
    def browse_overlay_file(self):
        """Browse for overlay file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Overlay Audio File",
            str(self.project_root / "data" / "test_audio"),
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.aac *.ogg);;All Files (*.*)"
        )
        if file_path:
            self.overlay_path.setText(file_path)
    
    def add_to_chain(self):
        """Add current transform settings to chain."""
        transform_desc = []
        
        speed_value = self.speed_slider.value() / 100.0
        if speed_value != 1.0:
            transform_desc.append(f"Speed: {speed_value:.2f}x")
        
        pitch_value = self.pitch_slider.value()
        if pitch_value != 0:
            transform_desc.append(f"Pitch: {pitch_value:+d} semitones")
        
        reverb_value = self.reverb_slider.value()
        if reverb_value > 0:
            transform_desc.append(f"Reverb: {reverb_value}ms")
        
        noise_value = self.noise_slider.value()
        if noise_value > 0:
            transform_desc.append(f"Noise Reduction: {noise_value}%")
        
        eq_value = self.eq_slider.value()
        if eq_value != 0:
            transform_desc.append(f"EQ: {eq_value:+d} dB")
        
        codec = self.codec_combo.currentText()
        if codec != "None":
            bitrate = self.bitrate_combo.currentText()
            transform_desc.append(f"Compression: {codec} @ {bitrate}")
        
        overlay_path = self.overlay_path.text()
        if overlay_path and Path(overlay_path).exists():
            gain = self.overlay_gain_slider.value()
            transform_desc.append(f"Overlay: {Path(overlay_path).name} @ {gain}dB")
        
        if transform_desc:
            transform_dict = {
                'speed': speed_value if speed_value != 1.0 else None,
                'pitch': pitch_value if pitch_value != 0 else None,
                'reverb': reverb_value if reverb_value > 0 else None,
                'noise_reduction': noise_value / 100.0 if noise_value > 0 else None,
                'eq': eq_value if eq_value != 0 else None,
                'codec': codec if codec != "None" else None,
                'bitrate': self.bitrate_combo.currentText() if codec != "None" else None,
                'overlay_path': overlay_path if overlay_path and Path(overlay_path).exists() else None,
                'overlay_gain': self.overlay_gain_slider.value() if overlay_path and Path(overlay_path).exists() else None,
            }
            self.transform_chain.append(transform_dict)
            self.update_chain_display()
        else:
            self.test_results.setPlainText("No transforms selected. Adjust settings and try again.")
            self.test_results.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #fbbf24;
                    border-radius: 4px;
                    padding: 10px;
                    color: #fbbf24;
                    font-size: 12px;
                }
            """)
    
    def clear_chain(self):
        """Clear the transform chain."""
        self.transform_chain = []
        self.update_chain_display()
    
    def update_chain_display(self):
        """Update the chain list display."""
        if not self.transform_chain:
            self.chain_list.setPlainText("No transforms in chain. Adjust settings above and click 'Add to Chain'.")
        else:
            chain_text = "Transform Chain:\n"
            for i, transform in enumerate(self.transform_chain, 1):
                parts = []
                if transform.get('speed'):
                    parts.append(f"Speed {transform['speed']:.2f}x")
                if transform.get('pitch'):
                    parts.append(f"Pitch {transform['pitch']:+d}st")
                if transform.get('reverb'):
                    parts.append(f"Reverb {transform['reverb']}ms")
                if transform.get('noise_reduction'):
                    parts.append(f"Noise {transform['noise_reduction']*100:.0f}%")
                if transform.get('eq'):
                    parts.append(f"EQ {transform['eq']:+d}dB")
                if transform.get('codec'):
                    parts.append(f"{transform['codec']} {transform['bitrate']}")
                if transform.get('overlay_path'):
                    parts.append(f"Overlay {Path(transform['overlay_path']).name} @ {transform['overlay_gain']}dB")
                chain_text += f"{i}. {' → '.join(parts)}\n"
            self.chain_list.setPlainText(chain_text.strip())
    
    def test_fingerprint_match(self):
        """Test if fingerprint can match transformed audio to original."""
        # Use currently selected original and transformed audio
        original_path = self.original_audio_path
        transformed_path = self.transformed_audio_path
        
        if not original_path or not original_path.exists():
            self.test_results.setPlainText("Error: No original audio file selected. Please select an audio file first.")
            self.test_results.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #f87171;
                    border-radius: 4px;
                    padding: 10px;
                    color: #f87171;
                    font-size: 12px;
                }
            """)
            return
        
        if not transformed_path or not transformed_path.exists():
            self.test_results.setPlainText("Error: No transformed audio available. Please apply transforms first.")
            self.test_results.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #f87171;
                    border-radius: 4px;
                    padding: 10px;
                    color: #f87171;
                    font-size: 12px;
                }
            """)
            return
        
        self.test_results.setPlainText("Testing fingerprint match... This may take a moment.")
        self.test_results.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #60a5fa;
                border-radius: 4px;
                padding: 10px;
                color: #60a5fa;
                font-size: 12px;
            }
        """)
        
        # Run test in background thread
        test_thread = threading.Thread(
            target=self._test_fingerprint_worker,
            args=(Path(original_path), Path(transformed_path)),
            daemon=True
        )
        test_thread.start()
    
    def _test_fingerprint_worker(self, original_path: Path, transformed_path: Path):
        """Worker thread for fingerprint testing."""
        try:
            from fingerprint.load_model import load_fingerprint_model
            from fingerprint.embed import segment_audio, extract_embeddings, normalize_embeddings
            from fingerprint.query_index import build_index, load_index, query_index
            import json
            import numpy as np
            import tempfile
            
            # Load fingerprint model
            fingerprint_config = self.project_root / "config" / "fingerprint_v1.yaml"
            if not fingerprint_config.exists():
                self._update_test_results("Error: Fingerprint config not found. Please ensure config/fingerprint_v1.yaml exists.", "error")
                return
            
            model_config_dict = load_fingerprint_model(fingerprint_config)
            # Extract config values
            if isinstance(model_config_dict, dict):
                segment_length = model_config_dict.get("segment_length", 0.5)
                sample_rate = model_config_dict.get("sample_rate", 44100)
                model = model_config_dict  # Pass full dict to extract_embeddings
            else:
                # Fallback if model_config_dict is not a dict
                segment_length = 0.5
                sample_rate = 44100
                model = model_config_dict
            
            # Extract embeddings from both files
            segments_orig = segment_audio(
                original_path,
                segment_length=segment_length,
                sample_rate=sample_rate
            )
            embeddings_orig = extract_embeddings(segments_orig, model, save_embeddings=False)
            embeddings_orig = normalize_embeddings(embeddings_orig, method="l2")
            
            segments_manip = segment_audio(
                transformed_path,
                segment_length=segment_length,
                sample_rate=sample_rate
            )
            embeddings_manip = extract_embeddings(segments_manip, model, save_embeddings=False)
            embeddings_manip = normalize_embeddings(embeddings_manip, method="l2")
            
            # Create a temporary index with original embeddings
            index_config_path = self.project_root / "config" / "index_config.json"
            if not index_config_path.exists():
                index_config = {"index_type": "flat", "metric": "cosine", "normalize": True}
            else:
                with open(index_config_path, 'r') as f:
                    index_config = json.load(f)
            
            # Use original file stem as ID
            orig_id = original_path.stem
            orig_ids = [f"{orig_id}_seg_{i}" for i in range(len(embeddings_orig))]
            
            # Build temporary index
            with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp_index:
                tmp_index_path = Path(tmp_index.name)
            
            build_index(embeddings_orig, orig_ids, tmp_index_path, index_config, save_metadata=False)
            
            # Load index and query
            index, _ = load_index(tmp_index_path)
            
            # Query with manipulated embeddings (use mean of all segments)
            query_emb = np.mean(embeddings_manip, axis=0) if len(embeddings_manip) > 1 else embeddings_manip[0]
            results = query_index(index, query_emb, topk=10, ids=orig_ids, normalize=True)
            
            # Clean up temp index
            try:
                tmp_index_path.unlink()
            except:
                pass
            
            # Check if original is in results
            matched = False
            rank = None
            similarity = 0.0
            top_match = None
            
            if results and len(results) > 0:
                top_match = results[0].get("id", "")
                similarity = results[0].get("similarity", 0.0)
                
                # Check if any result matches original
                for i, result in enumerate(results):
                    result_id = result.get("id", "")
                    if orig_id in result_id:
                        matched = True
                        rank = i + 1
                        similarity = result.get("similarity", similarity)
                        break
            
            # Also compute direct cosine similarity
            orig_mean = np.mean(embeddings_orig, axis=0) if len(embeddings_orig) > 1 else embeddings_orig[0]
            direct_similarity = float(np.dot(query_emb, orig_mean))  # Cosine similarity for normalized vectors
            
            final_similarity = max(similarity, direct_similarity)
            final_matched = matched or direct_similarity > 0.7
            
            # Format results
            if final_matched:
                result_text = f"✓ MATCHED\n\n"
                result_text += f"Similarity Score: {final_similarity:.3f} ({final_similarity*100:.1f}%)\n"
                if rank:
                    result_text += f"Rank: {rank} (position in search results)\n"
                else:
                    result_text += f"Rank: 1 (direct similarity match)\n"
                result_text += f"Top Match: {top_match or orig_id}\n\n"
                if final_similarity > 0.9:
                    result_text += "Interpretation: Strong match - fingerprint is very robust to this transformation."
                elif final_similarity > 0.7:
                    result_text += "Interpretation: Good match - fingerprint is robust to this transformation."
                else:
                    result_text += "Interpretation: Moderate match - transformation affects fingerprint but still identifiable."
                self._update_test_results(result_text, "success")
            else:
                result_text = f""
                result_text += f"Similarity Score: {final_similarity:.3f} ({final_similarity*100:.1f}%)\n"
                result_text += f"Top Match: {top_match or 'N/A'}\n\n"
                result_text += "Interpretation: Fingerprint could not match transformed audio to original. "
                result_text += "This transformation may break fingerprint identification."
                self._update_test_results(result_text, "error")
                
        except Exception as e:
            error_msg = f"Error testing fingerprint: {str(e)}\n\n"
            error_msg += "Please ensure:\n"
            error_msg += "1. Fingerprint model is properly configured\n"
            error_msg += "2. Audio files are valid and accessible\n"
            error_msg += "3. Required dependencies are installed"
            self._update_test_results(error_msg, "error")
            logger.error(f"Fingerprint test failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_test_results(self, text: str, result_type: str):
        """Update test results display (thread-safe)."""
        from PyQt6.QtCore import QTimer
        def update():
            self.test_results.setPlainText(text)
            if result_type == "success":
                self.test_results.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e1e;
                        border: 1px solid #10b981;
                        border-radius: 4px;
                        padding: 10px;
                        color: #10b981;
                        font-size: 12px;
                    }
                """)
            elif result_type == "error":
                self.test_results.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e1e;
                        border: 1px solid #f87171;
                        border-radius: 4px;
                        padding: 10px;
                        color: #f87171;
                        font-size: 12px;
                    }
                """)
            else:
                self.test_results.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e1e;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 10px;
                        color: #c8c8c8;
                        font-size: 12px;
                    }
                """)
        QTimer.singleShot(0, update)  # Execute in main thread

