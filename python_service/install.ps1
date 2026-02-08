# MP3 Service - Windows PowerShell Installer
# Automated installation script for Windows 10

param(
    [switch]$SkipServiceInstall,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"

# Banner
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MP3 Service - Windows Installer v2.0" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PYTHON_MIN_VERSION = "3.8"
$NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"
$PYTHON_URL = "https://www.python.org/downloads/"

# Functions
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-PythonInstalled {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+\.\d+)") {
            $version = [version]$Matches[1]
            $minVersion = [version]$PYTHON_MIN_VERSION
            return $version -ge $minVersion
        }
    } catch {
        return $false
    }
    return $false
}

function Install-Dependencies {
    Write-Host "`n[1/6] Installing Python dependencies..." -ForegroundColor Yellow

    try {
        # Upgrade pip first
        Write-Host "  Upgrading pip..." -ForegroundColor Gray
        python -m pip install --upgrade pip --quiet

        # Install requirements
        Write-Host "  Installing packages (this may take a few minutes)..." -ForegroundColor Gray
        python -m pip install -r requirements.txt --quiet

        Write-Host "  ✓ Dependencies installed successfully" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  ✗ Failed to install dependencies: $_" -ForegroundColor Red
        return $false
    }
}

function New-Configuration {
    Write-Host "`n[2/6] Creating configuration..." -ForegroundColor Yellow

    if (Test-Path "config.json") {
        Write-Host "  Configuration already exists: config.json" -ForegroundColor Gray

        if (-not $Unattended) {
            $response = Read-Host "  Overwrite existing configuration? (y/n)"
            if ($response -ne "y") {
                Write-Host "  ✓ Keeping existing configuration" -ForegroundColor Green
                return $true
            }
        } else {
            Write-Host "  ✓ Using existing configuration" -ForegroundColor Green
            return $true
        }
    }

    try {
        if ($Unattended) {
            # Create default config
            Write-Host "  Creating default configuration..." -ForegroundColor Gray
            python main.py init --output config.json
        } else {
            # Interactive setup
            Write-Host "  Starting interactive setup wizard..." -ForegroundColor Gray
            python setup.py
        }

        Write-Host "  ✓ Configuration created successfully" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  ✗ Failed to create configuration: $_" -ForegroundColor Red
        return $false
    }
}

function Test-ServiceConfiguration {
    Write-Host "`n[3/6] Validating configuration..." -ForegroundColor Yellow

    try {
        python main.py validate
        Write-Host "  ✓ Configuration validated" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  ⚠ Configuration validation failed" -ForegroundColor Yellow
        return $false
    }
}

function Install-WindowsService {
    Write-Host "`n[4/6] Installing Windows Service..." -ForegroundColor Yellow

    if ($SkipServiceInstall) {
        Write-Host "  ⊙ Skipping Windows Service installation (--SkipServiceInstall)" -ForegroundColor Gray
        return $true
    }

    if ($Unattended) {
        Write-Host "  ⊙ Skipping Windows Service installation (unattended mode)" -ForegroundColor Gray
        return $true
    }

    $response = Read-Host "  Install as Windows Service? (y/n)"
    if ($response -ne "y") {
        Write-Host "  ⊙ Skipping Windows Service installation" -ForegroundColor Gray
        Write-Host "    You can run manually with: python main.py start --watch" -ForegroundColor Gray
        return $true
    }

    # Check if NSSM is available
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue

    if (-not $nssmPath) {
        Write-Host "  NSSM (Non-Sucking Service Manager) not found" -ForegroundColor Yellow
        Write-Host "  Please install NSSM manually from: https://nssm.cc/" -ForegroundColor Yellow
        Write-Host "  Then run: nssm install MP3Service" -ForegroundColor Yellow
        return $false
    }

    try {
        # Get paths
        $pythonPath = (Get-Command python).Source
        $servicePath = (Get-Location).Path
        $scriptPath = Join-Path $servicePath "main.py"

        # Check if service already exists
        $existingService = Get-Service -Name "MP3Service" -ErrorAction SilentlyContinue
        if ($existingService) {
            Write-Host "  Service already exists, removing old service..." -ForegroundColor Gray
            nssm stop MP3Service
            nssm remove MP3Service confirm
        }

        # Install service
        Write-Host "  Installing MP3Service..." -ForegroundColor Gray
        nssm install MP3Service $pythonPath "main.py start --watch"
        nssm set MP3Service AppDirectory $servicePath
        nssm set MP3Service DisplayName "MP3 Audio Processing Service"
        nssm set MP3Service Description "Automatically processes audio files with BPM detection and tag management"
        nssm set MP3Service Start SERVICE_AUTO_START

        Write-Host "  ✓ Service installed successfully" -ForegroundColor Green
        Write-Host "    Service name: MP3Service" -ForegroundColor Gray
        Write-Host "    Start with: nssm start MP3Service" -ForegroundColor Gray
        Write-Host "    Or use Services app (services.msc)" -ForegroundColor Gray

        return $true
    } catch {
        Write-Host "  ✗ Failed to install service: $_" -ForegroundColor Red
        return $false
    }
}

