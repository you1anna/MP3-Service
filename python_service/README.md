# MP3 Service - Audio File Processor

A cross-platform Python service that automatically processes audio files by detecting BPM, managing ID3 tags, cleaning filenames, and organizing files into designated directories.

## Features

- **Automatic BPM Detection**: Uses `librosa` to detect tempo/BPM for audio files
- **ID3 Tag Management**: Reads and writes artist, title, and BPM metadata
- **Intelligent Filename Cleaning**: Removes unwanted patterns and formats filenames consistently
- **Multi-Format Support**: Handles MP3, M4A, WAV, AIFF, AIF, and FLAC files
- **Automatic Organization**: Copies processed files to local and network destinations
- **Continuous Monitoring**: Polls directories at configurable intervals
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Project Structure

```
python_service/
├── main.py              # Entry point
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration management
│   ├── processor.py     # Main processing logic
│   ├── tag_handler.py   # ID3 tag operations
│   ├── file_handler.py  # File operations & cleaning
│   ├── bpm_detector.py  # BPM detection using librosa
│   └── logger.py        # Logging setup
└── README.md
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Windows

```bash
# Clone or download the project
cd python_service

# Install dependencies
pip install -r requirements.txt
```

### macOS

```bash
# Clone or download the project
cd python_service

# Install dependencies (may need additional libraries for librosa)
pip3 install -r requirements.txt

# On macOS, you might also need:
brew install ffmpeg  # For audio file handling
```

### Linux

```bash
# Clone or download the project
cd python_service

# Install dependencies
pip3 install -r requirements.txt

# You may also need system libraries:
sudo apt-get install ffmpeg libsndfile1  # Debian/Ubuntu
```

## Configuration

Edit `config.json` to customize the service:

```json
{
  "base_path": "c:/soulseek",           // Directory to monitor
  "local_path": "D:/BackupShare/Shared", // Where to copy processed files
  "network_path": "//psf/SAMSUNG/Traktor", // Optional network share
  "desktop_path": "c:/",                 // Optional desktop path
  "poll_interval": 40,                   // Seconds between scans
  "include_share": false,                // Enable network copying
  "supported_extensions": [              // File types to process
    ".mp3", ".m4a", ".wav", ".aif", ".aiff", ".flac"
  ],
  "bpm_range": {                        // Valid BPM range
    "min": 65,
    "max": 135
  },
  "log_file": "mp3_service.log",        // Log file path
  "log_level": "INFO"                   // DEBUG, INFO, WARNING, ERROR
}
```

### Configuration Options

- **base_path**: Directory to monitor for audio files (subdirectories included)
- **local_path**: Destination for processed files
- **network_path**: Optional network share for copying files
- **poll_interval**: How often to check for new files (in seconds)
- **include_share**: Set to `true` to enable network copying
- **supported_extensions**: Audio file formats to process
- **bpm_range**: Min/max acceptable BPM values (librosa can detect double/half-time)
- **log_file**: Where to write logs
- **log_level**: Logging verbosity (DEBUG for detailed output)

## Usage

### Run the Service

```bash
# Using default config.json
python main.py

# Or specify a custom config file
python main.py /path/to/custom_config.json
```

### How It Works

1. **Monitoring**: The service scans `base_path` for audio files every `poll_interval` seconds
2. **Processing**: For each new file:
   - Detects BPM using librosa (for MP3 files)
   - Reads existing ID3 tags (artist, title, BPM)
   - Extracts metadata from filename if tags are missing
   - Cleans filename using regex patterns
   - Validates and corrects BPM if out of range
3. **Organization**: Copies processed files to `local_path`
4. **Network Share** (optional): Copies to `network_path` if enabled
5. **Cleanup**: Removes empty directories and non-audio files

### Stop the Service

Press `Ctrl+C` to gracefully stop the service.

## Processing Logic

### BPM Detection

- Uses `librosa.beat.beat_track()` for tempo detection
- Analyzes first 2 minutes of audio file
- Automatically corrects double-time or half-time detection
- Only updates tags if BPM is within configured range

### Filename Cleaning

Applies multiple regex patterns to clean filenames:
- Replaces `--` with ` - `
- Converts underscores to spaces
- Removes leading numbers/letters (e.g., "01 ", "A1 ")
- Strips website patterns (e.g., "www.site.com")
- Removes unwanted suffixes
- Converts to Title Case

### Tag Management

Priority order for artist/title:
1. Existing ID3 tags (if valid)
2. Extracted from filename (format: "Artist - Title")
3. Cleaned original filename

## Logging

Logs are written to both:
- Console (INFO level and above)
- Log file specified in config (all levels based on `log_level`)

Log format:
```
2025-11-12 10:30:45 INFO     - Processing: Artist - Title.mp3
2025-11-12 10:30:46 INFO     - BPM Detected: 128
2025-11-12 10:30:47 INFO     - Copied: Artist - Title.mp3 -> D:/BackupShare/Shared
```

## Troubleshooting

### "librosa not available" warning

If you see this warning, BPM detection is disabled. Install librosa:
```bash
pip install librosa
```

### ImportError with librosa

On some systems, librosa needs additional audio libraries:
```bash
# Windows
pip install soundfile

# macOS
brew install ffmpeg libsndfile

# Linux
sudo apt-get install ffmpeg libsndfile1
```

### Permission errors

Ensure the service has read/write permissions for:
- `base_path` (read)
- `local_path` (write)
- `network_path` (write, if enabled)

### Network path not accessible

- Check network connectivity
- Verify path format (Windows: `//server/share`, macOS/Linux: `/Volumes/share`)
- Ensure you have access rights to the network share

## Platform-Specific Notes

### Windows

- Use forward slashes `/` or escaped backslashes `\\` in paths
- Network paths: `//server/share` format
- Can be run as a Windows service using tools like NSSM

### macOS

- Network paths: `/Volumes/NetworkShare` or `//server/share`
- May need to mount network shares in Finder first
- Use `brew` to install audio processing libraries

### Linux

- Can be configured as a systemd service
- Network paths: `/mnt/share` or SMB paths
- Ensure ffmpeg and libsndfile1 are installed

## Converting from Windows Service

This Python version replaces the C# Windows Service with:
- `log4net` → Python `logging` module
- `TagLib` → `mutagen` library
- `consolebpm.exe` → `librosa` for BPM detection
- Timer-based polling → Python `time.sleep()` loop
- Windows-only → Cross-platform support

## Performance Notes

- BPM detection can be CPU-intensive (analyzes up to 2 minutes of audio)
- Processing time depends on file size and audio format
- Network copying speed depends on connection bandwidth
- Set appropriate `poll_interval` to balance responsiveness vs. resource usage

## Version History

**v2.0.0** - Python rewrite
- Cross-platform support (Windows, macOS, Linux)
- Pure Python implementation with librosa
- Modular architecture
- JSON configuration
- Improved error handling and logging

**v1.1.0.4** - Original C# version
- Windows Service implementation
- TagLib for ID3 tags
- consolebpm.exe for BPM detection

## License

(Add your license information here)

## Support

For issues or questions:
1. Check the log file for detailed error messages
2. Enable DEBUG logging in config.json
3. Verify all paths exist and are accessible
4. Ensure required dependencies are installed
