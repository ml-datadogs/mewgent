"""Tests for the Mewgenics save file parser.

Uses a real save file (steamcampaign03.sav) as a fixture with known
ground-truth values extracted from the game.
"""

from __future__ import annotations

import pytest

from src.data.save_reader import (
    SaveData,
    _normalize_gender,
    _parse_inventory_blob,
    _valid_str,
    find_save_files,
)


# ── Save-level properties ────────────────────────────────────────────────


class TestSaveProperties:
    def test_current_day(self, save_data: SaveData):
        assert save_data.current_day == 171

    def test_house_gold(self, save_data: SaveData):
        assert save_data.house_gold == 195

    def test_house_food(self, save_data: SaveData):
        assert save_data.house_food == 244

    def test_owner_steamid(self, save_data: SaveData):
        assert save_data.owner_steamid == "76561198103052764"

    def test_total_cats(self, save_data: SaveData):
        assert len(save_data.cats) == 348

    def test_house_cats_count(self, save_data: SaveData):
        assert len(save_data.house_cats) == 17

    def test_unlocked_classes(self, save_data: SaveData):
        assert len(save_data.unlocked_classes) == 10
        assert "Fighter" in save_data.unlocked_classes
        assert "Mage" in save_data.unlocked_classes
        assert "Tinkerer" in save_data.unlocked_classes

    def test_unlocked_rooms(self, save_data: SaveData):
        assert save_data.unlocked_rooms == [
            "Floor1_Large",
            "Floor1_Small",
            "Floor2_Large",
            "Attic",
        ]


class TestInventory:
    def test_fixture_counts(self, save_data: SaveData):
        assert len(save_data.inventory_backpack) == 0
        assert len(save_data.inventory_storage) == 39
        assert len(save_data.inventory_trash) == 12

    def test_fixture_sample_ids(self, save_data: SaveData):
        storage_ids = {x.item_id for x in save_data.inventory_storage}
        trash_ids = {x.item_id for x in save_data.inventory_trash}
        assert "HeadWrap" in storage_ids
        assert "Whistle" in storage_ids
        assert "LuckyMask" in trash_ids
        assert "Antidote" in trash_ids

    def test_parse_empty_backpack_blob(self):
        assert _parse_inventory_blob(b"\x00\x00\x00\x00") == []
        assert _parse_inventory_blob(b"") == []
        assert _parse_inventory_blob(None) == []


# ── Cat parsing (parametrized) ───────────────────────────────────────────

_CAT_GROUND_TRUTH = {
    319: {
        "name": "Greifi",
        "gender": "female",
        "status": "in_house",
        "stats": (6, 6, 7, 5, 5, 5, 4),
    },
    323: {
        "name": "Lobo",
        "gender": "male",
        "status": "in_house",
        "stats": (6, 4, 5, 7, 5, 5, 4),
    },
    326: {
        "name": "Enzo",
        "gender": "male",
        "status": "in_house",
        "stats": (6, 6, 7, 3, 5, 5, 4),
    },
    332: {
        "name": "Sloane",
        "gender": "female",
        "status": "in_house",
        "stats": (4, 5, 5, 7, 5, 6, 5),
    },
    333: {
        "name": "Dingle",
        "gender": "male",
        "status": "historical",
        "stats": (5, 6, 7, 7, 5, 5, 7),
    },
    318: {
        "name": "William",
        "gender": "male",
        "status": "historical",
        "stats": (6, 7, 7, 3, 5, 5, 4),
    },
    345: {
        "name": "Musya",
        "gender": "female",
        "status": "in_house",
        "stats": (5, 5, 5, 7, 7, 4, 4),
    },
    353: {
        "name": "Lucyfer",
        "gender": "male",
        "status": "in_house",
        "stats": (3, 6, 5, 5, 7, 5, 5),
    },
}


def _cat_by_key(save_data: SaveData, key: int):
    for c in save_data.cats:
        if c.db_key == key:
            return c
    pytest.fail(f"Cat with db_key={key} not found")


@pytest.mark.parametrize(
    "db_key",
    list(_CAT_GROUND_TRUTH.keys()),
    ids=[str(v["name"]) for v in _CAT_GROUND_TRUTH.values()],
)
class TestCatParsing:
    def test_name(self, save_data: SaveData, db_key: int):
        cat = _cat_by_key(save_data, db_key)
        assert cat.name == _CAT_GROUND_TRUTH[db_key]["name"]

    def test_gender(self, save_data: SaveData, db_key: int):
        cat = _cat_by_key(save_data, db_key)
        assert cat.gender == _CAT_GROUND_TRUTH[db_key]["gender"]

    def test_status(self, save_data: SaveData, db_key: int):
        cat = _cat_by_key(save_data, db_key)
        assert cat.status == _CAT_GROUND_TRUTH[db_key]["status"]

    def test_stats(self, save_data: SaveData, db_key: int):
        cat = _cat_by_key(save_data, db_key)
        actual = (
            cat.base_str,
            cat.base_dex,
            cat.base_con,
            cat.base_int,
            cat.base_spd,
            cat.base_cha,
            cat.base_lck,
        )
        assert actual == _CAT_GROUND_TRUTH[db_key]["stats"]


