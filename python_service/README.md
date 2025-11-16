# MP3 Service - Audio File Processor

A modern, cross-platform Python service that automatically processes audio files with BPM detection, ID3 tag management, and intelligent file organization.

## ✨ Features

- **🎵 Automatic BPM Detection**: Uses `librosa` to detect tempo/BPM for audio files
- **🏷️ Smart ID3 Tag Management**: Reads and writes artist, title, and BPM metadata
- **🧹 Intelligent Filename Cleaning**: Removes unwanted patterns and formats consistently
- **📁 Multi-Format Support**: MP3, M4A, WAV, AIFF, AIF, and FLAC files
- **🔄 Flexible Monitoring**: Choose between polling or real-time file watching
- **👀 Dry-Run Mode**: Preview changes before committing
- **📊 Statistics Tracking**: See processing results and error counts
- **🌐 Network Share Support**: Optional copying to network destinations
- **⚡ Cross-Platform**: Works on Windows, macOS, and Linux

## 🚀 Quick Start

### Installation

```bash
# Navigate to project directory
cd python_service

# Install dependencies
pip install -r requirements.txt
```

**Note**: A `config.example.json` file is provided as reference. Use `python main.py init` to create your own `config.json`, or copy and customize the example file.

### Basic Usage

```bash
# Create default configuration
python main.py init

# Validate configuration
python main.py validate

# Test without making changes
python main.py start --dry-run

# Start processing
python main.py start
```

## 📋 Command Reference

### `init` - Create Configuration

```bash
python main.py init                    # Create config.json
python main.py init --output custom.json  # Custom location
python main.py init --force            # Overwrite existing
```

### `validate` - Check Configuration

```bash
python main.py validate                # Validate config.json
python main.py validate --config custom.json  # Validate custom config
```

Checks:
- Configuration file syntax
- Required fields present
- Paths exist and are accessible
- Settings within valid ranges

### `test` - Preview Files

```bash
python main.py test                    # Preview what will be processed
python main.py test --config custom.json  # Use custom config
```

Shows:
- Files to be processed
- Current tags
- Output filenames
- No files modified

### `status` - Show Information

```bash
python main.py status                  # Show current status
python main.py status --config custom.json  # Use custom config
```

Displays:
- Configuration summary
- Path accessibility
- File count
- Log file size

### `process` - Process Once

```bash
python main.py process                 # Process files once and exit
python main.py process --dry-run       # Preview without changes
python main.py process --config custom.json  # Use custom config
```

### `start` - Start Service

```bash
python main.py start                   # Start with polling
python main.py start --watch           # Use file watching (recommended)
python main.py start --dry-run         # Preview mode
python main.py start --config custom.json  # Use custom config
```

**Options:**
- `--watch, -w`: Real-time file watching (requires `watchdog`)
- `--dry-run, -d`: Preview changes without modifying files
- `--config, -c`: Specify configuration file path

## ⚙️ Configuration

### config.json Structure

```json
{
  "base_path": "~/Music/Incoming",
  "local_path": "~/Music/Processed",
  "network_path": "",
  "desktop_path": "",
  "poll_interval": 40,
  "include_share": false,
  "supported_extensions": [
    ".mp3", ".m4a", ".wav", ".aif", ".aiff", ".flac"
  ],
  "bpm_range": {
    "min": 65,
    "max": 135
  },
  "log_file": "mp3_service.log",
  "log_level": "INFO"
}
```

### Configuration Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `base_path` | string | Directory to monitor for audio files | `~/Music/Incoming` |
| `local_path` | string | Destination for processed files | `~/Music/Processed` |
| `network_path` | string | Optional network share path | `""` |
| `desktop_path` | string | Optional desktop path | `""` |
| `poll_interval` | integer | Seconds between scans (polling mode) | `40` |
| `include_share` | boolean | Enable network share copying | `false` |
| `supported_extensions` | array | Audio file types to process | See above |
| `bpm_range.min` | integer | Minimum acceptable BPM | `65` |
| `bpm_range.max` | integer | Maximum acceptable BPM | `135` |
| `log_file` | string | Path to log file | `mp3_service.log` |
| `log_level` | string | DEBUG, INFO, WARNING, ERROR | `INFO` |

## 🔍 How It Works

### Processing Pipeline

