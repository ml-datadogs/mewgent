"""Mewgenics .sav file reader.

The .sav file is a SQLite database with LZ4-compressed cat data blobs.
This module reads the save file and extracts all cat information.

Format discovered through reverse engineering:
- SQLite with STRICT tables: cats, files, furniture, properties, winning_teams
- Cat blobs: 4-byte LE uncompressed size + LZ4 block compressed flat data
- Flat cat data: header, hash, UTF-16LE name, class, DNA floats, mutations,
  level, age, gender/voice string, breed float, 7 base stats, abilities, passives
"""

from __future__ import annotations

import logging
import os
import sqlite3
import struct
from dataclasses import dataclass, field
from pathlib import Path

import lz4.block

log = logging.getLogger("mewgent.data.save_reader")

MEWGENICS_SAVE_DIR = Path(os.environ.get("APPDATA", "")) / "Glaiel Games" / "Mewgenics"

STAT_ORDER = ["str", "dex", "con", "int", "spd", "cha", "lck"]

KNOWN_CLASSES = frozenset({
    "None", "Fighter", "Hunter", "Mage", "Medic", "Tank", "Thief",
    "Necromancer", "Colorless", "Druid", "Butcher", "Tinkerer",
    "robotom", "terminator",
})


@dataclass
class SaveCat:
    """A cat parsed from the save file."""

    db_key: int = 0
    name: str = ""
    level: int = 0
    age: int = 0
    gender: str = ""
    active_class: str = ""
    base_str: int = 0
    base_dex: int = 0
    base_con: int = 0
    base_int: int = 0
    base_spd: int = 0
    base_cha: int = 0
    base_lck: int = 0
    abilities: list[str] = field(default_factory=list)
    passives: list[str] = field(default_factory=list)
    status: str = "unknown"  # in_house | historical | dead
    breed_coefficient: float = 0.0


@dataclass
class SaveData:
    """All data read from a Mewgenics save file."""

    cats: list[SaveCat] = field(default_factory=list)
    house_cat_keys: set[int] = field(default_factory=set)
    unlocked_classes: list[str] = field(default_factory=list)
    unlocked_abilities: list[str] = field(default_factory=list)
    unlocked_passives: list[str] = field(default_factory=list)
    current_day: int = 0
    house_gold: int = 0
    house_food: int = 0
    owner_steamid: str = ""
    save_path: str = ""

    @property
    def house_cats(self) -> list[SaveCat]:
        """Only cats currently in the player's house."""
        return [c for c in self.cats if c.status == "in_house"]


def find_save_files() -> list[Path]:
    """Auto-detect Mewgenics save files on the system."""
    results: list[Path] = []
    if not MEWGENICS_SAVE_DIR.exists():
        return results

    for steam_id_dir in MEWGENICS_SAVE_DIR.iterdir():
        if not steam_id_dir.is_dir():
            continue
        saves_dir = steam_id_dir / "saves"
        if not saves_dir.exists():
            continue
        for sav in sorted(saves_dir.glob("*.sav")):
            results.append(sav)
    return results


def _decompress_blob(blob: bytes) -> bytes | None:
    """Decompress an LZ4-compressed blob from the cats table."""
    if len(blob) < 8:
        return None
    uncompressed_size = struct.unpack_from("<I", blob, 0)[0]
    if uncompressed_size <= 0 or uncompressed_size > 100_000:
        return None
    try:
        return lz4.block.decompress(blob[4:], uncompressed_size=uncompressed_size)
    except Exception:
        log.debug("LZ4 decompress failed for blob of %d bytes", len(blob))
        return None


def _find_i64_strings(data: bytes, start: int = 0) -> list[tuple[int, int, str]]:
    """Find all i64-length-prefixed ASCII strings in flat cat data."""
    results: list[tuple[int, int, str]] = []
    p = start
    while p + 8 < len(data):
        slen = struct.unpack_from("<q", data, p)[0]
        if 1 <= slen <= 60 and p + 8 + slen <= len(data):
            raw = data[p + 8 : p + 8 + slen]
            try:
                s = raw.decode("ascii")
            except UnicodeDecodeError:
                p += 1
                continue
            if s.isprintable():
                results.append((p, slen, s))
                p += 8 + slen
                continue
        p += 1
    return results


