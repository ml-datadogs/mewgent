from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

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
