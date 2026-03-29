"""Bridge between Python backend and the React frontend via QWebChannel.

Exposes roster, team, breeding, and LLM data to JavaScript. Receives signals
from SaveWatcher and re-publishes them as QWebChannel signals.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from PySide6.QtCore import QObject, QThread, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src.breeding.calculator import (
    COMFORT_CAT_LIMIT,
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
from src.data.item_effects import item_effect_entry
from src.data.save_reader import RoomStats, SaveCat, SaveData
from src.llm.advisor import (
    LLMAdvisor,
    build_llm_advisor,
    inventory_item_ids_from_save,
    team_synergy_ui_payload,
    verify_openai_api_key,
)
from src.ui.payload import (
    cat_to_dict as _cat_dict,
    collar_to_dict as _collar_dict,
    compute_viable as _compute_viable,
    serialize_catalog_cats as _serialize_catalog_cats,
)
from src.utils.config_loader import AppConfig


def _serialize_save_info(
    save_data: SaveData | None, house_cat_count: int, status: str
) -> dict[str, Any]:
    empty_inv = {"backpack": [], "storage": [], "trash": []}
    if save_data is None:
        return {
            "day": 0,
            "cat_count": house_cat_count,
            "status": status,
            "inventory": empty_inv,
        }
    return {
        "day": save_data.current_day,
        "cat_count": house_cat_count,
        "status": status,
        "inventory": {
            "backpack": [
                item_effect_entry(x.item_id) for x in save_data.inventory_backpack
            ],
            "storage": [
                item_effect_entry(x.item_id) for x in save_data.inventory_storage
            ],
            "trash": [item_effect_entry(x.item_id) for x in save_data.inventory_trash],
        },
    }


log = logging.getLogger("mewgent.ui.bridge")

_TEAM_SYNERGY_EMPTY_JSON = '{"synergy":"","stash_tips":[]}'


class _LLMTeamWorker(QThread):
    """Run LLM team suggestion off the main thread."""

    result_ready = Signal(object)

    def __init__(
        self,
        advisor,
        cats,
        collars,
        base_scores,
        parent=None,
        *,
        inventory_item_ids: list[str] | None = None,
    ):
        super().__init__(parent)
        self._advisor = advisor
        self._cats = cats
        self._collars = collars
        self._base_scores = base_scores
        self._inventory_item_ids = inventory_item_ids

    def run(self):
        try:
            result = self._advisor.suggest_team_composition(
                self._cats,
                self._collars,
                self._base_scores,
                inventory_item_ids=self._inventory_item_ids,
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


class _LLMVerifyWorker(QThread):
    """Verify OpenAI API key off the main thread (HTTP GET /v1/models)."""

    finished_ok = Signal(int, bool, str)

    def __init__(
        self, req_id: int, api_key: str, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._req_id = req_id
        self._api_key = api_key

    def run(self) -> None:
        try:
            ok, msg = verify_openai_api_key(self._api_key)
        except Exception:
            log.exception("LLM verify worker crashed")
            ok, msg = False, "Could not verify OpenAI connection."
        log.info("LLM verify worker finished req=%s ok=%s", self._req_id, ok)
        self.finished_ok.emit(self._req_id, ok, msg)


class OverlayBridge(QObject):
    """QObject exposed to JavaScript via QWebChannel."""

    roster_updated = Signal(str)
    catalog_updated = Signal(str)
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
    llm_settings_changed = Signal(str)

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

        self._llm = build_llm_advisor(cfg.llm)
        self._llm_verify_req: int = 0
        self._llm_verify_worker: _LLMVerifyWorker | None = None

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
    def get_catalog(self) -> str:
        if self._save_data is None:
            return "[]"
        return json.dumps(_serialize_catalog_cats(self._save_data.cats))

    @Slot(result=str)
    def get_collars(self) -> str:
        return json.dumps([_collar_dict(c) for c in self._available_collars])

    @Slot(result=str)
    def get_team(self) -> str:
        return json.dumps(self._team_to_json())

    @Slot(result=str)
    def get_save_info(self) -> str:
        return json.dumps(
            _serialize_save_info(self._save_data, len(self._house_cats), self._status)
        )

    @Slot(result=str)
    def get_llm_settings(self) -> str:
        return json.dumps(
            self._llm.settings_snapshot(default_model=self._cfg.llm.model)
        )

    def _emit_llm_settings(self) -> None:
        snap = self._llm.settings_snapshot(default_model=self._cfg.llm.model)
        self.llm_settings_changed.emit(json.dumps(snap))

    @Slot(int, bool, str)
    def _on_llm_verify_done(self, req_id: int, ok: bool, msg: str) -> None:
        if req_id != self._llm_verify_req:
            log.debug(
                "Ignoring stale LLM verify result req=%s (current=%s)",
                req_id,
                self._llm_verify_req,
            )
            return
        self._llm.connection_set_result(ok, msg)
        self._emit_llm_settings()

    def _start_llm_verify(self) -> None:
        if not self._llm.can_verify_openai():
            return
        key = self._llm.effective_api_key()
        if not key:
            self._llm.connection_set_result(False, "No API key configured.")
            self._emit_llm_settings()
            return
        old = self._llm_verify_worker
        if old is not None:
            try:
                old.finished_ok.disconnect(self._on_llm_verify_done)
            except TypeError:
                pass
        self._llm_verify_req += 1
        rid = self._llm_verify_req
        w = _LLMVerifyWorker(rid, key, self)
        self._llm_verify_worker = w
        w.finished_ok.connect(
            self._on_llm_verify_done,
            Qt.ConnectionType.QueuedConnection,
        )
        w.start()

    @Slot(str, result=str)
    def apply_llm_settings(self, payload: str) -> str:
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("invalid payload")
            model = str(data.get("model", "")).strip()
            key_action = str(data.get("key_action", "unchanged"))
            key_value = str(data.get("api_key", ""))
            if key_action not in ("unchanged", "set", "clear"):
                key_action = "unchanged"
            trimmed_set = key_action == "set" and key_value.strip() != ""
            self._llm.apply_ui_settings(
                default_model=self._cfg.llm.model,
                model=model or self._cfg.llm.model,
                key_action=key_action,
                key_value=key_value,
            )
            if trimmed_set:
                self._llm.connection_set_pending()
            self._emit_llm_settings()
            if trimmed_set:
                self._start_llm_verify()
            return json.dumps({"ok": True})
        except Exception as e:
            log.exception("apply_llm_settings failed")
            return json.dumps({"ok": False, "error": str(e)})

    @Slot()
    def test_llm_connection(self) -> None:
        if not self._llm.can_verify_openai():
            return
        self._llm.connection_set_pending()
        self._emit_llm_settings()
        self._start_llm_verify()

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
        self.team_synergy_updated.emit(_TEAM_SYNERGY_EMPTY_JSON)

    @Slot()
    def autofill_team(self) -> None:
        """Deprecated no-op: team autofill is LLM-only. Slot kept for WebChannel compatibility."""

    @Slot()
    def autofill_team_llm(self) -> None:
        if not self._llm.available:
            self.llm_status_changed.emit("AI advisor unavailable")
            return
        self.llm_status_changed.emit("AI thinking...")

        available = [c for c in self._house_cats if c.age > 1 and not c.retired]
        base_scores: dict[int, list[tuple[CollarDef, float]]] = {}
        for cat in available:
            cs = save_cat_to_stats(cat)
            base_scores[cat.db_key] = [
                (c, collar_score(c, cs)) for c in self._available_collars
            ]

        stash_ids = inventory_item_ids_from_save(self._save_data)
        self._llm_worker = _LLMTeamWorker(
            self._llm,
            available,
            self._available_collars,
            base_scores,
            self,
            inventory_item_ids=stash_ids or None,
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

    def _emit_distribution_error(self, message: str) -> None:
        self.distribution_result.emit(
            json.dumps(
                {
                    "source": "error",
                    "distribution": None,
                    "error": message,
                }
            )
        )

    @Slot()
    def suggest_distribution_llm(self) -> None:
        """Request LLM-powered room distribution (async)."""
        if len(self._house_cats) < 2:
            self._emit_distribution_error("Need at least 2 cats in the house.")
            return
        if not self._room_stats:
            self._emit_distribution_error("No room data loaded.")
            return
        if not self._llm.available:
            self._emit_distribution_error(
                "OpenAI advisor is not available. Add an API key or enable the advisor."
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
        self.catalog_updated.emit(json.dumps(_serialize_catalog_cats(save_data.cats)))
        self.collars_updated.emit(
            json.dumps([_collar_dict(c) for c in self._available_collars])
        )
        self.save_info_updated.emit(
            json.dumps(
                _serialize_save_info(save_data, len(self._house_cats), self._status)
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

    def _backfill_llm_distribution(self, result: dict) -> dict:
        """Ensure every house cat appears in exactly one room's cat_keys.

        The LLM often only returns pair cats; this distributes the rest
        using comfort headroom, matching the deterministic calculator logic.
        """
        rooms = result.get("rooms")
        if not rooms or not self._house_cats or not self._room_stats:
            return result

        assigned: set[int] = set()
        for room in rooms:
            for k in room.get("cat_keys", []):
                assigned.add(k)

        missing = [c for c in self._house_cats if c.db_key not in assigned]
        if not missing:
            return result

        room_by_name: dict[str, dict] = {r["room_name"]: r for r in rooms}
        for rname in self._room_stats:
            if rname not in room_by_name:
                new_room = {
                    "room_name": rname,
                    "cat_keys": [],
                    "best_pair": None,
                    "pair_score": 0.0,
                    "pair_reason": "",
                }
                rooms.append(new_room)
                room_by_name[rname] = new_room

        for cat in missing:
            best_room_name: str | None = None
            best_headroom = float("-inf")
            for rname, room in room_by_name.items():
                rs = self._room_stats.get(rname)
                if rs is None:
                    continue
                count_after = len(room.get("cat_keys", [])) + 1
                headroom = rs.comfort - max(0, count_after - COMFORT_CAT_LIMIT)
                if headroom > best_headroom:
                    best_headroom = headroom
                    best_room_name = rname
                elif headroom == best_headroom and best_room_name is not None:
                    if not room.get("best_pair") and room_by_name[best_room_name].get(
                        "best_pair"
                    ):
                        best_room_name = rname
            if best_room_name:
                room_by_name[best_room_name].setdefault("cat_keys", []).append(
                    cat.db_key
                )

        for room in rooms:
            rs = self._room_stats.get(room["room_name"])
            if rs:
                count = len(room.get("cat_keys", []))
                room["effective_comfort"] = rs.comfort - max(
                    0, count - COMFORT_CAT_LIMIT
                )

        return result

    @Slot(object)
    def _on_llm_team_result(self, result: dict | None) -> None:
        if not result:
            self.llm_status_changed.emit("AI team suggestion failed")
            return
        self.llm_status_changed.emit("")

        if isinstance(result, dict):
            team_entries = result.get("team", [])
            synergy_payload = json.dumps(team_synergy_ui_payload(result))
        elif isinstance(result, list):
            team_entries = result
            synergy_payload = _TEAM_SYNERGY_EMPTY_JSON
        else:
            team_entries = []
            synergy_payload = _TEAM_SYNERGY_EMPTY_JSON

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
        self.team_synergy_updated.emit(synergy_payload)

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
        if result and isinstance(result, dict) and result.get("rooms"):
            result = self._backfill_llm_distribution(result)
            self.distribution_result.emit(
                json.dumps(
                    {
                        "source": "llm",
                        "distribution": result,
                        "error": None,
                    }
                )
            )
        else:
            self._emit_distribution_error(
                "Could not get room distribution from the model."
            )