def _parse_house_keys(cursor: sqlite3.Cursor) -> set[int]:
    """Extract cat keys from the house_state blob in the files table.

    Structure: u32 unknown, u32 count, then records at stride 52 starting
    at offset 8 where the first u32 of each record is the cat_key.
    """
    try:
        row = cursor.execute(
            "SELECT data FROM files WHERE key = 'house_state'"
        ).fetchone()
    except sqlite3.Error:
        log.warning("Failed to read house_state")
        return set()
    if not row or not row[0]:
        return set()

    blob: bytes = row[0]
    if len(blob) < 8:
        return set()

    count = struct.unpack_from("<I", blob, 4)[0]
    keys: set[int] = set()
    for i in range(count):
        offset = 8 + i * 52
        if offset + 4 > len(blob):
            break
        val = struct.unpack_from("<I", blob, offset)[0]
        if 1 <= val <= 10_000:
            keys.add(val)

    log.debug("house_state: %d cat keys", len(keys))
    return keys


def _parse_unlocks(cursor: sqlite3.Cursor) -> tuple[list[str], list[str], list[str]]:
    """Parse the unlocks blob to extract unlocked classes, abilities, passives.

    Structure: u32 num_categories, then for each category:
      u32 count, u32 padding, then count x [i64 len][ascii string]
    Category 1 = classes, 2 = active abilities, 3 = passive abilities.
    """
    try:
        row = cursor.execute(
            "SELECT data FROM files WHERE key = 'unlocks'"
        ).fetchone()
    except sqlite3.Error:
        log.warning("Failed to read unlocks")
        return [], [], []
    if not row or not row[0]:
        return [], [], []

    blob: bytes = row[0]
    if len(blob) < 4:
        return [], [], []

    categories: list[list[str]] = []
    p = 0
    num_cats = struct.unpack_from("<I", blob, p)[0]
    p += 4

    for _ in range(num_cats):
        if p + 8 > len(blob):
            break
        count = struct.unpack_from("<I", blob, p)[0]
        p += 4
        _padding = struct.unpack_from("<I", blob, p)[0]
        p += 4

        entries: list[str] = []
        for _ in range(count):
            if p + 8 > len(blob):
                break
            slen = struct.unpack_from("<q", blob, p)[0]
            p += 8
            if p + slen > len(blob) or slen <= 0:
                break
            entries.append(blob[p : p + slen].decode("ascii", errors="replace"))
            p += slen
        categories.append(entries)

    classes = categories[0] if len(categories) > 0 else []
    abilities = categories[1] if len(categories) > 1 else []
    passives = categories[2] if len(categories) > 2 else []

    log.debug(
        "unlocks: %d classes, %d abilities, %d passives",
        len(classes), len(abilities), len(passives),
    )
    return classes, abilities, passives


