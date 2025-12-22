# Audiolab macOS Desktop App

This is a macOS desktop application that provides the same interface and functionality as the web version, but connects to a VPS server for processing.

## Features

- **Exact Web Design**: The app uses the same HTML/CSS/JS as the web version, ensuring pixel-perfect design matching
- **VPS Connection**: Connects to VPS server at `78.46.37.169:8080` for all API operations
- **Native macOS App**: Runs as a native macOS application with proper window management
- **Offline UI**: UI files are bundled with the app, only API calls go to the VPS

## Requirements

- macOS 10.13 or later
- Python 3.8 or later
- Internet connection (to connect to VPS)

## Setup

1. Install dependencies:
```bash
cd mac_app
pip install -r requirements.txt
```

2. Configure VPS connection (if needed):
   - Edit `main.py` and change `VPS_HOST` and `VPS_PORT` if your server uses different settings

## Running the App

### Development Mode

Run directly from source:
```bash
python main.py
```

### Building the App Bundle

Build a `.app` bundle:
```bash
python build_app.py
```

This will:
1. Install build dependencies (PyInstaller)
2. Copy and modify UI files
3. Create `Audiolab.app` in the `dist/` directory
4. Create `Audiolab.dmg` for distribution

### Distribution

After building, you'll have:
- `dist/Audiolab.app` - The macOS application bundle
- `dist/Audiolab.dmg` - Disk image for easy distribution

Users can:
1. Double-click the `.dmg` file
2. Drag `Audiolab.app` to their Applications folder
3. Launch the app from Applications

## Architecture

The app uses:
- **pywebview**: Creates a native macOS window that displays HTML content
- **Local HTTP Server**: Serves UI files (HTML/CSS/JS/images) locally
- **VPS API**: All API calls are routed to the VPS server at `78.46.37.169:8080`

## File Structure

```
mac_app/
├── main.py              # Main application entry point
├── build_app.py         # Build script for creating .app and .dmg
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates (copied from ui/templates)
├── static/              # Static files (copied from ui/static, with modified API URLs)
├── build/               # Build artifacts (created during build)
└── dist/                # Distribution files (.app and .dmg)
```

## Troubleshooting

### App won't connect to VPS

1. Check that the VPS server is running and accessible
2. Verify the IP address and port in `main.py`
3. Check firewall settings on your Mac
4. Test the connection: `curl http://78.46.37.169:8080/api/status`

### Build fails

1. Make sure you have Xcode Command Line Tools installed:
   ```bash
   xcode-select --install
   ```

2. Ensure PyInstaller is installed:
   ```bash
   pip install pyinstaller
   ```

3. Check that all UI files exist in `ui/templates` and `ui/static`

### App crashes on launch

1. Check console logs: `Console.app` → Look for Audiolab errors
2. Try running from terminal to see error messages:
   ```bash
   python main.py
   ```

## Customization

### Change VPS Server

Edit `main.py`:
```python
VPS_HOST = "your-server-ip"
VPS_PORT = "your-port"
```

### Add App Icon

1. Create an `.icns` file (use `iconutil` or online converters)
2. Update `build_app.py` to include the icon:
   ```python
   "--icon", "path/to/icon.icns",
   ```

## Notes

- The app requires an active internet connection to function
- All audio processing happens on the VPS server
- The app UI is served locally for fast, responsive interface
- API calls are made directly to the VPS server

