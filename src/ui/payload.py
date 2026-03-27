"""Qt-free serialization helpers for WebChannel JSON payloads."""

from __future__ import annotations

from typing import Any

from src.data.collars import CollarDef, collar_score, save_cat_to_stats
from src.data.item_effects import item_effect_entry
from src.data.save_reader import STAT_ORDER, SaveCat


def cat_to_dict(cat: SaveCat) -> dict[str, Any]:
    return {
        "db_key": cat.db_key,
        "name": cat.name,
        "level": cat.level,
        "age": cat.age,
        "gender": cat.gender,
        "active_class": cat.active_class,
        "base_str": cat.base_str,
        "base_dex": cat.base_dex,
        "base_con": cat.base_con,
        "base_int": cat.base_int,
        "base_spd": cat.base_spd,
        "base_cha": cat.base_cha,
        "base_lck": cat.base_lck,
        "abilities": cat.abilities,
        "passives": cat.passives,
        "equipment": [item_effect_entry(eid) for eid in cat.equipment],
        "status": cat.status,
        "breed_coefficient": round(cat.breed_coefficient, 4),
        "retired": cat.retired,
        "aggression": round(cat.aggression, 3) if cat.aggression is not None else None,
        "libido": round(cat.libido, 3) if cat.libido is not None else None,
        "inbredness": round(cat.inbredness, 3) if cat.inbredness is not None else None,
        "disorders": cat.disorders,
        "visual_mutation_ids": cat.visual_mutation_ids,
        "parent_a_key": cat.parent_a_key,
        "parent_b_key": cat.parent_b_key,
        "children_keys": cat.children_keys,
        "lover_keys": cat.lover_keys,
        "hater_keys": cat.hater_keys,
        "generation": cat.generation,
        "room": cat.room,
    }


def collar_to_dict(c: CollarDef) -> dict[str, Any]:
    return {
        "name": c.name,
        "color": c.color,
        "modifiers": c.modifiers,
        "score_weights": list(c.score_weights),
    }


def compute_viable(
    house_cats: list[SaveCat],
    collars: list[CollarDef],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for cat in house_cats:
        if cat.age == 0 and all(getattr(cat, f"base_{s}") == 0 for s in STAT_ORDER):
            continue
        cs = save_cat_to_stats(cat)
        scores = [collar_score(c, cs) for c in collars]
        best_idx = max(range(len(scores)), key=lambda k: scores[k])
        result.append(
            {
                "cat": cat_to_dict(cat),
                "scores": [round(s, 2) for s in scores],
                "best_idx": best_idx,
                "best_score": round(scores[best_idx], 2),
            }
        )
    result.sort(key=lambda x: x["best_score"], reverse=True)
    return result
