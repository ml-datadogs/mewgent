from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from src.utils.config_loader import RegionDef

log = logging.getLogger("mewgent.ui.debug_panel")


def draw_regions_on_frame(
    frame: np.ndarray,
    regions: dict[str, RegionDef],
    reference_resolution: tuple[int, int] = (1920, 1080),
) -> np.ndarray:
    """Draw labelled rectangles on a copy of the frame for visual debugging."""
    canvas = frame.copy()
    h, w = canvas.shape[:2]
    ref_w, ref_h = reference_resolution
    sx = w / ref_w
    sy = h / ref_h

    for name, rdef in regions.items():
        rx, ry, rw, rh = rdef.rect
        x1 = int(rx * sx)
        y1 = int(ry * sy)
        x2 = x1 + int(rw * sx)
        y2 = y1 + int(rh * sy)

        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(canvas, name, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    return canvas


def save_calibration_image(
    frame: np.ndarray,
    regions: dict[str, RegionDef],
    output_path: str | Path = "debug_screenshots/calibration.png",
    reference_resolution: tuple[int, int] = (1920, 1080),
) -> Path:
    """Capture one frame, overlay region rectangles, and save for the user to verify."""
    annotated = draw_regions_on_frame(frame, regions, reference_resolution)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), annotated)
    log.info("Calibration image saved: %s", p)
    return p
