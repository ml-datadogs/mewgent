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


@dataclass(frozen=True)
class CollarDef:
    name: str
    color: str
    modifiers: dict[str, int]
    score_weights: tuple[tuple[str, float], ...] = field(default_factory=tuple)


COLLARS: list[CollarDef] = [
    CollarDef(
        name="Fighter",
        color="#A85044",
        modifiers={"STR": +2, "SPD": +1, "INT": -1},
        score_weights=(("STR", 1.5), ("SPD", 1.25), ("DEX", 1.0)),
    ),
    CollarDef(
        name="Necromancer",
        color="#7B6898",
        modifiers={"CON": +2, "CHA": +1, "STR": -2},
        score_weights=(("CON", 1.5), ("CHA", 1.25), ("INT", 1.0)),
    ),
    CollarDef(
        name="Mage",
        color="#5A7A9E",
        modifiers={"INT": +2, "CHA": +2, "STR": -1, "CON": -1},
        score_weights=(("INT", 1.5), ("CHA", 1.25), ("DEX", 1.0)),
    ),
    CollarDef(
        name="Thief",
        color="#5E574E",
        modifiers={"SPD": +4, "STR": -1, "CON": -1},
        score_weights=(("SPD", 1.5), ("DEX", 1.25), ("LCK", 1.0)),
    ),
    CollarDef(
        name="Ranger",
        color="#5E8A52",
        modifiers={"DEX": +3, "LCK": +2, "SPD": -2},
        score_weights=(("DEX", 1.5), ("LCK", 1.25), ("INT", 1.0)),
    ),
    CollarDef(
        name="Cleric",
        color="#C4B9A8",
        modifiers={"CON": +2, "CHA": +2, "SPD": -1, "DEX": -1},
        score_weights=(("CHA", 1.5), ("CON", 1.25), ("INT", 1.0)),
    ),
    CollarDef(
        name="Tank",
        color="#8A7352",
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
