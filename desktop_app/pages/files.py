"""
File management page for browsing and uploading files.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QFileDialog, QGroupBox, QTextEdit, QFrame, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPixmap
from pathlib import Path
import shutil
from datetime import datetime


class CloudUploadIcon(QLabel):
    """Icon widget using file.png image."""
    
    def __init__(self, project_root: Path):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: transparent;")
        self.setScaledContents(False)
        
        # Load the image file
        image_path = project_root / "file.png"
        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                # Scale to appropriate size (80x80 or maintain aspect ratio)
                scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.setPixmap(scaled_pixmap)
                self.setMinimumSize(80, 80)
            else:
                # Image failed to load
                self.setMinimumSize(80, 80)
                self.setText("⚠")
        else:
            # Fallback: set minimum size even if image not found
            self.setMinimumSize(80, 80)
            self.setText("⚠")


class DragDropArea(QFrame):
    """Drag and drop file upload area."""
    
    def __init__(self, upload_callback=None, project_root=None):
        super().__init__()
        self.upload_callback = upload_callback
        self.project_root = project_root or Path.cwd()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: none;
                border-radius: 8px;
                background-color: #2d2d2d;
                min-height: 250px;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        """Initialize drag-drop area UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 10, 20, 20)
        
        # Image at the top
        icon_widget = CloudUploadIcon(self.project_root)
        layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Text container - all text below image
        # Main text: "Drag & drop files here"
        main_text = QLabel("Drag & drop files here")
        main_text.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 500;
                background-color: transparent;
            }
        """)
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_text.setWordWrap(False)
        layout.addWidget(main_text)
        
        # Secondary text with clickable link
    #    secondary_text = QLabel("or click to <a href='#' style='color: #93c5fd;'>Browse Files</a> from your system")
    # #    secondary_text.setStyleSheet("""
    #        secondary_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    #        secondary_text.setOpenExternalLinks(False)
    #        secondary_text.linkActivated.connect(self._on_browse_clicked)
    #        secondary_text.setWordWrap(False)
    #        layout.addWidget(secondary_text)
        
        # Support text
        support_text = QLabel("Supports audio, document, and experiment data files.")
        support_text.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 12px;
                background-color: transparent;
            }
        """)
        support_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_text.setWordWrap(False)
        layout.addWidget(support_text)
    
    def _on_browse_clicked(self):
        """Handle browse button click."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.wav *.mp3 *.m4a *.flac);;All Files (*.*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files and self.upload_callback:
                self.upload_callback(files)
    
    def mousePressEvent(self, event):
        """Handle mouse click to open file browser."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_browse_clicked()
        super().mousePressEvent(event)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Visual feedback - highlight border
            self.setStyleSheet("""
                QFrame {
                    border: none;
                    border-radius: 8px;
                    background-color: #2d2d2d;
                    min-height: 250px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Reset border style
        self.setStyleSheet("""
            QFrame {
                border: none;
                border-radius: 8px;
                background-color: #2d2d2d;
                min-height: 250px;
            }
        """)
    
    def dropEvent(self, event):
        """Handle drop event."""
        # Reset border style
        self.setStyleSheet("""
            QFrame {
                border: none;
                border-radius: 8px;
                background-color: #2d2d2d;
                min-height: 250px;
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
        
        # Breadcrumb and search bar
        breadcrumb_layout = QHBoxLayout()
        breadcrumb = QLabel("Home > Projects > Audio-Robustness-Lab > Files")
        breadcrumb.setStyleSheet("color: #9ca3af; font-size: 12px;")
        breadcrumb_layout.addWidget(breadcrumb)
        breadcrumb_layout.addStretch()
        
        # Search bar
        search_input = QLineEdit()
        search_input.setPlaceholderText("Q Search files...")
        search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px 12px;
                color: #9ca3af;
                font-size: 13px;
                min-width: 200px;
            }
            QLineEdit:focus {
                border: 1px solid #427eea;
            }
        """)
        breadcrumb_layout.addWidget(search_input)
        
        new_folder_btn = QPushButton("New Folder")
        new_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #427eea;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 13px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #3464ba;
            }
        """)
        breadcrumb_layout.addWidget(new_folder_btn)
        layout.addLayout(breadcrumb_layout)
        
        # Drag & Drop area
        self.drag_drop_area = DragDropArea(upload_callback=self.upload_files, project_root=self.project_root)
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
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Last Modified"])
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
                padding: 10px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #427eea;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #ffffff;
                padding: 10px;
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
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setShowGrid(False)
        # Hide the corner button (white square in header)
        self.file_table.setCornerButtonEnabled(False)
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
                for ext in ["*.wav", "*.mp3", "*.m4a", "*.flac", "*.json", "*.csv", "*.yaml", "*.yml", "*.pth", "*.pt", "*.zip"]:
                    files.extend(directory.glob(ext))
        
        # Sort files by modification time (newest first) and limit to 100
        sorted_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:100]
        
        # Set row count to actual number of files
        self.file_table.setRowCount(len(sorted_files))
        
        for i, file_path in enumerate(sorted_files):
            # Name
            name_item = QTableWidgetItem(file_path.name)
            name_item.setData(Qt.ItemDataRole.UserRole, str(file_path))
            self.file_table.setItem(i, 0, name_item)
            
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
            
            # Set row height
            self.file_table.setRowHeight(i, 40)
        
        # Resize columns to fit content
        self.file_table.resizeColumnsToContents()
        
        # Set minimum column widths
        self.file_table.setColumnWidth(0, max(200, self.file_table.columnWidth(0)))
        self.file_table.setColumnWidth(1, max(120, self.file_table.columnWidth(1)))
        self.file_table.setColumnWidth(2, max(100, self.file_table.columnWidth(2)))
        self.file_table.setColumnWidth(3, max(120, self.file_table.columnWidth(3)))
        
        # Select first row by default if available
        if self.file_table.rowCount() > 0:
            self.file_table.selectRow(0)
            self._on_selection_changed()
    
    def _on_selection_changed(self):
        """Update file details when selection changes."""
        selected_rows = self.file_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            name_item = self.file_table.item(row, 0)
            if name_item:
                file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
                if not file_path_str:
                    return
                
                file_name = name_item.text()
                type_item = self.file_table.item(row, 1)
                size_item = self.file_table.item(row, 2)
                mod_item = self.file_table.item(row, 3)
                
                file_type = type_item.text() if type_item else "Unknown"
                file_size = size_item.text() if size_item else "Unknown"
                last_modified = mod_item.text() if mod_item else "Unknown"
                
                # Get actual file path
                try:
                    file_path = Path(file_path_str)
                    actual_path = str(file_path) if file_path.exists() else f"/Audio-Robustness-Lab/experiments/{file_name}"
                except:
                    actual_path = f"/Audio-Robustness-Lab/experiments/{file_name}"
                
                # Update file details
                details_text = f"""Name: {file_name}
Type: {file_type}
Size: {file_size}
Last Modified: {last_modified}
Path: {actual_path}
Owner: System
Permissions: Read, Write"""
                self.file_details.setPlainText(details_text)
    
    def _on_select_file(self, row):
        """Handle file selection button click."""
        self.file_table.selectRow(row)
        self._on_selection_changed()
    
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
