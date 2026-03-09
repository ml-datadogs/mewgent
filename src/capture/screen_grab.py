from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import numpy as np
import win32gui
import win32ui

log = logging.getLogger("mewgent.capture.screen_grab")

PW_CLIENTONLY = 1


class ScreenGrabber:
    """Capture the client area of a window via PrintWindow (win32).

    Works even when the target window is partially obscured.
    """

    def __init__(self, debug_dir: str | None = None) -> None:
        self._debug_dir = Path(debug_dir) if debug_dir else None
        if self._debug_dir:
            self._debug_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, hwnd: int) -> np.ndarray | None:
        """Return a BGR numpy array of the window's client area, or None on failure."""
        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            w = right - left
            h = bottom - top
            if w <= 0 or h <= 0:
                log.warning("Invalid client rect: %dx%d", w, h)
                return None

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)

            result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_CLIENTONLY)
            if result == 0:
                log.warning("PrintWindow returned 0 — capture may be blank")

            bmp_info = bitmap.GetInfo()
            bmp_bits = bitmap.GetBitmapBits(True)

            img = np.frombuffer(bmp_bits, dtype=np.uint8).reshape(
                bmp_info["bmHeight"], bmp_info["bmWidth"], 4
            )
            # BGRA -> BGR (drop alpha)
            img = img[:, :, :3].copy()

            # Cleanup GDI resources
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            win32gui.DeleteObject(bitmap.GetHandle())

            log.debug("Captured frame: %dx%d", w, h)
            return img

        except Exception:
            log.exception("Screen capture failed")
            return None

    def capture_and_save_debug(self, hwnd: int) -> np.ndarray | None:
        """Capture a frame and optionally save a debug screenshot."""
        frame = self.capture(hwnd)
        if frame is not None and self._debug_dir is not None:
            self._save_debug(frame)
        return frame

    def _save_debug(self, frame: np.ndarray) -> None:
        import cv2

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self._debug_dir / f"frame_{ts}.png"
        cv2.imwrite(str(path), frame)
        log.debug("Debug screenshot saved: %s", path)
