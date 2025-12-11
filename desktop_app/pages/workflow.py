"""
Workflow page for step-by-step experiment execution.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from pathlib import Path
import subprocess
import sys
import queue
import threading
from datetime import datetime


class ProcessWorker(QThread):
    """Worker thread for running processes."""
    log_output = pyqtSignal(str)
    finished = pyqtSignal(int)
    
    def __init__(self, command, log_queue):
        super().__init__()
        self.command = command
        self.log_queue = log_queue
        self.process = None
    
    def run(self):
        """Run the command and emit logs."""
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.log_output.emit(line.strip())
            
            self.process.wait()
            self.finished.emit(self.process.returncode)
        except Exception as e:
            self.log_output.emit(f"Error: {e}")
            self.finished.emit(1)
    
    def terminate_process(self):
        """Terminate the running process."""
        if self.process:
            self.process.terminate()


class WorkflowPage(QWidget):
    """Workflow management page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.current_worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        title = QLabel("Workflow Management")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)
        
        # Overall controls
        controls_group = QGroupBox("Overall Workflow Controls")
        controls_group.setStyleSheet("""
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
                color: #ffffff;
            }
        """)
        controls_layout = QHBoxLayout(controls_group)
        
        self.run_btn = QPushButton("▶ Run Workflow")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: #ffffff;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        self.cancel_btn = QPushButton("✕ Cancel Workflow")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #787878;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
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
        self.progress_label = QLabel("0% Complete")
        self.progress_label.setStyleSheet("color: #ffffff; min-width: 80px;")
        
        controls_layout.addWidget(self.run_btn)
        controls_layout.addWidget(self.cancel_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.progress_label)
        controls_layout.addWidget(self.progress_bar)
        controls_layout.setStretchFactor(self.progress_bar, 1)
        
        layout.addWidget(controls_group)
        
        # Workflow steps (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
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
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: #1e1e1e;")
        scroll_layout = QVBoxLayout(scroll_widget)
        
        steps_group = QGroupBox("Workflow Steps")
        steps_group.setStyleSheet("""
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
                color: #ffffff;
            }
        """)
        steps_layout = QVBoxLayout(steps_group)
        
        # Step 1: Create Test Audio
        self.step1_group = self._create_step_group(
            "Step 1: Create Test Audio",
            {"num_files": (QSpinBox, 2, 1, 10),
             "duration": (QDoubleSpinBox, 5.0, 1.0, 60.0),
             "output_dir": (QLineEdit, "data/test_audio")}
        )
        steps_layout.addWidget(self.step1_group)
        
        # Step 2: Create Manifest
        self.step2_group = self._create_step_group(
            "Step 2: Create Manifest",
            {"audio_dir": (QLineEdit, "data/test_audio"),
             "output": (QLineEdit, "data/manifests/test_manifest.csv")}
        )
        steps_layout.addWidget(self.step2_group)
        
        # Step 3-7: Placeholder steps
        for i, step_name in enumerate([
            "Step 3: Ingest Files",
            "Step 4: Generate Transforms",
            "Step 5: Build Index",
            "Step 6: Run Queries",
            "Step 7: Analyze Results"
        ], 3):
            step_group = self._create_step_group(step_name, {})
            steps_layout.addWidget(step_group)
        
        scroll_layout.addWidget(steps_group)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Live log
        log_group = QGroupBox("Live Workflow Log")
        log_group.setStyleSheet("""
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
                color: #ffffff;
            }
        """)
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 10))
        self.log_output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                color: #c8c8c8;
            }
        """)
        log_layout.addWidget(self.log_output)
        
        layout.addWidget(log_group)
        
        # Connect signals
        self.run_btn.clicked.connect(self.start_workflow)
        self.cancel_btn.clicked.connect(self.cancel_workflow)
    
    def _create_step_group(self, title: str, fields: dict) -> QGroupBox:
        """Create a step group with form fields."""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ffffff;
            }
        """)
        layout = QHBoxLayout(group)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_widgets = {}
        
        for field_name, (widget_class, default, *args) in fields.items():
            label_text = field_name.replace("_", " ").title() + ":"
            label = QLabel(label_text)
            label.setStyleSheet("color: #ffffff;")
            
            if widget_class == QLineEdit:
                widget = QLineEdit(str(default))
                widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #1e1e1e;
                        color: #ffffff;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 6px;
                        min-width: 200px;
                    }
                """)
            elif widget_class == QSpinBox:
                widget = QSpinBox()
                widget.setRange(*args)
                widget.setValue(int(default))
                widget.setStyleSheet("""
                    QSpinBox {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 6px;
                        min-width: 80px;
                    }
                    QSpinBox::up-button, QSpinBox::down-button {
                        width: 20px;
                        background-color: #f0f0f0;
                    }
                """)
            elif widget_class == QDoubleSpinBox:
                widget = QDoubleSpinBox()
                widget.setRange(*args)
                widget.setValue(float(default))
                widget.setStyleSheet("""
                    QDoubleSpinBox {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 6px;
                        min-width: 80px;
                    }
                    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                        width: 20px;
                        background-color: #f0f0f0;
                    }
                """)
            else:
                widget = widget_class()
            
            form_layout.addRow(label, widget)
            form_widgets[field_name] = widget
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        start_btn = QPushButton("Start")
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                border: none;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setEnabled(False)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                border: none;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #787878;
            }
        """)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        group.form_widgets = form_widgets
        group.start_btn = start_btn
        group.cancel_btn = cancel_btn
        
        return group
    
    def start_workflow(self):
        """Start the full workflow."""
        self.log_output.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] Starting workflow...")
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        # TODO: Implement full workflow execution
    
    def cancel_workflow(self):
        """Cancel the running workflow."""
        if self.current_worker:
            self.current_worker.terminate_process()
            self.log_output.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] Workflow cancelled.")
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