function New-Shortcuts {
    Write-Host "`n[5/6] Creating shortcuts..." -ForegroundColor Yellow

    try {
        $servicePath = (Get-Location).Path
        $desktopPath = [Environment]::GetFolderPath("Desktop")
        $startMenuPath = [Environment]::GetFolderPath("Programs")
        $mp3ServiceFolder = Join-Path $startMenuPath "MP3 Service"

        # Create Start Menu folder
        if (-not (Test-Path $mp3ServiceFolder)) {
            New-Item -ItemType Directory -Path $mp3ServiceFolder | Out-Null
        }

        # Create shortcuts
        $WScriptShell = New-Object -ComObject WScript.Shell

        # Desktop shortcut - Start Service
        $shortcut = $WScriptShell.CreateShortcut("$desktopPath\MP3 Service.lnk")
        $shortcut.TargetPath = "python"
        $shortcut.Arguments = "main.py start --watch"
        $shortcut.WorkingDirectory = $servicePath
        $shortcut.Description = "Start MP3 Audio Processing Service"
        $shortcut.Save()

        # Start Menu shortcuts
        $shortcuts = @(
            @{Name="Start MP3 Service"; Args="main.py start --watch"; Desc="Start the service"},
            @{Name="Configure MP3 Service"; Args="setup.py"; Desc="Configure the service"},
            @{Name="Validate Configuration"; Args="main.py validate"; Desc="Validate configuration"},
            @{Name="Health Check"; Args="health_check.py"; Desc="Run system health check"},
            @{Name="Service Folder"; Target=$servicePath; Desc="Open service folder"}
        )

        foreach ($s in $shortcuts) {
            $shortcutPath = Join-Path $mp3ServiceFolder "$($s.Name).lnk"
            $shortcut = $WScriptShell.CreateShortcut($shortcutPath)

            if ($s.Target) {
                $shortcut.TargetPath = $s.Target
            } else {
                $shortcut.TargetPath = "python"
                $shortcut.Arguments = $s.Args
                $shortcut.WorkingDirectory = $servicePath
            }

            $shortcut.Description = $s.Desc
            $shortcut.Save()
        }

        Write-Host "  ✓ Shortcuts created" -ForegroundColor Green
        Write-Host "    Desktop: MP3 Service.lnk" -ForegroundColor Gray
        Write-Host "    Start Menu: Programs\MP3 Service" -ForegroundColor Gray

        return $true
    } catch {
        Write-Host "  ⚠ Failed to create shortcuts: $_" -ForegroundColor Yellow
        return $false
    }
}

function Show-Summary {
    Write-Host "`n[6/6] Installation Summary" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  MP3 Service installed successfully!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installation location: $(Get-Location)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor White
    Write-Host "  • Desktop shortcut created" -ForegroundColor Gray
    Write-Host "  • Start Menu folder: Programs\MP3 Service" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Manual Commands:" -ForegroundColor White
    Write-Host "  python main.py start --watch    # Start service" -ForegroundColor Gray
    Write-Host "  python main.py status           # Check status" -ForegroundColor Gray
    Write-Host "  python health_check.py          # Run diagnostics" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Documentation:" -ForegroundColor White
    Write-Host "  • README.md - Full documentation" -ForegroundColor Gray
    Write-Host "  • WINDOWS.md - Windows-specific guide" -ForegroundColor Gray
    Write-Host "  • IMPROVEMENTS.md - Features and roadmap" -ForegroundColor Gray
    Write-Host ""

    if (-not $SkipServiceInstall) {
        Write-Host "Windows Service:" -ForegroundColor White
        Write-Host "  • Service installed: MP3Service" -ForegroundColor Gray
        Write-Host "  • Start: nssm start MP3Service" -ForegroundColor Gray
        Write-Host "  • Or use: services.msc" -ForegroundColor Gray
        Write-Host ""
    }

    Write-Host "================================================================" -ForegroundColor Cyan
}

# Main Installation Process
try {
    # Check administrator privileges
    if (-not (Test-Administrator)) {
        Write-Host "✗ This installer requires administrator privileges" -ForegroundColor Red
        Write-Host "  Please right-click and select 'Run as Administrator'" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "✓ Running with administrator privileges" -ForegroundColor Green

    # Check Python
    Write-Host "`n[0/6] Checking prerequisites..." -ForegroundColor Yellow

    if (-not (Test-PythonInstalled)) {
        Write-Host "  ✗ Python $PYTHON_MIN_VERSION or higher not found" -ForegroundColor Red
        Write-Host "  Please install Python from: $PYTHON_URL" -ForegroundColor Yellow
        Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
        exit 1
    }

    $pythonVersion = python --version
    Write-Host "  ✓ $pythonVersion installed" -ForegroundColor Green

    # Run installation steps
    $steps = @(
        { Install-Dependencies },
        { New-Configuration },
        { Test-ServiceConfiguration },
        { Install-WindowsService },
        { New-Shortcuts }
    )

    $failed = $false
    foreach ($step in $steps) {
        if (-not (& $step)) {
            $failed = $true
            break
        }
    }

    if ($failed) {
        Write-Host "`n✗ Installation completed with errors" -ForegroundColor Red
        Write-Host "  Review the errors above and try again" -ForegroundColor Yellow
        exit 1
    }

    # Show summary
    Show-Summary

    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

    exit 0

} catch {
    Write-Host "`n✗ Installation failed with error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
