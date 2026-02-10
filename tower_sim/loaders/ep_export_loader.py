from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Dict, Mapping

from tower_sim.registry.ep_formula_registry import load_ep_formula_registry


# Provenance: tests/fixtures/tower-sim-data/EP_Export.csv from Harry Effective Paths export.
_HUMAN_SUFFIX_SCALE: Dict[str, float] = {
    "K": 1e3,
    "M": 1e6,
    "B": 1e9,
    "T": 1e12,
    "q": 1e15,
    "Q": 1e18,
    "O": 1e27,
}

# Row contract: every exported EP row must have a deterministic source reference.
# Sources use prefixes:
# - ep_formula:<formula_id>            (tables/registry/ep_formulas/formula_library.yaml)
# - ep_mechanic:<lambda_name>          (tables/registry/ep_formulas/mechanics_library.yaml)
# - stat_input:<stat_id>               (compiled deterministic stat input)
# - ehp_slice:<stat_key>               (deterministic eHP stat evaluator output)
# - ep_sheet:<Sheet!Cell>               (authoritative user-provided EP workbook cell formula)
_ROWS_WITHOUT_DEFINITIVE_FORMULAS: set[tuple[str, str]] = set()

_EP_ROW_SOURCES: Dict[tuple[str, str], tuple[str, str]] = {
    ("edmg", "edmg"): ("ep_formula:ep_edamage_ef5", "ep_formula.eval.edmg"),
    ("edmg", "damage"): ("ep_formula:ep_edamage_cr5", "stat_inputs.workshop_damage"),
    ("edmg", "attack_speed"): ("ep_mechanic:EPD_ASPD", "ep_formula.eval.attack_speed"),
    ("edmg", "crit_chance"): ("ep_mechanic:EPD_CRIT_CHANCE", "stat_inputs.workshop_critical_chance"),
    ("edmg", "crit_factor"): ("ep_formula:ep_edamage_dc5", "ep_formula.eval.crit_factor"),
    ("edmg", "range"): ("ep_mechanic:EPD_RANGE", "stat_inputs.workshop_range_meters"),
    ("edmg", "damage_per_meter"): ("ep_formula:ep_edamage_dl5", "stat_inputs.workshop_damage_per_meter"),
    ("edmg", "multishot_chance"): ("ep_mechanic:EPD_MSC", "stat_inputs.workshop_multishot_chance"),
    ("edmg", "multishot_targets"): ("ep_mechanic:EPD_MST", "stat_inputs.workshop_multishot_targets"),
    ("edmg", "rapid_fire_chance"): ("ep_mechanic:EPD_RFC", "stat_inputs.workshop_rapid_fire_chance"),
    ("edmg", "rapid_fire_duration"): ("ep_mechanic:EPD_RFD", "stat_inputs.workshop_rapid_fire_duration"),
    ("edmg", "bounce_shot_chance"): ("ep_mechanic:EPD_BSC", "stat_inputs.workshop_bounce_shot_chance"),
    ("edmg", "bounce_shot_targets"): ("ep_mechanic:EPD_BST", "stat_inputs.workshop_bounce_shot_targets"),
    ("edmg", "super_crit_chance"): ("ep_formula:ep_edamage_dm5", "ep_formula.eval.super_crit_chance"),
    ("edmg", "super_crit_multiplier"): ("ep_formula:ep_edamage_dp5", "ep_formula.eval.super_crit_multiplier"),
    ("edmg", "max_rend_mult"): ("ep_mechanic:EPD_MAXREND", "stat_inputs.workshop_rend_armor_mult"),
    ("edmg", "recovery_package_chance"): ("stat_input:workshop_recovery_packages", "stat_inputs.workshop_recovery_packages"),
    ("ehp", "ehp"): ("ep_sheet:eHP!CG5", "ep_formula.eval.ehp"),
    ("ehp", "health"): ("ep_mechanic:EPH_HEALTH", "ehp_slice.stats.tower_hp"),
    ("ehp", "health_regen"): ("ep_mechanic:EPH_REGEN", "ehp_slice.stats.tower_regen"),
    ("ehp", "defense_absolute"): ("ep_mechanic:EPH_DABS", "stat_inputs.workshop_defense_absolute"),
    ("ehp", "defense_percent"): ("ep_mechanic:EPH_DEF_PCT", "ehp_slice.stats.def_pct"),
    ("ehp", "wall_health"): ("ep_mechanic:EPH_WALL_HEALTH", "ehp_slice.stats.wall_hp"),
    ("ehp", "wall_fortification"): ("ep_mechanic:EPH_ARMOR", "ep_formula.eval.wall_fortification"),
    ("ehp", "wall_regen"): ("ep_mechanic:EPH_WALL_REGEN", "ehp_slice.stats.wall_regen"),
    ("ehp", "max_recovery"): ("ep_mechanic:EPH_MAX_RCVR", "ep_formula.eval.max_recovery"),
    ("eecon", "cpk_average"): ("ep_sheet:eEcon!AO26", "ep_formula.eval.cpk_average"),
    ("eecon", "coins_per_kill_bonus"): ("stat_input:workshop_coins_per_kill_bonus", "stat_inputs.workshop_coins_per_kill_bonus"),
    ("eecon", "free_attack_upgrade"): ("stat_input:workshop_free_attack_upgrade", "stat_inputs.workshop_free_attack_upgrade"),
    ("eecon", "free_defense_upgrade"): ("stat_input:workshop_free_defense_upgrade", "stat_inputs.workshop_free_defense_upgrade"),
    ("eecon", "free_utility_upgrade"): ("stat_input:workshop_free_utility_upgrade", "stat_inputs.workshop_free_utility_upgrade"),
}


