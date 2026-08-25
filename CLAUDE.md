# MP3-Service

Audio file processor for DJ workflow. Watches Soulseek downloads, processes to Pioneer XDJ-compatible formats.

## Setup
- Venv: `python_service/.venv` (Python 3.12)
- Config: `python_service/config.json` (local only, not in git)
- Activate: `cd python_service && source .venv/bin/activate`

## Architecture
- `main.py` — CLI entry point (start, process, test, validate, status, init)
- `src/processor.py` — Core logic: FLAC conversion, BPM detection, file routing
- `src/tag_handler.py` — mutagen-based tag read/write (MP3, AIFF, M4A, FLAC)
- `src/bpm_detector.py` — librosa BPM detection (all formats)
- `src/file_handler.py` — File operations, filename cleaning, copiedList.txt
- `src/watcher.py` — watchdog real-time file watching
- `src/ssd_archive.py` — optional move from local staging to external SSD
- `src/rekordbox_xml.py` / `src/rekordbox_watcher.py` — Rekordbox XML feed and external-drive scanner
- `src/config.py` — JSON config loader
- `src/cli.py` — CLI argument parsing
- `src/logger.py` — Logging setup
- `health_check.py` — Service health check endpoint

## Custom modifications (vs upstream)
- FLAC→AIFF (16-bit/44.1kHz) conversion added to processor.py
- `keep_flac_sources` (default **true**) decides whether a source FLAC is deleted once its AIFF reaches its final destination. It is deliberately independent of `ssd_archive_path`: an SSD that is merely unplugged must never change whether lossless originals are destroyed. Set `false` only on a machine whose archive path is a real archive drive
- FLAC→AIFF conversion never discards its own output. If the SSD is absent the AIFF stays in `local_path` and `reconcile()` moves it across when the drive returns
- Source files already in copiedList (any format) are cleaned up only when the matching output exists in the configured final destination — except FLACs on a `keep_flac_sources` machine, which are exempt entirely. That cleanup route deletes with no conversion involved, so it needs its own gate
- Config paths support `~` and `$VARS` (`src/config.py:expand_path`), so one config shape works on both hosts instead of hard-coding a home directory
- `src/maintenance.py` self-heals watch mode: staging reconcile each poll tick, a full source rescan on SSD remount, and an infrequent sweep (`sweep_interval`, default 900s) as a catch-all. Files that keep failing are parked after `AudioProcessor.MAX_RETRY_ATTEMPTS` (3) and un-parked on remount or restart
- SSD mount detection uses `os.path.ismount`, not `exists()` — a stale `/Volumes/<drive>` directory must not be treated as mounted
- BPM detection on all formats (was MP3-only)
- BPM detection bounds: 65-135 (librosa range; not a filter — no files are skipped)
- numpy array fix for librosa 0.11+ (`float(tempo[0])`)

## Two machines
`config.json` is gitignored, so the Mac mini and the MacBook Air each carry their own and `git pull` does **not** carry new keys across. Run `python3 main.py doctor` on a machine to see how it resolves its config and what that implies (paths, SSD mount state, FLAC retention, marker file, ffmpeg). The same report is written to the log at every service start.

| | Mac mini | MacBook Air |
|---|---|---|
| `ssd_archive_path` | `/Volumes/Extreme SSD/music` | same, but the drive is not attached |
| `keep_flac_sources` | `false` — archive drive is the backstop | `true` — the source FLAC is the only lossless copy |
| `local_path` role | staging, swept onto the SSD | final destination |

## Testing
- `python3 main.py doctor` — machine-resolved config report
- `python3 main.py process --dry-run` — safe test run
- `python3 main.py test` — run test suite
- Delete `copiedList.txt` to reprocess all files

## Service
- launchd: `com.macmini.mp3service`
- Plist: `~/Library/LaunchAgents/com.macmini.mp3service.plist`
- Log: `mp3_service.log`
- Errors: `launchd_stderr.log`
- Config: `poll_interval` 40s, `file_stability_wait` 5s

## Paths
- Source: `~/Soulseek Downloads/complete`
- Local staging: `~/Music/Processed`
- SSD archive destination: `/Volumes/Extreme SSD/music` (Mac mini; absent on the Air)
