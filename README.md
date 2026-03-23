# Mewgent

<p align="center">
  <img src="images/mewgent-logo.jpg" alt="Mewgent mascot — cat agent companion" width="420" />
</p>

> Live companion overlay for [Mewgenics](https://store.steampowered.com/app/686060/Mewgenics/) — real-time cat stats, breeding recommendations, and team management, right on top of your game.

**Windows:** [Download the latest release](https://github.com/ml-datadogs/mewgent/releases) — each version ships as `mewgent-vX.Y.Z-win64.zip` with `mewgent.exe` inside.

### Why Mewgent?

**The problem:** Mewgenics gives you a lot to juggle — stats, collars, room assignments, and breeding genetics. Without a second screen, that often means tabbing to wikis, notes, or spreadsheets and losing your place in the game.

**The solution:** Mewgent is a **live companion** that watches your save file and refreshes on a short interval. It shows cat stats, breeding pair scores, and roster context in an **always-on-top overlay** so you can decide without leaving the game. Optional **LLM** help adds plain-language breeding strategy on top of the built-in scoring.

| Team | Breeding |
| :---: | :---: |
| <img src="ui/public/mainscreens/team.png" alt="Team panel" width="380" /> | <img src="ui/public/mainscreens/breeding.png" alt="Breeding panel" width="380" /> |

---

## Features

- **Live save file watcher** — detects changes every 2 seconds, no manual refresh needed
- **Cat stats at a glance** — STR, DEX, CON, INT, SPD, CHA, LCK with visual charts
- **Breeding advisor** — scores every pair by class fit, stat synergy, and genetic traits
- **Team management** — track your roster, room assignments, and collar classes
- **LLM-powered advice** — optional OpenAI integration for natural language breeding strategy
- **Always-on-top overlay** — frameless, semi-transparent, toggle with `Ctrl+Shift+M`
- **Auto-detects your save file** — no manual path configuration needed

---

## Requirements

- **Prebuilt Windows zip** (see [Installation](#installation)): Windows 10/11 only. You do **not** need Python, uv, or Node — run `mewgent.exe` from the extracted folder.
- **Running from source** (clone + `uv run`): Windows 10/11 for the real save-file overlay; Python 3.11+ and [uv](https://docs.astral.sh/uv/). macOS/Linux work with `uv run python -m src.main --dev-ui` (mock data).

---

## Installation

### Prebuilt Windows (recommended)

Every [GitHub Release](https://github.com/ml-datadogs/mewgent/releases) for this repo includes a zip named like `mewgent-v1.0.0-win64.zip`. Download it, extract all files into a folder, and run `mewgent.exe`. No Python or build tools required.

### From source

```bash
# 1. Install uv (if not already installed)
# Windows (recommended):
winget install --id=astral-sh.uv
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone https://github.com/ml-datadogs/mewgent.git
cd mewgent

# 3. Install dependencies
uv sync

# 4. Run
uv run python -m src.main
```

The overlay will appear and auto-detect your Mewgenics save file.

---

## LLM advice (optional)

To enable AI-powered breeding recommendations, set your OpenAI API key and enable the feature in `config/settings.yaml`:

```yaml
llm:
  enabled: true
  model: "gpt-4o-mini"
```

Then create a `.env` file in the project root (use `.env.example` as a template):

```
OPENAI_API_KEY=sk-...
```

---

## Configuration

Edit `config/settings.yaml` to customize behavior:

| Key | Default | Description |
|---|---|---|
| `save_file.path` | `""` | Save file path — auto-detected if empty |
| `save_file.poll_interval_ms` | `2000` | How often to check for save changes |
| `llm.enabled` | `false` | Enable OpenAI-powered advice |
| `llm.model` | `"gpt-4o-mini"` | OpenAI model to use |
| `hotkey.toggle` | `"Ctrl+Shift+M"` | Hotkey to show/hide the overlay |
| `overlay.opacity` | `0.92` | Overlay transparency (0.0–1.0) |

---

## Development

### Developer documentation

- [Save file parsing](docs/save-parsing.md) — SQLite layout, LZ4 cat blobs, and how Mewgent reads `.sav` files

### Run with mock data (no game needed)

Works on macOS and Linux too:

```bash
uv run python -m src.main --dev-ui
```

### Frontend (React + TypeScript)

```bash
cd ui
npm install
npm run dev      # Vite dev server on port 5173
npm run build    # production build → ui/dist/
```

### Linting & type checking

```bash
ruff check .             # Python lint
ruff format --check .    # Python format check (no writes)
ty check                 # Python type check
cd ui && npm run lint    # TypeScript lint
```

### Tests

```bash
pytest
```

### Build release executable

```bash
cd ui && npm ci && npm run build && cd ..
uv run pyinstaller mewgent.spec --noconfirm
# Output: dist/mewgent/mewgent.exe
```

The spec embeds a Windows icon ([`images/mewgent.ico`](images/mewgent.ico)) and version metadata derived from [`pyproject.toml`](pyproject.toml) (File properties / Details in Explorer).

---

## Project structure

```
src/
  main.py          # Entry point
  capture/         # Save file watcher (real + mock)
  data/            # Save parser, stat extractor, collars, furniture
  breeding/        # Pair scoring and breeding calculator
  ui/              # PySide6 overlay + Qt WebChannel bridge
  llm/             # OpenAI advisor
  wiki/            # Game wiki scraper
  utils/           # Config loader, logging, update checker
ui/                # React + TypeScript frontend
config/            # settings.yaml
tests/             # pytest tests + fixtures
docs/              # Developer docs (e.g. save format)
```

---

## Disclaimer

Mewgent is an independent **read-only** companion: it reads your **local** Mewgenics save file to show stats and suggestions in an overlay. It does not modify game files or gameplay. **Use at your own risk.** This project is **not affiliated with or endorsed by** the Mewgenics developers or publishers. **You are responsible** for making sure your use complies with the game’s terms of service, EULA, and any other applicable rules.

---

## License

[MIT](LICENSE)
