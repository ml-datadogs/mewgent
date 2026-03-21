"""Mewgenics .sav file reader.

The .sav file is a SQLite database with LZ4-compressed cat data blobs.
This module reads the save file and extracts all cat information.

Binary format based on MewgenicsBreedingManager's proven reverse-engineering:
- SQLite with STRICT tables: cats, files, furniture, properties, winning_teams
- Cat blobs: 4-byte LE uncompressed size + LZ4 block compressed flat data
- Flat cat data parsed sequentially via BinaryReader: breed_id, uid, name,
  name_tag, parent UIDs, collar, visual mutations, gender, stats,
  personality traits, abilities, passives, disorders
- Save-level blobs: house_state (room assignments), adventure_state,
  house_unlocks, pedigree (parent/child map)
"""

from __future__ import annotations

import builtins
import logging
import math
import os
import re
import sqlite3
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeGuard

import lz4.block

log = logging.getLogger("mewgent.data.save_reader")

MEWGENICS_SAVE_DIR = Path(os.environ.get("APPDATA", "")) / "Glaiel Games" / "Mewgenics"

STAT_ORDER = ["str", "dex", "con", "int", "spd", "cha", "lck"]

KNOWN_CLASSES = frozenset(
    {
        "None",
        "Fighter",
        "Hunter",
        "Mage",
        "Medic",
        "Tank",
        "Thief",
        "Necromancer",
        "Colorless",
        "Druid",
        "Butcher",
        "Tinkerer",
        "robotom",
        "terminator",
    }
)

ROOM_DISPLAY = {
    "Floor1_Large": "Ground Floor Left",
    "Floor1_Small": "Ground Floor Right",
    "Floor2_Large": "Second Floor Right",
    "Floor2_Small": "Second Floor Left",
    "Attic": "Attic",
}

ROOM_KEYS = tuple(ROOM_DISPLAY.keys())

