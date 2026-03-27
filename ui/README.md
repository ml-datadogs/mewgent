# Mewgent overlay UI

React 19 + TypeScript + Vite + Tailwind. The production bundle is loaded by the PySide6 `QWebChannel` host from `ui/dist/`.

## Commands

```bash
npm install    # or npm ci in CI
npm run dev    # Vite on http://localhost:5173
npm run build  # output → ui/dist/
npm run lint   # ESLint
```

## Types and bridge

Payload shapes mirror the Python bridge (`src/ui/bridge.py`). Inventory and equipment entries include `item_id`, `effect`, `icon_url`, and `slot` (wiki slot when known).

See the repository root [README.md](../README.md) and [CLAUDE.md](../CLAUDE.md) for full-stack development and CI.
