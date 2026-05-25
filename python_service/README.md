# MP3 Service

Automated audio processor for a DJ workflow on macOS. Watches a source folder (Soulseek downloads), cleans tags and filenames, detects BPM, converts FLAC → AIFF (16-bit/44.1kHz for Pioneer XDJ), and moves processed files to a destination folder or external SSD.

BPM range settings are detection bounds only. Tracks outside the configured range are not skipped.

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
| `bpm_range` | `{min, max}` — BPM detection bounds; not a processing filter |
| `backup_before_delete` | `true` → move originals to `backup_path` instead of deleting |
| `backup_path` | required if `backup_before_delete: true` |
| `poll_interval` | seconds between scans in polling mode |
| `ssd_archive_path` | optional external SSD destination; processed tracks are moved here when the volume is mounted |
| `rekordbox_xml_path` | optional Rekordbox XML file to append processed tracks to |
| `external_watch_path` | optional external drive root watched by `rekordbox_watch.py` |
| `external_seen_file` | persistent list of external-drive files already scanned |

## External SSD and Rekordbox behavior

The audio pipeline and Rekordbox pipeline are separate:

1. `main.py start --watch` processes Soulseek downloads.
   - MP3/M4A/WAV/AIFF files are cleaned and copied to `local_path`.
   - FLAC files are converted to AIFF in `local_path`; the original FLAC is kept in the Soulseek complete folder.
   - If `ssd_archive_path` is configured and its `/Volumes/<drive>` mount is present, the processed output is moved from `local_path` to the SSD.
   - If the SSD is not mounted, the processed output remains in `local_path` so the audio pipeline does not fail.

2. `rekordbox_watch.py` scans `external_watch_path` and appends new audio files to `rekordbox_xml_path`.
   - The first scan creates a baseline in `external_seen_file` and does not register existing files, to avoid flooding Rekordbox with the existing SSD library.
   - Later files that appear on the SSD are registered in the XML feed.
   - The watcher skips Rekordbox-managed/system folders such as `rekordbox`, `.Trashes`, `.Spotlight-V100`, `$RECYCLE.BIN`, and `System Volume Information`.

Rekordbox does not automatically add XML entries to the main Collection or to playlists. The XML is a one-way import feed. In Rekordbox, configure the same XML path under Preferences → Advanced → rekordbox xml, then open the `rekordbox xml` browser panel and import the desired tracks into the Collection or a playlist.

Example: if `/Volumes/Extreme SSD/music/Hemka - Rich Sex.mp3` exists and appears in `rekordbox-sync.xml`, the service has registered it. Restarting Rekordbox alone will not make it appear in normal playlists; import it from the `rekordbox xml` panel.

## Run as a background service (launchd)

Plist at `~/Library/LaunchAgents/com.macmini.mp3service.plist` runs `main.py start --watch` at login and restarts on crash.

Optional Rekordbox XML sync plist:

```bash
~/Library/LaunchAgents/com.macmini.rekordbox-sync.plist
```

It runs `rekordbox_watch.py`, polling the configured external drive and updating `rekordbox_xml_path`.

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
    ├── ssd_archive.py    # optional move from local_path to external SSD
    ├── rekordbox_xml.py  # append processed tracks to Rekordbox XML
    ├── rekordbox_watcher.py # external-drive scanner for Rekordbox XML
    ├── config.py         # JSON config loader
    ├── cli.py            # init/validate/test/status commands
    └── logger.py
```