_JUNK_STRINGS = frozenset({"none", "null", "", "defaultmove", "default_move"})
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_VISUAL_MUTATION_FIELDS = [
    ("fur", 0),
    ("body", 3),
    ("head", 8),
    ("tail", 13),
    ("leg_L", 18),
    ("leg_R", 23),
    ("arm_L", 28),
    ("arm_R", 33),
    ("eye_L", 38),
    ("eye_R", 43),
    ("eyebrow_L", 48),
    ("eyebrow_R", 53),
    ("ear_L", 58),
    ("ear_R", 63),
    ("mouth", 68),
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _valid_str(s: str | None) -> TypeGuard[str]:
    return bool(s) and s.strip().lower() not in _JUNK_STRINGS


def _normalize_gender(raw_gender: str | None) -> str:
    g = (raw_gender or "").strip().lower()
    if g.startswith("male"):
        return "male"
    if g.startswith("female"):
        return "female"
    if g == "spidercat":
        return "?"
    return "?"


# ── BinaryReader ──────────────────────────────────────────────────────────────


class _BinaryReader:
    """Stateful little-endian binary reader for cat blob parsing."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def u64(self) -> int:
        lo, hi = struct.unpack_from("<II", self.data, self.pos)
        self.pos += 8
        return lo + hi * 4_294_967_296

    def f64(self) -> float:
        v = struct.unpack_from("<d", self.data, self.pos)[0]
        self.pos += 8
        return v

    def str(self) -> builtins.str | None:
        start = self.pos
        try:
            length = self.u64()
            if length > 10_000:
                self.pos = start
                return None
            s = self.data[self.pos : self.pos + int(length)].decode(
                "utf-8", errors="ignore"
            )
            self.pos += int(length)
            return s
        except Exception:
            self.pos = start
            return None

    def utf16str(self) -> builtins.str:
        char_count = self.u64()
        byte_len = int(char_count * 2)
        s = self.data[self.pos : self.pos + byte_len].decode(
            "utf-16le", errors="ignore"
        )
        self.pos += byte_len
        return s

    def skip(self, n: int) -> None:
        self.pos += n

    def seek(self, n: int) -> None:
        self.pos = n

    def remaining(self) -> int:
        return len(self.data) - self.pos


# ── Data classes ──────────────────────────────────────────────────────────────


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
    status: str = "unknown"  # in_house | adventure | historical | dead | retired
    breed_coefficient: float = 0.0
    retired: bool = False

    unique_id: str = ""
    breed_id: int = 0
    name_tag: str = ""
    collar: str = ""
    gender_source: str = ""
    stat_mod: list[int] = field(default_factory=list)
    stat_sec: list[int] = field(default_factory=list)
    total_stats: dict[str, int] = field(default_factory=dict)
    aggression: float | None = None
    libido: float | None = None
    inbredness: float | None = None
    disorders: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    visual_mutation_ids: list[int] = field(default_factory=list)
    body_parts: dict[str, int] = field(default_factory=dict)
    room: str = ""
    on_adventure: bool = False
    parent_a_key: int = 0
    parent_b_key: int = 0
    children_keys: list[int] = field(default_factory=list)
    lover_keys: list[int] = field(default_factory=list)
    hater_keys: list[int] = field(default_factory=list)
    generation: int = 0


@dataclass
class RoomStats:
    """Aggregated house stats for a single room, derived from furniture."""

    appeal: int = 0
    comfort: int = 0
    stimulation: int = 0
    health: int = 0
    mutation: int = 0
    cat_count: int = 0
    furniture_count: int = 0


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

    room_assignments: dict[int, str] = field(default_factory=dict)
    adventure_keys: set[int] = field(default_factory=set)
    unlocked_rooms: list[str] = field(default_factory=list)
    pedigree: dict[int, tuple[int | None, int | None]] = field(default_factory=dict)
    room_stats: dict[str, RoomStats] = field(default_factory=dict)

    @property
    def house_cats(self) -> list[SaveCat]:
        """Only cats currently in the player's house."""
        return [c for c in self.cats if c.status == "in_house"]


# ── Auto-detect ───────────────────────────────────────────────────────────────


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


# ── Blob decompression ────────────────────────────────────────────────────────


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


# ── Cat blob parsing helpers ──────────────────────────────────────────────────


def _read_db_key_candidates(
    raw: bytes,
    self_key: int,
    offsets: tuple[int, ...],
    base_offset: int = 0,
) -> list[int]:
    """Read u32 values at given offsets as potential db_key references."""
    keys: list[int] = []
    for off in offsets:
        pos = base_offset + off
        if pos < 0 or pos + 4 > len(raw):
            continue
        try:
            value = struct.unpack_from("<I", raw, pos)[0]
        except Exception:
            continue
        if value in (0, 0xFFFF_FFFF) or value == self_key:
            continue
        if value not in keys:
            keys.append(value)
    return keys


def _parse_flat_cat(data: bytes, db_key: int, current_day: int = 0) -> SaveCat | None:
    """Parse a decompressed flat cat record using sequential BinaryReader.

    Layout (from MewgenicsBreedingManager reference parser):
      @0:   u32 breed_id
      @4:   u64 unique_id
      @12:  utf16str name
            str name_tag -> personality_anchor = reader.pos
            u64 parent_uid_a, u64 parent_uid_b
            str collar, u32 skip
            skip(64)
            72 x u32 visual mutation table
            3 x u32 gender_token_fields
            str raw_gender -> resolve via sex_code at raw[personality_anchor]
            f64 breed_coefficient
            7 x u32 base stats, 7 x i32 stat_mod, 7 x i32 stat_sec
            personality: libido @+32, inbredness @+40, aggression @+64 from anchor
            lover_keys @+48, hater_keys @+72 from anchor
            ability run: scan for "DefaultMove" marker
            age: creation_day u32 near end of blob
    """
    if len(data) < 100:
        return None

    try:
        return _parse_flat_cat_inner(data, db_key, current_day)
    except Exception:
        log.debug("Failed to parse cat #%d via BinaryReader", db_key, exc_info=True)
        return None


def _parse_flat_cat_inner(data: bytes, db_key: int, current_day: int) -> SaveCat | None:
    r = _BinaryReader(data)
    cat = SaveCat(db_key=db_key)

    # ── Header ────────────────────────────────────────────────────────
    cat.breed_id = r.u32()

    uid_int = r.u64()
    cat.unique_id = hex(uid_int)

    cat.name = r.utf16str()
    if not cat.name:
        return None

    cat.name_tag = r.str() or ""
    personality_anchor = r.pos

    if cat.name_tag in KNOWN_CLASSES:
        cat.active_class = cat.name_tag

    # Parent UIDs (stored but not used directly -- pedigree blob is authoritative)
    r.u64()  # parent_uid_a
    r.u64()  # parent_uid_b

    # ── Collar ────────────────────────────────────────────────────────
    cat.collar = r.str() or ""
    r.u32()  # padding

    # ── Visual mutation table ─────────────────────────────────────────
    r.skip(64)
    T = [r.u32() for _ in range(72)]

    cat.body_parts = {"texture": T[0], "bodyShape": T[3], "headShape": T[8]}

    mutation_ids: list[int] = []
    for _slot_key, table_index in _VISUAL_MUTATION_FIELDS:
        if table_index < len(T):
            mid = T[table_index]
            if mid in (0, 0xFFFF_FFFF):
                continue
            is_defect = (700 <= mid <= 706) or mid == 0xFFFF_FFFE
            if not is_defect and mid >= 300:
                mutation_ids.append(mid)
    cat.visual_mutation_ids = mutation_ids

    # ── Gender ────────────────────────────────────────────────────────
    r.u32()  # gender_token_field 1
    r.u32()  # gender_token_field 2
    r.u32()  # gender_token_field 3

    raw_gender = r.str()

    sex_code = data[personality_anchor] if personality_anchor < len(data) else None
    gender_from_code = (
        {0: "male", 1: "female", 2: "?"}.get(sex_code) if sex_code is not None else None
    )
    if gender_from_code:
        cat.gender = gender_from_code
        cat.gender_source = "sex_code"
    else:
        cat.gender = _normalize_gender(raw_gender)
        cat.gender_source = "token_fallback"

    # ── Breed coefficient ─────────────────────────────────────────────
    breed_val = r.f64()
    if 0.0 <= breed_val <= 1.0:
        cat.breed_coefficient = breed_val

    # ── Stats ─────────────────────────────────────────────────────────
    stat_base = [r.u32() for _ in range(7)]
    cat.base_str = stat_base[0]
    cat.base_dex = stat_base[1]
    cat.base_con = stat_base[2]
    cat.base_int = stat_base[3]
    cat.base_spd = stat_base[4]
    cat.base_cha = stat_base[5]
    cat.base_lck = stat_base[6]

    cat.stat_mod = [r.i32() for _ in range(7)]
    cat.stat_sec = [r.i32() for _ in range(7)]

    cat.total_stats = {
        n: stat_base[i] + cat.stat_mod[i] + cat.stat_sec[i]
        for i, n in enumerate(STAT_ORDER)
    }

    # ── Personality traits (from personality_anchor offsets) ───────────
    def _read_personality(offset: int) -> float | None:
        pos = personality_anchor + offset
        if pos + 8 > len(data):
            return None
        try:
            v = struct.unpack_from("<d", data, pos)[0]
        except Exception:
            return None
        if not math.isfinite(v) or not (0.0 <= v <= 1.0):
            return None
        return float(v)

    cat.libido = _read_personality(32)
    cat.inbredness = _read_personality(40)
    cat.aggression = _read_personality(64)

    # ── Relationships ─────────────────────────────────────────────────
    cat.lover_keys = _read_db_key_candidates(
        data, db_key, (48,), base_offset=personality_anchor
    )
    cat.hater_keys = _read_db_key_candidates(
        data, db_key, (72,), base_offset=personality_anchor
    )

    # ── Ability run (scan for "DefaultMove" marker) ───────────────────
    _parse_abilities(data, r, cat, db_key)

    # ── Age (creation_day near end of blob) ───────────────────────────
    if current_day > 0:
        for offset_from_end in (103, 102, 104, 101, 105, 100, 106, 107, 108, 109, 110):
            pos = len(data) - offset_from_end
            if pos < 0 or pos + 4 > len(data):
                continue
            creation_day = struct.unpack_from("<I", data, pos)[0]
            if 0 <= creation_day <= current_day:
                age = current_day - creation_day
                if 0 <= age <= 100:
                    cat.age = age
                    break

    # ── Retired flag (byte at -66 from end, non-zero → retired) ──────
    retire_pos = len(data) - 66
    if retire_pos >= 0:
        cat.retired = data[retire_pos] != 0

    return cat


def _parse_abilities(data: bytes, r: _BinaryReader, cat: SaveCat, db_key: int) -> None:
    """Parse ability run from the cat blob, filling cat.abilities/passives/disorders."""
    curr = r.pos
    run_start = -1

    for i in range(curr, min(curr + 600, len(data) - 19)):
        lo = struct.unpack_from("<I", data, i)[0]
        hi = struct.unpack_from("<I", data, i + 4)[0]
        if hi != 0 or not (1 <= lo <= 96):
            continue
        try:
            cand = data[i + 8 : i + 8 + lo].decode("ascii")
            if cand == "DefaultMove":
                run_start = i
                break
        except Exception:
            continue

    if run_start != -1:
        r.seek(run_start)
        run_items: list[str] = []
        for _ in range(32):
            saved = r.pos
            item = r.str()
            if item is None or not _IDENT_RE.match(item):
                r.seek(saved)
                break
            run_items.append(item)

        cat.abilities = [x for x in run_items[1:6] if _valid_str(x)]

        passives: list[str] = []
        for ri in run_items[10:]:
            if _valid_str(ri):
                passives.append(ri)

        try:
            r.u32()  # passive1 tier
        except Exception:
            pass

        disorders: list[str] = []
        for tail_idx in range(3):
            try:
                item = r.str()
            except Exception:
                break
            if item is not None and _IDENT_RE.match(item) and _valid_str(item):
                if tail_idx == 0:
                    if item not in passives:
                        passives.append(item)
                else:
                    disorders.append(item)
            try:
                r.u32()
            except Exception:
                break

        cat.passives = passives
        cat.disorders = disorders
        cat.equipment = []
    else:
        log.debug("Cat #%d: DefaultMove marker not found, using heuristic", db_key)
        found = -1
        for i in range(curr, min(curr + 500, len(data) - 9)):
            length = struct.unpack_from("<I", data, i)[0]
            if (
                0 < length < 64
                and struct.unpack_from("<I", data, i + 4)[0] == 0
                and 65 <= data[i + 8] <= 90
            ):
                found = i
                break
        if found != -1:
            r.seek(found)

        cat.abilities = [a for a in (r.str() for _ in range(6)) if _valid_str(a)]
        cat.equipment = [s for s in (r.str() for _ in range(4)) if _valid_str(s)]

        passives: list[str] = []
        cat.disorders = []
        first = r.str()
        if _valid_str(first):
            passives.append(first)
        for _ in range(13):
            if r.remaining() < 12:
                break
            flag = r.u32()
            if flag == 0:
                break
            p = r.str()
            if _valid_str(p):
                passives.append(p)
        cat.passives = passives


# ── Save-level parsers ────────────────────────────────────────────────────────


def _parse_house_info(cursor: sqlite3.Cursor) -> dict[int, str]:
    """Parse house_state blob into {cat_key: room_name}.

    Variable-length records: u32 cat_key, u32 pad, u32 room_len, u32 pad,
    room_name (ASCII, room_len bytes), 24 bytes trailing data.
    """
    try:
        row = cursor.execute(
            "SELECT data FROM files WHERE key = 'house_state'"
        ).fetchone()
    except sqlite3.Error:
        log.warning("Failed to read house_state")
        return {}
    if not row or not row[0]:
        return {}

    blob: bytes = row[0]
    if len(blob) < 8:
        return {}

    count = struct.unpack_from("<I", blob, 4)[0]
    pos = 8
    result: dict[int, str] = {}
    for _ in range(count):
        if pos + 8 > len(blob):
            break
        cat_key = struct.unpack_from("<I", blob, pos)[0]
        pos += 8
        if pos + 8 > len(blob):
            break
        room_len = struct.unpack_from("<I", blob, pos)[0]
        pos += 8
        room_name = ""
        if room_len > 0 and pos + room_len <= len(blob):
            room_name = blob[pos : pos + room_len].decode("ascii", errors="ignore")
            pos += room_len
        pos += 24
        if 1 <= cat_key <= 10_000:
            result[cat_key] = room_name

    log.debug("house_state: %d cat-room entries", len(result))
    return result


def _parse_pedigree(cursor: sqlite3.Cursor) -> dict[int, tuple[int | None, int | None]]:
    """Parse pedigree blob: 32-byte entries mapping cat -> parent_a, parent_b."""
    try:
        row = cursor.execute("SELECT data FROM files WHERE key='pedigree'").fetchone()
        if not row:
            return {}
        blob: bytes = row[0]
    except Exception:
        log.warning("Failed to read pedigree blob", exc_info=True)
        return {}

    NULL = 0xFFFF_FFFF_FFFF_FFFF
    MAX_KEY = 1_000_000
    ped_map: dict[int, tuple[int | None, int | None]] = {}

    for pos in range(8, len(blob) - 31, 32):
        cat_k, pa_k, pb_k, _extra = struct.unpack_from("<QQQQ", blob, pos)
        if cat_k == 0 or cat_k == NULL or cat_k > MAX_KEY:
            continue
        pa = int(pa_k) if pa_k != NULL and 0 < pa_k <= MAX_KEY else None
        pb = int(pb_k) if pb_k != NULL and 0 < pb_k <= MAX_KEY else None
        cat_key = int(cat_k)

        existing = ped_map.get(cat_key)
        if existing is None:
            ped_map[cat_key] = (pa, pb)
        elif existing[0] is None or existing[1] is None:
            if pa is not None and pb is not None:
                ped_map[cat_key] = (pa, pb)

    log.debug("pedigree: %d entries", len(ped_map))
    return ped_map


def _get_adventure_keys(cursor: sqlite3.Cursor) -> set[int]:
    """Parse adventure_state blob to find cat keys on adventure."""
    keys: set[int] = set()
    try:
        row = cursor.execute(
            "SELECT data FROM files WHERE key = 'adventure_state'"
        ).fetchone()
        if not row or len(row[0]) < 8:
            return keys
        blob: bytes = row[0]
        count = struct.unpack_from("<I", blob, 4)[0]
        pos = 8
        for _ in range(count):
            if pos + 8 > len(blob):
                break
            val = struct.unpack_from("<Q", blob, pos)[0]
            pos += 8
            cat_key = (val >> 32) & 0xFFFF_FFFF
            if cat_key:
                keys.add(cat_key)
    except Exception:
        log.warning("Failed to parse adventure_state blob", exc_info=True)
    log.debug("adventure_state: %d keys", len(keys))
    return keys


def _get_unlocked_house_rooms(cursor: sqlite3.Cursor) -> list[str]:
    """Parse house_unlocks blob to determine which rooms are available."""
    try:
        row = cursor.execute(
            "SELECT data FROM files WHERE key = 'house_unlocks'"
        ).fetchone()
    except sqlite3.Error:
        return []
    if not row or not row[0]:
        return []

    tokens = {
        m.group(0).decode("ascii", errors="ignore")
        for m in re.finditer(rb"[A-Za-z][A-Za-z0-9_]+", row[0])
    }
    unlocked: set[str] = set()

    if tokens & {"Default", "House3", "MediumHouse", "LargeHouse"}:
        unlocked.add("Floor1_Large")
    if tokens & {"House3", "MediumHouse_SmallRoom", "LargeHouse"}:
        unlocked.add("Floor1_Small")
    if "SmallHouse_Attic" in tokens:
        unlocked.add("Attic")
    if tokens & {"MediumHouse", "LargeHouse_Floor2Large"}:
        unlocked.add("Floor2_Large")
    if "LargeHouse_Floor2Small" in tokens:
        unlocked.add("Floor2_Small")

    return [room for room in ROOM_KEYS if room in unlocked]


def _count_cats_per_room(room_assignments: dict[int, str]) -> dict[str, int]:
    """Count how many cats are assigned to each room."""
    counts: dict[str, int] = {}
    for room in room_assignments.values():
        counts[room] = counts.get(room, 0) + 1
    return counts


def _parse_furniture(cursor: sqlite3.Cursor) -> dict[str, RoomStats]:
    """Parse furniture table to extract per-room house stats.

    Each furniture blob contains the item name, assigned room, and 5 stat
    values (Appeal, Comfort, Stimulation, Health, Mutation) packed as i32
    in the last 20 bytes.

    The blob layout is:
      u32 version (1)
      u32 name_len, u32 pad
      name bytes (ASCII)
      u32 room_len, u32 pad
      room bytes (ASCII)
      ... positioning / transform data ...
      last 20 bytes: 5 x i32 house stat contributions
    """
    room_totals: dict[str, RoomStats] = {}
    try:
        rows = cursor.execute("SELECT key, data FROM furniture").fetchall()
    except sqlite3.Error:
        log.warning("Failed to read furniture table")
        return room_totals

    for _key, blob in rows:
        if not blob or len(blob) < 28:
            continue
        try:
            r = _BinaryReader(blob)
            r.u32()  # version
            name_len = r.u32()
            r.u32()  # pad
            if name_len > 200 or r.pos + name_len > len(blob):
                continue
            _furniture_name = blob[r.pos : r.pos + name_len].decode(
                "ascii", errors="ignore"
            )
            r.skip(name_len)

            room_len = r.u32()
            r.u32()  # pad
            if room_len > 100 or r.pos + room_len > len(blob):
                continue
            room_name = blob[r.pos : r.pos + room_len].decode("ascii", errors="ignore")

            if len(blob) < 20:
                continue
            stats_offset = len(blob) - 20
            vals = struct.unpack_from("<5i", blob, stats_offset)

            rs = room_totals.get(room_name)
            if rs is None:
                rs = RoomStats()
                room_totals[room_name] = rs
            rs.appeal += vals[0]
            rs.comfort += vals[1]
            rs.stimulation += vals[2]
            rs.health += vals[3]
            rs.mutation += vals[4]
            rs.furniture_count += 1
        except Exception:
            log.debug("Failed to parse furniture #%s", _key, exc_info=True)

    log.debug("furniture: %d rooms with stats", len(room_totals))
    return room_totals


def _parse_unlocks(
    cursor: sqlite3.Cursor,
) -> tuple[list[str], list[str], list[str]]:
    """Parse the unlocks blob to extract unlocked classes, abilities, passives.

    Structure: u32 num_categories, then for each category:
      u32 count, u32 padding, then count x [i64 len][ascii string]
    Category 1 = classes, 2 = active abilities, 3 = passive abilities.
    """
    try:
        row = cursor.execute("SELECT data FROM files WHERE key = 'unlocks'").fetchone()
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
        len(classes),
        len(abilities),
        len(passives),
    )
    return classes, abilities, passives


