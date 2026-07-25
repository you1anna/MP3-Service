import tempfile
import unittest
from pathlib import Path

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


class ProcessorReconcileTests(unittest.TestCase):
    def test_process_all_reconciles_stranded_local_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            processor = AudioProcessor(config)

            calls = []
            processor.ssd_archiver.reconcile = lambda local_path: calls.append(local_path) or 0

            processor.process_all()

            self.assertEqual(calls, [config.local_path])

    def test_process_all_does_not_reconcile_in_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = DummyConfig(Path(tmp))
            processor = AudioProcessor(config, dry_run=True)

            calls = []
            processor.ssd_archiver.reconcile = lambda local_path: calls.append(local_path) or 0

            processor.process_all()

            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
