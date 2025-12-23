"""Tests for Ableton Live parser."""
import unittest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from daw_parser import AbletonParser, DAWParseError, DAWType
from daw_parser.exceptions import CorruptedFileError


class TestAbletonParser(unittest.TestCase):
    """Test cases for Ableton parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    def test_parser_initialization_invalid_file(self):
        """Test parser raises error for invalid file."""
        invalid_file = self.fixtures_dir / "nonexistent.als"
        with self.assertRaises(FileNotFoundError):
            AbletonParser(invalid_file)
    
    def test_parser_initialization_wrong_extension(self):
        """Test parser raises error for wrong file extension."""
        wrong_file = self.fixtures_dir / "test.txt"
        wrong_file.touch()  # Create empty file
        try:
            with self.assertRaises(ValueError):
                AbletonParser(wrong_file)
        finally:
            wrong_file.unlink()  # Clean up
    
    def test_detect_daw_type(self):
        """Test DAW type detection."""
        # Create a dummy .als file for testing
        test_file = self.fixtures_dir / "test.als"
        try:
            # Create a minimal zip file (Ableton .als files are zips)
            import zipfile
            with zipfile.ZipFile(test_file, 'w') as zf:
                zf.writestr("AbletonProject.xml", '<?xml version="1.0"?><Ableton></Ableton>')
            
            parser = AbletonParser(test_file)
            self.assertEqual(parser.daw_type, DAWType.ABLETON)
            self.assertEqual(parser.daw_type.value, "ableton")
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_parse_minimal_file(self):
        """Test parsing minimal .als file."""
        test_file = self.fixtures_dir / "minimal.als"
        try:
            # Create minimal valid .als file
            import zipfile
            import xml.etree.ElementTree as ET
            
            root = ET.Element("Ableton")
            root.set("Creator", "Ableton Live 11.0")
            tree = ET.ElementTree(root)
            
            with zipfile.ZipFile(test_file, 'w') as zf:
                import io
                xml_buffer = io.BytesIO()
                tree.write(xml_buffer, encoding='utf-8', xml_declaration=True)
                zf.writestr("AbletonProject.xml", xml_buffer.getvalue())
            
            parser = AbletonParser(test_file)
            metadata = parser.parse()
            
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.daw_type, DAWType.ABLETON)
            self.assertIsInstance(metadata.midi_data, list)
            self.assertIsInstance(metadata.arrangement, type(metadata.arrangement))
            self.assertIsInstance(metadata.tempo_changes, list)
            self.assertIsInstance(metadata.plugin_chains, list)
            self.assertIsInstance(metadata.sample_sources, list)
            self.assertIsInstance(metadata.automation, list)
            
            # Test to_dict method
            metadata_dict = metadata.to_dict()
            self.assertIn("daw_type", metadata_dict)
            self.assertEqual(metadata_dict["daw_type"], "ableton")
            
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_validate_method(self):
        """Test validation method."""
        test_file = self.fixtures_dir / "validate_test.als"
        try:
            import zipfile
            with zipfile.ZipFile(test_file, 'w') as zf:
                zf.writestr("AbletonProject.xml", '<?xml version="1.0"?><Ableton></Ableton>')
            
            parser = AbletonParser(test_file)
            self.assertTrue(parser.validate())
        finally:
            if test_file.exists():
                test_file.unlink()


if __name__ == '__main__':
    unittest.main()
