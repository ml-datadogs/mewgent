from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.stat_parser import CatStats

_STAT_ATTR = {
    "STR": "stat_str",
    "DEX": "stat_dex",
    "CON": "stat_con",
    "INT": "stat_int",
    "SPD": "stat_spd",
    "CHA": "stat_cha",
    "LCK": "stat_lck",
}

CLASS_TO_COLLAR: dict[str, str] = {
    "Fighter": "Fighter",
    "Hunter": "Ranger",
    "Mage": "Mage",
    "Medic": "Cleric",
    "Tank": "Tank",
    "Thief": "Thief",
    "Necromancer": "Necromancer",
}


@dataclass(frozen=True)
class CollarDef:
    name: str
    color: str
    modifiers: dict[str, int]
    score_weights: tuple[tuple[str, float], ...] = field(default_factory=tuple)


COLLARS: list[CollarDef] = [
    CollarDef(
        name="Fighter",
        color="#C13128",
        modifiers={"STR": +2, "SPD": +1, "INT": -1},
        score_weights=(("STR", 1.5), ("SPD", 1.25), ("DEX", 1.0)),
    ),
    CollarDef(
        name="Necromancer",
        color="#6B4D7A",
        modifiers={"CON": +2, "CHA": +1, "STR": -2},
        score_weights=(("CON", 1.5), ("CHA", 1.25), ("INT", 1.0)),
    ),
    CollarDef(
        name="Mage",
        color="#4A90E2",
        modifiers={"INT": +2, "CHA": +2, "STR": -1, "CON": -1},
        score_weights=(("INT", 1.5), ("CHA", 1.25), ("DEX", 1.0)),
    ),
    CollarDef(
        name="Thief",
        color="#7B5EA7",
        modifiers={"SPD": +4, "STR": -1, "CON": -1},
        score_weights=(("SPD", 1.5), ("DEX", 1.25), ("LCK", 1.0)),
    ),
    CollarDef(
        name="Ranger",
        color="#3B7A57",
        modifiers={"DEX": +3, "LCK": +2, "SPD": -2},
        score_weights=(("DEX", 1.5), ("LCK", 1.25), ("INT", 1.0)),
    ),
    CollarDef(
        name="Cleric",
        color="#9E9488",
        modifiers={"CON": +2, "CHA": +2, "SPD": -1, "DEX": -1},
        score_weights=(("CHA", 1.5), ("CON", 1.25), ("INT", 1.0)),
    ),
    CollarDef(
        name="Tank",
        color="#B8860B",
        modifiers={"CON": +4, "SPD": -1, "DEX": -1},
        score_weights=(("CON", 1.5), ("STR", 1.25), ("DEX", 1.0)),
    ),
]


def collar_score(collar: CollarDef, stats: CatStats) -> float:
    """Weighted suitability score for a single collar.

    Formula: ((stat1 * 1.5) + (stat2 * 1.25) + (stat3 * 1.0)) / 3
    """
    total = 0.0
    for stat_key, weight in collar.score_weights:
        attr = _STAT_ATTR[stat_key]
        total += getattr(stats, attr).total * weight
    return round(total / 3, 2)


def compute_collar_scores(stats: CatStats) -> list[tuple[CollarDef, float]]:
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
    for cls in unlocked_classes:
        collar_name = CLASS_TO_COLLAR.get(cls)
        if collar_name and collar_name in _COLLAR_BY_NAME:
            result.append(_COLLAR_BY_NAME[collar_name])
    return result


def save_cat_to_stats(sc: "SaveCat") -> CatStats:  # noqa: F821
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
