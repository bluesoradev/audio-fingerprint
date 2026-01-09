"""Simple test to verify model is being passed correctly."""
import sys
import requests
from pathlib import Path

API_URL = "http://148.251.88.48:8080"

def test_api():
    """Test the fingerprint match API."""
    print("=" * 60)
    print("Testing Model Fix - Fingerprint Match API")
    print("=" * 60)
    
    # Check server status
    try:
        response = requests.get(f"{API_URL}/api/query/status", timeout=5)
        if response.status_code == 200:
            print("[OK] Server is running")
        else:
            print(f"[ERROR] Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Cannot connect to server: {e}")
        print("[INFO] Please restart the server with: python -m uvicorn ui.app:app --host 0.0.0.0 --port 8080")
        return False
    
    # Test with a file
    test_file = Path("data/originals/andygrvcia_onna_leash_Ebm_99.wav")
    if not test_file.exists():
        print(f"[ERROR] Test file not found: {test_file}")
        return False
    
    print(f"[INFO] Testing with file: {test_file.name}")
    print(f"[INFO] This file should match itself with high score (0.7-0.95+)")
    print()
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'audio/wav')}
            data = {'min_score': 0.3, 'max_matches': 10}
            
            response = requests.post(
                f"{API_URL}/api/fingerprint/match",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            matches = result.get('matches', [])
            query_time = result.get('query_time_ms', 0)
            
            print(f"[OK] Request successful (status 200)")
            print(f"[INFO] Query time: {query_time:.2f} ms")
            print(f"[INFO] Found {len(matches)} matches")
            print()
            
            if len(matches) > 0:
                print("Matches found:")
                for i, match in enumerate(matches[:5], 1):
                    track_uuid = match.get('track_uuid', 'unknown')
                    score = match.get('match_score', 0.0)
                    print(f"  {i}. Track: {track_uuid}, Score: {score:.4f}")
                
                # Check if it matched itself
                top_match = matches[0]
                top_score = top_match.get('match_score', 0.0)
                top_track = top_match.get('track_uuid', '')
                
                if 'andygrvcia_onna_leash_Ebm_99' in top_track and top_score > 0.7:
                    print()
                    print("[SUCCESS] Model fix is working! File matched itself with high score.")
                    print(f"         Score: {top_score:.4f} (expected: >0.7)")
                    return True
                elif top_score > 0.5:
                    print()
                    print("[PARTIAL] Matches found but score is lower than expected.")
                    print(f"         Top score: {top_score:.4f} (expected: >0.7)")
                    print("         This might indicate the model is working but needs tuning.")
                    return True
                else:
                    print()
                    print("[WARNING] Matches found but scores are very low.")
                    print(f"         Top score: {top_score:.4f} (expected: >0.7)")
                    print("         The model might not be working correctly.")
                    return False
            else:
                print()
                print("[ERROR] No matches found (even with min_score=0.3)")
                print("        This suggests the model is not being used correctly.")
                print("        Check server logs for 'Extracting embeddings using model: dict'")
                print("        It should say 'Extracting embeddings using model: EmbeddingGenerator'")
                return False
        else:
            print(f"[ERROR] Request failed with status {response.status_code}")
            print(f"        Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
