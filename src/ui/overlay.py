from __future__ import annotations

import math
import logging
import sys
from typing import Any

from PySide6.QtCore import QPointF, QRectF, QSettings, QThread, QTimer, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.data.collars import (
    COLLARS,
    CollarDef,
    collar_by_name,
    collar_score,
    save_cat_to_stats,
    unlocked_collars,
)
from src.data.save_reader import SaveCat, SaveData
from src.llm.advisor import LLMAdvisor
from src.utils.config_loader import PROJECT_ROOT, AppConfig

log = logging.getLogger("mewgent.ui.overlay")

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import ctypes
    import ctypes.wintypes

HOTKEY_ID_TOGGLE = 1
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000
VK_M = 0x4D

LOGO_PATH = str(PROJECT_ROOT / "images" / "mewgent-logo.jpg")
CHAR_DIR = PROJECT_ROOT / "images" / "characteristics"

if _IS_WIN:
    FONT_MONO = "Consolas"
    FONT_UI = "Georgia"
else:
    FONT_MONO = "Menlo"
    FONT_UI = "Georgia"

# ── Warm paper palette (matches Mewgenics torn-paper UI) ─────────────
CLR_BG = "#DDD4C4"
CLR_BORDER = "#B8AD9C"
CLR_DIM = "#8A7D6D"
CLR_TEXT = "#2D2926"
CLR_ACCENT = "#C17070"
CLR_BG_DIM = "rgba(0, 0, 0, 12)"
CLR_BG_CARD = "rgba(255, 252, 245, 200)"
CLR_HIGHLIGHT = "rgba(110, 128, 86, 35)"
CLR_SELECTED = "rgba(110, 128, 86, 20)"
CLR_BEST = "#5E7A3A"

STAT_COLORS: dict[str, str] = {
    "str": "#C13128",
    "dex": "#E8A524",
    "con": "#3B7A57",
    "int": "#4A90E2",
    "spd": "#D4A017",
    "cha": "#C17070",
    "lck": "#5E7A3A",
}

STAT_ICON_FILES: dict[str, str] = {
    "str": "Stat_Strength.png",
    "dex": "Stat_Dexterity.png",
    "con": "Stat_Constitution.png",
    "int": "Stat_Intelligence.png",
    "spd": "Stat_Speed.png",
    "cha": "Stat_Charisma.png",
    "lck": "Stat_Luck.png",
}

STAT_ORDER = ["str", "dex", "con", "int", "spd", "cha", "lck"]
STAT_LABELS = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]


def _load_stat_icons(size: int = 14) -> dict[str, QPixmap]:
    """Load stat icons as black silhouettes (perfect on paper background)."""
    icons: dict[str, QPixmap] = {}
    for stat_key, filename in STAT_ICON_FILES.items():
        path = CHAR_DIR / filename
        pix = QPixmap(str(path))
        if pix.isNull():
            continue
        icons[stat_key] = pix.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return icons


CLASS_ICON_DIR = PROJECT_ROOT / "wiki_data" / "images" / "classes"

CLASS_ICON_FILES: dict[str, str] = {
    "Collarless": "Collarless_Icon.png",
    "Fighter": "Fighter_Icon.png",
    "Hunter": "Hunter_Icon.png",
    "Mage": "Mage_Icon.png",
    "Tank": "Tank_Icon.png",
    "Cleric": "Cleric_Icon.png",
    "Thief": "Thief_Icon.png",
    "Necromancer": "Necromancer_Icon.png",
    "Tinkerer": "Tinkerer_Icon.png",
    "Butcher": "Butcher_Icon.png",
    "Druid": "Druid_Icon.png",
    "Psychic": "Psychic_Icon.png",
    "Monk": "Monk_Icon.png",
    "Jester": "Jester_Icon.png",
}


def _load_class_icons(size: int = 18) -> dict[str, QPixmap]:
    icons: dict[str, QPixmap] = {}
    for collar_name, filename in CLASS_ICON_FILES.items():
        path = CLASS_ICON_DIR / filename
        pix = QPixmap(str(path))
        if pix.isNull():
            continue
        icons[collar_name] = pix.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return icons


# ── Win32-only hotkey thread ─────────────────────────────────────────


class HotkeyThread(QThread):
    triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread_id: int | None = None

    def run(self) -> None:
        if not _IS_WIN:
            return
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(
            None, HOTKEY_ID_TOGGLE, MOD_ALT | MOD_NOREPEAT, VK_M
        ):
            log.warning("Failed to register Alt+M hotkey")
            return
        log.info("Global hotkey registered: Alt+M")
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312 and msg.wParam == HOTKEY_ID_TOGGLE:
                self.triggered.emit()
        user32.UnregisterHotKey(None, HOTKEY_ID_TOGGLE)

    def stop(self) -> None:
        if not _IS_WIN or self._thread_id is None:
            return
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_separator() -> QLabel:
    sep = QLabel()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {CLR_BORDER}; margin-top: 2px; margin-bottom: 2px;")
    return sep


def _detach(widget: QWidget | None) -> None:
    """Immediately detach a widget from its parent/layout then schedule deletion."""
    if widget is None:
        return
    widget.setParent(None)
    widget.deleteLater()


# ── Radar chart widget ───────────────────────────────────────────────


