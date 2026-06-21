"""Watch an external drive for newly-arriving audio files and register them
in the shared Rekordbox XML.

Design constraints (per user):
- ZERO impact on the existing Rekordbox library. The XML is a one-way feed
  into Rekordbox's "rekordbox xml" side panel; tracks only enter the
  collection when the user explicitly imports them.
- First-run baseline: every file present at first scan is recorded in a
  persistent "seen" set WITHOUT registering it. Only files that appear
  AFTER baseline get registered. This prevents flooding the XML with the
  user's existing 30k+ catalogue.
- Drive may unmount/remount; the watcher must tolerate that without crashing.
- Failures must be isolated per-file; one bad track must not stop the loop.
"""

import time
from pathlib import Path
from typing import Iterable, Set

from .config import Config
from .logger import get_logger
from .rekordbox_xml import RekordboxXMLWriter
from .tag_handler import TagHandler


# Always-skip directory names. Anything starting with '.' is also skipped.
_DEFAULT_SKIP_DIRS = frozenset({
    "$RECYCLE.BIN",
    "System Volume Information",
    "rekordbox",  # Rekordbox's own export tree — already managed by RB
    ".Trashes",
    ".Spotlight-V100",
    ".fseventsd",
    ".DocumentRevisions-V100",
    ".TemporaryItems",
})


class ExternalDriveWatcher:
    """Polls a watch root and registers new audio files in the Rekordbox XML."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.tag_handler = TagHandler()
        self.writer = RekordboxXMLWriter(config.rekordbox_xml_path)

        self.watch_root: Path = config.external_watch_path
        self.poll_interval: int = config.external_poll_interval
        self.seen_file: Path = config.external_seen_file
        self.skip_dirs: Set[str] = set(_DEFAULT_SKIP_DIRS) | set(
            config.external_skip_dirs
        )
        self.extensions = tuple(e.lower() for e in config.supported_extensions)
        # Anti-flood: if a single scan turns up more than this many "new" files,
        # it's almost certainly a move/reorg (paths are the identity key), not a
        # genuine batch of new tracks. Re-baseline instead of mass-registering.
        # 0 disables the cap.
        self.max_new_per_scan: int = getattr(config, "external_max_new_per_scan", 200)

        self.seen: Set[str] = self._load_seen()
        self._mount_warned = False

    def run_forever(self) -> None:
        if not self.writer.enabled:
            self.logger.error(
                "rekordbox XML disabled (no rekordbox_xml_path or pyrekordbox missing); "
                "watcher exiting"
            )
            return

        self.logger.info(
            f"watching {self.watch_root} every {self.poll_interval}s "
            f"(skip dirs: {sorted(self.skip_dirs)})"
        )

        while True:
            try:
                self._scan_once()
            except Exception as e:
                self.logger.error(f"scan iteration failed: {e}", exc_info=True)
            time.sleep(self.poll_interval)

    def _scan_once(self) -> None:
        if not self.watch_root.exists():
            if not self._mount_warned:
                self.logger.info(
                    f"drive not mounted at {self.watch_root}; will retry"
                )
                self._mount_warned = True
            return

        if self._mount_warned:
            self.logger.info(f"drive remounted at {self.watch_root}; resuming")
            self._mount_warned = False

        baseline = not self.seen_file.exists()
        if baseline:
            self.logger.info(
                "first scan: baselining existing files "
                "(they will NOT be registered in the XML)"
            )

        # Collect everything not already seen, then decide in bulk. Deciding
        # after counting is what lets the safety valve catch a reorg before it
        # registers thousands of moved files.
        unseen = [p for p in self._iter_audio_files(self.watch_root) if str(p) not in self.seen]
        if not unseen:
            return

        # First-run baseline, or a suspiciously large batch (move/reorg): record
        # the files as seen WITHOUT registering them in the XML.
        over_cap = self.max_new_per_scan and len(unseen) > self.max_new_per_scan
        if baseline or over_cap:
            if over_cap and not baseline:
                self.logger.warning(
                    f"{len(unseen)} new files exceeds the safety cap of "
                    f"{self.max_new_per_scan}; treating as a re-baseline and NOT "
                    f"registering them. This usually means files were moved or "
                    f"reorganised under {self.watch_root} (paths are the identity "
                    f"key). Adjust external_max_new_per_scan if this was intentional."
                )
            for path in unseen:
                self.seen.add(str(path))
            self._persist_seen()
            self.logger.info(f"baseline: {len(unseen)} file(s) recorded (not registered)")
            return

        registered = 0
        for path in unseen:
            try:
                self._register_one(path)
                self.seen.add(str(path))
                registered += 1
            except Exception as e:
                self.logger.error(f"failed on {path}: {e}", exc_info=False)

        if registered > 0:
            self.logger.info(f"registered {registered} new track(s)")
            self._persist_seen()

    def _iter_audio_files(self, root: Path) -> Iterable[Path]:
        """Yield audio files under root, pruning skip-dirs and dot-dirs."""
        # Manual walk with pruning — Path.rglob has no skip-dir support.
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                with __import__("os").scandir(current) as it:
                    for entry in it:
                        try:
                            name = entry.name
                            if entry.is_dir(follow_symlinks=False):
                                if name in self.skip_dirs or name.startswith("."):
                                    continue
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                if name.startswith("."):
                                    continue
                                lower = name.lower()
                                if any(lower.endswith(ext) for ext in self.extensions):
                                    yield Path(entry.path)
                        except OSError:
                            continue
            except (FileNotFoundError, PermissionError, OSError) as e:
                self.logger.debug(f"scandir failed on {current}: {e}")
                continue

    def _register_one(self, path: Path) -> None:
        artist = title = None
        bpm = None
        try:
            artist, title, bpm = self.tag_handler.get_tags(path)
        except Exception as e:
            self.logger.warning(
                f"tag read failed for {path.name}; registering with filename only: {e}"
            )
        self.writer.register(path, artist, title, bpm)

    def _load_seen(self) -> Set[str]:
        if not self.seen_file.exists():
            return set()
        try:
            with self.seen_file.open("r", encoding="utf-8") as f:
                return {line.rstrip("\n") for line in f if line.rstrip("\n")}
        except Exception as e:
            self.logger.error(
                f"failed to load seen file {self.seen_file}: {e}; "
                f"treating as empty (baseline pass will run)"
            )
            return set()

    def _persist_seen(self) -> None:
        try:
            self.seen_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.seen_file.with_suffix(self.seen_file.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                for entry in sorted(self.seen):
                    f.write(entry)
                    f.write("\n")
            tmp.replace(self.seen_file)
        except Exception as e:
            self.logger.error(f"failed to persist seen file: {e}", exc_info=True)
