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


def _flac_processor_that_always_fails(config: DummyConfig) -> AudioProcessor:
    processor = AudioProcessor(config)
    processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)
    processor._process_bpm = lambda path, bpm: bpm
    processor._convert_flac_to_aiff = lambda src, dst: False
    return processor


class ProcessorRetryCapTests(unittest.TestCase):
    def test_process_all_stops_retrying_after_max_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")

            processor = _flac_processor_that_always_fails(config)
            attempts = []
            original = processor._convert_flac_to_aiff
            processor._convert_flac_to_aiff = lambda src, dst: attempts.append(src) or original(src, dst)

            for _ in range(6):
                processor.process_all()

            self.assertEqual(len(attempts), AudioProcessor.MAX_RETRY_ATTEMPTS)
            self.assertTrue(source.exists())

    def test_reset_retry_state_allows_reprocessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")

            processor = _flac_processor_that_always_fails(config)
            attempts = []
            original = processor._convert_flac_to_aiff
            processor._convert_flac_to_aiff = lambda src, dst: attempts.append(src) or original(src, dst)

            for _ in range(5):
                processor.process_all()
            self.assertEqual(len(attempts), AudioProcessor.MAX_RETRY_ATTEMPTS)

            processor.reset_retry_state()
            processor.process_all()

            self.assertEqual(len(attempts), AudioProcessor.MAX_RETRY_ATTEMPTS + 1)

    def test_successful_processing_clears_the_failure_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            source = config.base_path / "Artist - Title.flac"
            source.write_bytes(b"flac")

            processor = _flac_processor_that_always_fails(config)
            processor.process_all()
            self.assertEqual(processor._failed_attempts.get(str(source)), 1)

            processor.tag_handler.set_tags = lambda *args, **kwargs: None
            processor.tag_handler.clear_extra_tags = lambda *args, **kwargs: None
            processor._convert_flac_to_aiff = lambda src, dst: dst.write_bytes(b"aiff") or True
            processor.ssd_archiver.relocate = lambda path: path
            processor.rekordbox_xml.register = lambda *args, **kwargs: None

            processor.process_all()

            self.assertNotIn(str(source), processor._failed_attempts)


class ProcessorCopiedSourceCleanupTests(unittest.TestCase):
    """A source file already in copiedList must be removed once its output exists.

    This used to be FLAC-only, so a re-downloaded MP3 sat in the source
    directory forever: blocked from reprocessing by its copiedList entry and
    ignored by the FLAC-only cleanup.
    """

    def _processor_with_ssd(self, config: DummyConfig) -> AudioProcessor:
        processor = AudioProcessor(config)
        processor.ssd_archiver = SimpleNamespace(
            configured=True,
            archive_path=config.ssd_archive_path,
            reconcile=lambda local_path: 0,
        )
        processor.tag_handler.get_tags = lambda path: ("Artist", "Title", 128)
        return processor

    def test_removes_copied_mp3_source_when_output_exists_on_ssd(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            config.ssd_archive_path.mkdir(parents=True)
            source = config.base_path / "01-artist-title.mp3"
            source.write_bytes(b"mp3")
            (config.ssd_archive_path / "Artist - Title.mp3").write_bytes(b"mp3")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            stats = self._processor_with_ssd(config).process_all()

            self.assertFalse(source.exists())
            self.assertEqual(stats["skipped"], 1)

    def test_keeps_copied_mp3_source_when_output_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"
            config.ssd_archive_path.mkdir(parents=True)
            source = config.base_path / "01-artist-title.mp3"
            source.write_bytes(b"mp3")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            stats = self._processor_with_ssd(config).process_all()

            self.assertTrue(source.exists())
            self.assertEqual(stats["skipped"], 1)

    def test_keeps_copied_source_when_ssd_is_unreachable(self):
        """The SSD being down must not be mistaken for 'output does not exist'."""
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            config.ssd_archive_path = Path(tmp) / "ssd" / "music"  # never created
            source = config.base_path / "01-artist-title.mp3"
            source.write_bytes(b"mp3")
            (config.base_path / "copiedList.txt").write_text(f"{source}\n")

            self._processor_with_ssd(config).process_all()

            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
