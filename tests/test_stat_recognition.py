"""Stat recognition tests against ground-truth fixtures.

Fixtures live in tests/fixtures/ as paired PNG + JSON files.
To add a new test case, drop a screenshot and a matching JSON
with expected CatStats fields — the parametrized test discovers
them automatically.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import pytest

from src.data.stat_parser import STAT_NAMES, StatValue, _safe_int, parse_regions
from src.utils.config_loader import PROJECT_ROOT, load_config
from src.vision.ocr_engine import OCREngine
from src.vision.region_crop import RegionCropper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

STAT_FIELDS = [f"stat_{sn}" for sn in STAT_NAMES]


@dataclass
class Fixture:
    name: str
    image_path: Path
    expected: dict


def discover_fixtures() -> list[Fixture]:
    fixtures: list[Fixture] = []
    for json_path in sorted(FIXTURES_DIR.glob("*.json")):
        image_path = json_path.with_suffix(".png")
        if not image_path.exists():
            continue
        with open(json_path, encoding="utf-8") as f:
            expected = json.load(f)
        fixtures.append(Fixture(
            name=json_path.stem,
            image_path=image_path,
            expected=expected,
        ))
    return fixtures


_fixtures = discover_fixtures()


@pytest.fixture(scope="module")
def pipeline():
    cfg = load_config()
    ref_res = tuple(cfg.regions.game_resolution)
    cropper = RegionCropper(
        cfg.regions.regions,
        reference_resolution=ref_res,
    )
    ocr = OCREngine(gpu=True)

    allowlists: dict[str, str] = {}
    for name, rdef in cfg.regions.regions.items():
        if rdef.is_stat_triple:
            for suffix in ("total", "base", "bonus"):
                allowlists[f"{name}_{suffix}"] = rdef.allowlist
        else:
            allowlists[name] = rdef.allowlist

    return cropper, ocr, allowlists


@pytest.mark.parametrize(
    "fixture",
    _fixtures,
    ids=[f.name for f in _fixtures],
)
def test_stat_recognition(pipeline, fixture: Fixture):
    cropper, ocr, allowlists = pipeline

    frame = cv2.imread(str(fixture.image_path))
    assert frame is not None, f"Could not read {fixture.image_path}"

    crops = cropper.crop_all(frame)
    results = ocr.recognise_regions(crops, allowlists)
    stats = parse_regions(results)

    expected = fixture.expected
    errors: list[str] = []

    if "cat_name" in expected:
        if stats.cat_name != expected["cat_name"]:
            errors.append(
                f"cat_name: got '{stats.cat_name}', expected '{expected['cat_name']}'"
            )

    for key in STAT_FIELDS:
        if key not in expected:
            continue
        exp = expected[key]
        sv: StatValue = getattr(stats, key)

        if isinstance(exp, dict):
            for sub in ("total", "base", "bonus"):
                if sub not in exp:
                    continue
                actual_val = getattr(sv, sub)
                exp_val = exp[sub]
                if actual_val != exp_val:
                    errors.append(f"{key}.{sub}: got {actual_val}, expected {exp_val}")
        else:
            if sv.total != exp:
                errors.append(f"{key}.total: got {sv.total}, expected {exp}")

    assert not errors, "Mismatches:\n  " + "\n  ".join(errors)


# ------------------------------------------------------------------
# Unit tests for _safe_int
# ------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("5", 5),
    ("12", 12),
    ("-3", -3),
    ("-12", -12),
    ("  7 ", 7),
    ("abc", 0),
    ("", 0),
    ("stat: -5!", -5),
    ("--3", -3),
    ("0", 0),
    ("-0", 0),
    ("+5", 5),
    ("+0", 0),
])
def test_safe_int(raw: str, expected: int):
    assert _safe_int(raw) == expected
