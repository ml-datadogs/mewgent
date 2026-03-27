# Shell helpers

| File | Purpose |
|------|---------|
| [`dev-ui.sh`](dev-ui.sh) | Convenience script for Unix-like dev (Vite + backend); optional. |
| [`ensure-ui-dist.ps1`](ensure-ui-dist.ps1) | Ensures `ui/dist` exists before packaging (Windows). |

The canonical local CI surface is [`Taskfile.yml`](../Taskfile.yml) at the repo root (`task check` when [Task](https://taskfile.dev/) is installed).
