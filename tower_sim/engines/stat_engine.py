from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from tower_sim.registry.stat_registry import Phase, StatKind, StatRegistry
from tower_sim.util.statbook import StatBook, StatRow
from tower_sim.engines.tier_rule_apply import apply_tier_rules_to_inputs
from tower_sim.engines.tier_rules import TierRulesResult
from tower_sim.engines.wave_engine import RunWaveState


@dataclass(frozen=True)
class StatInput:
    stat_id: str
    phase: Phase
    base_value: Optional[float] = None
    loadout_delta: Optional[float] = None
    enhancement_multiplier: Optional[float] = None
    tier_rule_delta: Optional[float] = None
    tier_rule_multiplier: Optional[float] = None
    derived_value: Optional[float] = None
    provenance: Optional[str] = None


@dataclass(frozen=True)
class RunStats:
    phase: Phase
    values: Dict[str, float]


@dataclass(frozen=True)
class StatEngineResult:
    statbook: StatBook
    run_stats: Dict[Phase, RunStats]


class StatEngine:
    def __init__(self, registry: StatRegistry) -> None:
        self._registry = registry

    def build(
        self,
        inputs: Iterable[StatInput],
        wave_state: RunWaveState | None = None,
    ) -> StatEngineResult:
        rows: list[StatRow] = []
        phase_values: Dict[Phase, Dict[str, float]] = {}
        resolved_inputs = list(inputs)
        if wave_state is not None:
            resolved_inputs = self._append_wave_state_inputs(
                resolved_inputs, wave_state
            )
        for stat_input in resolved_inputs:
            stat_def = self._registry.get(stat_input.stat_id)
            if stat_input.phase not in stat_def.allowed_phases:
                raise ValueError(
                    f"Stat {stat_input.stat_id} does not allow phase {stat_input.phase}."
                )
            row = self._build_row(stat_input, stat_def.kind)
            rows.append(row)
            if row.final_value is not None:
                phase_values.setdefault(stat_input.phase, {})[stat_input.stat_id] = float(row.final_value)

        run_stats = _build_run_stats_from_inputs(resolved_inputs)
        return StatEngineResult(statbook=StatBook(rows=rows), run_stats=run_stats)

    def build_with_tier_rules(
        self,
        inputs: Iterable[StatInput],
        tier_rules: TierRulesResult,
        wave_state: RunWaveState | None = None,
    ) -> StatEngineResult:
        adjusted = apply_tier_rules_to_inputs(inputs, tier_rules)
        return self.build(adjusted, wave_state=wave_state)

    def _build_row(self, stat_input: StatInput, stat_kind: StatKind) -> StatRow:
        if stat_input.derived_value is not None:
            _validate_derived(stat_input, stat_kind)
            return StatRow(
                stat_id=stat_input.stat_id,
                phase=stat_input.phase,
                base_value=_decimal_optional(stat_input.base_value),
                loadout_delta_modules=_loadout_component(stat_input.loadout_delta, component="zero"),
                loadout_delta_cards=_loadout_component(stat_input.loadout_delta, component="zero"),
                loadout_delta_bots=_loadout_component(stat_input.loadout_delta, component="zero"),
                loadout_delta_guardians=_loadout_component(stat_input.loadout_delta, component="zero"),
                loadout_delta_other=_loadout_component(stat_input.loadout_delta, component="value"),
                enhancement_multiplier=_decimal_optional(stat_input.enhancement_multiplier),
                tier_rule_delta_or_multiplier=_decimal_optional(_tier_rule_numeric(stat_input.tier_rule_delta, stat_input.tier_rule_multiplier)),
                final_value=_decimal_optional(stat_input.derived_value),
                provenance=stat_input.provenance or "derived:stat_engine",
            )

        if (
            stat_input.base_value is None
            and stat_input.loadout_delta is None
            and stat_input.enhancement_multiplier is None
            and stat_input.tier_rule_delta is None
            and stat_input.tier_rule_multiplier is None
        ):
            raise ValueError(
                f"Missing base/loadout data for stat_id {stat_input.stat_id}."
            )

        base_value = stat_input.base_value or 0.0
        loadout_delta = stat_input.loadout_delta or 0.0
        enhancement_multiplier = stat_input.enhancement_multiplier or 1.0

        combined = base_value + loadout_delta
        enhanced = combined * enhancement_multiplier
        tiered = _apply_tier_rule(
            enhanced, stat_input.tier_rule_delta, stat_input.tier_rule_multiplier
        )

        return StatRow(
            stat_id=stat_input.stat_id,
            phase=stat_input.phase,
            base_value=_decimal_optional(stat_input.base_value),
            loadout_delta_modules=_loadout_component(stat_input.loadout_delta, component="zero"),
            loadout_delta_cards=_loadout_component(stat_input.loadout_delta, component="zero"),
            loadout_delta_bots=_loadout_component(stat_input.loadout_delta, component="zero"),
            loadout_delta_guardians=_loadout_component(stat_input.loadout_delta, component="zero"),
            loadout_delta_other=_loadout_component(stat_input.loadout_delta, component="value"),
            enhancement_multiplier=_decimal_optional(stat_input.enhancement_multiplier),
            tier_rule_delta_or_multiplier=_decimal_optional(_tier_rule_numeric(stat_input.tier_rule_delta, stat_input.tier_rule_multiplier)),
            final_value=_decimal_optional(tiered),
            provenance=stat_input.provenance or "derived:stat_engine",
        )

    def _append_wave_state_inputs(
        self,
        inputs: list[StatInput],
        wave_state: RunWaveState,
    ) -> list[StatInput]:
        reserved = {
            ("wave_attack_index", Phase.AT_WAVE),
            ("wave_health_index", Phase.AT_WAVE),
        }
        duplicates = [
            f"{item.stat_id}:{item.phase.value}"
            for item in inputs
            if (item.stat_id, item.phase) in reserved
        ]
        if duplicates:
            raise ValueError(
                "Wave-state-derived stat inputs already provided: "
                + ", ".join(sorted(duplicates))
            )
        return inputs + [
            StatInput(
                stat_id="wave_attack_index",
                phase=Phase.AT_WAVE,
                derived_value=float(wave_state.W_attack),
                provenance="derived:wave_engine",
            ),
            StatInput(
                stat_id="wave_health_index",
                phase=Phase.AT_WAVE,
                derived_value=float(wave_state.W_health),
                provenance="derived:wave_engine",
            ),
        ]


