"""Tests for WebChannel JSON payload helpers."""

from src.data.save_reader import SaveCat
from src.ui.payload import serialize_catalog_cats


def test_serialize_catalog_preserves_status() -> None:
    cats = [
        SaveCat(db_key=1, name="In", status="in_house"),
        SaveCat(db_key=2, name="Past", status="historical"),
    ]
    out = serialize_catalog_cats(cats)
    assert len(out) == 2
    assert out[0]["db_key"] == 1
    assert out[0]["status"] == "in_house"
    assert out[1]["status"] == "historical"
