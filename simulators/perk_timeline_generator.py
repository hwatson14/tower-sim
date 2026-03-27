from __future__ import annotations

from dataclasses import dataclass
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qe.perk_tables import (
    PerkDefinition,
    PerkWaveRequirementStep,
    load_perk_definitions,
    load_perk_pool_weights,
    load_perk_wave_requirement_steps,
)


# ── policy ──


@dataclass(frozen=True)
class PerkTimelinePolicy:
    seed: int
    target_wave: int

    # Labs
    waves_required_lab: int = 0          # positive integer subtracted from base WR
    standard_perk_bonus: float = 0.0     # decimal, e.g. 0.25  (SPB lab level / 100)
    perk_option_quantity: int = 0         # 0..2 => 2..4 options
    ban_perks_capacity: int = 0          # max bans that apply

    # Preferences
    banned_perks: List[str] = None
    priority_order: List[str] = None
    first_perk_choice: Optional[str] = None


def load_policy(path: Path) -> PerkTimelinePolicy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PerkTimelinePolicy(
        seed=int(raw["seed"]),
        target_wave=int(raw["target_wave"]),
        waves_required_lab=int(raw.get("waves_required_lab", 0)),
        standard_perk_bonus=float(raw.get("standard_perk_bonus", 0.0)),
        perk_option_quantity=int(raw.get("perk_option_quantity", 0)),
        ban_perks_capacity=int(raw.get("ban_perks_capacity", 0)),
        banned_perks=list(raw.get("banned_perks", [])),
        priority_order=list(raw.get("priority_order", [])),
        first_perk_choice=raw.get("first_perk_choice"),
    )


# ── wave requirement formula ──
#
# Wiki formula (https://the-tower-idle-tower-defense.fandom.com/wiki/Perks):
#   step = (Base Waves Required - Waves Required lab) * (1 - (PWR_qty * 0.20 * (1 + SPB / 100)))
#   "If you get a decimal, you need to round the answer down."
#   "The rounded answer can be multiplied by number of perks."
#
# PWR is RETROACTIVE: picking PWR recalculates the entire wave schedule.
# When retroactive recalculation places the next perk at or before the current wave,
# that perk is awarded immediately (burst).
#
# KB sources:
#   - perk-wave-requirement-steps.csv: base thresholds (200/250/300/350)
#   - perk-entity-registry.csv: stacking_type=additive for PWR
#   - perk-effect-registry.csv: remaining_fraction=0.80 (i.e. -20% per pick)
#   - wiki: formula above, retroactive behavior confirmed


def _offers_count(perk_option_quantity: int) -> int:
    """Base 2 + lab, capped at 4."""
    return max(2, min(4, 2 + max(0, perk_option_quantity)))


def _step_exact(
    base: int,
    waves_required_lab: int,
    pwr_quantity: int,
    standard_perk_bonus: float,
) -> float:
    """Exact (unfloored) step for a given base, lab, PWR count, and SPB.

    Wiki: step = (base - lab) * (1 - PWR_qty * 0.20 * (1 + SPB/100))
    """
    after_lab = base - waves_required_lab
    # PWR reduction is linear (additive stacking per KB entity registry)
    pwr_reduction = pwr_quantity * 0.20 * (1.0 + standard_perk_bonus)
    residual = max(0.0, 1.0 - pwr_reduction)
    return max(0.0, after_lab * residual)


def _floored_step(
    base: int,
    waves_required_lab: int,
    pwr_quantity: int,
    standard_perk_bonus: float,
) -> int:
    """Wiki: "round the answer down." """
    return max(0, math.floor(_step_exact(base, waves_required_lab, pwr_quantity, standard_perk_bonus)))


def _ideal_wave(
    perk_number: int,
    pwr_quantity: int,
    waves_required_lab: int,
    standard_perk_bonus: float,
    steps: List[PerkWaveRequirementStep],
) -> int:
    """Retroactive ideal cumulative wave for perk N with given PWR stacks.

    Accumulates exact (unfloored) section contributions, floors once at the end.
    This matches the verified reference table for 0-PWR (45/45) and 1-PWR (45/45).

    Wiki formula per section:
      step_exact = (base - WR_lab) * (1 - PWR_qty * 0.20 * (1 + SPB))
    Cumulative = floor(sum of count_in_section * step_exact_for_section)
    """
    total_exact = 0.0
    remaining = perk_number
    sorted_asc = sorted(steps, key=lambda s: s.perks_taken_threshold)

    for i, step_def in enumerate(sorted_asc):
        if remaining <= 0:
            break
        next_threshold = sorted_asc[i + 1].perks_taken_threshold if i + 1 < len(sorted_asc) else 99999
        section_capacity = next_threshold - step_def.perks_taken_threshold
        section_count = min(remaining, section_capacity)

        se = _step_exact(
            step_def.base_waves_required,
            waves_required_lab,
            pwr_quantity,
            standard_perk_bonus,
        )
        total_exact += section_count * se
        remaining -= section_count

    return max(0, math.floor(total_exact))


# ── timeline generation ──


