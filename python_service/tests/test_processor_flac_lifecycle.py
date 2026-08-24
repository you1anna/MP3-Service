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

    def test_unreachable_ssd_stages_aiff_locally_and_keeps_flac_without_retrying(self):
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

            # The lossless source survives until the AIFF is actually on the SSD...
            self.assertTrue(source.exists())
            # ...but the converted output is staged, not destroyed. reconcile()
            # moves it across once the volume reconnects.
            self.assertTrue((config.local_path / "Artist - Title.aiff").exists())
            # Recorded as processed so the next sweep does not redo BPM detection
            # and ffmpeg on a file whose only outstanding step is the archive hop.
            self.assertIn(str(source), (config.base_path / "copiedList.txt").read_text())
            self.assertEqual(processor.stats["processed"], 1)
            self.assertEqual(processor.stats["errors"], 0)

    def test_process_all_keeps_flac_when_aiff_is_only_staged_locally(self):
        """A locally staged AIFF must not authorise deleting the last lossless copy."""
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            config.ssd_archive_path.mkdir(parents=True)
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")
            staged = config.local_path / "Artist - Title.aiff"
            staged.write_bytes(b"aiff")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            processor = AudioProcessor(config)
            processor.ssd_archiver = SimpleNamespace(
                configured=True,
                archive_path=config.ssd_archive_path,
                reconcile=lambda local_path: 0,
            )
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)

            stats = processor.process_all()

            self.assertTrue(source.exists())
            self.assertTrue(staged.exists())
            self.assertEqual(stats["errors"], 0)
            self.assertEqual(stats["skipped"], 1)

    def test_process_all_removes_flac_once_reconcile_lands_the_aiff_on_the_ssd(self):
        """The deferred path closes: SSD returns -> reconcile moves -> source cleaned up."""
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            config.ssd_archive_path.mkdir(parents=True)
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")
            staged = config.local_path / "Artist - Title.aiff"
            staged.write_bytes(b"aiff")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            def reconnected_reconcile(local_path):
                moved = 0
                for item in sorted(Path(local_path).iterdir()):
                    if item.is_file() and not item.name.startswith("."):
                        item.rename(config.ssd_archive_path / item.name)
                        moved += 1
                return moved

            processor = AudioProcessor(config)
            processor.ssd_archiver = SimpleNamespace(
                configured=True,
                archive_path=config.ssd_archive_path,
                reconcile=reconnected_reconcile,
            )
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)

            stats = processor.process_all()

            self.assertTrue((config.ssd_archive_path / "Artist - Title.aiff").exists())
            self.assertFalse(staged.exists())
            self.assertFalse(source.exists())
            self.assertEqual(stats["errors"], 0)

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

    def test_process_all_removes_legacy_copied_flac_when_final_aiff_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            config.ssd_archive_path.mkdir(parents=True)
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")
            final = config.ssd_archive_path / "Artist - Title.aiff"
            final.write_bytes(b"aiff")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            processor = AudioProcessor(config)
            processor.ssd_archiver = SimpleNamespace(
                configured=True,
                archive_path=config.ssd_archive_path,
                reconcile=lambda local_path: 0,
            )
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)

            stats = processor.process_all()

            self.assertFalse(source.exists())
            self.assertTrue(final.exists())
            self.assertEqual(stats["processed"], 0)
            self.assertEqual(stats["errors"], 0)
            self.assertEqual(stats["skipped"], 1)

    def test_process_all_keeps_legacy_copied_flac_when_final_aiff_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            config.ssd_archive_path.mkdir(parents=True)
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            processor = AudioProcessor(config)
            processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)

            stats = processor.process_all()

            self.assertTrue(source.exists())
            self.assertEqual(stats["processed"], 0)
            self.assertEqual(stats["errors"], 0)
            self.assertEqual(stats["skipped"], 1)


if __name__ == "__main__":
    unittest.main()
