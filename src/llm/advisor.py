from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.data.collars import CollarDef
    from src.data.save_reader import SaveCat

log = logging.getLogger("mewgent.llm.advisor")

_WIKI_DIR = Path(__file__).resolve().parents[2] / "wiki_data" / "text"

_SYSTEM_PROMPT = """\
You are an expert advisor for the game Mewgenics. You analyze cat stats, \
abilities, and class mechanics to recommend optimal class assignments and \
team compositions. Always respond with valid JSON matching the requested schema.\
"""


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


def _cat_summary(cat: SaveCat) -> str:
    stats = (
        f"STR={cat.base_str} DEX={cat.base_dex} CON={cat.base_con} "
        f"INT={cat.base_int} SPD={cat.base_spd} CHA={cat.base_cha} LCK={cat.base_lck}"
    )
    abilities = ", ".join(cat.abilities) if cat.abilities else "none"
    return f"{cat.name} (Lv{cat.level}, Age{cat.age}): {stats} | abilities: {abilities}"


class LLMAdvisor:
    """OpenAI-powered advisor for class scoring, team synergy, and explanations.

    Gracefully degrades to None/empty results if the API key is missing or
    the LLM is disabled in config.
    """

    def __init__(self, *, model: str = "gpt-4o-mini", enabled: bool = True) -> None:
        self._model = model
        self._enabled = enabled
        self._client: Any = None
        self._wiki_context: str = ""
        self._explanation_cache: dict[str, str] = {}

        if not enabled:
            log.info("LLM advisor disabled in config")
            return

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            log.warning("OPENAI_API_KEY not set -- LLM advisor disabled")
            self._enabled = False
            return

        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._wiki_context = _load_wiki_context()
            log.info("LLM advisor ready (model=%s)", model)
        except Exception:
            log.exception("Failed to initialize OpenAI client")
            self._enabled = False

    @property
    def available(self) -> bool:
        return self._enabled and self._client is not None

    def _chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str | None:
        if not self.available:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=1500,
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

        collar_list = ", ".join(f"{c.name} ({s:.1f})" for c, s in base_scores)
        prompt = (
            f"Analyze this cat's abilities for class synergy.\n\n"
            f"Cat: {_cat_summary(cat)}\n\n"
            f"Base scores: {collar_list}\n\n"
            f"Game context:\n{self._wiki_context}\n\n"
            f"For each class, provide a score adjustment between -2.0 and +2.0 "
            f"based on how well the cat's abilities synergize with that class. "
            f"Respond with ONLY a JSON object mapping class name to float adjustment. "
            f"Example: {{\"Fighter\": 0.5, \"Mage\": -1.0, ...}}"
        )

        raw = self._chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
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

    # ── Team synergy ─────────────────────────────────────────────────

    def suggest_team_composition(
        self,
        cats: list["SaveCat"],
        collars: list["CollarDef"],
        base_scores: dict[int, list[tuple["CollarDef", float]]],
    ) -> list[dict[str, Any]] | None:
        """Suggest a balanced 4-cat team using LLM reasoning.

        Args:
            cats: Available house cats.
            collars: Unlocked collars.
            base_scores: Mapping from cat db_key to list of (collar, score) pairs.

        Returns list of 4 dicts with keys: cat_name, cat_db_key, collar_name,
        score, reason. Returns None if LLM unavailable.
        """
        if not self.available or len(cats) < 2:
            return None

        cat_summaries = "\n".join(_cat_summary(c) for c in cats[:20])
        collar_names = [c.name for c in collars]

        top_per_cat: list[str] = []
        for cat in cats[:20]:
            scores = base_scores.get(cat.db_key, [])
            top3 = sorted(scores, key=lambda x: x[1], reverse=True)[:3]
            top_str = ", ".join(f"{c.name}={s:.1f}" for c, s in top3)
            top_per_cat.append(f"  {cat.name} (key={cat.db_key}): {top_str}")

        prompt = (
            f"Select the best 4-cat team from these cats.\n\n"
            f"Available cats:\n{cat_summaries}\n\n"
            f"Top class scores per cat:\n" + "\n".join(top_per_cat) + "\n\n"
            f"Available classes: {', '.join(collar_names)}\n\n"
            f"Game context:\n{self._wiki_context}\n\n"
            f"Rules:\n"
            f"- Pick exactly 4 different cats with different classes\n"
            f"- Balance the team: include a tank/frontliner, a healer/support, "
            f"and damage dealers where possible\n"
            f"- Each cat should be assigned their best-fitting class\n"
            f"- Consider ability synergies if abilities are listed\n\n"
            f"Respond with ONLY a JSON array of 4 objects, each with:\n"
            f"  cat_name (str), cat_db_key (int), collar_name (str), "
            f"reason (1 sentence)\n"
        )

        raw = self._chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ], temperature=0.2)
        if not raw:
            return None

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(raw)
            if not isinstance(result, list) or len(result) == 0:
                return None
            return result[:4]
        except (json.JSONDecodeError, ValueError):
            log.warning("Failed to parse team composition response")
            return None

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

        prompt = (
            f"Explain why this cat is a good or bad fit for this class. "
            f"Be concise (1-2 sentences).\n\n"
            f"Cat: {_cat_summary(cat)}\n"
            f"Class: {collar.name} (score: {score:.1f})\n"
            f"Class modifiers: {collar.modifiers}\n\n"
            f"Game context:\n{self._wiki_context}\n\n"
            f"Respond with ONLY the explanation text, no JSON."
        )

        raw = self._chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ], temperature=0.4)
        if raw:
            explanation = raw.strip()[:200]
            self._explanation_cache[cache_key] = explanation
            return explanation
        return None

    def clear_cache(self) -> None:
        self._explanation_cache.clear()
