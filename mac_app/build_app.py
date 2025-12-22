#!/usr/bin/env python3
"""
Build script to create macOS .app bundle and .dmg file
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parent
BUILD_DIR = APP_DIR / "build"
DIST_DIR = APP_DIR / "dist"

def install_dependencies():
    """Install PyInstaller and other build dependencies"""
    print("Installing build dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "pywebview"], check=True)

def build_app():
    """Build the .app bundle using PyInstaller"""
    print("Building macOS app bundle...")
    
    # Clean previous builds
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    
    # Ensure UI files are set up and modified
    print("Setting up UI files for build...")
    from main import setup_ui_files, UI_DIR, STATIC_DIR, TEMPLATES_DIR
    setup_ui_files()
    
    # Collect all data files
    add_data_args = []
    
    # Add templates directory (must exist after setup_ui_files)
    if TEMPLATES_DIR.exists():
        add_data_args.extend(["--add-data", f"{TEMPLATES_DIR}{os.pathsep}templates"])
        print(f"  Added templates: {TEMPLATES_DIR}")
    else:
        print(f"  ⚠ Warning: Templates directory not found: {TEMPLATES_DIR}")
    
    # Add static directory (must exist after setup_ui_files)
    if STATIC_DIR.exists():
        add_data_args.extend(["--add-data", f"{STATIC_DIR}{os.pathsep}static"])
        print(f"  Added static: {STATIC_DIR}")
    else:
        print(f"  ⚠ Warning: Static directory not found: {STATIC_DIR}")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name", "Audiolab",
        "--windowed",  # No console window
        "--onedir",  # Create a directory bundle (better for macOS)
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms.cocoa",
        "--hidden-import", "http.server",
        "--collect-all", "webview",
        "--osx-bundle-identifier", "com.audiolab.desktop",
    ] + add_data_args + [
        str(APP_DIR / "main.py")
    ]
    
    subprocess.run(cmd, check=True, cwd=APP_DIR)
    
    # Move the .app to a better location
    app_bundle = DIST_DIR / "Audiolab.app"
    if app_bundle.exists():
        print(f"✓ App bundle created: {app_bundle}")
        return app_bundle
    else:
        raise FileNotFoundError("App bundle not found after build")

def create_dmg(app_bundle):
    """Create a .dmg file from the .app bundle"""
    print("Creating DMG file...")
    
    dmg_name = "Audiolab.dmg"
    dmg_path = DIST_DIR / dmg_name
    
    # Use hdiutil to create DMG (macOS built-in tool)
    cmd = [
        "hdiutil", "create",
        "-volname", "Audiolab",
        "-srcfolder", str(app_bundle),
        "-ov",
        "-format", "UDZO",
        str(dmg_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✓ DMG created: {dmg_path}")
        return dmg_path
    except subprocess.CalledProcessError:
        print("Warning: Could not create DMG automatically.")
        print("You can create it manually using:")
        print(f"  hdiutil create -volname Audiolab -srcfolder {app_bundle} -ov -format UDZO {dmg_path}")
        return None

def main():
    """Main build process"""
    print("=" * 60)
    print("Building Audiolab macOS Desktop App")
    print("=" * 60)
    
    try:
        install_dependencies()
        app_bundle = build_app()
        dmg_path = create_dmg(app_bundle)
        
        print("\n" + "=" * 60)
        print("Build completed successfully!")
        print("=" * 60)
        print(f"App bundle: {app_bundle}")
        if dmg_path:
            print(f"DMG file: {dmg_path}")
        print("\nTo test the app, double-click the .app bundle or .dmg file.")
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

