@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-ui-dist.ps1" -ProjectRoot "%CD%"
if errorlevel 1 (
    echo UI build failed.
    pause
    exit /b 1
)

echo Starting Mewgent...
python -m uv run python -m src.main %*
pause