def _build_run_stats_from_inputs(inputs: list[StatInput]) -> Dict[Phase, RunStats]:
    merged: Dict[tuple[Phase, str], StatInput] = {}
    for item in inputs:
        key = (item.phase, item.stat_id)
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
            continue
        merged[key] = _merge_stat_input_for_run_stats(existing, item)

    phase_values: Dict[Phase, Dict[str, float]] = {}
    for (phase, stat_id), item in merged.items():
        phase_values.setdefault(phase, {})[stat_id] = _resolve_input_value(item)
    return {
        phase: RunStats(phase=phase, values=values)
        for phase, values in phase_values.items()
    }


def _merge_stat_input_for_run_stats(existing: StatInput, item: StatInput) -> StatInput:
    if existing.derived_value is not None or item.derived_value is not None:
        existing_has_components = any(
            value is not None
            for value in (
                existing.base_value,
                existing.loadout_delta,
                existing.enhancement_multiplier,
                existing.tier_rule_delta,
                existing.tier_rule_multiplier,
            )
        )
        item_has_components = any(
            value is not None
            for value in (
                item.base_value,
                item.loadout_delta,
                item.enhancement_multiplier,
                item.tier_rule_delta,
                item.tier_rule_multiplier,
            )
        )
        if existing_has_components or item_has_components:
            raise ValueError(
                f"Derived stat {existing.stat_id} cannot mix with base/loadout rows."
            )
        return StatInput(
            stat_id=existing.stat_id,
            phase=existing.phase,
            derived_value=float(item.derived_value if item.derived_value is not None else existing.derived_value),
            provenance=item.provenance or existing.provenance,
        )

    base = None
    if existing.base_value is not None or item.base_value is not None:
        base = float(existing.base_value or 0.0) + float(item.base_value or 0.0)

    loadout_delta = None
    if existing.loadout_delta is not None or item.loadout_delta is not None:
        loadout_delta = float(existing.loadout_delta or 0.0) + float(item.loadout_delta or 0.0)

    enhancement_multiplier = None
    if existing.enhancement_multiplier is not None or item.enhancement_multiplier is not None:
        enhancement_multiplier = float(existing.enhancement_multiplier or 1.0) * float(item.enhancement_multiplier or 1.0)

    tier_rule_delta = None
    if existing.tier_rule_delta is not None or item.tier_rule_delta is not None:
        tier_rule_delta = float(existing.tier_rule_delta or 0.0) + float(item.tier_rule_delta or 0.0)

    tier_rule_multiplier = None
    if existing.tier_rule_multiplier is not None or item.tier_rule_multiplier is not None:
        tier_rule_multiplier = float(existing.tier_rule_multiplier or 1.0) * float(item.tier_rule_multiplier or 1.0)

    if tier_rule_delta is not None and tier_rule_multiplier is not None:
        raise ValueError(
            f"Tier rule cannot be both delta and multiplier for stat_id {existing.stat_id}."
        )

    return StatInput(
        stat_id=existing.stat_id,
        phase=existing.phase,
        base_value=base,
        loadout_delta=loadout_delta,
        enhancement_multiplier=enhancement_multiplier,
        tier_rule_delta=tier_rule_delta,
        tier_rule_multiplier=tier_rule_multiplier,
        provenance=item.provenance or existing.provenance,
    )


