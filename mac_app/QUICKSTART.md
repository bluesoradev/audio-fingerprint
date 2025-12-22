# Quick Start Guide

## Prerequisites

1. **Python 3.8+** installed on your Mac
2. **Xcode Command Line Tools** (for building):
   ```bash
   xcode-select --install
   ```
3. **VPS Server** running at `78.46.37.169:8080`

## Step 1: Install Dependencies

```bash
cd mac_app
pip install -r requirements.txt
```

## Step 2: Test Connection (Optional)

Test that you can connect to the VPS:
```bash
python test_connection.py
```

## Step 3: Run in Development Mode

Run the app directly:
```bash
python main.py
```

The app will:
- Copy UI files from `../ui/`
- Modify JavaScript to point to VPS
- Start a local web server
- Open a native macOS window

## Step 4: Build the App Bundle

Create a distributable `.app` and `.dmg`:
```bash
python build_app.py
```

This will:
1. Install PyInstaller (if needed)
2. Copy and modify UI files
3. Build `Audiolab.app` in `dist/` directory
4. Create `Audiolab.dmg` for distribution

## Step 5: Distribute

After building:
- **For testing**: Double-click `dist/Audiolab.app`
- **For distribution**: Share `dist/Audiolab.dmg`

Users can:
1. Open the `.dmg` file
2. Drag `Audiolab.app` to Applications
3. Launch from Applications folder

## Troubleshooting

### "Module not found" errors
```bash
pip install --upgrade -r requirements.txt
```

### Build fails
- Make sure Xcode Command Line Tools are installed
- Check that `ui/templates` and `ui/static` directories exist

### App won't connect to VPS
- Verify VPS is running: `curl http://78.46.37.169:8080/api/status`
- Check firewall settings
- Verify IP address in `main.py`

### Port already in use
If port 8765 is busy, change `LOCAL_PORT` in `main.py`

## Customization

### Change VPS Server

Edit `main.py`:
```python
VPS_HOST = "your-server-ip"
VPS_PORT = "your-port"
```

Then rebuild the app.

