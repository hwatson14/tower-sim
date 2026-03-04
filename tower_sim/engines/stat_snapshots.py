from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

from tower_sim.engines.battle_conditions import BattleConditions
from tower_sim.run.context import RunContext
from tower_sim.engines.stat_engine import StatEngineResult, StatInput
from tower_sim.registry.stat_registry import Phase, StatRegistry
from tower_sim.engines.tier_rules import TierRulesResult
from tower_sim.engines.wave_engine import RunWaveState


class StatSnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class AtWaveSnapshot:
    wave: int
    values: Dict[str, float]
    applied_bc: Dict[str, float]
    applied_heat: Dict[str, float]
    frozen_order: List[str]


def build_at_wave_snapshot(
    stat_inputs: Iterable[StatInput],
    engine_result: StatEngineResult,
    registry: StatRegistry,
    tier_rules: TierRulesResult | None,
    battle_conditions: BattleConditions | None,
    wave_state: RunWaveState | None,
    *,
    wave: int,
    run_context: RunContext,
    heat_magnitudes: Mapping[str, float] | None = None,
    per_wave_overrides: Mapping[str, float] | None = None,
) -> AtWaveSnapshot:
    stat_ids = registry.stat_ids_in_order()
    stat_inputs_list = list(stat_inputs)
    at_wave_inputs: List[StatInput] = []
    for stat_id in stat_ids:
        if Phase.AT_WAVE not in registry.get(stat_id).allowed_phases:
            continue
        if (
            Phase.AT_WAVE in engine_result.run_stats
            and stat_id in engine_result.run_stats[Phase.AT_WAVE].values
        ):
            continue
        derived_value = _resolve_at_wave_value(
            stat_id,
            stat_inputs=stat_inputs_list,
            engine_result=engine_result,
            wave_state=wave_state,
        )
        if derived_value is None:
            continue
        at_wave_inputs.append(
            StatInput(
                stat_id=stat_id,
                phase=Phase.AT_WAVE,
                derived_value=derived_value,
                provenance="wave_state",
            )
        )
    if at_wave_inputs:
        combined_inputs = stat_inputs_list + at_wave_inputs
        engine = _build_engine_with_rules(registry, tier_rules)
        engine_result = engine.build(combined_inputs)

    start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
    if start_stats is None:
        raise StatSnapshotError("Missing START_OF_RUN stats for snapshot build.")
    base_values = dict(start_stats.values)

    at_wave_stats = engine_result.run_stats.get(Phase.AT_WAVE)
    if at_wave_stats is not None:
        base_values.update(at_wave_stats.values)

    if per_wave_overrides:
        for stat_id, value in per_wave_overrides.items():
            if stat_id not in base_values:
                continue
            base_values[stat_id] = float(value)
    bc_values: Dict[str, float] = {}
    heat_values: Dict[str, float] = {}

    if battle_conditions is not None:
        bc_context = battle_conditions.for_run_context(run_context)
        for stat_id in stat_ids:
            if stat_id not in base_values:
                continue
            before = base_values[stat_id]
            after_bc = bc_context.apply(stat_id, before)
            if after_bc != before:
                bc_values[stat_id] = after_bc
            base_values[stat_id] = after_bc

    if heat_magnitudes:
        for stat_id in stat_ids:
            if stat_id not in base_values:
                continue
            if stat_id in heat_magnitudes:
                base_values[stat_id] = heat_magnitudes[stat_id]
                heat_values[stat_id] = heat_magnitudes[stat_id]

    return AtWaveSnapshot(
        wave=wave,
        values=base_values,
        applied_bc=bc_values,
        applied_heat=heat_values,
        frozen_order=stat_ids,
    )


def _resolve_at_wave_value(
    stat_id: str,
    *,
    stat_inputs: Iterable[StatInput],
    engine_result: StatEngineResult,
    wave_state: RunWaveState | None,
) -> float | None:
    if stat_id == "wave_attack_index":
        if wave_state is None:
            raise StatSnapshotError("Wave state missing for wave_attack_index.")
        return float(wave_state.W_attack)
    if stat_id == "wave_health_index":
        if wave_state is None:
            raise StatSnapshotError("Wave state missing for wave_health_index.")
        return float(wave_state.W_health)
    for stat_input in stat_inputs:
        if stat_input.stat_id == stat_id and stat_input.phase == Phase.AT_WAVE:
            return _extract_value(stat_input, engine_result)

    start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
    end_stats = engine_result.run_stats.get(Phase.END_OF_RUN)
    if start_stats is None and end_stats is None:
        return None
    start_value = None if start_stats is None else start_stats.values.get(stat_id)
    end_value = None if end_stats is None else end_stats.values.get(stat_id)
    if start_value is None and end_value is None:
        return None
    if end_value is None:
        return float(start_value)
    if start_value is None:
        return float(end_value)
    if abs(float(end_value) - float(start_value)) > 1e-9:
        raise StatSnapshotError(
            "Per-wave composition missing for stat "
            f"{stat_id}: START_OF_RUN={start_value} END_OF_RUN={end_value}."
        )
    return float(start_value)


def _extract_value(stat_input: StatInput, engine_result: StatEngineResult) -> float:
    if stat_input.derived_value is not None:
        return float(stat_input.derived_value)

    has_components = any(
        value is not None
        for value in (
            stat_input.base_value,
            stat_input.loadout_delta,
            stat_input.enhancement_multiplier,
            stat_input.tier_rule_delta,
            stat_input.tier_rule_multiplier,
        )
    )
    if not has_components:
        raise StatSnapshotError(
            f"Missing value for AT_WAVE stat input {stat_input.stat_id}."
        )

    base_value = float(stat_input.base_value or 0.0)
    loadout_delta = float(stat_input.loadout_delta or 0.0)
    enhancement_multiplier = float(stat_input.enhancement_multiplier or 1.0)
    tier_delta = float(stat_input.tier_rule_delta or 0.0)
    tier_multiplier = float(stat_input.tier_rule_multiplier or 1.0)
    return ((base_value + loadout_delta) * enhancement_multiplier + tier_delta) * tier_multiplier


def _build_engine_with_rules(
    registry: StatRegistry,
    tier_rules: TierRulesResult | None,
):
    from tower_sim.engines.stat_engine import StatEngine

    engine = StatEngine(registry=registry)
    if tier_rules is None:
        return engine

    class _Wrapper(StatEngine):
        def build(self, inputs: Iterable[StatInput]):  # type: ignore[override]
            return engine.build_with_tier_rules(inputs, tier_rules)

    return _Wrapper(registry=registry)
