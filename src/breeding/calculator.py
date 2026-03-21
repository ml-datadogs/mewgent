"""Deterministic breeding calculator based on Mewgenics wiki mechanics.

Implements the 13-step kitten birth process formulas for stat inheritance,
ability inheritance, inbreeding prediction, and pair ranking for target classes.
Also provides room-based distribution optimization for maximizing offspring quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.data.collars import CollarDef
    from src.data.save_reader import RoomStats, SaveCat

STAT_KEYS = ("str", "dex", "con", "int", "spd", "cha", "lck")

COMFORT_CAT_LIMIT = 4


@dataclass
class BreedingAdvice:
    """Result of analyzing a breeding pair."""

    cat_a_name: str
    cat_a_key: int
    cat_b_name: str
    cat_b_key: int
    stimulation: int

    stat_high_probs: dict[str, float]

    first_active_chance: float
    second_active_chance: float
    passive_chance: float
    class_bias_chance: float

    expected_stats: dict[str, float]

    inbreeding_warning: str
    parent_a_coeff: float
    parent_b_coeff: float

    disorder_chance_per_parent: float = 0.15
    birth_defect_disorder_chance: float = 0.02
    birth_defect_parts_chance: float = 0.0

    comfort_breeding_odds: str | None = None
    room_context: dict[str, Any] | None = None
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
    same_room: bool = False
    room_name: str = ""


@dataclass
class RoomAssignment:
    """Optimal cat placement for a single room."""

    room_name: str
    cat_keys: list[int] = field(default_factory=list)
    best_pair: tuple[int, int] | None = None
    pair_score: float = 0.0
    pair_reason: str = ""
    room_stimulation: int = 0
    room_comfort: int = 0
    comfort_breeding_odds: str = ""


@dataclass
class RoomDistribution:
    """Full house distribution result with per-room assignments."""

    rooms: list[RoomAssignment] = field(default_factory=list)
    total_score: float = 0.0


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


def class_bias_chance_fn(stimulation: int) -> float:
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


def _comfort_breeding_odds(comfort: int, cat_count: int) -> str:
    """Describe breeding odds based on effective comfort."""
    effective = comfort - max(0, cat_count - COMFORT_CAT_LIMIT)
    if effective < 0:
        return "very low (fighting likely)"
    if effective == 0:
        return "low"
    if effective < 10:
        return "moderate"
    if effective < 20:
        return "good"
    return "high"


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
    room_stats: "RoomStats | None" = None,
) -> BreedingAdvice:
    """Compute breeding probabilities for a pair of cats.

    If room_stats is provided and stimulation is 0, the room's stimulation
    value is used automatically.
    """
    effective_stim = stimulation
    room_ctx: dict[str, Any] | None = None
    comfort_odds: str | None = None

    if room_stats is not None:
        if stimulation == 0:
            effective_stim = max(0, room_stats.stimulation)
        room_ctx = {
            "room_name": cat_a.room or cat_b.room,
            "stimulation": room_stats.stimulation,
            "comfort": room_stats.comfort,
        }
        comfort_odds = _comfort_breeding_odds(room_stats.comfort, room_stats.cat_count)

    high_prob = higher_stat_probability(effective_stim)

    stat_probs: dict[str, float] = {}
    expected: dict[str, float] = {}
    for key in STAT_KEYS:
        va = getattr(cat_a, f"base_{key}")
        vb = getattr(cat_b, f"base_{key}")
        stat_probs[key] = high_prob if va != vb else 0.5
        expected[key] = round(_expected_stat(va, vb, high_prob), 2)

    avg_coeff = (cat_a.breed_coefficient + cat_b.breed_coefficient) / 2

    return BreedingAdvice(
        cat_a_name=cat_a.name,
        cat_a_key=cat_a.db_key,
        cat_b_name=cat_b.name,
        cat_b_key=cat_b.db_key,
        stimulation=effective_stim,
        stat_high_probs=stat_probs,
        first_active_chance=round(first_active_ability_chance(effective_stim), 4),
        second_active_chance=round(second_active_ability_chance(effective_stim), 4),
        passive_chance=round(passive_ability_chance(effective_stim), 4),
        class_bias_chance=round(class_bias_chance_fn(effective_stim), 4),
        expected_stats=expected,
        inbreeding_warning=_inbreeding_warning(
            cat_a.breed_coefficient,
            cat_b.breed_coefficient,
        ),
        parent_a_coeff=cat_a.breed_coefficient,
        parent_b_coeff=cat_b.breed_coefficient,
        birth_defect_disorder_chance=round(birth_defect_disorder_chance(avg_coeff), 4),
        birth_defect_parts_chance=round(birth_defect_parts_chance(avg_coeff), 4),
        comfort_breeding_odds=comfort_odds,
        room_context=room_ctx,
        tips=_stimulation_tips(effective_stim),
    )


def rank_pairs_for_class(
    cats: list["SaveCat"],
    collar: "CollarDef",
    stimulation: int = 0,
    room_stats: dict[str, "RoomStats"] | None = None,
    max_results: int = 5,
) -> list[PairRanking]:
    """Rank all unique cat pairs by expected offspring suitability for a class.

    Uses weighted expected stats based on the collar's score_weights.
    When room_stats is provided and stimulation is 0, per-room stimulation
    is used for pairs sharing a room.
    """
    rankings: list[PairRanking] = []
    for i, a in enumerate(cats):
        for b in cats[i + 1 :]:
            if a.gender == b.gender:
                continue

            same_room = bool(a.room and a.room == b.room)
            pair_stim = stimulation
            room_name = ""

            if same_room:
                room_name = a.room
                if stimulation == 0 and room_stats and a.room in room_stats:
                    pair_stim = max(0, room_stats[a.room].stimulation)

            high_prob = higher_stat_probability(pair_stim)

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
                    same_room=same_room,
                    room_name=room_name,
                )
            )

    rankings.sort(key=lambda r: r.expected_score, reverse=True)
    return rankings[:max_results]


def _pair_total_score(
    cat_a: "SaveCat",
    cat_b: "SaveCat",
    stimulation: int,
) -> float:
    """Sum of expected offspring stats across all 7 stats (class-agnostic)."""
    high_prob = higher_stat_probability(stimulation)
    total = 0.0
    for key in STAT_KEYS:
        va = getattr(cat_a, f"base_{key}")
        vb = getattr(cat_b, f"base_{key}")
        total += _expected_stat(va, vb, high_prob)
    return round(total, 2)


def _inbreeding_penalty(coeff_a: float, coeff_b: float) -> float:
    """Multiplier in [0.5, 1.0] penalising high inbreeding."""
    avg = (coeff_a + coeff_b) / 2
    if avg <= 0.05:
        return 1.0
    return max(0.5, 1.0 - avg)


def rank_pairs_overall(
    cats: list["SaveCat"],
    room_stats: dict[str, "RoomStats"] | None = None,
    max_results: int = 10,
) -> list[PairRanking]:
    """Rank all opposite-gender pairs by total expected stat sum (class-agnostic).

    Uses per-room stimulation when both cats share a room.
    """
    rankings: list[PairRanking] = []
    for i, a in enumerate(cats):
        for b in cats[i + 1 :]:
            if a.gender == b.gender:
                continue

            same_room = bool(a.room and a.room == b.room)
            pair_stim = 0
            room_name = ""

            if same_room and room_stats and a.room in room_stats:
                room_name = a.room
                pair_stim = max(0, room_stats[a.room].stimulation)

            raw = _pair_total_score(a, b, pair_stim)
            penalty = _inbreeding_penalty(a.breed_coefficient, b.breed_coefficient)
            score = round(raw * penalty, 2)

            parts: list[str] = [f"Expected stat total {raw:.0f}"]
            if penalty < 1.0:
                parts.append(f"inbreeding penalty {penalty:.0%}")
            if same_room:
                parts.append(f"room {room_name} stim {pair_stim}")

            rankings.append(
                PairRanking(
                    cat_a_key=a.db_key,
                    cat_a_name=a.name,
                    cat_b_key=b.db_key,
                    cat_b_name=b.name,
                    expected_score=score,
                    reason=", ".join(parts),
                    same_room=same_room,
                    room_name=room_name,
                )
            )

    rankings.sort(key=lambda r: r.expected_score, reverse=True)
    return rankings[:max_results]


def suggest_room_distribution(
    cats: list["SaveCat"],
    room_stats: dict[str, "RoomStats"],
) -> RoomDistribution:
    """Suggest optimal cat placement across rooms for maximum breeding quality.

    Greedy algorithm:
    1. Build all valid opposite-gender pairs and score them per room
    2. Sort by (score * inbreeding_penalty) descending
    3. Assign best pair to best room, removing used cats from pool
    4. Remaining cats are placed in rooms they were already in
    """
    rooms_with_stim = {
        name: rs for name, rs in room_stats.items() if rs.stimulation > 0
    }

    if not rooms_with_stim:
        rooms_with_stim = dict(room_stats)

    males = [c for c in cats if c.gender == "male"]
    females = [c for c in cats if c.gender == "female"]

    candidates: list[tuple[float, str, "SaveCat", "SaveCat"]] = []
    for m in males:
        for f in females:
            for rname, rs in rooms_with_stim.items():
                stim = max(0, rs.stimulation)
                raw = _pair_total_score(m, f, stim)
                penalty = _inbreeding_penalty(m.breed_coefficient, f.breed_coefficient)

                comfort_pen = max(0, rs.cat_count - COMFORT_CAT_LIMIT)
                comfort_factor = max(0.6, 1.0 - 0.05 * comfort_pen)

                score = raw * penalty * comfort_factor
                candidates.append((score, rname, m, f))

    candidates.sort(key=lambda x: x[0], reverse=True)

    used_cats: set[int] = set()
    used_rooms: set[str] = set()
    assignments: dict[str, RoomAssignment] = {}

    for score, rname, cat_m, cat_f in candidates:
        if rname in used_rooms:
            continue
        if cat_m.db_key in used_cats or cat_f.db_key in used_cats:
            continue

        rs = room_stats[rname]
        stim = max(0, rs.stimulation)
        comfort_odds = _comfort_breeding_odds(rs.comfort, rs.cat_count)

        parts: list[str] = [f"Expected total {score:.0f}"]
        avg_inbred = (cat_m.breed_coefficient + cat_f.breed_coefficient) / 2
        if avg_inbred > 0.05:
            parts.append(f"inbreeding {avg_inbred:.0%}")
        parts.append(f"stim {stim}")

        assignments[rname] = RoomAssignment(
            room_name=rname,
            cat_keys=[cat_m.db_key, cat_f.db_key],
            best_pair=(cat_m.db_key, cat_f.db_key),
            pair_score=round(score, 2),
            pair_reason=", ".join(parts),
            room_stimulation=stim,
            room_comfort=rs.comfort,
            comfort_breeding_odds=comfort_odds,
        )
        used_cats.add(cat_m.db_key)
        used_cats.add(cat_f.db_key)
        used_rooms.add(rname)

    for rname in room_stats:
        if rname not in assignments:
            rs = room_stats[rname]
            assignments[rname] = RoomAssignment(
                room_name=rname,
                cat_keys=[],
                room_stimulation=max(0, rs.stimulation),
                room_comfort=rs.comfort,
                comfort_breeding_odds=_comfort_breeding_odds(rs.comfort, rs.cat_count),
            )

    for cat in cats:
        if cat.db_key in used_cats:
            continue
        room = cat.room or ""
        if room in assignments:
            assignments[room].cat_keys.append(cat.db_key)
        else:
            for rname, ra in assignments.items():
                if not ra.best_pair:
                    ra.cat_keys.append(cat.db_key)
                    break

    room_list = sorted(assignments.values(), key=lambda r: r.pair_score, reverse=True)
    total = sum(r.pair_score for r in room_list)

    return RoomDistribution(rooms=room_list, total_score=round(total, 2))
