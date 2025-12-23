"""Tests for FL Studio parser."""
import unittest
from pathlib import Path
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from daw_parser import FLStudioParser, DAWParseError, DAWType
from daw_parser.exceptions import CorruptedFileError


class TestFLStudioParser(unittest.TestCase):
    """Test cases for FL Studio parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    def test_parser_initialization_invalid_file(self):
        """Test parser raises error for invalid file."""
        invalid_file = self.fixtures_dir / "nonexistent.flp"
        with self.assertRaises(FileNotFoundError):
            FLStudioParser(invalid_file)
    
    def test_parser_initialization_wrong_extension(self):
        """Test parser raises error for wrong file extension."""
        wrong_file = self.fixtures_dir / "test.txt"
        wrong_file.touch()
        try:
            with self.assertRaises(ValueError):
                FLStudioParser(wrong_file)
        finally:
            wrong_file.unlink()
    
    def test_detect_daw_type(self):
        """Test DAW type detection."""
        # Create a minimal .flp file for testing
        test_file = self.fixtures_dir / "test.flp"
        try:
            # Create minimal binary file
            with open(test_file, 'wb') as f:
                f.write(b'FLhd')  # Minimal header
            
            parser = FLStudioParser(test_file)
            self.assertEqual(parser.daw_type, DAWType.FLSTUDIO)
            self.assertEqual(parser.daw_type.value, "flstudio")
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_parse_minimal_file(self):
        """Test parsing minimal .flp file."""
        test_file = self.fixtures_dir / "minimal.flp"
        try:
            # Create minimal valid .flp file
            with open(test_file, 'wb') as f:
                f.write(b'FLhd' + b'\x00' * 100)  # Minimal header with padding
            
            parser = FLStudioParser(test_file)
            metadata = parser.parse()
            
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.daw_type, DAWType.FLSTUDIO)
            self.assertIsInstance(metadata.midi_data, list)
            self.assertIsInstance(metadata.arrangement, type(metadata.arrangement))
            self.assertIsInstance(metadata.tempo_changes, list)
            self.assertIsInstance(metadata.plugin_chains, list)
            self.assertIsInstance(metadata.sample_sources, list)
            self.assertIsInstance(metadata.automation, list)
            
            # Test to_dict method
            metadata_dict = metadata.to_dict()
            self.assertIn("daw_type", metadata_dict)
            self.assertEqual(metadata_dict["daw_type"], "flstudio")
            
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_validate_method(self):
        """Test validation method."""
        test_file = self.fixtures_dir / "validate_test.flp"
        try:
            with open(test_file, 'wb') as f:
                f.write(b'FLhd' + b'\x00' * 100)
            
            parser = FLStudioParser(test_file)
            # Validation may fail for minimal files, but should not crash
            result = parser.validate()
            self.assertIsInstance(result, bool)
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_binary_reading_utilities(self):
        """Test binary reading utility methods."""
        test_file = self.fixtures_dir / "binary_test.flp"
        try:
            import struct
            # Create file with known binary data
            with open(test_file, 'wb') as f:
                f.write(b'FLhd')
                f.write(struct.pack('<H', 12345))  # uint16
                f.write(struct.pack('<I', 12345678))  # uint32
                f.write(struct.pack('<f', 123.45))  # float
            
            parser = FLStudioParser(test_file)
            
            # Test reading utilities
            self.assertEqual(parser._read_uint16(4), 12345)
            self.assertEqual(parser._read_uint32(6), 12345678)
            self.assertAlmostEqual(parser._read_float(10), 123.45, places=2)
            
        finally:
            if test_file.exists():
                test_file.unlink()


if __name__ == '__main__':
    unittest.main()
