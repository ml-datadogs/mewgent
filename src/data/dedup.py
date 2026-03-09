from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict

import imagehash
import numpy as np
from PIL import Image

from src.data.stat_parser import CatStats

log = logging.getLogger("mewgent.data.dedup")


class DuplicateGuard:
    """Three-layer duplicate detection:

    1. Frame-level perceptual hash (skip re-OCR of unchanged frames)
    2. Field fingerprint (skip DB write if identical parsed data)
    3. DB UNIQUE constraint (final safety net, handled in SQLiteStore)
    """

    def __init__(self, phash_threshold: int = 6, cache_size: int = 64) -> None:
        self._phash_threshold = phash_threshold
        self._last_frame_hash: imagehash.ImageHash | None = None
        self._seen_fingerprints: OrderedDict[str, bool] = OrderedDict()
        self._cache_size = cache_size

    def is_same_frame(self, frame: np.ndarray) -> bool:
        """Return True if the frame is perceptually identical to the last one."""
        pil = Image.fromarray(frame[:, :, ::-1])  # BGR -> RGB
        current_hash = imagehash.phash(pil)

        if self._last_frame_hash is not None:
            dist = current_hash - self._last_frame_hash
            if dist <= self._phash_threshold:
                log.debug("Frame duplicate (phash distance=%d, threshold=%d)", dist, self._phash_threshold)
                return True

        self._last_frame_hash = current_hash
        return False

    def is_duplicate_stats(self, stats: CatStats) -> bool:
        """Return True if these exact stats have already been recorded recently."""
        fp = stats.fingerprint()
        if fp in self._seen_fingerprints:
            log.debug("Duplicate stats fingerprint: %s", fp)
            return True

        self._seen_fingerprints[fp] = True
        if len(self._seen_fingerprints) > self._cache_size:
            self._seen_fingerprints.popitem(last=False)

        return False

    def snapshot_hash(self, stats: CatStats) -> str:
        """Compute a deterministic hash for the DB unique constraint."""
        return hashlib.sha256(stats.fingerprint().encode()).hexdigest()[:16]
