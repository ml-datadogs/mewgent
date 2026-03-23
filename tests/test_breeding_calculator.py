"""Tests for wiki-derived breeding formulas and ranking helpers."""

from __future__ import annotations

import pytest

from src.breeding.calculator import (
    COMFORT_CAT_LIMIT,
    analyze_pair,
    birth_defect_disorder_chance,
    birth_defect_parts_chance,
    class_bias_chance_fn,
    first_active_ability_chance,
    higher_stat_probability,
    passive_ability_chance,
    rank_pairs_for_class,
    rank_pairs_overall,
    second_active_ability_chance,
    suggest_room_distribution,
)
from src.data.collars import collar_by_name
from src.data.save_reader import RoomStats, SaveCat

_SEVEN_FIVES: tuple[int, int, int, int, int, int, int] = (5, 5, 5, 5, 5, 5, 5)


def _cat(
    key: int,
    name: str,
    gender: str,
    room: str = "",
    bases: tuple[int, int, int, int, int, int, int] | None = None,
    breed_coefficient: float = 0.0,
    age: int = 1,
) -> SaveCat:
    b = bases or (5, 5, 5, 5, 5, 5, 5)
    return SaveCat(
        db_key=key,
        name=name,
        gender=gender,
        room=room,
        base_str=b[0],
        base_dex=b[1],
        base_con=b[2],
        base_int=b[3],
        base_spd=b[4],
        base_cha=b[5],
        base_lck=b[6],
        breed_coefficient=breed_coefficient,
        age=age,
    )


class TestFormulaBoundaries:
    @pytest.mark.parametrize(
        "stim, expected",
        [
            (0, 0.5),
            (100, pytest.approx(2 / 3, rel=1e-9)),
        ],
    )
    def test_higher_stat_probability(self, stim: int, expected):
        assert higher_stat_probability(stim) == expected

    def test_first_active_guaranteed_at_32(self):
        assert first_active_ability_chance(31) < 1.0
        assert first_active_ability_chance(32) == 1.0

    def test_second_active_guaranteed_at_196(self):
        assert second_active_ability_chance(195) < 1.0
        assert second_active_ability_chance(196) == 1.0

    def test_passive_guaranteed_at_95(self):
        assert passive_ability_chance(94) < 1.0
        assert passive_ability_chance(95) == 1.0

    def test_class_bias_guaranteed_at_100(self):
        assert class_bias_chance_fn(99) < 1.0
        assert class_bias_chance_fn(100) == 1.0

    def test_birth_defect_disorder_min_and_clamp(self):
        assert birth_defect_disorder_chance(0.2) == pytest.approx(0.02)
        assert birth_defect_disorder_chance(1.0) == pytest.approx(0.02 + 0.4 * 0.8)

    def test_birth_defect_parts_below_threshold(self):
        assert birth_defect_parts_chance(0.05) == 0.0
        assert birth_defect_parts_chance(0.1) == pytest.approx(0.15)


class TestAnalyzePair:
    def test_equal_parent_stats_use_half_high_prob(self):
        a = _cat(1, "A", "male")
        b = _cat(2, "B", "female")
        advice = analyze_pair(a, b, stimulation=0)
        assert advice.stimulation == 0
        for p in advice.stat_high_probs.values():
            assert p == 0.5
        assert advice.first_active_chance == pytest.approx(0.2)
        assert advice.inbreeding_warning == "none"

    def test_room_stats_supply_stimulation_when_stim_zero(self):
        a = _cat(1, "A", "male", room="R1")
        b = _cat(2, "B", "female", room="R1")
        rs = RoomStats(stimulation=40, comfort=10, cat_count=2)
        advice = analyze_pair(a, b, stimulation=0, room_stats=rs)
        assert advice.stimulation == 40
        assert advice.room_context is not None
        assert advice.room_context["stimulation"] == 40
        assert advice.comfort_breeding_odds is not None

    def test_explicit_stimulation_overrides_room_when_nonzero(self):
        a = _cat(1, "A", "male", room="R1")
        b = _cat(2, "B", "female", room="R1")
        rs = RoomStats(stimulation=99, comfort=10, cat_count=2)
        advice = analyze_pair(a, b, stimulation=10, room_stats=rs)
        assert advice.stimulation == 10


class TestRankPairsForClass:
    def test_skips_same_gender(self):
        collar = collar_by_name("Fighter")
        assert collar is not None
        cats = [_cat(1, "M1", "male"), _cat(2, "M2", "male")]
        assert rank_pairs_for_class(cats, collar) == []

    def test_opposite_genders_produce_rankings(self):
        collar = collar_by_name("Fighter")
        assert collar is not None
        cats = [
            _cat(1, "M", "male", bases=(10, 1, 1, 1, 1, 1, 1)),
            _cat(2, "F", "female", bases=(1, 1, 1, 1, 1, 1, 1)),
        ]
        rankings = rank_pairs_for_class(cats, collar, stimulation=0, max_results=5)
        assert len(rankings) == 1
        assert rankings[0].cat_a_key in (1, 2)
        assert rankings[0].cat_b_key in (1, 2)

    def test_same_room_uses_room_stimulation(self):
        collar = collar_by_name("Collarless")
        assert collar is not None
        room_stats = {
            "R1": RoomStats(stimulation=50, comfort=20, cat_count=2),
        }
        cats = [
            _cat(1, "M", "male", room="R1", bases=(4, 4, 4, 4, 4, 4, 4)),
            _cat(2, "F", "female", room="R1", bases=(6, 6, 6, 6, 6, 6, 6)),
        ]
        rankings = rank_pairs_for_class(
            cats, collar, stimulation=0, room_stats=room_stats, max_results=5
        )
        assert len(rankings) == 1
        assert rankings[0].same_room is True
        hp = higher_stat_probability(50)
        assert rankings[0].expected_score == pytest.approx(
            6 * hp + 4 * (1 - hp), rel=1e-5
        )


class TestRankPairsOverall:
    def test_inbreeding_penalty_reduces_score(self):
        low = _cat(1, "M", "male", breed_coefficient=0.0, bases=_SEVEN_FIVES)
        f_low = _cat(2, "F", "female", breed_coefficient=0.0, bases=_SEVEN_FIVES)
        high = _cat(3, "M2", "male", breed_coefficient=0.5, bases=_SEVEN_FIVES)
        f_high = _cat(4, "F2", "female", breed_coefficient=0.5, bases=_SEVEN_FIVES)
        r1 = rank_pairs_overall([low, f_low], room_stats=None, max_results=10)
        r2 = rank_pairs_overall([high, f_high], room_stats=None, max_results=10)
        assert r1[0].expected_score > r2[0].expected_score


class TestSuggestRoomDistribution:
    def test_pairs_male_female_into_room(self):
        m = _cat(1, "M", "male", bases=_SEVEN_FIVES)
        f = _cat(2, "F", "female", bases=_SEVEN_FIVES)
        rooms = {"Only": RoomStats(stimulation=10, comfort=15, cat_count=0)}
        dist = suggest_room_distribution([m, f], rooms)
        assert len(dist.rooms) == 1
        ra = dist.rooms[0]
        assert set(ra.cat_keys) == {1, 2}
        assert ra.best_pair == (1, 2) or ra.best_pair == (2, 1)
        assert ra.effective_comfort == 15 - max(0, 2 - COMFORT_CAT_LIMIT)


class TestComfortCatLimitConstant:
    """Keep in sync with save_reader.RoomStats per-cat threshold."""

    def test_matches_room_stats_threshold(self):
        assert COMFORT_CAT_LIMIT == RoomStats._CAT_COMFORT_THRESHOLD
