# MP3 Service - Windows Installation Guide

Complete guide for installing MP3 Service on Windows 10 using the automated installer.

## Quick Install

1. **Download or clone the repository**
2. **Right-click `install.bat`**
3. **Select "Run as Administrator"**
4. **Follow the prompts**

That's it! The installer handles everything automatically.

## What the Installer Does

The automated installer performs these steps:

✅ **Checks Python Installation**
- Verifies Python 3.8+ is installed
- Checks PATH configuration
- Provides download link if missing

✅ **Installs Dependencies**
- Upgrades pip
- Installs all required packages from requirements.txt
- Handles errors gracefully

✅ **Creates Configuration**
- Runs interactive setup wizard
- Or creates default config in unattended mode
- Validates configuration

✅ **Validates Setup**
- Runs health checks
- Verifies paths exist
- Tests permissions

✅ **Installs Windows Service** (Optional)
- Installs using NSSM
- Configures auto-start
- Sets up service description

✅ **Creates Shortcuts**
- Desktop shortcut to start service
- Start Menu folder with utilities
- Easy access to all functions

## Installation Methods

### Method 1: Interactive (Recommended)

```powershell
# Right-click install.bat → Run as Administrator
```

This method:
- Asks questions during setup
- Guides you through configuration
- Optionally installs as Windows Service
- Creates shortcuts

### Method 2: Silent/Unattended

```powershell
# Run PowerShell as Administrator
PowerShell -ExecutionPolicy Bypass -File install.ps1 -Unattended -SkipServiceInstall
```

This method:
- Uses default configuration
- No user interaction
- Skips Windows Service installation
- Good for automation/deployment

### Method 3: Manual (Advanced)

```powershell
# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python setup.py

# Validate
python health_check.py
```

## Prerequisites

### Required

**Python 3.8 or higher**
- Download from: https://www.python.org/downloads/
- ✅ **Important**: Check "Add Python to PATH" during installation
- Verify: `python --version`

**Administrator Privileges**
- Right-click installer → "Run as Administrator"

### Optional (for Windows Service)

**NSSM (Non-Sucking Service Manager)**
- Download from: https://nssm.cc/
- Extract to `C:\nssm\` or add to PATH
- Only needed if installing as Windows Service

## Installation Options

### Installer Flags

```powershell
# Skip Windows Service installation
install.ps1 -SkipServiceInstall

# Unattended mode (no prompts)
install.ps1 -Unattended

# Both
install.ps1 -Unattended -SkipServiceInstall
```

### What Gets Installed

**Files Created:**
- `config.json` - Your configuration
- `copiedList.txt` - Tracking file (created on first run)
- `mp3_service.log` - Log file (created on first run)

**Shortcuts Created:**
- Desktop: "MP3 Service.lnk"
- Start Menu: "Programs\MP3 Service\"
  - Start MP3 Service
  - Configure MP3 Service
  - Validate Configuration
  - Health Check
  - Service Folder

**Windows Service** (if selected):
- Service Name: `MP3Service`
- Display Name: "MP3 Audio Processing Service"
- Startup Type: Automatic
- Control: services.msc or `nssm`

## Post-Installation

### Verify Installation

```powershell
# Check health
python health_check.py

# Validate configuration
python main.py validate

# Check status
python main.py status
```

### First Run

```powershell
# Test mode (safe, no changes)
python main.py start --dry-run

# Run once
python main.py process

# Start service
python main.py start --watch
```

### If Installed as Windows Service

```powershell
# Start service
nssm start MP3Service
# Or use: services.msc

# Check status
nssm status MP3Service

# Stop service
nssm stop MP3Service

# Restart service
nssm restart MP3Service

# View logs
type mp3_service.log
```

## Troubleshooting

### "Python not found"

**Solution**:
1. Install Python from python.org
2. ✅ Check "Add Python to PATH"
3. Restart PowerShell/Command Prompt
4. Verify: `python --version`

### "Access Denied" or "Permission Denied"

**Solution**:
- Right-click `install.bat`
- Select "Run as Administrator"

### "Execution Policy" Error

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Cannot find NSSM"

**Solution**:
- Download NSSM: https://nssm.cc/
- Extract to `C:\nssm\win64\`
- Add to PATH or specify full path

**Or skip service installation**:
```powershell
install.ps1 -SkipServiceInstall
```

### Dependencies Won't Install

**Solution**:
```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install manually
pip install mutagen watchdog