def _parse_flat_cat(data: bytes, db_key: int) -> SaveCat | None:
    """Parse a decompressed flat cat record.

    Layout (discovered by reverse engineering against save_file_cat):
      @0: u32 header
      @4: 8-byte unique hash
      @12: u64 name_length (in UTF-16 chars)
      @20: UTF-16LE name + zero padding
      ...
      String[0]: initial class (usually "None")
      ... binary mutation/genetics data ...
      @(S2-8): i32 level
      @(S2-4): i32 age
      String[1]: gender+voice or active_class name (e.g. "male78", "robotom")
      After String[1]: f64 breed value, then 7 x i32 base stats
      String[2]: skin/palette name (e.g. "none")
      String[3..]: abilities (DefaultMove, BasicMelee, ...), passives, "Colorless"
    """
    if len(data) < 100:
        return None

    cat = SaveCat(db_key=db_key)

    # Name
    try:
        name_len = struct.unpack_from("<q", data, 12)[0]
        if 0 < name_len < 50:
            cat.name = data[20 : 20 + name_len * 2].decode("utf-16-le", errors="replace").rstrip("\x00")
    except (struct.error, UnicodeDecodeError):
        return None

    if not cat.name:
        return None

    strings = _find_i64_strings(data, 20 + max(0, struct.unpack_from("<q", data, 12)[0]) * 2)
    if len(strings) < 2:
        return None

    # String[0] = initial class
    initial_class = strings[0][2]

    # String[1] = gender+voice or active class
    s1_offset, s1_len, s1_text = strings[1]

    # Level and age are the two i32 values immediately before String[1]
    if s1_offset >= 8:
        cat.level = struct.unpack_from("<i", data, s1_offset - 8)[0]
        cat.age = struct.unpack_from("<i", data, s1_offset - 4)[0]

    # Sanitize: level/age should be in reasonable range
    if cat.level < 0 or cat.level > 200:
        cat.level = 0
    if cat.age < 0 or cat.age > 200:
        cat.age = 0

    # Determine gender and active class from s1_text
    if s1_text.startswith("female"):
        cat.gender = "female"
    elif s1_text.startswith("male"):
        cat.gender = "male"

    if s1_text in KNOWN_CLASSES:
        cat.active_class = s1_text
    else:
        cat.active_class = initial_class

    # Breed coefficient (f64) sits right after String[1] data
    breed_offset = s1_offset + 8 + s1_len
    if breed_offset + 8 <= len(data):
        breed_val = struct.unpack_from("<d", data, breed_offset)[0]
        if 0.0 <= breed_val <= 1.0:
            cat.breed_coefficient = breed_val

    # Base stats: after the 8-byte f64 breed value
    stats_offset = breed_offset + 8
    if stats_offset + 28 <= len(data):
        base_vals = [struct.unpack_from("<i", data, stats_offset + i * 4)[0] for i in range(7)]
        if all(-10 <= v <= 30 for v in base_vals):
            cat.base_str = base_vals[0]
            cat.base_dex = base_vals[1]
            cat.base_con = base_vals[2]
            cat.base_int = base_vals[3]
            cat.base_spd = base_vals[4]
            cat.base_cha = base_vals[5]
            cat.base_lck = base_vals[6]

    # Abilities and passives from remaining strings
    for _, _, s in strings[3:]:
        if s in ("None", "Colorless", "none"):
            continue
        if s.startswith("Basic") or s == "DefaultMove":
            continue
        cat.abilities.append(s)

    # Find the actual class from the end of the string list
    # The very last meaningful string (not "Colorless"/"None") might be the class
    for _, _, s in reversed(strings):
        if s in KNOWN_CLASSES and s not in ("None", "Colorless"):
            cat.active_class = s
            break

    return cat


def read_save(path: str | Path) -> SaveData:
    """Read a Mewgenics .sav file and return parsed data.

    Requires SQLite >= 3.37.0 for STRICT table support.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Save file not found: {path}")

    result = SaveData(save_path=str(path))

    conn = sqlite3.connect(str(path))
    try:
        cursor = conn.cursor()

        # Properties
        try:
            for key, val in cursor.execute("SELECT key, data FROM properties"):
                if key == "current_day" and isinstance(val, int):
                    result.current_day = val
                elif key == "house_gold" and isinstance(val, int):
                    result.house_gold = val
                elif key == "house_food" and isinstance(val, int):
                    result.house_food = val
                elif key == "owner_steamid" and isinstance(val, str):
                    result.owner_steamid = val
        except sqlite3.Error:
            log.warning("Failed to read properties table")

        # House state and unlocks
        house_keys = _parse_house_keys(cursor)
        result.house_cat_keys = house_keys

        classes, abilities, passives = _parse_unlocks(cursor)
        result.unlocked_classes = classes
        result.unlocked_abilities = abilities
        result.unlocked_passives = passives

        # Cats
        try:
            for db_key, blob in cursor.execute("SELECT key, data FROM cats ORDER BY key"):
                if blob is None:
                    continue
                flat = _decompress_blob(blob)
                if flat is None:
                    log.debug("Failed to decompress cat #%d", db_key)
                    continue
                cat = _parse_flat_cat(flat, db_key)
                if cat is None:
                    log.debug("Failed to parse cat #%d", db_key)
                    continue

                if db_key in house_keys:
                    cat.status = "in_house"
                elif cat.age == 0:
                    cat.status = "dead"
                else:
                    cat.status = "historical"

                result.cats.append(cat)
        except sqlite3.Error:
            log.warning("Failed to read cats table")

    finally:
        conn.close()

    house_count = sum(1 for c in result.cats if c.status == "in_house")
    log.info(
        "Read save '%s': %d cats (%d in house), day %d, %d classes unlocked",
        path.name, len(result.cats), house_count,
        result.current_day, len(result.unlocked_classes),
    )
    return result
