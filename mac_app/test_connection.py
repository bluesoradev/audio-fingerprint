#!/usr/bin/env python3
"""
Test script to verify VPS connection before building the app
"""

import requests
import sys
from main import VPS_HOST, VPS_PORT, VPS_API_BASE

def test_connection():
    """Test connection to VPS server"""
    print("=" * 60)
    print("Testing VPS Connection")
    print("=" * 60)
    print(f"VPS Host: {VPS_HOST}")
    print(f"VPS Port: {VPS_PORT}")
    print(f"API Base: {VPS_API_BASE}")
    print()
    
    try:
        # Test status endpoint
        print("Testing /api/status endpoint...")
        response = requests.get(f"{VPS_API_BASE}/status", timeout=5)
        
        if response.status_code == 200:
            print("✓ Connection successful!")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ Connection failed with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed: Could not reach server")
        print("  Make sure the VPS server is running and accessible")
        return False
    except requests.exceptions.Timeout:
        print("✗ Connection failed: Request timed out")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("Please install requests: pip install requests")
        sys.exit(1)
    
    success = test_connection()
    sys.exit(0 if success else 1)

