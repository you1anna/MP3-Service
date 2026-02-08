@echo off
REM MP3 Service Windows Installer Launcher
REM This batch file launches the PowerShell installer with proper permissions

echo.
echo ================================================================
echo   MP3 Service - Windows Installer
echo ================================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    echo.
    goto :run_installer
) else (
    echo This installer requires administrator privileges.
    echo Please right-click and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

:run_installer
REM Run PowerShell installer
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if %errorLevel% == 0 (
    echo.
    echo ================================================================
    echo   Installation completed successfully!
    echo ================================================================
    echo.
) else (
    echo.
    echo ================================================================
    echo   Installation failed. See errors above.
    echo ================================================================
    echo.
)

pause
