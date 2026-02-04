from __future__ import annotations

from tower_sim.util.account_snapshot import AccountSnapshot
from tower_sim.registry.stat_registry import Phase, StatRegistry, default_registry
from tower_sim.util.statbook import CanonicalStatBook, CanonicalStatRow, StatBook, StatRow

PHASE_START = Phase.START_OF_RUN
PHASE_END = Phase.END_OF_RUN


def build_statbook(snapshot: AccountSnapshot) -> StatBook:
    rows: list[StatRow] = []
    for name, level in snapshot.labs.items():
        level_value = _optional_str(level)
        rows.append(
            _make_row(
                stat_id=name,
                phase=PHASE_START,
                value=level_value,
                provenance="ids:labs",
            )
        )
        rows.append(
            _make_row(
                stat_id=name,
                phase=PHASE_END,
                value=level_value,
                provenance="ids:labs",
            )
        )
    for entry in snapshot.workshop.values():
        coin_level_value = _optional_str(entry.coin_level)
        max_value = _optional_str(entry.max_level) or coin_level_value
        rows.append(
            _make_row(
                stat_id=entry.name,
                phase=PHASE_START,
                value=coin_level_value,
                provenance="ids:workshop",
            )
        )
        rows.append(
            _make_row(
                stat_id=entry.name,
                phase=PHASE_END,
                value=max_value,
                provenance="ids:workshop",
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


def _make_row(
    stat_id: str,
    phase: Phase,
    value: str | None,
    provenance: str,
) -> StatRow:
    return StatRow(
        stat_id=stat_id,
        phase=phase.value,
        base_value=value,
        loadout_delta=None,
        enhancement_multiplier=None,
        tier_rule_delta_or_multiplier=None,
        final_value=value,
        provenance=provenance,
    )


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value)
