"""Comprehensive test suite for Phase 1 DAW Parser implementation."""
import sys
import unittest
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import io
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from daw_parser import (
    AbletonParser, DAWMetadata, MIDINote, MIDITrack, ArrangementData,
    TempoChange, KeyChange, PluginChain, SampleSource, AutomationData,
    DAWType, DAWParseError, CorruptedFileError, UnsupportedDAWError
)
from daw_parser.models import (
    ClipData, PluginDevice, PluginParameter, AutomationPoint
)
from daw_parser.utils import (
    save_metadata, load_metadata, detect_daw_type, find_daw_files,
    link_daw_to_audio
)


class TestPhase1Imports(unittest.TestCase):
    """Test that all Phase 1 modules can be imported."""
    
    def test_core_imports(self):
        """Test core module imports."""
        from daw_parser import (
            DAWMetadata, MIDINote, MIDITrack, ArrangementData,
            TempoChange, KeyChange, PluginChain, SampleSource,
            AutomationData, DAWType
        )
        self.assertTrue(True)
    
    def test_parser_imports(self):
        """Test parser imports."""
        from daw_parser import BaseDAWParser, AbletonParser
        self.assertTrue(True)
    
    def test_exception_imports(self):
        """Test exception imports."""
        from daw_parser import (
            DAWParseError, CorruptedFileError, UnsupportedDAWError
        )
        self.assertTrue(True)
    
    def test_utils_imports(self):
        """Test utility imports."""
        from daw_parser.utils import (
            save_metadata, detect_daw_type, find_daw_files
        )
        self.assertTrue(True)


class TestPhase1DataModels(unittest.TestCase):
    """Test Phase 1 data models."""
    
    def test_midi_note_creation(self):
        """Test MIDINote creation."""
        note = MIDINote(
            note=60,
            velocity=100,
            start_time=0.0,
            duration=1.0,
            channel=0
        )
        self.assertEqual(note.note, 60)
        self.assertEqual(note.velocity, 100)
        self.assertEqual(note.start_time, 0.0)
        self.assertEqual(note.duration, 1.0)
        self.assertEqual(note.channel, 0)
    
    def test_midi_track_creation(self):
        """Test MIDITrack creation."""
        notes = [
            MIDINote(note=60, velocity=100, start_time=0.0, duration=1.0),
            MIDINote(note=64, velocity=80, start_time=1.0, duration=0.5)
        ]
        track = MIDITrack(
            track_name="Test Track",
            track_index=0,
            notes=notes
        )
        self.assertEqual(track.track_name, "Test Track")
        self.assertEqual(len(track.notes), 2)
        self.assertEqual(track.track_index, 0)
    
    def test_arrangement_data_creation(self):
        """Test ArrangementData creation."""
        clips = [
            ClipData(
                clip_name="Clip 1",
                start_time=0.0,
                end_time=4.0,
                track_name="Track 1",
                clip_type="audio"
            )
        ]
        arrangement = ArrangementData(
            clips=clips,
            total_length=4.0,
            tracks=["Track 1"]
        )
        self.assertEqual(len(arrangement.clips), 1)
        self.assertEqual(arrangement.total_length, 4.0)
        self.assertEqual(len(arrangement.tracks), 1)
    
    def test_tempo_change_creation(self):
        """Test TempoChange creation."""
        tempo = TempoChange(
            time=0.0,
            tempo=120.0,
            time_signature="4/4"
        )
        self.assertEqual(tempo.time, 0.0)
        self.assertEqual(tempo.tempo, 120.0)
        self.assertEqual(tempo.time_signature, "4/4")
    
    def test_plugin_chain_creation(self):
        """Test PluginChain creation."""
        device = PluginDevice(
            device_name="Compressor",
            device_type="native",
            parameters=[
                PluginParameter(parameter_name="Threshold", value=-12.0)
            ]
        )
        chain = PluginChain(
            track_name="Track 1",
            devices=[device]
        )
        self.assertEqual(chain.track_name, "Track 1")
        self.assertEqual(len(chain.devices), 1)
        self.assertEqual(chain.devices[0].device_name, "Compressor")
    
    def test_daw_metadata_creation(self):
        """Test DAWMetadata creation."""
        metadata = DAWMetadata(
            project_path=Path("test.als"),
            daw_type=DAWType.ABLETON,
            version="11.0"
        )
        self.assertEqual(metadata.daw_type, DAWType.ABLETON)
        self.assertEqual(metadata.version, "11.0")
        self.assertIsInstance(metadata.midi_data, list)
        self.assertIsInstance(metadata.arrangement, ArrangementData)
    
    def test_daw_metadata_to_dict(self):
        """Test DAWMetadata.to_dict() method."""
        metadata = DAWMetadata(
            project_path=Path("test.als"),
            daw_type=DAWType.ABLETON,
            version="11.0"
        )
        metadata_dict = metadata.to_dict()
        
        self.assertIn("daw_type", metadata_dict)
        self.assertIn("version", metadata_dict)
        self.assertIn("midi_tracks", metadata_dict)
        self.assertEqual(metadata_dict["daw_type"], "ableton")
        self.assertEqual(metadata_dict["version"], "11.0")