1. **Discovery**: Monitors `base_path` for audio files
2. **Tag Reading**: Extracts existing ID3 tags (artist, title, BPM)
3. **BPM Detection**: Analyzes audio for tempo if missing (MP3 only, skipped in dry-run)
4. **Tag Extraction**: Gets metadata from filename if tags missing (format: "Artist - Title")
5. **Filename Cleaning**: Applies regex patterns to clean filename
6. **Validation**: Ensures BPM is within configured range
7. **Processing**: Copies to `local_path` with cleaned filename
8. **Network Share**: Optionally copies to network location
9. **Cleanup**: Removes empty directories and source files

### Filename Cleaning Rules

Automatically removes/fixes:
- Double dashes (`--`) → single dash with spaces (` - `)
- Multiple underscores → spaces
- Leading track numbers (e.g., `01`, `A1`)
- Website patterns (e.g., `www.site.com`)
- Release group tags
- Converts to Title Case

**Example:**
```
01_artist_name--track_title_www.site.com.mp3
→
Artist Name - Track Title.mp3
```

### BPM Detection

- Uses `librosa.beat.beat_track()` for accurate tempo detection
- Analyzes first 2 minutes of audio
- Auto-corrects double/half-time detection
- Only updates tags if BPM is within configured range (65-135 by default)
- Skipped in dry-run mode for performance

## 📊 Statistics

After processing, view statistics:
- **Processed**: Files successfully handled
- **Errors**: Files that encountered errors
- **Skipped**: Previously processed files

## 🔧 Advanced Usage

### Dry-Run Mode (Recommended First Use)

Always test with dry-run before processing real files:

```bash
# Preview what will happen
python main.py start --dry-run

# Review the log output
# When satisfied, run without --dry-run
python main.py start
```

Dry-run mode:
- ✅ Shows all processing decisions
- ✅ Displays output filenames
- ✅ Reads tags
- ❌ Doesn't modify files
- ❌ Doesn't copy files
- ❌ Skips BPM detection (for speed)

### File Watching vs Polling

**File Watching** (Recommended):
```bash
python main.py start --watch
```
- ✅ Real-time processing
- ✅ Lower CPU usage
- ✅ Instant response to new files
- Requires `watchdog` library

**Polling**:
```bash
python main.py start
```
- ✅ Simple and reliable
- ✅ Works everywhere
- ⚠️ Periodic scanning (configurable interval)
- ⚠️ Slight delay before processing

### Custom Configuration

```bash
# Create custom config
python main.py init --output ~/my-config.json

# Edit the file
nano ~/my-config.json

# Use it
python main.py start --config ~/my-config.json
```

### Multiple Instances

Run multiple instances with different configurations:

```bash
# Terminal 1: Process music downloads
python main.py start --config ~/music-config.json

# Terminal 2: Process DJ drops
python main.py start --config ~/dj-config.json --watch
```

## 🗂️ Project Structure

```
python_service/
├── main.py              # CLI entry point
├── config.example.json  # Example configuration (copy to config.json)
├── requirements.txt     # Python dependencies
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLI commands (init, validate, test, status)
│   ├── config.py        # Configuration management
│   ├── processor.py     # Main processing logic
│   ├── tag_handler.py   # ID3 tag operations
│   ├── file_handler.py  # File operations & cleaning
│   ├── bpm_detector.py  # BPM detection with librosa
│   ├── watcher.py       # File system watching
│   └── logger.py        # Logging setup
└── README.md
```

## 💻 Platform-Specific Notes

### Windows

**📘 See [WINDOWS.md](WINDOWS.md) for complete Windows 10 setup guide including:**
- Installation troubleshooting
- Running as Windows Service (NSSM)
- Task Scheduler setup
- UNC network path configuration
- Performance optimization

**Quick Start:**
```powershell
# Install dependencies
pip install -r requirements.txt

# Create config
python main.py init

# Paths use forward slashes (recommended) or escaped backslashes
{
  "base_path": "C:/Users/YourName/Music/Incoming",
  "local_path": "D:/Music/Processed",
  "network_path": "//server/share/Music"
}

# Test and run
python main.py validate
python main.py start --watch
```

**UNC Network Paths:** `//server/share` format works directly

### macOS

```bash
# Install dependencies (may need Homebrew libraries)
brew install ffmpeg libsndfile
pip3 install -r requirements.txt

# Paths in config.json
{
  "base_path": "/Users/YourName/Music/Incoming",
  "network_path": "/Volumes/NetworkShare"
}
```

### Linux

```bash
# Install system dependencies
sudo apt-get install ffmpeg libsndfile1

# Install Python dependencies
pip3 install -r requirements.txt

# Paths in config.json
{
  "base_path": "/home/username/Music/Incoming",
  "network_path": "/mnt/share"
}
```

