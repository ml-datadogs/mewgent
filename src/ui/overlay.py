from __future__ import annotations

import logging
import sys
from typing import Any

from PySide6.QtCore import QSettings, QThread, QTimer, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
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
CLR_HIGHLIGHT = "rgba(110, 128, 86, 35)"
CLR_SELECTED = "rgba(107, 93, 79, 40)"
CLR_BEST = "#6E8056"


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
        if not user32.RegisterHotKey(None, HOTKEY_ID_TOGGLE, MOD_ALT, VK_M):
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


def _score_cell(value: float, is_best: bool, collar_color: str) -> QLabel:
    """Create a score label for the scoring table."""
    lbl = QLabel(f"{value:.1f}")
    lbl.setFont(QFont(FONT_MONO, 8))
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if is_best:
        lbl.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {collar_color}; font-weight: bold;")
    else:
        lbl.setStyleSheet(f"color: {CLR_DIM};")
    return lbl


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

        self.setWindowTitle("Mewgent" + (" [DEV]" if dev_mode else ""))
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(520, 400)

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
        self._build_scoring_table(root)
        root.addWidget(_make_separator())
        self._build_status_bar(root)

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

        self._info_label = QLabel("")
        self._info_label.setFont(QFont(FONT_MONO, 7))
        self._info_label.setStyleSheet(f"color: {CLR_DIM};")
        row.addWidget(self._info_label)

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
            slot_w.setStyleSheet("border-radius: 4px;")
            slot_lay = QHBoxLayout(slot_w)
            slot_lay.setContentsMargins(6, 4, 6, 4)
            slot_lay.setSpacing(6)

            slot_num = QLabel(f"{i + 1}.")
            slot_num.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
            slot_num.setStyleSheet(f"color: {CLR_DIM};")
            slot_num.setFixedWidth(18)
            slot_lay.addWidget(slot_num)

            slot_name = QLabel("(empty)")
            slot_name.setFont(QFont(FONT_UI, 9))
            slot_name.setStyleSheet(f"color: {CLR_DIM};")
            slot_name.setMinimumWidth(100)
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
                    color: {CLR_TEXT}; background: rgba(0,0,0,15);
                }}
            """)
            remove_btn.setVisible(False)
            slot_idx = i
            remove_btn.clicked.connect(lambda _checked=False, idx=slot_idx: self._remove_team_slot(idx))
            slot_lay.addWidget(remove_btn)

            self._team_slot_widgets.append({
                "widget": slot_w,
                "name": slot_name,
                "combo": slot_class_combo,
                "score": slot_score,
                "remove": remove_btn,
            })
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
            QPushButton:hover {{ background: rgba(107, 93, 79, 50); }}
        """)
        self._autofill_btn.clicked.connect(self._autofill_team)
        btn_row.addWidget(self._autofill_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFont(QFont(FONT_UI, 8))
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: {CLR_DIM}; background: transparent;
                border: 1px solid {CLR_BORDER}; border-radius: 4px;
                padding: 2px 10px;
            }}
            QPushButton:hover {{ color: {CLR_TEXT}; background: rgba(0,0,0,10); }}
        """)
        clear_btn.clicked.connect(self._clear_team)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        card_lay.addLayout(btn_row)

        layout.addWidget(card)

    # ── Scoring table (all cats x all classes) ───────────────────────

    def _build_scoring_table(self, layout: QVBoxLayout) -> None:
        header_row = QHBoxLayout()
        header_row.setSpacing(4)

        table_lbl = QLabel("CLASS SUITABILITY")
        table_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        table_lbl.setStyleSheet(f"color: {CLR_ACCENT};")
        header_row.addWidget(table_lbl)
        header_row.addStretch()

        self._table_count = QLabel("")
        self._table_count.setFont(QFont(FONT_MONO, 7))
        self._table_count.setStyleSheet(f"color: {CLR_DIM};")
        header_row.addWidget(self._table_count)
        layout.addLayout(header_row)

        self._table_scroll = QScrollArea()
        self._table_scroll.setWidgetResizable(True)
        self._table_scroll.setMinimumHeight(200)
        self._table_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {CLR_BORDER};
                border-radius: 6px;
                background: {CLR_BG_CARD};
            }}
            QScrollBar:vertical {{
                width: 6px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {CLR_DIM}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._table_container = QWidget()
        self._table_grid = QGridLayout(self._table_container)
        self._table_grid.setContentsMargins(6, 4, 6, 4)
        self._table_grid.setSpacing(0)

        self._table_scroll.setWidget(self._table_container)
        layout.addWidget(self._table_scroll, 1)

        self._table_cat_rows: list[dict[str, Any]] = []

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

    # ── Save data handling ───────────────────────────────────────────

    def _on_save_updated(self, save_data: SaveData) -> None:
        self._save_data = save_data
        self._house_cats = save_data.house_cats
        self._available_collars = unlocked_collars(save_data.unlocked_classes)
        if not self._available_collars:
            self._available_collars = list(COLLARS)

        self._info_label.setText(
            f"Day {save_data.current_day} \u2502 {len(self._house_cats)} cats"
        )

        collar_names = [c.name for c in self._available_collars]
        for sw in self._team_slot_widgets:
            combo: QComboBox = sw["combo"]
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(collar_names)
            combo.blockSignals(False)

        self._rebuild_scoring_table()
        self._refresh_team_scores()

        self._status_label.setText(
            f"Save loaded: {len(save_data.cats)} total cats "
            f"({len(self._house_cats)} in house)"
        )

    # ── Scoring table rebuild ────────────────────────────────────────

    def _rebuild_scoring_table(self) -> None:
        # Clear grid (but don't touch placeholder -- it may already be deleted)
        while self._table_grid.count():
            item = self._table_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._table_cat_rows.clear()

        collars = self._available_collars
        num_collars = len(collars)
        self._table_count.setText(f"{len(self._house_cats)} cats \u00d7 {num_collars} classes")

        # Header row
        name_header = QLabel("Cat")
        name_header.setFont(QFont(FONT_MONO, 7, QFont.Weight.Bold))
        name_header.setStyleSheet(f"color: {CLR_ACCENT}; padding: 2px 4px;")
        self._table_grid.addWidget(name_header, 0, 0)

        lv_header = QLabel("Lv")
        lv_header.setFont(QFont(FONT_MONO, 7, QFont.Weight.Bold))
        lv_header.setStyleSheet(f"color: {CLR_ACCENT}; padding: 2px 2px;")
        lv_header.setFixedWidth(22)
        lv_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table_grid.addWidget(lv_header, 0, 1)

        for j, collar in enumerate(collars):
            hdr = QLabel(collar.name[:4])
            hdr.setFont(QFont(FONT_MONO, 7, QFont.Weight.Bold))
            hdr.setStyleSheet(f"color: {collar.color}; padding: 2px 2px;")
            hdr.setFixedWidth(36)
            hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr.setToolTip(collar.name)
            self._table_grid.addWidget(hdr, 0, j + 2)

        # Separator line after header
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {CLR_BORDER};")
        self._table_grid.addWidget(sep, 1, 0, 1, num_collars + 2)

        # Viable cats: skip zero-stat cats
        viable_cats: list[tuple[SaveCat, list[float], int, float]] = []
        for cat in self._house_cats:
            if cat.age == 0 and all(
                getattr(cat, f"base_{s}") == 0
                for s in ("str", "dex", "con", "int", "spd", "cha", "lck")
            ):
                continue
            cs = save_cat_to_stats(cat)
            scores = [collar_score(c, cs) for c in collars]
            best_idx = max(range(len(scores)), key=lambda k: scores[k])
            viable_cats.append((cat, scores, best_idx, scores[best_idx]))

        viable_cats.sort(key=lambda x: x[3], reverse=True)

        cats_in_team = {
            slot["cat"].db_key for slot in self._team_slots if slot is not None
        }

        for row_i, (cat, scores, best_idx, best_score) in enumerate(viable_cats):
            grid_row = row_i + 2
            in_team = cat.db_key in cats_in_team

            # Cat name
            name_lbl = QLabel(cat.name)
            name_lbl.setFont(QFont(FONT_UI, 8))
            name_lbl.setStyleSheet(
                f"color: {CLR_TEXT}; padding: 3px 4px; font-weight: bold;"
                if in_team else f"color: {CLR_TEXT}; padding: 3px 4px;"
            )
            name_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            cat_ref = cat
            name_lbl.mousePressEvent = lambda _e, c=cat_ref: self._on_table_cat_click(c)
            self._table_grid.addWidget(name_lbl, grid_row, 0)

            # Level
            lv_lbl = QLabel(str(cat.level))
            lv_lbl.setFont(QFont(FONT_MONO, 7))
            lv_lbl.setStyleSheet(f"color: {CLR_DIM}; padding: 3px 2px;")
            lv_lbl.setFixedWidth(22)
            lv_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_grid.addWidget(lv_lbl, grid_row, 1)

            # Score cells
            for j, score_val in enumerate(scores):
                is_best = (j == best_idx)
                cell = _score_cell(score_val, is_best, collars[j].color)
                cell.setFixedWidth(36)
                cell.setStyleSheet(
                    cell.styleSheet() + " padding: 3px 2px;"
                )
                if in_team:
                    cell.setStyleSheet(
                        cell.styleSheet() + f" background: {CLR_HIGHLIGHT};"
                    )
                cell.setCursor(Qt.CursorShape.PointingHandCursor)
                collar_ref = collars[j]
                cell.mousePressEvent = lambda _e, c=cat_ref, co=collar_ref: self._on_table_cell_click(c, co)
                self._table_grid.addWidget(cell, grid_row, j + 2)

            self._table_cat_rows.append({
                "cat": cat,
                "scores": scores,
                "best_idx": best_idx,
                "row": grid_row,
            })

    def _on_table_cat_click(self, cat: SaveCat) -> None:
        """Add the cat to the next empty slot with their best class."""
        cs = save_cat_to_stats(cat)
        best_collar = self._available_collars[0]
        best_score = -999.0
        for c in self._available_collars:
            s = collar_score(c, cs)
            if s > best_score:
                best_score = s
                best_collar = c
        self._add_to_team(cat, best_collar, best_score)

    def _on_table_cell_click(self, cat: SaveCat, collar: CollarDef) -> None:
        """Add the cat with a specific class to the next empty slot."""
        cs = save_cat_to_stats(cat)
        score = collar_score(collar, cs)
        self._add_to_team(cat, collar, score)

    def _add_to_team(self, cat: SaveCat, collar: CollarDef, score: float) -> None:
        # Don't add the same cat twice
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
                self._rebuild_scoring_table()
                return

    # ── Team slot management ─────────────────────────────────────────

    def _remove_team_slot(self, idx: int) -> None:
        self._team_slots[idx] = None
        self._refresh_team_ui()
        self._rebuild_scoring_table()

    def _clear_team(self) -> None:
        self._team_slots = [None, None, None, None]
        self._refresh_team_ui()
        self._rebuild_scoring_table()

    def _refresh_team_ui(self) -> None:
        total_score = 0.0
        for i, slot in enumerate(self._team_slots):
            sw = self._team_slot_widgets[i]
            if slot is None:
                sw["name"].setText("(empty)")
                sw["name"].setStyleSheet(f"color: {CLR_DIM};")
                sw["score"].setText("")
                sw["combo"].setVisible(False)
                sw["remove"].setVisible(False)
                sw["widget"].setStyleSheet("border-radius: 4px;")
            else:
                cat = slot["cat"]
                collar = slot["collar"]
                score = slot["score"]
                sw["name"].setText(cat.name)
                sw["name"].setStyleSheet(f"color: {CLR_TEXT}; font-weight: bold;")
                sw["score"].setText(f"{score:.1f}")
                sw["combo"].setVisible(True)
                sw["remove"].setVisible(True)
                sw["widget"].setStyleSheet(
                    f"background: {CLR_HIGHLIGHT}; border-radius: 4px;"
                )

                combo: QComboBox = sw["combo"]
                combo.blockSignals(True)
                for j in range(combo.count()):
                    if combo.itemText(j) == collar.name:
                        combo.setCurrentIndex(j)
                        break
                combo.blockSignals(False)

                try:
                    combo.currentTextChanged.disconnect()
                except (RuntimeError, TypeError):
                    pass
                slot_idx = i
                combo.currentTextChanged.connect(
                    lambda text, idx=slot_idx: self._on_slot_class_changed(idx, text)
                )
                total_score += score

        self._tb_team_score_label.setText(
            f"Score: {total_score:.1f}" if total_score > 0 else "Score: --"
        )

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
        available_cats = [
            c for c in self._house_cats
            if c.age > 0 or any(
                getattr(c, f"base_{s}") != 0
                for s in ("str", "dex", "con", "int", "spd", "cha", "lck")
            )
        ]
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
        self._rebuild_scoring_table()

    # ── Window chrome ────────────────────────────────────────────────

    def _force_topmost(self) -> None:
        if not self.isVisible() or not _IS_WIN:
            return
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(
                hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0010,
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
            self.resize(560, 620)
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