class RadarChartWidget(QWidget):
    """Heptagonal spider/radar chart for 7 stats.

    Accepts either a SaveCat or raw stat values list.
    Optionally draws a min/max range polygon behind the data.
    """

    def __init__(
        self,
        cat: SaveCat | None = None,
        size: int = 140,
        show_labels: bool = True,
        values: list[float] | None = None,
        range_min: list[float] | None = None,
        range_max: list[float] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if values is not None:
            self._values = values
        elif cat is not None:
            self._values = [float(getattr(cat, f"base_{s}", 0)) for s in STAT_ORDER]
        else:
            self._values = [0.0] * 7
        self._range_min = range_min
        self._range_max = range_max
        self._show_labels = show_labels
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2
        margin = 22 if self._show_labels else 6
        radius = min(w, h) / 2 - margin
        n = 7
        max_stat = 10.0

        angle_offset = -math.pi / 2

        def _point(idx: int, r: float) -> QPointF:
            a = angle_offset + (2 * math.pi * idx / n)
            return QPointF(cx + r * math.cos(a), cy + r * math.sin(a))

        for frac in (0.25, 0.50, 0.75, 1.0):
            ring = QPolygonF([_point(i, radius * frac) for i in range(n)])
            ring.append(ring[0])
            pen_color = QColor(CLR_BORDER)
            pen_color.setAlpha(80 if frac < 1.0 else 140)
            p.setPen(QPen(pen_color, 0.5 if frac < 1.0 else 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolygon(ring)

        for i in range(n):
            pt = _point(i, radius)
            pen_color = QColor(CLR_BORDER)
            pen_color.setAlpha(50)
            p.setPen(QPen(pen_color, 0.5))
            p.drawLine(QPointF(cx, cy), pt)

        # Range polygon (min/max band)
        if self._range_min and self._range_max:
            range_poly = QPolygonF()
            for i in range(n):
                r = (min(self._range_max[i], max_stat) / max_stat) * radius
                range_poly.append(_point(i, max(r, radius * 0.03)))
            range_poly.append(range_poly[0])
            fill = QColor("#B8AD9C")
            fill.setAlpha(40)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor("#B8AD9C"), 0.5))
            p.drawPolygon(range_poly)

            min_poly = QPolygonF()
            for i in range(n):
                r = (min(self._range_min[i], max_stat) / max_stat) * radius
                min_poly.append(_point(i, max(r, radius * 0.03)))
            min_poly.append(min_poly[0])
            erase = QColor(CLR_BG)
            erase.setAlpha(180)
            p.setBrush(QBrush(erase))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(min_poly)

        # Data polygon
        data_pts = QPolygonF()
        for i, val in enumerate(self._values):
            r = (min(val, max_stat) / max_stat) * radius
            data_pts.append(_point(i, max(r, radius * 0.03)))
        data_pts.append(data_pts[0])

        fill_color = QColor("#5E7A3A")
        fill_color.setAlpha(50)
        p.setBrush(QBrush(fill_color))
        p.setPen(QPen(QColor("#5E7A3A"), 1.5))
        p.drawPolygon(data_pts)

        for i, val in enumerate(self._values):
            r = (min(val, max_stat) / max_stat) * radius
            pt = _point(i, max(r, radius * 0.03))
            dot_color = QColor(STAT_COLORS[STAT_ORDER[i]])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot_color)
            p.drawEllipse(pt, 3, 3)

        if self._show_labels:
            font = QFont(FONT_MONO, 7, QFont.Weight.Bold)
            p.setFont(font)
            fm = QFontMetrics(font)
            for i, val in enumerate(self._values):
                lbl_pt = _point(i, radius + 12)
                label = STAT_LABELS[i]
                tw = fm.horizontalAdvance(label)
                th = fm.height()
                color = (
                    QColor(STAT_COLORS[STAT_ORDER[i]]) if val >= 7 else QColor(CLR_DIM)
                )
                p.setPen(color)
                p.drawText(
                    QRectF(lbl_pt.x() - tw / 2, lbl_pt.y() - th / 2, tw, th),
                    Qt.AlignmentFlag.AlignCenter,
                    label,
                )

        p.end()


# ── Stat Distribution chart (page 1) ────────────────────────────────


