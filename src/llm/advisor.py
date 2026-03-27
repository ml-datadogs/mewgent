from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.data.collars import CollarDef
    from src.utils.config_loader import LLMConfig

from src.data.item_effects import (
    item_effect_entry,
    item_effect_for_id,
    item_slot_for_id,
)
from src.data.save_reader import SaveCat, SaveData

log = logging.getLogger("mewgent.llm.advisor")

_WIKI_DIR = Path(__file__).resolve().parents[2] / "wiki_data" / "text"
_STRATEGY_PATH = Path(__file__).resolve().parent / "breeding_strategy_context.md"
# Cap wiki excerpt so bundled community strategy notes are not truncated away.
_WIKI_BREEDING_MAX_CHARS = 12000

_SYSTEM_PROMPT = """\
You are an expert advisor for the game Mewgenics. You analyze cat stats, \
abilities, and class mechanics to recommend optimal class assignments and \
team compositions. You also provide breeding advice based on inheritance \
mechanics, house stats, and inbreeding risks. Players may follow conservative \
(outcrossing) or aggressive (high-inbreeding) breeding philosophies; reflect \
the roster, coefficients, and room stats you are given. Always respond with \
valid JSON matching the requested schema.\
"""

_ROLE_TAGS: dict[str, str] = {
    "Fighter": "melee DPS",
    "Hunter": "ranged DPS",
    "Mage": "magic DPS",
    "Tank": "frontline tank",
    "Cleric": "healer/support",
    "Thief": "fast striker",
    "Necromancer": "sustain caster",
    "Tinkerer": "gadget specialist",
    "Butcher": "bruiser",
    "Druid": "summoner/support",
    "Psychic": "control caster",
    "Monk": "versatile hybrid",
    "Jester": "wildcard",
    "Collarless": "generalist",
}

OPENAI_MODEL_CHOICES: tuple[str, ...] = (
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5.4",
    "o4-mini",
    "o3-mini",
)

_MOCK_EXPLANATIONS = [
    "High {stat} makes this cat a natural {role}, and {ability} synergizes well with the class kit.",
    "With strong {stat}, this cat excels as a {role}. {ability} provides additional utility.",
    "This cat's {stat} is outstanding for the {role} role, though low {weak} is a minor concern.",
    "Excellent {stat} combined with {ability} makes this an ideal {role} pick.",
    "A solid {role} candidate -- {stat} is well above average for the class needs.",
]


def _load_wiki_context() -> str:
    """Load class and ability descriptions from scraped wiki data."""
    parts: list[str] = []
    for name in ("classes", "abilities"):
        path = _WIKI_DIR / f"{name}.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if len(text) > 12000:
                text = text[:12000] + "\n[... truncated]"
            parts.append(text)
    return "\n\n---\n\n".join(parts)


def _load_breeding_context() -> str:
    """Load breeding mechanics (scraped wiki) plus community strategy notes."""
    parts: list[str] = []
    wiki_path = _WIKI_DIR / "breeding.md"
    if wiki_path.exists():
        text = wiki_path.read_text(encoding="utf-8")
        if len(text) > _WIKI_BREEDING_MAX_CHARS:
            text = text[:_WIKI_BREEDING_MAX_CHARS] + "\n[... truncated]"
        parts.append(text)
    if _STRATEGY_PATH.exists():
        parts.append(_STRATEGY_PATH.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def openai_verify_error_message(exc: BaseException) -> str:
    """Map OpenAI / network errors to a short user-facing string (no secrets)."""
    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError
    except ImportError:
        return "Could not verify OpenAI connection."
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "status_code", None)
        if code == 401:
            return "Invalid API key."
        if code == 429:
            return "Rate limited. Try again later."
        if code is not None:
            return f"OpenAI error ({code})."
        return "OpenAI request failed."
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return "Network error. Check your connection."
    if isinstance(exc, TimeoutError):
        return "Network error. Check your connection."
    return "Could not verify OpenAI connection."


