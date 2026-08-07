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

        # A temp dir is never a real mount point, so stand in a directory-exists
        # check for os.path.ismount while exercising the reconcile logic.
        original_ismount = ssd_archive_module._is_mount_point
        ssd_archive_module._is_mount_point = lambda path: Path(path).is_dir()
        self.addCleanup(setattr, ssd_archive_module, "_is_mount_point", original_ismount)

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

    def test_reconcile_skips_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_path = tmp_path / "processed"
            local_path.mkdir()
            (local_path / ".DS_Store").write_bytes(b"junk")

            archiver = self._make_archiver(tmp_path, mounted=True)

            moved = archiver.reconcile(local_path)

            self.assertEqual(moved, 0)
            self.assertTrue((local_path / ".DS_Store").exists())
            self.assertFalse((archiver.archive_path / ".DS_Store").exists())

    def test_reconcile_is_noop_when_local_path_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archiver = self._make_archiver(tmp_path, mounted=True)

            moved = archiver.reconcile(tmp_path / "does-not-exist")

            self.assertEqual(moved, 0)


class SSDArchiverMountDetectionTests(unittest.TestCase):
    """The mount root existing as a directory is not proof the volume is mounted.

    macOS can leave a stale /Volumes/<drive> directory behind after an
    ungraceful eject. Treating that as mounted would silently archive tracks
    onto the boot disk under a path that looks like the SSD.
    """

    def _archiver(self, tmp: Path) -> SSDArchiver:
        volumes = tmp / "Volumes"
        volumes.mkdir(exist_ok=True)
        original_volumes = ssd_archive_module._VOLUMES
        ssd_archive_module._VOLUMES = volumes
        self.addCleanup(setattr, ssd_archive_module, "_VOLUMES", original_volumes)
        return SSDArchiver(volumes / "FakeSSD" / "music")

    def test_stale_mount_directory_is_not_reported_as_mounted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "Volumes" / "FakeSSD").mkdir(parents=True)

            archiver = self._archiver(tmp_path)

            self.assertTrue(archiver.configured)
            self.assertFalse(archiver.mounted)

    def test_relocate_keeps_file_local_when_mount_root_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "Volumes" / "FakeSSD").mkdir(parents=True)
            staged = tmp_path / "Artist - Title.mp3"
            staged.write_bytes(b"audio")

            archiver = self._archiver(tmp_path)

            self.assertEqual(archiver.relocate(staged), staged)
            self.assertTrue(staged.exists())
            self.assertFalse((tmp_path / "Volumes" / "FakeSSD" / "music").exists())

    def test_real_mount_point_is_reported_as_mounted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "Volumes" / "FakeSSD").mkdir(parents=True)

            original_ismount = ssd_archive_module._is_mount_point
            ssd_archive_module._is_mount_point = lambda path: True
            self.addCleanup(setattr, ssd_archive_module, "_is_mount_point", original_ismount)

            self.assertTrue(self._archiver(tmp_path).mounted)


if __name__ == "__main__":
    unittest.main()
