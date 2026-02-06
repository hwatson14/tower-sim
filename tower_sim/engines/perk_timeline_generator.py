from __future__ import annotations

from dataclasses import dataclass
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tower_sim.loaders.perk_tables import PerkDefinition, load_perk_definitions, load_perk_pool_weights


@dataclass(frozen=True)
class PerkTimelinePolicy:
    seed: int
    target_wave: int

    # Labs
    waves_required_lab: int = 0  # subtracts from base WR
    standard_perk_bonus: float = 0.0  # decimal, e.g. 0.25
    perk_option_quantity: int = 0  # 0..2 => 2..4 options
    ban_perks_capacity: int = 0  # max bans that apply

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


def _offers_count(perk_option_quantity: int) -> int:
    # base 2 + lab, capped at 4
    return max(2, min(4, 2 + max(0, perk_option_quantity)))


def _base_waves_required(perks_taken: int) -> int:
    # Repo intent: match your perk-PWR sheet logic (200 base; step-ups after 20/30/40)
    if perks_taken >= 40:
        return 350
    if perks_taken >= 30:
        return 300
    if perks_taken >= 20:
        return 250
    return 200


def _perk_wave_requirement_waves(
    perks_taken: int,
    pwr_stacks: int,
    waves_required_lab: int,
    standard_perk_bonus: float,
) -> int:
    # PWR base: -20% each stack; Standard Perk Bonus increases perk effectiveness
    base = _base_waves_required(perks_taken)
    after_lab = max(1, base - max(0, waves_required_lab))

    effective = 0.20 * (1.0 + max(0.0, standard_perk_bonus))  # e.g. 0.20 * 1.25 = 0.25
    mult = (1.0 - effective) ** max(0, pwr_stacks)

    return max(1, int(math.floor(after_lab * mult)))


def generate_timeline(policy_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    policy = load_policy(policy_path)
    rng = random.Random(policy.seed)

    perks = load_perk_definitions()
    weights = {w.category: w.weight_percent for w in load_perk_pool_weights()}

    by_name = {p.perk_name: p for p in perks}

    banned = (policy.banned_perks or [])[: max(0, policy.ban_perks_capacity)]
    priority = policy.priority_order or []

    def eligible(name: str) -> bool:
        return name in by_name and name not in banned

    pool = [p.perk_name for p in perks if eligible(p.perk_name)]
    if not pool:
        return [], {"enabled": True, "reason": "empty_pool_after_bans"}

    # Detect canonical PWR perk name if present
    pwr_name = "Perk Wave Requirement -20.00%"
    if pwr_name not in by_name:
        pwr_name = None

    offers_k = _offers_count(policy.perk_option_quantity)

    def sample_offer_set(k: int) -> List[str]:
        # Weighted by category percentage (fallback 1.0)
        remaining = [n for n in pool]
        offered: List[str] = []
        while remaining and len(offered) < k:
            wts = [float(weights.get(by_name[n].category, 1.0)) for n in remaining]
            choice = rng.choices(remaining, weights=wts, k=1)[0]
            offered.append(choice)
            remaining.remove(choice)
        return offered

    timeline: List[Dict[str, Any]] = []
    diag: Dict[str, Any] = {
        "seed": policy.seed,
        "bans_applied": banned,
        "offers_k": offers_k,
        "missing_policy_names": [x for x in (banned + priority + ([policy.first_perk_choice] if policy.first_perk_choice else [])) if x and x not in by_name],
    }

    current_wave = 0
    perks_taken = 0
    pwr_stacks = 0
    taken_counts: Dict[str, int] = {}

    while True:
        step = _perk_wave_requirement_waves(
            perks_taken=perks_taken,
            pwr_stacks=pwr_stacks,
            waves_required_lab=policy.waves_required_lab,
            standard_perk_bonus=policy.standard_perk_bonus,
        )
        next_wave = current_wave + step
        if next_wave > policy.target_wave:
            break

        offered = sample_offer_set(offers_k)

        # Force first pick if requested
        if perks_taken == 0 and policy.first_perk_choice and policy.first_perk_choice in by_name:
            if policy.first_perk_choice not in offered and offered:
                offered[-1] = policy.first_perk_choice

        # Choose by priority order (first match), else first offered
        taken = None
        for pref in priority:
            if pref in offered:
                taken = pref
                break
        if taken is None:
            taken = offered[0] if offered else None
        if taken is None:
            diag["terminated_reason"] = "no_offers"
            break

        # Respect max_picks
        perk_def: PerkDefinition = by_name[taken]
        new_count = taken_counts.get(taken, 0) + 1
        if perk_def.max_picks > 0 and new_count > perk_def.max_picks:
            # If somehow selected beyond cap, skip taking and stop (fail-closed)
            diag["terminated_reason"] = "selected_beyond_max_picks"
            diag["bad_pick"] = {"perk": taken, "count": new_count, "max_picks": perk_def.max_picks}
            break
        taken_counts[taken] = new_count

        if pwr_name and taken == pwr_name:
            pwr_stacks += 1

        timeline.append(
            {
                "wave": next_wave,
                "perk_taken": taken,
                "effect": perk_def.effect,
                "effect_stat_id": perk_def.effect_stat_id,
                "stacking_type": perk_def.stacking_type,
                "quantity": taken_counts[taken],
                "offered": offered,
            }
        )

        current_wave = next_wave
        perks_taken += 1

    diag.update(
        {
            "generated_rows": len(timeline),
            "final_wave": current_wave,
            "perks_taken": perks_taken,
            "pwr_stacks": pwr_stacks,
        }
    )
    return timeline, diag
