"""Mewgent — Live Mewgenics Companion App.

Entry point: ``python -m src.main``
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from src.capture.screen_grab import ScreenGrabber
from src.capture.window_bind import WindowBinder
from src.data.db import SQLiteStore
from src.data.dedup import DuplicateGuard
from src.data.stat_parser import parse_regions
from src.utils.config_loader import PROJECT_ROOT, AppConfig, load_config
from src.utils.logging_setup import setup_logging
from src.vision.ocr_engine import OCREngine
from src.vision.region_crop import RegionCropper
from src.vision.scene_detect import SceneDetector

log = logging.getLogger("mewgent.main")


def _build_pipeline(cfg: AppConfig):
    """Instantiate all pipeline components from config."""
    binder = WindowBinder(
        title=cfg.capture.window_title,
        dpi_aware=cfg.capture.dpi_aware,
    )

    debug_dir = str(PROJECT_ROOT / cfg.debug.screenshots_dir) if cfg.debug.save_screenshots else None
    grabber = ScreenGrabber(debug_dir=debug_dir)

    detector = SceneDetector()
    for name, tdef in cfg.regions.scene_templates.items():
        tpl_path = PROJECT_ROOT / tdef.file
        detector.load_template(name, tpl_path, tdef.match_threshold, tdef.match_region)

    ref_res = tuple(cfg.regions.game_resolution)
    cropper = RegionCropper(cfg.regions.regions, reference_resolution=ref_res)

    ocr = OCREngine(gpu=cfg.ocr.gpu, languages=cfg.ocr.languages)

    db = SQLiteStore(str(PROJECT_ROOT / cfg.database.path))
    dedup = DuplicateGuard()

    return binder, grabber, detector, cropper, ocr, db, dedup


def run_headless(cfg: AppConfig) -> None:
    """Main capture loop without GUI — useful for testing the pipeline."""
    binder, grabber, detector, cropper, ocr, db, dedup = _build_pipeline(cfg)

    allowlists = {name: rdef.allowlist for name, rdef in cfg.regions.regions.items()}

    log.info("Starting headless capture loop  (interval=%dms)", cfg.capture.interval_ms)
    log.info("Waiting for game window '%s'…", cfg.capture.window_title)
    binder.wait_for_window(poll_interval=2.0)
    log.info("Game window found — entering scan loop")

    interval_s = cfg.capture.interval_ms / 1000.0

    try:
        while True:
            hwnd = binder.hwnd
            if hwnd is None:
                binder.find()
                time.sleep(interval_s)
                continue

            frame = grabber.capture_and_save_debug(hwnd)
            if frame is None:
                binder.find()
                time.sleep(interval_s)
                continue

            # Layer 1: frame-level dedup
            if dedup.is_same_frame(frame):
                time.sleep(interval_s)
                continue

            scene = detector.detect(frame)
            if scene != "cat_stats_screen":
                log.debug("Not a cat stats screen (scene=%s)", scene)
                time.sleep(interval_s)
                continue

            crops = cropper.crop_all(frame)
            ocr_results = ocr.recognise_regions(crops, allowlists)
            stats = parse_regions(ocr_results)

            if not stats.cat_name:
                log.debug("OCR returned empty cat name — skipping")
                time.sleep(interval_s)
                continue

            # Layer 2: field-level dedup
            if dedup.is_duplicate_stats(stats):
                time.sleep(interval_s)
                continue

            # Layer 3: DB insert (UNIQUE constraint as final guard)
            snap_hash = dedup.snapshot_hash(stats)
            db.save_cat(stats, snap_hash)
            log.info("Cats in DB: %d", db.count_cats())

            time.sleep(interval_s)

    except KeyboardInterrupt:
        log.info("Stopped by user")
    finally:
        db.close()


def run_gui(cfg: AppConfig) -> None:
    """Main entry point with PySide6 overlay."""
    from PySide6.QtWidgets import QApplication

    from src.ui.overlay import MewgentOverlay

    app = QApplication(sys.argv)
    pipeline = _build_pipeline(cfg)
    overlay = MewgentOverlay(cfg, pipeline)
    overlay.show()
    sys.exit(app.exec())


def main() -> None:
    cfg = load_config()
    setup_logging(level=cfg.logging.level, log_file=cfg.logging.file)
    log.info("Mewgent v%s starting", "0.1.0")

    if "--headless" in sys.argv:
        run_headless(cfg)
    else:
        run_gui(cfg)


if __name__ == "__main__":
    main()
