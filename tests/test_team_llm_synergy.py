"""Tests for team LLM synergy formatting and save → stash id helpers."""

from __future__ import annotations

from pathlib import Path

from src.data.save_reader import read_save
from src.llm.advisor import (
    format_team_llm_synergy_text,
    inventory_item_ids_from_save,
    stash_text_for_team_prompt,
    team_synergy_ui_payload,
)

FIXTURE_SAV = Path(__file__).resolve().parent / "fixtures" / "steamcampaign03.sav"


def test_format_team_llm_synergy_merges_tips():
    text = format_team_llm_synergy_text(
        {
            "synergy": "Tank + Mage core.",
            "inventory_tips": [
                {
                    "item_id": "HeadWrap",
                    "equip_on": "Mittens",
                    "reason": "Extra regen for the frontliner.",
                }
            ],
        }
    )
    assert "Tank + Mage" in text
    assert "Stash / loadout ideas:" in text
    assert "HeadWrap" in text
    assert "Mittens" in text


def test_inventory_item_ids_from_save_fixture():
    save = read_save(FIXTURE_SAV)
    ids = inventory_item_ids_from_save(save)
    assert len(ids) >= 10
    assert len(ids) == len(set(ids))


def test_stash_text_includes_slot_for_known_item():
    lines = stash_text_for_team_prompt(["HeadWrap", "UnknownItemZZZ"])
    assert "HeadWrap" in lines
    assert "[Head]" in lines


def test_team_synergy_ui_payload_enriches_tips():
    payload = team_synergy_ui_payload(
        {
            "synergy": "Solid frontline.",
            "inventory_tips": [
                {
                    "item_id": "HeadWrap",
                    "equip_on": "Pat",
                    "reason": "Regen for tank.",
                }
            ],
        }
    )
    assert payload["synergy"] == "Solid frontline."
    assert len(payload["stash_tips"]) == 1
    tip = payload["stash_tips"][0]
    assert tip["item_id"] == "HeadWrap"
    assert tip["equip_on"] == "Pat"
    assert tip["reason"] == "Regen for tank."
    assert tip.get("icon_url")
    assert tip.get("slot") == "Head"