class TestCatAbilities:
    def test_greifi_abilities(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 319)
        assert "BasicTankMelee" in cat.abilities
        assert "Earthquake" in cat.abilities

    def test_greifi_passives(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 319)
        assert "HomeRun" in cat.passives

    def test_musya_abilities(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 345)
        assert "TinkererCraft" in cat.abilities
        assert "TeslaCoil" in cat.abilities

    def test_musya_passives(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 345)
        assert "EMP" in cat.passives
        assert "Unrestricted" in cat.passives

    def test_johan_abilities(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 334)
        assert "BasicMedicMelee" in cat.abilities
        assert "BlindingLight" in cat.abilities

    def test_choochoo_abilities(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 347)
        assert "FreezeRay" in cat.abilities


# ── Relationships / pedigree ─────────────────────────────────────────────


class TestRelationships:
    def test_greifi_parents(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 319)
        assert cat.parent_a_key == 318  # William
        assert cat.parent_b_key == 313  # Mili

    def test_dingle_parents(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 333)
        assert cat.parent_a_key == 326  # Enzo
        assert cat.parent_b_key == 329

    def test_greifi_children(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 319)
        for child_key in (326, 328, 336, 343):
            assert child_key in cat.children_keys

    def test_lobo_children(self, save_data: SaveData):
        cat = _cat_by_key(save_data, 323)
        for child_key in (328, 331, 334, 352):
            assert child_key in cat.children_keys

    def test_generation_depth(self, save_data: SaveData):
        william = _cat_by_key(save_data, 318)
        assert william.generation == 0

        pandora = _cat_by_key(save_data, 298)
        assert pandora.generation == 0

        dingle = _cat_by_key(save_data, 333)
        assert dingle.generation == 4

        tripp = _cat_by_key(save_data, 317)
        assert tripp.generation == 2

    def test_orphan_has_no_parents(self, save_data: SaveData):
        sloane = _cat_by_key(save_data, 332)
        assert sloane.parent_a_key == 0
        assert sloane.parent_b_key == 0


# ── Status assignment ────────────────────────────────────────────────────


class TestStatusAssignment:
    def test_dead_cats(self, save_data: SaveData):
        dead_keys = {c.db_key for c in save_data.cats if c.status == "dead"}
        for key in (1, 10, 50, 100, 127):
            assert key in dead_keys, f"Cat #{key} should be dead"

    def test_house_cats(self, save_data: SaveData):
        house_keys = {c.db_key for c in save_data.cats if c.status == "in_house"}
        for key in (319, 323, 326, 328, 332, 334, 336, 343, 345):
            assert key in house_keys, f"Cat #{key} should be in_house"

    def test_historical_cats(self, save_data: SaveData):
        hist_keys = {c.db_key for c in save_data.cats if c.status == "historical"}
        for key in (129, 131, 298, 318, 333):
            assert key in hist_keys, f"Cat #{key} should be historical"

    def test_house_cats_property(self, save_data: SaveData):
        house_cats = save_data.house_cats
        assert all(c.status == "in_house" for c in house_cats)
        assert len(house_cats) == 17


# ── Helper functions ─────────────────────────────────────────────────────


class TestValidStr:
    @pytest.mark.parametrize(
        "val",
        ["none", "null", "", "None", "NULL", "defaultmove", "default_move"],
    )
    def test_rejects_junk(self, val: str):
        assert _valid_str(val) is False

    @pytest.mark.parametrize("val", ["Fighter", "BasicMelee", "Earthquake", "A"])
    def test_accepts_valid(self, val: str):
        assert _valid_str(val) is True

    def test_rejects_none(self):
        assert _valid_str(None) is False


class TestNormalizeGender:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("male", "male"),
            ("male_cat", "male"),
            ("female", "female"),
            ("female_something", "female"),
            ("spidercat", "?"),
            ("", "?"),
            (None, "?"),
            ("unknown_value", "?"),
        ],
    )
    def test_normalize(self, raw: str | None, expected: str):
        assert _normalize_gender(raw) == expected


class TestFindSaveFiles:
    def test_finds_saves(self):
        saves = find_save_files()
        if not saves:
            pytest.skip(
                "No Mewgenics save files (normal on CI / machines without the game)"
            )
        assert any(s.name.endswith(".sav") for s in saves)


class TestRoomStats:
    def test_room_stats_has_no_empty_keys(self, save_data: SaveData):
        assert "" not in save_data.room_stats

    def test_room_stats_has_known_rooms(self, save_data: SaveData):
        assert "Floor1_Large" in save_data.room_stats

    def test_furniture_distributed_to_rooms(self, save_data: SaveData):
        total_furniture = sum(
            rs.furniture_count for rs in save_data.room_stats.values()
        )
        assert total_furniture > 0
        rooms_with_furniture = [
            name for name, rs in save_data.room_stats.items() if rs.furniture_count > 0
        ]
        assert len(rooms_with_furniture) >= 2

    def test_stats_computed_from_furniture(self, save_data: SaveData):
        rs = save_data.room_stats["Floor1_Large"]
        assert rs.furniture_count == 29
        assert rs.appeal == 6
        assert rs.comfort == 21
        assert rs.stimulation == 15
        assert rs.health == 6
        assert rs.mutation == 0
