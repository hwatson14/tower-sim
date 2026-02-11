from __future__ import annotations

from decimal import Decimal

from tower_sim.engines.stat_input_compiler import _UW_TRACK_SPECS, compile_full_stat_inputs
from tower_sim.registry.combat_stat_contract import required_max_wave_stat_input_ids
from tower_sim.registry.stat_registry import Phase, StatRegistry, default_registry
from tower_sim.util.account_snapshot import AccountSnapshot
from tower_sim.util.statbook import StatBook, StatRow

PHASE_START = Phase.START_OF_RUN


def build_statbook(snapshot: AccountSnapshot) -> StatBook:
    compiled = compile_full_stat_inputs(snapshot)
    start_inputs = {
        stat_input.stat_id: stat_input
        for stat_input in compiled.stat_inputs
        if stat_input.phase == PHASE_START
    }
    rows: list[StatRow] = []
    for stat_id in _ordered_target_stat_ids():
        stat_input = start_inputs.get(stat_id)
        if stat_input is None:
            rows.append(_missing_row(stat_id))
            continue
        rows.append(_stat_input_to_row(stat_input))
    return build_canonical_statbook(rows)


def build_canonical_statbook(
    rows: list[StatRow],
    registry: StatRegistry | None = None,
) -> StatBook:
    resolved_registry = registry or default_registry()
    for row in rows:
        resolved_registry.validate_stat_id(row.stat_id)
        stat_def = resolved_registry.get(row.stat_id)
        if row.phase not in stat_def.allowed_phases:
            raise ValueError(
                f"Phase {row.phase.value} not allowed for stat_id {row.stat_id}."
            )
        if not row.provenance:
            raise ValueError(f"Provenance required for stat_id {row.stat_id}.")
        row.loadout_delta_total()
    return StatBook(rows=rows)


def _ordered_target_stat_ids() -> list[str]:
    ids = _target_stat_ids()
    return sorted(ids, key=lambda stat_id: (stat_id.startswith("uw_"), stat_id))


def _target_stat_ids() -> set[str]:
    max_wave_ids = set(required_max_wave_stat_input_ids())
    uw_ids = set()
    for tracks in _UW_TRACK_SPECS.values():
        for spec in tracks.values():
            uw_ids.add(spec.stat_id)
            uw_ids.add(f"{spec.stat_id}_next_cost")
    return max_wave_ids | uw_ids


def _missing_row(stat_id: str) -> StatRow:
    return StatRow(
        stat_id=stat_id,
        phase=PHASE_START,
        base_value=None,
        loadout_delta_modules=None,
        loadout_delta_cards=None,
        loadout_delta_bots=None,
        loadout_delta_guardians=None,
        loadout_delta_other=None,
        enhancement_multiplier=None,
        tier_rule_delta_or_multiplier=None,
        final_value=None,
        provenance="missing:stat_input",
    )


def _stat_input_to_row(stat_input) -> StatRow:
    base_value = _decimal_or_none(stat_input.base_value)
    loadout_delta = _decimal_or_none(stat_input.loadout_delta)
    enhancement = _decimal_or_none(stat_input.enhancement_multiplier)
    tier_rule = _decimal_or_none(stat_input.tier_rule_delta)
    if tier_rule is None:
        tier_rule = _decimal_or_none(stat_input.tier_rule_multiplier)
    final_value = _resolve_final_value(stat_input)
    return StatRow(
        stat_id=stat_input.stat_id,
        phase=stat_input.phase,
        base_value=base_value,
        loadout_delta_modules=Decimal(0),
        loadout_delta_cards=Decimal(0),
        loadout_delta_bots=Decimal(0),
        loadout_delta_guardians=Decimal(0),
        loadout_delta_other=loadout_delta,
        enhancement_multiplier=enhancement,
        tier_rule_delta_or_multiplier=tier_rule,
        final_value=final_value,
        provenance=stat_input.provenance or "compiled:stat_input",
    )


def _resolve_final_value(stat_input) -> Decimal | None:
    if stat_input.derived_value is not None:
        return Decimal(str(stat_input.derived_value))
    if (
        stat_input.base_value is None
        and stat_input.loadout_delta is None
        and stat_input.enhancement_multiplier is None
        and stat_input.tier_rule_delta is None
        and stat_input.tier_rule_multiplier is None
    ):
        return None
    base = stat_input.base_value or 0.0
    loadout = stat_input.loadout_delta or 0.0
    enhancement = stat_input.enhancement_multiplier or 1.0
    tiered = (base + loadout) * enhancement
    if stat_input.tier_rule_delta is not None:
        tiered += stat_input.tier_rule_delta
    if stat_input.tier_rule_multiplier is not None:
        tiered *= stat_input.tier_rule_multiplier
    return Decimal(str(tiered))


def _decimal_or_none(value: float | int | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
