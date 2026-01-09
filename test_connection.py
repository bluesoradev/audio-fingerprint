#!/usr/bin/env python3
"""
Quick connection test script for fingerprint API.

Usage:
    python test_connection.py [api_url]
    
Default: http://localhost:8080
"""

import requests
import sys
import os

# Get API URL from command line or environment
if len(sys.argv) > 1:
    API_BASE_URL = sys.argv[1]
elif os.getenv("API_BASE_URL"):
    API_BASE_URL = os.getenv("API_BASE_URL")
else:
    API_BASE_URL = "http://localhost:8080"

STATUS_ENDPOINT = f"{API_BASE_URL}/api/query/status"

print("="*60)
print("Fingerprint API Connection Test")
print("="*60)
print(f"Testing: {API_BASE_URL}")
print()

try:
    print("Connecting to server...")
    response = requests.get(STATUS_ENDPOINT, timeout=10)
    
    if response.status_code == 200:
        print("✓ Connection successful!")
        print()
        
        status = response.json()
        print("Server Status:")
        print(f"  Index loaded: {status.get('index_loaded', False)}")
        print(f"  Model config loaded: {status.get('model_config_loaded', False)}")
        
        if status.get('index_metadata'):
            metadata = status['index_metadata']
            print(f"  Index dimension: {metadata.get('embedding_dim', 'N/A')}")
            print(f"  Index type: {metadata.get('index_type', 'N/A')}")
        
        if status.get('model_config'):
            model = status['model_config']
            print(f"  Model name: {model.get('model_name', 'N/A')}")
            print(f"  Sample rate: {model.get('sample_rate', 'N/A')}")
        
        if status.get('index_loaded') and status.get('model_config_loaded'):
            print()
            print("✓ Server is ready for API requests!")
            sys.exit(0)
        else:
            print()
            print("⚠ Server is running but not fully initialized")
            print("  Check server logs for loading errors")
            sys.exit(1)
    else:
        print(f"✗ Server returned error: {response.status_code}")
        try:
            error = response.json()
            print(f"  Error: {error}")
        except:
            print(f"  Response: {response.text}")
        sys.exit(1)
        
except requests.exceptions.ConnectionError:
    print("✗ Connection refused!")
    print()
    print("The server is not running or not accessible.")
    print()
    if "localhost" in API_BASE_URL or "127.0.0.1" in API_BASE_URL:
        print("For local testing:")
        print("  1. Start server: cd ui && python -m uvicorn app:app --host 0.0.0.0 --port 8080")
        print("  2. Wait for 'Application startup complete' message")
    else:
        print(f"For remote server ({API_BASE_URL}):")
        print("  1. Ensure server is running on the remote machine")
        print("  2. Check firewall allows port 8080")
        print("  3. Verify server is bound to 0.0.0.0 (not 127.0.0.1)")
        print("  4. Test from server itself: curl http://localhost:8080/api/query/status")
    sys.exit(1)
    
except requests.exceptions.Timeout:
    print("✗ Connection timeout!")
    print("  Server may be slow to respond or unreachable")
    sys.exit(1)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
