"""Register processed tracks in a Rekordbox-compatible XML library file.

Rekordbox XML is a one-way bridge: this module appends entries to an XML
file, and Rekordbox reads it when configured via Preferences > Advanced >
rekordbox xml. We never write to master.db — that path can corrupt the
library on schema drift between Rekordbox versions.

Failures here must NEVER fail the audio pipeline. All errors are logged
and swallowed.
"""

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .logger import get_logger

try:
    from pyrekordbox.rbxml import RekordboxXml
    _PYREKORDBOX_OK = True
except ImportError:
    _PYREKORDBOX_OK = False
    RekordboxXml = None  # type: ignore[assignment,misc]


PLAYLIST_NAME = "mp3service"


_KIND_BY_EXT = {
    ".aiff": "AIFF File",
    ".aif": "AIFF File",
    ".mp3": "MP3 File",
    ".m4a": "M4A File",
    ".wav": "WAV File",
    ".flac": "FLAC File",
}


class RekordboxXMLWriter:
    """Append tracks to a Rekordbox-importable XML, idempotent + atomic.

    Disabled when xml_path is None or pyrekordbox is not installed.
    """

    def __init__(self, xml_path: Optional[Path]):
        self.xml_path: Optional[Path] = Path(xml_path) if xml_path else None
        self.logger = get_logger(__name__)
        self._import_warning_emitted = False

    @property
    def enabled(self) -> bool:
        if self.xml_path is None:
            return False
        if not _PYREKORDBOX_OK:
            if not self._import_warning_emitted:
                self.logger.warning(
                    "rekordbox_xml: pyrekordbox not installed; sync disabled "
                    "(pip install pyrekordbox)"
                )
                self._import_warning_emitted = True
            return False
        return True

    def register(
        self,
        audio_path: Path,
        artist: Optional[str],
        title: Optional[str],
        bpm: Optional[int],
    ) -> None:
        """Add the track to the XML if not already present. Never raises."""
        if not self.enabled:
            return

        try:
            audio_path = audio_path.resolve(strict=True)
        except (FileNotFoundError, OSError) as e:
            self.logger.warning(
                f"rekordbox_xml: skip (file unreadable) {audio_path}: {e}"
            )
            return

        try:
            with self._lock():
                xml = self._load_or_init()
                if xml is None:
                    return

                newly_added = False
                if not self._already_registered(xml, audio_path):
                    kind = _KIND_BY_EXT.get(
                        audio_path.suffix.lower(), "Audio File"
                    )
                    kwargs = {
                        "Name": title or audio_path.stem,
                        "Artist": artist or "",
                        "Kind": kind,
                        # pyrekordbox 0.4.4 resets _last_id=0 on reload, which
                        # would clash with existing IDs; assign explicitly.
                        "TrackID": (max(xml._ids) + 1) if xml._ids else 1,
                    }
                    if bpm:
                        kwargs["AverageBpm"] = float(bpm)

                    xml.add_track(str(audio_path), **kwargs)
                    newly_added = True

                # Adding to the COLLECTION is not enough — Rekordbox only shows
                # a playlist when the XML defines one. Keep the mp3service
                # playlist in sync with the collection (also backfills tracks
                # registered before playlist support existed).
                playlist_changed = self._sync_playlist(xml)

                if newly_added or playlist_changed:
                    self._atomic_write(xml)

                if newly_added:
                    self.logger.info(
                        f"rekordbox_xml: registered {audio_path.name}"
                    )
                elif playlist_changed:
                    self.logger.info(
                        f"rekordbox_xml: backfilled playlist "
                        f"'{PLAYLIST_NAME}' ({audio_path.name} already "
                        f"in collection)"
                    )
                else:
                    self.logger.debug(
                        f"rekordbox_xml: already registered: {audio_path.name}"
                    )
        except Exception as e:
            self.logger.error(
                f"rekordbox_xml: failed to register {audio_path.name}: {e}",
                exc_info=True,
            )

    @contextmanager
    def _lock(self):
        """Cross-process advisory lock so manual CLI runs don't race the service."""
        assert self.xml_path is not None
        lock_path = self.xml_path.with_suffix(self.xml_path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _load_or_init(self) -> Optional["RekordboxXml"]:
        assert self.xml_path is not None
        if not self.xml_path.exists():
            self.xml_path.parent.mkdir(parents=True, exist_ok=True)
            return RekordboxXml(
                name="MP3-Service", version="1.0.0", company="macmini"
            )
        try:
            return RekordboxXml(self.xml_path)
        except Exception as e:
            self.logger.error(
                f"rekordbox_xml: existing XML at {self.xml_path} is "
                f"unparseable ({e}). Refusing to overwrite. "
                f"Inspect or move it aside, then re-run."
            )
            return None

    @staticmethod
    def _already_registered(xml: "RekordboxXml", audio_path: Path) -> bool:
        target = str(audio_path)
        for track in xml.get_tracks():
            try:
                if track["Location"] == target:
                    return True
            except Exception:
                continue
        return False

    def _sync_playlist(self, xml: "RekordboxXml") -> bool:
        """Ensure the mp3service playlist mirrors every collection track.

        This XML is written solely by MP3-Service, so the playlist should
        contain all collection tracks. Idempotent; returns True if the tree
        was modified (playlist created and/or tracks appended).

        Node.get_playlist() side-effects a stray empty NODE when the name is
        missing, so we enumerate the root's children by name instead.
        """
        root = xml.get_playlist()  # no names -> root node, no side effects
        playlist = None
        for node in root.get_playlists():
            try:
                if node.is_playlist and node.name == PLAYLIST_NAME:
                    playlist = node
                    break
            except ValueError:
                continue

        changed = False
        if playlist is None:
            playlist = xml.add_playlist(PLAYLIST_NAME, keytype="TrackID")
            changed = True

        existing = set()
        for key in playlist.get_tracks():
            try:
                existing.add(int(key))
            except (TypeError, ValueError):
                existing.add(key)

        for track in xml.get_tracks():
            tid = int(track["TrackID"])
            if tid not in existing:
                playlist.add_track(tid)
                existing.add(tid)
                changed = True
        return changed

    def _atomic_write(self, xml: "RekordboxXml") -> None:
        assert self.xml_path is not None
        tmp = self.xml_path.with_suffix(self.xml_path.suffix + ".tmp")
        xml.save(path=tmp)
        tmp.replace(self.xml_path)
