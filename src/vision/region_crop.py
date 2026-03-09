from __future__ import annotations

import logging

import cv2
import numpy as np

from src.utils.config_loader import RegionDef

log = logging.getLogger("mewgent.vision.region_crop")


def _preprocess(img: np.ndarray, steps: list[str]) -> np.ndarray:
    """Apply a sequence of preprocessing steps to a cropped region."""
    result = img
    for step in steps:
        if step == "grayscale":
            if len(result.shape) == 3:
                result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        elif step == "threshold":
            if len(result.shape) == 3:
                result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            _, result = cv2.threshold(result, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif step == "invert":
            result = cv2.bitwise_not(result)
        elif step == "resize2x":
            result = cv2.resize(result, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        else:
            log.warning("Unknown preprocess step: '%s'", step)
    return result


class RegionCropper:
    """Crop named regions from a full frame and apply preprocessing."""

    def __init__(
        self,
        regions: dict[str, RegionDef],
        reference_resolution: tuple[int, int] = (1920, 1080),
    ) -> None:
        self._regions = regions
        self._ref_w, self._ref_h = reference_resolution

    def crop_all(
        self, frame: np.ndarray
    ) -> dict[str, np.ndarray]:
        """Crop all configured regions, scaling rects if the frame size differs from reference."""
        h, w = frame.shape[:2]
        sx = w / self._ref_w
        sy = h / self._ref_h

        crops: dict[str, np.ndarray] = {}
        for name, rdef in self._regions.items():
            rx, ry, rw, rh = rdef.rect
            x = int(rx * sx)
            y = int(ry * sy)
            cw = int(rw * sx)
            ch = int(rh * sy)

            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            cw = max(1, min(cw, w - x))
            ch = max(1, min(ch, h - y))

            crop = frame[y : y + ch, x : x + cw]
            crop = _preprocess(crop, rdef.preprocess)
            crops[name] = crop
            log.debug("Cropped '%s': rect=[%d,%d,%d,%d] -> %s", name, x, y, cw, ch, crop.shape)

        return crops
