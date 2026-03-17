from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.stat_parser import CatStats

_STAT_KEYS = ("str", "dex", "con", "int", "spd", "cha", "lck")

CLASS_TO_COLLAR: dict[str, str] = {
    "Fighter": "Fighter",
    "Hunter": "Hunter",
    "Mage": "Mage",
    "Medic": "Cleric",
    "Tank": "Tank",
    "Thief": "Thief",
    "Necromancer": "Necromancer",
    "Tinkerer": "Tinkerer",
    "Butcher": "Butcher",
    "Druid": "Druid",
    "Psychic": "Psychic",
    "Monk": "Monk",
    "Jester": "Jester",
    "None": "Collarless",
    "Colorless": "Collarless",
}


@dataclass(frozen=True)
class CollarDef:
    name: str
    color: str
    modifiers: dict[str, int]
    # 7-float tuple: (STR, DEX, CON, INT, SPD, CHA, LCK)
    score_weights: tuple[float, ...] = field(default_factory=tuple)


COLLARS: list[CollarDef] = [
    # ── Starter classes ──────────────────────────────────────────────
    CollarDef(
        name="Collarless",
        color="#888888",
        modifiers={},
        score_weights=(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    ),
    CollarDef(
        name="Fighter",
        color="#C13128",
        modifiers={"STR": +2, "SPD": +1, "INT": -1},
        score_weights=(2.0, 0.0, 0.5, 0.0, 1.0, 0.0, 0.25),
    ),
    CollarDef(
        name="Hunter",
        color="#3B7A57",
        modifiers={"DEX": +3, "LCK": +2, "CON": -1, "SPD": -2},
        score_weights=(0.0, 2.0, 0.25, 0.0, 0.0, 0.0, 1.5),
    ),
    CollarDef(
        name="Mage",
        color="#4A90E2",
        modifiers={"INT": +2, "CHA": +2, "CON": -1, "STR": -1},
        score_weights=(0.0, 0.0, 0.25, 1.5, 0.5, 1.5, 0.25),
    ),
    CollarDef(
        name="Tank",
        color="#B8860B",
        modifiers={"CON": +4, "DEX": -1, "INT": -1},
        score_weights=(0.5, 0.0, 2.5, 0.0, 0.0, 0.0, 0.0),
    ),
    # ── Unlockable classes ───────────────────────────────────────────
    CollarDef(
        name="Cleric",
        color="#9E9488",
        modifiers={"CHA": +2, "CON": +2, "DEX": -1, "SPD": -1},
        score_weights=(0.0, 0.0, 1.0, 0.75, 0.0, 1.5, 0.25),
    ),
    CollarDef(
        name="Thief",
        color="#7B5EA7",
        modifiers={"SPD": +4, "LCK": +1, "STR": -1, "CON": -1},
        score_weights=(0.0, 0.5, 0.0, 0.0, 2.0, 0.0, 1.0),
    ),
    CollarDef(
        name="Necromancer",
        color="#6B4D7A",
        modifiers={"CON": +2, "CHA": +1, "STR": -2},
        score_weights=(0.0, 0.0, 1.5, 0.75, 0.0, 1.0, 0.0),
    ),
    CollarDef(
        name="Tinkerer",
        color="#4682B4",
        modifiers={"INT": +4, "LCK": -1, "CHA": -1},
        score_weights=(0.0, 0.5, 0.5, 2.0, 0.5, 0.0, 0.0),
    ),
    CollarDef(
        name="Butcher",
        color="#8B0000",
        modifiers={"CON": +3, "STR": +2, "SPD": -2},
        score_weights=(1.5, 0.0, 2.0, 0.0, 0.0, 0.0, 0.25),
    ),
    CollarDef(
        name="Druid",
        color="#2E8B57",
        modifiers={"CHA": +3, "LCK": +1, "CON": -2},
        score_weights=(0.0, 0.0, 0.25, 0.5, 0.0, 2.0, 0.75),
    ),
    CollarDef(
        name="Psychic",
        color="#9370DB",
        modifiers={"INT": +1, "CHA": +1, "SPD": +1, "CON": -1},
        score_weights=(0.0, 0.0, 0.25, 1.0, 1.0, 1.5, 0.0),
    ),
    CollarDef(
        name="Monk",
        color="#CD853F",
        modifiers={"INT": +2, "CHA": +2, "STR": -1, "DEX": -1},
        score_weights=(0.5, 0.5, 0.5, 1.0, 0.75, 1.0, 0.25),
    ),
    CollarDef(
        name="Jester",
        color="#DA70D6",
        modifiers={},
        score_weights=(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    ),
]


def collar_score(collar: CollarDef, stats: "CatStats") -> float:
    """Gameplay-aware suitability score using full 7-stat weight vectors.

    Each class has weights derived from wiki mechanics:
      HP = CON*4, max mana = CHA*3, mana regen = INT,
      melee dmg = STR, ranged dmg = DEX/2, movement = SPD, crit = LCK.
    """
    total = 0.0
    norm = 0.0
    for key, weight in zip(_STAT_KEYS, collar.score_weights):
        val = getattr(stats, f"stat_{key}").total
        total += val * weight
        norm += abs(weight)
    return round(total / norm, 2) if norm > 0 else 0.0


def compute_collar_scores(stats: "CatStats") -> list[tuple[CollarDef, float]]:
    """Return all collars ranked by suitability score (highest first)."""
    scored = [(c, collar_score(c, stats)) for c in COLLARS]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


_COLLAR_BY_NAME: dict[str, CollarDef] = {c.name: c for c in COLLARS}


def collar_by_name(name: str) -> CollarDef | None:
    return _COLLAR_BY_NAME.get(name)


def unlocked_collars(unlocked_classes: list[str]) -> list[CollarDef]:
    """Return only the collars whose game class is in the unlocked set."""
    result: list[CollarDef] = []
    seen: set[str] = set()
    for cls in unlocked_classes:
        collar_name = CLASS_TO_COLLAR.get(cls)
        if collar_name and collar_name in _COLLAR_BY_NAME and collar_name not in seen:
            result.append(_COLLAR_BY_NAME[collar_name])
            seen.add(collar_name)
    return result


def save_cat_to_stats(sc: "SaveCat") -> "CatStats":  # noqa: F821
    """Bridge a SaveCat (base stats only) into a CatStats for scoring."""
    from src.data.stat_parser import CatStats, StatValue

    return CatStats(
        cat_name=sc.name,
        stat_str=StatValue(total=sc.base_str, base=sc.base_str, bonus=0),
        stat_dex=StatValue(total=sc.base_dex, base=sc.base_dex, bonus=0),
        stat_con=StatValue(total=sc.base_con, base=sc.base_con, bonus=0),
        stat_int=StatValue(total=sc.base_int, base=sc.base_int, bonus=0),
        stat_spd=StatValue(total=sc.base_spd, base=sc.base_spd, bonus=0),
        stat_cha=StatValue(total=sc.base_cha, base=sc.base_cha, bonus=0),
        stat_lck=StatValue(total=sc.base_lck, base=sc.base_lck, bonus=0),
    )