class TestPhase1AbletonParser(unittest.TestCase):
    """Test Ableton Live parser functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_minimal_als_file(self, filename="test.als"):
        """Create a minimal valid .als file for testing."""
        test_file = self.temp_dir / filename
        
        root = ET.Element("Ableton")
        root.set("Creator", "Ableton Live 11.0")
        root.set("MajorVersion", "11")
        root.set("MinorVersion", "0")
        
        # Add LiveSet element
        live_set = ET.SubElement(root, "LiveSet")
        
        tree = ET.ElementTree(root)
        
        with zipfile.ZipFile(test_file, 'w') as zf:
            xml_buffer = io.BytesIO()
            tree.write(xml_buffer, encoding='utf-8', xml_declaration=True)
            zf.writestr("AbletonProject.xml", xml_buffer.getvalue())
        
        return test_file
    
    def test_parser_initialization(self):
        """Test parser can be initialized."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        
        self.assertIsNotNone(parser)
        self.assertEqual(parser.daw_type, DAWType.ABLETON)
        self.assertEqual(parser.file_path, test_file)
    
    def test_parser_file_not_found(self):
        """Test parser raises error for non-existent file."""
        with self.assertRaises(FileNotFoundError):
            AbletonParser(self.temp_dir / "nonexistent.als")
    
    def test_parser_wrong_extension(self):
        """Test parser raises error for wrong file extension."""
        wrong_file = self.temp_dir / "test.txt"
        wrong_file.touch()
        
        try:
            with self.assertRaises(ValueError):
                AbletonParser(wrong_file)
        finally:
            wrong_file.unlink()
    
    def test_parse_minimal_file(self):
        """Test parsing minimal .als file."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        metadata = parser.parse()
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.daw_type, DAWType.ABLETON)
        self.assertIsInstance(metadata.midi_data, list)
        self.assertIsInstance(metadata.arrangement, ArrangementData)
        self.assertIsInstance(metadata.tempo_changes, list)
        self.assertIsInstance(metadata.plugin_chains, list)
        self.assertIsInstance(metadata.sample_sources, list)
        self.assertIsInstance(metadata.automation, list)
    
    def test_extract_version(self):
        """Test version extraction."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        version = parser._extract_version()
        
        self.assertIsInstance(version, str)
        self.assertGreater(len(version), 0)
    
    def test_extract_midi_data_empty(self):
        """Test MIDI data extraction from empty file."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        midi_data = parser._extract_midi_data()
        
        self.assertIsInstance(midi_data, list)
        # Empty file should return empty list
    
    def test_extract_arrangement_empty(self):
        """Test arrangement extraction from empty file."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        arrangement = parser._extract_arrangement()
        
        self.assertIsInstance(arrangement, ArrangementData)
        self.assertEqual(len(arrangement.clips), 0)
        self.assertEqual(arrangement.total_length, 0.0)
    
    def test_extract_tempo_changes(self):
        """Test tempo changes extraction."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        tempo_changes = parser._extract_tempo_changes()
        
        self.assertIsInstance(tempo_changes, list)
    
    def test_extract_plugin_chains(self):
        """Test plugin chains extraction."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        plugin_chains = parser._extract_plugin_chains()
        
        self.assertIsInstance(plugin_chains, list)
    
    def test_extract_sample_sources(self):
        """Test sample sources extraction."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        sample_sources = parser._extract_sample_sources()
        
        self.assertIsInstance(sample_sources, list)
    
    def test_extract_automation(self):
        """Test automation extraction."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        automation = parser._extract_automation()
        
        self.assertIsInstance(automation, list)
    
    def test_validate_method(self):
        """Test validation method."""
        test_file = self.create_minimal_als_file()
        parser = AbletonParser(test_file)
        
        is_valid = parser.validate()
        self.assertTrue(is_valid)
    
    def test_parse_corrupted_file(self):
        """Test parsing corrupted file."""
        corrupted_file = self.temp_dir / "corrupted.als"
        with open(corrupted_file, 'wb') as f:
            f.write(b"Not a valid zip file")
        
        # Corrupted file should raise error during initialization
        with self.assertRaises((CorruptedFileError, DAWParseError)):
            AbletonParser(corrupted_file)