# ── Main entry point ──────────────────────────────────────────────────────────


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

        # ── Properties ────────────────────────────────────────────────
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

        # ── Save-level blobs ──────────────────────────────────────────
        room_assignments = _parse_house_info(cursor)
        result.room_assignments = room_assignments
        result.house_cat_keys = set(room_assignments.keys())

        adventure_keys = _get_adventure_keys(cursor)
        result.adventure_keys = adventure_keys

        result.unlocked_rooms = _get_unlocked_house_rooms(cursor)

        pedigree = _parse_pedigree(cursor)
        result.pedigree = pedigree

        classes, abilities, passives = _parse_unlocks(cursor)
        result.unlocked_classes = classes
        result.unlocked_abilities = abilities
        result.unlocked_passives = passives

        # ── Furniture / room stats ────────────────────────────────────
        room_stats = _parse_furniture(cursor)
        for room_name, count in _count_cats_per_room(room_assignments).items():
            rs = room_stats.get(room_name)
            if rs is None:
                rs = RoomStats()
                room_stats[room_name] = rs
            rs.cat_count = count
        result.room_stats = room_stats

        # ── Cats ──────────────────────────────────────────────────────
        try:
            for db_key, blob in cursor.execute(
                "SELECT key, data FROM cats ORDER BY key"
            ):
                if blob is None:
                    continue
                flat = _decompress_blob(blob)
                if flat is None:
                    log.debug("Failed to decompress cat #%d", db_key)
                    continue
                cat = _parse_flat_cat(flat, db_key, current_day=result.current_day)
                if cat is None:
                    log.debug("Failed to parse cat #%d", db_key)
                    continue

                # Status / room / adventure
                if db_key in adventure_keys:
                    cat.status = "adventure"
                    cat.on_adventure = True
                elif db_key in room_assignments:
                    cat.status = "in_house"
                    cat.room = room_assignments[db_key]
                elif cat.age == 0:
                    cat.status = "dead"
                else:
                    cat.status = "historical"

                result.cats.append(cat)
        except sqlite3.Error:
            log.warning("Failed to read cats table")

    finally:
        conn.close()

    # ── Post-parse resolution ─────────────────────────────────────────
    _resolve_relationships(result, pedigree)

    house_count = sum(1 for c in result.cats if c.status == "in_house")
    adventure_count = sum(1 for c in result.cats if c.status == "adventure")
    log.info(
        "Read save '%s': %d cats (%d in house, %d on adventure), day %d, %d classes",
        path.name,
        len(result.cats),
        house_count,
        adventure_count,
        result.current_day,
        len(result.unlocked_classes),
    )
    _dump_save_debug(result)
    return result


