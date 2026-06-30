@echo off
setlocal
cd /d "%~dp0"

REM Prefer py launcher (selects newest installed Python, e.g. 3.13).
REM tomllib requires Python 3.11+, so a stale `python` on PATH (e.g. 3.10)
REM would fail with ModuleNotFoundError: No module named 'tomllib'.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 app.py
    if not errorlevel 1 goto :eof
    echo.
    echo Failed to start with py launcher, trying python...
)

python app.py
if not errorlevel 1 goto :eof

echo.
echo Failed to start application.
echo Please ensure Python 3.11+ is installed and available in PATH.
pause
exit /b 1
