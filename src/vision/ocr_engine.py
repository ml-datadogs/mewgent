from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

log = logging.getLogger("mewgent.vision.ocr_engine")

_reader_instance: Any = None


def _get_reader(gpu: bool = True, languages: list[str] | None = None) -> Any:
    """Lazily initialise a singleton EasyOCR Reader."""
    global _reader_instance
    if _reader_instance is not None:
        return _reader_instance

    import easyocr

    langs = languages or ["en"]
    log.info("Initialising EasyOCR  gpu=%s  languages=%s  (first call downloads models)", gpu, langs)
    _reader_instance = easyocr.Reader(langs, gpu=gpu)
    log.info("EasyOCR ready")
    return _reader_instance


class OCREngine:
    """Run OCR on cropped region images using EasyOCR (GPU-accelerated)."""

    def __init__(self, gpu: bool = True, languages: list[str] | None = None) -> None:
        self._gpu = gpu
        self._languages = languages or ["en"]

    def recognise(self, image: np.ndarray, allowlist: str = "") -> str:
        """Run OCR on a single image region and return the recognised text."""
        reader = _get_reader(self._gpu, self._languages)

        # EasyOCR expects RGB or grayscale
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        kwargs: dict[str, Any] = {"detail": 0, "paragraph": True}
        if allowlist:
            kwargs["allowlist"] = allowlist

        results = reader.readtext(image, **kwargs)
        text = " ".join(results).strip() if results else ""
        log.debug("OCR result: '%s'  (allowlist='%s')", text, allowlist)
        return text

    def recognise_regions(
        self, crops: dict[str, np.ndarray], allowlists: dict[str, str] | None = None
    ) -> dict[str, str]:
        """OCR every cropped region and return a name->text mapping."""
        alists = allowlists or {}
        out: dict[str, str] = {}
        for name, img in crops.items():
            al = alists.get(name, "")
            out[name] = self.recognise(img, allowlist=al)
        return out
