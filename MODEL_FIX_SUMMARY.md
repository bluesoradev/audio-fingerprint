# Model Fix Summary

## Problem Identified
The `QueryService` was using `model_config.__dict__` to extract embeddings, but `ModelConfig` (a dataclass) doesn't contain the actual `EmbeddingGenerator` model object. This caused the system to fall back to librosa embeddings instead of using MERT, resulting in very low similarity scores (0.04 instead of 0.7-0.95+).

## Solution Implemented

### 1. Updated `infrastructure/dependency_container.py`
- Added `_model_dict` field to store the full model dict (includes EmbeddingGenerator)
- Modified `load_model_config()` to load both:
  - `_model_dict`: Full dict from `load_fingerprint_model()` (includes `"model": EmbeddingGenerator`)
  - `_model_config`: ModelConfig dataclass (for compatibility)
- Updated `get_query_service()` to pass `model_dict` to QueryService

### 2. Updated `services/query_service.py`
- Added `model_dict` parameter to `__init__()`
- Store `model_dict` as `self._model_dict`
- Modified `query_file()` to use `self._model_dict` instead of `model_config.__dict__` when extracting embeddings
- Added fallback to `model_config.__dict__` for compatibility

## Files Modified
1. `infrastructure/dependency_container.py`
2. `services/query_service.py`

## Testing Instructions

### Step 1: Restart the Server
The server must be restarted to pick up the code changes:

1. Stop the current server (Ctrl+C in the terminal where it's running)
2. Restart it:
   ```powershell
   cd D:\project\manipulate-audio
   .\venv\Scripts\Activate.ps1
   python -m uvicorn ui.app:app --host 0.0.0.0 --port 8080
   ```

### Step 2: Verify Server Logs
When the server starts, you should see:
```
INFO: ✓ Loaded fingerprint index from ...
INFO: ✓ Loaded model config from ...
INFO: ✓ Dependency container initialized successfully
```

### Step 3: Test the API
Run the test script:
```powershell
python test_model_fix.py
```

**Expected Results:**
- ✅ Server responds successfully
- ✅ Query completes in ~2-3 seconds
- ✅ **Finds matches** (should find at least 1 match)
- ✅ **High match score** (0.7-0.95+ for the same file)
- ✅ Logs show: `"Extracting embeddings using model: EmbeddingGenerator"` (NOT `"dict"`)

### Step 4: Verify in Server Logs
When you make a query, check the server logs. You should see:
```
INFO:fingerprint.embed:Extracting embeddings using model: EmbeddingGenerator, batch_support: True, batch_size: 256
```

**NOT:**
```
INFO:fingerprint.embed:Extracting embeddings using model: dict, batch_support: False, batch_size: 256
```

## What Changed
- **Before**: QueryService used `model_config.__dict__` → No EmbeddingGenerator → Fallback to librosa → Low scores (0.04)
- **After**: QueryService uses `self._model_dict` → Has EmbeddingGenerator → Uses MERT → High scores (0.7-0.95+)

## Verification
After restarting and testing, you should see:
1. ✅ `andygrvcia_onna_leash_Ebm_99.wav` matches itself with score > 0.7
2. ✅ Server logs show "EmbeddingGenerator" not "dict"
3. ✅ Query returns matches instead of 0 matches
