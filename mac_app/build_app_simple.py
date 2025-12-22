#!/usr/bin/env python3
"""
Simplified build script using PyInstaller spec file
Based on the working audio-ai-mac project methodology
"""
import subprocess
import sys
import shutil
import os
from pathlib import Path

APP_DIR = Path(__file__).parent
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"

def main():
    """Main build process"""
    print("=" * 60)
    print("Building Audiolab macOS Desktop App")
    print("=" * 60)
    
    # Clean previous builds
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    
    # Ensure UI files are set up
    print("Setting up UI files...")
    try:
        from main import setup_ui_files
        setup_ui_files()
        print("✓ UI files set up")
    except Exception as e:
        print(f"⚠ Warning: UI setup failed: {e}")
    
    # Build using PyInstaller spec file
    spec_file = APP_DIR / "Audiolab.spec"
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        sys.exit(1)
    
    print(f"Building with PyInstaller spec file: {spec_file}")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--clean",
        "--noconfirm",
    ]
    
    try:
        result = subprocess.run(cmd, cwd=APP_DIR, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:")
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)
    
    # Check if app bundle was created
    app_bundle = DIST_DIR / "Audiolab.app"
    if app_bundle.exists():
        print(f"\n✓ App bundle created: {app_bundle}")
        
        # Create DMG if hdiutil is available
        try:
            dmg_path = DIST_DIR / "Audiolab.dmg"
            if dmg_path.exists():
                dmg_path.unlink()
            
            subprocess.run([
                "hdiutil", "create", "-volname", "Audiolab",
                "-srcfolder", str(app_bundle),
                "-ov", "-format", "UDZO",
                str(dmg_path)
            ], check=True, capture_output=True)
            
            if dmg_path.exists():
                print(f"✓ DMG created: {dmg_path}")
        except Exception as e:
            print(f"⚠ Warning: DMG creation failed: {e}")
        
        print("\n" + "=" * 60)
        print("Build completed successfully!")
        print("=" * 60)
        print(f"App bundle: {app_bundle}")
        if (DIST_DIR / "Audiolab.dmg").exists():
            print(f"DMG file: {DIST_DIR / 'Audiolab.dmg'}")
        print("\nTo test the app, double-click the .app bundle or .dmg file.")
        return app_bundle
    else:
        print(f"❌ App bundle not found: {app_bundle}")
        print("Contents of dist/:")
        if DIST_DIR.exists():
            for item in DIST_DIR.iterdir():
                print(f"  {item}")
        sys.exit(1)

if __name__ == "__main__":
    main()

