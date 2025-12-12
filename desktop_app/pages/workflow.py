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
                border: none;
                border-radius: 0px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: transparent;
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
        self.progress_label.setStyleSheet("color: #ffffff; min-width: 100px;")
        
        controls_layout.addWidget(self.run_btn)
        controls_layout.addWidget(self.cancel_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.progress_label)
        controls_layout.addWidget(self.progress_bar)
        controls_layout.setStretchFactor(self.progress_bar, 2)
        
        layout.addWidget(controls_group)
        
        # Workflow steps
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
        steps_group_layout = QVBoxLayout(steps_group)
        
        # Create scrollable content widget
        steps_content = QWidget()
        steps_layout = QVBoxLayout(steps_content)
        steps_layout.setSpacing(10)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        
        # Step 1: Create Test Audio
        self.step1_group = self._create_step_group(
            "Step 1: Create Test Audio",
            {"num_files": (QSpinBox, 1, 1, 10),
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
        
        # Step 3: Ingest Files
        self.step3_group = self._create_step_group(
            "Step 3: Ingest Files",
            {"manifest_file": (QLineEdit, "data/manifests/test_manifest.csv"),
             "sample_rate": (QSpinBox, 44100, 8000, 192000)}
        )
        steps_layout.addWidget(self.step3_group)
        
        # Step 4: Build Index
        self.step4_group = self._create_step_group(
            "Step 4: Build Index",
            {"audio_dir": (QLineEdit, "data/test_audio"),
             "output_index": (QLineEdit, "data/indexes/test_index.faiss")}
        )
        steps_layout.addWidget(self.step4_group)
        
        # Step 5: Run Queries
        self.step5_group = self._create_step_group(
            "Step 5: Run Queries",
            {"manifest_file": (QLineEdit, "data/manifests/test_manifest.csv"),
             "index_file": (QLineEdit, "data/indexes/test_index.faiss"),
             "output_results": (QLineEdit, "data/results/query_results.json")}
        )
        steps_layout.addWidget(self.step5_group)
        
        steps_layout.addStretch()
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(steps_content)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
                border: none;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 4px;
                min-height: 30px;
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
        
        steps_group_layout.addWidget(scroll_area)
        layout.addWidget(steps_group, 1)
        
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
                padding-top: 20px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #ffffff;
            }
        """)
        layout = QHBoxLayout(group)
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(20)
        
        form_widgets = {}
        
        # Create a vertical layout for form fields
        form_container = QWidget()
        form_container.setStyleSheet("background-color: transparent;")
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        field_list = list(fields.items())
        
        # First row: two fields side by side (if we have at least 2 fields)
        if len(field_list) >= 2:
            first_row = QHBoxLayout()
            first_row.setSpacing(20)
            first_row.setContentsMargins(0, 0, 0, 0)
            
            for idx in range(2):
                field_name, (widget_class, default, *args) = field_list[idx]
                label_text = field_name.replace("_", " ").title() + ":"
                label = QLabel(label_text)
                label.setStyleSheet("color: #ffffff; min-width: 90px; font-size: 13px;")
                
                if widget_class == QLineEdit:
                    widget = QLineEdit(str(default))
                    widget.setStyleSheet("""
                        QLineEdit {
                            background-color: #353535;
                            color: #ffffff;
                            border: 1px solid #3d3d3d;
                            border-radius: 4px;
                            padding: 12px 20px;
                            min-width: 150px;
                            font-size: 13px;
                        }
                        QLineEdit:focus {
                            border: 1px solid #427eea;
                        }
                    """)
                elif widget_class == QSpinBox:
                    widget = QSpinBox()
                    widget.setRange(*args)
                    widget.setValue(int(default))
                    widget.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
                    widget.setStyleSheet("""
                        QSpinBox {
                            background-color: #353535;
                            color: #ffffff;
                            border: 1px solid #3d3d3d;
                            border-radius: 4px;
                            padding: 12px 20px;
                            min-width: 80px;
                            font-size: 13px;
                        }
                        QSpinBox:focus {
                            border: 1px solid #427eea;
                        }
                    """)
                elif widget_class == QDoubleSpinBox:
                    widget = QDoubleSpinBox()
                    widget.setRange(*args)
                    widget.setValue(float(default))
                    widget.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
                    widget.setStyleSheet("""
                        QDoubleSpinBox {
                            background-color: #353535;
                            color: #ffffff;
                            border: 1px solid #3d3d3d;
                            border-radius: 4px;
                            padding: 12px 20px;
                            min-width: 80px;
                            font-size: 13px;
                        }
                        QDoubleSpinBox:focus {
                            border: 1px solid #427eea;
                        }
                    """)
                else:
                    widget = widget_class()
                
                form_widgets[field_name] = widget
                
                field_widget = QWidget()
                field_layout = QHBoxLayout(field_widget)
                field_layout.setContentsMargins(0, 0, 0, 0)
                field_layout.setSpacing(12)
                field_layout.addWidget(label)
                field_layout.addWidget(widget, 1)
                first_row.addWidget(field_widget, 1)
            
            form_layout.addLayout(first_row)
        
        # Second row: remaining fields (one per row)
        for idx in range(2, len(field_list)):
            field_name, (widget_class, default, *args) = field_list[idx]
            label_text = field_name.replace("_", " ").title() + ":"
            label = QLabel(label_text)
            label.setStyleSheet("color: #ffffff; min-width: 90px; font-size: 13px;")
            
            if widget_class == QLineEdit:
                widget = QLineEdit(str(default))
                widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #353535;
                        color: #ffffff;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 12px 20px;
                        min-width: 200px;
                        font-size: 13px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #427eea;
                    }
                """)
            elif widget_class == QSpinBox:
                widget = QSpinBox()
                widget.setRange(*args)
                widget.setValue(int(default))
                widget.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
                widget.setStyleSheet("""
                    QSpinBox {
                        background-color: #353535;
                        color: #ffffff;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 12px 20px;
                        min-width: 80px;
                        font-size: 13px;
                    }
                    QSpinBox:focus {
                        border: 1px solid #427eea;
                    }
                """)
            elif widget_class == QDoubleSpinBox:
                widget = QDoubleSpinBox()
                widget.setRange(*args)
                widget.setValue(float(default))
                widget.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
                widget.setStyleSheet("""
                    QDoubleSpinBox {
                        background-color: #353535;
                        color: #ffffff;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                        padding: 12px 20px;
                        min-width: 80px;
                        font-size: 13px;
                    }
                    QDoubleSpinBox:focus {
                        border: 1px solid #427eea;
                    }
                """)
            else:
                widget = widget_class()
            
            form_widgets[field_name] = widget
            
            field_widget = QWidget()
            field_widget.setStyleSheet("background-color: transparent;")
            field_layout = QHBoxLayout(field_widget)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(12)
            field_layout.addWidget(label)
            field_layout.addWidget(widget, 1)
            form_layout.addWidget(field_widget)
        
        layout.addWidget(form_container, 1)
        layout.addStretch()
        
        start_btn = QPushButton("▶ Start")
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: #ffffff;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
            QPushButton:pressed {
                background-color: #2a5098;
            }
        """)
        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setEnabled(False)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #787878;
            }
        """)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
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

