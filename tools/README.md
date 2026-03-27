# Developer tools

Scripts in this folder are **not** imported by the packaged app. Run them from the **repository root** with `uv run python …` so imports and paths resolve correctly.

| Script | Purpose |
|--------|---------|
| [`generate_item_effects_wiki.py`](generate_item_effects_wiki.py) | Fetches the [Items](https://mewgenics.wiki.gg/wiki/Items) wiki table and writes generated JSON under `src/data/` (effects, icon URLs, slot column). See [`docs/generated-data.md`](../docs/generated-data.md). |
| [`investigate_house.py`](investigate_house.py) | Ad-hoc save / house blob inspection (development). |
| [`test_save_reader.py`](test_save_reader.py) | Manual harness for save parsing (development). |

```bash
uv run python tools/generate_item_effects_wiki.py
```
