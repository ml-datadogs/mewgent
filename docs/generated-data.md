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

## Other `src/data/` modules

Python modules here (`save_reader.py`, `collars.py`, `furniture_stats.py`, …) are normal source code, not generated.
