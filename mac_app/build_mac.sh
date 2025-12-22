#!/bin/bash
# Build script for macOS app bundle
# Based on the working audio-ai-mac project methodology

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "Building Audiolab macOS Desktop App"
echo "============================================================"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Ensure UI files are set up
echo "Setting up UI files..."
python3 -c "from main import setup_ui_files; setup_ui_files()" || echo "Warning: UI setup failed"

# Build using PyInstaller spec file
echo "Building with PyInstaller..."
python3 -m PyInstaller Audiolab.spec --clean --noconfirm

# Check if app bundle was created
if [ -d "dist/Audiolab.app" ]; then
    echo "✓ App bundle created: dist/Audiolab.app"
    
    # Create DMG if hdiutil is available
    if command -v hdiutil &> /dev/null; then
        echo "Creating DMG file..."
        DMG_PATH="dist/Audiolab.dmg"
        rm -f "$DMG_PATH"
        hdiutil create -volname "Audiolab" -srcfolder "dist/Audiolab.app" -ov -format UDZO "$DMG_PATH" || echo "Warning: DMG creation failed"
        if [ -f "$DMG_PATH" ]; then
            echo "✓ DMG created: $DMG_PATH"
        fi
    fi
    
    echo ""
    echo "============================================================"
    echo "Build completed successfully!"
    echo "============================================================"
    echo "App bundle: dist/Audiolab.app"
    if [ -f "dist/Audiolab.dmg" ]; then
        echo "DMG file: dist/Audiolab.dmg"
    fi
    echo ""
    echo "To test the app, double-click the .app bundle or .dmg file."
else
    echo "❌ App bundle not found after build!"
    echo "Contents of dist/:"
    ls -la dist/ || echo "dist/ directory doesn't exist"
    exit 1
fi

