#!/usr/bin/env python3
"""Entry point for the external-drive Rekordbox XML sync watcher.

Run via launchd (com.macmini.rekordbox-sync) or directly:
    .venv/bin/python rekordbox_watch.py
    .venv/bin/python rekordbox_watch.py --once   # single scan, no loop
"""

import argparse
import sys
from pathlib import Path

# Make `src` importable when launched from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import Config
from src.logger import setup_logger
from src.rekordbox_watcher import ExternalDriveWatcher


def main() -> int:
    parser = argparse.ArgumentParser(description="Rekordbox XML sync watcher for external drive")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent / config_path

    config = Config(str(config_path))

    # Dedicated log file so watcher logs don't interleave with the MP3 service.
    log_path = Path(__file__).resolve().parent / "rekordbox_sync.log"
    setup_logger("src", log_file=log_path, level=config.log_level)
    logger = setup_logger(__name__, log_file=log_path, level=config.log_level)

    if config.rekordbox_xml_path is None:
        logger.error("rekordbox_xml_path not configured; nothing to do")
        return 2

    watcher = ExternalDriveWatcher(config)

    if args.once:
        logger.info("running single scan (--once)")
        watcher._scan_once()
        return 0

    watcher.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
