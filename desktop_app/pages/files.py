"""
File management page for browsing and uploading files.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QFileDialog, QGroupBox, QTextEdit, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path
import shutil
from datetime import datetime


class DragDropArea(QFrame):
    """Drag and drop file upload area."""
    
    def __init__(self, upload_callback=None):
        super().__init__()
        self.upload_callback = upload_callback
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                background-color: #2d2d2d;
                min-height: 200px;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        """Initialize drag-drop area UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        # Cloud upload icon
        icon_label = QLabel("☁️")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Text
        text_label = QLabel("Drag & Drop Files Here")
        text_label.setStyleSheet("""
            QLabel {
                color: #c8c8c8;
                font-size: 18px;
                font-weight: 500;
            }
        """)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)
        
        subtitle = QLabel("Or click to browse your local file system for audio and experiment data.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Browse button
        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #c8c8c8;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #427eea;
                color: white;
            }
        """)
        self.browse_btn.setMaximumWidth(150)
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        layout.addWidget(self.browse_btn, 0, Qt.AlignmentFlag.AlignCenter)
    
    def _on_browse_clicked(self):
        """Handle browse button click."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.wav *.mp3 *.m4a *.flac);;All Files (*.*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files and self.upload_callback:
                self.upload_callback(files)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Visual feedback - highlight border
            self.setStyleSheet("""
                QFrame {
                    border: 2px dashed #427eea;
                    border-radius: 8px;
                    background-color: #2d2d2d;
                    min-height: 200px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Reset border style
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                background-color: #2d2d2d;
                min-height: 200px;
            }
        """)
    
    def dropEvent(self, event):
        """Handle drop event."""
        # Reset border style
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                background-color: #2d2d2d;
                min-height: 200px;
            }
        """)
        
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files and self.upload_callback:
            self.upload_callback(files)
        event.acceptProposedAction()


class FilesPage(QWidget):
    """File management page."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.init_ui()
        self.load_files()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        title = QLabel("File Management")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)
        
        subtitle = QLabel("Browse, upload, and manage all your audio and experiment-related files.")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Breadcrumb
        breadcrumb_layout = QHBoxLayout()
        breadcrumb = QLabel("Home / Projects / Audio-Robustness-Lab")
        breadcrumb.setStyleSheet("color: #9ca3af; font-size: 12px;")
        breadcrumb_layout.addWidget(breadcrumb)
        breadcrumb_layout.addStretch()
        
        new_folder_btn = QPushButton("New Folder")
        new_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #c8c8c8;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #427eea;
                color: white;
            }
        """)
        breadcrumb_layout.addWidget(new_folder_btn)
        layout.addLayout(breadcrumb_layout)
        
        # Drag & Drop area
        self.drag_drop_area = DragDropArea(upload_callback=self.upload_files)
        layout.addWidget(self.drag_drop_area)
        
        # Main content area (File Browser + File Details)
        main_content = QHBoxLayout()
        main_content.setSpacing(20)
        
        # File Browser
        browser_group = QGroupBox("File Browser")
        browser_group.setStyleSheet("""
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
        browser_layout = QVBoxLayout(browser_group)
        
        browser_subtitle = QLabel("Manage and select files for your experiments.")
        browser_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        browser_layout.addWidget(browser_subtitle)
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Last Modified", "Actions"])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #427eea;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #3d3d3d;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
                border: none;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 4px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.file_table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        browser_layout.addWidget(self.file_table)
        main_content.addWidget(browser_group, 2)
        
        # File Details
        details_group = QGroupBox("File Details")
        details_group.setStyleSheet(browser_group.styleSheet())
        details_layout = QVBoxLayout(details_group)
        
        details_subtitle = QLabel("Detailed information about the selected file.")
        details_subtitle.setStyleSheet("color: #9ca3af; font-size: 13px; margin-bottom: 10px;")
        details_layout.addWidget(details_subtitle)
        
        self.file_details = QTextEdit()
        self.file_details.setReadOnly(True)
        self.file_details.setPlaceholderText("Select a file to view its details.")
        self.file_details.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                color: #9ca3af;
                min-height: 300px;
            }
        """)
        details_layout.addWidget(self.file_details)
        main_content.addWidget(details_group, 1)
        
        layout.addLayout(main_content)
        layout.addStretch()
    
    def load_files(self):
        """Load files from the selected directory."""
        self.file_table.setRowCount(0)
        
        # Check multiple directories
        directories = [
            self.data_dir / "originals",
            self.data_dir / "transformed",
            self.data_dir / "test_audio",
            self.data_dir / "manipulated",
            self.project_root / "models",
            self.project_root / "reports",
        ]
        
        files = []
        for directory in directories:
            if directory.exists():
                for ext in ["*.wav", "*.mp3", "*.json", "*.csv", "*.yaml", "*.yml", "*.pth", "*.pt", "*.zip"]:
                    files.extend(directory.glob(ext))
        
        self.file_table.setRowCount(len(files))
        for i, file_path in enumerate(sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:50]):
            # Name
            self.file_table.setItem(i, 0, QTableWidgetItem(file_path.name))
            
            # Type
            ext = file_path.suffix[1:].upper() if file_path.suffix else "Unknown"
            if ext in ["WAV", "MP3", "M4A", "FLAC"]:
                file_type = "Audio File"
            elif ext in ["PTH", "PT"]:
                file_type = "Model"
            elif ext == "ZIP":
                file_type = "Dataset"
            elif ext in ["CSV", "JSON", "YAML", "YML"]:
                file_type = "Log File" if "log" in file_path.name.lower() else "Config File"
            elif ext == "PY":
                file_type = "Python Script"
            else:
                file_type = ext
            self.file_table.setItem(i, 1, QTableWidgetItem(file_type))
            
            # Size
            size = file_path.stat().st_size
            if size > 1024 * 1024 * 1024:
                size_str = f"{size / (1024**3):.2f} GB"
            elif size > 1024 * 1024:
                size_str = f"{size / (1024**2):.2f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size} B"
            self.file_table.setItem(i, 2, QTableWidgetItem(size_str))
            
            # Last Modified
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            self.file_table.setItem(i, 3, QTableWidgetItem(mod_time.strftime("%Y-%m-%d")))
            
            # Actions
            select_btn = QPushButton("Select")
            select_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    border: none;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #427eea;
                    color: #ffffff;
                }
            """)
            select_btn.clicked.connect(lambda checked, row=i: self._on_select_file(row))
            self.file_table.setCellWidget(i, 4, select_btn)
        
        self.file_table.resizeColumnsToContents()
        # Ensure Actions column has minimum width
        if self.file_table.columnCount() > 4:
            self.file_table.setColumnWidth(4, 100)
    
    def _on_selection_changed(self):
        """Update button styles when selection changes."""
        selected_rows = set()
        for index in self.file_table.selectionModel().selectedRows():
            selected_rows.add(index.row())
        
        for row in range(self.file_table.rowCount()):
            btn = self.file_table.cellWidget(row, 4)
            if btn:
                if row in selected_rows:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #427eea;
                            color: #ffffff;
                            padding: 6px 12px;
                            border-radius: 4px;
                            font-size: 12px;
                            border: none;
                            min-width: 60px;
                        }
                        QPushButton:hover {
                            background-color: #3464ba;
                            color: #ffffff;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3d3d3d;
                            color: #ffffff;
                            padding: 6px 12px;
                            border-radius: 4px;
                            font-size: 12px;
                            border: none;
                            min-width: 60px;
                        }
                        QPushButton:hover {
                            background-color: #427eea;
                            color: #ffffff;
                        }
                    """)
    
    def _on_select_file(self, row):
        """Handle file selection button click."""
        self.file_table.selectRow(row)
        # Update file details
        file_item = self.file_table.item(row, 0)
        if file_item:
            file_name = file_item.text()
            # TODO: Load and display file details
            self.file_details.setPlainText(f"Selected: {file_name}")
    
    def upload_files(self, file_paths):
        """Upload files to the data directory."""
        if not file_paths:
            return
        
        # Determine target directory based on file type
        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg'}
        target_dir = self.data_dir / "originals"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_count = 0
        failed_count = 0
        failed_files = []
        
        for file_path_str in file_paths:
            try:
                source_path = Path(file_path_str)
                if not source_path.exists():
                    failed_files.append(f"{source_path.name} (file not found)")
                    failed_count += 1
                    continue
                
                # Check if it's an audio file
                if source_path.suffix.lower() in audio_extensions:
                    target_path = target_dir / source_path.name
                else:
                    # For non-audio files, put in a general uploads directory
                    uploads_dir = self.data_dir / "uploads"
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    target_path = uploads_dir / source_path.name
                
                # Handle duplicate files by adding a timestamp
                if target_path.exists():
                    stem = target_path.stem
                    suffix = target_path.suffix
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    target_path = target_path.parent / f"{stem}_{timestamp}{suffix}"
                
                # Copy file
                shutil.copy2(source_path, target_path)
                uploaded_count += 1
                
            except Exception as e:
                failed_files.append(f"{Path(file_path_str).name} ({str(e)})")
                failed_count += 1
        
        # Show result message
        if uploaded_count > 0 and failed_count == 0:
            QMessageBox.information(
                self,
                "Upload Successful",
                f"Successfully uploaded {uploaded_count} file(s) to:\n{target_dir}"
            )
        elif uploaded_count > 0 and failed_count > 0:
            msg = f"Uploaded {uploaded_count} file(s) successfully.\n\n"
            msg += f"Failed to upload {failed_count} file(s):\n"
            msg += "\n".join(failed_files[:5])  # Show first 5 failures
            if len(failed_files) > 5:
                msg += f"\n... and {len(failed_files) - 5} more"
            QMessageBox.warning(self, "Partial Upload", msg)
        else:
            msg = f"Failed to upload {failed_count} file(s):\n"
            msg += "\n".join(failed_files[:5])
            if len(failed_files) > 5:
                msg += f"\n... and {len(failed_files) - 5} more"
            QMessageBox.critical(self, "Upload Failed", msg)
        
        # Refresh file list
        if uploaded_count > 0:
            self.load_files()
