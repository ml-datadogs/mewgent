"""Quick OCR test on saved screenshots with optional ground-truth validation.

Looks for fixture JSONs in tests/fixtures/ alongside matching PNGs.
Falls back to debug_screenshots/ for images without fixtures.

Usage:
    uv run python -m tools.test_ocr
    uv run python -m tools.test_ocr tests/fixtures/dingle.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

from src.data.stat_parser import STAT_NAMES, parse_regions
from src.utils.config_loader import PROJECT_ROOT, load_config
from src.vision.ocr_engine import OCREngine
from src.vision.region_crop import RegionCropper

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
DEBUG_DIR = PROJECT_ROOT / "debug_screenshots"

STAT_FIELDS = [f"stat_{sn}" for sn in STAT_NAMES]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def _load_ground_truth(image_path: Path) -> dict | None:
    json_path = image_path.with_suffix(".json")
    if not json_path.exists():
        json_path = FIXTURES_DIR / (image_path.stem + ".json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _resolve_images(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(p) for p in argv]

    images: list[Path] = []
    for path in sorted(FIXTURES_DIR.glob("*.png")):
        images.append(path)
    if not images:
        for name in ["dingle.png"]:
            p = DEBUG_DIR / name
            if p.exists():
                images.append(p)
    return images


def main() -> None:
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

    images = _resolve_images(sys.argv[1:])
    if not images:
        print("No images found. Place PNGs in tests/fixtures/ or debug_screenshots/.")
        return

    total_fields = 0
    total_pass = 0
    total_fail = 0

    for img_path in images:
        print(f"\n{'=' * 60}")
        print(f"  {img_path.name}")
        print(f"{'=' * 60}")

        frame = cv2.imread(str(img_path))
        if frame is None:
            print(f"  {RED}ERROR: could not read image{RESET}")
            continue

        crops = cropper.crop_all(frame)
        results = ocr.recognise_regions(crops, allowlists)

        print("  Raw OCR:")
        for k, v in sorted(results.items()):
            print(f"    {k}: '{v}'")

        stats = parse_regions(results)
        print(f"\n  Parsed:")
        print(f"    Name: {stats.cat_name}")
        for sn in STAT_NAMES:
            sv = getattr(stats, f"stat_{sn}")
            print(f"    {sn.upper()}: total={sv.total}  base={sv.base}  bonus={sv.bonus}")

        ground_truth = _load_ground_truth(img_path)
        if ground_truth is None:
            print(f"\n  {YELLOW}No ground truth JSON found — skipping validation{RESET}")
            continue

        print(f"\n  Validation:")

        if "cat_name" in ground_truth:
            total_fields += 1
            if stats.cat_name == ground_truth["cat_name"]:
                total_pass += 1
                print(f"    {GREEN}PASS{RESET}  cat_name: '{stats.cat_name}'")
            else:
                total_fail += 1
                print(f"    {RED}FAIL{RESET}  cat_name: got '{stats.cat_name}', expected '{ground_truth['cat_name']}'")

        for key in STAT_FIELDS:
            if key not in ground_truth:
                continue
            expected = ground_truth[key]
            sv = getattr(stats, key)

            if isinstance(expected, dict):
                for sub in ("total", "base", "bonus"):
                    if sub not in expected:
                        continue
                    exp_val = expected[sub]
                    actual_val = getattr(sv, sub)
                    total_fields += 1
                    label = f"{key}.{sub}"
                    if actual_val == exp_val:
                        total_pass += 1
                        print(f"    {GREEN}PASS{RESET}  {label}: {actual_val}")
                    else:
                        total_fail += 1
                        print(f"    {RED}FAIL{RESET}  {label}: got {actual_val}, expected {exp_val}")
            else:
                total_fields += 1
                if sv.total == expected:
                    total_pass += 1
                    print(f"    {GREEN}PASS{RESET}  {key}: {sv.total}")
                else:
                    total_fail += 1
                    print(f"    {RED}FAIL{RESET}  {key}: got {sv.total}, expected {expected}")

    print(f"\n{'=' * 60}")
    print(f"  Summary: {total_pass} passed, {total_fail} failed, {total_fields} total")
    if total_fail:
        print(f"  {RED}SOME TESTS FAILED{RESET}")
    elif total_fields:
        print(f"  {GREEN}ALL TESTS PASSED{RESET}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
