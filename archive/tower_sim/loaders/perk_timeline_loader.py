from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase, StatRegistry


class PerkTimelineError(ValueError):
    def __init__(self, message: str, *, reason: str = "invalid_precomputed_table") -> None:
        super().__init__(message)
        self.reason = reason


def _choose_phase_for_stat(
    registry: StatRegistry,
    stat_id: str,
    existing: Dict[Tuple[str, Phase], StatInput],
) -> Phase:
    for (sid, ph) in existing.keys():
        if sid == stat_id:
            return ph
    allowed = registry.get(stat_id).allowed_phases
    if Phase.START_OF_RUN in allowed:
        return Phase.START_OF_RUN
    return next(iter(allowed))


def _parse_row(
    row: Dict[str, Any],
    *,
    row_index: int,
    registry: StatRegistry,
    existing: Dict[Tuple[str, Phase], StatInput],
) -> Tuple[int, str, Phase, float, float, str]:
    if not isinstance(row, dict):
        raise PerkTimelineError(f"Invalid perk table row at index {row_index}: expected object.")
    if "perk_taken" in row:
        raise PerkTimelineError(
            "Legacy perk timeline event format is unsupported at runtime. "
            "Expected pre-generated perk-effect table rows (wave/stat_id/phase/loadout_delta/enhancement_multiplier)."
        )

    wave_raw = row.get("wave")
    if wave_raw is None:
        raise PerkTimelineError(f"Perk table row {row_index} missing 'wave'.")
    try:
        wave = int(wave_raw)
    except (TypeError, ValueError) as exc:
        raise PerkTimelineError(f"Perk table row {row_index} has invalid 'wave': {wave_raw!r}") from exc

    stat_id = str(row.get("stat_id", "")).strip()
    if not stat_id:
        raise PerkTimelineError(f"Perk table row {row_index} missing 'stat_id'.")

    phase_raw = row.get("phase")
    if phase_raw in (None, ""):
        phase = _choose_phase_for_stat(registry, stat_id, existing)
    else:
        try:
            phase = Phase(str(phase_raw))
        except ValueError as exc:
            raise PerkTimelineError(
                f"Perk table row {row_index} has invalid 'phase': {phase_raw!r}"
            ) from exc

    loadout_delta_raw = row.get("loadout_delta", 0.0)
    enhancement_raw = row.get("enhancement_multiplier", 1.0)
    try:
        loadout_delta = float(loadout_delta_raw)
    except (TypeError, ValueError) as exc:
        raise PerkTimelineError(
            f"Perk table row {row_index} has invalid 'loadout_delta': {loadout_delta_raw!r}"
        ) from exc
    try:
        enhancement_multiplier = float(enhancement_raw)
    except (TypeError, ValueError) as exc:
        raise PerkTimelineError(
            f"Perk table row {row_index} has invalid 'enhancement_multiplier': {enhancement_raw!r}"
        ) from exc

    if "loadout_delta" not in row and "enhancement_multiplier" not in row:
        raise PerkTimelineError(
            f"Perk table row {row_index} missing both 'loadout_delta' and 'enhancement_multiplier'."
        )

    provenance = str(row.get("provenance") or "perk_table")
    return wave, stat_id, phase, loadout_delta, enhancement_multiplier, provenance


def apply_perk_timeline_to_inputs(
    registry: StatRegistry,
    stat_inputs: List[StatInput],
    perk_timeline_path: Optional[str],
    current_wave: int,
) -> Tuple[List[StatInput], Dict[str, Any]]:
    if not perk_timeline_path:
        raise PerkTimelineError(
            "Missing required pre-generated perk table path for non-tournament scenario.",
            reason="missing_precomputed_table",
        )

    p = Path(perk_timeline_path)
    if not p.exists():
        raise PerkTimelineError(
            f"Pre-generated perk table path does not exist: {p}",
            reason="missing_precomputed_table",
        )

    rows = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise PerkTimelineError(f"Invalid perk table format at {p} (expected list).")

    existing = {(i.stat_id, i.phase): i for i in stat_inputs}
    updated = list(stat_inputs)
    applied_effects: List[Dict[str, Any]] = []

    for row_index, row in enumerate(rows):
        (
            wave,
            stat_id,
            phase,
            row_delta,
            row_multiplier,
            row_provenance,
        ) = _parse_row(row, row_index=row_index, registry=registry, existing=existing)
        if wave > current_wave:
            continue

        key = (stat_id, phase)
        prior = existing.get(key)
        if prior is None:
            prior = StatInput(
                stat_id=stat_id,
                phase=phase,
                base_value=None,
                loadout_delta=0.0,
                enhancement_multiplier=1.0,
                provenance=row_provenance,
            )
            updated.append(prior)
            existing[key] = prior

        merged = StatInput(
            stat_id=prior.stat_id,
            phase=prior.phase,
            base_value=prior.base_value,
            loadout_delta=(prior.loadout_delta or 0.0) + row_delta,
            enhancement_multiplier=(prior.enhancement_multiplier or 1.0) * row_multiplier,
            tier_rule_delta=prior.tier_rule_delta,
            tier_rule_multiplier=prior.tier_rule_multiplier,
            derived_value=prior.derived_value,
            provenance=row_provenance,
        )

        for idx, item in enumerate(updated):
            if item.stat_id == key[0] and item.phase == key[1]:
                updated[idx] = merged
                break
        existing[key] = merged

        applied_effects.append(
            {
                "wave": wave,
                "stat_id": stat_id,
                "phase": phase.value,
                "loadout_delta": row_delta,
                "enhancement_multiplier": row_multiplier,
            }
        )

    diag = {
        "enabled": True,
        "mode": "precomputed_table",
        "path": str(p),
        "current_wave": current_wave,
        "effects_applied": applied_effects,
        "rows_applied": len(applied_effects),
    }
    return updated, diag
