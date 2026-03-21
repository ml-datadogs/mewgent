"""Background version checker that fetches a remote version.json."""

from __future__ import annotations

import logging

import httpx
from PySide6.QtCore import QThread, Signal

from src.version import __version__

log = logging.getLogger("mewgent.update_checker")


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.lstrip("v").split("."))


class UpdateCheckerThread(QThread):
    """Fetch a remote ``version.json`` and emit if a newer version exists."""

    update_found = Signal(str, str, str)

    def __init__(self, check_url: str, parent=None) -> None:
        super().__init__(parent)
        self._url = check_url

    def run(self) -> None:
        if not self._url:
            return
        try:
            resp = httpx.get(self._url, timeout=5, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            latest = data.get("latest", "")
            url = data.get("url", "")
            changelog = data.get("changelog", "")
            if latest and _parse_version(latest) > _parse_version(__version__):
                log.info("Update available: %s -> %s", __version__, latest)
                self.update_found.emit(latest, url, changelog)
            else:
                log.debug("Up to date (%s)", __version__)
        except Exception:
            log.debug("Update check failed (non-critical)", exc_info=True)