class StatDistributionWidget(QWidget):
    """Horizontal stacked bars showing low/mid/high cat counts per stat."""

    def __init__(
        self,
        cats: list[SaveCat],
        icons: dict[str, QPixmap],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cats = cats
        self._icons = icons
        self.setMinimumHeight(max(160, 24 * 7 + 20))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        total_cats = len(self._cats)
        if total_cats == 0:
            p.setPen(QColor(CLR_DIM))
            p.setFont(QFont(FONT_UI, 9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No cats")
            p.end()
            return

        bar_h = 16
        gap = 6
        label_w = 50
        count_w = 60
        bar_area = w - label_w - count_w - 10
        y = 8

        for idx, stat_key in enumerate(STAT_ORDER):
            low = mid = high = 0
            for cat in self._cats:
                val = getattr(cat, f"base_{stat_key}", 0)
                if val <= 3:
                    low += 1
                elif val <= 6:
                    mid += 1
                else:
                    high += 1

            base_color = QColor(STAT_COLORS[stat_key])

            # Icon + label
            icon_x = 4
            icon = self._icons.get(stat_key)
            if icon:
                p.drawPixmap(icon_x, int(y + (bar_h - 14) / 2), icon)
                icon_x += 18

            p.setPen(QColor(CLR_TEXT))
            p.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
            p.drawText(
                QRectF(icon_x, y, label_w - icon_x, bar_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                stat_key.upper(),
            )

            # Stacked bar
            bx = label_w
            for count, alpha in [(low, 60), (mid, 120), (high, 220)]:
                if count == 0:
                    continue
                seg_w = max(1, int((count / total_cats) * bar_area))
                c = QColor(base_color)
                c.setAlpha(alpha)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(QRectF(bx, y + 1, seg_w, bar_h - 2), 3, 3)
                bx += seg_w

            # Counts text
            p.setPen(QColor(CLR_DIM))
            p.setFont(QFont(FONT_MONO, 7))
            p.drawText(
                QRectF(w - count_w - 4, y, count_w, bar_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                f"{low}L  {mid}M  {high}H",
            )

            y += bar_h + gap

        p.end()


# ── Class Fit chart (page 2) ────────────────────────────────────────


class ClassFitWidget(QWidget):
    """Horizontal stacked bars showing good/ok/poor cat counts per class."""

    def __init__(
        self,
        cats: list[SaveCat],
        collars: list[CollarDef],
        class_icons: dict[str, QPixmap] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cats = cats
        self._collars = collars
        self._class_icons = class_icons or {}
        self.setMinimumHeight(max(120, 24 * len(collars) + 20))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        total_cats = len(self._cats)
        if total_cats == 0:
            p.setPen(QColor(CLR_DIM))
            p.setFont(QFont(FONT_UI, 9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No cats")
            p.end()
            return

        bar_h = 16
        gap = 6
        label_w = 74
        count_w = 60
        bar_area = w - label_w - count_w - 10
        y = 8

        for collar in self._collars:
            good = ok = poor = 0
            for cat in self._cats:
                cs = save_cat_to_stats(cat)
                sc = collar_score(collar, cs)
                if sc >= 7.0:
                    good += 1
                elif sc >= 5.0:
                    ok += 1
                else:
                    poor += 1

            base_color = QColor(collar.color)

            icon_x = 4
            icon = self._class_icons.get(collar.name)
            if icon:
                p.drawPixmap(
                    icon_x,
                    int(y + (bar_h - 14) / 2),
                    icon.scaled(
                        14,
                        14,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )
                icon_x += 18

            p.setPen(base_color)
            p.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
            p.drawText(
                QRectF(icon_x, y, label_w - icon_x, bar_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                collar.name[:6],
            )

            bx = label_w
            for count, alpha in [(poor, 50), (ok, 120), (good, 220)]:
                if count == 0:
                    continue
                seg_w = max(1, int((count / total_cats) * bar_area))
                c = QColor(base_color)
                c.setAlpha(alpha)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(QRectF(bx, y + 1, seg_w, bar_h - 2), 3, 3)
                bx += seg_w

            p.setPen(QColor(CLR_DIM))
            p.setFont(QFont(FONT_MONO, 7))
            p.drawText(
                QRectF(w - count_w - 4, y, count_w, bar_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                f"{good}G  {ok}O  {poor}P",
            )

            y += bar_h + gap

        p.end()


# ── LLM worker threads ──────────────────────────────────────────────


class _LLMTeamWorker(QThread):
    """Run LLM team suggestion off the main thread."""

    finished = Signal(object)  # list[dict] | None

    def __init__(
        self,
        advisor: LLMAdvisor,
        cats: list[SaveCat],
        collars: list[CollarDef],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._advisor = advisor
        self._cats = cats
        self._collars = collars

    def run(self) -> None:
        base_scores: dict[int, list[tuple[CollarDef, float]]] = {}
        for cat in self._cats:
            cs = save_cat_to_stats(cat)
            base_scores[cat.db_key] = [(c, collar_score(c, cs)) for c in self._collars]
        result = self._advisor.suggest_team_composition(
            self._cats,
            self._collars,
            base_scores,
        )
        self.finished.emit(result)


class _LLMExplainWorker(QThread):
    """Run LLM explanation off the main thread."""

    finished = Signal(int, str, str)  # slot_idx, collar_name, explanation

    def __init__(
        self,
        advisor: LLMAdvisor,
        cat: SaveCat,
        collar: CollarDef,
        score: float,
        slot_idx: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._advisor = advisor
        self._cat = cat
        self._collar = collar
        self._score = score
        self._slot_idx = slot_idx

    def run(self) -> None:
        explanation = self._advisor.explain_recommendation(
            self._cat,
            self._collar,
            self._score,
        )
        self.finished.emit(
            self._slot_idx,
            self._collar.name,
            explanation or "",
        )


# ── Main overlay window ──────────────────────────────────────────────


class MewgentOverlay(QMainWindow):
    """Always-on-top overlay for team building from save file data."""

    def __init__(
        self,
        cfg: AppConfig,
        pipeline: tuple,
        parent: QWidget | None = None,
        *,
        dev_mode: bool = False,
        save_watcher=None,
    ) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._dev_mode = dev_mode
        self._save_watcher = save_watcher
        self._save_data: SaveData | None = None
        self._house_cats: list[SaveCat] = []
        self._available_collars: list[CollarDef] = list(COLLARS)
        self._team_slots: list[dict | None] = [None, None, None, None]
        self._stat_icons = _load_stat_icons(14)
        self._class_icons = _load_class_icons(18)

        self._llm = LLMAdvisor(
            model=cfg.llm.model,
            enabled=cfg.llm.enabled,
            mock=cfg.llm.mock,
        )
        self._llm_worker: _LLMTeamWorker | None = None
        self._llm_explain_workers: list[_LLMExplainWorker] = []

        self._viable_cats: list[tuple[SaveCat, list[float], int, float]] = []
        self._overview_page: int = 0

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

        self._restore_geometry()
        self._build_ui()
        self._setup_tray()

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._force_topmost)
        self._topmost_timer.start(1000)
        self._force_topmost()

        self._hotkey_thread: HotkeyThread | None = None
        if _IS_WIN and not dev_mode:
            self._hotkey_thread = HotkeyThread(self)
            self._hotkey_thread.triggered.connect(self._toggle_overlay)
            self._hotkey_thread.start()

        if self._save_watcher is not None:
            self._save_watcher.save_updated.connect(self._on_save_updated)
            self._save_watcher.start()

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
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)

        self._build_title_bar(root)
        root.addWidget(_make_separator())
        self._build_team_panel(root)
        root.addWidget(_make_separator())
        self._build_overview_section(root)
        root.addWidget(_make_separator())
        self._build_status_bar(root)

    # ── Title bar ────────────────────────────────────────────────────

    def _build_title_bar(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(6)

        logo_label = QLabel()
        pix = QPixmap(LOGO_PATH)
        if not pix.isNull():
            logo_label.setPixmap(
                pix.scaled(
                    20,
                    20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        row.addWidget(logo_label)

        title = QLabel("Mewgent")
        title.setFont(QFont(FONT_UI, 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {CLR_ACCENT};")
        row.addWidget(title)
        row.addStretch()

        self._info_label = QLabel("")
        self._info_label.setFont(QFont(FONT_MONO, 7))
        self._info_label.setStyleSheet(f"color: {CLR_DIM};")
        row.addWidget(self._info_label)

        if _IS_WIN:
            hotkey_hint = QLabel("Ctrl+Shift+M")
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
                color: {CLR_TEXT}; background: rgba(0,0,0,10);
            }}
        """)
        close_btn.clicked.connect(self._quit)
        row.addWidget(close_btn)
        layout.addLayout(row)

    # ── Team panel (4 slots + buttons) ───────────────────────────────

    def _build_team_panel(self, layout: QVBoxLayout) -> None:
        card = QWidget()
        card.setObjectName("teamCard")
        card.setStyleSheet(f"""
            #teamCard {{
                background: {CLR_BG_CARD};
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(10, 8, 10, 8)
        card_lay.setSpacing(4)

        header_row = QHBoxLayout()
        team_lbl = QLabel("TEAM")
        team_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        team_lbl.setStyleSheet(f"color: {CLR_ACCENT};")
        header_row.addWidget(team_lbl)
        header_row.addStretch()

        self._tb_team_score_label = QLabel("Score: --")
        self._tb_team_score_label.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        self._tb_team_score_label.setStyleSheet(f"color: {CLR_ACCENT};")
        header_row.addWidget(self._tb_team_score_label)
        card_lay.addLayout(header_row)

        self._team_slot_widgets: list[dict[str, Any]] = []
        for i in range(4):
            slot_w = QWidget()
            slot_w.setObjectName(f"teamSlot{i}")
            slot_w.setStyleSheet(f"""
                #teamSlot{i} {{
                    border-radius: 4px;
                    border-left: 3px solid transparent;
                }}
            """)
            slot_lay = QHBoxLayout(slot_w)
            slot_lay.setContentsMargins(8, 3, 6, 3)
            slot_lay.setSpacing(6)

            slot_num = QLabel(f"{i + 1}.")
            slot_num.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
            slot_num.setStyleSheet(f"color: {CLR_DIM};")
            slot_num.setFixedWidth(18)
            slot_lay.addWidget(slot_num)

            radar_placeholder = QWidget()
            radar_placeholder.setFixedSize(0, 0)
            slot_lay.addWidget(radar_placeholder)

            slot_name = QLabel("(empty)")
            slot_name.setFont(QFont(FONT_UI, 9))
            slot_name.setStyleSheet(f"color: {CLR_DIM};")
            slot_name.setMinimumWidth(80)
            slot_lay.addWidget(slot_name)
            slot_lay.addStretch()

            slot_class_combo = QComboBox()
            slot_class_combo.setFont(QFont(FONT_MONO, 8))
            slot_class_combo.setFixedWidth(105)
            slot_class_combo.setFixedHeight(22)
            slot_class_combo.setStyleSheet(f"""
                QComboBox {{
                    background: {CLR_BG_DIM};
                    color: {CLR_TEXT};
                    border: 1px solid {CLR_BORDER};
                    border-radius: 3px;
                    padding: 0 6px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 16px;
                }}
                QComboBox QAbstractItemView {{
                    background: {CLR_BG};
                    color: {CLR_TEXT};
                    border: 1px solid {CLR_BORDER};
                    selection-background-color: {CLR_BG_DIM};
                }}
            """)
            slot_class_combo.setVisible(False)
            slot_lay.addWidget(slot_class_combo)

            slot_score = QLabel("")
            slot_score.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
            slot_score.setStyleSheet(f"color: {CLR_ACCENT};")
            slot_score.setFixedWidth(36)
            slot_score.setAlignment(Qt.AlignmentFlag.AlignRight)
            slot_lay.addWidget(slot_score)

            remove_btn = QPushButton("\u2715")
            remove_btn.setFixedSize(18, 18)
            remove_btn.setFont(QFont(FONT_UI, 8))
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {CLR_DIM}; background: transparent; border: none;
                    border-radius: 9px;
                }}
                QPushButton:hover {{
                    color: {CLR_TEXT}; background: rgba(0,0,0,10);
                }}
            """)
            remove_btn.setVisible(False)
            slot_idx = i
            remove_btn.clicked.connect(
                lambda _checked=False, idx=slot_idx: self._remove_team_slot(idx)
            )
            slot_lay.addWidget(remove_btn)

            self._team_slot_widgets.append(
                {
                    "widget": slot_w,
                    "name": slot_name,
                    "combo": slot_class_combo,
                    "score": slot_score,
                    "remove": remove_btn,
                    "radar": radar_placeholder,
                    "layout": slot_lay,
                }
            )
            card_lay.addWidget(slot_w)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._autofill_btn = QPushButton("Auto-fill best team")
        self._autofill_btn.setFont(QFont(FONT_UI, 8))
        self._autofill_btn.setFixedHeight(26)
        self._autofill_btn.setStyleSheet(f"""
            QPushButton {{
                color: {CLR_TEXT}; background: {CLR_BG_DIM};
                border: 1px solid {CLR_BORDER}; border-radius: 4px;
                padding: 2px 14px;
            }}
            QPushButton:hover {{ background: rgba(0, 0, 0, 18); }}
        """)
        self._autofill_btn.clicked.connect(self._autofill_team)
        btn_row.addWidget(self._autofill_btn)

        self._ai_team_btn = QPushButton("AI Team")
        self._ai_team_btn.setFont(QFont(FONT_UI, 8))
        self._ai_team_btn.setFixedHeight(26)
        self._ai_team_btn.setStyleSheet(f"""
            QPushButton {{
                color: {CLR_TEXT}; background: {CLR_BG_DIM};
                border: 1px solid {CLR_BORDER}; border-radius: 4px;
                padding: 2px 10px;
            }}
            QPushButton:hover {{ background: rgba(0, 0, 0, 18); }}
            QPushButton:disabled {{ color: {CLR_DIM}; }}
        """)
        self._ai_team_btn.clicked.connect(self._autofill_team_llm)
        self._ai_team_btn.setVisible(self._llm.available)
        btn_row.addWidget(self._ai_team_btn)

        self._llm_status_label = QLabel("")
        self._llm_status_label.setFont(QFont(FONT_UI, 7))
        self._llm_status_label.setStyleSheet(f"color: {CLR_DIM};")
        btn_row.addWidget(self._llm_status_label)

        clear_btn = QPushButton("Clear")
        clear_btn.setFont(QFont(FONT_UI, 8))
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: {CLR_DIM}; background: transparent;
                border: 1px solid {CLR_BORDER}; border-radius: 4px;
                padding: 2px 10px;
            }}
            QPushButton:hover {{ color: {CLR_TEXT}; background: rgba(0,0,0,8); }}
        """)
        clear_btn.clicked.connect(self._clear_team)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        card_lay.addLayout(btn_row)

        layout.addWidget(card)

    # ── Overview section (4 chart pages) ─────────────────────────────

    _TAB_NAMES = ["Stats", "Classes", "Top 3", "Avg"]

    def _build_overview_section(self, layout: QVBoxLayout) -> None:
        header = QHBoxLayout()
        header.setSpacing(6)

        overview_lbl = QLabel("ROSTER OVERVIEW")
        overview_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        overview_lbl.setStyleSheet(f"color: {CLR_ACCENT};")
        header.addWidget(overview_lbl)
        header.addStretch()

        self._tab_buttons: list[QPushButton] = []
        for idx, name in enumerate(self._TAB_NAMES):
            btn = QPushButton(name)
            btn.setFont(QFont(FONT_MONO, 8))
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_idx = idx
            btn.clicked.connect(
                lambda _c=False, i=tab_idx: self._switch_overview_page(i)
            )
            self._tab_buttons.append(btn)
            header.addWidget(btn)

        layout.addLayout(header)
        self._update_tab_styles()

        card = QWidget()
        card.setObjectName("overviewCard")
        card.setStyleSheet(f"""
            #overviewCard {{
                background: {CLR_BG_CARD};
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
        """)
        self._overview_card_layout = QVBoxLayout(card)
        self._overview_card_layout.setContentsMargins(10, 8, 10, 8)
        self._overview_card_layout.setSpacing(0)

        self._overview_content: QWidget | None = None
        self._overview_placeholder = QLabel("Save data not loaded yet")
        self._overview_placeholder.setFont(QFont(FONT_UI, 9))
        self._overview_placeholder.setStyleSheet(f"color: {CLR_DIM};")
        self._overview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overview_placeholder.setMinimumHeight(160)
        self._overview_card_layout.addWidget(self._overview_placeholder)

        layout.addWidget(card, 1)

    def _update_tab_styles(self) -> None:
        for i, btn in enumerate(self._tab_buttons):
            if i == self._overview_page:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {CLR_TEXT}; background: {CLR_HIGHLIGHT};
                        border: 1px solid {CLR_BORDER}; border-radius: 4px;
                        padding: 2px 8px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {CLR_DIM}; background: transparent;
                        border: 1px solid {CLR_BORDER}; border-radius: 4px;
                        padding: 2px 8px;
                    }}
                    QPushButton:hover {{ color: {CLR_TEXT}; background: rgba(0,0,0,6); }}
                """)

    def _switch_overview_page(self, page: int) -> None:
        self._overview_page = page
        self._update_tab_styles()
        self._render_overview_page()

    def _render_overview_page(self) -> None:
        if self._overview_content is not None:
            self._overview_card_layout.removeWidget(self._overview_content)
            _detach(self._overview_content)
            self._overview_content = None
        if self._overview_placeholder is not None:
            self._overview_card_layout.removeWidget(self._overview_placeholder)
            _detach(self._overview_placeholder)
            self._overview_placeholder = None

        cats = [c for c, *_ in self._viable_cats]
        if not cats:
            placeholder = QLabel("No viable cats loaded")
            placeholder.setFont(QFont(FONT_UI, 9))
            placeholder.setStyleSheet(f"color: {CLR_DIM};")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setMinimumHeight(160)
            self._overview_content = placeholder
            self._overview_card_layout.addWidget(placeholder)
            return

        page = self._overview_page
        if page == 0:
            widget = StatDistributionWidget(cats, self._stat_icons)
        elif page == 1:
            widget = ClassFitWidget(cats, self._available_collars, self._class_icons)
        elif page == 2:
            widget = self._build_top3_page(cats)
        elif page == 3:
            widget = self._build_avg_radar_page(cats)
        else:
            widget = QLabel("Unknown page")

        self._overview_content = widget
        self._overview_card_layout.addWidget(widget)

    # ── Page 3: Top 3 per class ──────────────────────────────────────

    def _build_top3_page(self, cats: list[SaveCat]) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(160)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                width: 6px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {CLR_DIM}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        container = QWidget()
        container_lay = QVBoxLayout(container)
        container_lay.setContentsMargins(0, 0, 0, 0)
        container_lay.setSpacing(8)

        for collar in self._available_collars:
            scored: list[tuple[SaveCat, float]] = []
            for cat in cats:
                cs = save_cat_to_stats(cat)
                sc = collar_score(collar, cs)
                scored.append((cat, sc))
            scored.sort(key=lambda x: x[1], reverse=True)
            top3 = scored[:3]

            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(8)

            icon_pix = self._class_icons.get(collar.name)
            if icon_pix:
                icon_lbl = QLabel()
                icon_lbl.setPixmap(
                    icon_pix.scaled(
                        16,
                        16,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                icon_lbl.setFixedSize(16, 16)
                row_lay.addWidget(icon_lbl)

            class_lbl = QLabel(collar.name[:6])
            class_lbl.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
            class_lbl.setStyleSheet(f"color: {collar.color};")
            class_lbl.setFixedWidth(52)
            row_lay.addWidget(class_lbl)

            for cat, sc in top3:
                entry = QWidget()
                entry_lay = QHBoxLayout(entry)
                entry_lay.setContentsMargins(4, 2, 4, 2)
                entry_lay.setSpacing(4)

                radar = RadarChartWidget(cat=cat, size=40, show_labels=False)
                entry_lay.addWidget(radar)

                info_lay = QVBoxLayout()
                info_lay.setSpacing(0)
                info_lay.setContentsMargins(0, 0, 0, 0)

                name_btn = QPushButton(cat.name[:12])
                name_btn.setFont(QFont(FONT_UI, 8))
                name_btn.setFixedHeight(18)
                name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                name_btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {CLR_TEXT}; background: transparent;
                        border: none; padding: 0; text-align: left;
                    }}
                    QPushButton:hover {{ color: {collar.color}; }}
                """)
                cat_ref = cat
                collar_ref = collar
                sc_ref = sc
                name_btn.clicked.connect(
                    lambda _c=False, ca=cat_ref, co=collar_ref, s=sc_ref: (
                        self._add_to_team(ca, co, s)
                    )
                )
                info_lay.addWidget(name_btn)

                score_lbl = QLabel(f"{sc:.1f}")
                score_lbl.setFont(QFont(FONT_MONO, 7, QFont.Weight.Bold))
                score_lbl.setStyleSheet(f"color: {collar.color};")
                info_lay.addWidget(score_lbl)

                entry_lay.addLayout(info_lay)
                row_lay.addWidget(entry)

            row_lay.addStretch()
            container_lay.addWidget(row_w)

        container_lay.addStretch()
        scroll.setWidget(container)
        return scroll

    # ── Page 4: Average roster radar ─────────────────────────────────

    def _build_avg_radar_page(self, cats: list[SaveCat]) -> QWidget:
        n = len(cats)
        avg_vals = []
        min_vals = []
        max_vals = []
        for stat_key in STAT_ORDER:
            vals = [getattr(c, f"base_{stat_key}", 0) for c in cats]
            avg_vals.append(sum(vals) / n if n else 0)
            min_vals.append(min(vals) if vals else 0)
            max_vals.append(max(vals) if vals else 0)

        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.setSpacing(6)

        title = QLabel(f"Average Stats ({n} cats)")
        title.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {CLR_DIM};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_lay.addWidget(title)

        radar_row = QHBoxLayout()
        radar_row.addStretch()
        radar = RadarChartWidget(
            values=avg_vals,
            range_min=min_vals,
            range_max=max_vals,
            size=200,
            show_labels=True,
        )
        radar_row.addWidget(radar)
        radar_row.addStretch()
        page_lay.addLayout(radar_row)

        # Stat summary labels
        summary_row = QHBoxLayout()
        summary_row.setSpacing(4)
        summary_row.addStretch()
        for i, stat_key in enumerate(STAT_ORDER):
            lbl = QLabel(f"{STAT_LABELS[i]} {avg_vals[i]:.1f}")
            lbl.setFont(QFont(FONT_MONO, 7))
            color = STAT_COLORS[stat_key] if avg_vals[i] >= 5.5 else CLR_DIM
            lbl.setStyleSheet(f"color: {color};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            summary_row.addWidget(lbl)
        summary_row.addStretch()
        page_lay.addLayout(summary_row)

        page_lay.addStretch()
        return page

    # ── Status bar ───────────────────────────────────────────────────

    def _build_status_bar(self, layout: QVBoxLayout) -> None:
        self._status_label = QLabel("Waiting for save data...")
        self._status_label.setFont(QFont(FONT_UI, 8))
        self._status_label.setStyleSheet(f"color: {CLR_DIM};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

    # ── System tray ──────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self._logo_icon, self)
        self._tray.setToolTip("Mewgent \u2014 Ctrl+Shift+M to toggle")

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

    # ── Save data handling ───────────────────────────────────────────

    def _on_save_updated(self, save_data: SaveData) -> None:
        self._save_data = save_data
        self._house_cats = save_data.house_cats
        self._available_collars = unlocked_collars(save_data.unlocked_classes)
        if not self._available_collars:
            self._available_collars = list(COLLARS)
        self._llm.clear_cache()

        self._info_label.setText(
            f"Day {save_data.current_day} \u2502 {len(self._house_cats)} cats"
        )

        collar_names = [c.name for c in self._available_collars]
        for sw in self._team_slot_widgets:
            combo: QComboBox = sw["combo"]
            combo.blockSignals(True)
            combo.clear()
            for cname in collar_names:
                icon_pix = self._class_icons.get(cname)
                if icon_pix:
                    combo.addItem(QIcon(icon_pix), cname)
                else:
                    combo.addItem(cname)
            combo.blockSignals(False)

        self._rebuild_viable_cats()
        self._refresh_team_scores()

        self._status_label.setText(
            f"Save loaded: {len(save_data.cats)} total cats "
            f"({len(self._house_cats)} in house)"
        )

    # ── Viable cats computation ──────────────────────────────────────

    def _rebuild_viable_cats(self) -> None:
        collars = self._available_collars
        self._viable_cats = []
        for cat in self._house_cats:
            if cat.age == 0 and all(
                getattr(cat, f"base_{s}") == 0
                for s in ("str", "dex", "con", "int", "spd", "cha", "lck")
            ):
                continue
            cs = save_cat_to_stats(cat)
            scores = [collar_score(c, cs) for c in collars]
            best_idx = max(range(len(scores)), key=lambda k: scores[k])
            self._viable_cats.append((cat, scores, best_idx, scores[best_idx]))

        self._viable_cats.sort(key=lambda x: x[3], reverse=True)
        self._render_overview_page()

    # ── Team slot management ─────────────────────────────────────────

    def _add_to_team(self, cat: SaveCat, collar: CollarDef, score: float) -> None:
        for slot in self._team_slots:
            if slot is not None and slot["cat"].db_key == cat.db_key:
                return
        for i, slot in enumerate(self._team_slots):
            if slot is None:
                self._team_slots[i] = {
                    "cat": cat,
                    "collar": collar,
                    "score": score,
                }
                self._refresh_team_ui()
                return

    def _remove_team_slot(self, idx: int) -> None:
        self._team_slots[idx] = None
        self._refresh_team_ui()

    def _clear_team(self) -> None:
        self._team_slots = [None, None, None, None]
        self._refresh_team_ui()

    def _refresh_team_ui(self) -> None:
        total_score = 0.0
        for i, slot in enumerate(self._team_slots):
            sw = self._team_slot_widgets[i]
            obj_name = f"teamSlot{i}"

            old_radar = sw.get("radar")
            if old_radar is not None:
                sw["layout"].removeWidget(old_radar)
                _detach(old_radar)

            if slot is None:
                sw["name"].setText("(empty)")
                sw["name"].setStyleSheet(f"color: {CLR_DIM};")
                sw["score"].setText("")
                sw["combo"].setVisible(False)
                sw["remove"].setVisible(False)
                sw["widget"].setStyleSheet(f"""
                    #{obj_name} {{
                        border-radius: 4px;
                        border-left: 3px solid transparent;
                    }}
                """)
                placeholder = QWidget()
                placeholder.setFixedSize(0, 0)
                sw["layout"].insertWidget(1, placeholder)
                sw["radar"] = placeholder
            else:
                cat = slot["cat"]
                collar = slot["collar"]
                score = slot["score"]
                sw["name"].setText(cat.name)
                sw["name"].setStyleSheet(f"color: {CLR_TEXT}; font-weight: bold;")
                sw["score"].setText(f"{score:.1f}")
                sw["combo"].setVisible(True)
                sw["remove"].setVisible(True)
                sw["widget"].setStyleSheet(f"""
                    #{obj_name} {{
                        background: {CLR_HIGHLIGHT};
                        border-radius: 4px;
                        border-left: 3px solid {collar.color};
                    }}
                """)

                radar = RadarChartWidget(cat=cat, size=48, show_labels=False)
                sw["layout"].insertWidget(1, radar)
                sw["radar"] = radar

                combo: QComboBox = sw["combo"]
                combo.blockSignals(True)
                for j in range(combo.count()):
                    if combo.itemText(j) == collar.name:
                        combo.setCurrentIndex(j)
                        break
                combo.blockSignals(False)

                combo.blockSignals(True)
                try:
                    combo.currentTextChanged.disconnect()
                except RuntimeError:
                    pass
                combo.blockSignals(False)
                slot_idx = i
                combo.currentTextChanged.connect(
                    lambda text, idx=slot_idx: self._on_slot_class_changed(idx, text)
                )
                total_score += score

        self._tb_team_score_label.setText(
            f"Score: {total_score:.1f}" if total_score > 0 else "Score: --"
        )
        self._request_explanations()

    def _refresh_team_scores(self) -> None:
        for slot in self._team_slots:
            if slot is not None:
                cs = save_cat_to_stats(slot["cat"])
                slot["score"] = collar_score(slot["collar"], cs)
        self._refresh_team_ui()

    def _on_slot_class_changed(self, slot_idx: int, collar_name: str) -> None:
        slot = self._team_slots[slot_idx]
        if slot is None:
            return
        c = collar_by_name(collar_name)
        if c is None:
            return
        cs = save_cat_to_stats(slot["cat"])
        slot["collar"] = c
        slot["score"] = collar_score(c, cs)
        self._refresh_team_ui()

    def _autofill_team(self) -> None:
        if not self._house_cats or not self._available_collars:
            return

        self._team_slots = [None, None, None, None]
        available_cats = [c for c in self._house_cats if c.age > 1]
        used_cat_keys: set[int] = set()
        used_collar_names: set[str] = set()

        for slot_idx in range(4):
            best_pick = None
            best_score = -999.0
            for cat in available_cats:
                if cat.db_key in used_cat_keys:
                    continue
                cs = save_cat_to_stats(cat)
                for c in self._available_collars:
                    if c.name in used_collar_names:
                        continue
                    s = collar_score(c, cs)
                    if s > best_score:
                        best_score = s
                        best_pick = (cat, c, s)
            if best_pick is None:
                break
            cat, collar, score = best_pick
            self._team_slots[slot_idx] = {
                "cat": cat,
                "collar": collar,
                "score": score,
            }
            used_cat_keys.add(cat.db_key)
            used_collar_names.add(collar.name)

        self._refresh_team_ui()

    # ── LLM-powered team building ────────────────────────────────────

    def _autofill_team_llm(self) -> None:
        """Use LLM to suggest a balanced team composition."""
        if (
            not self._llm.available
            or not self._house_cats
            or not self._available_collars
        ):
            self._autofill_team()
            return

        available_cats = [c for c in self._house_cats if c.age > 1]
        if len(available_cats) < 2:
            self._autofill_team()
            return

        self._ai_team_btn.setEnabled(False)
        self._llm_status_label.setText("AI thinking...")

        self._llm_worker = _LLMTeamWorker(
            self._llm,
            available_cats,
            self._available_collars,
            self,
        )
        self._llm_worker.finished.connect(self._on_llm_team_result)
        self._llm_worker.start()

    def _on_llm_team_result(self, result: list[dict] | None) -> None:
        self._ai_team_btn.setEnabled(True)
        self._llm_status_label.setText("")

        if not result:
            self._autofill_team()
            return

        self._team_slots = [None, None, None, None]
        cat_by_key = {c.db_key: c for c in self._house_cats}

        for slot_idx, entry in enumerate(result[:4]):
            db_key = entry.get("cat_db_key")
            collar_name = entry.get("collar_name", "")
            cat = cat_by_key.get(db_key)
            collar = collar_by_name(collar_name)
            if cat is None or collar is None:
                continue
            if cat.age <= 1:
                continue
            cs = save_cat_to_stats(cat)
            score = collar_score(collar, cs)
            self._team_slots[slot_idx] = {
                "cat": cat,
                "collar": collar,
                "score": score,
            }

        self._refresh_team_ui()

    def _request_explanations(self) -> None:
        """Request LLM explanations for each filled team slot."""
        if not self._llm.available:
            return

        for worker in self._llm_explain_workers:
            if worker.isRunning():
                worker.quit()
        self._llm_explain_workers.clear()

        for i, slot in enumerate(self._team_slots):
            if slot is None:
                continue
            cat = slot["cat"]
            collar = slot["collar"]
            score = slot["score"]

            cached = self._llm._explanation_cache.get(f"{cat.db_key}:{collar.name}")
            if cached:
                sw = self._team_slot_widgets[i]
                sw["widget"].setToolTip(cached)
                continue

            worker = _LLMExplainWorker(
                self._llm,
                cat,
                collar,
                score,
                i,
                self,
            )
            worker.finished.connect(self._on_explanation_result)
            self._llm_explain_workers.append(worker)
            worker.start()

    def _on_explanation_result(
        self, slot_idx: int, collar_name: str, explanation: str
    ) -> None:
        if slot_idx < len(self._team_slot_widgets) and explanation:
            slot = self._team_slots[slot_idx]
            if slot is not None and slot["collar"].name == collar_name:
                self._team_slot_widgets[slot_idx]["widget"].setToolTip(explanation)

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
            self.show()
            self._force_topmost()

    # ── Window dragging ──────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
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
