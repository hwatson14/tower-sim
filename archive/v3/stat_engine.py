"""v3 stat engine.

Deterministic v3-local stat composition engine.
It composes stat inputs into per-input rows and per-phase resolved values without
calling the legacy/common `tower_sim.engines.stat_engine.StatEngine` runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase, StatKind, default_registry


@dataclass(frozen=True)
class V3StatRow:
    stat_id: str
    phase: Phase
    base_value: Decimal | None
    loadout_delta: Decimal | None
    enhancement_multiplier: Decimal | None
    tier_rule_delta: Decimal | None
    tier_rule_multiplier: Decimal | None
    derived_value: Decimal | None
    final_value: Decimal
    provenance: str


@dataclass(frozen=True)
class V3StatEngineResult:
    rows: list[V3StatRow]
    run_stats: dict[Phase, dict[str, float]]


class V3StatEngineError(RuntimeError):
    pass


class V3StatEngine:
    def __init__(self) -> None:
        self._registry = default_registry()

    def build(self, inputs: Iterable[StatInput]) -> V3StatEngineResult:
        rows: list[V3StatRow] = []
        merged: dict[tuple[Phase, str], float] = {}

        for item in inputs:
            stat_def = self._registry.get(item.stat_id)
            if item.phase not in stat_def.allowed_phases:
                raise V3StatEngineError(
                    f"Stat {item.stat_id} does not allow phase {item.phase.value}."
                )

            final_value = self._resolve_input(item, stat_kind=stat_def.kind)
            row = V3StatRow(
                stat_id=item.stat_id,
                phase=item.phase,
                base_value=_decimal_optional(item.base_value),
                loadout_delta=_decimal_optional(item.loadout_delta),
                enhancement_multiplier=_decimal_optional(item.enhancement_multiplier),
                tier_rule_delta=_decimal_optional(item.tier_rule_delta),
                tier_rule_multiplier=_decimal_optional(item.tier_rule_multiplier),
                derived_value=_decimal_optional(item.derived_value),
                final_value=Decimal(str(final_value)),
                provenance=item.provenance or "derived:v3_stat_engine",
            )
            rows.append(row)
            key = (item.phase, item.stat_id)
            merged[key] = merged.get(key, 0.0) + final_value

        run_stats: dict[Phase, dict[str, float]] = {}
        for (phase, stat_id), value in merged.items():
            run_stats.setdefault(phase, {})[stat_id] = float(value)
        return V3StatEngineResult(rows=rows, run_stats=run_stats)

    def _resolve_input(self, item: StatInput, *, stat_kind: StatKind) -> float:
        if item.derived_value is not None:
            if stat_kind != StatKind.DERIVED:
                raise V3StatEngineError(f"Stat {item.stat_id} has derived_value but is not DERIVED.")
            has_non_derived_components = (
                item.base_value is not None
                or item.loadout_delta is not None
                or item.tier_rule_delta is not None
                or item.tier_rule_multiplier is not None
                or (item.enhancement_multiplier is not None and float(item.enhancement_multiplier) != 1.0)
            )
            if has_non_derived_components:
                raise V3StatEngineError(
                    f"Derived stat {item.stat_id} cannot mix derived_value with additive/multiplier components."
                )
            return float(item.derived_value)

        if (
            item.base_value is None
            and item.loadout_delta is None
            and item.enhancement_multiplier is None
            and item.tier_rule_delta is None
            and item.tier_rule_multiplier is None
        ):
            raise V3StatEngineError(f"Missing base/loadout data for stat_id {item.stat_id}.")

        base_value = float(item.base_value or 0.0)
        loadout_delta = float(item.loadout_delta or 0.0)
        enhancement_multiplier = float(item.enhancement_multiplier or 1.0)

        resolved = (base_value + loadout_delta) * enhancement_multiplier
        tier_delta = item.tier_rule_delta
        tier_mult = item.tier_rule_multiplier
        if tier_delta is not None and tier_mult is not None:
            raise V3StatEngineError(
                f"Stat {item.stat_id} cannot have both tier_rule_delta and tier_rule_multiplier."
            )
        if tier_delta is not None:
            resolved += float(tier_delta)
        if tier_mult is not None:
            resolved *= float(tier_mult)
        return resolved


def _decimal_optional(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
