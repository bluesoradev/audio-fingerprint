#!/usr/bin/env python3
"""
Build script to create macOS .app bundle and .dmg file
"""

import subprocess
import sys
import shutil
import os
import importlib
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
    """Build the .app bundle using PyInstaller spec file (following audio-ai-mac methodology)"""
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
    
    # Use PyInstaller spec file (following the working audio-ai-mac approach)
    spec_file = APP_DIR / "Audiolab.spec"
    if not spec_file.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_file}")
    
    print(f"Using spec file: {spec_file}")
    
    # Run PyInstaller with spec file
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--clean",
        "--noconfirm",
    ]
    
    subprocess.run(cmd, check=True, cwd=APP_DIR)
    
    # PyInstaller with spec file creates the .app bundle directly
    app_bundle = DIST_DIR / "Audiolab.app"
    
    if app_bundle.exists():
        print(f"✓ App bundle created: {app_bundle}")
        return app_bundle
    else:
        # Create .app bundle structure - preserve PyInstaller's internal structure
        print("Creating .app bundle structure...")
        # PyInstaller creates a directory with the executable, not a .app bundle
        app_dir = DIST_DIR / "Audiolab"
        if not app_dir.exists():
            raise FileNotFoundError(f"PyInstaller output directory not found: {app_dir}")
        
        if app_bundle.exists():
            shutil.rmtree(app_bundle)
        app_bundle.mkdir()
        contents_dir = app_bundle / "Contents"
        contents_dir.mkdir()
        macos_dir = contents_dir / "MacOS"
        macos_dir.mkdir()
        resources_dir = contents_dir / "Resources"
        resources_dir.mkdir()
        frameworks_dir = contents_dir / "Frameworks"
        frameworks_dir.mkdir()
        
        # Move executable to MacOS
        executable = app_dir / "Audiolab"
        if executable.exists():
            shutil.copy2(executable, macos_dir / "Audiolab")
            os.chmod(macos_dir / "Audiolab", 0o755)
        
        # Move all files/directories from app_dir to MacOS
        # PyInstaller expects everything in the same directory as the executable
        for item in app_dir.iterdir():
            if item.name != "Audiolab":  # Don't move the executable again
                dest = macos_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
        
        # Create Info.plist
        info_plist = contents_dir / "Info.plist"
        info_plist.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Audiolab</string>
    <key>CFBundleIdentifier</key>
    <string>com.audiolab.desktop</string>
    <key>CFBundleName</key>
    <string>Audiolab</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>""")
        
        # PyInstaller expects Python standard library in Frameworks directory
        # Copy all Python-related files from _internal to Frameworks
        internal_dir = macos_dir / "_internal"
        frameworks_dir = contents_dir / "Frameworks"
        frameworks_dir.mkdir(exist_ok=True)
        
        # Copy Python.framework if it exists
        python_framework_internal = internal_dir / "Python.framework"
        if python_framework_internal.exists():
            python_framework_frameworks = frameworks_dir / "Python.framework"
            if not python_framework_frameworks.exists():
                shutil.copytree(python_framework_internal, python_framework_frameworks)
                print("✓ Copied Python.framework to Frameworks")
            # Also create Python symlink for compatibility
            python_frameworks = frameworks_dir / "Python"
            if not python_frameworks.exists():
                os.symlink("Python.framework/Versions/Current/Python", str(python_frameworks))
                print("✓ Created Python symlink")
        
        # Copy base_library.zip and python3.11 directory (standard library)
        base_library = internal_dir / "base_library.zip"
        if base_library.exists():
            shutil.copy2(base_library, frameworks_dir / "base_library.zip")
            print("✓ Copied base_library.zip")
        
        python_lib_dir = internal_dir / "python3.11"
        if python_lib_dir.exists():
            python_lib_frameworks = frameworks_dir / "python3.11"
            if not python_lib_frameworks.exists():
                shutil.copytree(python_lib_dir, python_lib_frameworks)
                print("✓ Copied python3.11 standard library")
        
        # Copy lib-dynload if it exists separately
        lib_dynload = internal_dir / "lib-dynload"
        if lib_dynload.exists():
            lib_dynload_frameworks = frameworks_dir / "lib-dynload"
            if lib_dynload_frameworks.exists():
                shutil.rmtree(lib_dynload_frameworks)
            shutil.copytree(lib_dynload, lib_dynload_frameworks)
            print("✓ Copied lib-dynload")
        
        # Copy SSL and crypto libraries to Frameworks (needed by ssl module)
        for lib_name in ['libssl.3.dylib', 'libcrypto.3.dylib']:
            lib_file = internal_dir / lib_name
            if lib_file.exists():
                lib_dest = frameworks_dir / lib_name
                if not lib_dest.exists():
                    shutil.copy2(lib_file, lib_dest)
                    print(f"✓ Copied {lib_name}")
        
        # Also copy to python3.11/lib-dynload for direct access
        python_lib_dynload = frameworks_dir / "python3.11" / "lib-dynload"
        if python_lib_dynload.exists():
            for lib_name in ['libssl.3.dylib', 'libcrypto.3.dylib']:
                lib_file = internal_dir / lib_name
                if lib_file.exists():
                    lib_dest = python_lib_dynload.parent.parent / lib_name
                    if not lib_dest.exists():
                        shutil.copy2(lib_file, lib_dest)
        
        # Manually ensure webview is included if missing
        # Check if webview exists in _internal, if not copy it
        webview_internal = internal_dir / "webview"
        # Also check in site-packages subdirectory
        site_packages_dirs = list(internal_dir.glob("*site-packages*"))
        webview_found = webview_internal.exists()
        if not webview_found and site_packages_dirs:
            for sp_dir in site_packages_dirs:
                if (sp_dir / "webview").exists():
                    webview_found = True
                    break
        
        if not webview_found:
            # Try to find and copy webview from system site-packages
            try:
                import webview
                webview_path = os.path.dirname(webview.__file__)
                if os.path.exists(webview_path):
                    # Find or create site-packages directory in _internal
                    site_packages = None
                    for sp_dir in site_packages_dirs:
                        if sp_dir.is_dir():
                            site_packages = sp_dir
                            break
                    if not site_packages:
                        # Create site-packages directory
                        site_packages = internal_dir / "site-packages"
                        site_packages.mkdir(exist_ok=True)
                    
                    # Copy webview package to site-packages
                    webview_dest = site_packages / "webview"
                    if not webview_dest.exists():
                        shutil.copytree(webview_path, webview_dest)
                        print("✓ Manually copied webview package to site-packages")
                    
                    # Also copy webview dependencies (proxy_tools, bottle, etc.)
                    try:
                        import proxy_tools
                        proxy_tools_path = os.path.dirname(proxy_tools.__file__)
                        proxy_tools_dest = site_packages / "proxy_tools"
                        if not proxy_tools_dest.exists() and os.path.exists(proxy_tools_path):
                            shutil.copytree(proxy_tools_path, proxy_tools_dest)
                            print("✓ Copied proxy_tools dependency")
                    except:
                        pass
                    
                    try:
                        import bottle
                        bottle_file = bottle.__file__
                        if os.path.exists(bottle_file):
                            if os.path.isfile(bottle_file):
                                # Single file module
                                bottle_dest = site_packages / "bottle.py"
                                if not bottle_dest.exists():
                                    shutil.copy2(bottle_file, bottle_dest)
                                    print("✓ Copied bottle dependency")
                            else:
                                # Package directory
                                bottle_path = os.path.dirname(bottle_file)
                                bottle_dest = site_packages / "bottle"
                                if bottle_dest.exists():
                                    shutil.rmtree(bottle_dest)
                                if os.path.exists(bottle_path):
                                    shutil.copytree(bottle_path, bottle_dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                                    print("✓ Copied bottle dependency")
                    except Exception as e:
                        print(f"⚠ Warning: Could not copy bottle: {e}")
                    
                    try:
                        import typing_extensions
                        typing_ext_file = typing_extensions.__file__
                        if os.path.exists(typing_ext_file):
                            if os.path.isfile(typing_ext_file):
                                # Single file module - copy and patch it
                                typing_ext_dest = site_packages / "typing_extensions.py"
                                shutil.copy2(typing_ext_file, typing_ext_dest)
                                
                                # Patch typing_extensions to handle missing Concatenate
                                # Read the file and fix the problematic line
                                with open(typing_ext_dest, 'r') as f:
                                    lines = f.readlines()
                                
                                # Find and replace the problematic line
                                patched = False
                                for i, line in enumerate(lines):
                                    if 'Concatenate = typing.Concatenate' in line and not patched:
                                        # Get indentation
                                        indent = len(line) - len(line.lstrip())
                                        indent_str = ' ' * indent
                                        
                                        # Replace with try/except block
                                        new_lines = [
                                            indent_str + 'try:\n',
                                            indent_str + '    Concatenate = typing.Concatenate\n',
                                            indent_str + 'except AttributeError:\n',
                                            indent_str + '    # Concatenate not available in this Python version\n',
                                            indent_str + '    # Create a subscriptable type alias\n',
                                            indent_str + '    from typing import Generic, TypeVar\n',
                                            indent_str + '    _T = TypeVar("_T")\n',
                                            indent_str + '    class Concatenate(Generic[_T]):\n',
                                            indent_str + '        def __class_getitem__(cls, item):\n',
                                            indent_str + '            return cls\n',
                                            indent_str + '        pass\n'
                                        ]
                                        lines[i:i+1] = new_lines
                                        patched = True
                                        break
                                
                                if patched:
                                    with open(typing_ext_dest, 'w') as f:
                                        f.writelines(lines)
                                    print("  Patched typing_extensions for Concatenate compatibility")
                                
                                print("✓ Copied and patched typing_extensions dependency")
                            else:
                                # Package directory
                                typing_ext_path = os.path.dirname(typing_ext_file)
                                typing_ext_dest = site_packages / "typing_extensions"
                                if typing_ext_dest.exists():
                                    shutil.rmtree(typing_ext_dest)
                                shutil.copytree(typing_ext_path, typing_ext_dest)
                                print("✓ Copied typing_extensions dependency")
                    except Exception as e:
                                    print(f"⚠ Warning: Could not copy typing_extensions: {e}")
                    
                    # Create a minimal objc package that uses system objc but bundled _objc.so
                    # This allows system objc Python code to work while using bundled .so file
                    try:
                        import objc
                        objc_path = os.path.dirname(objc.__file__)
                        _objc_so = os.path.join(objc_path, '_objc.cpython-39-darwin.so')
                        if os.path.exists(_objc_so):
                            # Create objc directory in site-packages
                            objc_dest_dir = site_packages / "objc"
                            objc_dest_dir.mkdir(exist_ok=True)
                            
                            # Copy _objc.so
                            objc_dest_so = objc_dest_dir / "_objc.cpython-39-darwin.so"
                            if not objc_dest_so.exists():
                                shutil.copy2(_objc_so, objc_dest_so)
                            
                            # Create __init__.py that imports from system objc but uses bundled _objc
                            objc_init = objc_dest_dir / "__init__.py"
                            if not objc_init.exists():
                                objc_init.write_text("""# Minimal objc package wrapper
