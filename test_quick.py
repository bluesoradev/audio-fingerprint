"""Quick test script to verify the robustness lab pipeline works."""
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported."""
    logger.info("Testing imports...")
    try:
        import numpy
        import pandas
        import librosa
        import soundfile
        import faiss
        logger.info("✓ Core libraries imported")
        
        from transforms import pitch_shift, time_stretch
        from fingerprint import load_fingerprint_model
        from evaluation import compute_recall_at_k
        logger.info("✓ Project modules imported")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_audio_creation():
    """Test creating test audio files."""
    logger.info("\nTesting audio file creation...")
    try:
        from scripts.create_test_audio import create_test_audio
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.wav"
            create_test_audio(test_file, duration_sec=1.0)
            
            if test_file.exists():
                logger.info(f"✓ Created test audio: {test_file.stat().st_size} bytes")
                return True
            else:
                logger.error("✗ Test audio file not created")
                return False
    except Exception as e:
        logger.error(f"✗ Audio creation failed: {e}")
        return False


def test_transforms():
    """Test basic transform functions."""
    logger.info("\nTesting transforms...")
    try:
        from transforms.pitch import pitch_shift
        from transforms.speed import time_stretch
        import tempfile
        import soundfile as sf
        import numpy as np
        
        # Create a simple test audio
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            input_file = tmpdir / "input.wav"
            
            # Create 1 second of audio
            y = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 44100))
            sf.write(str(input_file), y, 44100)
            
            # Test pitch shift
            output_file = tmpdir / "output.wav"
            pitch_shift(input_file, semitones=1, out_path=output_file)
            
            if output_file.exists():
                logger.info("✓ Pitch shift transform works")
            else:
                logger.error("✗ Pitch shift failed")
                return False
            
            # Test time stretch
            output_file2 = tmpdir / "output2.wav"
            time_stretch(input_file, rate=1.1, out_path=output_file2)
            
            if output_file2.exists():
                logger.info("✓ Time stretch transform works")
            else:
                logger.error("✗ Time stretch failed")
                return False
            
            return True
    except Exception as e:
        logger.error(f"✗ Transform test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_segmentation():
    """Test audio segmentation."""
    logger.info("\nTesting segmentation...")
    try:
        from fingerprint.embed import segment_audio
        import tempfile
        import soundfile as sf
        import numpy as np
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.wav"
            
            # Create 5 seconds of audio
            duration = 5.0
            y = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(44100 * duration)))
            sf.write(str(test_file), y, 44100)
            
            segments = segment_audio(test_file, segment_length=0.5, sample_rate=44100)
            
            if len(segments) > 0:
                logger.info(f"✓ Segmentation works: {len(segments)} segments created")
                return True
            else:
                logger.error("✗ No segments created")
                return False
    except Exception as e:
        logger.error(f"✗ Segmentation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """Test loading configuration files."""
    logger.info("\nTesting config loading...")
    try:
        import yaml
        import json
        
        # Test YAML configs
        config_files = [
            Path("config/fingerprint_v1.yaml"),
            Path("config/test_matrix.yaml"),
        ]
        
        for config_file in config_files:
            if not config_file.exists():
                logger.warning(f"⚠ Config file not found: {config_file}")
                continue
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✓ Loaded {config_file.name}")
        
        # Test JSON config
        json_config = Path("config/index_config.json")
        if json_config.exists():
            with open(json_config, 'r') as f:
                config = json.load(f)
            logger.info(f"✓ Loaded {json_config.name}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Config loading failed: {e}")
        return False


def main():
    """Run all quick tests."""
    logger.info("=" * 60)
    logger.info("Quick Test Suite - Audio Fingerprint Robustness Lab")
    logger.info("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Config Loading", test_config_loading),
        ("Audio Creation", test_audio_creation),
        ("Transforms", test_transforms),
        ("Segmentation", test_segmentation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"✗ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✅ All tests passed! The lab is ready to use.")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
