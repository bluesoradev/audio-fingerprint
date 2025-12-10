# Audio Manipulation UI Guide

The web interface now includes a comprehensive **Audio Manipulation** section that allows you to apply all transformations directly through the UI.

## 🎵 Accessing the Feature

1. Start the web UI: `cd ui && uvicorn app:app --port 8080`
2. Navigate to **"🎵 Manipulate Audio"** in the sidebar
3. All manipulation features are now accessible!

## Available Transformations

### 1. ⚡ Speed Change
- **Speed up**: Set ratio > 1.0 (e.g., 1.1x, 1.2x = 10-20% faster)
- **Slow down**: Set ratio < 1.0 (e.g., 0.8x, 0.9x = 20-10% slower)
- **Preserve Pitch**: Checkbox to maintain pitch while changing speed
- **Apply**: Click "Apply Speed Change" button

### 2. 🎹 Pitch Shift
- **Pitch up**: Positive semitones (e.g., +1, +3, +6)
- **Pitch down**: Negative semitones (e.g., -1, -3, -6)
- **Range**: -12 to +12 semitones
- **Apply**: Click "Apply Pitch Shift" button

### 3. 🎤 Add Vocals/Overlay
- **Upload overlay file**: Optional - upload a vocal/audio file to overlay
- **Auto-generate**: Leave empty to generate test overlay
- **Gain control**: Adjust overlay volume in dB (-20 to 0)
- **Apply**: Click "Apply Overlay" button

### 4. 🔊 Add Noise
- **SNR control**: Signal-to-noise ratio (5-40 dB)
- **Noise type**: White noise or Pink noise
- **Apply**: Click "Add Noise" button

### 5. 💾 Re-encode
- **Codec**: MP3 or AAC
- **Bitrate**: 320k, 192k, 128k, or 64k
- **Apply**: Click "Re-encode" button

### 6. ✂️ Slice/Chop
- **Remove from start**: Seconds to remove from beginning
- **Remove from end**: Seconds to remove from end
- **Apply**: Click "Apply Slice" button

## 🔗 Combining Transforms (Chain)

You can combine multiple transforms:

1. Configure each transform (speed, pitch, overlay, etc.)
2. Click "Add [Transform] to Chain" to add to chain
3. Repeat for multiple transforms
4. Click "Apply Chain" to apply all transforms in sequence

**Example Chain:**
- Add Speed (1.1x) → Add Pitch (+2 semitones) → Add Overlay → Apply Chain

## 🧪 Testing Fingerprint Robustness

After applying transforms, test if the fingerprint can still identify the original:

1. Select **Original Audio File** (the source file)
2. Select **Manipulated Audio File** (the transformed version)
3. Click **"🔍 Test Fingerprint Match"**
4. View results:
   - **Match Status**: ✓ MATCHED or ✗ NOT MATCHED
   - **Similarity Score**: 0.0 to 1.0 (higher = better match)
   - **Rank**: Position in search results (1 = best match)
   - **Top Match**: ID of best matching result

## Workflow Example

### Example 1: Speed Up Audio
1. Select audio file from dropdown
2. Set Speed Ratio to `1.2` (20% faster)
3. Check "Preserve Pitch" if desired
4. Click "Apply Speed Change"
5. Wait for completion alert
6. File saved to `data/manipulated/`

### Example 2: Pitch Down + Add Vocals
1. Select audio file
2. Set Pitch Semitones to `-3`
3. Click "Apply Pitch Shift"
4. Wait for completion
5. Select the pitch-shifted file
6. Upload vocal file (or leave empty)
7. Set Gain to `-6` dB
8. Click "Apply Overlay"
9. Test fingerprint: Select original → Select final manipulated file → Test

### Example 3: Combined Transform Chain
1. Select audio file
2. Set Speed to `1.1x` → Click "Add Speed to Chain"
3. Set Pitch to `+2` → Click "Add Pitch to Chain"
4. Set Overlay Gain to `-6` → Click "Add Overlay to Chain"
5. Click "Apply Chain" to apply all at once
6. Test fingerprint robustness

## Output Files

All manipulated files are saved to:
- **Default**: `data/manipulated/`
- **Custom**: Set in "Output Directory" field
- **Naming**: Auto-generated based on transform type and parameters
- **Custom name**: Optional - set in "Output Filename" field

## File Preview

- Selected audio files show a preview player
- Listen to original before applying transforms
- Compare original vs manipulated after transformation

## Integration with Full Workflow

The manipulated files can be used in:
- **Full Experiment**: Add to manifest and run complete robustness test
- **Batch Processing**: Use in transform generation workflow
- **Individual Testing**: Test fingerprint matching directly

## Tips

1. **Start Simple**: Test one transform at a time first
2. **Test Incrementally**: Apply transform → Test fingerprint → Apply next
3. **Use Chains**: For complex combinations, use the chain feature
4. **Check Results**: Always test fingerprint after manipulation
5. **Save Settings**: Note which transforms work well for your use case

## API Endpoints

All manipulations are available via API:
- `POST /api/manipulate/speed`
- `POST /api/manipulate/pitch`
- `POST /api/manipulate/overlay`
- `POST /api/manipulate/noise`
- `POST /api/manipulate/encode`
- `POST /api/manipulate/chop`
- `POST /api/manipulate/chain`
- `POST /api/test/fingerprint`

## Next Steps

After manipulation:
1. Review manipulated files in "Files" section
2. Test fingerprint matching individually
3. Add to manifest for batch testing
4. Run full experiment to get comprehensive metrics
5. View results in "Results" section
