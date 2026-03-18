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
    from src.data.save_reader import SaveCat

log = logging.getLogger("mewgent.llm.advisor")

_WIKI_DIR = Path(__file__).resolve().parents[2] / "wiki_data" / "text"

_SYSTEM_PROMPT = """\
You are an expert advisor for the game Mewgenics. You analyze cat stats, \
abilities, and class mechanics to recommend optimal class assignments and \
team compositions. You also provide breeding advice based on inheritance \
mechanics, house stats, and inbreeding risks. Always respond with valid \
JSON matching the requested schema.\
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
    """Load breeding mechanics wiki data for LLM context."""
    path = _WIKI_DIR / "breeding.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if len(text) > 15000:
            text = text[:15000] + "\n[... truncated]"
        return text
    return ""


def _cat_summary(cat: SaveCat) -> str:
    stats = (
        f"STR={cat.base_str} DEX={cat.base_dex} CON={cat.base_con} "
        f"INT={cat.base_int} SPD={cat.base_spd} CHA={cat.base_cha} LCK={cat.base_lck}"
    )
    abilities = ", ".join(cat.abilities) if cat.abilities else "none"
    return f"{cat.name} (Lv{cat.level}, Age{cat.age}): {stats} | abilities: {abilities}"


class LLMAdvisor:
    """Advisor for class scoring, team synergy, and explanations.

    Supports three modes:
    - Real: Uses OpenAI API (requires OPENAI_API_KEY)
    - Mock: Returns realistic fake data with simulated latency (for dev/demo)
    - Disabled: Returns empty/None for all methods
    """

    def __init__(
        self, *, model: str = "gpt-4o-mini", enabled: bool = True, mock: bool = False,
    ) -> None:
        self._model = model
        self._enabled = enabled
        self._mock = mock
        self._client: Any = None
        self._wiki_context: str = ""
        self._breeding_context: str = ""
        self._explanation_cache: dict[str, str] = {}

        if not enabled:
            log.info("LLM advisor disabled in config")
            return

        if mock:
            self._enabled = True
            log.info("LLM advisor running in MOCK mode")
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
            self._breeding_context = _load_breeding_context()
            log.info("LLM advisor ready (model=%s)", model)
        except Exception:
            log.exception("Failed to initialize OpenAI client")
            self._enabled = False

    @property
    def available(self) -> bool:
        if self._mock:
            return self._enabled
        return self._enabled and self._client is not None

    def _chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str | None:
        if not self.available or self._mock:
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

    def _mock_ability_adjustments(
        self,
        cat: "SaveCat",
        base_scores: list[tuple[CollarDef, float]],
    ) -> dict[str, float]:
        rng = random.Random(cat.db_key)
        return {
            c.name: round(rng.uniform(-0.8, 1.2), 1)
            for c, _ in base_scores
        }

    # ── Team synergy ─────────────────────────────────────────────────

    def suggest_team_composition(
        self,
        cats: list["SaveCat"],
        collars: list["CollarDef"],
        base_scores: dict[int, list[tuple["CollarDef", float]]],
    ) -> list[dict[str, Any]] | None:
        """Suggest a balanced 4-cat team using LLM reasoning.

        Returns list of 4 dicts with keys: cat_name, cat_db_key, collar_name,
        score, reason. Returns None if LLM unavailable.
        """
        if not self.available or len(cats) < 2:
            return None

        if self._mock:
            return self._mock_team_composition(cats, collars, base_scores)

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

    def _mock_team_composition(
        self,
        cats: list["SaveCat"],
        collars: list["CollarDef"],
        base_scores: dict[int, list[tuple["CollarDef", float]]],
    ) -> list[dict[str, Any]]:
        time.sleep(0.8)

        desired_roles = ["Tank", "Cleric", "Fighter", "Mage"]
        collar_by_name = {c.name: c for c in collars}
        available_roles = [r for r in desired_roles if r in collar_by_name]
        if len(available_roles) < 4:
            extra = [c.name for c in collars if c.name not in available_roles]
            available_roles.extend(extra[:4 - len(available_roles)])

        used_cats: set[int] = set()
        result: list[dict[str, Any]] = []

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
            result.append({
                "cat_name": best_cat.name,
                "cat_db_key": best_cat.db_key,
                "collar_name": role,
                "reason": f"Best {tag} candidate with a score of {best_score:.1f}.",
            })
            used_cats.add(best_cat.db_key)

        return result

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

        raw = self._chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ], temperature=0.4)
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
            "STR": cat.base_str, "DEX": cat.base_dex, "CON": cat.base_con,
            "INT": cat.base_int, "SPD": cat.base_spd, "CHA": cat.base_cha,
            "LCK": cat.base_lck,
        }
        best_stat = max(stat_map, key=lambda k: stat_map[k])
        worst_stat = min(stat_map, key=lambda k: stat_map[k])
        ability = cat.abilities[0] if cat.abilities else "their base stats"
        role = _ROLE_TAGS.get(collar.name, "specialist")

        rng = random.Random(cat.db_key + hash(collar.name))
        template = rng.choice(_MOCK_EXPLANATIONS)
        explanation = template.format(
            stat=best_stat, role=role, ability=ability, weak=worst_stat,
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
            f"  {_cat_summary(c)} | inbreeding={c.breed_coefficient:.2f}"
            for c in cats[:20]
        )

        prompt = (
            f"Suggest the best 3 breeding pairs to produce a strong {collar_name} offspring.\n\n"
            f"Stimulation level: {stimulation}\n\n"
            f"Available cats:\n{cat_summaries}\n\n"
            f"Breeding mechanics:\n{self._breeding_context}\n\n"
            f"Class info:\n{self._wiki_context}\n\n"
            f"Rules:\n"
            f"- Each pair must be different genders (male + female)\n"
            f"- Prioritize parents whose stats align with {collar_name} class weights\n"
            f"- Consider ability inheritance -- class abilities are valuable\n"
            f"- Flag inbreeding risks if both parents have high coefficients\n"
            f"- Consider Stimulation thresholds for guaranteed inheritance\n\n"
            f"Respond with ONLY a JSON array of 3 objects, each with:\n"
            f"  cat_a_name (str), cat_a_key (int), cat_b_name (str), "
            f"cat_b_key (int), reason (1-2 sentences)\n"
        )

        raw = self._chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ], temperature=0.3)
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
            males = cats[:len(cats) // 2]
            females = cats[len(cats) // 2:]

        rng = random.Random(hash(collar_name))
        result: list[dict[str, Any]] = []
        used: set[int] = set()

        for _ in range(min(3, len(males), len(females))):
            m = rng.choice([c for c in males if c.db_key not in used] or males)
            f = rng.choice([c for c in females if c.db_key not in used] or females)
            used.add(m.db_key)
            used.add(f.db_key)
            role = _ROLE_TAGS.get(collar_name, "specialist")
            result.append({
                "cat_a_name": m.name,
                "cat_a_key": m.db_key,
                "cat_b_name": f.name,
                "cat_b_key": f.db_key,
                "reason": f"Strong stat complementarity for {role} offspring.",
            })
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
            f"3. Inbreeding risk\n"
            f"4. Key tips for this Stimulation level\n\n"
            f"Respond with ONLY 2-4 sentences of explanation, no JSON."
        )

        raw = self._chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ], temperature=0.4)
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
            "STR": cat_a.base_str, "DEX": cat_a.base_dex, "CON": cat_a.base_con,
            "INT": cat_a.base_int, "SPD": cat_a.base_spd, "CHA": cat_a.base_cha,
        }
        stat_b = {
            "STR": cat_b.base_str, "DEX": cat_b.base_dex, "CON": cat_b.base_con,
            "INT": cat_b.base_int, "SPD": cat_b.base_spd, "CHA": cat_b.base_cha,
        }
        best_a = max(stat_a, key=lambda k: stat_a[k])
        best_b = max(stat_b, key=lambda k: stat_b[k])
        role = _ROLE_TAGS.get(collar_name, "specialist")

        explanation = (
            f"{cat_a.name}'s high {best_a} complements {cat_b.name}'s strong {best_b}, "
            f"making their offspring promising {role} candidates. "
        )
        if cat_a.breed_coefficient > 0.2 or cat_b.breed_coefficient > 0.2:
            explanation += "Watch for inbreeding risk -- consider mixing in stray bloodlines."
        else:
            explanation += "Low inbreeding coefficients mean healthy offspring are likely."

        key = f"breed:{cat_a.db_key}:{cat_b.db_key}:{collar_name}:0"
        self._explanation_cache[key] = explanation
        return explanation
