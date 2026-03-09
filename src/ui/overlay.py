from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import time
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QSettings, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.capture.screen_grab import ScreenGrabber
from src.capture.window_bind import WindowBinder
from src.data.db import SQLiteStore
from src.data.dedup import DuplicateGuard
from src.data.stat_parser import CatStats, parse_regions
from src.utils.config_loader import PROJECT_ROOT, AppConfig
from src.vision.ocr_engine import OCREngine
from src.vision.region_crop import RegionCropper
from src.vision.scene_detect import SceneDetector

log = logging.getLogger("mewgent.ui.overlay")

HOTKEY_ID_TOGGLE = 1
MOD_ALT = 0x0001
VK_M = 0x4D

LOGO_PATH = str(PROJECT_ROOT / "images" / "mewgent-logo.jpg")

FONT_MONO = "Consolas"
FONT_UI = "Segoe UI"
CLR_DIM = "#8C847C"
CLR_BG_DIM = "rgba(140,132,124,30)"


@dataclass
class DebugInfo:
    """Snapshot of pipeline debug state, emitted every tick."""
    scan_number: int = 0
    frame_skips: int = 0
    phash_dist: int = -1
    pipeline_state: str = "idle"
    raw_ocr: dict[str, str] | None = None
    last_action: str = ""


class HotkeyThread(QThread):
    """Listen for a global hotkey (Alt+M) even when the game has focus."""

    triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread_id: int | None = None

    def run(self) -> None:
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        if not user32.RegisterHotKey(None, HOTKEY_ID_TOGGLE, MOD_ALT, VK_M):
            log.warning("Failed to register Alt+M hotkey — may already be in use")
            return

        log.info("Global hotkey registered: Alt+M to toggle overlay")

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == HOTKEY_ID_TOGGLE:
                    self.triggered.emit()

        user32.UnregisterHotKey(None, HOTKEY_ID_TOGGLE)
        log.info("Global hotkey unregistered")

    def stop(self) -> None:
        """Post WM_QUIT to break the GetMessageW loop."""
        if self._thread_id is not None:
            WM_QUIT = 0x0012
            ctypes.windll.user32.PostThreadMessageW(
                self._thread_id, WM_QUIT, 0, 0,
            )


