# MP3 Service

Automated audio processor for a DJ workflow on macOS. Watches a source folder (Soulseek downloads), cleans tags and filenames, detects BPM, filters by BPM range, converts FLAC → AIFF (16-bit/44.1kHz for Pioneer XDJ), and moves processed files to a destination folder.

## Install

Requires Python 3.12, Homebrew ffmpeg.

```bash
brew install ffmpeg
cd python_service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json   # then edit paths
```

## Run

```bash
python main.py validate            # check config
python main.py start --dry-run     # preview without touching files
python main.py start --watch       # run with real-time file watcher
python health_check.py             # diagnostics
```

## Configuration

Edit `config.json`. Key fields:

| field | meaning |
|---|---|
| `base_path` | source folder to watch |
| `local_path` | destination for processed files |
| `supported_extensions` | audio types to process |
| `bpm_range` | `{min, max}` — tracks outside this range are skipped |
| `backup_before_delete` | `true` → move originals to `backup_path` instead of deleting |
| `backup_path` | required if `backup_before_delete: true` |
| `poll_interval` | seconds between scans in polling mode |

## Run as a background service (launchd)

Plist at `~/Library/LaunchAgents/com.macmini.mp3service.plist` runs `main.py start --watch` at login and restarts on crash.

Shell aliases (in `~/.zshrc`):

| alias | action |
|---|---|
| `mp3start` / `mp3stop` / `mp3restart` | control the agent |
| `mp3status` | launchctl status |
| `mp3log` | tail the service log |
| `mp3errors` | tail launchd stderr |
| `mp3health` | run `health_check.py` |
| `mp3process` / `mp3dry` | one-shot process / dry-run |

## Safety

Directory cleanup (removing non-audio files from subdirectories of `base_path`) only runs if a marker file `.mp3-service-managed` exists at `base_path`. Create it once to opt in:

```bash
touch "$(jq -r .base_path config.json)/.mp3-service-managed"
```

Without the marker, processing runs normally but no cleanup happens — a safeguard against a misconfigured `base_path`.

## Layout

```
python_service/
├── main.py            # CLI entry
├── health_check.py    # diagnostics
├── setup.py           # interactive first-time setup (optional)
├── config.json        # local config (gitignored)
├── config.example.json
├── requirements.txt
└── src/
    ├── processor.py      # main pipeline + ffmpeg FLAC→AIFF
    ├── tag_handler.py    # mutagen read/write (MP3/AIFF/M4A/FLAC)
    ├── bpm_detector.py   # librosa tempo detection
    ├── file_handler.py   # copy/move/delete, filename cleaning
    ├── watcher.py        # watchdog real-time file events
    ├── config.py         # JSON config loader
    ├── cli.py            # init/validate/test/status commands
    └── logger.py
```