@dataclass(frozen=True)
class EPExportRow:
    suite: str
    key: str
    label: str
    value_raw: str
    value_numeric: float
    preset: str
    source_ref: str
    verification_path: str
    has_definitive_formula: bool

    @property
    def is_pending(self) -> bool:
        # Non-blocking behavior: this remains available if future rows are marked non-definitive.
        return not self.has_definitive_formula


@dataclass(frozen=True)
class EPExportDataset:
    rows: tuple[EPExportRow, ...]
    verification_presets: Mapping[str, str]

    @property
    def pending_rows(self) -> tuple[EPExportRow, ...]:
        return tuple(row for row in self.rows if row.is_pending)

    @property
    def rows_without_definitive_formulas(self) -> tuple[EPExportRow, ...]:
        return self.pending_rows


def extract_max_wave_targets(dataset: EPExportDataset) -> Mapping[str, float]:
    """Return EP-exported max-wave targets keyed by suite.

    Fail-closed behavior:
    - Raises when EP export has no recognizable max-wave rows.
    - Raises when duplicate max-wave rows exist for the same suite.
    """

    rows = [
        row
        for row in dataset.rows
        if row.key.lower() in {"max_wave", "w_max", "wave_max"}
        or row.label.strip().lower() in {"max wave", "w max", "wave max"}
    ]
    if not rows:
        raise ValueError(
            "EP export is missing max-wave rows; cannot verify max-wave parity."
        )

    targets: dict[str, float] = {}
    for row in rows:
        if row.suite in targets:
            raise ValueError(
                f"EP export has duplicate max-wave rows for suite {row.suite!r}."
            )
        targets[row.suite] = row.value_numeric
    return targets


def parse_human_number(raw: str) -> float:
    text = raw.strip()
    if not text:
        raise ValueError("EP export value is empty.")

    if text.startswith("x"):
        return float(text[1:])

    parts = text.split()
    if len(parts) == 2 and parts[1] in _HUMAN_SUFFIX_SCALE:
        return float(parts[0]) * _HUMAN_SUFFIX_SCALE[parts[1]]

    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Unsupported EP export number format: {raw!r}") from exc


def load_ep_export_dataset(
    *,
    ep_export_path: Path = Path("tests/fixtures/tower-sim-data/EP_Export.csv"),
    manifest_path: Path = Path("tests/fixtures/tower-sim-data/manifest.json"),
) -> EPExportDataset:
    verification_presets = _load_verification_presets(manifest_path)
    _validate_registry_sources()

    lines = ep_export_path.read_text(encoding="utf-8").splitlines()
    try:
        header_idx = lines.index("suite,key,label,value,import")
    except ValueError as exc:
        raise ValueError(f"Missing EP export header row in {ep_export_path}") from exc

    reader = csv.DictReader(lines[header_idx:])
    rows = []
    for csv_row in reader:
        suite = csv_row["suite"]
        key = csv_row["key"]
        row_key = (suite, key)
        if suite not in verification_presets:
            raise ValueError(f"Suite {suite!r} missing preset mapping in manifest.")
        if row_key not in _EP_ROW_SOURCES:
            raise ValueError(f"Missing EP source mapping for row {row_key!r}.")
        source_ref, verification_path = _EP_ROW_SOURCES[row_key]
        value_raw = csv_row["value"]
        rows.append(
            EPExportRow(
                suite=suite,
                key=key,
                label=csv_row["label"],
                value_raw=value_raw,
                value_numeric=parse_human_number(value_raw),
                preset=verification_presets[suite],
                source_ref=source_ref,
                verification_path=verification_path,
                has_definitive_formula=row_key not in _ROWS_WITHOUT_DEFINITIVE_FORMULAS,
            )
        )
    if not rows:
        raise ValueError(f"EP export has no data rows: {ep_export_path}")
    return EPExportDataset(rows=tuple(rows), verification_presets=verification_presets)


def _validate_registry_sources() -> None:
    registry = load_ep_formula_registry(strict=False)
    for source_ref, _ in _EP_ROW_SOURCES.values():
        if source_ref.startswith("ep_formula:"):
            formula_id = source_ref.split(":", 1)[1]
            if formula_id not in registry.formulas:
                raise ValueError(f"Missing formula registry id: {formula_id}")
        if source_ref.startswith("ep_mechanic:"):
            mechanic = source_ref.split(":", 1)[1]
            if mechanic not in registry.mechanics:
                raise ValueError(f"Missing formula registry mechanic: {mechanic}")


def _load_verification_presets(manifest_path: Path) -> Mapping[str, str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        mapping = manifest["files"]["EP_Export.csv"]["verification_presets"]
    except KeyError as exc:
        raise ValueError(
            "manifest missing files.EP_Export.csv.verification_presets"
        ) from exc
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("verification_presets must be a non-empty object")
    return mapping


__all__ = [
    "EPExportDataset",
    "EPExportRow",
    "extract_max_wave_targets",
    "load_ep_export_dataset",
    "parse_human_number",
]
