import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.processor import AudioProcessor


class DummyConfig:
    def __init__(self, root: Path):
        self.base_path = root / "complete"
        self.local_path = root / "processed"
        self.base_path.mkdir()
        self.local_path.mkdir()
        self.supported_extensions = (".flac", ".mp3")
        self.rekordbox_xml_path = None
        self.ssd_archive_path = None
        self.include_share = False
        self.network_path = None
        self.desktop_path = None
        self.backup_before_delete = False
        self.backup_path = None
        self.bpm_range = (65, 135)


class ProcessorFlacLifecycleTests(unittest.TestCase):
    def test_flac_source_is_deleted_after_successful_final_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")

            processor = AudioProcessor(config)
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)
            processor._process_bpm = lambda path, bpm: bpm
            processor._convert_flac_to_aiff = lambda src, dst: dst.write_bytes(b"aiff") or True
            processor.tag_handler.set_tags = lambda *args, **kwargs: None
            processor.tag_handler.clear_extra_tags = lambda *args, **kwargs: None
            processor.ssd_archiver.relocate = lambda path: path
            processor.rekordbox_xml.register = lambda *args, **kwargs: None

            processor.process_file(source)

            self.assertFalse(source.exists())
            self.assertTrue((config.local_path / "Artist - Title.aiff").exists())
            self.assertIn(str(source), (config.base_path / "copiedList.txt").read_text())
            self.assertEqual(processor.stats["processed"], 1)
            self.assertEqual(processor.stats["errors"], 0)

    def test_failed_flac_conversion_keeps_source_and_does_not_mark_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")

            processor = AudioProcessor(config)
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)
            processor._process_bpm = lambda path, bpm: bpm
            processor._convert_flac_to_aiff = lambda src, dst: False

            processor.process_file(source)

            self.assertTrue(source.exists())
            self.assertFalse((config.local_path / "Artist - Title.aiff").exists())
            self.assertEqual((config.base_path / "copiedList.txt").read_text(), "")
            self.assertEqual(processor.stats["processed"], 0)
            self.assertEqual(processor.stats["errors"], 1)

    def test_flac_source_is_kept_when_configured_ssd_move_does_not_reach_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")

            processor = AudioProcessor(config)
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)
            processor._process_bpm = lambda path, bpm: bpm
            processor._convert_flac_to_aiff = lambda src, dst: dst.write_bytes(b"aiff") or True
            processor.tag_handler.set_tags = lambda *args, **kwargs: None
            processor.tag_handler.clear_extra_tags = lambda *args, **kwargs: None
            processor.ssd_archiver = SimpleNamespace(
                configured=True,
                archive_path=config.ssd_archive_path,
                relocate=lambda path: path,
            )
            processor.rekordbox_xml.register = lambda *args, **kwargs: None

            processor.process_file(source)

            self.assertTrue(source.exists())
            self.assertFalse((config.local_path / "Artist - Title.aiff").exists())
            self.assertEqual((config.base_path / "copiedList.txt").read_text(), "")
            self.assertEqual(processor.stats["processed"], 0)
            self.assertEqual(processor.stats["errors"], 1)

    def test_process_file_skips_paths_already_in_copied_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            processor = AudioProcessor(config)
            calls = []
            processor.tag_handler.get_tags = lambda path: calls.append(path)

            processor.process_file(source)

            self.assertEqual(calls, [])
            self.assertTrue(source.exists())
            self.assertEqual(processor.stats["processed"], 0)
            self.assertEqual(processor.stats["skipped"], 1)


if __name__ == "__main__":
    unittest.main()
