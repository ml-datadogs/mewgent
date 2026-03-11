from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

log = logging.getLogger("mewgent.data.stat_parser")

STAT_NAMES = ["str", "dex", "con", "int", "spd", "cha", "lck"]


@dataclass
class StatValue:
    total: int = 0
    base: int = 0
    bonus: int = 0

    def __int__(self) -> int:
        return self.total


@dataclass
class CatStats:
    cat_name: str = ""
    stat_str: StatValue = field(default_factory=StatValue)
    stat_dex: StatValue = field(default_factory=StatValue)
    stat_con: StatValue = field(default_factory=StatValue)
    stat_int: StatValue = field(default_factory=StatValue)
    stat_spd: StatValue = field(default_factory=StatValue)
    stat_cha: StatValue = field(default_factory=StatValue)
    stat_lck: StatValue = field(default_factory=StatValue)
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        """Deterministic string for dedup (ignores timestamp)."""
        parts = [self.cat_name.strip().lower()]
        for sn in STAT_NAMES:
            sv: StatValue = getattr(self, f"stat_{sn}")
            parts.append(f"{sv.total}/{sv.base}/{sv.bonus}")
        return "|".join(parts)


def _safe_int(raw: str) -> int:
    """Extract the first integer (possibly negative or with +) from an OCR string."""
    m = re.search(r"[+-]?\d+", raw)
    if not m:
        return 0
    return int(m.group())


def parse_regions(ocr_results: dict[str, str]) -> CatStats:
    """Convert raw OCR text dict into a typed CatStats object.

    Expects keys like ``stat_str_total``, ``stat_str_base``, ``stat_str_bonus``
    for each stat, produced by RegionCropper from triple-rect regions.
    """
    stats = CatStats(cat_name=ocr_results.get("cat_name", "").strip())

    for sn in STAT_NAMES:
        total = _safe_int(ocr_results.get(f"stat_{sn}_total", ""))
        base = _safe_int(ocr_results.get(f"stat_{sn}_base", ""))
        bonus = _safe_int(ocr_results.get(f"stat_{sn}_bonus", ""))
        setattr(stats, f"stat_{sn}", StatValue(total=total, base=base, bonus=bonus))

    log.info(
        "Parsed stats: name='%s' STR=%d DEX=%d CON=%d INT=%d SPD=%d CHA=%d LCK=%d",
        stats.cat_name,
        stats.stat_str.total, stats.stat_dex.total, stats.stat_con.total,
        stats.stat_int.total, stats.stat_spd.total, stats.stat_cha.total,
        stats.stat_lck.total,
    )
    return stats
