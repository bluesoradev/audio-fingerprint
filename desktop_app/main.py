"""
Main entry point for the Audio Fingerprint Robustness Lab desktop application.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from desktop_app.window import MainWindow


def main():
    """Launch the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Robustness Lab")
    app.setOrganizationName("Audio Robustness Lab")
    
    # High DPI scaling is enabled by default in PyQt6/Qt6
    # No need to set these attributes anymore
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