def verify_openai_api_key(api_key: str) -> tuple[bool, str]:
    """Lightweight authenticated GET /v1/models?limit=1 (same auth as chat).

    Uses **httpx** with explicit connect/read timeouts. The OpenAI SDK's
    ``models.list()`` iterator can ignore per-request timeouts on some setups,
    leaving the UI stuck on "pending" forever.
    """
    import httpx

    key = (api_key or "").strip()
    if not key:
        return False, "No API key configured."
    timeout = httpx.Timeout(20.0, connect=5.0)
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                params={"limit": 1},
            )
    except httpx.TimeoutException:
        log.warning("OpenAI connection verify timed out")
        return False, "Network error. Check your connection."
    except httpx.ConnectError:
        log.warning("OpenAI connection verify: connect error")
        return False, "Network error. Check your connection."
    except httpx.RequestError as e:
        log.warning("OpenAI connection verify failed: %s", type(e).__name__)
        return False, "Could not verify OpenAI connection."

    if r.status_code == 200:
        return True, ""
    if r.status_code == 401:
        return False, "Invalid API key."
    if r.status_code == 429:
        return False, "Rate limited. Try again later."
    log.warning("OpenAI connection verify HTTP %s", r.status_code)
    return False, f"OpenAI error ({r.status_code})."


def _cat_summary(cat: SaveCat) -> str:
    stats = (
        f"STR={cat.base_str} DEX={cat.base_dex} CON={cat.base_con} "
        f"INT={cat.base_int} SPD={cat.base_spd} CHA={cat.base_cha} LCK={cat.base_lck}"
    )
    abilities = ", ".join(cat.abilities) if cat.abilities else "none"
    passives = ", ".join(cat.passives) if cat.passives else "none"
    if cat.equipment:
        eparts: list[str] = []
        for eid in cat.equipment:
            eff = item_effect_for_id(eid)
            slot = item_slot_for_id(eid)
            slot_b = f" [{slot}]" if slot else ""
            if eff:
                eparts.append(f"{eid}{slot_b}: {eff}")
            else:
                eparts.append(f"{eid}{slot_b}" if slot_b else eid)
        equip = " | ".join(eparts)
    else:
        equip = "none"
    return (
        f"{cat.name} (Lv{cat.level}, Age{cat.age}): {stats} "
        f"| abilities: {abilities} | passives: {passives} | equipment: {equip}"
    )


def dedupe_preserve_order(item_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for iid in item_ids:
        if not iid or iid in seen:
            continue
        seen.add(iid)
        out.append(iid)
    return out


def inventory_item_ids_from_save(save_data: SaveData | None) -> list[str]:
    """Backpack + storage item ids (deduped) for LLM stash context."""
    if save_data is None:
        return []
    ids: list[str] = []
    for row in save_data.inventory_backpack:
        ids.append(row.item_id)
    for row in save_data.inventory_storage:
        ids.append(row.item_id)
    return dedupe_preserve_order(ids)


def stash_text_for_team_prompt(item_ids: list[str], *, max_items: int = 55) -> str:
    """Compact backpack/storage listing for LLM team composition (wiki slot + effect)."""
    lines: list[str] = []
    for iid in item_ids[:max_items]:
        slot = item_slot_for_id(iid)
        eff = item_effect_for_id(iid)
        slot_b = f" [{slot}]" if slot else ""
        if eff:
            short = eff if len(eff) <= 130 else eff[:127] + "..."
            lines.append(f"- {iid}{slot_b}: {short}")
        else:
            lines.append(f"- {iid}{slot_b}")
    if len(item_ids) > max_items:
        lines.append(f"... ({len(item_ids) - max_items} more item ids omitted)")
    return "\n".join(lines)


def _normalize_inventory_tips(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[:10]:
        if isinstance(item, str) and item.strip():
            out.append({"item_id": "", "equip_on": "", "reason": item.strip()})
            continue
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "item_id": str(item.get("item_id", "")).strip(),
                "equip_on": str(item.get("equip_on", "")).strip(),
                "reason": str(item.get("reason", "")).strip(),
            }
        )
    return out