def generate_timeline(policy_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    policy = load_policy(policy_path)
    rng = random.Random(policy.seed)

    perks = load_perk_definitions()
    weights = {w.category: w.weight_percent for w in load_perk_pool_weights()}
    steps = load_perk_wave_requirement_steps()

    by_name: Dict[str, PerkDefinition] = {p.perk_name: p for p in perks}

    banned_set: set[str] = set(
        (policy.banned_perks or [])[: max(0, policy.ban_perks_capacity)]
    )

    def eligible(name: str) -> bool:
        return name in by_name and name not in banned_set

    # Mutable pool: shrinks as perks are exhausted.
    pool: List[str] = [p.perk_name for p in perks if eligible(p.perk_name)]
    if not pool:
        return [], {"enabled": True, "reason": "empty_pool_after_bans"}

    # Detect canonical PWR perk name.
    pwr_name = "Perk Wave Requirement -20.00%"
    if pwr_name not in by_name:
        pwr_name = None

    priority = policy.priority_order or []
    offers_k = _offers_count(policy.perk_option_quantity)

    def sample_offer_set(k: int) -> List[str]:
        """Weighted category sampling without replacement within one offer."""
        remaining = list(pool)
        offered: List[str] = []
        while remaining and len(offered) < k:
            wts = [float(weights.get(by_name[n].category, 1.0)) for n in remaining]
            choice = rng.choices(remaining, weights=wts, k=1)[0]
            offered.append(choice)
            remaining.remove(choice)
        return offered

    def choose_perk(offered: List[str]) -> str | None:
        """Choose from offered: priority first (skipping exhausted), then first non-exhausted."""
        for pref in priority:
            if pref in offered:
                pdef = by_name[pref]
                if pdef.max_picks <= 0 or taken_counts.get(pref, 0) < pdef.max_picks:
                    return pref
        for candidate in offered:
            pdef = by_name[candidate]
            if pdef.max_picks <= 0 or taken_counts.get(candidate, 0) < pdef.max_picks:
                return candidate
        return None

    timeline: List[Dict[str, Any]] = []
    taken_counts: Dict[str, int] = {}
    current_wave = 0
    perks_taken = 0
    pwr_stacks = 0

    while True:
        if not pool:
            break

        # Compute ideal wave for the NEXT perk using retroactive formula.
        next_perk_number = perks_taken + 1
        ideal = _ideal_wave(
            next_perk_number, pwr_stacks,
            policy.waves_required_lab, policy.standard_perk_bonus, steps,
        )

        # The first perk can never appear before after_lab of the first section.
        if perks_taken == 0:
            first_base = min(s.base_waves_required for s in steps)
            first_after_lab = max(1, first_base - policy.waves_required_lab)
            ideal = max(ideal, first_after_lab)

        # If ideal is in the past or present, perk is awarded immediately (retroactive burst).
        # Otherwise advance to ideal wave.
        next_wave = max(current_wave, ideal)

        if next_wave > policy.target_wave:
            break

        offered = sample_offer_set(offers_k)

        # Force first pick if requested — only if eligible (not banned).
        if (
            perks_taken == 0
            and policy.first_perk_choice
            and eligible(policy.first_perk_choice)
        ):
            if policy.first_perk_choice not in offered and offered:
                offered[-1] = policy.first_perk_choice

        taken = choose_perk(offered)
        if taken is None:
            break

        perk_def = by_name[taken]
        new_count = taken_counts.get(taken, 0) + 1
        taken_counts[taken] = new_count

        is_pwr = pwr_name is not None and taken == pwr_name
        if is_pwr:
            pwr_stacks += 1

        timeline.append(
            {
                "wave": next_wave,
                "perk_taken": taken,
                "effect": perk_def.effect,
                "effect_stat_id": perk_def.effect_stat_id,
                "stacking_type": perk_def.stacking_type,
                "quantity": new_count,
                "offered": offered,
                "pwr_stacks_after": pwr_stacks,
                "retroactive_burst": next_wave == current_wave and perks_taken > 0,
            }
        )

        # Remove from pool if max_picks reached.
        if perk_def.max_picks > 0 and new_count >= perk_def.max_picks:
            pool = [n for n in pool if n != taken]

        current_wave = next_wave
        perks_taken += 1

    diag: Dict[str, Any] = {
        "seed": policy.seed,
        "target_wave": policy.target_wave,
        "bans_applied": sorted(banned_set),
        "offers_k": offers_k,
        "waves_required_lab": policy.waves_required_lab,
        "standard_perk_bonus": policy.standard_perk_bonus,
        "pwr_model": "retroactive_linear_additive",
        "pwr_formula": "step = floor((base - WR_lab) * (1 - PWR_qty * 0.20 * (1 + SPB)))",
        "pwr_formula_source": "wiki: https://the-tower-idle-tower-defense.fandom.com/wiki/Perks",
        "wave_steps_source": "kb/perks/tables/perk-wave-requirement-steps.csv",
        "pool_weights_source": "kb/perks/tables/perk-pool-weights.csv",
        "missing_policy_names": [
            x
            for x in (
                list(banned_set)
                + priority
                + ([policy.first_perk_choice] if policy.first_perk_choice else [])
            )
            if x and x not in by_name
        ],
        "generated_rows": len(timeline),
        "final_wave": current_wave,
        "perks_taken": perks_taken,
        "pwr_stacks": pwr_stacks,
        "taken_counts": dict(sorted(taken_counts.items())),
        "pool_remaining": len(pool),
    }
    return timeline, diag


def perk_state_at_wave(timeline: List[Dict[str, Any]], wave: int) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in timeline:
        try:
            row_wave = int(row.get("wave", 0))
        except Exception:
            row_wave = 0
        if row_wave <= int(wave):
            perk_name = row.get("perk_taken") or row.get("picked_perk") or row.get("perk_name")
            if perk_name:
                counts[str(perk_name)] = counts.get(str(perk_name), 0) + 1
    return counts


def final_perk_state(timeline: List[Dict[str, Any]]) -> Dict[str, int]:
    last_wave = 0
    for row in timeline:
        try:
            last_wave = max(last_wave, int(row.get("wave", 0)))
        except Exception:
            pass
    return perk_state_at_wave(timeline, last_wave)
