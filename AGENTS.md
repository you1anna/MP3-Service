# MP3 Service — Agent Instructions

Audio file processor for DJ workflow. Watches Soulseek downloads, processes to Pioneer XDJ-compatible formats.

See `CLAUDE.md` for full architecture detail.

## Key facts

- Canonical path: `/Users/macbookair/Dev/MP3-Service/python_service`
- Stale duplicate at `~/MP3-Service` — ignore it
- Venv: `python_service/.venv` (Python 3.12)
- Config: `python_service/config.json` (local only, not in git)
- launchd service: `com.macmini.mp3service`

## Entry points

- `main.py` — CLI (start, process, test, validate, status, init)
- `src/processor.py` — core logic: FLAC conversion, BPM detection, routing
- `src/watcher.py` — watchdog real-time file watching

## FLAC→AIFF invariants

- Output: 16-bit / 44.1 kHz
- FLAC originals deleted only after AIFF is confirmed in final destination
- If SSD placement fails: temp AIFF removed, FLAC retained for retry

## Testing

```sh
cd python_service && source .venv/bin/activate
python3 main.py process --dry-run   # safe test
python3 main.py test
```
