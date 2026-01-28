from __future__ import annotations

from tower_sim.ids_state import IdsState
from tower_sim.stat_registry import Phase, StatRegistry, default_registry
from tower_sim.statbook import CanonicalStatBook, CanonicalStatRow, StatBook, StatRow


PHASE_START = Phase.START_OF_RUN.value
PHASE_END = Phase.END_OF_RUN.value


def _optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def build_statbook(ids_state: IdsState) -> StatBook:
    rows: list[StatRow] = []
    for name, level in ids_state.labs.labs.items():
        level_value = _optional_str(level)
        rows.append(
            StatRow(
                stat_id=name,
                phase=PHASE_START,
                base_value=level_value,
                loadout_delta=None,
                enhancement_multiplier=None,
                tier_rule_delta_or_multiplier=None,
                final_value=level_value,
                provenance="ids:labs",
            )
        )
        rows.append(
            StatRow(
                stat_id=name,
                phase=PHASE_END,
                base_value=level_value,
                loadout_delta=None,
                enhancement_multiplier=None,
                tier_rule_delta_or_multiplier=None,
                final_value=level_value,
                provenance="ids:labs (end-of-run placeholder)",
            )
        )
    for entry in ids_state.workshop.entries.values():
        coin_level_value = _optional_str(entry.coin_level)
        max_value = _optional_str(entry.max_level) or coin_level_value
        rows.append(
            StatRow(
                stat_id=entry.name,
                phase=PHASE_START,
                base_value=coin_level_value,
                loadout_delta=None,
                enhancement_multiplier=None,
                tier_rule_delta_or_multiplier=None,
                final_value=coin_level_value,
                provenance="ids:workshop",
            )
        )
        rows.append(
            StatRow(
                stat_id=entry.name,
                phase=PHASE_END,
                base_value=coin_level_value,
                loadout_delta=None,
                enhancement_multiplier=None,
                tier_rule_delta_or_multiplier=None,
                final_value=max_value,
                provenance="ids:workshop (max level fallback)",
            )
        )
    return StatBook(rows=rows)


def build_canonical_statbook(
    rows: list[CanonicalStatRow],
    registry: StatRegistry | None = None,
) -> CanonicalStatBook:
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
    return CanonicalStatBook(rows=rows)
