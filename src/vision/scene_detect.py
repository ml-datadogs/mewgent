from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("mewgent.vision.scene_detect")


class SceneDetector:
    """Detect whether the current frame shows a known game screen (e.g. cat stats)."""

    def __init__(self) -> None:
        self._templates: dict[str, tuple[np.ndarray, float, list[int]]] = {}

    def load_template(
        self,
        name: str,
        path: str | Path,
        threshold: float = 0.80,
        match_region: list[int] | None = None,
    ) -> bool:
        """Load a reference template image. Returns True on success."""
        p = Path(path)
        if not p.exists():
            log.warning("Template file not found: %s — scene '%s' disabled", p, name)
            return False

        tpl = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if tpl is None:
            log.warning("Failed to read template: %s", p)
            return False

        region = match_region or [0, 0, 0, 0]
        self._templates[name] = (tpl, threshold, region)
        log.info("Template loaded: '%s' from %s  (threshold=%.2f)", name, p, threshold)
        return True

    def detect(self, frame: np.ndarray) -> str | None:
        """Check the frame against all loaded templates.

        Returns the name of the first matching scene, or None.
        If no templates are loaded, returns 'cat_stats_screen' (skip detection).
        """
        if not self._templates:
            return "cat_stats_screen"

        for name, (tpl, threshold, region) in self._templates.items():
            x, y, w, h = region
            if w > 0 and h > 0:
                roi = frame[y : y + h, x : x + w]
            else:
                roi = frame

            if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
                log.debug("ROI too small for template '%s', trying full frame", name)
                roi = frame

            if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
                continue

            result = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            log.debug("Template '%s' match: %.3f at %s", name, max_val, max_loc)

            if max_val >= threshold:
                return name

        return None
