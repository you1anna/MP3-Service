# Windows Installation & Setup Guide

Complete guide for running MP3 Service on Windows 10.

## Prerequisites

1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/
   - During installation: ✅ Check "Add Python to PATH"
   - Verify: `python --version`

2. **Microsoft Visual C++ Build Tools** (for some dependencies)
   - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Or install via: `pip install wheel`

## Installation

### Method 1: Quick Install (Recommended)

```powershell
# Open PowerShell as Administrator
cd C:\path\to\MP3-Service\python_service

# Install dependencies
pip install -r requirements.txt

# If you get errors with librosa/numba, try:
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### Method 2: Install Without BPM Detection (Faster)

If you don't need BPM detection:

```powershell
# Install only essential packages
pip install mutagen watchdog
```

## Configuration

### 1. Create Configuration

```powershell
python main.py init
```

### 2. Edit config.json for Windows

Use **forward slashes** or **escaped backslashes** in paths:

```json
{
  "base_path": "C:/Users/YourName/Music/Incoming",
  "local_path": "D:/Music/Processed",
  "network_path": "//server/share/Music",
  "poll_interval": 40,
  "include_share": false
}
```

**Path Format Options:**
- ✅ `C:/Users/Name/Music` (forward slashes - recommended)
- ✅ `C:\\Users\\Name\\Music` (escaped backslashes)
- ✅ `//server/share` (UNC network paths)
- ❌ `C:\Users\Name\Music` (single backslash - will cause errors)

### 3. Network Shares

**Map Network Drive (Recommended):**
```powershell
# Map drive
net use Z: \\server\share /persistent:yes

# In config.json:
"network_path": "Z:/Music"
```

**Or use UNC path directly:**
```json
"network_path": "//server/share/Music"
```

## Running the Service

### Interactive Mode (Testing)

```powershell
# Test configuration
python main.py validate

# Preview without changes
python main.py start --dry-run

# Run once
python main.py process

# Run continuously (polling)
python main.py start

# Run with file watching (recommended)
python main.py start --watch
```

### Run on Startup (Task Scheduler)

1. **Create a batch file** `start_mp3_service.bat`:
   ```batch
   @echo off
   cd C:\path\to\MP3-Service\python_service
   python main.py start --watch
   ```

2. **Open Task Scheduler**
   - Windows Key → "Task Scheduler"
   - Create Basic Task
   - Name: "MP3 Service"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: `C:\path\to\start_mp3_service.bat`
   - ✅ Run whether user is logged on or not
   - ✅ Run with highest privileges

### Run as Windows Service (Advanced)

Use **NSSM (Non-Sucking Service Manager)**:

1. **Download NSSM**
   - https://nssm.cc/download
   - Extract to `C:\nssm`

2. **Install service**
   ```powershell
   # Open PowerShell as Administrator
   cd C:\nssm\win64

   .\nssm install MP3Service
   ```

3. **Configure in NSSM GUI:**
   - Path: `C:\Python311\python.exe`
   - Startup directory: `C:\path\to\MP3-Service\python_service`
   - Arguments: `main.py start --watch`
   - Service name: `MP3Service`
   - Display name: `MP3 Audio Processing Service`
   - Description: `Automatically processes audio files with BPM detection and tag management`

4. **Start service:**
   ```powershell
   nssm start MP3Service
   ```

5. **Check status:**
   ```powershell
   nssm status MP3Service
   ```

6. **View logs:**
   - Check `mp3_service.log` in the application directory

## Troubleshooting

### "Python not recognized"

```powershell
# Add to PATH manually:
# 1. Windows Key → "Environment Variables"
# 2. Edit "Path" under "System variables"
# 3. Add: C:\Python311\
# 4. Add: C:\Python311\Scripts\
```

### "No module named 'mutagen'"

