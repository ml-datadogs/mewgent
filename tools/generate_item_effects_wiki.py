"""Fetch https://mewgenics.wiki.gg/wiki/Items and write data files.

Outputs:

- ``src/data/item_effects_wiki.json`` — description text per wiki row key.
- ``src/data/item_icons_wiki.json`` — absolute icon URLs (``ITEM_*.svg``) per same key.
- ``src/data/item_slots_wiki.json`` — wiki **Slot** column (Weapon, Head, Trinket, …) per same key.

Run from repo root after wiki updates:

  uv run python tools/generate_item_effects_wiki.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "item_effects_wiki.json"
OUT_ICONS = ROOT / "src" / "data" / "item_icons_wiki.json"
OUT_SLOTS = ROOT / "src" / "data" / "item_slots_wiki.json"
WIKI_ORIGIN = "https://mewgenics.wiki.gg"


def _enrich_shield_spans(cell: Tag) -> None:
    """Append ``Shield`` after ``+N`` when the wiki shows only the shield icon (no text).

    Some rows (e.g. Cursed Rock) use ``+6`` + ``/wiki/Shield`` icon; others (Rock Hat) also
    include a literal ``Shield`` span — we replace the icon cluster and normalize to ``+6 Shield``.
    """
    for a in list(cell.select('a[href="/wiki/Shield"]')):
        root = a.find_parent(
            "span", style=lambda v: bool(v) and "inline-flex" in str(v)
        )
        if root is None:
            root = a.find_parent("span")
        if root is None:
            continue
        label = str(a.get("title") or "Shield").strip() or "Shield"
        prev = root.previous_sibling
        while (
            prev is not None
            and isinstance(prev, NavigableString)
            and not str(prev).strip()
        ):
            prev = prev.previous_sibling
        if isinstance(prev, NavigableString):
            s = str(prev)
            m = re.search(r"([+-]?\d+)\s*$", s)
            if m:
                new_s = s[: m.end(1)] + f" {label}" + s[m.end(1) :]
                prev.replace_with(new_s)
        root.decompose()


def _enrich_inline_stat_spans(cell: Tag) -> None:
    """Turn ``-99`` + Luck icon into ``-99 Luck`` (stat name from ``img alt`` / link).

    The Items table uses ``<span class="inline-stat">`` with a ``/wiki/Stats#…`` link
    and a stat icon; stripping images alone drops which stat the number applies to.
    """
    for span in cell.select("span.inline-stat"):
        a = span.find("a", href=True)
        if not a:
            continue
        href = a.get("href") or ""
        if "/wiki/Stats" not in href:
            continue
        img = a.find("img")
        stat = ""
        if img and img.get("alt"):
            stat = str(img["alt"]).strip()
        if not stat:
            stat = str(a.get("title") or "").strip()
        if not stat:
            continue
        prefix = ""
        for child in list(span.children):
            if child is a:
                break
            if isinstance(child, NavigableString):
                prefix += str(child)
            elif isinstance(child, Tag):
                prefix += child.get_text(strip=True)
        prefix = " ".join(prefix.split())
        label = f"{prefix} {stat}" if prefix else stat
        span.clear()
        span.append(label)


def _cell_description_text(cell: Tag) -> str:
    """Plain text for the Description column.

    Wiki wraps stat lines in ``<span class="inline-stat">``; ``get_text(strip=True)``
    concatenates siblings with no separator, so ``+6`` and ``-99`` become the
    misleading ``+6-99``. Shield bonuses often use ``/wiki/Shield`` icons without the
    word ``Shield`` in HTML. We label those, then stat icons, then join with spaces.
    """
    _enrich_shield_spans(cell)
    _enrich_inline_stat_spans(cell)
    raw = cell.get_text(" ", strip=True)
    raw = re.sub(r"\s*,\s*", ", ", raw)
    raw = re.sub(r" {2,}", " ", raw).strip()
    return raw


def display_to_internal_key(name: str) -> str:
    name = name.split("(")[0].strip()
    chunks = re.split(r"[\s\-]+", name)
    out: list[str] = []
    for ch in chunks:
        ch = ch.strip("'")
        if not ch or not ch[0].isalnum():
            continue
        if ch.isupper() and len(ch) <= 4:
            out.append(ch)
        else:
            out.append(ch[0].upper() + ch[1:])
    return "".join(out)


def _absolute_item_icon_url(image_cell: Tag) -> str | None:
    """First column of the Items table: ``ITEM_*.svg`` under ``/images/``."""
    img = image_cell.find("img")
    if not img:
        return None
    src = str(img.get("src") or "").strip()
    if not src:
        return None
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return WIKI_ORIGIN + src
    if src.startswith("http"):
        return src
    return None


def row_key(display_name: str) -> str:
    """Stable id for JSON: disambiguate ``Broken Mirror (Trinket)`` vs ``(Head Armor)``."""
    if "(" not in display_name:
        return display_to_internal_key(display_name)
    main = display_name.split("(", 1)[0].strip()
    variant = display_name.split("(", 1)[1].split(")", 1)[0].strip()
    return f"{display_to_internal_key(main)}_{display_to_internal_key(variant)}"


def main() -> int:
    r = httpx.get(
        "https://mewgenics.wiki.gg/wiki/Items",
        timeout=120.0,
        follow_redirects=True,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table", class_=lambda c: c and "wikitable" in c)
    if len(tables) < 2:
        print("Expected second wikitable for Items list", file=sys.stderr)
        return 1
    t = tables[1]
    wiki_map: dict[str, str] = {}
    wiki_icons: dict[str, str] = {}
    wiki_slots: dict[str, str] = {}
    for row in t.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue
        disp = cells[1].get_text(strip=True)
        desc = _cell_description_text(cells[5])
        if not disp or not desc:
            continue
        key = row_key(disp)
        if key in wiki_map:
            continue
        wiki_map[key] = desc
        icon_url = _absolute_item_icon_url(cells[0])
        if icon_url:
            wiki_icons[key] = icon_url
        slot = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
        if slot:
            wiki_slots[key] = slot

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(wiki_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUT_ICONS.write_text(
        json.dumps(wiki_icons, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUT_SLOTS.write_text(
        json.dumps(wiki_slots, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(wiki_map)} entries to {OUT}")
    print(f"Wrote {len(wiki_icons)} icon URLs to {OUT_ICONS}")
    print(f"Wrote {len(wiki_slots)} slots to {OUT_SLOTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
