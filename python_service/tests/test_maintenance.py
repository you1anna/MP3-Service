import unittest
from types import SimpleNamespace

from src.maintenance import MaintenanceScheduler


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeProcessor:
    def __init__(self, mounted: bool):
        self.ssd_archiver = SimpleNamespace(
            mounted=mounted,
            reconcile=lambda local_path: self.reconciles.append(local_path) or 0,
        )
        self.reconciles = []
        self.scans = 0
        self.retry_resets = 0

    def process_all(self):
        self.scans += 1
        return {'processed': 0, 'errors': 0, 'skipped': 0}

    def reset_retry_state(self):
        self.retry_resets += 1


class DummyConfig:
    local_path = "/tmp/processed"
    sweep_interval = 900


class MaintenanceSchedulerTests(unittest.TestCase):
    def _scheduler(self, mounted: bool):
        clock = FakeClock()
        processor = FakeProcessor(mounted=mounted)
        scheduler = MaintenanceScheduler(DummyConfig(), processor, clock=clock)
        return scheduler, processor, clock

    def test_steady_state_only_reconciles_staging(self):
        scheduler, processor, _ = self._scheduler(mounted=True)

        scheduler.tick()
        scheduler.tick()

        self.assertEqual(processor.scans, 0)
        self.assertEqual(len(processor.reconciles), 2)

    def test_remount_triggers_full_rescan_and_clears_retry_state(self):
        scheduler, processor, _ = self._scheduler(mounted=False)

        scheduler.tick()
        self.assertEqual(processor.scans, 0)

        processor.ssd_archiver.mounted = True
        scheduler.tick()

        self.assertEqual(processor.scans, 1)
        self.assertEqual(processor.retry_resets, 1)

    def test_remount_rescan_happens_once_not_on_every_later_tick(self):
        scheduler, processor, _ = self._scheduler(mounted=False)

        processor.ssd_archiver.mounted = True
        scheduler.tick()
        scheduler.tick()
        scheduler.tick()

        self.assertEqual(processor.scans, 1)

    def test_unmount_does_not_rescan_or_reconcile(self):
        scheduler, processor, _ = self._scheduler(mounted=True)

        processor.ssd_archiver.mounted = False
        scheduler.tick()

        self.assertEqual(processor.scans, 0)
        self.assertEqual(processor.reconciles, [])

    def test_sweep_runs_only_after_sweep_interval_elapses(self):
        scheduler, processor, clock = self._scheduler(mounted=True)

        clock.advance(899)
        scheduler.tick()
        self.assertEqual(processor.scans, 0)

        clock.advance(2)
        scheduler.tick()
        self.assertEqual(processor.scans, 1)

    def test_remount_rescan_resets_the_sweep_timer(self):
        scheduler, processor, clock = self._scheduler(mounted=False)

        clock.advance(899)
        processor.ssd_archiver.mounted = True
        scheduler.tick()
        self.assertEqual(processor.scans, 1)  # remount rescan

        clock.advance(2)
        scheduler.tick()
        self.assertEqual(processor.scans, 1)  # sweep timer restarted, no extra scan

        clock.advance(900)
        scheduler.tick()
        self.assertEqual(processor.scans, 2)

    def test_scan_failure_does_not_break_the_loop(self):
        scheduler, processor, clock = self._scheduler(mounted=True)

        def boom():
            raise OSError("SSD vanished mid-scan")

        processor.process_all = boom
        clock.advance(901)

        scheduler.tick()  # must not raise

        clock.advance(901)
        scheduler.tick()


if __name__ == "__main__":
    unittest.main()
