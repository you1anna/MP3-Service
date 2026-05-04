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
- `src/config.py` — JSON config loader
- `src/cli.py` — CLI argument parsing
- `src/logger.py` — Logging setup
- `health_check.py` — Service health check endpoint

## Custom modifications (vs upstream)
- FLAC→AIFF (16-bit/44.1kHz) conversion added to processor.py
- BPM detection on all formats (was MP3-only)
- BPM detection bounds: 65-135 (librosa range; not a filter — no files are skipped)
- numpy array fix for librosa 0.11+ (`float(tempo[0])`)

## Testing
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
- Source: `/Users/macmini/Soulseek Downloads/complete`
- Destination: `/Users/macmini/Music/Processed`
