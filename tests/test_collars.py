"""Tests for collar scoring, unlock mapping, and viable-class aggregation."""

from __future__ import annotations

from src.data.collars import (
    COLLARS,
    collar_by_name,
    collar_score,
    save_cat_to_stats,
    unlocked_collars,
)
from src.data.save_reader import SaveCat
from src.data.stat_parser import CatStats, StatValue
from src.ui.bridge import _compute_viable


def _save_cat(
    key: int,
    name: str,
    bases: tuple[int, int, int, int, int, int, int],
    age: int = 1,
) -> SaveCat:
    return SaveCat(
        db_key=key,
        name=name,
        gender="male",
        age=age,
        base_str=bases[0],
        base_dex=bases[1],
        base_con=bases[2],
        base_int=bases[3],
        base_spd=bases[4],
        base_cha=bases[5],
        base_lck=bases[6],
    )


class TestCollarScore:
    def test_collarless_uniform_stats(self):
        collar = collar_by_name("Collarless")
        assert collar is not None
        v = StatValue(total=7, base=7, bonus=0)
        stats = CatStats(
            cat_name="x",
            stat_str=v,
            stat_dex=v,
            stat_con=v,
            stat_int=v,
            stat_spd=v,
            stat_cha=v,
            stat_lck=v,
        )
        assert collar_score(collar, stats) == 7.0

    def test_fighter_weights_favor_str(self):
        fighter = collar_by_name("Fighter")
        assert fighter is not None
        high_str = save_cat_to_stats(
            _save_cat(1, "S", (10, 4, 4, 4, 4, 4, 4)),
        )
        high_dex = save_cat_to_stats(
            _save_cat(2, "D", (4, 10, 4, 4, 4, 4, 4)),
        )
        assert collar_score(fighter, high_str) > collar_score(fighter, high_dex)


class TestUnlockedCollars:
    def test_maps_game_class_to_collar_and_dedupes(self):
        collars = unlocked_collars(["Fighter", "Mage", "Fighter"])
        names = [c.name for c in collars]
        assert names == ["Fighter", "Mage"]

    def test_medic_maps_to_cleric(self):
        collars = unlocked_collars(["Medic"])
        assert len(collars) == 1
        assert collars[0].name == "Cleric"

    def test_unknown_class_skipped(self):
        collars = unlocked_collars(["Fighter", "NotARealClass"])
        assert [c.name for c in collars] == ["Fighter"]


class TestSaveCatToStats:
    def test_round_trip_bases_to_totals(self):
        sc = _save_cat(1, "N", (3, 4, 5, 6, 7, 8, 9))
        cs = save_cat_to_stats(sc)
        assert cs.stat_str.total == 3
        assert cs.stat_lck.total == 9
        assert cs.stat_con.bonus == 0


class TestComputeViable:
    def test_filters_zero_age_zero_stat_kittens(self):
        collars = [c for c in COLLARS if c.name in ("Fighter", "Mage")]
        adult = _save_cat(1, "Adult", (5, 5, 5, 5, 5, 5, 5), age=5)
        kitten = SaveCat(
            db_key=2,
            name="Kit",
            gender="female",
            age=0,
            base_str=0,
            base_dex=0,
            base_con=0,
            base_int=0,
            base_spd=0,
            base_cha=0,
            base_lck=0,
        )
        out = _compute_viable([adult, kitten], collars)
        assert len(out) == 1
        assert out[0]["cat"]["db_key"] == 1

    def test_sorted_by_best_score_descending(self):
        collars = [c for c in COLLARS if c.name in ("Fighter", "Tank")]
        weak = _save_cat(1, "W", (3, 3, 3, 3, 3, 3, 3))
        strong = _save_cat(2, "S", (9, 9, 9, 9, 9, 9, 9))
        out = _compute_viable([weak, strong], collars)
        assert [x["cat"]["db_key"] for x in out] == [2, 1]
        assert out[0]["best_score"] >= out[1]["best_score"]

    def test_best_idx_points_at_highest_collar_score(self):
        collars = [c for c in COLLARS if c.name in ("Fighter", "Mage")]
        bruiser = _save_cat(1, "B", (10, 3, 3, 3, 3, 3, 3))
        out = _compute_viable([bruiser], collars)
        assert len(out) == 1
        fighter_i = next(i for i, c in enumerate(collars) if c.name == "Fighter")
        mage_i = next(i for i, c in enumerate(collars) if c.name == "Mage")
        assert out[0]["best_idx"] in (fighter_i, mage_i)
        assert out[0]["scores"][out[0]["best_idx"]] == max(out[0]["scores"])