# Optional (BPM detection)
pip install librosa
```

### Service Won't Start

**Check**:
1. Configuration valid: `python main.py validate`
2. Paths exist and accessible
3. Check service logs: `type mp3_service.log`
4. Event Viewer: Application logs

**Fix**:
```powershell
# Reinstall service
nssm stop MP3Service
nssm remove MP3Service confirm
nssm install MP3Service "C:\Python311\python.exe" "main.py start --watch"
nssm set MP3Service AppDirectory "C:\path\to\python_service"
nssm start MP3Service
```

## Uninstallation

### Automated Uninstaller

```powershell
# Right-click uninstall.bat → Run as Administrator
```

Or PowerShell:
```powershell
# Remove everything
PowerShell -ExecutionPolicy Bypass -File uninstall.ps1

# Keep configuration
PowerShell -ExecutionPolicy Bypass -File uninstall.ps1 -KeepConfig
```

### Manual Uninstall

```powershell
# Stop and remove service
nssm stop MP3Service
nssm remove MP3Service confirm

# Remove shortcuts
Remove-Item "$env:USERPROFILE\Desktop\MP3 Service.lnk"
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\MP3 Service" -Recurse

# Uninstall packages (optional)
pip uninstall -y mutagen librosa numpy soundfile scipy watchdog

# Delete folder
Remove-Item "C:\path\to\python_service" -Recurse
```

## Advanced Configuration

### Custom Installation Location

```powershell
# Extract/clone to desired location
cd C:\MyPrograms\MP3Service

# Run installer from there
.\install.bat
```

### Multiple Instances

Install in different folders with different configs:

```powershell
# Instance 1
cd C:\MP3Service-Music
.\install.bat

# Instance 2
cd C:\MP3Service-DJ
.\install.bat
```

Each gets its own service, config, and shortcuts.

### Network Deployment

For deploying to multiple PCs:

```powershell
# Create config template
python main.py init --output config.template.json

# Customize config.template.json for your environment

# Deploy script
Copy-Item config.template.json \\PC01\C$\MP3Service\config.json
Invoke-Command -ComputerName PC01 -ScriptBlock {
    cd C:\MP3Service
    .\install.bat
}
```

## Updating

### Update to New Version

```powershell
# Backup config
Copy-Item config.json config.backup.json

# Stop service
nssm stop MP3Service

# Update files (git pull or extract new version)
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
nssm start MP3Service

# Or reinstall service
.\install.bat
```

## Security Notes

**Installer requires Administrator**:
- Needed to install Windows Service
- Needed to create shortcuts in Start Menu
- Needed to write to system directories

**What the installer does NOT do**:
- Does not connect to the internet (except pip for packages)
- Does not modify system files outside service directory
- Does not create firewall rules
- Does not access network without your configuration

**Best Practices**:
- Review configuration before running
- Use specific paths, not system directories
- Backup your configuration
- Monitor logs for unexpected activity

## Getting Help

**Check Installation**:
```powershell
python health_check.py
python main.py validate
```

**View Logs**:
```powershell
type mp3_service.log
```

**Documentation**:
- README.md - Full documentation
- WINDOWS.md - Windows guide
- IMPROVEMENTS.md - Features and roadmap

**Support**:
- GitHub Issues
- Check logs for error messages
- Run health check for diagnostics

## Summary

The installer makes MP3 Service deployment on Windows 10 as simple as:

1. **Right-click `install.bat`**
2. **"Run as Administrator"**
3. **Follow prompts**
4. **Done!**

Everything is automated, validated, and ready to use. The service can run as:
- Windows Service (automatic background operation)
- Manual execution (run when needed)
- Scheduled Task (run on schedule)

Choose what works best for your workflow!
