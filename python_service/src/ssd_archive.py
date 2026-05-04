"""Move processed tracks to an external SSD when the volume is mounted.

If the SSD is not mounted, or any step of the move fails, the source path
is returned unchanged so the audio pipeline degrades gracefully to keeping
files on the local disk. The pipeline must NEVER fail because of SSD I/O.
"""

import shutil
from pathlib import Path
from typing import Optional

from .logger import get_logger


_VOLUMES = Path("/Volumes")


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
        return self._mount_root is not None and self._mount_root.exists()

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
