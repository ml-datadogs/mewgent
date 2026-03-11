from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.data.stat_parser import STAT_NAMES, CatStats

log = logging.getLogger("mewgent.data.db")

_STAT_COLS = []
for _sn in STAT_NAMES:
    _STAT_COLS.extend([f"stat_{_sn}_total", f"stat_{_sn}_base", f"stat_{_sn}_bonus"])

SCHEMA = """
CREATE TABLE IF NOT EXISTS cats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cat_name        TEXT NOT NULL,
    stat_str_total  INTEGER, stat_str_base INTEGER, stat_str_bonus INTEGER,
    stat_dex_total  INTEGER, stat_dex_base INTEGER, stat_dex_bonus INTEGER,
    stat_con_total  INTEGER, stat_con_base INTEGER, stat_con_bonus INTEGER,
    stat_int_total  INTEGER, stat_int_base INTEGER, stat_int_bonus INTEGER,
    stat_spd_total  INTEGER, stat_spd_base INTEGER, stat_spd_bonus INTEGER,
    stat_cha_total  INTEGER, stat_cha_base INTEGER, stat_cha_bonus INTEGER,
    stat_lck_total  INTEGER, stat_lck_base INTEGER, stat_lck_bonus INTEGER,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    snapshot_hash   TEXT NOT NULL,
    UNIQUE(cat_name, snapshot_hash)
);
"""


class SQLiteStore:
    """Simple SQLite persistence for cat stats."""

    def __init__(self, db_path: str = "data/mewgent.db") -> None:
        p = Path(db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(p)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        log.info("Database opened: %s", p)

    def save_cat(self, stats: CatStats, snapshot_hash: str) -> bool:
        """Insert or update a cat snapshot. Returns True if a new row was inserted."""
        col_names = ", ".join(_STAT_COLS)
        placeholders = ", ".join(["?"] * (1 + len(_STAT_COLS) + 3))

        values: list[Any] = [stats.cat_name]
        for sn in STAT_NAMES:
            sv = getattr(stats, f"stat_{sn}")
            values.extend([sv.total, sv.base, sv.bonus])
        values.extend([stats.captured_at, stats.captured_at, snapshot_hash])

        try:
            self._conn.execute(
                f"""
                INSERT INTO cats (cat_name, {col_names}, first_seen, last_seen, snapshot_hash)
                VALUES ({placeholders})
                ON CONFLICT(cat_name, snapshot_hash) DO UPDATE SET last_seen = excluded.last_seen
                """,
                values,
            )
            self._conn.commit()
            inserted = self._conn.execute("SELECT changes()").fetchone()[0] > 0
            if inserted:
                log.info("Saved cat: '%s'", stats.cat_name)
            return inserted
        except sqlite3.Error:
            log.exception("Failed to save cat '%s'", stats.cat_name)
            return False

    def get_latest_cat(self) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM cats ORDER BY last_seen DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_all_cats(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM cats ORDER BY last_seen DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def count_cats(self) -> int:
        row = self._conn.execute("SELECT COUNT(DISTINCT cat_name) FROM cats").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()
