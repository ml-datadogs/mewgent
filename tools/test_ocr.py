"""Quick OCR test on saved screenshots."""
import cv2

from src.utils.config_loader import load_config
from src.vision.region_crop import RegionCropper
from src.vision.ocr_engine import OCREngine
from src.data.stat_parser import parse_regions


def main() -> None:
    cfg = load_config()
    cropper = RegionCropper(cfg.regions.regions, tuple(cfg.regions.game_resolution))
    ocr = OCREngine(gpu=True)
    allowlists = {name: r.allowlist for name, r in cfg.regions.regions.items()}

    for img_name in ["william_1.png", "william_2.png", "icon_1.png"]:
        print(f"=== {img_name} ===")
        frame = cv2.imread(f"debug_screenshots/{img_name}")
        if frame is None:
            print("  ERROR: could not read image")
            continue

        crops = cropper.crop_all(frame)
        results = ocr.recognise_regions(crops, allowlists)

        print("  Raw OCR:")
        for k, v in results.items():
            print(f"    {k}: '{v}'")

        stats = parse_regions(results)
        print("  Parsed:")
        print(f"    Name: {stats.cat_name}")
        print(f"    STR={stats.stat_str} DEX={stats.stat_dex} CON={stats.stat_con}")
        print(f"    INT={stats.stat_int} SPD={stats.stat_spd} CHA={stats.stat_cha} LCK={stats.stat_lck}")
        print()


if __name__ == "__main__":
    main()
