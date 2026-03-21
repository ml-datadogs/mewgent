# Mewgent

**Live companion app for [Mewgenics](https://store.steampowered.com/app/Mewgenics)** — reads your save file and provides real-time cat stats, breeding advice, and team management.

## What it does

1. Watches your Mewgenics save file for changes
2. Parses cat stats (STR, DEX, CON, INT, SPD, CHA, LCK), abilities, classes, and more
3. Displays the latest info in a small always-on-top overlay
4. Provides LLM-powered breeding and team-building advice

## Requirements

- **Windows 10/11**
- **Python 3.11+** (managed by uv)
- **[uv](https://docs.astral.sh/uv/)** package manager

## Quick start

```bash
# 1. Install uv (if not already installed)
pip install uv

# 2. Clone and enter the project
cd mewgent

# 3. Sync dependencies
python -m uv sync

# 4. Run with GUI overlay
python -m uv run python -m src.main
```

Or use the convenience script:

```bash
run.bat
```

## Configuration

### `config/settings.yaml`

| Key | Default | Description |
|---|---|---|
| `database.path` | `"data/mewgent.db"` | SQLite database location |
| `save_file.enabled` | `true` | Enable save file watching |
| `save_file.path` | `""` | Save file path (auto-detected if empty) |
| `save_file.poll_interval_ms` | `2000` | Save file poll interval in milliseconds |
| `llm.enabled` | `true` | Enable LLM-powered advice |
| `llm.model` | `"gpt-5.4"` | LLM model to use |
| `hotkey.toggle` | `"Ctrl+Shift+M"` | Hotkey to toggle the overlay |

## Project structure

```
mewgent/
  pyproject.toml          # Dependencies and uv config
  config/
    settings.yaml         # App settings
  src/
    main.py               # Entry point
    capture/              # Save file watcher
    data/                 # Save parser, collar scoring
    ui/                   # PySide6 overlay + React UI bridge
    llm/                  # LLM-powered advisor
    wiki/                 # Wiki scraper for game data
    utils/                # Config loader, logging
  ui/                     # React frontend
  data/                   # SQLite database
```

## License

Personal use. Not affiliated with the Mewgenics developers.
