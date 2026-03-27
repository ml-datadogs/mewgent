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
  data/        # Save parser, collars, furniture; generated item_*_wiki.json (see docs/generated-data.md)
  breeding/    # Pair scoring and breeding calculator
  llm/         # OpenAI advisor (team / breeding / room; team prompt can use backpack+storage stash)
  ui/          # PySide6 overlay + QWebChannel bridge
  wiki/        # Game wiki scraper
  utils/       # Config loader, logging, update checker, LLM user key store
ui/            # React + TypeScript frontend
  src/
    components/  # React panels, Radix UI wrappers, assets
tools/         # Dev-only scripts (e.g. tools/generate_item_effects_wiki.py — not bundled)
scripts/       # Optional dev helpers (PowerShell / shell)
config/        # settings.yaml
tests/         # pytest tests + fixtures
docs/          # save-parsing.md, generated-data.md, …
Taskfile.yml   # task check:ui / check:python (mirrors CI)
```

## Development Commands

### Python backend

```bash
uv sync --dev                    # install dependencies (includes pytest; matches CI)
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

### Linting, type checking, and tests (Python)

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```

### Full CI surface locally

Install [Task](https://taskfile.dev/), then from the repo root:

```bash
uv sync --dev
task check:ui      # npm ci + eslint + production Vite build (in ui/)
task check:python  # ruff + format check + ty + pytest
# or: task check    # both, sequentially
```

If `task` is not on PATH (common on Windows without Task installed), run the same commands as in `Taskfile.yml` manually — see root [README.md](README.md) **Linting, type checking, and tests**.

### Regenerating wiki item JSON

```bash
uv run python tools/generate_item_effects_wiki.py
```

Writes `src/data/item_effects_wiki.json`, `item_icons_wiki.json`, `item_slots_wiki.json`. Details: [docs/generated-data.md](docs/generated-data.md).

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
- `llm.enabled` / `llm.model` / `llm.mock` — OpenAI integration (mock skips the API)
- `hotkey.toggle` — overlay toggle (default `Ctrl+Shift+M`)
- `logging.level` / `logging.file`

**OpenAI (BYOK):** The overlay can save an API key and default model under the app data directory (`openai_user_settings.json`). Otherwise `OPENAI_API_KEY` is used. The UI can run a lightweight connection check (`models.list`) after saving a key or via “Test connection.”

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

- **CI** (`ci.yml`): runs on all branches — two jobs via **Task**:
  - `task check:ui` — `npm ci`, `npm run lint`, `npm run build` in `ui/`
  - `uv sync --dev` then `task check:python` — `ruff check`, `ruff format --check`, `ty check`, `pytest`
- **Release** (`release.yml`): triggered on `v*` tags — builds React (`npm ci && npm run build`), packages exe via PyInstaller, uploads to GitHub Releases, deploys `version.json` to Cloudflare Pages

## Platform Notes

- **Production**: Windows 10/11 only (save file auto-detection uses Win32 APIs)
- **Development**: macOS/Linux supported via `--dev-ui` flag with mock data
