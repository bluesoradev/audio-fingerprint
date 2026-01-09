#!/usr/bin/env python3
"""
Test script for /api/fingerprint/match endpoint.

Usage:
    python test_fingerprint_match_api.py [audio_file_path]
    
If no audio file is provided, it will look for test files in data/test_audio/
"""

import requests
import sys
import os
from pathlib import Path
import json

# Default configuration - can be overridden via environment variable
# Usage: set API_BASE_URL=http://148.251.88.48:8080
# Or: python test_fingerprint_match_api.py --url http://148.251.88.48:8080
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
ENDPOINT = f"{API_BASE_URL}/api/fingerprint/match"
STATUS_ENDPOINT = f"{API_BASE_URL}/api/query/status"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(message):
    """Print success message in green."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    """Print error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message):
    """Print info message in blue."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_warning(message):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def check_server_status():
    """Check if server is running and index is loaded."""
    print_info("Checking server status...")
    try:
        response = requests.get(STATUS_ENDPOINT, timeout=10)
        if response.status_code == 200:
            status = response.json()
            if status.get("index_loaded"):
                print_success("Server is running and index is loaded")
                if status.get("model_config_loaded"):
                    print_success("Model config is loaded")
                else:
                    print_warning("Model config is not loaded")
                return True
            else:
                print_error("Server is running but index is not loaded")
                print_info("Check server logs for index loading errors")
                return False
        else:
            print_error(f"Server returned status code: {response.status_code}")
            try:
                error_detail = response.json()
                print_error(f"Error detail: {error_detail}")
            except:
                print_error(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError as e:
        print_error("Cannot connect to server. Connection refused.")
        print()
        print_info("Possible causes:")
        print_info(f"  1. Server is not running at {API_BASE_URL}")
        print_info("  2. Firewall is blocking the connection")
        print_info("  3. Server is bound to wrong interface (should be 0.0.0.0)")
        print()
        if "148.251.88.48" in API_BASE_URL:
            print_info("For VPS deployment:")
            print_info("  - SSH/RDP to VPS and start server")
            print_info("  - Check Windows Firewall allows port 8080")
            print_info("  - Verify server command: python -m uvicorn app:app --host 0.0.0.0 --port 8080")
        else:
            print_info("For local testing:")
            print_info("  - Start server: cd ui && python -m uvicorn app:app --host 0.0.0.0 --port 8080")
        return False
    except requests.exceptions.Timeout:
        print_error("Connection timeout - server may be slow to respond")
        return False
    except Exception as e:
        print_error(f"Error checking server status: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fingerprint_match(file_path: Path, min_score: float = 0.5, max_matches: int = 10):
    """
    Test the fingerprint match endpoint.
    
    Args:
        file_path: Path to audio file to test
        min_score: Minimum match score threshold
        max_matches: Maximum number of matches to return
    """
    print_info(f"\nTesting fingerprint match with file: {file_path.name}")
    print_info(f"Parameters: min_score={min_score}, max_matches={max_matches}")
    
    if not file_path.exists():
        print_error(f"File not found: {file_path}")
        return False
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "audio/mpeg")}
            data = {
                "min_score": str(min_score),
                "max_matches": str(max_matches)
            }
            
            print_info("Sending request...")
            response = requests.post(ENDPOINT, files=files, data=data, timeout=60)
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print_success("Request successful!")
                print(f"\nResults:")
                print(f"  Total matches: {result.get('total_matches', 0)}")
                print(f"  Query time: {result.get('query_time_ms', 0)} ms")
                
                matches = result.get("matches", [])
                if matches:
                    print(f"\n  Matches:")
                    for i, match in enumerate(matches, 1):
                        print(f"    {i}. Track UUID: {match.get('track_uuid')}")
                        print(f"       Match Score: {match.get('match_score')}")
                else:
                    print_warning("  No matches found (may be below min_score threshold)")
                
                return True
            else:
                print_error(f"Request failed with status {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"  Error: {error_detail.get('detail', 'Unknown error')}")
                except:
                    print(f"  Response: {response.text}")
                return False
                
    except FileNotFoundError:
        print_error(f"File not found: {file_path}")
        return False
    except requests.exceptions.Timeout:
        print_error("Request timed out (60s). The file may be too large or processing is slow.")
        return False
    except Exception as e:
        print_error(f"Error during request: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_cases():
    """Test various error cases."""
    print_info("\n" + "="*60)
    print_info("Testing Error Cases")
    print_info("="*60)
    
    # Test 1: No file provided
    print_info("\nTest 1: No file provided")
    try:
        response = requests.post(ENDPOINT, data={"min_score": "0.5"}, timeout=5)
        # FastAPI returns 422 for validation errors (missing required field)
        if response.status_code in (400, 422):
            print_success(f"Correctly returned {response.status_code} for missing file")
        else:
            print_error(f"Expected 400 or 422, got {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")
    
    # Test 2: Invalid file format
    print_info("\nTest 2: Invalid file format")
    try:
        # Create a dummy text file
        dummy_file = Path("test_dummy.txt")
        dummy_file.write_text("This is not an audio file")
        
        with open(dummy_file, "rb") as f:
            files = {"file": ("test_dummy.txt", f, "text/plain")}
            response = requests.post(ENDPOINT, files=files, timeout=5)
            
        dummy_file.unlink()  # Clean up
        
        if response.status_code == 400:
            print_success("Correctly returned 400 for invalid file format")
        else:
            print_error(f"Expected 400, got {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")
    
    # Test 3: Invalid min_score
    print_info("\nTest 3: Invalid min_score (out of range)")
    try:
        # Create a dummy audio file (just for testing validation)
        dummy_audio = Path("test_dummy.mp3")
        dummy_audio.write_bytes(b"fake audio data")
        
        with open(dummy_audio, "rb") as f:
            files = {"file": ("test_dummy.mp3", f, "audio/mpeg")}
            data = {"min_score": "1.5"}  # Invalid: > 1.0
            response = requests.post(ENDPOINT, files=files, data=data, timeout=5)
            
        dummy_audio.unlink()  # Clean up
        
        if response.status_code == 400:
            print_success("Correctly returned 400 for invalid min_score")
        else:
            print_error(f"Expected 400, got {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")


def find_test_audio_files():
    """Find test audio files in common locations."""
    test_dirs = [
        Path("data/test_audio"),
        Path("data/originals"),
        Path("data/manipulated"),
    ]
    
    audio_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
    test_files = []
    
    for test_dir in test_dirs:
        if test_dir.exists():
            for file in test_dir.iterdir():
                if file.suffix.lower() in audio_extensions:
                    test_files.append(file)
    
    return test_files


def main():
    """Main test function."""
    global API_BASE_URL, ENDPOINT, STATUS_ENDPOINT
    
    # Check for URL override in command line (first arg starting with http)
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        API_BASE_URL = sys.argv[1]
        ENDPOINT = f"{API_BASE_URL}/api/fingerprint/match"
        STATUS_ENDPOINT = f"{API_BASE_URL}/api/query/status"
        audio_file_arg = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        audio_file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("="*60)
    print("Fingerprint Match API Test Script")
    print("="*60)
    print_info(f"Testing API at: {API_BASE_URL}")
    print()
    
    # Check server status first
    if not check_server_status():
        print_error("\nCannot proceed with tests. Server is not accessible.")
        print()
        print_info("Troubleshooting:")
        print_info("1. For local testing:")
        print_info("   Start server with: cd ui && python -m uvicorn app:app --host 0.0.0.0 --port 8080")
        print()
        print_info("2. For VPS testing (148.251.88.48):")
        print_info("   - Ensure server is running on VPS")
        print_info("   - Check firewall allows port 8080")
        print_info("   - Verify server is bound to 0.0.0.0 (not 127.0.0.1)")
        print()
        print_info("3. Change API URL:")
        print_info("   Set environment: set API_BASE_URL=http://148.251.88.48:8080")
        print_info("   Or use: python test_fingerprint_match_api.py http://148.251.88.48:8080 [audio_file]")
        sys.exit(1)
    
    # Get audio file from command line or find test files
    if audio_file_arg:
        audio_file = Path(audio_file_arg)
    else:
        print_info("\nNo audio file specified. Looking for test files...")
        test_files = find_test_audio_files()
        
        if not test_files:
            print_error("No test audio files found.")
            print_info("Please provide an audio file path as argument:")
            print_info("  python test_fingerprint_match_api.py path/to/audio.mp3")
            sys.exit(1)
        
        audio_file = test_files[0]
        print_info(f"Using test file: {audio_file}")
    
    # Run tests
    print("\n" + "="*60)
    print("Running Tests")
    print("="*60)
    
    # Test 1: Basic match with default parameters
    print_info("\n" + "-"*60)
    print_info("Test 1: Basic match (default parameters)")
    print_info("-"*60)
    success1 = test_fingerprint_match(audio_file, min_score=0.5, max_matches=10)
    
    # Test 2: Higher threshold
    print_info("\n" + "-"*60)
    print_info("Test 2: Higher threshold (min_score=0.8)")
    print_info("-"*60)
    success2 = test_fingerprint_match(audio_file, min_score=0.8, max_matches=10)
    
    # Test 3: Lower threshold, more matches
    print_info("\n" + "-"*60)
    print_info("Test 3: Lower threshold, more matches (min_score=0.3, max_matches=20)")
    print_info("-"*60)
    success3 = test_fingerprint_match(audio_file, min_score=0.3, max_matches=20)
    
    # Test error cases
    test_error_cases()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    if success1 or success2 or success3:
        print_success("At least one test passed!")
    else:
        print_error("All tests failed. Check server logs for details.")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
