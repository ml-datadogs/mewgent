#!/usr/bin/env bash
# Start Vite (ui/) and Mewgent overlay in --dev-ui mode. Stops Vite when the app exits.
# Equivalent (Task): task dev
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ui"

if [[ ! -d node_modules ]]; then
  echo "Installing UI dependencies (npm install)…" >&2
  npm install
fi

npm run dev &
VITE_PID=$!

cleanup() {
  kill "$VITE_PID" 2>/dev/null || true
  wait "$VITE_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ready=0
for _ in $(seq 1 100); do
  if (echo >/dev/tcp/127.0.0.1/5173) &>/dev/null; then
    ready=1
    break
  fi
  sleep 0.1
done
if [[ "$ready" != 1 ]]; then
  echo "Vite did not become ready on http://127.0.0.1:5173" >&2
  exit 1
fi

cd "$ROOT"
uv run python -m src.main --dev-ui