def team_synergy_ui_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Structured payload for WebChannel: synergy text + stash tips with wiki icons.

    Each tip merges LLM fields with ``item_effect_entry`` (icon_url, slot, effect).
    """
    synergy = str(result.get("synergy", "")).strip()
    raw_tips = result.get("inventory_tips")
    tips_out: list[dict[str, Any]] = []
    if isinstance(raw_tips, list):
        for tip in raw_tips[:12]:
            if not isinstance(tip, dict):
                continue
            iid = str(tip.get("item_id", "")).strip()
            if not iid:
                continue
            meta = item_effect_entry(iid)
            tips_out.append(
                {
                    "item_id": iid,
                    "equip_on": str(tip.get("equip_on", "")).strip(),
                    "reason": str(tip.get("reason", "")).strip(),
                    "icon_url": meta.get("icon_url"),
                    "slot": meta.get("slot"),
                    "effect": meta.get("effect"),
                }
            )
    return {"synergy": synergy, "stash_tips": tips_out}


def format_team_llm_synergy_text(result: dict[str, Any]) -> str:
    """Merge synergy paragraph and optional stash tips for plain-text tooltips (Qt overlay)."""
    synergy = str(result.get("synergy", "")).strip()
    tips = result.get("inventory_tips")
    lines: list[str] = []
    if synergy:
        lines.append(synergy)
    if isinstance(tips, list) and tips:
        lines.append("")
        lines.append("Stash / loadout ideas:")
        for tip in tips:
            if not isinstance(tip, dict):
                continue
            iid = str(tip.get("item_id", "")).strip()
            who = str(tip.get("equip_on", "")).strip()
            reason = str(tip.get("reason", "")).strip()
            if not iid and not reason:
                continue
            who_bit = f" → {who}" if who else ""
            if iid:
                lines.append(
                    f"• {iid}{who_bit}: {reason}" if reason else f"• {iid}{who_bit}"
                )
            elif reason:
                lines.append(f"• {reason}")
    return "\n".join(lines)


class LLMAdvisor:
    """Advisor for class scoring, team synergy, and explanations.

    Supports three modes:
    - Real: Uses OpenAI API (saved key in overlay data dir or OPENAI_API_KEY)
    - Mock: Returns realistic fake data with simulated latency (for dev/demo)
    - Disabled: Returns empty/None for all methods
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        enabled: bool = True,
        mock: bool = False,
        user_api_key: str | None = None,
    ) -> None:
        self._model = model
        self._cfg_llm_enabled = enabled
        self._mock = mock
        self._user_api_key = user_api_key
        self._client: Any = None
        self._wiki_context: str = ""
        self._breeding_context: str = ""
        self._explanation_cache: dict[str, str] = {}
        self._connection_check: str = "idle"
        self._connection_message: str = ""

        if not enabled:
            log.info("LLM advisor disabled in config")
            return

        if mock:
            log.info("LLM advisor running in MOCK mode")
            return

        self._init_live_client()

    def _init_live_client(self) -> None:
        self._client = None
        api_key = (self._user_api_key or "").strip() or os.environ.get(
            "OPENAI_API_KEY", ""
        )
        if not api_key:
            log.warning(
                "No OpenAI API key (overlay settings or OPENAI_API_KEY) — LLM advisor inactive"
            )
            return
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
            if not self._wiki_context:
                self._wiki_context = _load_wiki_context()
            if not self._breeding_context:
                self._breeding_context = _load_breeding_context()
            log.info("LLM advisor ready (model=%s)", self._model)
        except Exception:
            log.exception("Failed to initialize OpenAI client")
            self._client = None

    def apply_ui_settings(
        self,
        *,
        default_model: str,
        model: str,
        key_action: str,
        key_value: str,
    ) -> None:
        from src.utils.llm_user_store import UserLlm, save_user_llm

        self._model = model.strip() or default_model
        if key_action == "set":
            self._user_api_key = key_value.strip() or None
            if not key_value.strip():
                self._connection_check = "idle"
                self._connection_message = ""
        elif key_action == "clear":
            self._user_api_key = None
            self._connection_check = "idle"
            self._connection_message = ""

        save_user_llm(
            UserLlm(
                model=self._model,
                api_key=self._user_api_key,
            )
        )
        self.clear_cache()

        if not self._cfg_llm_enabled or self._mock:
            return

        self._init_live_client()

    def settings_snapshot(self, *, default_model: str) -> dict[str, Any]:
        models = list(OPENAI_MODEL_CHOICES)
        if self._model not in models:
            models.insert(0, self._model)
        return {
            "model": self._model,
            "default_model": default_model,
            "models": models,
            "has_saved_key": bool(self._user_api_key),
            "available": self.available,
            "mock": self._mock,
            "enabled": self._cfg_llm_enabled,
            "connection_check": self._connection_check,
            "connection_message": self._connection_message,
        }

    def effective_api_key(self) -> str | None:
        k = (self._user_api_key or "").strip() or os.environ.get(
            "OPENAI_API_KEY", ""
        ).strip()
        return k or None

    def connection_idle(self) -> None:
        self._connection_check = "idle"
        self._connection_message = ""

    def connection_set_pending(self) -> None:
        self._connection_check = "pending"
        self._connection_message = ""

    def connection_set_result(self, ok: bool, message: str = "") -> None:
        if ok:
            self._connection_check = "ok"
            self._connection_message = ""
        else:
            self._connection_check = "failed"
            self._connection_message = message or "Could not verify OpenAI connection."

    def can_verify_openai(self) -> bool:
        """True when real API (not mock/disabled); used for connection test worker."""
        return self._cfg_llm_enabled and not self._mock

    @property
    def available(self) -> bool:
        if not self._cfg_llm_enabled:
            return False
        if self._mock:
            return True
        return self._client is not None

    def _chat(
        self, messages: list[dict[str, str]], temperature: float = 0.3
    ) -> str | None:
        if not self.available or self._mock:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=1500,
            )
            return resp.choices[0].message.content
        except Exception:
            log.exception("LLM request failed")
            return None

    # ── Ability-aware scoring ────────────────────────────────────────

    def adjust_scores_for_abilities(
        self,
        cat: "SaveCat",
        base_scores: list[tuple[CollarDef, float]],
    ) -> dict[str, float]:
        """Return per-class score adjustments based on ability synergy.

        Returns a dict mapping collar name -> adjustment (-2.0 to +2.0).
        Empty dict if LLM unavailable.
        """
        if not self.available or not cat.abilities:
            return {}

        if self._mock:
            return self._mock_ability_adjustments(cat, base_scores)

        collar_list = ", ".join(f"{c.name} ({s:.1f})" for c, s in base_scores)
        prompt = (
            f"Analyze this cat's abilities for class synergy.\n\n"
            f"Cat: {_cat_summary(cat)}\n\n"
            f"Base scores: {collar_list}\n\n"
            f"Game context:\n{self._wiki_context}\n\n"
            f"For each class, provide a score adjustment between -2.0 and +2.0 "
            f"based on how well the cat's abilities synergize with that class. "
            f"Respond with ONLY a JSON object mapping class name to float adjustment. "
            f'Example: {{"Fighter": 0.5, "Mage": -1.0, ...}}'
        )

        raw = self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        if not raw:
            return {}

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(raw)
            return {
                k: max(-2.0, min(2.0, float(v)))
                for k, v in result.items()
                if isinstance(v, (int, float))
            }
        except (json.JSONDecodeError, ValueError):
            log.warning("Failed to parse ability adjustment response")
            return {}

    def _mock_ability_adjustments(
        self,
        cat: "SaveCat",
        base_scores: list[tuple[CollarDef, float]],
    ) -> dict[str, float]:
        rng = random.Random(cat.db_key)
        return {c.name: round(rng.uniform(-0.8, 1.2), 1) for c, _ in base_scores}

    # ── Team synergy ─────────────────────────────────────────────────

    def suggest_team_composition(
        self,
        cats: list["SaveCat"],
        collars: list["CollarDef"],
        base_scores: dict[int, list[tuple["CollarDef", float]]],
        *,
        inventory_item_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Suggest a balanced 4-cat team using LLM reasoning.

        Returns dict with keys:
          - "team": list of 4 dicts (cat_name, cat_db_key, collar_name, reason)
          - "synergy": 1-2 sentence team synergy analysis
          - "inventory_tips": optional list of {item_id, equip_on, reason} stash ideas
        Returns None if LLM unavailable.
        """
        if not self.available or len(cats) < 2:
            return None

        stash_ids = dedupe_preserve_order(inventory_item_ids or [])

        if self._mock:
            return self._mock_team_composition(
                cats, collars, base_scores, stash_ids=stash_ids
            )

        cat_summaries = "\n".join(_cat_summary(c) for c in cats[:20])
        collar_names = [c.name for c in collars]

        top_per_cat: list[str] = []
        for cat in cats[:20]:
            scores = base_scores.get(cat.db_key, [])
            top3 = sorted(scores, key=lambda x: x[1], reverse=True)[:3]
            top_str = ", ".join(f"{c.name}={s:.1f}" for c, s in top3)
            top_per_cat.append(f"  {cat.name} (key={cat.db_key}): {top_str}")

        stash_block = ""
        stash_rules = ""
        if stash_ids:
            stash_block = (
                "\nItems in backpack + storage (not necessarily equipped on anyone):\n"
                f"{stash_text_for_team_prompt(stash_ids)}\n"
            )
            stash_rules = (
                "\n- After choosing the team, pick up to 5 items from that stash list "
                "that especially fit the comp (cover weak stats, duplicate resist themes, "
                "or fill an open wiki slot type the team lacks). "
                'Use JSON key "inventory_tips": array of objects with item_id (must match '
                'a line above), equip_on (exact cat name from your team, or "flex"), '
                "reason (short). Use [] if nothing stands out. "
                "Skip items you cannot justify from stats/effects.\n"
            )

        prompt = (
            f"Select the best 4-cat team from these cats.\n\n"
            f"Available cats:\n{cat_summaries}\n\n"
            f"Top class scores per cat:\n" + "\n".join(top_per_cat) + "\n\n"
            f"Available classes: {', '.join(collar_names)}\n\n"
            f"{stash_block}"
            f"Game context:\n{self._wiki_context}\n\n"
            f"Rules:\n"
            f"- Pick exactly 4 different cats with different classes\n"
            f"- Balance the team: include a tank/frontliner, a healer/support, "
            f"and damage dealers where possible\n"
            f"- Each cat should be assigned their best-fitting class\n"
            f"- Consider ability synergies if abilities are listed\n"
            f"- Consider passive trait synergies and how they complement the team\n"
            f"- Equipment lines use [Weapon]/[Head]/[Trinket]/etc. from the wiki Slot column"
            f" when known{stash_rules}\n"
            f"Respond with ONLY a JSON object with keys:\n"
            f'  "team": array of 4 objects, each with cat_name (str), '
            f"cat_db_key (int), collar_name (str), reason (1 sentence)\n"
            f'  "synergy": 1-2 sentences analyzing the chosen team\'s '
            f"class/passive interactions and overall balance\n"
            f'  "inventory_tips": array (see rules above; use [] if no stash or no picks)\n'
        )

        raw = self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        if not raw:
            return None

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(raw)

            if isinstance(result, list):
                return {"team": result[:4], "synergy": "", "inventory_tips": []}
            if isinstance(result, dict):
                team = result.get("team", [])
                if not isinstance(team, list) or len(team) == 0:
                    return None
                tips = _normalize_inventory_tips(result.get("inventory_tips"))
                if stash_ids:
                    allowed = set(stash_ids)
                    tips = [t for t in tips if t.get("item_id") in allowed]
                else:
                    tips = []
                return {
                    "team": team[:4],
                    "synergy": str(result.get("synergy", "")),
                    "inventory_tips": tips,
                }
            return None
        except (json.JSONDecodeError, ValueError):
            log.warning("Failed to parse team composition response")
            return None

    def _mock_team_composition(
        self,
        cats: list["SaveCat"],
        collars: list["CollarDef"],
        base_scores: dict[int, list[tuple["CollarDef", float]]],
        *,
        stash_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        time.sleep(0.8)

        desired_roles = ["Tank", "Cleric", "Fighter", "Mage"]
        collar_by_name = {c.name: c for c in collars}
        available_roles = [r for r in desired_roles if r in collar_by_name]
        if len(available_roles) < 4:
            extra = [c.name for c in collars if c.name not in available_roles]
            available_roles.extend(extra[: 4 - len(available_roles)])

        used_cats: set[int] = set()
        team: list[dict[str, Any]] = []

        for role in available_roles[:4]:
            best_cat = None
            best_score = -999.0
            for cat in cats:
                if cat.db_key in used_cats:
                    continue
                scores = base_scores.get(cat.db_key, [])
                for collar, score in scores:
                    if collar.name == role and score > best_score:
                        best_score = score
                        best_cat = cat

            if best_cat is None:
                continue

            tag = _ROLE_TAGS.get(role, "specialist")
            passive_note = ""
            if best_cat.passives:
                passive_note = f" Passive '{best_cat.passives[0]}' adds extra value."
            team.append(
                {
                    "cat_name": best_cat.name,
                    "cat_db_key": best_cat.db_key,
                    "collar_name": role,
                    "reason": f"Best {tag} candidate with a score of {best_score:.1f}.{passive_note}",
                }
            )
            used_cats.add(best_cat.db_key)

        role_list = " + ".join(
            _ROLE_TAGS.get(e["collar_name"], e["collar_name"]) for e in team
        )
        synergy = (
            f"Balanced composition with {role_list}. "
            f"Passives complement the team's frontline and support roles."
        )

        tips: list[dict[str, str]] = []
        if stash_ids and team:
            pick = stash_ids[0]
            tips.append(
                {
                    "item_id": pick,
                    "equip_on": str(team[0].get("cat_name", "flex")),
                    "reason": "Mock tip: consider equipping from stash for this comp.",
                }
            )

        return {"team": team, "synergy": synergy, "inventory_tips": tips}

    # ── Explanations ─────────────────────────────────────────────────

    def explain_recommendation(
        self,
        cat: "SaveCat",
        collar: "CollarDef",
        score: float,
    ) -> str | None:
        """Generate a 1-2 sentence explanation for a cat-class pairing.

        Results are cached by (cat.db_key, collar.name).
        Returns None if LLM unavailable.
        """
        cache_key = f"{cat.db_key}:{collar.name}"
        if cache_key in self._explanation_cache:
            return self._explanation_cache[cache_key]

        if not self.available:
            return None

        if self._mock:
            return self._mock_explanation(cat, collar, score)

        prompt = (
            f"Explain why this cat is a good or bad fit for this class. "
            f"Be concise (1-2 sentences).\n\n"
            f"Cat: {_cat_summary(cat)}\n"
            f"Class: {collar.name} (score: {score:.1f})\n"
            f"Class modifiers: {collar.modifiers}\n\n"
            f"Game context:\n{self._wiki_context}\n\n"
            f"Respond with ONLY the explanation text, no JSON."
        )

        raw = self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        if raw:
            explanation = raw.strip()[:200]
            self._explanation_cache[cache_key] = explanation
            return explanation
        return None

    def _mock_explanation(
        self,
        cat: "SaveCat",
        collar: "CollarDef",
        score: float,
    ) -> str:
        time.sleep(0.3)

        stat_map = {
            "STR": cat.base_str,
            "DEX": cat.base_dex,
            "CON": cat.base_con,
            "INT": cat.base_int,
            "SPD": cat.base_spd,
            "CHA": cat.base_cha,
            "LCK": cat.base_lck,
        }
        best_stat = max(stat_map, key=lambda k: stat_map[k])
        worst_stat = min(stat_map, key=lambda k: stat_map[k])
        ability = cat.abilities[0] if cat.abilities else "their base stats"
        role = _ROLE_TAGS.get(collar.name, "specialist")

        rng = random.Random(cat.db_key + hash(collar.name))
        template = rng.choice(_MOCK_EXPLANATIONS)
        explanation = template.format(
            stat=best_stat,
            role=role,
            ability=ability,
            weak=worst_stat,
        )
        self._explanation_cache[f"{cat.db_key}:{collar.name}"] = explanation
        return explanation

    def clear_cache(self) -> None:
        self._explanation_cache.clear()

    # ── Breeding advice ──────────────────────────────────────────────

    def suggest_breeding_pairs(
        self,
        cats: list["SaveCat"],
        collar_name: str,
        stimulation: int = 0,
        room_stats: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        """Suggest top breeding pairs for a target class using LLM reasoning.

        Returns list of dicts with keys: cat_a_name, cat_a_key, cat_b_name,
        cat_b_key, reason. Returns None if LLM unavailable.
        """
        if not self.available or len(cats) < 2:
            return None

        if self._mock:
            return self._mock_breeding_pairs(cats, collar_name)

        cat_summaries = "\n".join(
            f"  {_cat_summary(c)} | gender={c.gender} "
            f"| inbreeding={c.breed_coefficient:.2f} | room={c.room}"
            for c in cats[:20]
        )

        room_context = ""
        if room_stats:
            room_lines = "\n".join(
                f"  {name}: appeal={rs.appeal} comfort={rs.comfort} "
                f"effective_comfort={rs.effective_comfort} "
                f"stimulation={rs.stimulation} health={rs.health} "
                f"mutation={rs.mutation} cats={rs.cat_count}"
                for name, rs in room_stats.items()
            )
            room_context = f"Room stats:\n{room_lines}\n\n"

        prompt = (
            f"Suggest the best 3 breeding pairs to produce a strong {collar_name} offspring.\n\n"
            f"Stimulation level (override): {stimulation}\n\n"
            f"Available cats:\n{cat_summaries}\n\n"
            f"{room_context}"
            f"Breeding mechanics:\n{self._breeding_context}\n\n"
            f"Class info:\n{self._wiki_context}\n\n"
            f"Rules:\n"
            f"- Each pair must be different genders (male + female)\n"
            f"- Prioritize parents whose stats align with {collar_name} class weights\n"
            f"- Consider ability inheritance -- class abilities are valuable\n"
            f"- Prefer lower inbreeding coefficients when possible (better defect/disorder odds); "
            f"if both parents are high, flag the risk and note that some players accept it to consolidate stats\n"
            f"- Consider room Stimulation thresholds for guaranteed inheritance\n"
            f"- effective_comfort = comfort - max(0, cats - 4); higher means better breeding odds\n\n"
            f"Respond with ONLY a JSON array of 3 objects, each with:\n"
            f"  cat_a_name (str), cat_a_key (int), cat_b_name (str), "
            f"cat_b_key (int), reason (1-2 sentences)\n"
        )

        raw = self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        if not raw:
            return None

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(raw)
            if not isinstance(result, list) or len(result) == 0:
                return None
            return result[:5]
        except (json.JSONDecodeError, ValueError):
            log.warning("Failed to parse breeding pairs response")
            return None

    def _mock_breeding_pairs(
        self,
        cats: list["SaveCat"],
        collar_name: str,
    ) -> list[dict[str, Any]]:
        time.sleep(0.6)

        males = [c for c in cats if c.gender == "male"]
        females = [c for c in cats if c.gender == "female"]
        if not males or not females:
            males = cats[: len(cats) // 2]
            females = cats[len(cats) // 2 :]

        rng = random.Random(hash(collar_name))
        result: list[dict[str, Any]] = []
        used: set[int] = set()

        for _ in range(min(3, len(males), len(females))):
            m = rng.choice([c for c in males if c.db_key not in used] or males)
            f = rng.choice([c for c in females if c.db_key not in used] or females)
            used.add(m.db_key)
            used.add(f.db_key)
            role = _ROLE_TAGS.get(collar_name, "specialist")
            result.append(
                {
                    "cat_a_name": m.name,
                    "cat_a_key": m.db_key,
                    "cat_b_name": f.name,
                    "cat_b_key": f.db_key,
                    "reason": f"Strong stat complementarity for {role} offspring.",
                }
            )
        return result

    def explain_breeding_pair(
        self,
        cat_a: "SaveCat",
        cat_b: "SaveCat",
        collar_name: str,
        stimulation: int = 0,
    ) -> str | None:
        """Generate a detailed explanation of a breeding pair's potential.

        Returns None if LLM unavailable.
        """
        cache_key = f"breed:{cat_a.db_key}:{cat_b.db_key}:{collar_name}:{stimulation}"
        if cache_key in self._explanation_cache:
            return self._explanation_cache[cache_key]

        if not self.available:
            return None

        if self._mock:
            return self._mock_breeding_explanation(cat_a, cat_b, collar_name)

        prompt = (
            f"Explain this breeding pair's potential for producing a {collar_name} offspring.\n\n"
            f"Parent A: {_cat_summary(cat_a)} | inbreeding={cat_a.breed_coefficient:.2f}\n"
            f"Parent B: {_cat_summary(cat_b)} | inbreeding={cat_b.breed_coefficient:.2f}\n"
            f"Stimulation: {stimulation}\n\n"
            f"Breeding mechanics:\n{self._breeding_context}\n\n"
            f"Analyze:\n"
            f"1. Stat inheritance outlook for {collar_name}\n"
            f"2. Ability inheritance potential\n"
            f"3. Inbreeding risk (defect/disorder odds vs aggressive-lineage tradeoffs)\n"
            f"4. Key tips for this Stimulation level\n\n"
            f"Respond with ONLY 2-4 sentences of explanation, no JSON."
        )

        raw = self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        if raw:
            explanation = raw.strip()[:400]
            self._explanation_cache[cache_key] = explanation
            return explanation
        return None

    def _mock_breeding_explanation(
        self,
        cat_a: "SaveCat",
        cat_b: "SaveCat",
        collar_name: str,
    ) -> str:
        time.sleep(0.4)

        stat_a = {
            "STR": cat_a.base_str,
            "DEX": cat_a.base_dex,
            "CON": cat_a.base_con,
            "INT": cat_a.base_int,
            "SPD": cat_a.base_spd,
            "CHA": cat_a.base_cha,
        }
        stat_b = {
            "STR": cat_b.base_str,
            "DEX": cat_b.base_dex,
            "CON": cat_b.base_con,
            "INT": cat_b.base_int,
            "SPD": cat_b.base_spd,
            "CHA": cat_b.base_cha,
        }
        best_a = max(stat_a, key=lambda k: stat_a[k])
        best_b = max(stat_b, key=lambda k: stat_b[k])
        role = _ROLE_TAGS.get(collar_name, "specialist")

        explanation = (
            f"{cat_a.name}'s high {best_a} complements {cat_b.name}'s strong {best_b}, "
            f"making their offspring promising {role} candidates. "
        )
        if cat_a.breed_coefficient > 0.2 or cat_b.breed_coefficient > 0.2:
            explanation += (
                "Higher inbreeding raises defect odds -- outcross with strays unless you are "
                "deliberately consolidating a line."
            )
        else:
            explanation += (
                "Lower inbreeding coefficients favor healthier offspring odds."
            )

        key = f"breed:{cat_a.db_key}:{cat_b.db_key}:{collar_name}:0"
        self._explanation_cache[key] = explanation
        return explanation

    # ── Room distribution ─────────────────────────────────────────────

    def suggest_room_distribution(
        self,
        cats: list["SaveCat"],
        room_stats: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Ask LLM to suggest optimal cat placement across rooms.

        Returns a dict matching RoomDistribution shape:
          { rooms: [...RoomAssignment], total_score: float }
        Returns None if LLM unavailable.
        """
        if not self.available or len(cats) < 2:
            return None

        if self._mock:
            return self._mock_room_distribution(cats, room_stats)

        cat_summaries = "\n".join(
            f"  key={c.db_key} {_cat_summary(c)} | gender={c.gender} "
            f"| inbreeding={c.breed_coefficient:.2f} | room={c.room}"
            for c in cats[:50]
        )

        room_info = "\n".join(
            f"  {name}: appeal={rs.appeal} comfort={rs.comfort} "
            f"effective_comfort={rs.effective_comfort} "
            f"stimulation={rs.stimulation} health={rs.health} "
            f"mutation={rs.mutation} cats={rs.cat_count}"
            for name, rs in room_stats.items()
        )

        prompt = (
            f"Suggest the best cat-to-room distribution for overnight breeding.\n\n"
            f"Available cats:\n{cat_summaries}\n\n"
            f"Rooms:\n{room_info}\n\n"
            f"Breeding mechanics:\n{self._breeding_context}\n\n"
            f"Rules:\n"
            f"- Each room should ideally have one male + one female for breeding\n"
            f"- Pair cats with complementary stats (high + high preferred)\n"
            f"- Place best pairs in rooms with highest stimulation\n"
            f"- effective_comfort = comfort - max(0, cats - 4); higher means better breeding odds\n"
            f"- Prefer lower inbreeding pairings when possible; if unavoidable, acknowledge the tradeoff\n"
            f"- Maximize total expected offspring stat sum across all rooms\n\n"
            f"Respond with ONLY a JSON object:\n"
            f'{{"rooms": [{{"room_name": "...", "cat_keys": [int, ...], '
            f'"best_pair": [int, int] or null, "pair_score": float, '
            f'"pair_reason": "1 sentence"}}, ...], '
            f'"total_score": float}}\n'
        )

        raw = self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        if not raw:
            return None

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(raw)
            if isinstance(result, dict) and "rooms" in result:
                return result
            return None
        except (json.JSONDecodeError, ValueError):
            log.warning("Failed to parse room distribution response")
            return None

    def _mock_room_distribution(
        self,
        cats: list["SaveCat"],
        room_stats: dict[str, Any],
    ) -> dict[str, Any]:
        time.sleep(0.7)

        from src.breeding.calculator import suggest_room_distribution as calc_dist
        from dataclasses import asdict

        dist = calc_dist(cats, room_stats)
        result = asdict(dist)
        for room in result["rooms"]:
            if room["best_pair"]:
                room["pair_reason"] = "AI: " + room["pair_reason"]
        return result


def build_llm_advisor(cfg: "LLMConfig") -> LLMAdvisor:
    from src.utils.llm_user_store import load_user_llm

    user = load_user_llm()
    model = user.model if user.model else cfg.model
    return LLMAdvisor(
        model=model,
        enabled=cfg.enabled,
        mock=cfg.mock,
        user_api_key=user.api_key,
    )
