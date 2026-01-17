from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, Optional, Sequence

from tower_sim.ids_state import IdsState
from tower_sim.libs import labs_lib, workshop_lib
from tower_sim.stat_registry import Phase, StatRegistry, default_registry
from tower_sim.statbook import CanonicalStatBook, CanonicalStatRow
from tower_sim.statbook_builder import build_canonical_statbook
from tower_sim.wiki.enemy_level_skip import workshop_level_to_chance


class StatEngineError(RuntimeError):
    pass


class MissingStatDataError(StatEngineError):
    pass


@dataclass(frozen=True)
class StatSnapshot:
    phase: Phase
    stats: Dict[str, Decimal]


@dataclass(frozen=True)
class RunStats:
    start: StatSnapshot
    end: StatSnapshot


@dataclass(frozen=True)
class StatEngineResult:
    run_stats: RunStats
    statbook: CanonicalStatBook


SUPPORTED_STAT_IDS: Sequence[str] = (
    "tower_hp",
    "tower_regen",
    "wall_regen",
    "eals_pct",
    "ehls_pct",
)


_WORKSHOP_SPECS = {
    "tower_hp": ("Health", "Health", "WSValues"),
    "tower_regen": ("Health Regen", "HPregen", "WSValues"),
}


_LAB_SPECS = {
    "tower_hp": ("Health", "raw_number"),
    "tower_regen": ("Health Regen", "raw_number"),
    "wall_regen": ("Wall Regen", "percent"),
    "eals_pct": ("Enemy Attack Level Skip", "percent_points"),
    "ehls_pct": ("Enemy Health Level Skip", "percent_points"),
}


def build_stat_engine(
    ids_state: IdsState,
    *,
    registry: Optional[StatRegistry] = None,
    workshop_tables: Optional[workshop_lib.WorkshopTables] = None,
    labs_table: Optional[Dict[str, labs_lib.LabLevels]] = None,
    include_stat_ids: Optional[Sequence[str]] = None,
    strict: bool = True,
) -> StatEngineResult:
    resolved_registry = registry or default_registry()
    resolved_tables = workshop_tables or workshop_lib.load_workshop_tables()
    resolved_labs = labs_table or labs_lib.load_labs_values()

    stat_ids = list(include_stat_ids or SUPPORTED_STAT_IDS)

    missing = [stat_id for stat_id in stat_ids if stat_id not in SUPPORTED_STAT_IDS]
    if missing:
        raise MissingStatDataError(
            "Unsupported stat IDs requested: " + ", ".join(sorted(missing))
        )

    rows: list[CanonicalStatRow] = []
    start_stats: Dict[str, Decimal] = {}
    end_stats: Dict[str, Decimal] = {}

    for stat_id in stat_ids:
        resolved_registry.validate_stat_id(stat_id)
        start_value, start_provenance = _compute_stat_value(
            stat_id=stat_id,
            phase=Phase.START_OF_RUN,
            ids_state=ids_state,
            tables=resolved_tables,
            labs=resolved_labs,
            start_stats=start_stats,
            end_stats=end_stats,
        )
        end_value, end_provenance = _compute_stat_value(
            stat_id=stat_id,
            phase=Phase.END_OF_RUN,
            ids_state=ids_state,
            tables=resolved_tables,
            labs=resolved_labs,
            start_stats=start_stats,
            end_stats=end_stats,
        )

        start_stats[stat_id] = start_value
        end_stats[stat_id] = end_value

        rows.append(
            _row_for_phase(
                stat_id=stat_id,
                phase=Phase.START_OF_RUN,
                value=start_value,
                provenance=start_provenance,
            )
        )
        rows.append(
            _row_for_phase(
                stat_id=stat_id,
                phase=Phase.END_OF_RUN,
                value=end_value,
                provenance=end_provenance,
            )
        )

    statbook = build_canonical_statbook(rows, registry=resolved_registry)
    run_stats = RunStats(
        start=StatSnapshot(phase=Phase.START_OF_RUN, stats=start_stats),
        end=StatSnapshot(phase=Phase.END_OF_RUN, stats=end_stats),
    )
    return StatEngineResult(run_stats=run_stats, statbook=statbook)


