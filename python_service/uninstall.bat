@echo off
REM MP3 Service Windows Uninstaller Launcher

echo.
echo ================================================================
echo   MP3 Service - Uninstaller
echo ================================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    echo.
    goto :run_uninstaller
) else (
    echo This uninstaller requires administrator privileges.
    echo Please right-click and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

:run_uninstaller
REM Run PowerShell uninstaller
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"

if %errorLevel% == 0 (
    echo.
    echo ================================================================
    echo   Uninstallation completed
    echo ================================================================
    echo.
) else (
    echo.
    echo ================================================================
    echo   Uninstallation failed. See errors above.
    echo ================================================================
    echo.
)

pause
