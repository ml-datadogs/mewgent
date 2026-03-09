from __future__ import annotations

import ctypes
import logging
import time

import win32gui

log = logging.getLogger("mewgent.capture.window_bind")


def _set_dpi_aware() -> None:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        log.debug("SetProcessDPIAware failed — may already be set")


class WindowBinder:
    """Locate and track the Mewgenics game window by title substring."""

    def __init__(self, title: str = "Mewgenics", dpi_aware: bool = True) -> None:
        self._title = title
        self._hwnd: int | None = None
        if dpi_aware:
            _set_dpi_aware()

    @property
    def hwnd(self) -> int | None:
        return self._hwnd

    def find(self) -> int | None:
        """Search for the window and return its HWND, or None."""
        found: list[int] = []

        def _cb(hwnd: int, _extra: object) -> bool:
            if win32gui.IsWindowVisible(hwnd):
                text = win32gui.GetWindowText(hwnd)
                if self._title.lower() in text.lower():
                    found.append(hwnd)
            return True

        win32gui.EnumWindows(_cb, None)

        if found:
            self._hwnd = found[0]
            log.info("Window found: hwnd=%s  title='%s'", hex(self._hwnd), win32gui.GetWindowText(self._hwnd))
        else:
            self._hwnd = None
            log.debug("Window '%s' not found", self._title)

        return self._hwnd

    def get_rect(self) -> tuple[int, int, int, int] | None:
        """Return (left, top, right, bottom) of the window client area."""
        if self._hwnd is None:
            return None
        try:
            return win32gui.GetWindowRect(self._hwnd)
        except Exception:
            log.warning("GetWindowRect failed — window may have closed")
            self._hwnd = None
            return None

    def get_client_size(self) -> tuple[int, int] | None:
        """Return (width, height) of the client area."""
        rect = self.get_rect()
        if rect is None:
            return None
        left, top, right, bottom = rect
        return (right - left, bottom - top)

    def wait_for_window(self, poll_interval: float = 2.0, timeout: float = 0.0) -> int | None:
        """Block until the window appears.  timeout=0 means wait forever."""
        start = time.monotonic()
        while True:
            hwnd = self.find()
            if hwnd is not None:
                return hwnd
            if timeout > 0 and (time.monotonic() - start) >= timeout:
                return None
            log.info("Waiting for '%s' window…", self._title)
            time.sleep(poll_interval)
