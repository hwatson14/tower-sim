from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase, StatRegistry
from tower_sim.loaders.perk_tables import PerkDefinition, load_perk_definitions


class PerkTimelineError(ValueError):
    pass


_MULT_RE = re.compile(r"[×x]\s*([0-9]+(?:\.[0-9]+)?)")
_PP_RE = re.compile(r"([+\-−])\s*([0-9]+(?:\.[0-9]+)?)\s*percentage points", re.IGNORECASE)


def _parse_perk_base(defn: PerkDefinition) -> Tuple[Optional[float], Optional[str]]:
    """
    Returns (perk_base_decimal, mode_str) where mode_str is "multiplicative" or "additive".
    """
    eff = defn.effect or ""
    m = _MULT_RE.search(eff)
    if m:
        mult = float(m.group(1))
        return (mult - 1.0), "multiplicative"

    p = _PP_RE.search(eff)
    if p:
        sign = -1.0 if p.group(1) in ("-", "−") else 1.0
        pp = float(p.group(2))
        return (sign * (pp / 100.0)), "additive"  # +4pp => +0.04

    # Unknown / non-numeric perks (UW unlocks, missiles, etc.)
    return None, None


def _choose_phase_for_stat(registry: StatRegistry, stat_id: str, existing: Dict[Tuple[str, Phase], StatInput]) -> Phase:
    # Prefer existing phase if present
    for (sid, ph) in existing.keys():
        if sid == stat_id:
            return ph
    # Else prefer START_OF_RUN if allowed, else any allowed phase
    allowed = registry.get(stat_id).allowed_phases
    if Phase.START_OF_RUN in allowed:
        return Phase.START_OF_RUN
    return next(iter(allowed))


def apply_perk_timeline_to_inputs(
    registry: StatRegistry,
    stat_inputs: List[StatInput],
    perk_timeline_path: Optional[str],
    current_wave: int,
) -> Tuple[List[StatInput], Dict[str, Any]]:
    if not perk_timeline_path:
        return stat_inputs, {"enabled": False, "reason": "no_path"}

    p = Path(perk_timeline_path)
    if not p.exists():
        return stat_inputs, {"enabled": False, "reason": "path_missing", "path": str(p)}

    rows = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise PerkTimelineError(f"Invalid timeline format at {p} (expected list).")

    defs = {d.perk_name: d for d in load_perk_definitions()}

    # Count perk stacks up to current wave
    stacks: Dict[str, int] = {}
    applied_rows = [r for r in rows if int(r.get("wave", 10**18)) <= current_wave]
    for r in applied_rows:
        name = str(r.get("perk_taken", "")).strip()
        if not name:
            continue
        stacks[name] = stacks.get(name, 0) + 1

    existing = {(i.stat_id, i.phase): i for i in stat_inputs}
    updated = list(stat_inputs)

    applied_effects: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    # Apply each perk’s numeric effect to its effect_stat_id
    for perk_name, qty in stacks.items():
        defn = defs.get(perk_name)
        if defn is None or not defn.effect_stat_id:
            skipped.append({"perk": perk_name, "reason": "no_definition_or_no_effect_stat_id"})
            continue

        base, mode = _parse_perk_base(defn)
        if base is None or mode is None:
            skipped.append({"perk": perk_name, "reason": "non_numeric_or_unparsed_effect", "effect": defn.effect})
            continue

        stat_id = defn.effect_stat_id
        phase = _choose_phase_for_stat(registry, stat_id, existing)
        key = (stat_id, phase)

        # Merge into existing StatInput or create a new one
        prior = existing.get(key)
        if prior is None:
            prior = StatInput(stat_id=stat_id, phase=phase, base_value=None, loadout_delta=0.0, enhancement_multiplier=1.0, provenance="perk_timeline")
            updated.append(prior)
            existing[key] = prior

        # StatEngine applies: (base + loadout_delta) * enhancement_multiplier
        loadout_delta = prior.loadout_delta or 0.0
        enh = prior.enhancement_multiplier or 1.0

        if mode == "multiplicative":
            # multiplier is 1 + base*qty (no standard perk bonus applied here; your repo’s perk_engine exists,
            # but perk tables currently don’t wire SPB per perk-effect in stat engine. This is deterministic baseline.)
            mult = 1.0 + base * qty
            enh *= mult
        else:
            loadout_delta += base * qty

        merged = StatInput(
            stat_id=prior.stat_id,
            phase=prior.phase,
            base_value=prior.base_value,
            loadout_delta=loadout_delta,
            enhancement_multiplier=enh,
            tier_rule_delta=prior.tier_rule_delta,
            tier_rule_multiplier=prior.tier_rule_multiplier,
            derived_value=prior.derived_value,
            provenance=prior.provenance or "perk_timeline",
        )

        # Replace in updated list
        for idx, item in enumerate(updated):
            if item.stat_id == key[0] and item.phase == key[1]:
                updated[idx] = merged
                break
        existing[key] = merged

        applied_effects.append({"perk": perk_name, "stat_id": stat_id, "mode": mode, "qty": qty})

    diag = {
        "enabled": True,
        "path": str(p),
        "current_wave": current_wave,
        "rows_applied": len(applied_rows),
        "effects_applied": applied_effects,
        "effects_skipped": skipped,
    }
    return updated, diag
