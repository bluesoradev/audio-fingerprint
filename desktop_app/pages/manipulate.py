"""
Audio manipulation page for applying transforms.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
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
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        title = QLabel("Audio Manipulation")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # File selection
        file_group = QGroupBox("Select Audio File")
        file_layout = QHBoxLayout(file_group)
        
        self.file_combo = QComboBox()
        self.file_combo.setEditable(False)
        file_layout.addWidget(QLabel("Audio Source:"))
        file_layout.addWidget(self.file_combo, 1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_audio_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # Transform controls
        transform_group = QGroupBox()
        transform_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 0 5px;
            }
        """)
        transform_group.setTitle("Audio Transform Controls")
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
                background-color: #3d3d3d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #427eea;
                width: 18px;
                height: 18px;
                border-radius: 4px;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #3464ba;
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
        self.pitch_spin = QSpinBox()
        self.pitch_spin.setRange(-12, 12)
        self.pitch_spin.setValue(0)
        self.pitch_spin.setStyleSheet("""
            QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                min-width: 120px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 25px;
                background-color: #f0f0f0;
                border-left: 1px solid #cccccc;
            }
            QSpinBox::up-button {
                border-top-right-radius: 4px;
            }
            QSpinBox::down-button {
                border-bottom-right-radius: 4px;
            }
        """)
        transform_layout.addRow(pitch_label_text, self.pitch_spin)
        
        # Noise Reduction
        noise_label_text = QLabel("Noise Reduction:")
        noise_label_text.setStyleSheet("color: #ffffff;")
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setRange(0, 100)
        self.noise_slider.setValue(50)
        self.noise_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #3d3d3d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #427eea;
                width: 18px;
                height: 18px;
                border-radius: 4px;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #3464ba;
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
        self.reverb_spin = QSpinBox()
        self.reverb_spin.setRange(0, 500)
        self.reverb_spin.setValue(0)
        self.reverb_spin.setStyleSheet("""
            QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                min-width: 120px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 25px;
                background-color: #f0f0f0;
                border-left: 1px solid #cccccc;
            }
            QSpinBox::up-button {
                border-top-right-radius: 4px;
            }
            QSpinBox::down-button {
                border-bottom-right-radius: 4px;
            }
        """)
        transform_layout.addRow(reverb_label_text, self.reverb_spin)
        
        # EQ
        eq_label_text = QLabel("EQ Adjustment (dB):")
        eq_label_text.setStyleSheet("color: #ffffff;")
        self.eq_spin = QSpinBox()
        self.eq_spin.setRange(-20, 20)
        self.eq_spin.setValue(2)
        self.eq_spin.setStyleSheet("""
            QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                min-width: 120px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 25px;
                background-color: #f0f0f0;
                border-left: 1px solid #cccccc;
            }
            QSpinBox::up-button {
                border-top-right-radius: 4px;
            }
            QSpinBox::down-button {
                border-bottom-right-radius: 4px;
            }
        """)
        transform_layout.addRow(eq_label_text, self.eq_spin)
        
        # Apply button
        apply_btn = QPushButton("Apply Transforms")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: #ffffff;
                padding: 12px;
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
            QPushButton:pressed {
                background-color: #2a5098;
            }
        """)
        apply_btn_layout = QHBoxLayout()
        apply_btn_layout.addStretch()
        apply_btn_layout.addWidget(apply_btn)
        apply_btn_layout.addStretch()
        transform_layout.addRow("", apply_btn_layout)
        apply_btn.clicked.connect(self.apply_transforms)
        
        layout.addWidget(transform_group)
        
        # Output path
        output_group = QGroupBox("Output & Status")
        output_layout = QFormLayout(output_group)
        
        self.output_path = QLineEdit("data/manipulated/transformed_audio.wav")
        output_layout.addRow("Output Path:", self.output_path)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        output_layout.addRow("Processing Progress:", self.progress_bar)
        
        layout.addWidget(output_group)
        
        # Audio Playback Section
        playback_group = QGroupBox("Audio Playback")
        playback_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        playback_layout = QVBoxLayout(playback_group)
        playback_layout.setSpacing(15)
        
        # Two-column layout for original and transformed players
        players_layout = QHBoxLayout()
        players_layout.setSpacing(20)
        
        # Original Audio Player
        original_player_group = QGroupBox("Original Audio")
        original_player_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
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
        
        self.original_file_label = QLabel("No audio loaded")
        self.original_file_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        original_player_layout.addWidget(self.original_file_label)
        
        self.original_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.original_position_slider.setRange(0, 0)
        self.original_position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #3d3d3d;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background-color: #427eea;
                width: 14px;
                height: 14px;
                border-radius: 2px;
                margin: -5px 0;
            }
        """)
        original_player_layout.addWidget(self.original_position_slider)
        
        original_controls = QHBoxLayout()
        self.original_play_btn = QPushButton("▶")
        self.original_play_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        self.original_play_btn.clicked.connect(self.toggle_original_playback)
        original_controls.addWidget(self.original_play_btn)
        
        self.original_time_label = QLabel("00:00 / 00:00")
        self.original_time_label.setStyleSheet("color: #c8c8c8; font-size: 12px;")
        original_controls.addWidget(self.original_time_label)
        original_controls.addStretch()
        
        original_player_layout.addLayout(original_controls)
        players_layout.addWidget(original_player_group, 1)
        
        # Transformed Audio Player
        transformed_player_group = QGroupBox("Transformed Audio")
        transformed_player_group.setStyleSheet(original_player_group.styleSheet())
        transformed_player_layout = QVBoxLayout(transformed_player_group)
        
        self.transformed_file_label = QLabel("Apply transforms to generate audio")
        self.transformed_file_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        transformed_player_layout.addWidget(self.transformed_file_label)
        
        self.transformed_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.transformed_position_slider.setRange(0, 0)
        self.transformed_position_slider.setStyleSheet(self.original_position_slider.styleSheet())
        transformed_player_layout.addWidget(self.transformed_position_slider)
        
        transformed_controls = QHBoxLayout()
        self.transformed_play_btn = QPushButton("▶")
        self.transformed_play_btn.setStyleSheet(self.original_play_btn.styleSheet())
        self.transformed_play_btn.clicked.connect(self.toggle_transformed_playback)
        self.transformed_play_btn.setEnabled(False)
        transformed_controls.addWidget(self.transformed_play_btn)
        
        self.transformed_time_label = QLabel("00:00 / 00:00")
        self.transformed_time_label.setStyleSheet(self.original_time_label.styleSheet())
        transformed_controls.addWidget(self.transformed_time_label)
        transformed_controls.addStretch()
        
        transformed_player_layout.addLayout(transformed_controls)
        players_layout.addWidget(transformed_player_group, 1)
        
        playback_layout.addLayout(players_layout)
        layout.addWidget(playback_group)
        
        layout.addStretch()
        
        # Initialize audio players
        self.init_audio_players()
        
        # Load audio files
        self.load_audio_files()
        
        # Connect file selection to load original audio
        self.file_combo.currentIndexChanged.connect(self.on_file_selected)
    
    def load_audio_files(self):
        """Load available audio files."""
        self.file_combo.clear()
        audio_dirs = ["data/originals", "data/test_audio", "data/manipulated"]
        
        for audio_dir in audio_dirs:
            audio_path = self.project_root / audio_dir
            if audio_path.exists():
                for file in sorted(audio_path.glob("*.wav")):
                    self.file_combo.addItem(f"{audio_dir}/{file.name}", str(file))
                for file in sorted(audio_path.glob("*.mp3")):
                    self.file_combo.addItem(f"{audio_dir}/{file.name}", str(file))
    
    def init_audio_players(self):
        """Initialize audio players."""
        # Connect slider movements
        self.original_position_slider.sliderMoved.connect(self.set_original_position)
        self.transformed_position_slider.sliderMoved.connect(self.set_transformed_position)
        
        if not HAS_SOUNDDEVICE and not HAS_PYDUB:
            # Show warning if no audio library available
            self.original_file_label.setText("Audio playback not available - install sounddevice or pydub")
            self.original_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
            self.transformed_file_label.setText("Audio playback not available")
            self.transformed_file_label.setStyleSheet("color: #f87171; font-size: 12px;")
    
    def on_file_selected(self):
        """Load original audio when file is selected."""
        if self.file_combo.currentIndex() >= 0:
            file_path = self.file_combo.currentData()
            if file_path:
                self.load_original_audio(file_path)
    
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
                self.original_position_slider.setRange(0, int(self.original_duration * 1000))
                self.original_position_slider.setValue(0)
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
                self.transformed_position_slider.setRange(0, int(self.transformed_duration * 1000))
                self.transformed_position_slider.setValue(0)
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
            data, sample_rate = sf.read(str(file_path))
            with lock:
                start_pos = getattr(self, position_attr) / 1000.0  # Convert ms to seconds
            start_sample = int(start_pos * sample_rate)
            
            if start_sample < len(data):
                data_to_play = data[start_sample:]
                
                # Play in chunks to allow stopping and position tracking
                chunk_duration = 0.1  # 100ms chunks
                chunk_samples = int(sample_rate * chunk_duration)
                
                current_pos = start_pos
                for i in range(0, len(data_to_play), chunk_samples):
                    if stop_event.is_set():
                        break
                    chunk = data_to_play[i:i+chunk_samples]
                    if len(chunk) == 0:
                        break
                    
                    # Play chunk
                    sd.play(chunk, sample_rate, blocking=True)
                    
                    # Update position
                    current_pos = start_pos + (i + len(chunk)) / sample_rate
                    with lock:
                        setattr(self, position_attr, current_pos * 1000)
                    
                    if current_pos >= duration:
                        with lock:
                            setattr(self, position_attr, duration * 1000)
                        break
        except Exception as e:
            print(f"Error playing audio: {e}")
        finally:
            stop_event.clear()
    
    def _play_audio_pydub(self, file_path: Path, stop_event: threading.Event, position_attr: str, duration: float, lock: Lock):
        """Play audio using pydub."""
        try:
            audio = AudioSegment.from_file(str(file_path))
            with lock:
                start_pos_ms = getattr(self, position_attr)
            
            if start_pos_ms < len(audio):
                audio_to_play = audio[start_pos_ms:]
                
                # Play in chunks for position tracking
                chunk_ms = 100  # 100ms chunks
                for i in range(0, len(audio_to_play), chunk_ms):
                    if stop_event.is_set():
                        break
                    chunk = audio_to_play[i:i+chunk_ms]
                    if len(chunk) == 0:
                        break
                    play(chunk)
                    
                    # Update position
                    with lock:
                        setattr(self, position_attr, start_pos_ms + i + len(chunk))
                        if getattr(self, position_attr) >= len(audio):
                            setattr(self, position_attr, len(audio))
                            break
        except Exception as e:
            print(f"Error playing audio: {e}")
        finally:
            stop_event.clear()
    
    def toggle_original_playback(self):
        """Toggle original audio playback."""
        if not self.original_audio_path or not self.original_audio_path.exists():
            return
        
        if self.original_playing:
            # Stop playback
            self.original_stop_event.set()
            if self.original_thread and self.original_thread.is_alive():
                self.original_thread.join(timeout=1.0)
            self.original_playing = False
            self.original_play_btn.setText("▶")
        else:
            # Stop transformed if playing
            if self.transformed_playing:
                self.toggle_transformed_playback()
            
            # Start playback
            self.original_stop_event.clear()
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
                return
            
            self.original_thread.start()
            self.original_playing = True
            self.original_play_btn.setText("⏸")
    
    def toggle_transformed_playback(self):
        """Toggle transformed audio playback."""
        if not self.transformed_audio_path or not self.transformed_audio_path.exists():
            return
        
        if self.transformed_playing:
            # Stop playback
            self.transformed_stop_event.set()
            if self.transformed_thread and self.transformed_thread.is_alive():
                self.transformed_thread.join(timeout=1.0)
            self.transformed_playing = False
            self.transformed_play_btn.setText("▶")
        else:
            # Stop original if playing
            if self.original_playing:
                self.toggle_original_playback()
            
            # Start playback
            self.transformed_stop_event.clear()
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
                return
            
            self.transformed_thread.start()
            self.transformed_playing = True
            self.transformed_play_btn.setText("⏸")
    
    def update_positions(self):
        """Update position displays (called by timer)."""
        # Update original
        with self.original_position_lock:
            current_original_pos = self.original_position
        
        if self.original_duration > 0:
            # Block slider signals to avoid feedback loop
            self.original_position_slider.blockSignals(True)
            self.original_position_slider.setValue(int(current_original_pos))
            self.original_position_slider.blockSignals(False)
            
            current_time = self.format_time(int(current_original_pos))
            total_time = self.format_time(int(self.original_duration * 1000))
            self.original_time_label.setText(f"{current_time} / {total_time}")
        
        # Update transformed
        with self.transformed_position_lock:
            current_transformed_pos = self.transformed_position
        
        if self.transformed_duration > 0:
            # Block slider signals to avoid feedback loop
            self.transformed_position_slider.blockSignals(True)
            self.transformed_position_slider.setValue(int(current_transformed_pos))
            self.transformed_position_slider.blockSignals(False)
            
            current_time = self.format_time(int(current_transformed_pos))
            total_time = self.format_time(int(self.transformed_duration * 1000))
            self.transformed_time_label.setText(f"{current_time} / {total_time}")
        
        # Check if playback finished
        if self.original_playing and not (self.original_thread and self.original_thread.is_alive()):
            self.original_playing = False
            self.original_play_btn.setText("▶")
            # Reset position if finished
            if current_original_pos >= self.original_duration * 1000:
                with self.original_position_lock:
                    self.original_position = 0
        
        if self.transformed_playing and not (self.transformed_thread and self.transformed_thread.is_alive()):
            self.transformed_playing = False
            self.transformed_play_btn.setText("▶")
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
            str(self.project_root / "data"),
            "Audio Files (*.wav *.mp3 *.m4a *.flac)"
        )
        if file_path:
            self.file_combo.addItem(file_path, file_path)
            self.file_combo.setCurrentIndex(self.file_combo.count() - 1)
    
    def apply_transforms(self):
        """Apply the selected transforms."""
        if self.file_combo.currentIndex() < 0:
            return
        
        input_file = self.file_combo.currentData()
        output_file = Path(self.output_path.text())
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # TODO: Implement transform application
        # For now, just copy the file as a placeholder
        # In real implementation, apply actual transforms here
        try:
            import shutil
            shutil.copy2(input_file, output_file)
            self.progress_bar.setValue(100)
            
            # Load transformed audio for playback
            self.load_transformed_audio(str(output_file))
        except Exception as e:
            self.progress_bar.setValue(0)
            # TODO: Show error message

