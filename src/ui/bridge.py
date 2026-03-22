"""Bridge between Python backend and the React frontend via QWebChannel.

Exposes roster, team, breeding, and LLM data to JavaScript. Receives signals
from SaveWatcher and re-publishes them as QWebChannel signals.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src.breeding.calculator import (
    analyze_pair,
    rank_pairs_for_class,
    rank_pairs_overall,
    suggest_room_distribution,
)
from src.data.collars import (
    COLLARS,
    CollarDef,
    collar_by_name,
    collar_score,
    save_cat_to_stats,
    unlocked_collars,
)
from src.data.save_reader import RoomStats, SaveCat, SaveData
from src.llm.advisor import LLMAdvisor
from src.utils.config_loader import AppConfig

log = logging.getLogger("mewgent.ui.bridge")

STAT_ORDER = ["str", "dex", "con", "int", "spd", "cha", "lck"]


def _cat_dict(cat: SaveCat) -> dict[str, Any]:
    return {
        "db_key": cat.db_key,
        "name": cat.name,
        "level": cat.level,
        "age": cat.age,
        "gender": cat.gender,
        "active_class": cat.active_class,
        "base_str": cat.base_str,
        "base_dex": cat.base_dex,
        "base_con": cat.base_con,
        "base_int": cat.base_int,
        "base_spd": cat.base_spd,
        "base_cha": cat.base_cha,
        "base_lck": cat.base_lck,
        "abilities": cat.abilities,
        "passives": cat.passives,
        "status": cat.status,
        "breed_coefficient": round(cat.breed_coefficient, 4),
        "retired": cat.retired,
        "aggression": round(cat.aggression, 3) if cat.aggression is not None else None,
        "libido": round(cat.libido, 3) if cat.libido is not None else None,
        "inbredness": round(cat.inbredness, 3) if cat.inbredness is not None else None,
        "disorders": cat.disorders,
        "visual_mutation_ids": cat.visual_mutation_ids,
        "parent_a_key": cat.parent_a_key,
        "parent_b_key": cat.parent_b_key,
        "children_keys": cat.children_keys,
        "lover_keys": cat.lover_keys,
        "hater_keys": cat.hater_keys,
        "generation": cat.generation,
        "room": cat.room,
    }


def _collar_dict(c: CollarDef) -> dict[str, Any]:
    return {
        "name": c.name,
        "color": c.color,
        "modifiers": c.modifiers,
        "score_weights": list(c.score_weights),
    }


def _compute_viable(
    house_cats: list[SaveCat],
    collars: list[CollarDef],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for cat in house_cats:
        if cat.age == 0 and all(getattr(cat, f"base_{s}") == 0 for s in STAT_ORDER):
            continue
        cs = save_cat_to_stats(cat)
        scores = [collar_score(c, cs) for c in collars]
        best_idx = max(range(len(scores)), key=lambda k: scores[k])
        result.append(
            {
                "cat": _cat_dict(cat),
                "scores": [round(s, 2) for s in scores],
                "best_idx": best_idx,
                "best_score": round(scores[best_idx], 2),
            }
        )
    result.sort(key=lambda x: x["best_score"], reverse=True)
    return result


class _LLMTeamWorker(QThread):
    """Run LLM team suggestion off the main thread."""

    result_ready = Signal(object)

    def __init__(self, advisor, cats, collars, base_scores, parent=None):
        super().__init__(parent)
        self._advisor = advisor
        self._cats = cats
        self._collars = collars
        self._base_scores = base_scores

    def run(self):
        try:
            result = self._advisor.suggest_team_composition(
                self._cats,
                self._collars,
                self._base_scores,
            )
            self.result_ready.emit(result)
        except Exception:
            log.exception("LLM team worker failed")
            self.result_ready.emit(None)


class _LLMBreedWorker(QThread):
    """Run LLM breeding pair suggestion off the main thread."""

    result_ready = Signal(object)

    def __init__(
        self, advisor, cats, collar_name, stimulation, room_stats=None, parent=None
    ):
        super().__init__(parent)
        self._advisor = advisor
        self._cats = cats
        self._collar_name = collar_name
        self._stimulation = stimulation
        self._room_stats = room_stats

    def run(self):
        try:
            result = self._advisor.suggest_breeding_pairs(
                self._cats,
                self._collar_name,
                self._stimulation,
                room_stats=self._room_stats,
            )
            self.result_ready.emit(result)
        except Exception:
            log.exception("LLM breed worker failed")
            self.result_ready.emit(None)


class _LLMDistributionWorker(QThread):
    """Run LLM room distribution suggestion off the main thread."""

    result_ready = Signal(object)

    def __init__(self, advisor, cats, room_stats, parent=None):
        super().__init__(parent)
        self._advisor = advisor
        self._cats = cats
        self._room_stats = room_stats

    def run(self):
        try:
            result = self._advisor.suggest_room_distribution(
                self._cats,
                self._room_stats,
            )
            self.result_ready.emit(result)
        except Exception:
            log.exception("LLM distribution worker failed")
            self.result_ready.emit(None)


class OverlayBridge(QObject):
    """QObject exposed to JavaScript via QWebChannel."""

    roster_updated = Signal(str)
    team_updated = Signal(str)
    team_synergy_updated = Signal(str)
    save_info_updated = Signal(str)
    llm_status_changed = Signal(str)
    collars_updated = Signal(str)
    breeding_result = Signal(str)
    distribution_result = Signal(str)
    room_stats_updated = Signal(str)
    update_available = Signal(str)
    update_check_status = Signal(str)

    def __init__(self, cfg: AppConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._save_data: SaveData | None = None
        self._house_cats: list[SaveCat] = []
        self._available_collars: list[CollarDef] = list(COLLARS)
        self._team_slots: list[dict | None] = [None, None, None, None]
        self._viable: list[dict[str, Any]] = []
        self._status = "Waiting for save data..."
        self._shell = None
        self._update_info: str = ""
        self._drag_origin_x: int = 0
        self._drag_origin_y: int = 0
        self._drag_win_x: int = 0
        self._drag_win_y: int = 0
        self._update_check_worker: QThread | None = None
        self._room_stats: dict[str, RoomStats] = {}

        self._llm = LLMAdvisor(
            model=cfg.llm.model,
            enabled=cfg.llm.enabled,
            mock=cfg.llm.mock,
        )

    def set_shell(self, shell) -> None:
        """Store a reference to the OverlayShell for window management."""
        self._shell = shell

    @property
    def llm(self) -> LLMAdvisor:
        return self._llm

    # ── Slots callable from JavaScript ──────────────────────────────

    @Slot(result=str)
    def get_roster(self) -> str:
        return json.dumps(self._viable)

    @Slot(result=str)
    def get_collars(self) -> str:
        return json.dumps([_collar_dict(c) for c in self._available_collars])

    @Slot(result=str)
    def get_team(self) -> str:
        return json.dumps(self._team_to_json())

    @Slot(result=str)
    def get_save_info(self) -> str:
        sd = self._save_data
        return json.dumps(
            {
                "day": sd.current_day if sd else 0,
                "cat_count": len(self._house_cats),
                "status": self._status,
            }
        )

    @Slot(result=str)
    def get_room_stats(self) -> str:
        return json.dumps(self._room_stats_json())

    @Slot(int, int, str)
    def set_team_slot(self, slot: int, cat_db_key: int, collar_name: str) -> None:
        if slot < 0 or slot > 3:
            return
        cat = next((c for c in self._house_cats if c.db_key == cat_db_key), None)
        collar = collar_by_name(collar_name)
        if cat is None or collar is None:
            return
        if cat.age <= 1 or cat.retired:
            return
        cs = save_cat_to_stats(cat)
        score = collar_score(collar, cs)
        self._team_slots[slot] = {
            "cat": cat,
            "collar": collar,
            "score": score,
        }
        self._emit_team()

    @Slot(int)
    def remove_team_slot(self, slot: int) -> None:
        if 0 <= slot <= 3:
            self._team_slots[slot] = None
            self._emit_team()

    @Slot()
    def clear_team(self) -> None:
        self._team_slots = [None, None, None, None]
        self._emit_team()
        self.team_synergy_updated.emit("")

    @Slot()
    def autofill_team(self) -> None:
        if not self._house_cats or not self._available_collars:
            return
        self._team_slots = [None, None, None, None]
        self.team_synergy_updated.emit("")
        available = [c for c in self._house_cats if c.age > 1 and not c.retired]
        used_cats: set[int] = set()
        used_collars: set[str] = set()

        for slot_idx in range(4):
            best_pick = None
            best_score = -999.0
            for cat in available:
                if cat.db_key in used_cats:
                    continue
                cs = save_cat_to_stats(cat)
                for c in self._available_collars:
                    if c.name in used_collars:
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
            used_cats.add(cat.db_key)
            used_collars.add(collar.name)

        self._emit_team()

    @Slot()
    def autofill_team_llm(self) -> None:
        if not self._llm.available:
            self.autofill_team()
            return
        self.llm_status_changed.emit("AI thinking...")

        available = [c for c in self._house_cats if c.age > 1 and not c.retired]
        base_scores: dict[int, list[tuple[CollarDef, float]]] = {}
        for cat in available:
            cs = save_cat_to_stats(cat)
            base_scores[cat.db_key] = [
                (c, collar_score(c, cs)) for c in self._available_collars
            ]

        self._llm_worker = _LLMTeamWorker(
            self._llm,
            available,
            self._available_collars,
            base_scores,
            self,
        )
        self._llm_worker.result_ready.connect(self._on_llm_team_result)
        self._llm_worker.start()

    @Slot()
    def request_close(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    @Slot(result=str)
    def get_update_info(self) -> str:
        return self._update_info

    @Slot(str)
    def open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def check_for_updates(self) -> None:
        """Fetch version.json from config update.check_url (runs in a worker thread)."""
        from src.utils.update_checker import ManualUpdateCheckWorker

        url = (self._cfg.update.check_url or "").strip()
        if not url:
            self.update_check_status.emit(json.dumps({"state": "disabled"}))
            return
        if (
            self._update_check_worker is not None
            and self._update_check_worker.isRunning()
        ):
            return
        self.update_check_status.emit(json.dumps({"state": "checking"}))
        worker = ManualUpdateCheckWorker(url, self)
        worker.result.connect(self._on_manual_update_check_result)
        self._update_check_worker = worker
        worker.start()

    @Slot(str)
    def _on_manual_update_check_result(self, payload_json: str) -> None:
        try:
            data = json.loads(payload_json)
        except json.JSONDecodeError:
            return
        if data.get("state") == "available":
            self.on_update_found(
                str(data.get("version", "")),
                str(data.get("url", "")),
                str(data.get("changelog", "")),
            )
        self.update_check_status.emit(payload_json)

    def on_update_found(self, version: str, url: str, changelog: str) -> None:
        self._update_info = json.dumps(
            {"version": version, "url": url, "changelog": changelog}
        )
        self.update_available.emit(self._update_info)

    # ── Window drag slots (called from JS title bar) ─────────────────

    @Slot(int, int)
    def begin_drag(self, screen_x: int, screen_y: int) -> None:
        if self._shell is None:
            return
        self._drag_origin_x = screen_x
        self._drag_origin_y = screen_y
        pos = self._shell.pos()
        self._drag_win_x = pos.x()
        self._drag_win_y = pos.y()

    @Slot(int, int)
    def update_drag(self, screen_x: int, screen_y: int) -> None:
        if self._shell is None:
            return
        dx = screen_x - self._drag_origin_x
        dy = screen_y - self._drag_origin_y
        self._shell.move(self._drag_win_x + dx, self._drag_win_y + dy)

    @Slot()
    def end_drag(self) -> None:
        pass

    # ── Breeding slots ───────────────────────────────────────────────

    @Slot(int, int, int, result=str)
    def get_breeding_advice(
        self, cat_a_key: int, cat_b_key: int, stimulation: int
    ) -> str:
        """Compute deterministic breeding probabilities for a pair."""
        cat_a = next((c for c in self._house_cats if c.db_key == cat_a_key), None)
        cat_b = next((c for c in self._house_cats if c.db_key == cat_b_key), None)
        if cat_a is None or cat_b is None:
            return json.dumps(None)

        pair_room = None
        if cat_a.room and cat_a.room == cat_b.room:
            pair_room = self._room_stats.get(cat_a.room)

        advice = analyze_pair(cat_a, cat_b, stimulation, room_stats=pair_room)
        return json.dumps(asdict(advice))

    @Slot(str, int, result=str)
    def get_breeding_rankings(self, collar_name: str, stimulation: int) -> str:
        """Rank cat pairs for a target class (deterministic)."""
        collar = collar_by_name(collar_name)
        if collar is None or len(self._house_cats) < 2:
            return json.dumps([])
        rankings = rank_pairs_for_class(
            self._house_cats, collar, stimulation, room_stats=self._room_stats
        )
        return json.dumps([asdict(r) for r in rankings])

    @Slot(str, int)
    def suggest_breeding_llm(self, collar_name: str, stimulation: int) -> None:
        """Request LLM-powered breeding pair suggestions (async)."""
        if not self._llm.available:
            rankings = []
            collar = collar_by_name(collar_name)
            if collar and len(self._house_cats) >= 2:
                rankings = rank_pairs_for_class(
                    self._house_cats, collar, stimulation, room_stats=self._room_stats
                )
            self.breeding_result.emit(
                json.dumps(
                    {
                        "source": "calculator",
                        "pairs": [asdict(r) for r in rankings],
                    }
                )
            )
            return

        self.llm_status_changed.emit("AI analyzing breeding pairs...")

        self._llm_breed_worker = _LLMBreedWorker(
            self._llm,
            self._house_cats,
            collar_name,
            stimulation,
            room_stats=self._room_stats,
            parent=self,
        )
        self._llm_breed_worker.result_ready.connect(self._on_llm_breed_result)
        self._llm_breed_worker.start()

    @Slot(result=str)
    def get_room_distribution(self) -> str:
        """Compute deterministic room distribution for optimal breeding."""
        if len(self._house_cats) < 2 or not self._room_stats:
            return json.dumps(None)
        dist = suggest_room_distribution(self._house_cats, self._room_stats)
        return json.dumps(asdict(dist))

    @Slot(result=str)
    def get_overall_rankings(self) -> str:
        """Rank all cat pairs by total expected stats (class-agnostic)."""
        if len(self._house_cats) < 2:
            return json.dumps([])
        rankings = rank_pairs_overall(self._house_cats, room_stats=self._room_stats)
        return json.dumps([asdict(r) for r in rankings])

    @Slot()
    def suggest_distribution_llm(self) -> None:
        """Request LLM-powered room distribution (async)."""
        if not self._llm.available or len(self._house_cats) < 2:
            dist = None
            if self._house_cats and self._room_stats:
                dist = suggest_room_distribution(self._house_cats, self._room_stats)
            self.distribution_result.emit(
                json.dumps(
                    {
                        "source": "calculator",
                        "distribution": asdict(dist) if dist else None,
                    }
                )
            )
            return

        self.llm_status_changed.emit("AI optimizing room distribution...")
        self._llm_dist_worker = _LLMDistributionWorker(
            self._llm,
            self._house_cats,
            self._room_stats,
            self,
        )
        self._llm_dist_worker.result_ready.connect(self._on_llm_distribution_result)
        self._llm_dist_worker.start()

    # ── Save data handling (called from overlay shell) ──────────────

    def on_save_updated(self, save_data: SaveData) -> None:
        self._save_data = save_data
        self._house_cats = save_data.house_cats
        self._available_collars = unlocked_collars(save_data.unlocked_classes)
        if not self._available_collars:
            self._available_collars = list(COLLARS)
        self._llm.clear_cache()

        self._viable = _compute_viable(self._house_cats, self._available_collars)
        self._room_stats = save_data.room_stats
        self._refresh_team_scores()

        self._status = (
            f"Save loaded: {len(save_data.cats)} total cats "
            f"({len(self._house_cats)} in house)"
        )

        self.roster_updated.emit(json.dumps(self._viable))
        self.collars_updated.emit(
            json.dumps([_collar_dict(c) for c in self._available_collars])
        )
        self.save_info_updated.emit(
            json.dumps(
                {
                    "day": save_data.current_day,
                    "cat_count": len(self._house_cats),
                    "status": self._status,
                }
            )
        )
        self._emit_team()
        self.room_stats_updated.emit(json.dumps(self._room_stats_json()))

    # ── Internal helpers ────────────────────────────────────────────

    def _team_to_json(self) -> list[dict | None]:
        result: list[dict | None] = []
        for slot in self._team_slots:
            if slot is None:
                result.append(None)
            else:
                d: dict[str, Any] = {
                    "cat": _cat_dict(slot["cat"]),
                    "collar_name": slot["collar"].name,
                    "score": round(slot["score"], 2),
                }
                if slot.get("explanation"):
                    d["explanation"] = slot["explanation"]
                result.append(d)
        return result

    def _emit_team(self) -> None:
        self.team_updated.emit(json.dumps(self._team_to_json()))

    def _room_stats_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for room_name, rs in self._room_stats.items():
            result[room_name] = {
                "appeal": rs.appeal,
                "comfort": rs.comfort,
                "effective_comfort": rs.effective_comfort,
                "stimulation": rs.stimulation,
                "health": rs.health,
                "mutation": rs.mutation,
                "cat_count": rs.cat_count,
                "furniture_count": rs.furniture_count,
            }
        return result

    def _refresh_team_scores(self) -> None:
        for slot in self._team_slots:
            if slot is not None:
                cs = save_cat_to_stats(slot["cat"])
                slot["score"] = collar_score(slot["collar"], cs)
        self._emit_team()

    @Slot(object)
    def _on_llm_team_result(self, result: dict | None) -> None:
        self.llm_status_changed.emit("")
        if not result:
            self.autofill_team()
            return

        team_entries = result.get("team", []) if isinstance(result, dict) else result
        synergy = result.get("synergy", "") if isinstance(result, dict) else ""

        self._team_slots = [None, None, None, None]
        cat_by_key = {c.db_key: c for c in self._house_cats}

        for slot_idx, entry in enumerate(team_entries[:4]):
            db_key = entry.get("cat_db_key")
            collar_name = entry.get("collar_name", "")
            cat = cat_by_key.get(db_key)
            collar = collar_by_name(collar_name)
            if cat is None or collar is None:
                continue
            if cat.age <= 1 or cat.retired:
                continue
            cs = save_cat_to_stats(cat)
            score = collar_score(collar, cs)
            self._team_slots[slot_idx] = {
                "cat": cat,
                "collar": collar,
                "score": score,
                "explanation": entry.get("reason", ""),
            }

        self._emit_team()
        self.team_synergy_updated.emit(synergy)

    @Slot(object)
    def _on_llm_breed_result(self, result: list[dict] | None) -> None:
        self.llm_status_changed.emit("")
        if result:
            self.breeding_result.emit(
                json.dumps(
                    {
                        "source": "llm",
                        "pairs": result,
                    }
                )
            )
        else:
            self.breeding_result.emit(
                json.dumps(
                    {
                        "source": "llm",
                        "pairs": [],
                    }
                )
            )

    @Slot(object)
    def _on_llm_distribution_result(self, result: dict | None) -> None:
        self.llm_status_changed.emit("")
        if result and isinstance(result, dict):
            self.distribution_result.emit(
                json.dumps({"source": "llm", "distribution": result})
            )
        else:
            dist = None
            if self._house_cats and self._room_stats:
                dist = suggest_room_distribution(self._house_cats, self._room_stats)
            self.distribution_result.emit(
                json.dumps(
                    {
                        "source": "calculator",
                        "distribution": asdict(dist) if dist else None,
                    }
                )
            )
