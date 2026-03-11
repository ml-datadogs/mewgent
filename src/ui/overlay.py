from __future__ import annotations

import logging
import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QPointF, QSettings, QThread, QTimer, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.data.collars import COLLARS, compute_collar_scores
from src.data.stat_parser import CatStats, StatValue, STAT_NAMES
from src.utils.config_loader import PROJECT_ROOT, AppConfig

log = logging.getLogger("mewgent.ui.overlay")

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import ctypes
    import ctypes.wintypes

HOTKEY_ID_TOGGLE = 1
MOD_ALT = 0x0001
VK_M = 0x4D

LOGO_PATH = str(PROJECT_ROOT / "images" / "mewgent-logo.jpg")

if _IS_WIN:
    FONT_MONO = "Consolas"
    FONT_UI = "Georgia"
else:
    FONT_MONO = "Menlo"
    FONT_UI = "Georgia"

CLR_BG = "rgba(232, 223, 209, 245)"
CLR_BORDER = "#A89880"
CLR_DIM = "#9C8E7E"
CLR_TEXT = "#3B342D"
CLR_ACCENT = "#6B5D4F"
CLR_BG_DIM = "rgba(107, 93, 79, 25)"
CLR_BG_CARD = "rgba(255, 252, 245, 120)"

STAT_KEYS = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]
STAT_ATTRS = ["stat_str", "stat_dex", "stat_con", "stat_int", "stat_spd", "stat_cha", "stat_lck"]
STAT_COLORS = {
    "STR": "#A0523D",
    "DEX": "#B09840",
    "CON": "#A0523D",
    "INT": "#5A7A7D",
    "SPD": "#B09840",
    "CHA": "#6E8056",
    "LCK": "#B09840",
}

MAX_BAR_W = 140


@dataclass
class DebugInfo:
    """Snapshot of pipeline debug state, emitted every tick."""
    scan_number: int = 0
    frame_skips: int = 0
    phash_dist: int = -1
    pipeline_state: str = "idle"
    raw_ocr: dict[str, str] | None = None
    last_action: str = ""


# ── Radar chart widget ───────────────────────────────────────────────

