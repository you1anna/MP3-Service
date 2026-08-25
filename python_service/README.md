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

`python setup.py` is an interactive alternative. It writes a minimal config — the optional fields
(`ssd_archive_path`, `rekordbox_xml_path`, `sweep_interval`, the `external_*` keys) are left out and
fall back to their defaults; copy them from `config.example.json` if you need them.

## Run

```bash
python main.py validate            # check config
python main.py doctor              # how THIS machine resolves the config
python main.py start --dry-run     # preview without touching files
python main.py start --watch       # run with real-time file watcher
python health_check.py             # diagnostics
```

## Configuration

Edit `config.json`. Paths support `~` and `$VARS`, so the same config shape works on any machine.

| field | meaning |
|---|---|
| `base_path` | source folder to watch |
| `local_path` | destination for processed files |
| `keep_flac_sources` | **default `true`.** Keep the source FLAC after its AIFF reaches its final destination. See below |
| `supported_extensions` | audio types to process |
| `bpm_range` | `{min, max}` — BPM detection bounds; not a processing filter |
| `backup_before_delete` | `true` → move originals to `backup_path` instead of deleting |
| `backup_path` | required if `backup_before_delete: true` |
| `poll_interval` | seconds between scans in polling mode |
| `sweep_interval` | seconds between full source rescans in watch mode (default 900) |
| `log_file` | optional; defaults to `mp3_service.log` beside `config.json` |
| `ssd_archive_path` | optional external SSD destination; processed tracks are moved here when the volume is mounted. Must sit under `/Volumes/<drive>/…` so mount state can be checked |
| `rekordbox_xml_path` | optional Rekordbox XML file to append processed tracks to |
| `external_watch_path` | optional directory watched by `rekordbox_watch.py`. Point it at the track directory (i.e. `ssd_archive_path`), **not** the drive root — a drive that also holds a sample library will sweep tens of thousands of one-shots into Rekordbox |
| `external_seen_file` | persistent list of external-drive files already scanned; defaults beside `config.json` |
| `external_max_new_per_scan` | anti-flood cap; a scan finding more than this re-baselines instead of registering (default 200) |

## Two machines, two configs

`config.json` is gitignored, so each machine carries its own and `git pull` does **not** carry new
keys across. Run `python main.py doctor` on a machine to see how it resolves its config and what that
implies — resolved paths, SSD mount state, FLAC retention, marker file, ffmpeg. The same report is
written to the log at every service start, so a log tells you which branch that host took.

|  | machine with an archive drive | machine without one |
|---|---|---|
| `ssd_archive_path` | set, drive attached | set but absent, or empty |
| `keep_flac_sources` | `false` — the archive drive is the backstop | `true` — the source FLAC is the only lossless copy |
| `local_path` role | staging, swept onto the drive | final destination |

### `keep_flac_sources`

This decides whether the service deletes your lossless originals, and it is deliberately
**independent of `ssd_archive_path`**. A drive that is merely unplugged must never change the answer.

Set it to `false` only on a machine whose archive path is a real archive drive — a 16-bit/44.1kHz
AIFF is not a replacement for a 24-bit/96kHz FLAC. On any other machine leave it `true`, and the
source folder keeps the lossless copy.

## External SSD and Rekordbox behavior

The audio pipeline and Rekordbox pipeline are separate:

1. `main.py start --watch` processes Soulseek downloads.
   - MP3/M4A/WAV/AIFF files are cleaned and copied to `local_path`.
   - FLAC files are converted to AIFF in `local_path`. With `keep_flac_sources: true` (the default) the original stays put; with `false` it is deleted once the AIFF reaches its final destination.
   - Sources already listed in `copiedList.txt` are cleaned up when the matching output exists in the configured final destination. FLACs are exempt from this on a `keep_flac_sources` machine — that route deletes with no conversion involved, so it is gated separately.
   - If `ssd_archive_path` is configured and its `/Volumes/<drive>` mount is present, the processed output is moved from `local_path` to the SSD.
   - If the SSD is absent, the converted AIFF stays in `local_path` and the source is left alone. The output is never discarded: `src/maintenance.py` reconciles staging onto the drive when it reconnects, then the source is cleaned up (if retention is off). An unreachable drive is a deferral, not a failure.
   - For non-FLAC files, if the SSD is not mounted, the processed output remains in `local_path` so the audio pipeline does not fail.

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
├── rekordbox_watch.py # external-drive Rekordbox sync entry point
├── tests/             # unittest suite (no pytest)
└── src/
    ├── processor.py      # main pipeline + ffmpeg FLAC→AIFF
    ├── tag_handler.py    # mutagen read/write (MP3/AIFF/M4A/FLAC)
    ├── bpm_detector.py   # librosa tempo detection
    ├── file_handler.py   # copy/move/delete, filename cleaning
    ├── watcher.py        # watchdog real-time file events
    ├── maintenance.py    # watch-mode self-healing: reconcile, remount rescan, sweep
    ├── ssd_archive.py    # optional move from local_path to external SSD
    ├── diagnostics.py    # machine-resolved config report (doctor + startup log)
    ├── rekordbox_xml.py  # append processed tracks to Rekordbox XML
    ├── rekordbox_watcher.py # external-drive scanner for Rekordbox XML
    ├── config.py         # JSON config loader
    ├── cli.py            # init/validate/test/status/doctor commands
    └── logger.py
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```
