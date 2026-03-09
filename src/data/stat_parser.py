from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

log = logging.getLogger("mewgent.data.stat_parser")


@dataclass
class CatStats:
    cat_name: str = ""
    stat_str: int = 0
    stat_dex: int = 0
    stat_con: int = 0
    stat_int: int = 0
    stat_spd: int = 0
    stat_cha: int = 0
    stat_lck: int = 0
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        """Deterministic string for dedup (ignores timestamp)."""
        parts = [
            self.cat_name.strip().lower(),
            str(self.stat_str),
            str(self.stat_dex),
            str(self.stat_con),
            str(self.stat_int),
            str(self.stat_spd),
            str(self.stat_cha),
            str(self.stat_lck),
        ]
        return "|".join(parts)


def _safe_int(raw: str) -> int:
    """Extract the first integer from an OCR string."""
    cleaned = "".join(ch for ch in raw if ch.isdigit())
    if not cleaned:
        return 0
    return int(cleaned)


def parse_regions(ocr_results: dict[str, str]) -> CatStats:
    """Convert raw OCR text dict into a typed CatStats object."""
    stats = CatStats(
        cat_name=ocr_results.get("cat_name", "").strip(),
        stat_str=_safe_int(ocr_results.get("stat_str", "")),
        stat_dex=_safe_int(ocr_results.get("stat_dex", "")),
        stat_con=_safe_int(ocr_results.get("stat_con", "")),
        stat_int=_safe_int(ocr_results.get("stat_int", "")),
        stat_spd=_safe_int(ocr_results.get("stat_spd", "")),
        stat_cha=_safe_int(ocr_results.get("stat_cha", "")),
        stat_lck=_safe_int(ocr_results.get("stat_lck", "")),
    )
    log.info("Parsed stats: name='%s' STR=%d DEX=%d CON=%d INT=%d SPD=%d CHA=%d LCK=%d",
             stats.cat_name, stats.stat_str, stats.stat_dex, stats.stat_con,
             stats.stat_int, stats.stat_spd, stats.stat_cha, stats.stat_lck)
    return stats
