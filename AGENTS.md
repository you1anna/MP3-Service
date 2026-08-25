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

- `main.py` — CLI (start, process, test, validate, status, doctor, init)
- `src/processor.py` — core logic: FLAC conversion, BPM detection, routing
- `src/watcher.py` — watchdog real-time file watching

## FLAC→AIFF invariants

- Output: 16-bit / 44.1 kHz
- `keep_flac_sources` (default `true`) decides whether the source FLAC is deleted once its AIFF
  reaches its final destination. It is **independent of `ssd_archive_path`** — a drive that is
  merely unplugged must never change whether lossless originals are destroyed. Two code paths
  delete (`_process_flac` and `_cleanup_previously_processed_source`); both are gated
- If the SSD is absent: the AIFF stays in `local_path` and the source is left alone. The output is
  never discarded — `maintenance.py` reconciles it onto the drive when it reconnects
- Config paths expand `~` and `$VARS`

## Two machines

`config.json` is gitignored, so each host carries its own and `git pull` does not carry new keys
across. Run `python3 main.py doctor` on a machine to see how it resolves its config; the same report
goes to the log at every service start. See `CLAUDE.md` for the per-machine table.

## Testing

```sh
cd python_service && source .venv/bin/activate
python3 main.py doctor              # machine-resolved config report
python3 main.py process --dry-run   # safe test
.venv/bin/python -m unittest discover -s tests
```
