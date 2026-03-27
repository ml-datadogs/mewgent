"""Tests for wiki-backed item effect lookup."""

from __future__ import annotations

from pathlib import Path

from src.data.item_effects import (
    item_effect_entry,
    item_effect_for_id,
    item_icon_url_for_id,
    item_slot_for_id,
)
from src.data.save_reader import read_save

FIXTURE_SAV = Path(__file__).resolve().parent / "fixtures" / "steamcampaign03.sav"


def test_known_item_head_wrap():
    eff = item_effect_for_id("HeadWrap")
    assert eff is not None
    assert "Regen" in eff
    assert item_slot_for_id("HeadWrap") == "Head"


def test_alias_water_bottle_empty():
    eff = item_effect_for_id("WaterBottle_Empty")
    assert eff is not None
    assert "Throw" in eff or "Refills" in eff


def test_alias_dumbell():
    eff = item_effect_for_id("Dumbell")
    assert eff is not None


def test_unknown_returns_none():
    assert item_effect_for_id("TotallyFakeItemIdXYZ") is None


def test_broken_mirror_save_id_resolves_trinket_minus_luck():
    """Save uses ``BrokenMirror``; wiki lists trinket vs head armor separately."""
    eff = item_effect_for_id("BrokenMirror")
    assert eff is not None
    assert "-99" in eff
    assert "Luck" in eff
    assert item_slot_for_id("BrokenMirror") == "Trinket"


def test_broken_mirror_head_armor_distinct_key():
    eff = item_effect_for_id("BrokenMirror_HeadArmor")
    assert eff is not None
    assert "Luck" in eff
    assert "Bleed" in eff or "glass" in eff.lower()


def test_head_wrap_wiki_icon_url():
    url = item_icon_url_for_id("HeadWrap")
    assert url is not None
    assert url.startswith("https://mewgenics.wiki.gg/images/ITEM_")
    assert ".svg" in url


def test_broken_mirror_alias_icon_is_trinket_art():
    url = item_icon_url_for_id("BrokenMirror")
    assert url is not None
    assert "Trinket" in url or "trinket" in url.lower()


def test_item_effect_entry_includes_icon_url():
    d = item_effect_entry("HeadWrap")
    assert d["item_id"] == "HeadWrap"
    assert d["effect"] is not None
    assert d["icon_url"] is not None
    assert d["slot"] == "Head"


def test_cursed_rock_shield_label_from_wiki_icon():
    """Wiki uses +6 + shield icon without the word Shield in HTML."""
    eff = item_effect_for_id("CursedRock")
    assert eff is not None
    assert "+6 Shield" in eff
    assert "Strength" in eff


def test_alias_survivalist_gaiter_apostrophe():
    eff = item_effect_for_id("SurvivalistGaiter")
    assert eff is not None
    assert "grass" in eff.lower() or "Stealth" in eff
    assert item_icon_url_for_id("SurvivalistGaiter") is not None


def test_alias_catnip_big_to_large_baggy():
    eff = item_effect_for_id("CatnipBig")
    assert eff is not None
    assert "mana" in eff.lower()


def test_alias_dry_bone_hat_to_helm():
    eff = item_effect_for_id("DryBoneHat")
    assert eff is not None
    assert "Thorns" in eff or "Shield" in eff


def test_lucky_mask_not_on_wiki_items_table():
    """No ``Lucky * Mask`` row on https://mewgenics.wiki.gg/wiki/Items (scraped keys)."""
    assert item_effect_for_id("LuckyMask") is None
    assert item_icon_url_for_id("LuckyMask") is None
    assert item_slot_for_id("LuckyMask") is None


def test_fixture_trash_all_mapped_except_lucky_mask():
    save = read_save(FIXTURE_SAV)
    trash_ids = sorted({x.item_id for x in save.inventory_trash})
    assert "LuckyMask" in trash_ids
    unmapped = [i for i in trash_ids if not item_effect_for_id(i)]
    assert unmapped == ["LuckyMask"]
