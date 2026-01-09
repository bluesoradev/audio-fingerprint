# Deployment Guide - Fingerprint Match API

## Quick Start

### Local Testing

1. **Start the server locally:**
   ```bash
   cd ui
   python -m uvicorn app:app --host 0.0.0.0 --port 8080
   ```

2. **Test the connection:**
   ```bash
   python test_connection.py
   ```

3. **Test the API:**
   ```bash
   python test_fingerprint_match_api.py path/to/audio.mp3
   ```

### VPS Deployment (148.251.88.48)

#### Step 1: Transfer Files to VPS

**Option A: Using RDP**
- Connect via Remote Desktop to `148.251.88.48`
- Copy project folder to `C:\project\manipulate-audio`

**Option B: Using SCP (if SSH is enabled)**
```bash
scp -r D:\project\manipulate-audio administrator@148.251.88.48:C:\project\
```

#### Step 2: Setup on VPS

**On the VPS, open PowerShell and run:**
```powershell
# Navigate to project
cd C:\project\manipulate-audio

# Activate virtual environment (or create one)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Verify index exists
Test-Path indexes\faiss_index.bin
Test-Path config\fingerprint_v1.yaml
```

#### Step 3: Configure Firewall

**Run as Administrator on VPS:**
```powershell
# Check if rule exists
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*8080*"}

# Create firewall rule (if needed)
New-NetFirewallRule -DisplayName "Fingerprint API Port 8080" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

#### Step 4: Start Server

**On VPS:**
```powershell
cd C:\project\manipulate-audio\ui
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
✓ Loaded fingerprint index from ...
✓ Loaded model config from ...
✓ Dependency container initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

#### Step 5: Test from Local Machine

**From your local machine:**
```bash
# Test connection
python test_connection.py http://148.251.88.48:8080

# Test API
python test_fingerprint_match_api.py http://148.251.88.48:8080 path/to/audio.mp3
```

## Troubleshooting

### Connection Refused

**Symptoms:** `ConnectionRefusedError` or `No connection could be made`

**Solutions:**
1. **Check if server is running on VPS:**
   ```powershell
   # On VPS
   netstat -an | findstr 8080
   ```
   Should show `0.0.0.0:8080` or `*:8080` listening

2. **Check firewall:**
   ```powershell
   # On VPS (as Administrator)
   Get-NetFirewallRule | Where-Object {$_.LocalPort -eq 8080}
   ```

3. **Verify server is bound to 0.0.0.0:**
   - Server command must include `--host 0.0.0.0`
   - NOT `--host 127.0.0.1` or `--host localhost`

4. **Test from VPS itself:**
   ```powershell
   # On VPS
   curl http://localhost:8080/api/query/status
   ```

### Index Not Loaded

**Symptoms:** `Index must be loaded before creating QueryService`

**Solutions:**
1. **Check index file exists:**
   ```powershell
   Test-Path C:\project\manipulate-audio\indexes\faiss_index.bin
   ```

2. **Check server logs for loading errors**

3. **Verify paths in startup event handler** (should be relative to PROJECT_ROOT)

### Model Config Not Loaded

**Symptoms:** `Model config must be loaded before creating QueryService`

**Solutions:**
1. **Check config file exists:**
   ```powershell
   Test-Path C:\project\manipulate-audio\config\fingerprint_v1.yaml
   ```

2. **Check server logs for config loading errors**

## Running as Windows Service (Optional)

For production, you may want to run the server as a Windows service:

1. **Install NSSM (Non-Sucking Service Manager):**
   - Download from: https://nssm.cc/download
   - Extract to `C:\nssm`

2. **Create service:**
   ```powershell
   # As Administrator
   C:\nssm\win64\nssm.exe install FingerprintAPI
   ```
   - **Path:** `C:\Python311\python.exe` (or your Python path)
   - **Startup directory:** `C:\project\manipulate-audio\ui`
   - **Arguments:** `-m uvicorn app:app --host 0.0.0.0 --port 8080`

3. **Start service:**
   ```powershell
   C:\nssm\win64\nssm.exe start FingerprintAPI
   ```

## API Endpoint Details

### Endpoint: `POST /api/fingerprint/match`

**Request:**
- `file`: Audio file (multipart/form-data)
- `min_score`: Optional, minimum match score (0.0-1.0, default: 0.5)
- `max_matches`: Optional, max matches to return (default: 10)

**Response:**
```json
{
  "matches": [
    {"track_uuid": "track_123", "match_score": 0.95},
    ...
  ],
  "total_matches": 5,
  "query_time_ms": 123.45
}
```

## Testing Commands

### Quick Connection Test
```bash
python test_connection.py http://148.251.88.48:8080
```

### Full API Test
```bash
# Local
python test_fingerprint_match_api.py path/to/audio.mp3

# VPS
python test_fingerprint_match_api.py http://148.251.88.48:8080 path/to/audio.mp3

# Using environment variable
set API_BASE_URL=http://148.251.88.48:8080
python test_fingerprint_match_api.py path/to/audio.mp3
```

### Using curl
```bash
curl -X POST "http://148.251.88.48:8080/api/fingerprint/match" \
  -F "file=@audio.mp3" \
  -F "min_score=0.5" \
  -F "max_matches=10"
```

## Checklist

### Before Deployment
- [ ] Code is tested locally
- [ ] Index file exists (`indexes/faiss_index.bin`)
- [ ] Config file exists (`config/fingerprint_v1.yaml`)
- [ ] All dependencies installed

### On VPS
- [ ] Files transferred to VPS
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] Firewall rule created for port 8080
- [ ] Server starts without errors
- [ ] Index loads successfully (check startup logs)
- [ ] Model config loads successfully

### After Deployment
- [ ] Can access `http://148.251.88.48:8080/api/query/status` from local machine
- [ ] Connection test passes: `python test_connection.py http://148.251.88.48:8080`
- [ ] API test passes: `python test_fingerprint_match_api.py http://148.251.88.48:8080 audio.mp3`
- [ ] Response format matches expected structure