def _compute_stat_value(
    *,
    stat_id: str,
    phase: Phase,
    ids_state: IdsState,
    tables: workshop_lib.WorkshopTables,
    labs: Dict[str, labs_lib.LabLevels],
    start_stats: Dict[str, Decimal],
    end_stats: Dict[str, Decimal],
) -> tuple[Decimal, str]:
    if stat_id in ("tower_hp", "tower_regen"):
        return _compute_workshop_stat(
            stat_id=stat_id,
            phase=phase,
            ids_state=ids_state,
            tables=tables,
            labs=labs,
        )
    if stat_id == "wall_regen":
        return _compute_wall_regen(
            phase=phase,
            ids_state=ids_state,
            labs=labs,
            start_stats=start_stats,
            end_stats=end_stats,
        )
    if stat_id in ("eals_pct", "ehls_pct"):
        return _compute_level_skip_stat(
            stat_id=stat_id,
            phase=phase,
            ids_state=ids_state,
            labs=labs,
        )
    raise MissingStatDataError(f"No stat computation defined for {stat_id!r}.")


def _compute_workshop_stat(
    *,
    stat_id: str,
    phase: Phase,
    ids_state: IdsState,
    tables: workshop_lib.WorkshopTables,
    labs: Dict[str, labs_lib.LabLevels],
) -> tuple[Decimal, str]:
    entry_name, table_key, section = _WORKSHOP_SPECS[stat_id]
    entry = ids_state.workshop.entries.get(entry_name)
    if entry is None:
        raise MissingStatDataError(f"Missing workshop entry for {entry_name!r}.")
    level = _workshop_level(entry, phase)
    base_value = _to_decimal(
        _workshop_value(table_key, level, tables, section=section)
    )

    lab_name, expected_unit = _LAB_SPECS[stat_id]
    multiplier, lab_provenance = _lab_multiplier(
        lab_name=lab_name,
        expected_unit=expected_unit,
        level=_lab_level(ids_state, lab_name),
        labs=labs,
    )
    value = (base_value * multiplier).quantize(Decimal("1.0000000000"))
    provenance = f"{_workshop_provenance(section, table_key, level)}"
    if lab_provenance:
        provenance = f"{provenance}; {lab_provenance}"
    return value, provenance


def _compute_wall_regen(
    *,
    phase: Phase,
    ids_state: IdsState,
    labs: Dict[str, labs_lib.LabLevels],
    start_stats: Dict[str, Decimal],
    end_stats: Dict[str, Decimal],
) -> tuple[Decimal, str]:
    base_regen = start_stats.get("tower_regen") if phase == Phase.START_OF_RUN else end_stats.get("tower_regen")
    if base_regen is None:
        raise MissingStatDataError("tower_regen must be computed before wall_regen.")

    lab_name, expected_unit = _LAB_SPECS["wall_regen"]
    lab_value, lab_provenance = _lab_value(
        lab_name=lab_name,
        expected_unit=expected_unit,
        level=_lab_level(ids_state, lab_name),
        labs=labs,
    )
    if lab_value is None:
        value = Decimal("0")
        provenance = "No Wall Regen lab level present; wall_regen set to 0."
        return value, provenance

    fraction = (lab_value / Decimal("100"))
    value = (base_regen * fraction).quantize(Decimal("1.0000000000"))
    provenance = f"labs_values_v1.csv:{lab_name}@lvl{_lab_level(ids_state, lab_name)}; wiki:Wall_Labs/Wall_Regen"
    return value, provenance


def _compute_level_skip_stat(
    *,
    stat_id: str,
    phase: Phase,
    ids_state: IdsState,
    labs: Dict[str, labs_lib.LabLevels],
) -> tuple[Decimal, str]:
    if stat_id == "eals_pct":
        entry_name = "Enemy Attack Level Skip"
    else:
        entry_name = "Enemy Health Level Skip"
    entry = ids_state.workshop.entries.get(entry_name)
    if entry is None:
        raise MissingStatDataError(f"Missing workshop entry for {entry_name!r}.")
    level = _workshop_level(entry, phase)
    base_chance = Decimal(str(workshop_level_to_chance(level)))

    lab_name, expected_unit = _LAB_SPECS[stat_id]
    lab_value, lab_provenance = _lab_value(
        lab_name=lab_name,
        expected_unit=expected_unit,
        level=_lab_level(ids_state, lab_name),
        labs=labs,
    )
    lab_add = Decimal("0") if lab_value is None else (lab_value / Decimal("100"))
    value = (base_chance + lab_add).quantize(Decimal("1.0000000000"))

    provenance = f"wiki:Enemy_Level_Skip@lvl{level}"
    if lab_provenance:
        provenance = f"{provenance}; {lab_provenance}"
    return value, provenance


