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
            phase_values.setdefault(stat_input.phase, {})[stat_input.stat_id] = float(
                row.final_value
            )

        run_stats = {
            phase: RunStats(phase=phase, values=values)
            for phase, values in phase_values.items()
        }
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
        tier_rule = _format_tier_rule(
            stat_input.tier_rule_delta, stat_input.tier_rule_multiplier
        )

        if stat_input.derived_value is not None:
            _validate_derived(stat_input, stat_kind)
            return StatRow(
                stat_id=stat_input.stat_id,
                phase=stat_input.phase.value,
                base_value=_format_optional(stat_input.base_value),
                loadout_delta=_format_optional(stat_input.loadout_delta),
                enhancement_multiplier=_format_optional(stat_input.enhancement_multiplier),
                tier_rule_delta_or_multiplier=tier_rule,
                final_value=_format_optional(stat_input.derived_value),
                provenance=stat_input.provenance,
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
            phase=stat_input.phase.value,
            base_value=_format_optional(stat_input.base_value),
            loadout_delta=_format_optional(stat_input.loadout_delta),
            enhancement_multiplier=_format_optional(stat_input.enhancement_multiplier),
            tier_rule_delta_or_multiplier=tier_rule,
            final_value=_format_optional(tiered),
            provenance=stat_input.provenance,
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


def _format_optional(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _format_tier_rule(
    delta: Optional[float],
    multiplier: Optional[float],
) -> Optional[str]:
    if delta is not None and multiplier is not None:
        raise ValueError("Tier rule cannot be both delta and multiplier.")
    if delta is not None:
        return f"delta:{delta}"
    if multiplier is not None:
        return f"mult:{multiplier}"
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