## 🐛 Troubleshooting

### "Configuration file not found"

```bash
# Create default configuration
python main.py init
```

### "librosa not available"

```bash
# Install librosa
pip install librosa soundfile

# On macOS/Linux, may also need:
brew install ffmpeg libsndfile  # macOS
sudo apt-get install ffmpeg libsndfile1  # Linux
```

### "watchdog not installed"

```bash
# Install watchdog for file watching
pip install watchdog

# Or use polling mode instead
python main.py start  # (without --watch flag)
```

### Permission Errors

Ensure the service has:
- **Read** access to `base_path`
- **Write** access to `local_path`
- **Write** access to `network_path` (if enabled)

### Network Path Issues

**Windows**: Use forward slashes
```json
"network_path": "//server/share/folder"
```

**macOS/Linux**: Mount share first
```bash
# macOS
open smb://server/share

# Linux
sudo mount -t cifs //server/share /mnt/share
```

### High CPU Usage

- Use file watching instead of polling:
  ```bash
  python main.py start --watch
  ```
- Increase poll interval in config:
  ```json
  "poll_interval": 120
  ```
- Set log level to WARNING to reduce I/O:
  ```json
  "log_level": "WARNING"
  ```

## 📈 Performance Tips

1. **Use File Watching**: Real-time processing with lower CPU usage
2. **Appropriate Poll Interval**: Balance responsiveness vs. resources
3. **Exclude Directories**: Remove from `base_path` any folders with non-music files
4. **Log Level**: Use INFO for normal operation, DEBUG only for troubleshooting
5. **BPM Detection**: Most CPU-intensive operation, only runs on MP3s

## 🔐 Security Considerations

- Service only processes files in configured directories
- No remote code execution
- No network services exposed
- Logs may contain file paths
- Network credentials handled by OS

## 📝 Logging

Logs written to:
- **Console**: INFO level and above
- **File**: All levels (configurable)

Log format:
```
2025-11-12 10:30:45 INFO     - Processing: Artist - Title.mp3
2025-11-12 10:30:46 INFO     - BPM Detected: 128
2025-11-12 10:30:47 INFO     - Copied: Artist - Title.mp3 -> ~/Music/Processed
```

View logs:
```bash
# Follow log in real-time
tail -f mp3_service.log

# Search for errors
grep ERROR mp3_service.log
```

## 🔄 Feature Parity with C# Version

This Python version maintains **100% feature parity** with the original C# Windows Service while adding improvements:

### Core Features Comparison

| Feature | C# v1.1.0.4 | Python v2.0.0 | Status |
|---------|-------------|---------------|--------|
| **Windows 10 Support** | ✅ Native | ✅ Tested | ✅ **PARITY** |
| **Audio File Processing** | ✅ MP3, M4A, WAV, AIFF, FLAC | ✅ MP3, M4A, WAV, AIFF, FLAC | ✅ **PARITY** |
| **BPM Detection** | consolebpm.exe | librosa (more accurate) | ✅ **IMPROVED** |
| **ID3 Tag Reading** | TagLib-Sharp | mutagen | ✅ **PARITY** |
| **ID3 Tag Writing** | ✅ Artist, Title, BPM | ✅ Artist, Title, BPM | ✅ **PARITY** |
| **Filename Cleaning** | ✅ Regex patterns | ✅ Same regex patterns | ✅ **PARITY** |
| **Title Case Conversion** | ✅ Yes | ✅ Yes | ✅ **PARITY** |
| **Directory Monitoring** | ✅ Timer-based | ✅ Polling + File watching | ✅ **IMPROVED** |
| **Poll Interval** | ✅ Configurable | ✅ Configurable | ✅ **PARITY** |
| **Local File Copy** | ✅ Yes | ✅ Yes | ✅ **PARITY** |
| **Network Share Copy** | ✅ UNC paths | ✅ UNC paths | ✅ **PARITY** |
| **Duplicate Detection** | ✅ copiedList.txt | ✅ copiedList.txt | ✅ **PARITY** |
| **Empty Dir Cleanup** | ✅ Yes | ✅ Yes | ✅ **PARITY** |
| **File Deletion** | ✅ After copy | ✅ After copy | ✅ **PARITY** |
| **Logging** | log4net | Python logging | ✅ **PARITY** |
| **Configuration** | App.config (XML) | config.json | ✅ **IMPROVED** |
| **Windows Service** | ✅ Native | ✅ Via NSSM/Task Scheduler | ✅ **PARITY** |
| **Error Handling** | ✅ Basic | ✅ Enhanced | ✅ **IMPROVED** |
| **Dry-run Mode** | ❌ No | ✅ Yes | ✅ **NEW** |
| **Configuration Validation** | ❌ No | ✅ Yes | ✅ **NEW** |
| **CLI Commands** | ❌ No | ✅ init, validate, test, status | ✅ **NEW** |
| **Real-time File Watching** | ❌ No | ✅ Optional | ✅ **NEW** |
| **Statistics Tracking** | ❌ No | ✅ Yes | ✅ **NEW** |
| **Cross-platform** | ❌ Windows only | ✅ Windows, macOS, Linux | ✅ **NEW** |