def _dump_save_debug(save: SaveData) -> None:
    """Emit a comprehensive DEBUG log of all parsed save data."""
    if not log.isEnabledFor(logging.DEBUG):
        return

    sep = "-" * 120

    lines: list[str] = [
        "",
        sep,
        "SAVE DATA DEBUG DUMP",
        sep,
        f"  Save file : {save.save_path}",
        f"  Day       : {save.current_day}",
        f"  Gold      : {save.house_gold}",
        f"  Food      : {save.house_food}",
        f"  Steam ID  : {save.owner_steamid}",
        f"  Total cats: {len(save.cats)}",
        f"  Rooms     : {save.unlocked_rooms}",
        f"  Classes   : {save.unlocked_classes}",
        f"  Abilities : {len(save.unlocked_abilities)} unlocked",
        f"  Passives  : {len(save.unlocked_passives)} unlocked",
        f"  Adventure : keys {save.adventure_keys or 'none'}",
        "",
    ]

    if save.room_stats:
        lines.append("  ROOM STATS (from furniture)")
        for room_name, rs in sorted(save.room_stats.items()):
            display = ROOM_DISPLAY.get(room_name, room_name)
            lines.append(
                f"    {display:24s}  Appeal={rs.appeal:4d}  Comfort={rs.comfort:4d}"
                f"  Stim={rs.stimulation:4d}  Health={rs.health:4d}"
                f"  Mutation={rs.mutation:4d}  cats={rs.cat_count}  furniture={rs.furniture_count}"
            )
        lines.append("")

    by_status: dict[str, list[SaveCat]] = {}
    for c in save.cats:
        by_status.setdefault(c.status, []).append(c)

    lines.append(
        "  Status breakdown: "
        + ", ".join(f"{s}={len(cats)}" for s, cats in sorted(by_status.items()))
    )
    lines.append("")

    # ── House cats (full detail) ──────────────────────────────────────
    house = save.house_cats
    retired_count = sum(1 for c in house if c.retired)
    lines.append(f"  HOUSE CATS ({len(house)} total, {retired_count} retired)")
    lines.append(sep)
    header = (
        f"  {'Key':>4} {'Name':22s} {'Age':>3} {'Gen':>3} {'Gnd':>4} "
        f"{'Class':12s} {'Room':18s} {'Ret':>3} "
        f"{'STR':>4} {'DEX':>4} {'CON':>4} {'INT':>4} {'SPD':>4} {'CHA':>4} {'LCK':>4}  "
        f"{'Breed':>5}  Abilities / Passives / Disorders"
    )
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))

    for c in house:
        room = ROOM_DISPLAY.get(c.room, c.room) or "(none)"
        ret_flag = "YES" if c.retired else ""
        abilities = ", ".join(c.abilities) if c.abilities else "-"
        passives = ", ".join(c.passives) if c.passives else "-"
        disorders = ", ".join(c.disorders) if c.disorders else "-"
        lines.append(
            f"  {c.db_key:4d} {c.name:22s} {c.age:3d} {c.generation:3d} {c.gender:>4s} "
            f"{c.active_class or '-':12s} {room:18s} {ret_flag:>3s} "
            f"{c.base_str:4d} {c.base_dex:4d} {c.base_con:4d} {c.base_int:4d} "
            f"{c.base_spd:4d} {c.base_cha:4d} {c.base_lck:4d}  "
            f"{c.breed_coefficient:5.3f}  A: {abilities}"
        )
        lines.append(
            f"  {'':4s} {'':22s} {'':3s} {'':3s} {'':4s} "
            f"{'':12s} {'':18s} {'':3s} "
            f"{'':4s} {'':4s} {'':4s} {'':4s} {'':4s} {'':4s} {'':4s}  "
            f"{'':5s}  P: {passives}  D: {disorders}"
        )
        extras: list[str] = []
        if c.aggression is not None:
            extras.append(f"aggr={c.aggression:.2f}")
        if c.libido is not None:
            extras.append(f"libido={c.libido:.2f}")
        if c.inbredness is not None:
            extras.append(f"inbred={c.inbredness:.2f}")
        if c.collar:
            extras.append(f"collar={c.collar}")
        if c.lover_keys:
            extras.append(f"lovers={c.lover_keys}")
        if c.hater_keys:
            extras.append(f"haters={c.hater_keys}")
        if c.parent_a_key or c.parent_b_key:
            extras.append(f"parents=[{c.parent_a_key},{c.parent_b_key}]")
        if c.children_keys:
            extras.append(f"children={c.children_keys}")
        if extras:
            lines.append(
                f"  {'':4s} {'':22s} {'':3s} {'':3s} {'':4s} "
                f"{'':12s} {'':18s} {'':3s} "
                f"{'':4s} {'':4s} {'':4s} {'':4s} {'':4s} {'':4s} {'':4s}  "
                f"{'':5s}  {' | '.join(extras)}"
            )

    lines.append("")

    # ── Historical / adventure cats (compact) ─────────────────────────
    for status_label in ("adventure", "historical"):
        group = by_status.get(status_label, [])
        if not group:
            continue
        lines.append(f"  {status_label.upper()} CATS ({len(group)})")
        lines.append(
            f"  {'Key':>4} {'Name':22s} {'Age':>3} {'Gen':>3} {'Gnd':>4} "
            f"{'STR':>4} {'DEX':>4} {'CON':>4} {'INT':>4} {'SPD':>4} {'CHA':>4} {'LCK':>4}"
        )
        for c in group[:30]:
            lines.append(
                f"  {c.db_key:4d} {c.name:22s} {c.age:3d} {c.generation:3d} {c.gender:>4s} "
                f"{c.base_str:4d} {c.base_dex:4d} {c.base_con:4d} {c.base_int:4d} "
                f"{c.base_spd:4d} {c.base_cha:4d} {c.base_lck:4d}"
            )
        if len(group) > 30:
            lines.append(f"  ... and {len(group) - 30} more")
        lines.append("")

    dead_count = len(by_status.get("dead", []))
    if dead_count:
        lines.append(f"  DEAD CATS: {dead_count} (not listed)")

    lines.append(sep)

    log.debug("\n".join(lines))


