# Generated data files (`src/data`)

Some assets under `src/data/` are **checked in** and **bundled** with the app (see `mewgent.spec` `datas`). They are produced by tooling rather than hand-edited.

## Wiki-derived item tables

| File | Contents |
|------|----------|
| `item_effects_wiki.json` | Plain-text effect descriptions per wiki row key (PascalCase). |
| `item_icons_wiki.json` | Absolute `ITEM_*.svg` icon URLs on wiki.gg. |
| `item_slots_wiki.json` | Wiki **Slot** column (Weapon, Head, Face, Neck, Trinket, Consumable, …). |

**Regenerate** (overwrites all three):

```bash
uv run python tools/generate_item_effects_wiki.py
```

Runtime lookup and WebChannel payloads use [`src/data/item_effects.py`](../src/data/item_effects.py) (`ITEM_ID_ALIASES`, `item_effect_for_id`, `item_slot_for_id`, `item_effect_entry`). Save files use internal ids that usually match wiki keys; aliases cover known mismatches.

## Wiki markdown for the LLM advisor (`wiki_data/text/`)

The `.md` files here are **checked in** so the LLM has class/stat/ability/breeding context without scraping. Root `.gitignore` ignores only `wiki_data/images/` (large scraper downloads). [`LLMAdvisor`](../src/llm/advisor.py) reads `stats.md`, `classes.md`, `abilities.md`, and `breeding.md` when present.

**Generate or refresh** (network required; Classes downloads many images and can take a few minutes):

```bash
uv run python -m src.wiki
```

Only advisor-relevant text (faster if you skip `house`):

```bash
uv run python -m src.wiki --pages stats classes abilities breeding
```

Output layout: `wiki_data/text/<name>.md` (tracked) and images under `wiki_data/images/<name>/` (gitignored). The advisor only needs the `.md` files for context; class icons for the legacy Qt overlay use `wiki_data/images/classes/` when present locally.

## Other `src/data/` modules

Python modules here (`save_reader.py`, `collars.py`, `furniture_stats.py`, …) are normal source code, not generated.
