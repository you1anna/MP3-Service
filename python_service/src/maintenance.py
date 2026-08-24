"""Periodic maintenance for watch mode.

The file watcher only reacts to new filesystem events, so work deferred by an
SSD outage has no way to resume on its own: a converted AIFF sits in local
staging waiting for the archive hop, and the source file it came from stays
put until that hop is confirmed. Neither will ever emit another watchdog
event, so before this existed they sat there until the service was restarted.

This scheduler closes that gap on three levels, cheapest first:

  1. every tick  - reconcile local staging onto the SSD (the existing sweep)
  2. on remount  - full source rescan, because that is when deferred work
                   becomes doable again
  3. infrequently - full source rescan as a catch-all for anything the
                   watcher missed for reasons unrelated to the SSD
"""

import time
from typing import Callable

from .logger import get_logger


class MaintenanceScheduler:
    """Runs the periodic self-healing work for a watching service.

    Call tick() on the service's poll interval; the scheduler owns all
    decisions about what that tick should actually do.
    """

    def __init__(self, config, processor, clock: Callable[[], float] = time.monotonic):
        self.config = config
        self.processor = processor
        self.logger = get_logger(__name__)
        self._clock = clock
        self._ssd_was_mounted = processor.ssd_archiver.mounted
        self._last_sweep = clock()

    def tick(self) -> None:
        """Run one maintenance step. Never raises."""
        if self._handle_ssd_transition():
            return

        if self._ssd_was_mounted:
            self.processor.ssd_archiver.reconcile(self.config.local_path)

        if self._clock() - self._last_sweep >= self.config.sweep_interval:
            self.logger.info("Periodic sweep: rescanning source directory")
            self._rescan()

    def _handle_ssd_transition(self) -> bool:
        """Act on a change in SSD mount state. Returns True if it rescanned."""
        mounted = self.processor.ssd_archiver.mounted
        was_mounted = self._ssd_was_mounted
        self._ssd_was_mounted = mounted

        if mounted and not was_mounted:
            self.logger.info(
                "SSD reconnected; rescanning source directory for deferred files"
            )
            # Files that failed only because the SSD was gone have burned
            # retry attempts they should not be charged for.
            self.processor.reset_retry_state()
            self._rescan()
            return True

        if was_mounted and not mounted:
            self.logger.warning(
                "SSD disconnected; new output will be held back until it returns"
            )

        return False

    def _rescan(self) -> None:
        """Full source-directory pass, isolated from the caller's control flow."""
        self._last_sweep = self._clock()
        try:
            stats = self.processor.process_all()
        except Exception as e:
            self.logger.error(f"Error during source rescan: {e}", exc_info=True)
            return

        if stats.get('processed') or stats.get('errors'):
            self.logger.info(
                f"Rescan: Processed={stats.get('processed', 0)}, "
                f"Errors={stats.get('errors', 0)}, "
                f"Skipped={stats.get('skipped', 0)}"
            )
