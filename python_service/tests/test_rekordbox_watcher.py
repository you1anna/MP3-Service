"""Tests for the external-drive Rekordbox watcher, focused on the anti-flood
safety valve that prevents a library move/reorg from mass-registering files."""

import tempfile
import unittest
from pathlib import Path

from src.rekordbox_watcher import ExternalDriveWatcher


class DummyConfig:
    """Minimal config the watcher needs, pointed at a temp tree."""

    def __init__(self, root: Path, max_new_per_scan: int = 200):
        self.rekordbox_xml_path = root / "rb.xml"
        self.external_watch_path = root / "watch"
        self.external_watch_path.mkdir(parents=True, exist_ok=True)
        self.external_poll_interval = 300
        self.external_seen_file = root / "seen.txt"
        self.external_skip_dirs = []
        self.supported_extensions = (".wav", ".mp3", ".aiff", ".flac")
        self.external_max_new_per_scan = max_new_per_scan
        self.log_level = "INFO"


class FakeWriter:
    enabled = True

    def __init__(self):
        self.registered = []

    def register(self, path, artist, title, bpm):
        self.registered.append(path)


class FakeTags:
    def get_tags(self, path):
        return (None, None, None)


def _make_audio(root: Path, n: int) -> None:
    for i in range(n):
        (root / f"track_{i:04d}.wav").write_bytes(b"RIFF....WAVE")


def _watcher(config: DummyConfig) -> ExternalDriveWatcher:
    w = ExternalDriveWatcher(config)
    w.writer = FakeWriter()
    w.tag_handler = FakeTags()
    return w


class SafetyValveTests(unittest.TestCase):
    def test_registers_new_files_when_under_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = DummyConfig(Path(tmp), max_new_per_scan=10)
            cfg.external_seen_file.write_text("")  # exists -> not first-run baseline
            _make_audio(cfg.external_watch_path, 3)

            w = _watcher(cfg)
            w._scan_once()

            self.assertEqual(len(w.writer.registered), 3)
            self.assertEqual(len(w.seen), 3)

    def test_rebaselines_without_registering_when_over_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = DummyConfig(Path(tmp), max_new_per_scan=3)
            cfg.external_seen_file.write_text("")  # exists -> not first-run baseline
            _make_audio(cfg.external_watch_path, 5)  # 5 > cap of 3

            w = _watcher(cfg)
            w._scan_once()

            # Anti-flood: nothing registered, but all recorded as seen.
            self.assertEqual(w.writer.registered, [])
            self.assertEqual(len(w.seen), 5)
            # Persisted so the next scan stays quiet.
            self.assertEqual(
                len(cfg.external_seen_file.read_text().splitlines()), 5
            )

    def test_first_run_baselines_without_registering(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = DummyConfig(Path(tmp), max_new_per_scan=10)
            # no seen file -> first-run baseline
            _make_audio(cfg.external_watch_path, 4)

            w = _watcher(cfg)
            w._scan_once()

            self.assertEqual(w.writer.registered, [])
            self.assertEqual(len(w.seen), 4)


if __name__ == "__main__":
    unittest.main()
