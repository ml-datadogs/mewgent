# CLAUDE.md

## Project Overview

**Mewgent** is a live companion overlay for the Steam game Mewgenics. It watches the game's save file for changes and displays a React UI overlay with cat stats, breeding recommendations, and team management.

## Architecture

- **Backend**: Python 3.11+ (PySide6 overlay, Qt WebChannel IPC bridge, save file parser)
- **Frontend**: React 19 + TypeScript + Tailwind CSS (rendered inside QWebEngineView)
- **IPC**: Qt WebChannel (`src/ui/bridge.py` ↔ React `QWebChannel` JS API)
- **Distribution**: PyInstaller bundles Python + `ui/dist/` into a single Windows exe

## Key Directories

```
src/           # Python backend
  capture/     # Save file watcher (real + mock)
  data/        # Save parser, stat extractor, collars, furniture
  breeding/    # Pair scoring and breeding calculator
  ui/          # PySide6 overlay + QWebChannel bridge
  wiki/        # Game wiki scraper
  utils/       # Config loader, logging, update checker
ui/            # React + TypeScript frontend
  src/
    components/  # 17 React components
config/        # settings.yaml
tests/         # pytest tests + fixtures
```

## Development Commands

### Python backend

```bash
uv sync                          # install dependencies
uv run python -m src.main        # run with real save file
uv run python -m src.main --dev-ui  # run with mock data (no game needed)
```

### Frontend

```bash
cd ui
npm install
npm run dev      # Vite dev server on port 5173
npm run build    # production build → ui/dist/
npm run lint     # ESLint
```

### Linting & type checking

```bash
ruff check .              # Python lint
ruff format --check .     # Python format check
ty check                  # Python type check
```

### Tests

```bash
pytest
```

### Build release exe

```bash
cd ui && npm ci && npm run build && cd ..
uv run pyinstaller mewgent.spec --noconfirm
# Output: dist/mewgent/mewgent.exe
```

## Configuration

`config/settings.yaml` controls:
- `save_file.path` — auto-detected if empty
- `save_file.poll_interval_ms` — default 2000
- `llm.enabled` / `llm.model` — OpenAI integration
- `hotkey.toggle` — overlay toggle (default `Ctrl+Shift+M`)
- `logging.level` / `logging.file`

## Tech Stack

| Layer | Tech |
|---|---|
| UI framework | React 19, Vite 8, TypeScript 5.9, Tailwind CSS 4 |
| UI components | Radix UI, Framer Motion, Recharts |
| Desktop shell | PySide6 (Qt6), QWebEngineView |
| IPC | Qt WebChannel (WebSocket) |
| Save parsing | lz4 decompression |
| LLM | OpenAI API |
| Wiki scraping | httpx, BeautifulSoup4 |
| Testing | pytest |
| Linting | ruff, ty (Python), ESLint (TS) |
| Packaging | PyInstaller |
| Package manager | uv (Python), npm (JS) |

## CI/CD

- **CI** (`ci.yml`): runs on all branches — `ruff check`, `ruff format --check`, `ty check`, `npm run lint`
- **Release** (`release.yml`): triggered on `v*` tags — builds React (`npm ci && npm run build`), packages exe via PyInstaller, uploads to GitHub Releases, deploys `version.json` to Cloudflare Pages

## Platform Notes

- **Production**: Windows 10/11 only (save file auto-detection uses Win32 APIs)
- **Development**: macOS/Linux supported via `--dev-ui` flag with mock data
