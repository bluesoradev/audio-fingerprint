# How to Test Audio After Transformation

After applying audio transformations, you can test whether the fingerprint can still identify the original audio. Here's how:

## 🎯 Quick Test (Recommended)

### Step-by-Step Guide:

1. **Apply a Transformation**
   - Go to **"🎵 Manipulate Audio"** section
   - Select an audio file
   - Apply any transform (speed, pitch, overlay, etc.)
   - Wait for the completion alert

2. **Test Fingerprint Match**
   - Scroll down to **"5. Test Fingerprint Robustness"** section
   - **Select Original Audio File**: Choose the source file you transformed
   - **Select Manipulated Audio File**: Choose the transformed output file
   - Click **"🔍 Test Fingerprint Match"** button

3. **View Results**
   The results will show:
   - **Match Status**: ✓ MATCHED or ✗ NOT MATCHED
   - **Similarity Score**: 0-100% (higher = better match)
   - **Rank**: Position in search results (1 = best match)
   - **Top Match**: ID of the best matching result
   - **Interpretation**: What the results mean

### Understanding Results:

- **MATCHED ✓**: The fingerprint successfully identified the manipulated audio as the original
  - Similarity > 70%: Strong match
  - Similarity 50-70%: Moderate match
  - Similarity < 50%: Weak match (may need investigation)

- **NOT MATCHED ✗**: The fingerprint could not match the manipulated audio
  - The transformation may have broken fingerprint identification
  - Try different transform parameters
  - Some transforms are inherently more challenging

## 📊 Test Different Transformations

Test how each transform affects fingerprint robustness:

1. **Speed Changes**: Test 0.8x, 1.0x, 1.2x, 1.5x speeds
2. **Pitch Shifts**: Test -6, -3, 0, +3, +6 semitones
3. **Overlay**: Test with different gain levels (-12dB to 0dB)
4. **Noise**: Test with different SNR levels (5dB to 40dB)
5. **Compression**: Test different bitrates (64k, 128k, 192k, 320k)
6. **Combined**: Test chains of multiple transforms

## 🔄 Testing Workflow

### Example Workflow:

```
1. Original File: "song.wav"
   ↓
2. Apply Transform: Speed 1.2x
   ↓
3. Output: "song_speed_1.2x.wav"
   ↓
4. Test:
   - Original: "song.wav"
   - Manipulated: "song_speed_1.2x.wav"
   ↓
5. Result: MATCHED ✓ (85% similarity)
   ✓ Fingerprint is robust to 1.2x speed change
```

## 📈 Full Experiment Testing

For comprehensive testing with metrics and reports:

1. Go to **"⚙️ Workflow"** section
2. Create or use existing manifest
3. Generate transforms (or use manually created ones)
4. Run full experiment
5. View detailed metrics in **"📈 Results"** section

This provides:
- Recall@K metrics
- Rank distribution
- Comprehensive reports (CSV, JSON, HTML)
- Failure case analysis

## 💡 Tips

1. **Start Simple**: Test one transform at a time first
2. **Use Incremental Testing**: Apply transform → Test → Apply next
3. **Document Results**: Note which transforms work well
4. **Compare Results**: Test the same transform with different parameters
5. **Check Thresholds**: Similarity > 70% is usually good for matching

## 🐛 Troubleshooting

### Test Returns Error:
- Check that both files exist
- Ensure files are valid audio format (WAV, MP3)
- Check server logs for detailed error messages

### Low Similarity Scores:
- Some transforms inherently reduce similarity
- Try adjusting transform parameters
- Check if original file has good quality

### Test Takes Long Time:
- First run loads the fingerprint model (may take 30-60 seconds)
- Subsequent tests are faster
- Large files take longer to process

## 📝 Example Test Cases

### Test Case 1: Speed Robustness
```
Original: "test_audio.wav"
Transform: Speed 1.1x
Expected: MATCHED (similarity > 80%)
```

### Test Case 2: Pitch Robustness  
```
Original: "test_audio.wav"
Transform: Pitch +2 semitones
Expected: MATCHED (similarity > 70%)
```

### Test Case 3: Compression Robustness
```
Original: "test_audio.wav"
Transform: MP3 @ 128k
Expected: MATCHED (similarity > 75%)
```

### Test Case 4: Combined Transform
```
Original: "test_audio.wav"
Transform: Speed 1.1x → Pitch +2 → MP3 192k
Expected: MATCHED (similarity > 65%)
```

## 🎓 Next Steps

After testing individual transforms:
1. Build a comprehensive test suite with multiple transforms
2. Run full experiments to get statistical metrics
3. Generate reports for analysis
4. Identify which transforms break fingerprint matching
5. Optimize fingerprint model for robustness
