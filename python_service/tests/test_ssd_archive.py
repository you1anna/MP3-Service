import tempfile
import unittest
from pathlib import Path

from src import ssd_archive as ssd_archive_module
from src.ssd_archive import SSDArchiver


class SSDArchiverReconcileTests(unittest.TestCase):
    def _make_archiver(self, tmp: Path, mounted: bool) -> SSDArchiver:
        volumes = tmp / "Volumes"
        volumes.mkdir(exist_ok=True)
        original_volumes = ssd_archive_module._VOLUMES
        ssd_archive_module._VOLUMES = volumes
        self.addCleanup(setattr, ssd_archive_module, "_VOLUMES", original_volumes)

        drive = volumes / "FakeSSD"
        if mounted:
            drive.mkdir(exist_ok=True)
        archive_path = drive / "music"
        return SSDArchiver(archive_path)

    def test_reconcile_moves_stranded_files_when_mounted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_path = tmp_path / "processed"
            local_path.mkdir()
            (local_path / "Artist - Title.mp3").write_bytes(b"audio")
            (local_path / "Other - Song.mp3").write_bytes(b"audio2")

            archiver = self._make_archiver(tmp_path, mounted=True)

            moved = archiver.reconcile(local_path)

            self.assertEqual(moved, 2)
            self.assertFalse((local_path / "Artist - Title.mp3").exists())
            self.assertFalse((local_path / "Other - Song.mp3").exists())
            self.assertTrue((archiver.archive_path / "Artist - Title.mp3").exists())
            self.assertTrue((archiver.archive_path / "Other - Song.mp3").exists())

    def test_reconcile_is_noop_when_not_mounted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_path = tmp_path / "processed"
            local_path.mkdir()
            stranded = local_path / "Artist - Title.mp3"
            stranded.write_bytes(b"audio")

            archiver = self._make_archiver(tmp_path, mounted=False)

            moved = archiver.reconcile(local_path)

            self.assertEqual(moved, 0)
            self.assertTrue(stranded.exists())

    def test_reconcile_is_noop_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "processed"
            local_path.mkdir()
            (local_path / "Artist - Title.mp3").write_bytes(b"audio")

            archiver = SSDArchiver(None)

            self.assertEqual(archiver.reconcile(local_path), 0)
            self.assertTrue((local_path / "Artist - Title.mp3").exists())

    def test_reconcile_skips_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_path = tmp_path / "processed"
            local_path.mkdir()
            (local_path / "subdir").mkdir()

            archiver = self._make_archiver(tmp_path, mounted=True)

            moved = archiver.reconcile(local_path)

            self.assertEqual(moved, 0)
            self.assertTrue((local_path / "subdir").exists())

    def test_reconcile_is_noop_when_local_path_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archiver = self._make_archiver(tmp_path, mounted=True)

            moved = archiver.reconcile(tmp_path / "does-not-exist")

            self.assertEqual(moved, 0)


if __name__ == "__main__":
    unittest.main()
