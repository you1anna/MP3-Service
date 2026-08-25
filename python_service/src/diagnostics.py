"""Report how the service resolves on the machine it is actually running on.

The same code runs on two hosts with deliberately different config.json
files (config.json is gitignored, so nothing keeps them in step). Almost
every behavioural difference between them - whether output is staged or
archived, whether lossless sources are kept, which drive is watched -
follows from config, so the only honest way to answer "does it work on
that machine?" is to have the machine answer for itself.

`main.py doctor` prints this; startup logs the same lines, so a log file
from either host records which branch it took.
"""

import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import List, Tuple

# level, message. Levels: 'ok', 'info', 'warn', 'fail'
Finding = Tuple[str, str]

MARKER_FILENAME = ".mp3-service-managed"


def _dir_finding(label: str, path: Path, required: bool) -> Finding:
    if path.exists():
        return ("ok", f"{label}: {path}")
    level = "fail" if required else "warn"
    suffix = "" if required else " (will be created)"
    return (level, f"{label} does not exist: {path}{suffix}")


def machine_report(config) -> List[Finding]:
    """Collect every machine-dependent fact the service's behaviour turns on."""
    findings: List[Finding] = []

    findings.append(("info", f"Host: {_host_label()}"))
    findings.append(("info", f"Config: {Path(config.config_path).resolve()}"))

    # --- Paths -------------------------------------------------------
    findings.append(_dir_finding("Source", config.base_path, required=True))
    findings.append(_dir_finding("Local output", config.local_path, required=False))

    marker = config.base_path / MARKER_FILENAME
    if marker.exists():
        findings.append(("ok", f"Cleanup marker present: {marker}"))
    else:
        findings.append((
            "warn",
            f"Cleanup marker missing, empty-directory cleanup is disabled. "
            f"Enable with: touch '{marker}'",
        ))

    # --- The one setting that can destroy data ------------------------
    if config.keep_flac_sources:
        findings.append((
            "ok",
            "FLAC sources: KEPT after conversion (keep_flac_sources=true)",
        ))
    else:
        findings.append((
            "info",
            "FLAC sources: DELETED once the AIFF reaches its final destination "
            "(keep_flac_sources=false)",
        ))

    if config.deletes_flac_sources_without_an_archive:
        findings.append((
            "fail",
            "keep_flac_sources=false with no ssd_archive_path: source FLACs will be "
            "deleted with nowhere archiving the output. Set keep_flac_sources=true "
            "on a machine with no archive drive.",
        ))

    # --- SSD archive --------------------------------------------------
    archive = config.ssd_archive_path
    if archive is None:
        findings.append((
            "info",
            "SSD archive: not configured; local output is the final destination",
        ))
    else:
        mount_root = _mount_root(archive)
        if mount_root is None:
            findings.append((
                "fail",
                f"SSD archive {archive} is not under /Volumes/<drive>, so mount state "
                "cannot be checked and archiving will never run",
            ))
        elif os.path.ismount(mount_root):
            findings.append(("ok", f"SSD archive mounted: {archive}"))
        else:
            staged = _staged_count(config.local_path)
            findings.append((
                "warn",
                f"SSD archive configured but {mount_root} is not mounted; "
                f"{staged} file(s) waiting in local staging for it to return",
            ))

    # --- Rekordbox ----------------------------------------------------
    xml = config.rekordbox_xml_path
    if xml is None:
        findings.append(("info", "Rekordbox XML: disabled"))
    else:
        findings.append(_dir_finding("Rekordbox XML", xml, required=False))

    # --- External drive watcher ---------------------------------------
    watch = config.external_watch_path
    watch_root = _mount_root(watch)
    if watch_root is not None and not os.path.ismount(watch_root):
        findings.append((
            "info",
            f"External watcher: {watch} not mounted; scanner idle on this machine",
        ))
    else:
        findings.append(("ok", f"External watcher: {watch}"))
        if watch_root is not None and watch.resolve() == watch_root.resolve():
            findings.append((
                "warn",
                f"External watcher points at the whole of {watch_root}, not a track "
                "directory. If that drive holds a sample library, every one-shot on it "
                "is a candidate for the Rekordbox XML.",
            ))

    # --- Tooling ------------------------------------------------------
    if shutil.which("ffmpeg"):
        findings.append(("ok", "ffmpeg: found on PATH"))
    else:
        findings.append(("fail", "ffmpeg not found on PATH; FLAC conversion will fail"))

    return findings


def _host_label() -> str:
    """A name a human recognises.

    socket.gethostname() returns whatever DHCP handed out - often the IP -
    which is useless in a report whose whole job is telling the two machines
    apart. LocalHostName is the one the user actually named the Mac.
    """
    try:
        name = subprocess.run(
            # Absolute path: launchd's PATH does not include /usr/sbin, so a
            # bare "scutil" silently falls back to the DHCP name in the one
            # place this report matters most - the service log.
            ["/usr/sbin/scutil", "--get", "LocalHostName"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if name:
            return name
    except (OSError, subprocess.SubprocessError):
        pass
    return socket.gethostname()


def _mount_root(path: Path):
    """Return /Volumes/<drive> for a path under /Volumes, else None."""
    volumes = Path("/Volumes")
    for ancestor in [path, *path.parents]:
        if ancestor.parent == volumes:
            return ancestor
    return None


def _staged_count(local_path: Path) -> int:
    try:
        return sum(
            1 for p in local_path.iterdir()
            if p.is_file() and not p.name.startswith(".")
        )
    except OSError:
        return 0