```powershell
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### "Permission denied" errors

**Run as Administrator:**
```powershell
# Right-click PowerShell → "Run as Administrator"
python main.py start
```

**Or grant permissions:**
```powershell
# Give user write access to directories
icacls "C:\path\to\base_path" /grant YourUsername:(OI)(CI)F
icacls "C:\path\to\local_path" /grant YourUsername:(OI)(CI)F
```

### "Cannot access network path"

**Verify network access:**
```powershell
# Test network path
dir \\server\share

# If fails, map drive first:
net use Z: \\server\share /user:domain\username password
```

### File locking errors

Windows locks open files. If you see "file in use" errors:
- Close any programs accessing the audio files
- Increase `poll_interval` in config
- Use `--watch` mode (better file detection)

### librosa installation fails

**Install precompiled wheels:**
```powershell
# Install from precompiled binaries
pip install librosa --only-binary :all:

# Or skip librosa (no BPM detection):
pip install mutagen watchdog
# Edit requirements.txt to remove librosa and its dependencies
```

### High CPU usage

```json
{
  "poll_interval": 120,
  "log_level": "WARNING"
}
```

Or use file watching:
```powershell
python main.py start --watch
```

## Performance Tips for Windows

1. **Exclude from Windows Defender** (faster file operations):
   - Windows Security → Virus & threat protection
   - Manage settings → Add or remove exclusions
   - Add: `C:\path\to\base_path`
   - Add: `C:\path\to\local_path`

2. **Use SSD for processing** (faster I/O):
   ```json
   "base_path": "C:/FastSSD/Incoming",
   "local_path": "C:/FastSSD/Processed"
   ```

3. **Disable file indexing** on processing folders:
   - Right-click folder → Properties
   - Uncheck "Allow files in this folder to have contents indexed"

## Firewall Configuration

If using network shares:
- Windows Firewall → Allow an app
- Python → Allow on Private and Public networks

## Comparison with C# Version

| Feature | C# Version | Python Version | Notes |
|---------|------------|----------------|-------|
| Windows Service | ✅ Native | ✅ Via NSSM/Task Scheduler | Python uses wrapper |
| BPM Detection | consolebpm.exe | librosa | Python is more accurate |
| Polling | ✅ Timer | ✅ Configurable | Same behavior |
| File Watching | ❌ No | ✅ Optional | Python adds real-time |
| Network Shares | ✅ UNC paths | ✅ UNC paths | Same support |
| ID3 Tags | TagLib-Sharp | mutagen | Both work well |
| Filename Cleaning | ✅ Regex | ✅ Same regex | Identical behavior |
| Dry-run Mode | ❌ No | ✅ Yes | Python adds safety |
| Configuration | XML | JSON | JSON easier to edit |
| Logging | log4net | Python logging | Similar output |

## Upgrading from C# Version

1. **Stop C# service:**
   ```powershell
   sc stop MP3Service2
   sc delete MP3Service2
   ```

2. **Migrate configuration:**
   - Copy paths from `App.config` to `config.json`
   - Use forward slashes in paths

3. **Test Python version:**
   ```powershell
   python main.py start --dry-run
   ```

4. **Install as service** (see above)

5. **Keep C# backup** until confident Python version works

## Example Startup Script

Save as `start_service.bat`:

```batch
@echo off
REM MP3 Service Startup Script
cd /d C:\MP3-Service\python_service

REM Activate virtual environment (if using one)
REM call venv\Scripts\activate

REM Start service
echo Starting MP3 Service...
python main.py start --watch --config config.json

REM If service crashes, wait and restart
if errorlevel 1 (
    echo Service crashed, restarting in 10 seconds...
    timeout /t 10
    goto :start
)
```

## Uninstall

```powershell
# If using NSSM:
nssm stop MP3Service
nssm remove MP3Service confirm

# If using Task Scheduler:
# Delete task in Task Scheduler

# Remove Python packages (optional):
pip uninstall -y mutagen librosa numpy soundfile scipy watchdog
```

## Support

For Windows-specific issues:
1. Check `mp3_service.log` for errors
2. Run with `"log_level": "DEBUG"` in config
3. Test with `python main.py validate`
4. Verify paths with `python main.py status`
