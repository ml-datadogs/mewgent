"""Slim PyQt shell that hosts a QWebEngineView rendering the React UI.

Handles only OS-level concerns: window flags, always-on-top, transparency,
system tray, global hotkey, and drag-to-move. All UI rendering is delegated
to the React app loaded in the embedded Chromium view.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QSettings, QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.ui.bridge import OverlayBridge
from src.utils.config_loader import PROJECT_ROOT, AppConfig

log = logging.getLogger("mewgent.ui.overlay_shell")

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import ctypes
    import ctypes.wintypes

HOTKEY_ID_TOGGLE = 1
SW_SHOWNOACTIVATE = 4

# Win32 modifier flags for RegisterHotKey
_MOD_MAP: dict[str, int] = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "shift": 0x0004,
    "win": 0x0008,
}
_MOD_NOREPEAT = 0x4000

# Win32 virtual-key codes for A-Z and 0-9
_VK_MAP: dict[str, int] = {chr(c): c for c in range(0x30, 0x3A)}  # 0-9
_VK_MAP.update({chr(c): c for c in range(0x41, 0x5B)})  # A-Z


def _parse_hotkey(combo: str) -> tuple[int, int, str]:
    """Parse a string like 'Ctrl+Shift+M' into (modifiers, vk, label)."""
    parts = [p.strip().lower() for p in combo.split("+")]
    mods = _MOD_NOREPEAT
    key_label_parts: list[str] = []
    vk = 0
    for part in parts:
        if part in _MOD_MAP:
            mods |= _MOD_MAP[part]
            key_label_parts.append(part.capitalize())
        else:
            upper = part.upper()
            if upper in _VK_MAP:
                vk = _VK_MAP[upper]
                key_label_parts.append(upper)
            else:
                log.warning("Unknown key in hotkey combo: %r", part)
    label = "+".join(key_label_parts)
    return mods, vk, label


LOGO_PATH = str(PROJECT_ROOT / "images" / "mewgent-logo.jpg")
UI_DIST = PROJECT_ROOT / "ui" / "dist"
UI_INDEX = UI_DIST / "index.html"


class HotkeyThread(QThread):
    """Win32 global hotkey listener (configurable combo)."""

    triggered = Signal()

    def __init__(self, modifiers: int, vk: int, label: str, parent=None):
        super().__init__(parent)
        self._modifiers = modifiers
        self._vk = vk
        self._label = label
        self._thread_id: int | None = None

    def run(self) -> None:
        if not _IS_WIN:
            return
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, HOTKEY_ID_TOGGLE, self._modifiers, self._vk):
            log.warning("Failed to register %s hotkey", self._label)
            return
        log.info("Global hotkey registered: %s", self._label)
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312 and msg.wParam == HOTKEY_ID_TOGGLE:
                self.triggered.emit()
        user32.UnregisterHotKey(None, HOTKEY_ID_TOGGLE)

    def stop(self) -> None:
        if not _IS_WIN or self._thread_id is None:
            return
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)


class OverlayShell(QMainWindow):
    """Frameless always-on-top window hosting a QWebEngineView."""

    def __init__(
        self,
        cfg: AppConfig,
        bridge: OverlayBridge,
        parent: QWidget | None = None,
        *,
        dev_mode: bool = False,
        save_watcher=None,
    ) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._bridge = bridge
        self._dev_mode = dev_mode
        self._save_watcher = save_watcher

        self.setWindowTitle("Mewgent" + (" [DEV]" if dev_mode else ""))
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(460, 560)

        self._logo_icon = QIcon(LOGO_PATH)
        self.setWindowIcon(self._logo_icon)

        self._build_webview()
        self._restore_geometry()
        self._hotkey_label = cfg.hotkey.toggle
        self._setup_tray()
        self._bridge.set_shell(self)

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._force_topmost)
        self._topmost_timer.start(1000)
        self._force_topmost()

        self._hotkey_thread: HotkeyThread | None = None
        if _IS_WIN and not dev_mode:
            mods, vk, label = _parse_hotkey(cfg.hotkey.toggle)
            self._hotkey_label = label
            self._tray.setToolTip(f"Mewgent \u2014 {label} to toggle")
            self._hotkey_thread = HotkeyThread(mods, vk, label, self)
            self._hotkey_thread.triggered.connect(self._toggle_overlay)
            self._hotkey_thread.start()

        if self._save_watcher is not None:
            self._save_watcher.save_updated.connect(self._bridge.on_save_updated)
            self._save_watcher.start()

    def _build_webview(self) -> None:
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._web_view = QWebEngineView()
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        self._web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))

        channel = QWebChannel(self._web_view.page())
        channel.registerObject("bridge", self._bridge)
        self._web_view.page().setWebChannel(channel)

        if self._dev_mode:
            url = QUrl("http://localhost:5173")
            log.info("Dev mode: loading React UI from Vite: %s", url.toString())
        elif UI_INDEX.exists():
            url = QUrl.fromLocalFile(str(UI_INDEX))
            log.info("Loading React UI from: %s", url.toString())
        else:
            url = QUrl("http://localhost:5173")
            log.info("UI dist not found, loading dev server: %s", url.toString())

        self._web_view.setUrl(url)
        layout.addWidget(self._web_view)

    # ── System tray ──────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self._logo_icon, self)
        self._tray.setToolTip(f"Mewgent — {self._hotkey_label} to toggle")

        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.setVisible(not self.isVisible())

    # ── Window chrome ────────────────────────────────────────────────

    def _force_topmost(self) -> None:
        if not self.isVisible() or not _IS_WIN:
            return
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                -1,
                0,
                0,
                0,
                0,
                0x0002 | 0x0001 | 0x0010,
            )
        except Exception:
            pass

    def _toggle_overlay(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            if _IS_WIN:
                hwnd = int(self.winId())
                ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
                self.setVisible(True)
            else:
                self.show()
            self._force_topmost()

    # ── Geometry persistence ─────────────────────────────────────────

    def _restore_geometry(self) -> None:
        settings = QSettings("Mewgent", "Overlay")
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(480, 720)
            self.move(100, 100)

    def closeEvent(self, event) -> None:
        settings = QSettings("Mewgent", "Overlay")
        settings.setValue("geometry", self.saveGeometry())
        if self._save_watcher is not None:
            self._save_watcher.stop()
            self._save_watcher.wait(3000)
        if self._hotkey_thread is not None:
            self._hotkey_thread.stop()
            self._hotkey_thread.wait(2000)
        self._topmost_timer.stop()
        event.accept()

    def _quit(self) -> None:
        if self._save_watcher is not None:
            self._save_watcher.stop()
            self._save_watcher.wait(3000)
        if self._hotkey_thread is not None:
            self._hotkey_thread.stop()
            self._hotkey_thread.wait(2000)
        self._topmost_timer.stop()
        QApplication.quit()
