"""Move processed tracks to an external SSD when the volume is mounted.

If the SSD is not mounted, or any step of the move fails, the source path
is returned unchanged so the audio pipeline degrades gracefully to keeping
files on the local disk. The pipeline must NEVER fail because of SSD I/O.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from .logger import get_logger


_VOLUMES = Path("/Volumes")


def _is_mount_point(path: Path) -> bool:
    """True only when path is a real mount point, not just an existing directory.

    macOS can leave a stale /Volumes/<drive> directory behind after an
    ungraceful eject. An exists() check would call that mounted and archive
    tracks onto the boot disk under a path that looks like the SSD.
    """
    try:
        return os.path.ismount(path)
    except OSError:
        return False


class SSDArchiver:
    """Optional sink that moves files to a configured SSD destination."""

    def __init__(self, archive_path: Optional[Path]):
        self.archive_path: Optional[Path] = archive_path
        self.logger = get_logger(__name__)
        self._mount_root: Optional[Path] = self._compute_mount_root(archive_path)

    @staticmethod
    def _compute_mount_root(archive_path: Optional[Path]) -> Optional[Path]:
        """Return /Volumes/<drive> for an archive_path, or None if not under /Volumes."""
        if archive_path is None:
            return None
        for ancestor in [archive_path, *archive_path.parents]:
            if ancestor.parent == _VOLUMES:
                return ancestor
        return None

    @property
    def configured(self) -> bool:
        return self.archive_path is not None and self._mount_root is not None

    @property
    def mounted(self) -> bool:
        return self._mount_root is not None and _is_mount_point(self._mount_root)

    def relocate(self, src: Path) -> Path:
        """Move src to the SSD archive path. Returns final path (src on any failure)."""
        if not self.configured:
            return src
        if not self.mounted:
            self.logger.info(
                f"SSD not mounted ({self._mount_root}); keeping {src.name} locally"
            )
            return src

        try:
            assert self.archive_path is not None  # configured implies set
            self.archive_path.mkdir(parents=True, exist_ok=True)
            target = self.archive_path / src.name
            target = self._uniquify(target)
            # shutil.move handles cross-filesystem (HFS+ -> exFAT) by copy+delete
            shutil.move(str(src), str(target))
            self.logger.info(f"Moved to SSD: {src.name} -> {target}")
            return target
        except Exception as e:
            self.logger.error(
                f"SSD move failed for {src.name}: {e}; keeping locally",
                exc_info=False,
            )
            return src

    def reconcile(self, local_path: Path) -> int:
        """Move any files stranded in local_path onto the SSD, now that it's mounted.

        A file only stays in local_path when relocate() ran while the SSD was
        unmounted. Nothing re-checks that later, so without this, files sit
        in local staging forever even after the SSD reconnects. Returns the
        number of files moved.
        """
        if not self.configured or not self.mounted or not local_path.exists():
            return 0

        moved = 0
        for item in sorted(local_path.iterdir()):
            if not item.is_file() or item.name.startswith('.'):
                continue
            if self.relocate(item) != item:
                moved += 1

        if moved:
            self.logger.info(f"Reconciled {moved} file(s) stranded in local staging onto SSD")

        return moved

    @staticmethod
    def _uniquify(target: Path) -> Path:
        """If target exists, append _1, _2, ... before the extension."""
        if not target.exists():
            return target
        stem, suffix = target.stem, target.suffix
        for i in range(1, 1000):
            candidate = target.with_name(f"{stem}_{i}{suffix}")
            if not candidate.exists():
                return candidate
        return target  # fall through; shutil will overwrite the same name
