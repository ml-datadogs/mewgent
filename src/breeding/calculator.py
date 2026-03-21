"""Deterministic breeding calculator based on Mewgenics wiki mechanics.

Implements the 13-step kitten birth process formulas for stat inheritance,
ability inheritance, inbreeding prediction, and pair ranking for target classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.collars import CollarDef
    from src.data.save_reader import SaveCat

STAT_KEYS = ("str", "dex", "con", "int", "spd", "cha", "lck")


@dataclass
class BreedingAdvice:
    """Result of analyzing a breeding pair."""

    cat_a_name: str
    cat_a_key: int
    cat_b_name: str
    cat_b_key: int
    stimulation: int

    # Per-stat probability of inheriting the higher parent's value
    stat_high_probs: dict[str, float]

    # Ability inheritance
    first_active_chance: float
    second_active_chance: float
    passive_chance: float

    # Offspring expected base stats (average of parents, weighted by stimulation)
    expected_stats: dict[str, float]

    # Inbreeding
    inbreeding_warning: str
    parent_a_coeff: float
    parent_b_coeff: float

    # Disorder inheritance (always 15% per parent, independent)
    disorder_chance_per_parent: float = 0.15

    # Tips based on thresholds
    tips: list[str] | None = None


@dataclass
class PairRanking:
    """A ranked breeding pair for a target class."""

    cat_a_key: int
    cat_a_name: str
    cat_b_key: int
    cat_b_name: str
    expected_score: float
    reason: str


def higher_stat_probability(stimulation: int) -> float:
    """Probability that the kitten inherits the HIGHER parent stat value.

    Formula from wiki: (1 + 0.01 * S) / (2 + 0.01 * S)
    At S=0: 50%, S=100: 66.7%, S=200: 75%
    """
    s = 0.01 * stimulation
    return (1.0 + s) / (2.0 + s)


def first_active_ability_chance(stimulation: int) -> float:
    """Chance of inheriting one active ability: 0.20 + 0.025 * S, capped at 1.0.

    Guaranteed at Stimulation >= 32.
    """
    return min(1.0, 0.20 + 0.025 * stimulation)


def second_active_ability_chance(stimulation: int) -> float:
    """Chance of a second active ability: 0.02 + 0.005 * S, capped at 1.0.

    Guaranteed at Stimulation >= 196.
    """
    return min(1.0, 0.02 + 0.005 * stimulation)


def passive_ability_chance(stimulation: int) -> float:
    """Chance of inheriting a passive ability: 0.05 + 0.01 * S, capped at 1.0.

    Guaranteed at Stimulation >= 95.
    """
    return min(1.0, 0.05 + 0.01 * stimulation)


def class_bias_chance(stimulation: int) -> float:
    """Chance that ability inheritance biases toward the parent with class abilities.

    Formula: min(0.01 * S, 1.0). At S>=100, guaranteed.
    """
    return min(1.0, max(0.0, 0.01 * stimulation))


def birth_defect_disorder_chance(inbreeding_coeff: float) -> float:
    """Probability of birth-defect disorder roll.

    0.02 + 0.4 * clamp(inbreeding_coefficient - 0.2, 0, 1)
    Minimum 2%, max 42%.
    """
    clamped = max(0.0, min(1.0, inbreeding_coeff - 0.2))
    return 0.02 + 0.4 * clamped


def birth_defect_parts_chance(inbreeding_coeff: float) -> float:
    """Probability of birth defect parts being applied.

    Condition: random < (inbreeding_coefficient * 1.5) AND coeff > 0.05
    """
    if inbreeding_coeff <= 0.05:
        return 0.0
    return min(1.0, inbreeding_coeff * 1.5)


def _inbreeding_warning(coeff_a: float, coeff_b: float) -> str:
    avg = (coeff_a + coeff_b) / 2
    if avg == 0.0:
        return "none"
    if avg < 0.15:
        return "low"
    if avg < 0.4:
        return "moderate"
    return "high"


def _expected_stat(val_a: int, val_b: int, high_prob: float) -> float:
    """Expected offspring stat value given both parents and higher-stat probability."""
    hi = max(val_a, val_b)
    lo = min(val_a, val_b)
    return hi * high_prob + lo * (1.0 - high_prob)


def _stimulation_tips(stimulation: int) -> list[str]:
    tips: list[str] = []
    if stimulation < 32:
        tips.append(
            f"Stimulation {stimulation} < 32: first active ability NOT guaranteed ({first_active_ability_chance(stimulation):.0%})"
        )
    else:
        tips.append("Stimulation 32+: first active ability guaranteed")

    if stimulation < 95:
        tips.append(
            f"Stimulation {stimulation} < 95: passive ability NOT guaranteed ({passive_ability_chance(stimulation):.0%})"
        )
    elif stimulation < 100:
        tips.append("Stimulation 95+: passive ability guaranteed")

    if stimulation >= 100:
        tips.append("Stimulation 100+: class ability parent bias guaranteed")

    if stimulation >= 196:
        tips.append("Stimulation 196+: second active ability guaranteed")
    elif stimulation >= 95:
        tips.append(
            f"Stimulation {stimulation} < 196: second active only {second_active_ability_chance(stimulation):.0%}"
        )

    return tips


def analyze_pair(
    cat_a: "SaveCat",
    cat_b: "SaveCat",
    stimulation: int = 0,
) -> BreedingAdvice:
    """Compute breeding probabilities for a pair of cats at a given Stimulation."""
    high_prob = higher_stat_probability(stimulation)

    stat_probs: dict[str, float] = {}
    expected: dict[str, float] = {}
    for key in STAT_KEYS:
        va = getattr(cat_a, f"base_{key}")
        vb = getattr(cat_b, f"base_{key}")
        stat_probs[key] = high_prob if va != vb else 0.5
        expected[key] = round(_expected_stat(va, vb, high_prob), 2)

    return BreedingAdvice(
        cat_a_name=cat_a.name,
        cat_a_key=cat_a.db_key,
        cat_b_name=cat_b.name,
        cat_b_key=cat_b.db_key,
        stimulation=stimulation,
        stat_high_probs=stat_probs,
        first_active_chance=round(first_active_ability_chance(stimulation), 4),
        second_active_chance=round(second_active_ability_chance(stimulation), 4),
        passive_chance=round(passive_ability_chance(stimulation), 4),
        expected_stats=expected,
        inbreeding_warning=_inbreeding_warning(
            cat_a.breed_coefficient,
            cat_b.breed_coefficient,
        ),
        parent_a_coeff=cat_a.breed_coefficient,
        parent_b_coeff=cat_b.breed_coefficient,
        tips=_stimulation_tips(stimulation),
    )


def rank_pairs_for_class(
    cats: list["SaveCat"],
    collar: "CollarDef",
    stimulation: int = 0,
    max_results: int = 5,
) -> list[PairRanking]:
    """Rank all unique cat pairs by expected offspring suitability for a class.

    Uses weighted expected stats based on the collar's score_weights.
    """
    high_prob = higher_stat_probability(stimulation)

    rankings: list[PairRanking] = []
    for i, a in enumerate(cats):
        for b in cats[i + 1 :]:
            if a.gender == b.gender:
                continue

            weighted_sum = 0.0
            weight_norm = 0.0
            for k, key in enumerate(STAT_KEYS):
                va = getattr(a, f"base_{key}")
                vb = getattr(b, f"base_{key}")
                exp = _expected_stat(va, vb, high_prob)
                w = collar.score_weights[k] if k < len(collar.score_weights) else 0.0
                weighted_sum += exp * w
                weight_norm += abs(w)

            score = round(weighted_sum / weight_norm, 2) if weight_norm > 0 else 0.0

            best_stats: list[str] = []
            for k, key in enumerate(STAT_KEYS):
                w = collar.score_weights[k] if k < len(collar.score_weights) else 0.0
                if w >= 1.5:
                    best_stats.append(key.upper())

            reason = f"Expected offspring score {score:.1f}"
            if best_stats:
                reason += f" (strong {', '.join(best_stats)})"

            rankings.append(
                PairRanking(
                    cat_a_key=a.db_key,
                    cat_a_name=a.name,
                    cat_b_key=b.db_key,
                    cat_b_name=b.name,
                    expected_score=score,
                    reason=reason,
                )
            )

    rankings.sort(key=lambda r: r.expected_score, reverse=True)
    return rankings[:max_results]
