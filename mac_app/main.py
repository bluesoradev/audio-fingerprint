#!/usr/bin/env python3
"""
macOS Desktop App for Audio Fingerprint Robustness Lab
Connects to VPS server at 78.46.37.169
"""

import webview
import sys
import os
import shutil
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

# Get the directory where this script is located
# Handle both development and bundled (PyInstaller) execution
if getattr(sys, 'frozen', False):
    # Running as bundled app - files are in the temp directory
    APP_DIR = Path(sys._MEIPASS)
    # In bundled mode, templates and static are already copied to APP_DIR
    UI_DIR = None  # Not needed in bundled mode
else:
    # Running from source
    APP_DIR = Path(__file__).parent
    UI_DIR = APP_DIR.parent / "ui"

STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

# VPS server configuration
VPS_HOST = "78.46.37.169"
VPS_PORT = "8080"  # Default FastAPI port, adjust if needed
VPS_API_BASE = f"http://{VPS_HOST}:{VPS_PORT}/api"

# Local server port for serving UI files
LOCAL_PORT = 8765

class CustomHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler to serve files from app directory"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)
    
    def log_message(self, format, *args):
        """Suppress log messages"""
        pass

def setup_ui_files():
    """Copy and modify UI files for desktop app"""
    if getattr(sys, 'frozen', False):
        # In bundled mode, files are already copied by PyInstaller
        # Just need to modify them
        print("Modifying bundled UI files...")
    else:
        # In development mode, copy files from UI directory
        print("Setting up UI files...")
        
        # Copy templates
        if TEMPLATES_DIR.exists():
            shutil.rmtree(TEMPLATES_DIR)
        if UI_DIR and (UI_DIR / "templates").exists():
            shutil.copytree(UI_DIR / "templates", TEMPLATES_DIR)
        else:
            TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            print("⚠ Warning: templates directory not found")
        
        # Copy static files
        if STATIC_DIR.exists():
            shutil.rmtree(STATIC_DIR)
        if UI_DIR and (UI_DIR / "static").exists():
            shutil.copytree(UI_DIR / "static", STATIC_DIR)
        else:
            STATIC_DIR.mkdir(parents=True, exist_ok=True)
            print("⚠ Warning: static directory not found")
    
    # Modify app.js to use VPS API (works in both modes)
    app_js_path = STATIC_DIR / "app.js"
    if app_js_path.exists():
        content = app_js_path.read_text()
        # Replace API_BASE to point to VPS
        content = content.replace("const API_BASE = '/api';", f"const API_BASE = '{VPS_API_BASE}';")
        # Also handle any other API references (hardcoded paths)
        content = content.replace("`/api/", f"`{VPS_API_BASE}/")
        content = content.replace("'/api/", f"'{VPS_API_BASE}/")
        content = content.replace('"/api/', f'"{VPS_API_BASE}/')
        content = content.replace("`${API_BASE}/", f"`{VPS_API_BASE}/")
        app_js_path.write_text(content)
        print(f"✓ Modified app.js to use VPS API: {VPS_API_BASE}")
    else:
        print("⚠ Warning: app.js not found")
    
    # Modify index.html to use local static files
    index_html_path = TEMPLATES_DIR / "index.html"
    if index_html_path.exists():
        content = index_html_path.read_text()
        # Replace static file paths
        content = content.replace('/static/', f'http://localhost:{LOCAL_PORT}/static/')
        index_html_path.write_text(content)
        print("✓ Modified index.html to use local static files")
    else:
        print("⚠ Warning: index.html not found")

def start_local_server():
    """Start a local HTTP server to serve UI files"""
    server = HTTPServer(('localhost', LOCAL_PORT), CustomHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"✓ Local server started on http://localhost:{LOCAL_PORT}")
    return server

def main():
    """Launch the desktop app"""
    print("=" * 60)
    print("Audiolab Desktop App")
    print(f"Connecting to VPS: {VPS_HOST}:{VPS_PORT}")
    print("=" * 60)
    
    # Setup UI files
    setup_ui_files()
    
    # Start local server
    server = start_local_server()
    
    # Wait a moment for server to start
    time.sleep(0.5)
    
    # Create webview window
    window = webview.create_window(
        'Audiolab',
        f'http://localhost:{LOCAL_PORT}/templates/index.html',
        width=1400,
        height=900,
        min_size=(1200, 700),
        resizable=True,
        fullscreen=False,
        background_color='#1e1e1e'
    )
    
    # Start webview
    try:
        webview.start(debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.shutdown()

if __name__ == '__main__':
    main()

