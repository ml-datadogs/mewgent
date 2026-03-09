@echo off
set PYTHONPATH=%~dp0
echo Starting Mewgent...
python -m uv run python -m src.main %*
pause
