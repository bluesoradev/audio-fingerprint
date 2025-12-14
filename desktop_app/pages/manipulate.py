"""
Audio manipulation page for applying transforms.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygon
from pathlib import Path
import threading
import time
from threading import Lock

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
            except Exception as e:
                self.original_file_label.setText(f"Error loading: {str(e)[:30]}")
                self.original_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
        else:
            self.original_file_label.setText("File not found")
            self.original_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
    
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
            except Exception as e:
                self.transformed_file_label.setText(f"Error loading: {str(e)[:30]}")
                self.transformed_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
                self.transformed_play_btn.setEnabled(False)
        else:
            self.transformed_file_label.setText("File not found")
            self.transformed_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
            self.transformed_play_btn.setEnabled(False)
    
    def _play_audio_sounddevice(self, file_path: Path, stop_event: threading.Event, position_attr: str, duration: float, lock: Lock):
        """Play audio using sounddevice."""
        try:
            # Read audio file
            data, file_sample_rate = sf.read(str(file_path))
            
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
                
                # Stop any existing playback first (important to prevent multiple streams)
                try:
                    sd.stop()
                except:
                    pass
                
                # Check if we should still play (might have been stopped while stopping previous)
                if stop_event.is_set():
                    return
                
                # Play entire remaining audio at once (non-blocking)
                sd.play(data_to_play, playback_sample_rate)
                
                # Track position while playing
                while not stop_event.is_set():
                    # Check stop event first before any operations
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
                        break
                    
                    # Sleep in smaller chunks to check stop_event more frequently
                    for _ in range(5):  # 5 x 10ms = 50ms total
                        if stop_event.is_set():
                            break
                        time.sleep(0.01)
                
                # Stop playback immediately if requested
                if stop_event.is_set():
                    try:
                        sd.stop()
                    except:
                        pass
                else:
                    # Replace blocking sd.wait() with polling loop
                    # This allows us to check stop_event even while "waiting"
                    while True:
                        if stop_event.is_set():
                            # Stop was requested during wait
                            try:
                                sd.stop()
                            except:
                                pass
                            break
                        
                        # Check if playback is still active with short timeout
                        try:
                            # Use short timeout to check stop_event frequently (every 50ms)
                            sd.wait(timeout=0.05)
                            # If wait returns, playback finished naturally
                            break
                        except:
                            # Playback might have finished or error occurred
                            break
                
                # Final position update
                with lock:
                    if not stop_event.is_set():
                        setattr(self, position_attr, duration * 1000)
        except Exception as e:
            print(f"Error playing audio: {e}")
            import traceback
            traceback.print_exc()
            try:
                sd.stop()
            except:
                pass
        finally:
            # Ensure playing state is cleared when thread finishes
            if position_attr == 'original_position':
                self.original_playing = False
                self.original_play_btn.set_playing(False)
            elif position_attr == 'transformed_position':
                self.transformed_playing = False
                self.transformed_play_btn.set_playing(False)
    
    def _play_audio_pydub(self, file_path: Path, stop_event: threading.Event, position_attr: str, duration: float, lock: Lock):
        """Play audio using pydub."""
        import subprocess
        import os
        
        try:
            audio = AudioSegment.from_file(str(file_path))
            
            # Ensure correct sample rate (44100 Hz)
            if audio.frame_rate != 44100:
                audio = audio.set_frame_rate(44100)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            with lock:
                start_pos_ms = getattr(self, position_attr)
            
            if start_pos_ms < len(audio):
                audio_to_play = audio[start_pos_ms:]
                
                if len(audio_to_play) == 0:
                    return
                
                # Export to temporary WAV file for playback
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                try:
                    audio_to_play.export(temp_path, format="wav")
                    
                    # Use sounddevice if available (better control)
                    if HAS_SOUNDDEVICE:
                        data, sr = sf.read(temp_path)
                        if len(data.shape) > 1:
                            data = data.mean(axis=1)
                        
                        playback_start_time = time.time()
                        actual_start_pos = start_pos_ms / 1000.0
                        audio_length_seconds = len(data) / sr
                        
                        try:
                            sd.stop()
                        except:
                            pass
                        
                        sd.play(data, sr)
                        
                        while not stop_event.is_set():
                            # Check stop event first
                            if stop_event.is_set():
                                break
                            
                            elapsed = time.time() - playback_start_time
                            current_pos_ms = start_pos_ms + (elapsed * 1000)
                            
                            with lock:
                                setattr(self, position_attr, min(current_pos_ms, len(audio)))
                            
                            if elapsed >= audio_length_seconds:
                                break
                            
                            # Sleep in smaller chunks to check stop_event more frequently
                            for _ in range(5):  # 5 x 10ms = 50ms total
                                if stop_event.is_set():
                                    break
                                time.sleep(0.01)
                        
                        # Stop immediately if requested
                        if stop_event.is_set():
                            try:
                                sd.stop()
                            except:
                                pass
                        else:
                            # Replace blocking sd.wait() with polling loop
                            # This allows us to check stop_event even while "waiting"
                            while True:
                                if stop_event.is_set():
                                    # Stop was requested during wait
                                    try:
                                        sd.stop()
                                    except:
                                        pass
                                    break
                                
                                # Check if playback is still active with short timeout
                                try:
                                    # Use short timeout to check stop_event frequently (every 50ms)
                                    sd.wait(timeout=0.05)
                                    # If wait returns, playback finished naturally
                                    break
                                except:
                                    # Playback might have finished or error occurred
                                    break
                    else:
                        # Fallback: use pydub play (can't be stopped easily)
                        start_time = time.time()
                        play(audio_to_play)
                        
                        # Update position
                        elapsed_ms = (time.time() - start_time) * 1000
                        with lock:
                            if not stop_event.is_set():
                                setattr(self, position_attr, min(start_pos_ms + elapsed_ms, len(audio)))
                    
                    # Final position update
                    with lock:
                        if not stop_event.is_set():
                            setattr(self, position_attr, len(audio))
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
        except Exception as e:
            print(f"Error playing audio: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Ensure playing state is cleared when thread finishes
            if position_attr == 'original_position':
                self.original_playing = False
                self.original_play_btn.set_playing(False)
            elif position_attr == 'transformed_position':
                self.transformed_playing = False
                self.transformed_play_btn.set_playing(False)
    
    def toggle_original_playback(self):
        """Toggle original audio playback."""
        if not self.original_audio_path or not self.original_audio_path.exists():
            return
        
        # Check current playing state - check flag first, then verify thread
        is_currently_playing = self.original_playing
        
        if is_currently_playing:
            # PAUSE: Set stop flag and keep it set (don't clear it here!)
            self.original_stop_event.set()
            
            # Update state immediately for UI responsiveness
            self.original_playing = False
            self.original_play_btn.set_playing(False)
            
            # Stop sounddevice immediately and aggressively (non-blocking)
            if HAS_SOUNDDEVICE:
                try:
                    sd.stop()
                    sd.stop()  # Call again to ensure it stops
                except:
                    pass
            
            # Keep stop event set - it will be cleared when starting new playback
            # This ensures the playback thread sees the stop signal
        else:
            # Don't start if thread is still running (prevent multiple threads)
            if self.original_thread and self.original_thread.is_alive():
                return
            
            # Stop transformed if playing (but don't wait)
            if self.transformed_playing:
                self.transformed_stop_event.set()
                self.transformed_playing = False
                self.transformed_play_btn.set_playing(False)
                if HAS_SOUNDDEVICE:
                    try:
                        sd.stop()
                    except:
                        pass
            
            # Ensure sounddevice is stopped before starting (non-blocking)
            if HAS_SOUNDDEVICE:
                try:
                    sd.stop()
                except:
                    pass
            
            # PLAY: Clear stop event BEFORE starting (this is the only place we clear it)
            self.original_stop_event.clear()
            
            # Start playback - update state immediately
            self.original_playing = True
            self.original_play_btn.set_playing(True)
            self.original_start_time = time.time()
            
            if HAS_SOUNDDEVICE:
                self.original_thread = threading.Thread(
                    target=self._play_audio_sounddevice,
                    args=(self.original_audio_path, self.original_stop_event, 'original_position', self.original_duration, self.original_position_lock),
                    daemon=True
                )
            elif HAS_PYDUB:
                self.original_thread = threading.Thread(
                    target=self._play_audio_pydub,
                    args=(self.original_audio_path, self.original_stop_event, 'original_position', self.original_duration, self.original_position_lock),
                    daemon=True
                )
            else:
                self.original_playing = False
                self.original_play_btn.set_playing(False)
                return
            
            self.original_thread.start()
    
    def toggle_transformed_playback(self):
        """Toggle transformed audio playback."""
        if not self.transformed_audio_path or not self.transformed_audio_path.exists():
            return
        
        # Check current playing state - check flag first, then verify thread
        is_currently_playing = self.transformed_playing
        
        if is_currently_playing:
            # PAUSE: Set stop flag and keep it set (don't clear it here!)
            self.transformed_stop_event.set()
            
            # Update state immediately for UI responsiveness
            self.transformed_playing = False
            self.transformed_play_btn.set_playing(False)
            
            # Stop sounddevice immediately and aggressively (non-blocking)
            if HAS_SOUNDDEVICE:
                try:
                    sd.stop()
                    sd.stop()  # Call again to ensure it stops
                except:
                    pass
            
            # Keep stop event set - it will be cleared when starting new playback
            # This ensures the playback thread sees the stop signal
        else:
            # Don't start if thread is still running (prevent multiple threads)
            if self.transformed_thread and self.transformed_thread.is_alive():
                return
            
            # Stop original if playing (but don't wait)
            if self.original_playing:
                self.original_stop_event.set()
                self.original_playing = False
                self.original_play_btn.set_playing(False)
                if HAS_SOUNDDEVICE:
                    try:
                        sd.stop()
                    except:
                        pass
            
            # Ensure sounddevice is stopped before starting (non-blocking)
            if HAS_SOUNDDEVICE:
                try:
                    sd.stop()
                except:
                    pass
            
            # PLAY: Clear stop event BEFORE starting (this is the only place we clear it)
            self.transformed_stop_event.clear()
            
            # Start playback - update state immediately
            self.transformed_playing = True
            self.transformed_play_btn.set_playing(True)
            self.transformed_start_time = time.time()
            
            if HAS_SOUNDDEVICE:
                self.transformed_thread = threading.Thread(
                    target=self._play_audio_sounddevice,
                    args=(self.transformed_audio_path, self.transformed_stop_event, 'transformed_position', self.transformed_duration, self.transformed_position_lock),
                    daemon=True
                )
            elif HAS_PYDUB:
                self.transformed_thread = threading.Thread(
                    target=self._play_audio_pydub,
                    args=(self.transformed_audio_path, self.transformed_stop_event, 'transformed_position', self.transformed_duration, self.transformed_position_lock),
                    daemon=True
                )
            else:
                self.transformed_playing = False
                self.transformed_play_btn.set_playing(False)
                return
            
            self.transformed_thread.start()
    
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
            from transforms.noise import add_noise
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
            
            # Apply noise reduction (if > 0)
            noise_value = self.noise_slider.value()
            if noise_value > 0:
                self.progress_bar.setValue(50)
                # Convert percentage to SNR (higher percentage = less noise = higher SNR)
                # 0% = SNR 0dB (lots of noise), 100% = SNR 30dB (minimal noise)
                snr_db = (noise_value / 100.0) * 30.0
                temp_file3 = output_file.parent / f"temp_noise_{output_file.stem}.wav"
                # Note: add_noise adds noise, so we'd need a noise reduction function
                # For now, skip this or implement a simple noise gate
                # transforms_applied.append(('noise_reduction', {'snr_db': snr_db}))
            
            # Apply EQ (if not 0)
            eq_value = self.eq_slider.value()
            if eq_value != 0:
                self.progress_bar.setValue(70)
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
            # TODO: Show error message to user