class CaptureWorker(QThread):
    """Background thread running the capture -> OCR -> dedup pipeline."""

    stats_ready = Signal(object)    # CatStats
    status_changed = Signal(str)    # status text
    debug_updated = Signal(object)  # DebugInfo

    def __init__(
        self,
        cfg: AppConfig,
        pipeline: tuple,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cfg = cfg
        (
            self._binder,
            self._grabber,
            self._detector,
            self._cropper,
            self._ocr,
            self._db,
            self._dedup,
        ) = pipeline
        self._running = True
        self._allowlists = {
            name: rdef.allowlist for name, rdef in cfg.regions.regions.items()
        }
        self._dbg = DebugInfo()

    def stop(self) -> None:
        self._running = False

    def _emit_debug(self, **overrides: Any) -> None:
        self._dbg.frame_skips = self._dedup.frame_skip_count
        self._dbg.phash_dist = self._dedup.last_phash_dist
        for k, v in overrides.items():
            setattr(self._dbg, k, v)
        self.debug_updated.emit(DebugInfo(
            scan_number=self._dbg.scan_number,
            frame_skips=self._dbg.frame_skips,
            phash_dist=self._dbg.phash_dist,
            pipeline_state=self._dbg.pipeline_state,
            raw_ocr=dict(self._dbg.raw_ocr) if self._dbg.raw_ocr else None,
            last_action=self._dbg.last_action,
        ))

    def run(self) -> None:
        interval = self._cfg.capture.interval_ms / 1000.0
        self.status_changed.emit("Waiting for game...")
        scan_count = 0

        while self._running:
            hwnd = self._binder.hwnd
            if hwnd is None:
                self._binder.find()
                if self._binder.hwnd is None:
                    self.status_changed.emit("Waiting for game...")
                    self._emit_debug(pipeline_state="waiting_for_game", last_action="no window")
                    time.sleep(2.0)
                    continue
                else:
                    self.status_changed.emit("Game found -- scanning")

            frame = self._grabber.capture_and_save_debug(self._binder.hwnd)
            if frame is None:
                log.debug("Capture returned None -- window may have closed")
                self._binder.find()
                self._emit_debug(pipeline_state="capture_failed", last_action="frame=None")
                time.sleep(interval)
                continue

            if self._dedup.is_same_frame(frame):
                self._emit_debug(pipeline_state="frame_dedup", last_action="same frame")
                time.sleep(interval)
                continue

            scan_count += 1
            self._dbg.scan_number = scan_count
            scene = self._detector.detect(frame)
            if scene != "cat_stats_screen":
                self.status_changed.emit("Scanning... (no cat screen)")
                self._emit_debug(pipeline_state="wrong_scene", last_action=f"scene={scene}")
                time.sleep(interval)
                continue

            self.status_changed.emit("Reading cat stats...")
            log.info("-- Scan #%d: new frame, running OCR --", scan_count)
            self._emit_debug(pipeline_state="ocr_running", last_action="OCR started")

            crops = self._cropper.crop_all(frame)
            ocr_results = self._ocr.recognise_regions(crops, self._allowlists)
            stats = parse_regions(ocr_results)
            self._dbg.raw_ocr = ocr_results

            if not stats.cat_name:
                log.info("  > Empty cat name -- skipping")
                self._emit_debug(pipeline_state="empty_name", last_action="no cat name")
                time.sleep(interval)
                continue

            if self._dedup.is_duplicate_stats(stats):
                log.info("  > Duplicate stats for '%s' -- skipping", stats.cat_name)
                self.status_changed.emit(f"Dup: {stats.cat_name}")
                self._emit_debug(pipeline_state="stat_dedup", last_action=f"dup: {stats.cat_name}")
                time.sleep(interval)
                continue

            snap_hash = self._dedup.snapshot_hash(stats)
            self._db.save_cat(stats, snap_hash)
            cat_count = self._db.count_cats()
            log.info("  > Saved '%s' (DB total: %d)", stats.cat_name, cat_count)

            self.stats_ready.emit(stats)
            self.status_changed.emit(f"Saved: {stats.cat_name}")
            self._emit_debug(pipeline_state="saved", last_action=f"saved: {stats.cat_name}")
            time.sleep(interval)

        self._db.close()


class MewgentOverlay(QMainWindow):
    """Always-on-top overlay showing the latest scanned cat stats."""

    def __init__(self, cfg: AppConfig, pipeline: tuple, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._db: SQLiteStore = pipeline[5]  # index 5 in the pipeline tuple

        self.setWindowTitle("Mewgent")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(380, 420)

        self._logo_icon = QIcon(LOGO_PATH)
        self.setWindowIcon(self._logo_icon)

        self._restore_geometry()
        self._build_ui()
        self._setup_tray()

        self._worker = CaptureWorker(cfg, pipeline, self)
        self._worker.stats_ready.connect(self._on_stats)
        self._worker.status_changed.connect(self._on_status)
        self._worker.debug_updated.connect(self._on_debug)
        self._worker.start()

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._force_topmost)
        self._topmost_timer.start(1000)
        self._force_topmost()

        self._hotkey_thread = HotkeyThread(self)
        self._hotkey_thread.triggered.connect(self._toggle_overlay)
        self._hotkey_thread.start()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet("""
            #central {
                background: rgba(26, 26, 26, 228);
                border: 2px solid #8C847C;
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Title bar row (draggable)
        title_row = QHBoxLayout()

        logo_label = QLabel()
        logo_pixmap = QPixmap(LOGO_PATH).scaled(
            22, 22,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logo_label.setPixmap(logo_pixmap)
        title_row.addWidget(logo_label)

        title_label = QLabel("Mewgent")
        title_label.setFont(QFont(FONT_UI, 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #B8A99A;")
        title_row.addWidget(title_label)
        title_row.addStretch()

        hotkey_hint = QLabel("Alt+M")
        hotkey_hint.setFont(QFont(FONT_MONO, 8))
        hotkey_hint.setStyleSheet(
            f"color: {CLR_DIM}; background: rgba(140,132,124,40); "
            "border-radius: 3px; padding: 1px 4px;"
        )
        title_row.addWidget(hotkey_hint)
        layout.addLayout(title_row)

        # Separator line
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {CLR_DIM};")
        layout.addWidget(sep)

        # Cat name
        self._name_label = QLabel("--")
        self._name_label.setFont(QFont(FONT_UI, 14, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #E5E0D8; margin-top: 4px;")
        layout.addWidget(self._name_label)

        # Stats grid
        self._stat_labels: dict[str, QLabel] = {}
        stat_names = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]

        stat_colors = {
            "STR": "#C24D4D",
            "DEX": "#D4AF37",
            "CON": "#C24D4D",
            "INT": "#5B7B8E",
            "SPD": "#D4AF37",
            "CHA": "#7A8B6C",
            "LCK": "#D4AF37",
        }

        row1 = QHBoxLayout()
        for s in stat_names[:3]:
            lbl = self._make_stat_label(s, "--", stat_colors.get(s, "#E5E0D8"))
            self._stat_labels[s] = lbl
            row1.addWidget(lbl)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        for s in stat_names[3:6]:
            lbl = self._make_stat_label(s, "--", stat_colors.get(s, "#E5E0D8"))
            self._stat_labels[s] = lbl
            row2.addWidget(lbl)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        lbl = self._make_stat_label(stat_names[6], "--", stat_colors.get("LCK", "#E5E0D8"))
        self._stat_labels[stat_names[6]] = lbl
        row3.addWidget(lbl)
        row3.addStretch()
        layout.addLayout(row3)

        # Separator
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: rgba(140,132,124,80);")
        layout.addWidget(sep2)

        # Status bar
        self._status_label = QLabel("Starting...")
        self._status_label.setFont(QFont(FONT_UI, 9))
        self._status_label.setStyleSheet(f"color: {CLR_DIM}; margin-top: 2px;")
        layout.addWidget(self._status_label)

        self._count_label = QLabel("Cats saved: 0")
        self._count_label.setFont(QFont(FONT_UI, 9))
        self._count_label.setStyleSheet(f"color: {CLR_DIM};")
        layout.addWidget(self._count_label)

        # ── Debug panel ──────────────────────────────────────────────
        self._build_debug_panel(layout)

    def _build_debug_panel(self, parent_layout: QVBoxLayout) -> None:
        sep3 = QLabel()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet(f"background: {CLR_DIM}; margin-top: 4px;")
        parent_layout.addWidget(sep3)

        debug_title = QLabel("DEBUG")
        debug_title.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        debug_title.setStyleSheet("color: #5B7B8E; margin-top: 2px;")
        parent_layout.addWidget(debug_title)

        dbg_style = f"color: #B8A99A; font-family: {FONT_MONO}; font-size: 9px;"

        # Pipeline state row
        r1 = QHBoxLayout()
        r1.setSpacing(8)
        self._dbg_state_label = QLabel("State: idle")
        self._dbg_state_label.setStyleSheet(dbg_style)
        r1.addWidget(self._dbg_state_label)
        r1.addStretch()
        self._dbg_scan_label = QLabel("Scan: 0")
        self._dbg_scan_label.setStyleSheet(dbg_style)
        r1.addWidget(self._dbg_scan_label)
        parent_layout.addLayout(r1)

        # Frame dedup row
        r2 = QHBoxLayout()
        r2.setSpacing(8)
        self._dbg_phash_label = QLabel("pHash dist: --")
        self._dbg_phash_label.setStyleSheet(dbg_style)
        r2.addWidget(self._dbg_phash_label)
        r2.addStretch()
        self._dbg_skips_label = QLabel("Frame skips: 0")
        self._dbg_skips_label.setStyleSheet(dbg_style)
        r2.addWidget(self._dbg_skips_label)
        parent_layout.addLayout(r2)

        # Last action
        self._dbg_action_label = QLabel("Action: --")
        self._dbg_action_label.setStyleSheet(dbg_style)
        parent_layout.addWidget(self._dbg_action_label)

        # Raw OCR section
        ocr_title = QLabel("Raw OCR:")
        ocr_title.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        ocr_title.setStyleSheet("color: #5B7B8E; margin-top: 4px;")
        parent_layout.addWidget(ocr_title)

        ocr_box = QWidget()
        ocr_box.setStyleSheet(
            f"background: {CLR_BG_DIM}; border-radius: 4px;"
        )
        self._ocr_grid = QVBoxLayout(ocr_box)
        self._ocr_grid.setContentsMargins(6, 4, 6, 4)
        self._ocr_grid.setSpacing(1)

        ocr_row_style = f"color: #E5E0D8; font-family: {FONT_MONO}; font-size: 8px;"
        ocr_key_style = f"color: {CLR_DIM}; font-family: {FONT_MONO}; font-size: 8px;"

        self._dbg_ocr_rows: dict[str, QLabel] = {}
        region_names = [
            "cat_name", "cat_age", "cat_level",
            "stat_str", "stat_dex", "stat_con",
            "stat_int", "stat_spd", "stat_cha", "stat_lck",
        ]
        for name in region_names:
            row = QHBoxLayout()
            row.setSpacing(4)
            key = QLabel(f"{name}:")
            key.setStyleSheet(ocr_key_style)
            key.setFixedWidth(70)
            row.addWidget(key)
            val = QLabel("--")
            val.setStyleSheet(ocr_row_style)
            row.addWidget(val)
            row.addStretch()
            self._dbg_ocr_rows[name] = val
            self._ocr_grid.addLayout(row)

        parent_layout.addWidget(ocr_box)

    @staticmethod
    def _make_stat_label(name: str, value: str, color: str = "#E5E0D8") -> QLabel:
        lbl = QLabel(f"{name}  {value}")
        lbl.setFont(QFont(FONT_MONO, 11))
        lbl.setStyleSheet(
            f"color: {color}; background: {CLR_BG_DIM}; "
            f"border-radius: 4px; padding: 2px 6px;"
        )
        lbl.setObjectName(f"stat_{name}")
        return lbl

    # ── System tray ──────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self._logo_icon, self)
        self._tray.setToolTip("Mewgent — Alt+M to toggle")

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

    # ── Force topmost (Win32 API) ──────────────────────────────────

    def _force_topmost(self) -> None:
        """Use Win32 SetWindowPos to keep overlay above fullscreen games."""
        if not self.isVisible():
            return
        try:
            hwnd = int(self.winId())
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except Exception:
            pass

    # ── Global hotkey toggle ────────────────────────────────────────

    def _toggle_overlay(self) -> None:
        """Toggle overlay visibility (called from Alt+M hotkey)."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self._force_topmost()

    # ── Slots ────────────────────────────────────────────────────────

    def _on_stats(self, stats: CatStats) -> None:
        self._name_label.setText(stats.cat_name or "—")
        mapping = {
            "STR": stats.stat_str, "DEX": stats.stat_dex, "CON": stats.stat_con,
            "INT": stats.stat_int, "SPD": stats.stat_spd, "CHA": stats.stat_cha,
            "LCK": stats.stat_lck,
        }
        for key, val in mapping.items():
            self._stat_labels[key].setText(f"{key}  {val}")

        self._count_label.setText(f"Cats saved: {self._db.count_cats()}")

    def _on_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _on_debug(self, info: DebugInfo) -> None:
        STATE_COLORS = {
            "saved": "#7A8B6C",
            "ocr_running": "#D4AF37",
            "frame_dedup": CLR_DIM,
            "stat_dedup": "#C24D4D",
            "waiting_for_game": "#C24D4D",
            "empty_name": "#C24D4D",
        }
        state_clr = STATE_COLORS.get(info.pipeline_state, "#B8A99A")
        self._dbg_state_label.setText(f"State: <span style='color:{state_clr}'>{info.pipeline_state}</span>")
        self._dbg_state_label.setTextFormat(Qt.TextFormat.RichText)
        self._dbg_scan_label.setText(f"Scan: {info.scan_number}")

        dist_str = str(info.phash_dist) if info.phash_dist >= 0 else "--"
        self._dbg_phash_label.setText(f"pHash dist: {dist_str}")
        self._dbg_skips_label.setText(f"Frame skips: {info.frame_skips}")

        self._dbg_action_label.setText(f"Action: {info.last_action}")

        if info.raw_ocr:
            for name, lbl in self._dbg_ocr_rows.items():
                val = info.raw_ocr.get(name, "")
                lbl.setText(f"'{val}'" if val else "--")

    # ── Window dragging (frameless) ──────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    # ── Geometry persistence ─────────────────────────────────────────

    def _restore_geometry(self) -> None:
        self._drag_pos = None
        settings = QSettings("Mewgent", "Overlay")
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(400, 480)
            self.move(100, 100)

    def closeEvent(self, event) -> None:
        settings = QSettings("Mewgent", "Overlay")
        settings.setValue("geometry", self.saveGeometry())
        self._worker.stop()
        self._worker.wait(3000)
        self._hotkey_thread.stop()
        self._hotkey_thread.wait(2000)
        self._topmost_timer.stop()
        event.accept()

    def _quit(self) -> None:
        self._worker.stop()
        self._worker.wait(3000)
        self._hotkey_thread.stop()
        self._hotkey_thread.wait(2000)
        self._topmost_timer.stop()
        QApplication.quit()
