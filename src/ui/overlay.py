from __future__ import annotations

import logging
import time
from typing import Any

from PySide6.QtCore import QSettings, QThread, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon
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


class CaptureWorker(QThread):
    """Background thread running the capture -> OCR -> dedup pipeline."""

    stats_ready = Signal(object)   # CatStats
    status_changed = Signal(str)   # status text

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

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        interval = self._cfg.capture.interval_ms / 1000.0
        self.status_changed.emit("Waiting for game…")

        while self._running:
            hwnd = self._binder.hwnd
            if hwnd is None:
                self._binder.find()
                if self._binder.hwnd is None:
                    self.status_changed.emit("Waiting for game…")
                    time.sleep(2.0)
                    continue
                else:
                    self.status_changed.emit("Game found — scanning")

            frame = self._grabber.capture_and_save_debug(self._binder.hwnd)
            if frame is None:
                self._binder.find()
                time.sleep(interval)
                continue

            if self._dedup.is_same_frame(frame):
                time.sleep(interval)
                continue

            scene = self._detector.detect(frame)
            if scene != "cat_stats_screen":
                self.status_changed.emit("Scanning… (no cat screen)")
                time.sleep(interval)
                continue

            self.status_changed.emit("Reading cat stats…")
            crops = self._cropper.crop_all(frame)
            ocr_results = self._ocr.recognise_regions(crops, self._allowlists)
            stats = parse_regions(ocr_results)

            if not stats.cat_name:
                time.sleep(interval)
                continue

            if self._dedup.is_duplicate_stats(stats):
                time.sleep(interval)
                continue

            snap_hash = self._dedup.snapshot_hash(stats)
            self._db.save_cat(stats, snap_hash)

            self.stats_ready.emit(stats)
            self.status_changed.emit(f"Saved: {stats.cat_name}")
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
        self.setMinimumSize(320, 220)

        self._restore_geometry()
        self._build_ui()
        self._setup_tray()

        self._worker = CaptureWorker(cfg, pipeline, self)
        self._worker.stats_ready.connect(self._on_stats)
        self._worker.status_changed.connect(self._on_status)
        self._worker.start()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(
            "#central { background: rgba(30, 30, 30, 210); border-radius: 10px; }"
        )
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 10, 14, 10)

        # Title bar row (draggable)
        title_row = QHBoxLayout()
        title_label = QLabel("Mewgent")
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e0e0e0;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Cat name
        self._name_label = QLabel("—")
        self._name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #ffffff; margin-top: 4px;")
        layout.addWidget(self._name_label)

        # Stats grid
        self._stat_labels: dict[str, QLabel] = {}
        stat_names = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]

        row1 = QHBoxLayout()
        for s in stat_names[:3]:
            lbl = self._make_stat_label(s, "—")
            self._stat_labels[s] = lbl
            row1.addWidget(lbl)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        for s in stat_names[3:6]:
            lbl = self._make_stat_label(s, "—")
            self._stat_labels[s] = lbl
            row2.addWidget(lbl)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        lbl = self._make_stat_label(stat_names[6], "—")
        self._stat_labels[stat_names[6]] = lbl
        row3.addWidget(lbl)
        row3.addStretch()
        layout.addLayout(row3)

        # Status bar
        self._status_label = QLabel("Starting…")
        self._status_label.setFont(QFont("Segoe UI", 9))
        self._status_label.setStyleSheet("color: #999999; margin-top: 6px;")
        layout.addWidget(self._status_label)

        self._count_label = QLabel("Cats saved: 0")
        self._count_label.setFont(QFont("Segoe UI", 9))
        self._count_label.setStyleSheet("color: #999999;")
        layout.addWidget(self._count_label)

    @staticmethod
    def _make_stat_label(name: str, value: str) -> QLabel:
        lbl = QLabel(f"{name}  {value}")
        lbl.setFont(QFont("Consolas", 11))
        lbl.setStyleSheet("color: #cccccc;")
        return lbl

    # ── System tray ──────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("Mewgent")

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
            self.resize(320, 220)
            self.move(100, 100)

    def closeEvent(self, event) -> None:
        settings = QSettings("Mewgent", "Overlay")
        settings.setValue("geometry", self.saveGeometry())
        self._worker.stop()
        self._worker.wait(3000)
        event.accept()

    def _quit(self) -> None:
        self._worker.stop()
        self._worker.wait(3000)
        QApplication.quit()
