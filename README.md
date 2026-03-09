# Mewgent

**Live companion app for [Mewgenics](https://store.steampowered.com/app/Mewgenics)** — reads cat stats directly from your screen and saves them to a local database.

## What it does

1. Binds to the Mewgenics game window
2. Captures screenshots in real-time (~1 FPS)
3. Detects when you're viewing a cat stats screen
4. Runs GPU-accelerated OCR (EasyOCR + CUDA) on configured screen regions
5. Parses cat name and all seven stats (STR, DEX, CON, INT, SPD, CHA, LCK)
6. Skips duplicates (perceptual hash + field fingerprint)
7. Saves results to a local SQLite database
8. Displays the latest cat info in a small always-on-top overlay

## Requirements

- **Windows 10/11**
- **Python 3.11+** (managed by uv)
- **NVIDIA GPU with CUDA 12.1** (RTX 3080 recommended) — falls back to CPU if unavailable
- **[uv](https://docs.astral.sh/uv/)** package manager

## Quick start

```bash
# 1. Install uv (if not already installed)
pip install uv

# 2. Clone and enter the project
cd mewgent

# 3. Sync dependencies (first run downloads ~2GB for PyTorch + EasyOCR models)
python -m uv sync

# 4. Run with GUI overlay
python -m uv run python -m src.main

# 5. Or run headless (no overlay, CLI output only)
python -m uv run python -m src.main --headless
```

Or use the convenience script:

```bash
run.bat
```

## Configuration

### `config/settings.yaml`

| Key | Default | Description |
|---|---|---|
| `capture.window_title` | `"Mewgenics"` | Window title substring to match |
| `capture.interval_ms` | `1000` | Capture interval in milliseconds |
| `ocr.gpu` | `true` | Use CUDA GPU for EasyOCR |
| `database.path` | `"data/mewgent.db"` | SQLite database location |
| `debug.save_screenshots` | `true` | Save every captured frame to `debug_screenshots/` |

### `config/regions.yaml`

Defines the pixel rectangles for each stat field at reference resolution (1920x1080). After your first run, check `debug_screenshots/` and adjust the `rect: [x, y, w, h]` values to match your game's UI layout.

### Scene template

Place a cropped screenshot of the cat stats screen header as `templates/cat_stats_header.png`. This is used for template matching to detect when you're on the cat stats screen.

## Region calibration

Run the calibration tool to verify your region config:

```bash
python -m uv run python -c "
from src.utils.config_loader import load_config, PROJECT_ROOT
from src.capture.window_bind import WindowBinder
from src.capture.screen_grab import ScreenGrabber
from src.ui.debug_panel import save_calibration_image

cfg = load_config()
binder = WindowBinder(cfg.capture.window_title)
binder.wait_for_window(timeout=10)
grabber = ScreenGrabber()
frame = grabber.capture(binder.hwnd)
if frame is not None:
    save_calibration_image(frame, cfg.regions.regions)
    print('Saved: debug_screenshots/calibration.png')
"
```

Open `debug_screenshots/calibration.png` and check that the green rectangles align with the stat fields.

## Project structure

```
mewgent/
  pyproject.toml          # Dependencies and uv config
  config/
    settings.yaml         # App settings
    regions.yaml          # OCR region definitions
  templates/              # Scene detection reference images
  src/
    main.py               # Entry point
    capture/              # Window binding + screen capture
    vision/               # Scene detection, region crop, OCR
    data/                 # Stat parsing, dedup, SQLite
    ui/                   # PySide6 overlay + debug tools
    utils/                # Config loader, logging
  debug_screenshots/      # Auto-saved frames
  data/                   # SQLite database
```

## Architecture

```
WindowBinder → ScreenGrabber → SceneDetector → RegionCropper → OCREngine
                                                                    ↓
                                               OverlayWindow ← SQLiteStore ← DuplicateGuard ← StatParser
```

## Duplicate detection

Three layers prevent redundant data:

1. **Frame pHash** — skips re-OCR if the screen hasn't changed
2. **Field fingerprint** — skips DB write if parsed stats are identical
3. **DB UNIQUE constraint** — final safety net on `(cat_name, snapshot_hash)`

## License

Personal use. Not affiliated with the Mewgenics developers.