def _resolve_relationships(
    result: SaveData,
    pedigree: dict[int, tuple[int | None, int | None]],
) -> None:
    """Resolve parent/child links, generation depth, and filter relationships."""
    key_to_cat = {c.db_key: c for c in result.cats}

    # ── Parents from pedigree ─────────────────────────────────────────
    for cat in result.cats:
        ped = pedigree.get(cat.db_key)
        if ped is None:
            continue
        pa_k, pb_k = ped
        if pa_k is not None and pa_k in key_to_cat and pa_k != cat.db_key:
            cat.parent_a_key = pa_k
        if pb_k is not None and pb_k in key_to_cat and pb_k != cat.db_key:
            cat.parent_b_key = pb_k

    # ── Children (inverse of parent links) ────────────────────────────
    for cat in result.cats:
        cat.children_keys = []
    for cat in result.cats:
        for parent_key in (cat.parent_a_key, cat.parent_b_key):
            if parent_key and parent_key in key_to_cat:
                parent = key_to_cat[parent_key]
                if cat.db_key not in parent.children_keys:
                    parent.children_keys.append(cat.db_key)

    # ── Filter lover/hater keys to existing cats ──────────────────────
    for cat in result.cats:
        cat.lover_keys = [k for k in cat.lover_keys if k in key_to_cat]
        cat.hater_keys = [k for k in cat.hater_keys if k in key_to_cat]

    # ── Generation depth (iterative, handles cycles) ──────────────────
    for c in result.cats:
        c.generation = 0 if (c.parent_a_key == 0 and c.parent_b_key == 0) else -1

    for _ in range(len(result.cats) + 1):
        changed = False
        for c in result.cats:
            pa = key_to_cat.get(c.parent_a_key)
            pb = key_to_cat.get(c.parent_b_key)
            pa_g = pa.generation if pa is not None else -1
            pb_g = pb.generation if pb is not None else -1

            if pa_g >= 0 or pb_g >= 0:
                g = max(pa_g, pb_g) + 1
                if c.generation != g:
                    c.generation = g
                    changed = True
        if not changed:
            break

    for c in result.cats:
        if c.generation < 0:
            c.generation = 0