def _resolve_input_value(stat_input: StatInput) -> float:
    if stat_input.derived_value is not None:
        return float(stat_input.derived_value)
    base_value = float(stat_input.base_value or 0.0)
    loadout_delta = float(stat_input.loadout_delta or 0.0)
    enhancement_multiplier = float(stat_input.enhancement_multiplier or 1.0)
    enhanced = (base_value + loadout_delta) * enhancement_multiplier
    return _apply_tier_rule(
        enhanced,
        stat_input.tier_rule_delta,
        stat_input.tier_rule_multiplier,
    )


from decimal import Decimal


def _decimal_optional(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _loadout_component(loadout_delta: Optional[float], *, component: str) -> Optional[Decimal]:
    if loadout_delta is None:
        return None
    if component == "zero":
        return Decimal(0)
    if component == "value":
        return Decimal(str(loadout_delta))
    raise ValueError(f"Unknown loadout component selector: {component}")


def _tier_rule_numeric(delta: Optional[float], multiplier: Optional[float]) -> Optional[float]:
    if delta is not None and multiplier is not None:
        raise ValueError("Tier rule cannot be both delta and multiplier.")
    if delta is not None:
        return delta
    if multiplier is not None:
        return multiplier
    return None


def _apply_tier_rule(
    value: float, delta: Optional[float], multiplier: Optional[float]
) -> float:
    if delta is not None and multiplier is not None:
        raise ValueError("Tier rule cannot be both delta and multiplier.")
    if delta is not None:
        return value + delta
    if multiplier is not None:
        return value * multiplier
    return value


def _validate_derived(stat_input: StatInput, stat_kind: StatKind) -> None:
    if stat_kind != StatKind.DERIVED:
        raise ValueError(
            f"Stat {stat_input.stat_id} is not marked as derived in registry."
        )
    if (
        stat_input.base_value is not None
        or stat_input.loadout_delta is not None
        or stat_input.enhancement_multiplier is not None
        or stat_input.tier_rule_delta is not None
        or stat_input.tier_rule_multiplier is not None
    ):
        raise ValueError(
            f"Derived stat {stat_input.stat_id} cannot mix base/loadout inputs."
        )