### Behavioral Equivalence

**The Python version processes files identically to the C# version:**
1. ✅ Same regex patterns for filename cleaning
2. ✅ Same BPM validation range (65-135)
3. ✅ Same tag extraction logic
4. ✅ Same file copy and delete behavior
5. ✅ Same network share handling
6. ✅ Same directory cleanup
7. ✅ Same copiedList.txt format

### Migration Steps

**From C# Windows Service to Python:**

1. **Stop C# service:**
   ```powershell
   sc stop MP3Service2
   # Keep it installed as backup initially
   ```

2. **Install Python version:**
   ```powershell
   cd python_service
   pip install -r requirements.txt
   ```

3. **Migrate configuration:**
   ```powershell
   # Create new config
   python main.py init

   # Edit config.json with paths from your App.config:
   # - BasePath → base_path
   # - LocalPath → local_path
   # - NetworkPath → network_path
   # - PollInterval → poll_interval (in seconds)
   # - IncludeShare → include_share (true/false)
   ```

4. **Test (important!):**
   ```powershell
   # Validate config
   python main.py validate

   # Preview changes (no files modified)
   python main.py start --dry-run

   # Process once
   python main.py process
   ```

5. **Install as Windows Service:**
   - See [WINDOWS.md](WINDOWS.md) for NSSM setup
   - Or use Task Scheduler for auto-start

6. **Verify then remove C# service:**
   ```powershell
   # After confirming Python version works
   sc delete MP3Service2
   ```

### Improvements Over C# Version

1. **Better BPM Detection**: librosa is more accurate than consolebpm.exe
2. **Safer**: Dry-run mode lets you preview changes
3. **Easier Setup**: JSON config is simpler than XML
4. **More Flexible**: Choose between polling or real-time file watching
5. **Better UX**: CLI commands for testing and validation
6. **Cross-platform**: Run on Windows, macOS, or Linux
7. **Better Error Messages**: More helpful diagnostics
8. **Statistics**: See exactly what was processed

## 🎯 Use Cases

- **DJ Libraries**: Auto-organize downloaded tracks with BPM tags
- **Music Production**: Clean and tag incoming samples
- **Podcast Processing**: Organize episodes with metadata
- **Audio Archives**: Maintain organized, tagged collections
- **Batch Processing**: Clean up large music collections

## 📦 Dependencies

### Core
- **mutagen**: ID3 tag manipulation (all formats)
- **librosa**: BPM detection and audio analysis
- **numpy**: Numerical operations for librosa
- **soundfile**: Audio file I/O

### Optional
- **watchdog**: File system watching (for `--watch` mode)

## 🤝 Contributing

This is a personal project converted from C# to Python. Feel free to fork and customize for your needs.

## 📄 License

(Add your license information here)

## 🆘 Support

For issues:
1. Check configuration with `python main.py validate`
2. Test with `python main.py test`
3. Enable DEBUG logging in config.json
4. Review log file for detailed errors

## 🎉 Version History

**v2.0.0** - Major refactor and improvements
- ✨ Added full CLI interface with subcommands
- ✨ Added dry-run mode for safe previewing
- ✨ Added file watching mode for real-time processing
- ✨ Added statistics tracking
- ✨ Added configuration validation and testing
- ✨ Improved error handling and logging
- ✨ Better cross-platform path handling
- 🐛 Fixed numerous edge cases
- 📚 Comprehensive documentation

**v1.0.0** - Initial Python conversion
- Cross-platform support (Windows, macOS, Linux)
- Pure Python implementation
- Modular architecture
- JSON configuration

**v1.1.0.4** - Original C# version
- Windows Service implementation
- TagLib for ID3 tags
- consolebpm.exe for BPM detection
