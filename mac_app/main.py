#!/usr/bin/env python3
"""
macOS Desktop App for Audio Fingerprint Robustness Lab
Connects to VPS server at 78.46.37.169
"""

import sys
import os
import re
from pathlib import Path

# Simplified path setup for PyInstaller bundles (following audio-ai-mac approach)
# PyInstaller handles most of this automatically, we just need minimal setup
if getattr(sys, 'frozen', False):
    # Running as bundled app
    # PyInstaller sets up sys.path automatically, but we may need to add system site-packages for PyObjC
    system_site_packages = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
    if os.path.exists(system_site_packages) and str(system_site_packages) not in sys.path:
        sys.path.append(system_site_packages)

# Import webview
import webview
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

# Get the directory where this script is located
# Handle both development and bundled (PyInstaller) execution
if getattr(sys, 'frozen', False):
    # Running as bundled app - files are in the temp directory
    APP_DIR = Path(sys._MEIPASS)
    # In bundled mode, templates and static are already copied to APP_DIR by PyInstaller
    UI_DIR = None  # Not needed in bundled mode
    # PyInstaller puts them in APP_DIR/templates and APP_DIR/static
    STATIC_DIR = APP_DIR / "static"
    TEMPLATES_DIR = APP_DIR / "templates"
    
    # If files not in _MEIPASS, check Contents/Resources (PyInstaller APP mode)
    if not STATIC_DIR.exists() or not TEMPLATES_DIR.exists():
        # Try to find the app bundle's Resources directory
        executable_path = Path(sys.executable)
        # sys.executable points to Contents/MacOS/Audiolab in bundled app
        if 'Contents' in executable_path.parts:
            resources_dir = executable_path.parent.parent / "Resources"
            if resources_dir.exists():
                resources_static = resources_dir / "static"
                resources_templates = resources_dir / "templates"
                if resources_static.exists():
                    STATIC_DIR = resources_static
                if resources_templates.exists():
                    TEMPLATES_DIR = resources_templates
                # Update APP_DIR to Resources for serving files
                APP_DIR = resources_dir
    
    # Debug: Print what's in APP_DIR
    print(f"Bundled APP_DIR: {APP_DIR}")
    if APP_DIR.exists():
        print(f"Contents of APP_DIR: {list(APP_DIR.iterdir())}")
    print(f"STATIC_DIR: {STATIC_DIR} (exists: {STATIC_DIR.exists()})")
    print(f"TEMPLATES_DIR: {TEMPLATES_DIR} (exists: {TEMPLATES_DIR.exists()})")
    if TEMPLATES_DIR.exists():
        print(f"Templates contents: {list(TEMPLATES_DIR.iterdir())}")
    if STATIC_DIR.exists():
        print(f"Static contents: {list(STATIC_DIR.iterdir())}")
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
# Try to find an available port
LOCAL_PORT = 8765
import socket
def find_free_port(start_port=8765, max_attempts=10):
    """Find a free port starting from start_port"""
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start_port  # Fallback to original port

LOCAL_PORT = find_free_port()

class CustomHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler to serve files from app directory"""
    def __init__(self, *args, **kwargs):
        # Serve from APP_DIR, which contains templates/ and static/ subdirectories
        super().__init__(*args, directory=str(APP_DIR), **kwargs)
    
    def translate_path(self, path):
        """Translate URL path to filesystem path"""
        # Remove query string and fragment
        path = path.split('?')[0].split('#')[0]
        # Remove leading slash
        path = path.lstrip('/')
        
        # Debug: print requested path
        # print(f"[HTTP] Requested path: {path}")
        
        # If path starts with templates/ or static/, serve from APP_DIR
        if path.startswith('templates/') or path.startswith('static/'):
            full_path = APP_DIR / path
        elif path == '' or path == 'index.html':
            # Root path or index.html -> serve templates/index.html
            full_path = APP_DIR / "templates" / "index.html"
        else:
            # Default behavior - try to find in APP_DIR
            full_path = APP_DIR / path
        
        # Verify file exists
        if not os.path.exists(full_path):
            # Try alternative locations
            if path.startswith('static/'):
                # Try without static/ prefix
                alt_path = APP_DIR / path.replace('static/', '')
                if os.path.exists(alt_path):
                    full_path = alt_path
        
        return str(full_path)
    
    def log_message(self, format, *args):
        """Suppress log messages"""
        pass

def setup_ui_files():
    """Copy and modify UI files for desktop app"""
    if getattr(sys, 'frozen', False):
        # In bundled mode, files are already copied by PyInstaller
        # But we need to ensure they exist and have content
        print("Modifying bundled UI files...")
        
        # If index.html is missing or empty, try to copy from source
        index_html_path = TEMPLATES_DIR / "index.html"
        if not index_html_path.exists() or index_html_path.stat().st_size == 0:
            print("⚠ index.html is missing or empty, attempting to restore...")
            # Try to find source file
            source_ui_dir = Path(__file__).parent.parent / "ui"
            source_index = source_ui_dir / "templates" / "index.html"
            if source_index.exists() and source_index.stat().st_size > 0:
                shutil.copy2(source_index, index_html_path)
                print(f"✓ Restored index.html from source ({source_index.stat().st_size} bytes)")
            else:
                print("⚠ Could not find source index.html")
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
    if app_js_path.exists() and app_js_path.stat().st_size > 0:
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
        print("⚠ Warning: app.js not found or empty")
    
    # Modify index.html to use local static files
    index_html_path = TEMPLATES_DIR / "index.html"
    if index_html_path.exists() and index_html_path.stat().st_size > 0:
        content = index_html_path.read_text()
        # Replace static file paths - but only if not already replaced
        # Check if already contains localhost URL to avoid duplicate replacements
        if f'http://localhost:{LOCAL_PORT}/static/' not in content:
            # First, clean up any existing incorrect localhost URLs
            content = re.sub(r'http://localhost:\d+/static/', '/static/', content)
            # Now replace /static/ with the correct URL
            content = content.replace('/static/', f'http://localhost:{LOCAL_PORT}/static/')
        # Also ensure app.js script tag uses the correct URL
        content = re.sub(r'src=["\']http://localhost:\d+/static/app\.js["\']', 
                        f'src="http://localhost:{LOCAL_PORT}/static/app.js"', content)
        content = re.sub(r'src=["\']/static/app\.js["\']', 
                        f'src="http://localhost:{LOCAL_PORT}/static/app.js"', content)
        index_html_path.write_text(content)
        print("✓ Modified index.html to use local static files")
    else:
        print(f"⚠ Warning: index.html not found or empty (exists: {index_html_path.exists()}, size: {index_html_path.stat().st_size if index_html_path.exists() else 0})")

def start_local_server():
    """Start a local HTTP server to serve UI files"""
    server = HTTPServer(('localhost', LOCAL_PORT), CustomHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"✓ Local server started on http://localhost:{LOCAL_PORT}")
    return server

def main():
    """Launch the desktop app"""
    try:
        print("=" * 60)
        print("Audiolab Desktop App")
        print(f"Connecting to VPS: {VPS_HOST}:{VPS_PORT}")
        print("=" * 60)
        
        # Setup UI files
        try:
            setup_ui_files()
        except Exception as e:
            print(f"Error setting up UI files: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Start local server
        try:
            server = start_local_server()
        except Exception as e:
            print(f"Error starting local server: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Wait a moment for server to start
        time.sleep(0.5)
        
        # Create webview window
        try:
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
        except Exception as e:
            print(f"Error creating webview window: {e}")
            import traceback
            traceback.print_exc()
            server.shutdown()
            return
        
        # Start webview
        try:
            webview.start(debug=False)
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error starting webview: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                server.shutdown()
            except:
                pass
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        # Show error dialog if possible
        try:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Error", f"Failed to start app: {e}")
        except:
            pass

if __name__ == '__main__':
    main()