# Import _objc from this directory (bundled .so file)
from . import _objc
# Import everything else from system objc
import sys
import os
_system_objc_path = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages/objc")
if _system_objc_path not in sys.path:
    sys.path.insert(0, _system_objc_path)
# Now import the rest from system objc
from objc import *
""")
                                print("✓ Created objc package wrapper with bundled _objc.so")
                    except Exception as e:
                        print(f"⚠ Warning: Could not set up objc package: {e}")
                    
                    # Remove other PyObjC packages - use system ones
                    pyobjc_modules = ['Foundation', 'AppKit', 'CoreFoundation']
                    removed_count = 0
                    for module_name in pyobjc_modules:
                        module_dest = site_packages / module_name
                        if module_dest.exists():
                            shutil.rmtree(module_dest)
                            removed_count += 1
                    if removed_count > 0:
                        print(f"✓ Removed {removed_count} bundled PyObjC modules (using system versions)")
                    
                    # Copy PyObjC modules for macOS Cocoa support (AppKit, Foundation, etc.)
                    pyobjc_modules = ['Foundation', 'AppKit', 'CoreFoundation', 'objc']
                    copied_pyobjc = []
                    for module_name in pyobjc_modules:
                        try:
                            module = importlib.import_module(module_name)
                            module_file = getattr(module, '__file__', None)
                            if module_file and os.path.exists(module_file):
                                module_path = os.path.dirname(module_file)
                                module_basename = os.path.basename(module_path)
                                module_dest = site_packages / module_basename
                                if not module_dest.exists() and os.path.exists(module_path):
                                    shutil.copytree(module_path, module_dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                                    copied_pyobjc.append(module_name)
                        except:
                            pass
                    if copied_pyobjc:
                        print(f"✓ Copied PyObjC modules: {', '.join(copied_pyobjc)}")
            except Exception as e:
                print(f"⚠ Warning: Could not copy webview manually: {e}")
        
        # Copy entire standard library from system Python
        # PyInstaller's base_library.zip is incomplete, so we need the full standard library
        python_lib_frameworks = frameworks_dir / "python3.11"
        if python_lib_frameworks.exists():
            try:
                import site
                # Find system Python's standard library directory
                stdlib_path = None
                for path in sys.path:
                    if 'lib/python' in path and 'site-packages' not in path:
                        if os.path.exists(path) and os.path.isdir(path):
                            stdlib_path = path
                            break
                
                if stdlib_path and os.path.exists(stdlib_path):
                    stdlib_dir = Path(stdlib_path)
                    copied_count = 0
                    # Copy all .py files and packages from standard library
                    for item in stdlib_dir.iterdir():
                        if item.name.startswith('.'):
                            continue
                        dest_item = python_lib_frameworks / item.name
                        if not dest_item.exists():
                            try:
                                if item.is_dir():
                                    # Copy directory (package)
                                    shutil.copytree(item, dest_item, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                                    copied_count += 1
                                elif item.suffix == '.py':
                                    # Copy .py file
                                    shutil.copy2(item, dest_item)
                                    copied_count += 1
                            except Exception:
                                pass
                if copied_count > 0:
                    print(f"✓ Copied {copied_count} standard library items")
                
                # Ensure typing module exists (needed by typing_extensions)
                # It should already be in python3.11 from the standard library copy above
                pass
            except Exception as e:
                print(f"⚠ Warning: Could not copy standard library: {e}")
        
        # Clean up old directory
        if app_dir.exists():
            shutil.rmtree(app_dir)
        print(f"✓ App bundle created: {app_bundle}")
        return app_bundle

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