class TestPhase1Utilities(unittest.TestCase):
    """Test utility functions."""
    
    def test_detect_daw_type(self):
        """Test DAW type detection."""
        self.assertEqual(detect_daw_type(Path("test.als")), "ableton")
        self.assertEqual(detect_daw_type(Path("test.flp")), "flstudio")
        self.assertEqual(detect_daw_type(Path("test.logicx")), "logic")
        self.assertEqual(detect_daw_type(Path("test.logic")), "logic")
        self.assertIsNone(detect_daw_type(Path("test.txt")))
        self.assertIsNone(detect_daw_type(Path("test.wav")))
    
    def test_save_and_load_metadata(self):
        """Test saving and loading metadata."""
        import tempfile
        
        metadata = DAWMetadata(
            project_path=Path("test.als"),
            daw_type=DAWType.ABLETON,
            version="11.0"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "metadata.json"
            save_metadata(metadata, output_file)
            
            self.assertTrue(output_file.exists())
            
            loaded = load_metadata(output_file)
            self.assertIn("daw_type", loaded)
            self.assertEqual(loaded["daw_type"], "ableton")
    
    def test_find_daw_files(self):
        """Test finding DAW files in directory."""
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Create test files
            (tmp_path / "project1.als").touch()
            (tmp_path / "project2.flp").touch()
            (tmp_path / "project3.logicx").touch()
            (tmp_path / "not_daw.txt").touch()
            
            daw_files = find_daw_files(tmp_path)
            
            self.assertEqual(len(daw_files), 3)
            extensions = [f.suffix.lower() for f in daw_files]
            self.assertIn(".als", extensions)
            self.assertIn(".flp", extensions)
            self.assertIn(".logicx", extensions)


class TestPhase1ErrorHandling(unittest.TestCase):
    """Test error handling."""
    
    def test_corrupted_file_error(self):
        """Test CorruptedFileError."""
        error = CorruptedFileError("File is corrupted", "test.als")
        self.assertEqual(error.message, "File is corrupted")
        self.assertEqual(error.file_path, "test.als")
    
    def test_daw_parse_error(self):
        """Test DAWParseError."""
        error = DAWParseError("Parse failed", "test.als")
        self.assertEqual(error.message, "Parse failed")
        self.assertEqual(error.file_path, "test.als")
    
    def test_unsupported_daw_error(self):
        """Test UnsupportedDAWError."""
        error = UnsupportedDAWError("Unsupported format", "test.xyz")
        self.assertIsInstance(error, DAWParseError)


class TestPhase1Integration(unittest.TestCase):
    """Integration tests for Phase 1."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_minimal_als_file(self, filename="test.als"):
        """Create a minimal valid .als file for testing."""
        test_file = self.temp_dir / filename
        
        root = ET.Element("Ableton")
        root.set("Creator", "Ableton Live 11.0")
        live_set = ET.SubElement(root, "LiveSet")
        tree = ET.ElementTree(root)
        
        with zipfile.ZipFile(test_file, 'w') as zf:
            xml_buffer = io.BytesIO()
            tree.write(xml_buffer, encoding='utf-8', xml_declaration=True)
            zf.writestr("AbletonProject.xml", xml_buffer.getvalue())
        
        return test_file
    
    def test_full_workflow(self):
        """Test complete workflow from file to JSON."""
        # Create test file
        test_file = self.create_minimal_als_file()
        
        # Parse
        parser = AbletonParser(test_file)
        metadata = parser.parse()
        
        # Save
        output_file = self.temp_dir / "metadata.json"
        save_metadata(metadata, output_file)
        
        # Verify
        self.assertTrue(output_file.exists())
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["daw_type"], "ableton")
        self.assertIn("extracted_at", data)
    
    def test_metadata_serialization(self):
        """Test metadata can be serialized to JSON."""
        metadata = DAWMetadata(
            project_path=Path("test.als"),
            daw_type=DAWType.ABLETON,
            version="11.0"
        )
        
        metadata_dict = metadata.to_dict()
        
        # Should be JSON serializable
        json_str = json.dumps(metadata_dict)
        self.assertIsInstance(json_str, str)
        
        # Should be deserializable
        loaded = json.loads(json_str)
        self.assertEqual(loaded["daw_type"], "ableton")


class TestPhase1CLI(unittest.TestCase):
    """Test CLI tool functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_minimal_als_file(self, filename="test.als"):
        """Create a minimal valid .als file for testing."""
        test_file = self.temp_dir / filename
        
        root = ET.Element("Ableton")
        root.set("Creator", "Ableton Live 11.0")
        live_set = ET.SubElement(root, "LiveSet")
        tree = ET.ElementTree(root)
        
        with zipfile.ZipFile(test_file, 'w') as zf:
            xml_buffer = io.BytesIO()
            tree.write(xml_buffer, encoding='utf-8', xml_declaration=True)
            zf.writestr("AbletonProject.xml", xml_buffer.getvalue())
        
        return test_file
    
    def test_cli_import(self):
        """Test CLI module can be imported."""
        from scripts.process_daw_files import process_daw_file
        self.assertTrue(callable(process_daw_file))


def run_all_tests():
    """Run all Phase 1 tests and print summary."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPhase1Imports,
        TestPhase1DataModels,
        TestPhase1AbletonParser,
        TestPhase1Utilities,
        TestPhase1ErrorHandling,
        TestPhase1Integration,
        TestPhase1CLI
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All Phase 1 tests passed!")
    else:
        print("\n[WARNING] Some tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
