"""File watcher that polls a Mewgenics .sav file for changes.

Emits ``save_updated(SaveData)`` whenever the file is modified.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.data.save_reader import SaveData, read_save

log = logging.getLogger("mewgent.capture.save_watcher")


class SaveWatcher(QThread):
    """Background thread that monitors a .sav file and re-parses on change."""

    save_updated = Signal(object)

    def __init__(
        self,
        save_path: str | Path,
        poll_ms: int = 2000,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._path = Path(save_path)
        self._poll_s = poll_ms / 1000.0
        self._running = True
        self._last_mtime: float = 0.0

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self._read_and_emit()

        while self._running:
            time.sleep(self._poll_s)
            if not self._running:
                break
            try:
                mtime = os.path.getmtime(self._path)
            except OSError:
                continue
            if mtime != self._last_mtime:
                self._read_and_emit()

    def _read_and_emit(self) -> None:
        if not self._path.exists():
            log.warning("Save file not found: %s", self._path)
            return
        try:
            self._last_mtime = os.path.getmtime(self._path)
            data = read_save(self._path)
            self.save_updated.emit(data)
            log.info(
                "Save updated: %d cats (%d in house), day %d",
                len(data.cats), len(data.house_cats), data.current_day,
            )
        except Exception:
            log.exception("Failed to read save file %s", self._path)