class RadarChartWidget(QWidget):
    """QPainter-based 7-axis spider/radar chart for cat stats."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(280, 260)
        self._values: list[int] = [0] * 7
        self._max_val: int = 20

    def update_stats(self, stats: CatStats) -> None:
        self._values = [getattr(stats, a).total for a in STAT_ATTRS]
        self._max_val = max(max(self._values), 1)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 5
        radius = 75
        painter.setClipRect(self.rect())
        n = 7
        angle_step = 2 * math.pi / n
        start_angle = -math.pi / 2

        def vertex(i: int, r: float) -> QPointF:
            a = start_angle + i * angle_step
            return QPointF(cx + r * math.cos(a), cy + r * math.sin(a))

        grid_pen = QPen(QColor(107, 93, 79, 50), 1)
        painter.setPen(grid_pen)

        for frac in (0.25, 0.5, 0.75, 1.0):
            ring = QPolygonF([vertex(i, radius * frac) for i in range(n)])
            ring.append(ring[0])
            painter.drawPolyline(ring)

        for i in range(n):
            painter.drawLine(QPointF(cx, cy), vertex(i, radius))

        label_font = QFont(FONT_MONO, 8, QFont.Weight.Bold)
        painter.setFont(label_font)
        fm = QFontMetrics(label_font)

        for i, key in enumerate(STAT_KEYS):
            pt = vertex(i, radius + 18)
            val = self._values[i]
            text = f"{key} {val}"
            tw = fm.horizontalAdvance(text)
            th = fm.height()

            tx = pt.x() - tw / 2
            ty = pt.y()

            angle = start_angle + i * angle_step
            if angle > 0.1:
                ty += th
            elif angle > -0.1:
                ty += th / 2

            painter.setPen(QColor(STAT_COLORS.get(key, CLR_TEXT)))
            painter.drawText(QPointF(tx, ty), text)

        if any(v > 0 for v in self._values):
            points = QPolygonF()
            for i in range(n):
                frac = self._values[i] / self._max_val if self._max_val > 0 else 0
                points.append(vertex(i, radius * frac))
            points.append(points[0])

            fill_color = QColor(139, 115, 85, 70)
            stroke_color = QColor(107, 93, 79, 200)

            path = QPainterPath()
            path.addPolygon(points)
            painter.fillPath(path, QBrush(fill_color))
            painter.setPen(QPen(stroke_color, 1.5))
            painter.drawPolyline(points)

            dot_pen = QPen(Qt.PenStyle.NoPen)
            for i in range(n):
                frac = self._values[i] / self._max_val if self._max_val > 0 else 0
                pt = vertex(i, radius * frac)
                clr = QColor(STAT_COLORS.get(STAT_KEYS[i], CLR_TEXT))
                clr.setAlpha(220)
                painter.setPen(dot_pen)
                painter.setBrush(QBrush(clr))
                painter.drawEllipse(pt, 3, 3)

        painter.end()


# ── Win32-only hotkey thread ─────────────────────────────────────────

class HotkeyThread(QThread):
    """Listen for a global hotkey (Alt+M) even when the game has focus.

    Only functional on Windows; on other platforms ``start()`` is a no-op.
    """

    triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread_id: int | None = None

    def run(self) -> None:
        if not _IS_WIN:
            return

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
        if not _IS_WIN or self._thread_id is None:
            return
        WM_QUIT = 0x0012
        ctypes.windll.user32.PostThreadMessageW(
            self._thread_id, WM_QUIT, 0, 0,
        )


# ── Real capture worker ──────────────────────────────────────────────

class CaptureWorker(QThread):
    """Background thread running the capture -> OCR -> dedup pipeline."""

    stats_ready = Signal(object)
    status_changed = Signal(str)
    debug_updated = Signal(object)

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
        self._allowlists: dict[str, str] = {}
        for name, rdef in cfg.regions.regions.items():
            if rdef.is_stat_triple:
                for suffix in ("total", "base", "bonus"):
                    self._allowlists[f"{name}_{suffix}"] = rdef.allowlist
            else:
                self._allowlists[name] = rdef.allowlist
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

            from src.data.stat_parser import parse_regions
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


# ── Mock capture worker (dev-ui mode) ────────────────────────────────

def _sv(total: int) -> StatValue:
    return StatValue(total=total, base=total, bonus=0)


_SAMPLE_CATS = [
    CatStats(cat_name="Whiskers", stat_str=_sv(12), stat_dex=_sv(8), stat_con=_sv(15),
             stat_int=_sv(6), stat_spd=_sv(10), stat_cha=_sv(14), stat_lck=_sv(3)),
    CatStats(cat_name="Mittens", stat_str=_sv(6), stat_dex=_sv(18), stat_con=_sv(9),
             stat_int=_sv(14), stat_spd=_sv(16), stat_cha=_sv(5), stat_lck=_sv(11)),
    CatStats(cat_name="Chairman Meow", stat_str=_sv(20), stat_dex=_sv(4), stat_con=_sv(18),
             stat_int=_sv(20), stat_spd=_sv(2), stat_cha=_sv(20), stat_lck=_sv(7)),
    CatStats(cat_name="Purrlock Holmes", stat_str=_sv(8), stat_dex=_sv(12), stat_con=_sv(10),
             stat_int=_sv(19), stat_spd=_sv(11), stat_cha=_sv(9), stat_lck=_sv(15)),
    CatStats(cat_name="Catrick Swayze", stat_str=_sv(14), stat_dex=_sv(15), stat_con=_sv(12),
             stat_int=_sv(7), stat_spd=_sv(17), stat_cha=_sv(16), stat_lck=_sv(5)),
]


class MockCaptureWorker(QObject):
    """Timer-driven fake pipeline that emits sample data for UI development."""

    stats_ready = Signal(object)
    status_changed = Signal(str)
    debug_updated = Signal(object)

    def __init__(self, interval_ms: int = 2000, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._index = 0
        self._scan = 0
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self.status_changed.emit("DEV MODE — mock data active")
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def wait(self, _timeout_ms: int = 0) -> None:
        pass

    def _tick(self) -> None:
        cat = _SAMPLE_CATS[self._index % len(_SAMPLE_CATS)]
        self._index += 1
        self._scan += 1

        self.stats_ready.emit(cat)
        self.status_changed.emit(f"[mock] Saved: {cat.cat_name}")

        raw_ocr: dict[str, str] = {
            "cat_name": cat.cat_name,
            "cat_age": str(random.randint(1, 9)),
            "cat_level": str(random.randint(1, 50)),
        }
        for sn in STAT_NAMES:
            sv: StatValue = getattr(cat, f"stat_{sn}")
            raw_ocr[f"stat_{sn}_total"] = str(sv.total)
            raw_ocr[f"stat_{sn}_base"] = str(sv.base)
            raw_ocr[f"stat_{sn}_bonus"] = str(sv.bonus)

        self.debug_updated.emit(DebugInfo(
            scan_number=self._scan,
            frame_skips=random.randint(0, 5),
            phash_dist=random.randint(0, 20),
            pipeline_state="saved",
            raw_ocr=raw_ocr,
            last_action=f"mock: {cat.cat_name}",
        ))


# ── Helpers ──────────────────────────────────────────────────────────

def _make_separator() -> QLabel:
    sep = QLabel()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {CLR_BORDER}; margin-top: 2px; margin-bottom: 2px;")
    return sep


# ── Main overlay window ──────────────────────────────────────────────

class MewgentOverlay(QMainWindow):
    """Always-on-top overlay showing the latest scanned cat stats."""

    def __init__(
        self,
        cfg: AppConfig,
        pipeline: tuple,
        parent: QWidget | None = None,
        *,
        dev_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._dev_mode = dev_mode
        self._db = pipeline[5] if not dev_mode else None

        self.setWindowTitle("Mewgent" + (" [DEV]" if dev_mode else ""))
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(340, 720)

        self._logo_icon = QIcon(LOGO_PATH)
        self.setWindowIcon(self._logo_icon)

        self._restore_geometry()
        self._build_ui()
        self._setup_tray()

        if dev_mode:
            self._worker = MockCaptureWorker(interval_ms=2000, parent=self)
        else:
            self._worker = CaptureWorker(cfg, pipeline, self)
        self._worker.stats_ready.connect(self._on_stats)
        self._worker.status_changed.connect(self._on_status)
        self._worker.debug_updated.connect(self._on_debug)
        self._worker.start()

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._force_topmost)
        self._topmost_timer.start(1000)
        self._force_topmost()

        self._hotkey_thread: HotkeyThread | None = None
        if _IS_WIN and not dev_mode:
            self._hotkey_thread = HotkeyThread(self)
            self._hotkey_thread.triggered.connect(self._toggle_overlay)
            self._hotkey_thread.start()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(f"""
            #central {{
                background: {CLR_BG};
                border: 1px solid {CLR_BORDER};
                border-radius: 10px;
            }}
        """)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(6)

        self._build_title_bar(root)
        root.addWidget(_make_separator())
        self._build_cat_header(root)
        self._build_radar(root)
        self._build_collar_panel(root)
        root.addWidget(_make_separator())
        self._build_status_bar(root)
        root.addWidget(_make_separator())
        self._build_debug_panel(root)

    # ── Title bar ────────────────────────────────────────────────────

    def _build_title_bar(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(6)

        logo_label = QLabel()
        pix = QPixmap(LOGO_PATH)
        if not pix.isNull():
            logo_label.setPixmap(pix.scaled(
                20, 20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        row.addWidget(logo_label)

        title = QLabel("Mewgent")
        title.setFont(QFont(FONT_UI, 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {CLR_ACCENT};")
        row.addWidget(title)
        row.addStretch()

        if _IS_WIN:
            hotkey_hint = QLabel("Alt+M")
            hotkey_hint.setFont(QFont(FONT_MONO, 7))
            hotkey_hint.setStyleSheet(
                f"color: {CLR_DIM}; background: {CLR_BG_DIM}; "
                "border-radius: 3px; padding: 1px 5px;"
            )
            row.addWidget(hotkey_hint)

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(20, 20)
        close_btn.setFont(QFont(FONT_UI, 9))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {CLR_DIM}; background: transparent; border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                color: {CLR_TEXT}; background: rgba(0,0,0,15);
            }}
        """)
        close_btn.clicked.connect(self._quit)
        row.addWidget(close_btn)

        layout.addLayout(row)

    # ── Cat name ─────────────────────────────────────────────────────

    def _build_cat_header(self, layout: QVBoxLayout) -> None:
        self._name_label = QLabel("--")
        self._name_label.setFont(QFont(FONT_UI, 16, QFont.Weight.Bold))
        self._name_label.setStyleSheet(f"color: {CLR_TEXT};")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_label)

    # ── Radar chart ──────────────────────────────────────────────────

    def _build_radar(self, layout: QVBoxLayout) -> None:
        card = QWidget()
        card.setObjectName("radarCard")
        card.setStyleSheet(f"""
            #radarCard {{
                background: {CLR_BG_CARD};
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(8, 6, 8, 6)
        card_lay.setSpacing(0)

        self._radar = RadarChartWidget(card)
        inner = QHBoxLayout()
        inner.addStretch()
        inner.addWidget(self._radar)
        inner.addStretch()
        card_lay.addLayout(inner)

        layout.addWidget(card)

    # ── Collar suitability panel ─────────────────────────────────────

    def _build_collar_panel(self, layout: QVBoxLayout) -> None:
        card = QWidget()
        card.setObjectName("collarCard")
        card.setStyleSheet(f"""
            #collarCard {{
                background: {CLR_BG_CARD};
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(10, 8, 10, 8)
        card_lay.setSpacing(3)

        header = QLabel("COLLAR FIT")
        header.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {CLR_ACCENT}; margin-bottom: 2px;")
        card_lay.addWidget(header)

        self._collar_container = QVBoxLayout()
        self._collar_container.setSpacing(3)

        self._collar_rows: list[dict[str, Any]] = []
        for collar in COLLARS:
            row_widget = QWidget()
            row_widget.setStyleSheet("border-radius: 4px;")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 3, 6, 3)
            row_layout.setSpacing(6)

            dot = QLabel("\u25CF")
            dot.setFixedWidth(12)
            dot.setStyleSheet(f"color: {collar.color}; font-size: 10px;")
            row_layout.addWidget(dot)

            name_lbl = QLabel(collar.name)
            name_lbl.setFont(QFont(FONT_UI, 8))
            name_lbl.setStyleSheet(f"color: {CLR_TEXT};")
            name_lbl.setFixedWidth(85)
            row_layout.addWidget(name_lbl)

            bar_bg = QWidget()
            bar_bg.setFixedHeight(8)
            bar_bg.setFixedWidth(MAX_BAR_W)
            bar_bg.setStyleSheet(
                f"background: {CLR_BG_DIM}; border-radius: 4px;"
            )

            bar_fill = QWidget(bar_bg)
            bar_fill.setFixedHeight(8)
            bar_fill.setFixedWidth(0)
            bar_fill.setStyleSheet(
                f"background: {collar.color}; border-radius: 4px;"
            )

            row_layout.addWidget(bar_bg)

            score_lbl = QLabel("--")
            score_lbl.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
            score_lbl.setStyleSheet(f"color: {CLR_DIM};")
            score_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            score_lbl.setFixedWidth(38)
            row_layout.addWidget(score_lbl)

            self._collar_rows.append({
                "widget": row_widget,
                "dot": dot,
                "name": name_lbl,
                "bar_bg": bar_bg,
                "bar_fill": bar_fill,
                "score": score_lbl,
            })
            self._collar_container.addWidget(row_widget)

        card_lay.addLayout(self._collar_container)
        layout.addWidget(card)

    def _update_collar_scores(self, stats: CatStats) -> None:
        ranked = compute_collar_scores(stats)
        top_score = ranked[0][1] if ranked else 0

        for i, (collar, score) in enumerate(ranked):
            row = self._collar_rows[i]

            row["dot"].setStyleSheet(f"color: {collar.color}; font-size: 10px;")
            row["name"].setText(collar.name)
            row["score"].setText(f"{score:.1f}")

            frac = score / top_score if top_score > 0 else 0
            bar_w = max(int(frac * MAX_BAR_W), 2)
            row["bar_fill"].setFixedWidth(bar_w)
            row["bar_fill"].setStyleSheet(
                f"background: {collar.color}; border-radius: 4px;"
            )

            if score == top_score:
                row["name"].setStyleSheet(f"color: {CLR_TEXT}; font-weight: bold;")
                row["score"].setStyleSheet(f"color: {CLR_TEXT}; font-weight: bold;")
                row["widget"].setStyleSheet(
                    f"background: rgba(107, 93, 79, 20); border-radius: 4px;"
                )
            else:
                row["name"].setStyleSheet(f"color: {CLR_TEXT};")
                row["score"].setStyleSheet(f"color: {CLR_DIM};")
                row["widget"].setStyleSheet("border-radius: 4px;")

    # ── Status bar ───────────────────────────────────────────────────

    def _build_status_bar(self, layout: QVBoxLayout) -> None:
        self._status_label = QLabel("Starting...")
        self._status_label.setFont(QFont(FONT_UI, 8))
        self._status_label.setStyleSheet(f"color: {CLR_DIM};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

    # ── Collapsible debug panel ──────────────────────────────────────

    def _build_debug_panel(self, layout: QVBoxLayout) -> None:
        header_row = QHBoxLayout()
        header_row.setSpacing(4)

        self._debug_chevron = QLabel("\u25B6")
        self._debug_chevron.setFont(QFont(FONT_MONO, 9))
        self._debug_chevron.setStyleSheet(f"color: {CLR_DIM};")
        self._debug_chevron.setFixedWidth(14)
        header_row.addWidget(self._debug_chevron)

        debug_title = QLabel("DEBUG")
        debug_title.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        debug_title.setStyleSheet(f"color: {CLR_ACCENT};")
        header_row.addWidget(debug_title)
        header_row.addStretch()

        header_widget = QWidget()
        header_widget.setLayout(header_row)
        header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        header_widget.setStyleSheet("""
            QWidget { padding: 2px 0; }
            QWidget:hover { background: rgba(0,0,0,10); border-radius: 4px; }
        """)
        header_widget.mousePressEvent = lambda _e: self._toggle_debug()
        layout.addWidget(header_widget)

        self._debug_content = QWidget()
        dbg_layout = QVBoxLayout(self._debug_content)
        dbg_layout.setContentsMargins(0, 4, 0, 0)
        dbg_layout.setSpacing(4)

        dbg_style = f"color: {CLR_ACCENT}; font-family: {FONT_MONO}; font-size: 12px;"

        r1 = QHBoxLayout()
        r1.setSpacing(8)
        self._dbg_state_label = QLabel("State: idle")
        self._dbg_state_label.setStyleSheet(dbg_style)
        r1.addWidget(self._dbg_state_label)
        r1.addStretch()
        self._dbg_scan_label = QLabel("Scan: 0")
        self._dbg_scan_label.setStyleSheet(dbg_style)
        r1.addWidget(self._dbg_scan_label)
        dbg_layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(8)
        self._dbg_phash_label = QLabel("pHash dist: --")
        self._dbg_phash_label.setStyleSheet(dbg_style)
        r2.addWidget(self._dbg_phash_label)
        r2.addStretch()
        self._dbg_skips_label = QLabel("Frame skips: 0")
        self._dbg_skips_label.setStyleSheet(dbg_style)
        r2.addWidget(self._dbg_skips_label)
        dbg_layout.addLayout(r2)

        self._dbg_action_label = QLabel("Action: --")
        self._dbg_action_label.setStyleSheet(dbg_style)
        dbg_layout.addWidget(self._dbg_action_label)

        ocr_title = QLabel("Raw OCR:")
        ocr_title.setFont(QFont(FONT_MONO, 10, QFont.Weight.Bold))
        ocr_title.setStyleSheet(f"color: {CLR_ACCENT}; margin-top: 4px;")
        dbg_layout.addWidget(ocr_title)

        ocr_box = QWidget()
        ocr_box.setStyleSheet(
            f"background: {CLR_BG_DIM}; border-radius: 4px;"
        )
        ocr_grid = QVBoxLayout(ocr_box)
        ocr_grid.setContentsMargins(8, 6, 8, 6)
        ocr_grid.setSpacing(2)

        ocr_row_style = f"color: {CLR_TEXT}; font-family: {FONT_MONO}; font-size: 11px;"
        ocr_key_style = f"color: {CLR_DIM}; font-family: {FONT_MONO}; font-size: 11px;"

        self._dbg_ocr_rows: dict[str, QLabel] = {}
        region_names = ["cat_name", "cat_age", "cat_level"]
        for sn in STAT_NAMES:
            for suffix in ("total", "base", "bonus"):
                region_names.append(f"stat_{sn}_{suffix}")
        for name in region_names:
            row = QHBoxLayout()
            row.setSpacing(4)
            key = QLabel(f"{name}:")
            key.setStyleSheet(ocr_key_style)
            key.setFixedWidth(85)
            row.addWidget(key)
            val = QLabel("--")
            val.setStyleSheet(ocr_row_style)
            row.addWidget(val)
            row.addStretch()
            self._dbg_ocr_rows[name] = val
            ocr_grid.addLayout(row)

        dbg_layout.addWidget(ocr_box)
        layout.addWidget(self._debug_content)

        expanded = QSettings("Mewgent", "Overlay").value("debug_expanded", False, type=bool)
        self._debug_content.setVisible(expanded)
        self._debug_chevron.setText("\u25BC" if expanded else "\u25B6")

    def _toggle_debug(self) -> None:
        visible = not self._debug_content.isVisible()
        self._debug_content.setVisible(visible)
        self._debug_chevron.setText("\u25BC" if visible else "\u25B6")
        QSettings("Mewgent", "Overlay").setValue("debug_expanded", visible)

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

    # ── Force topmost ────────────────────────────────────────────────

    def _force_topmost(self) -> None:
        """Use Win32 SetWindowPos on Windows; Qt flags suffice elsewhere."""
        if not self.isVisible() or not _IS_WIN:
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
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self._force_topmost()

    # ── Slots ────────────────────────────────────────────────────────

    def _on_stats(self, stats: CatStats) -> None:
        self._name_label.setText(stats.cat_name or "\u2014")

        self._radar.update_stats(stats)
        self._update_collar_scores(stats)

        if self._db is not None:
            count = self._db.count_cats()
        else:
            count = self._worker._index if hasattr(self._worker, "_index") else "?"
        self._status_label.setText(f"Saved: {stats.cat_name}  \u2502  Cats: {count}")

    def _on_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _on_debug(self, info: DebugInfo) -> None:
        STATE_COLORS = {
            "saved": "#6E8056",
            "ocr_running": "#B09840",
            "frame_dedup": CLR_DIM,
            "stat_dedup": "#A0523D",
            "waiting_for_game": "#A0523D",
            "empty_name": "#A0523D",
        }
        state_clr = STATE_COLORS.get(info.pipeline_state, CLR_ACCENT)
        self._dbg_state_label.setText(
            f"State: <span style='color:{state_clr}'>{info.pipeline_state}</span>"
        )
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
            self.resize(360, 780)
            self.move(100, 100)

    def closeEvent(self, event) -> None:
        settings = QSettings("Mewgent", "Overlay")
        settings.setValue("geometry", self.saveGeometry())
        self._worker.stop()
        self._worker.wait(3000)
        if self._hotkey_thread is not None:
            self._hotkey_thread.stop()
            self._hotkey_thread.wait(2000)
        self._topmost_timer.stop()
        event.accept()

    def _quit(self) -> None:
        self._worker.stop()
        self._worker.wait(3000)
        if self._hotkey_thread is not None:
            self._hotkey_thread.stop()
            self._hotkey_thread.wait(2000)
        self._topmost_timer.stop()
        QApplication.quit()
