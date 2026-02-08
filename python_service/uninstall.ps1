# MP3 Service - Windows Uninstaller

param(
    [switch]$KeepConfig
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MP3 Service - Uninstaller" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "✗ This uninstaller requires administrator privileges" -ForegroundColor Red
    Write-Host "  Please right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "This will remove MP3 Service from your system." -ForegroundColor Yellow
Write-Host ""

if (-not $KeepConfig) {
    Write-Host "⚠ WARNING: Your configuration file (config.json) will be deleted!" -ForegroundColor Red
    Write-Host "  Use -KeepConfig flag to preserve your configuration" -ForegroundColor Yellow
    Write-Host ""
}

$response = Read-Host "Continue with uninstall? (yes/no)"
if ($response -ne "yes") {
    Write-Host "Uninstall cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""

# Stop and remove Windows Service
Write-Host "[1/4] Removing Windows Service..." -ForegroundColor Yellow
try {
    $service = Get-Service -Name "MP3Service" -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host "  Stopping service..." -ForegroundColor Gray

        $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
        if ($nssmPath) {
            nssm stop MP3Service 2>&1 | Out-Null
            nssm remove MP3Service confirm 2>&1 | Out-Null
            Write-Host "  ✓ Service removed" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ NSSM not found, service may remain" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⊙ Service not installed" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠ Could not remove service: $_" -ForegroundColor Yellow
}

# Remove shortcuts
Write-Host "`n[2/4] Removing shortcuts..." -ForegroundColor Yellow
try {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $startMenuPath = [Environment]::GetFolderPath("Programs")

    $desktopShortcut = Join-Path $desktopPath "MP3 Service.lnk"
    if (Test-Path $desktopShortcut) {
        Remove-Item $desktopShortcut -Force
        Write-Host "  ✓ Removed desktop shortcut" -ForegroundColor Green
    }

    $startMenuFolder = Join-Path $startMenuPath "MP3 Service"
    if (Test-Path $startMenuFolder) {
        Remove-Item $startMenuFolder -Recurse -Force
        Write-Host "  ✓ Removed Start Menu folder" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ Could not remove shortcuts: $_" -ForegroundColor Yellow
}

# Remove config (optional)
Write-Host "`n[3/4] Handling configuration..." -ForegroundColor Yellow
if ($KeepConfig) {
    Write-Host "  ⊙ Keeping configuration file" -ForegroundColor Gray
} else {
    try {
        if (Test-Path "config.json") {
            Remove-Item "config.json" -Force
            Write-Host "  ✓ Configuration file removed" -ForegroundColor Green
        }
        if (Test-Path "copiedList.txt") {
            Remove-Item "copiedList.txt" -Force
            Write-Host "  ✓ Processed files list removed" -ForegroundColor Green
        }
        if (Test-Path "*.log") {
            Remove-Item "*.log" -Force
            Write-Host "  ✓ Log files removed" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠ Could not remove config: $_" -ForegroundColor Yellow
    }
}

# Uninstall Python packages (optional)
Write-Host "`n[4/4] Python packages..." -ForegroundColor Yellow
$response = Read-Host "  Remove Python packages? (y/n)"
if ($response -eq "y") {
    try {
        Write-Host "  Uninstalling packages..." -ForegroundColor Gray
        python -m pip uninstall -y mutagen librosa numpy soundfile scipy watchdog 2>&1 | Out-Null
        Write-Host "  ✓ Packages removed" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Could not remove packages: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⊙ Keeping Python packages" -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  MP3 Service uninstalled" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "The service files remain in this directory." -ForegroundColor Gray
Write-Host "You can safely delete this folder if no longer needed." -ForegroundColor Gray
Write-Host ""

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
