@echo off
setlocal
cd /d "%~dp0"

set "ELEVATE_ARGS=%*"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent()); if ($p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator privileges for the mobile portal...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%ComSpec%' -Verb RunAs -WorkingDirectory '%~dp0' -ArgumentList '/c','\"\"%~f0\"\" %ELEVATE_ARGS%'" >nul 2>&1
    if errorlevel 1 (
        echo Administrator elevation was canceled.
        pause
    )
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$svc = Get-Service -Name Tailscale -ErrorAction SilentlyContinue; if ($svc -and $svc.Status -ne 'Running') { Start-Service -Name Tailscale -ErrorAction SilentlyContinue }" >nul 2>&1

python mobile_portal.py
if not errorlevel 1 goto :eof

echo.
echo Failed to start with python, trying py launcher...
py -3 mobile_portal.py
if not errorlevel 1 goto :eof

echo.
echo Failed to start mobile portal.
echo Please ensure Python 3.11+ is installed and available in PATH.
pause
exit /b 1
