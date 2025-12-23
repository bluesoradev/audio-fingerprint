"""Tests for Logic Pro parser."""
import unittest
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from daw_parser import LogicParser, DAWParseError, DAWType
from daw_parser.exceptions import CorruptedFileError


class TestLogicParser(unittest.TestCase):
    """Test cases for Logic Pro parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    def test_parser_initialization_invalid_file(self):
        """Test parser raises error for invalid file."""
        invalid_file = self.fixtures_dir / "nonexistent.logicx"
        with self.assertRaises(FileNotFoundError):
            LogicParser(invalid_file)
    
    def test_parser_initialization_wrong_extension(self):
        """Test parser raises error for wrong file extension."""
        wrong_file = self.fixtures_dir / "test.txt"
        wrong_file.touch()
        try:
            with self.assertRaises(ValueError):
                LogicParser(wrong_file)
        finally:
            wrong_file.unlink()
    
    def test_parser_initialization_not_directory(self):
        """Test parser raises error if .logicx is not a directory."""
        test_file = self.fixtures_dir / "test.logicx"
        test_file.touch()  # Create as file, not directory
        try:
            with self.assertRaises(ValueError):
                LogicParser(test_file)
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_detect_daw_type(self):
        """Test DAW type detection."""
        # Create a minimal .logicx directory for testing
        test_dir = self.fixtures_dir / "test.logicx"
        try:
            test_dir.mkdir()
            
            # Create minimal XML file
            xml_file = test_dir / "project.xml"
            root = ET.Element("Logic")
            root.set("version", "10.0")
            tree = ET.ElementTree(root)
            tree.write(xml_file, encoding='utf-8', xml_declaration=True)
            
            parser = LogicParser(test_dir)
            self.assertEqual(parser.daw_type, DAWType.LOGIC)
            self.assertEqual(parser.daw_type.value, "logic")
        finally:
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)
    
    def test_parse_minimal_file(self):
        """Test parsing minimal .logicx file."""
        test_dir = self.fixtures_dir / "minimal.logicx"
        try:
            test_dir.mkdir()
            
            # Create minimal valid Logic Pro project structure
            root = ET.Element("Logic")
            root.set("version", "10.0")
            live_set = ET.SubElement(root, "LiveSet")
            tree = ET.ElementTree(root)
            
            xml_file = test_dir / "project.xml"
            tree.write(xml_file, encoding='utf-8', xml_declaration=True)
            
            parser = LogicParser(test_dir)
            metadata = parser.parse()
            
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.daw_type, DAWType.LOGIC)
            self.assertIsInstance(metadata.midi_data, list)
            self.assertIsInstance(metadata.arrangement, type(metadata.arrangement))
            self.assertIsInstance(metadata.tempo_changes, list)
            self.assertIsInstance(metadata.plugin_chains, list)
            self.assertIsInstance(metadata.sample_sources, list)
            self.assertIsInstance(metadata.automation, list)
            
            # Test to_dict method
            metadata_dict = metadata.to_dict()
            self.assertIn("daw_type", metadata_dict)
            self.assertEqual(metadata_dict["daw_type"], "logic")
            
        finally:
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)
    
    def test_validate_method(self):
        """Test validation method."""
        test_dir = self.fixtures_dir / "validate_test.logicx"
        try:
            test_dir.mkdir()
            xml_file = test_dir / "project.xml"
            
            root = ET.Element("Logic")
            tree = ET.ElementTree(root)
            tree.write(xml_file, encoding='utf-8', xml_declaration=True)
            
            parser = LogicParser(test_dir)
            self.assertTrue(parser.validate())
        finally:
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)
    
    def test_find_xml_files(self):
        """Test finding XML files in package."""
        test_dir = self.fixtures_dir / "xml_test.logicx"
        try:
            test_dir.mkdir()
            
            # Create XML in subdirectory
            project_data = test_dir / "projectdata"
            project_data.mkdir()
            xml_file = project_data / "project.xml"
            
            root = ET.Element("Logic")
            tree = ET.ElementTree(root)
            tree.write(xml_file, encoding='utf-8', xml_declaration=True)
            
            parser = LogicParser(test_dir)
            # Should successfully load XML from subdirectory
            self.assertIsNotNone(parser.xml_root)
            
        finally:
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)


if __name__ == '__main__':
    unittest.main()