def _row_for_phase(
    *,
    stat_id: str,
    phase: Phase,
    value: Decimal,
    provenance: str,
) -> CanonicalStatRow:
    zero = Decimal("0")
    one = Decimal("1")
    return CanonicalStatRow(
        stat_id=stat_id,
        phase=phase,
        base_value=value,
        loadout_delta_modules=zero,
        loadout_delta_cards=zero,
        loadout_delta_bots=zero,
        loadout_delta_guardians=zero,
        loadout_delta_other=zero,
        enhancement_multiplier=one,
        tier_rule_delta_or_multiplier=zero,
        final_value=value,
        provenance=provenance,
    )


def _workshop_level(entry: object, phase: Phase) -> int:
    coin_level = getattr(entry, "coin_level", None)
    max_level = getattr(entry, "max_level", None)
    value = coin_level if phase == Phase.START_OF_RUN else (max_level or coin_level)
    if value is None:
        raise MissingStatDataError("Missing workshop level for entry.")
    try:
        return int(float(value))
    except ValueError as exc:
        raise MissingStatDataError(f"Invalid workshop level value: {value}") from exc


def _lab_level(ids_state: IdsState, lab_name: str) -> int:
    raw_level = ids_state.labs.labs.get(lab_name)
    if raw_level is None or str(raw_level).strip() == "":
        return 0
    try:
        return int(float(raw_level))
    except ValueError as exc:
        raise MissingStatDataError(f"Invalid lab level for {lab_name!r}: {raw_level}") from exc


def _lab_multiplier(
    *,
    lab_name: str,
    expected_unit: str,
    level: int,
    labs: Dict[str, labs_lib.LabLevels],
) -> tuple[Decimal, str]:
    lab_value, provenance = _lab_value(
        lab_name=lab_name,
        expected_unit=expected_unit,
        level=level,
        labs=labs,
    )
    if lab_value is None:
        return Decimal("1"), ""
    if expected_unit == "raw_number":
        return lab_value, provenance
    if expected_unit == "percent":
        return Decimal("1") + (lab_value / Decimal("100")), provenance
    raise MissingStatDataError(
        f"Unsupported lab unit {expected_unit!r} for multiplier computation."
    )


def _lab_value(
    *,
    lab_name: str,
    expected_unit: str,
    level: int,
    labs: Dict[str, labs_lib.LabLevels],
) -> tuple[Optional[Decimal], str]:
    if lab_name not in labs:
        raise MissingStatDataError(f"Missing labs table for {lab_name!r}.")
    lab = labs[lab_name]
    if lab.unit != expected_unit:
        raise MissingStatDataError(
            f"Lab {lab_name!r} unit mismatch: expected {expected_unit}, got {lab.unit}."
        )
    if level <= 0:
        return None, ""
    if level not in lab.levels:
        raise MissingStatDataError(f"Lab {lab_name!r} missing level {level}.")
    value = Decimal(str(lab.levels[level]))
    provenance = f"labs_values_v1.csv:{lab_name}@lvl{level}"
    return value, provenance


def _workshop_provenance(section: str, stat_key: str, level: int) -> str:
    if section == "WSValues":
        return f"WSValues.csv:{stat_key}@lvl{level}"
    return f"DVT_Workshop.csv:{section}:{stat_key}@lvl{level}"


def _to_decimal(value: str) -> Decimal:
    normalized = value.replace(",", "").strip()
    return Decimal(normalized)


def _workshop_value(
    stat_key: str,
    level: int,
    tables: workshop_lib.WorkshopTables,
    *,
    section: str,
) -> str:
    try:
        return workshop_lib.workshop_value(stat_key, level, tables, section=section)
    except KeyError as exc:
        raise MissingStatDataError(
            f"Missing workshop value for {stat_key!r} at level {level} in {section}."
        ) from exc
