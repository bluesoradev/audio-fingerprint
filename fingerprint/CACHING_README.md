# Embedding Caching System

## Overview

The embedding caching system pre-generates and reuses embeddings for original audio files, significantly reducing processing time for Phase 1 and Phase 2 reports.

## How It Works

### Original Files (Cached)
- **First Run**: Embeddings are generated and cached to disk
- **Subsequent Runs**: Cached embeddings are loaded (80-90% faster)
- **New Files**: Only new files are processed, embeddings are cached for future use

### Transformed Files (Regenerated)
- Transformed files are generated dynamically each run
- Embeddings are regenerated each time (they're new files)
- This is correct behavior - transformed files change each run

## Cache Location

```
data/cache/original_embeddings/
├── cache_manifest.json          # Cache metadata
├── {file_id}_{hash}_{model_hash}/
│   ├── seg_0000.npy            # Segment embeddings
│   ├── seg_0001.npy
│   └── segments.json           # Segment metadata
└── ...
```

## Usage

### Automatic Caching (Default Behavior)

The caching system is **automatically enabled** when running experiments:

```bash
python run_experiment.py --config config/test_matrix_phase1.yaml
```

**First Run:**
- Generates embeddings for all original files
- Caches them to `data/cache/original_embeddings/`
- Builds FAISS index

**Second Run (same files):**
- Loads cached embeddings (much faster!)
- Rebuilds index using cached embeddings
- Generates transformed files and queries

**New Run (new files added):**
- Loads cached embeddings for existing files
- Generates embeddings for NEW files only
- Caches new embeddings
- Rebuilds index with all files

### Incremental Index Updates

When you add new original files, you can update the index incrementally:

```bash
python scripts/update_index_incremental.py \
    --new-files data/manifests/new_files_manifest.csv \
    --existing-index indexes/faiss_index.bin \
    --output-index indexes/faiss_index_updated.bin \
    --fingerprint-config config/fingerprint_v1.yaml
```

## Cache Management

### Check Cache Statistics

```python
from fingerprint.original_embeddings_cache import OriginalEmbeddingsCache

cache = OriginalEmbeddingsCache()
stats = cache.get_cache_stats()
print(f"Cached files: {stats['num_cached_files']}")
print(f"Cache size: {stats['total_cache_size_mb']:.2f} MB")
```

### Clear Cache

```python
from fingerprint.original_embeddings_cache import OriginalEmbeddingsCache

cache = OriginalEmbeddingsCache()

# Clear specific file
cache.clear(file_id="track1")

# Clear all cache
cache.clear()
```

## Performance Benefits

| Scenario | Without Cache | With Cache | Speedup |
|----------|--------------|------------|---------|
| First Run | 100% time | 100% time | 1x |
| Second Run (same files) | 100% time | 10-20% time | 5-10x |
| New Run (1 new file, 9 existing) | 100% time | 20-30% time | 3-5x |

## Cache Invalidation

The cache is automatically invalidated when:
- File content changes (file hash changes)
- Model configuration changes (model hash changes)
- Cache files are manually deleted

## Best Practices

1. **Keep cache directory**: Don't delete `data/cache/original_embeddings/` between runs
2. **Version control**: Don't commit cache directory (add to `.gitignore`)
3. **Disk space**: Cache uses ~1-5 MB per audio file (depends on duration)
4. **Backup**: Cache can be backed up and restored for faster setup on new machines

## Troubleshooting

### Cache Not Working
- Check that `data/cache/original_embeddings/` directory exists
- Verify file paths in manifest match actual files
- Check logs for cache hit/miss messages

### Stale Cache
- Clear cache: `cache.clear()`
- Or delete `data/cache/original_embeddings/` directory

### Cache Too Large
- Clear old entries: `cache.clear(file_id="old_file")`
- Or manually delete unused cache directories

