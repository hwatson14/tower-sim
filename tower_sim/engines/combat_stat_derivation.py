from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import re

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Dict, Iterable, List, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs, compile_workshop_values_at_wave
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, StatSnapshotError, build_at_wave_snapshot
from tower_sim.engines.survivability_pipeline import (
    compile_survivability_base_stat_inputs,
    compile_survivability_loadout_stat_inputs_with_diagnostics,
)
from tower_sim.loaders.perk_timeline_loader import apply_perk_timeline_to_inputs
from tower_sim.loaders.bc_heat_loader import HeatDataError, load_tournament_heat_table
from tower_sim.libs.labs_lib import load_labs_values
from tower_sim.loaders.account_snapshot_compiler import resolve_loadout
from tower_sim.libs.wave_damage_strict import EnemyWaveDamageLib
from tower_sim.libs.bots_lib import get_bot_attribute
from tower_sim.loaders.tournament_bc_enrichment import (
    TOURNAMENT_HEAT_BC_IDS,
    TOURNAMENT_HEAT_BC_TO_STATS,
    map_tournament_heat_bc_to_stat_magnitudes,
)
from tower_sim.registry.combat_stat_contract import (
    required_combat_stat_ids,
    required_max_wave_stat_input_ids,
)
from tower_sim.registry.stat_registry import Phase
from tower_sim.engines.wave_engine import RunWaveState, SkipRamp, make_wave_state
from tower_sim.loaders.wiki.module_rules import apply_hard_cap

_compile_full = compile_full_stat_inputs
_compile_survivability_base = compile_survivability_base_stat_inputs
_compile_survivability_loadout = compile_survivability_loadout_stat_inputs_with_diagnostics


@dataclass(frozen=True)
class CombatStatContribution:
    stat_id: str
    source: str
    value: float


@dataclass(frozen=True)
class CombatStatSnapshot:
    values: Dict[str, float]
    contributions: Dict[str, List[CombatStatContribution]]


@dataclass(frozen=True)
class CanonicalStatInputBuild:
    stat_inputs: List[StatInput]
    blocked_core_overrides: List[str]
    invalid_stat_inputs: List[str]
    missing_required_stat_inputs: List[str]
    compiled_missing: List[str]
    preset_resolution_errors: List[str]
    core_stat_override_policy: str
    module_contribution_ledger: List[Dict[str, object]] = field(default_factory=list)
    module_unmapped_by_layer: Dict[str, List[str]] = field(default_factory=dict)
    canonical_unmapped_by_source: Dict[str, List[str]] = field(default_factory=dict)




def _module_unmapped_by_layer(
    *,
    layer_gaps: List[str],
    module_contribution_ledger: List[Dict[str, object]],
) -> Dict[str, List[str]]:
    main_unmapped = sorted(
        {
            f"{row.get('slot')}:{row.get('placement')}:{row.get('module')}:{row.get('target')}"
            for row in module_contribution_ledger
            if row.get("layer") == "primary"
            and row.get("kind") == "behavior_binding"
            and str(row.get("target", "")).startswith("module_primary_effect:")
        }
    )
    unique_unmapped = sorted(
        {item for item in layer_gaps if item.startswith("module_unique_unmapped:")}
    )
    substat_unmapped = sorted(
        {item for item in layer_gaps if item.startswith("module_substat_unmapped:")}
    )
    return {
        "main": main_unmapped,
        "unique": unique_unmapped,
        "substats": substat_unmapped,
    }


def _canonical_unmapped_by_source(
    *,
    compiled_missing: List[str],
    module_unmapped_by_layer: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    buckets: Dict[str, set[str]] = {
        "modules": set(),
        "cards": set(),
        "labs": set(),
        "enhancements": set(),
        "workshop": set(),
        "ultimate_weapons": set(),
        "relics": set(),
        "other": set(),
    }

    for layer, items in module_unmapped_by_layer.items():
        for item in items:
            buckets["modules"].add(f"{layer}:{item}")

    for item in compiled_missing:
        if item.startswith("module_"):
            buckets["modules"].add(item)
        elif "unsupported_card" in item or "unknown_card" in item or item.startswith("cards:"):
            buckets["cards"].add(item)
        elif item.startswith("lab_") or item.startswith("lab:") or ":lab_" in item:
            buckets["labs"].add(item)
        elif "enhancement" in item:
            buckets["enhancements"].add(item)
        elif item.startswith("workshop"):
            buckets["workshop"].add(item)
        elif item.startswith("uw") or item.startswith("uw_"):
            buckets["ultimate_weapons"].add(item)
        elif item.startswith("relic"):
            buckets["relics"].add(item)
        else:
            buckets["other"].add(item)

    return {key: sorted(values) for key, values in buckets.items()}

def build_canonical_stat_inputs(
    *,
    problem_spec,
    ids_snapshot,
    registry,
) -> CanonicalStatInputBuild:
    spec_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
    compiled = _compile_full(ids_snapshot)
    base_inputs: List[StatInput] = []
    base_missing: List[str] = []
    try:
        base_inputs = _compile_survivability_base(ids_snapshot, allow_provisional=True)
    except Exception as exc:  # noqa: BLE001
        base_missing.append(f"survivability_base:{exc}")
    module_context, selected_cards, preset_resolution_errors = _resolve_preset_context(
        problem_spec,
        ids_snapshot,
    )
    loadout_inputs: List[StatInput] = []
    loadout_missing: List[str] = []
    module_contribution_ledger: List[Dict[str, object]] = []
    if not preset_resolution_errors:
        try:
            loadout_inputs, skipped_cards, module_contribution_ledger, layer_gaps = _compile_survivability_loadout_inputs_resilient(
                ids_snapshot,
                module_context=module_context,
                selected_cards=selected_cards,
            )
            loadout_missing.extend(skipped_cards)
            loadout_missing.extend(layer_gaps)
        except Exception as exc:  # noqa: BLE001
            loadout_missing.append(f"survivability_loadout:{exc}")

    strict_core_stat_overrides = not bool(
        getattr(problem_spec.scenario, "allow_core_stat_overrides", False)
    )
    merged_inputs, blocked = _merge_stat_inputs(
        spec_inputs,
        compiled.stat_inputs + base_inputs + loadout_inputs,
        strict_core_stat_overrides=strict_core_stat_overrides,
    )
    merged_inputs = _rebase_wall_stats_from_tower(
        merged_inputs,
        ids_snapshot=ids_snapshot,
    )
    filtered_inputs, invalid = _filter_known_stat_inputs(merged_inputs, registry)
    missing_required = _missing_required_stat_inputs(filtered_inputs)
    module_unmapped_by_layer = _module_unmapped_by_layer(
        layer_gaps=loadout_missing,
        module_contribution_ledger=module_contribution_ledger,
    )
    canonical_unmapped_by_source = _canonical_unmapped_by_source(
        compiled_missing=sorted(compiled.missing + base_missing + loadout_missing),
        module_unmapped_by_layer=module_unmapped_by_layer,
    )

    return CanonicalStatInputBuild(
        stat_inputs=filtered_inputs,
        blocked_core_overrides=blocked,
        invalid_stat_inputs=invalid,
        missing_required_stat_inputs=missing_required,
        compiled_missing=sorted(compiled.missing + base_missing + loadout_missing),
        preset_resolution_errors=sorted(set(preset_resolution_errors)),
        core_stat_override_policy=(
            "strict_fail_closed" if strict_core_stat_overrides else "explicit_override_mode"
        ),
        module_contribution_ledger=module_contribution_ledger,
        module_unmapped_by_layer=module_unmapped_by_layer,
        canonical_unmapped_by_source=canonical_unmapped_by_source,
    )


def _resolve_preset_context(problem_spec, ids_snapshot) -> tuple[str, List[str] | None, List[str]]:
    explicit = getattr(problem_spec.scenario, "preset", None)
    if explicit is not None:
        resolved = str(explicit).strip()
    else:
        mode = (problem_spec.scenario.mode or "").strip().lower()
        resolved = "Tourney" if mode == "tournament" else "Farming"

    errors: List[str] = []
    if not resolved:
        errors.append("preset_resolution:empty")
        return "", [], errors

    try:
        loadout = resolve_loadout(ids_snapshot, resolved)
        return resolved, list(loadout.card_names), errors
    except Exception as exc:  # noqa: BLE001
        # Test doubles and partial snapshots may only provide card presets; preserve
        # deterministic mode/preset wiring for loadout compilation in that case.
        card_presets = getattr(ids_snapshot, "card_presets", None)
        if isinstance(card_presets, dict) and resolved in card_presets:
            return resolved, list(card_presets.get(resolved, [])), errors
        if not hasattr(ids_snapshot, "card_presets") and not hasattr(ids_snapshot, "module_presets"):
            return resolved, None, errors
        errors.append(f"preset_resolution:{resolved}:{exc}")
        return resolved, [], errors


def _resolved_stat_input_value(stat_input: StatInput) -> float:
    if stat_input.derived_value is not None:
        return float(stat_input.derived_value)
    base_value = float(stat_input.base_value or 0.0)
    loadout_delta = float(stat_input.loadout_delta or 0.0)
    enhancement_multiplier = float(stat_input.enhancement_multiplier or 1.0)
    tier_delta = float(stat_input.tier_rule_delta or 0.0)
    tier_multiplier = float(stat_input.tier_rule_multiplier or 1.0)
    return ((base_value + loadout_delta) * enhancement_multiplier + tier_delta) * tier_multiplier


def _wall_ratio_from_ids(
    ids_snapshot,
    stat_inputs: List[StatInput],
) -> tuple[Optional[float], Optional[float], List[str]]:
    missing: List[str] = []
    labs = load_labs_values()

    by_key = {(item.stat_id, item.phase): item for item in stat_inputs}
    wall_health_input = by_key.get(("workshop_wall_health", Phase.START_OF_RUN))
    if wall_health_input is None:
        missing.append("workshop_alias_missing:workshop_wall_health")
        return None, None, missing
    wall_health_ratio = _resolved_stat_input_value(wall_health_input)

    wall_health_lab = ids_snapshot.labs.get("Wall Health")
    if wall_health_lab is None:
        missing.append("lab_level:Wall Health")
        wall_health_lab = 0
    if wall_health_lab > 0:
        lab = labs.get("Wall Health")
        if lab is None:
            missing.append("lab_table:Wall Health")
            return None, None, missing
        if wall_health_lab not in lab.levels:
            missing.append(f"lab_table:Wall Health:{wall_health_lab}")
            return None, None, missing
        if lab.unit not in {"percent", "percent_points"}:
            missing.append(f"lab_unit:Wall Health:{lab.unit}")
            return None, None, missing
        wall_health_ratio += float(lab.levels[wall_health_lab]) / 100.0

    wall_regen_input = by_key.get(("workshop_wall_regen", Phase.START_OF_RUN))
    wall_regen_ratio = (
        _resolved_stat_input_value(wall_regen_input) if wall_regen_input is not None else 0.0
    )
    wall_regen_lab = ids_snapshot.labs.get("Wall Regen")
    if wall_regen_lab is None:
        missing.append("lab_level:Wall Regen")
        wall_regen_lab = 0
    if wall_regen_lab > 0:
        lab = labs.get("Wall Regen")
        if lab is None:
            missing.append("lab_table:Wall Regen")
            return None, None, missing
        if wall_regen_lab not in lab.levels:
            missing.append(f"lab_table:Wall Regen:{wall_regen_lab}")
            return None, None, missing
        if lab.unit not in {"percent", "percent_points"}:
            missing.append(f"lab_unit:Wall Regen:{lab.unit}")
            return None, None, missing
        wall_regen_ratio += float(lab.levels[wall_regen_lab]) / 100.0
    return wall_health_ratio, wall_regen_ratio, missing


def _rebase_wall_stats_from_tower(stat_inputs: List[StatInput], *, ids_snapshot) -> List[StatInput]:
    by_key = {(item.stat_id, item.phase): item for item in stat_inputs}
    tower_hp = by_key.get(("tower_hp", Phase.START_OF_RUN))
    tower_regen = by_key.get(("tower_regen", Phase.START_OF_RUN))
    wall_hp = by_key.get(("wall_hp", Phase.START_OF_RUN))
    wall_regen = by_key.get(("wall_regen", Phase.START_OF_RUN))
    if tower_hp is None or tower_regen is None or wall_hp is None or wall_regen is None:
        return stat_inputs

    wall_health_ratio, wall_regen_ratio, missing = _wall_ratio_from_ids(
        ids_snapshot,
        stat_inputs,
    )
    if missing or wall_health_ratio is None or wall_regen_ratio is None:
        return stat_inputs

    target_wall_hp_base = _resolved_stat_input_value(tower_hp) * float(wall_health_ratio)
    target_wall_regen_base = _resolved_stat_input_value(tower_regen) * float(wall_regen_ratio)

    def _replace_base(item: StatInput, target_base: float) -> StatInput:
        current_base = float(item.base_value or 0.0)
        resolved = _resolved_stat_input_value(item)
        transfer_multiplier = 1.0
        if current_base > 0.0:
            transfer_multiplier = max(resolved / current_base, 0.0)
        return StatInput(
            stat_id=item.stat_id,
            phase=item.phase,
            base_value=target_base,
            loadout_delta=None,
            enhancement_multiplier=transfer_multiplier if transfer_multiplier != 1.0 else None,
            tier_rule_delta=None,
            tier_rule_multiplier=None,
            derived_value=None,
            provenance=(item.provenance or "") + ":rebased_from_tower",
        )

    replacements = {
        ("wall_hp", Phase.START_OF_RUN): _replace_base(wall_hp, target_wall_hp_base),
        ("wall_regen", Phase.START_OF_RUN): _replace_base(wall_regen, target_wall_regen_base),
    }

    rebased: List[StatInput] = []
    for item in stat_inputs:
        rebased.append(replacements.get((item.stat_id, item.phase), item))
    return rebased


_UNSUPPORTED_CARD_RE = re.compile(r"Unsupported card for survivability pipeline: '([^']+)'")
_UNKNOWN_CARD_RE = re.compile(r"Unknown card: '([^']+)'")


def _compile_survivability_loadout_inputs_resilient(
    ids_snapshot,
    *,
    module_context: str,
    selected_cards: List[str] | None = None,
) -> Tuple[List[StatInput], List[str], List[Dict[str, object]], List[str]]:
    skipped: List[str] = []
    while True:
        try:
            kwargs = {
                "module_context": module_context,
                "allow_provisional": True,
            }
            if selected_cards is not None:
                kwargs["selected_cards"] = selected_cards
            raw_result = _compile_survivability_loadout(
                ids_snapshot,
                **kwargs,
            )
            if hasattr(raw_result, "stat_inputs"):
                return (
                    raw_result.stat_inputs,
                    skipped,
                    list(getattr(raw_result, "module_contribution_ledger", [])),
                    list(getattr(raw_result, "layer_gaps", [])),
                )
            return raw_result, skipped, [], []
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            match = _UNSUPPORTED_CARD_RE.search(message)
            reason = "survivability_loadout_unsupported_card"
            if match is None:
                match = _UNKNOWN_CARD_RE.search(message)
                reason = "survivability_loadout_unknown_card"
            if match is None:
                raise
            if selected_cards is None:
                raise
            card_name = match.group(1)
            if card_name not in selected_cards:
                raise
            selected_cards = [card for card in selected_cards if card != card_name]
            skipped.append(f"{reason}:{card_name}")


def derive_canonical_combat_snapshot(
    engine_result,
    wave_snapshot: Optional[AtWaveSnapshot],
) -> Tuple[Optional[CombatStatSnapshot], List[str]]:
    """Derive canonical combat survivability stats for MAX_WAVE consumption.

    Source precedence is deterministic and fail-closed:
    1) at-wave snapshot value if present
    2) START_OF_RUN statbook value
    3) missing -> fail-closed marker
    """

    if engine_result is None:
        return None, ["stat_engine"]
    start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
    if start_stats is None:
        return None, ["start_stats"]

    snapshot_values = wave_snapshot.values if wave_snapshot is not None else {}
    values: Dict[str, float] = {}
    contributions: Dict[str, List[CombatStatContribution]] = {}
    missing: List[str] = []

    for stat_id in required_combat_stat_ids():
        from_wave = snapshot_values.get(stat_id)
        if from_wave is not None:
            value = float(from_wave)
            if stat_id == "def_pct":
                value = apply_hard_cap("Defense %", value)
            values[stat_id] = value
            contributions[stat_id] = [
                CombatStatContribution(
                    stat_id=stat_id,
                    source="at_wave_snapshot",
                    value=value,
                )
            ]
            continue

        from_start = start_stats.values.get(stat_id)
        if from_start is not None:
            value = float(from_start)
            if stat_id == "def_pct":
                value = apply_hard_cap("Defense %", value)
            values[stat_id] = value
            contributions[stat_id] = [
                CombatStatContribution(
                    stat_id=stat_id,
                    source="start_of_run",
                    value=value,
                )
            ]
            continue

        missing.append(stat_id)

    if missing:
        return None, [f"stat:{stat_id}" for stat_id in missing]

    return CombatStatSnapshot(values=values, contributions=contributions), []


def _missing_required_stat_inputs(stat_inputs: Iterable[StatInput]) -> List[str]:
    required = set(required_max_wave_stat_input_ids())
    by_stat_id: Dict[str, List[StatInput]] = {}
    for stat_input in stat_inputs:
        by_stat_id.setdefault(stat_input.stat_id, []).append(stat_input)

    missing: List[str] = []
    for stat_id in sorted(required):
        entries = by_stat_id.get(stat_id)
        if not entries:
            missing.append(f"stat_input:{stat_id}")
            continue
        has_base_or_derived = any(
            entry.base_value is not None or entry.derived_value is not None
            for entry in entries
        )
        if not has_base_or_derived:
            missing.append(f"stat_input:{stat_id}")
    return missing


def _merge_stat_inputs(
    spec_inputs: List[StatInput],
    compiled_inputs: List[StatInput],
    *,
    strict_core_stat_overrides: bool,
) -> Tuple[List[StatInput], List[str]]:
    existing = {(item.stat_id, item.phase): item for item in spec_inputs}
    merged = list(spec_inputs)
    blocked: List[str] = []
    for item in compiled_inputs:
        key = (item.stat_id, item.phase)
        if key in existing:
            if (
                strict_core_stat_overrides
                and item.phase == Phase.START_OF_RUN
            ):
                if item.base_value is not None or item.derived_value is not None:
                    provenance = item.provenance or ""
                    if provenance.startswith("workshop_alias:") or provenance.startswith("base:"):
                        continue
                    blocked.append(f"{item.stat_id}@{item.phase.value}")
                    continue
            existing_item = existing[key]
            merged_item = StatInput(
                stat_id=existing_item.stat_id,
                phase=existing_item.phase,
                base_value=(
                    existing_item.base_value
                    if existing_item.base_value is not None
                    else item.base_value
                ),
                loadout_delta=(existing_item.loadout_delta or 0.0)
                + (item.loadout_delta or 0.0),
                enhancement_multiplier=(existing_item.enhancement_multiplier or 1.0)
                * (item.enhancement_multiplier or 1.0),
                tier_rule_delta=(
                    existing_item.tier_rule_delta
                    if existing_item.tier_rule_delta is not None
                    else item.tier_rule_delta
                ),
                tier_rule_multiplier=(
                    existing_item.tier_rule_multiplier
                    if existing_item.tier_rule_multiplier is not None
                    else item.tier_rule_multiplier
                ),
                derived_value=(
                    existing_item.derived_value
                    if existing_item.derived_value is not None
                    else item.derived_value
                ),
                provenance=existing_item.provenance or item.provenance,
            )
            existing[key] = merged_item
            for idx, current in enumerate(merged):
                if current.stat_id == key[0] and current.phase == key[1]:
                    merged[idx] = merged_item
                    break
            continue
        merged.append(item)
        existing[key] = item
    return merged, sorted(set(blocked))


def _filter_known_stat_inputs(
    stat_inputs: List[StatInput],
    registry,
) -> Tuple[List[StatInput], List[str]]:
    filtered: List[StatInput] = []
    invalid: List[str] = []
    for item in stat_inputs:
        try:
            registry.validate_stat_id(item.stat_id)
        except Exception:  # noqa: BLE001
            invalid.append(item.stat_id)
            continue
        filtered.append(item)
    return filtered, sorted(set(invalid))




@lru_cache(maxsize=1)
def cached_tournament_heat_table(scale_path: str, registry_path: str):
    return load_tournament_heat_table(Path(scale_path), Path(registry_path))


def resolve_wave_state_for_wave(
    scenario,
    wave: int,
) -> Tuple[Optional[RunWaveState], List[str]]:
    missing: List[str] = []
    if scenario.eals_ramp is None:
        missing.append("skip_ramp:eals")
    if scenario.ehls_ramp is None:
        missing.append("skip_ramp:ehls")
    if missing:
        return None, missing
    eals = SkipRamp(
        start=scenario.eals_ramp.start,
        end=scenario.eals_ramp.end,
        ramp_waves=scenario.eals_ramp.ramp_waves,
    )
    ehls = SkipRamp(
        start=scenario.ehls_ramp.start,
        end=scenario.ehls_ramp.end,
        ramp_waves=scenario.ehls_ramp.ramp_waves,
    )
    return make_wave_state(wave, eals, ehls), []


def build_canonical_wave_row(
    problem_spec,
    registry,
    *,
    wave: int,
) -> Tuple[Optional[Dict[str, object]], List[str]]:
    wave_state, wave_missing = resolve_wave_state_for_wave(problem_spec.scenario, wave)
    if wave_missing or wave_state is None:
        return None, wave_missing

    row: Dict[str, object] = {
        "wave": int(wave),
        "enemy_attack_wave": int(wave_state.W_attack),
        "enemy_health_wave": int(wave_state.W_health),
    }

    if problem_spec.scenario.mode != "tournament":
        return row, []

    table_path = resolve_table_path("heat_scale_long")
    registry_path = resolve_table_path("heat_bc_registry")
    try:
        table = cached_tournament_heat_table(str(table_path), str(registry_path))
    except (HeatDataError, FileNotFoundError):
        return None, ["heat_tables"]

    league = (problem_spec.scenario.league or "").strip().lower()
    if not league:
        return None, ["heat_league"]

    bc_values: Dict[str, float] = {}
    missing_heat_ids: List[str] = []
    for bc_id in TOURNAMENT_HEAT_BC_IDS:
        try:
            value = table.value_at(league=league, wave_actual=wave, bc_id=bc_id).value_num
        except HeatDataError:
            missing_heat_ids.append(f"heat_bc_value:{bc_id}")
            continue
        bc_values[bc_id] = float(value)

    if missing_heat_ids:
        return None, sorted(set(missing_heat_ids))

    row["battle_conditions"] = bc_values
    row["heat_magnitudes"] = map_tournament_heat_bc_to_stat_magnitudes(
        registry=registry,
        bc_values=bc_values,
    )
    return row, []


def resolve_canonical_heat_magnitudes(
    *,
    problem_spec,
    registry,
    wave: int,
) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, object]], List[str]]:
    scenario = problem_spec.scenario
    if scenario.mode != "tournament":
        return None, None, []
    if scenario.league is None:
        return None, None, ["heat_league"]
    row, row_missing = build_canonical_wave_row(problem_spec, registry, wave=wave)
    if row_missing or row is None:
        return None, row, row_missing
    return row.get("heat_magnitudes"), row, []


__all__ = [
    "CanonicalStatInputBuild",
    "TOURNAMENT_HEAT_BC_IDS",
    "TOURNAMENT_HEAT_BC_TO_STATS",
    "CombatStatContribution",
    "CombatStatSnapshot",
    "build_canonical_stat_inputs",
    "resolve_wave_state_for_wave",
    "resolve_canonical_heat_magnitudes",
    "cached_tournament_heat_table",
    "build_canonical_wave_row",
    "wave_state_from_row",
    "build_canonical_wave_snapshot",
    "canonical_stat_inputs_for_wave",
    "default_wave_damage_tier",
    "derive_canonical_combat_snapshot",
    "resolve_canonical_wave_damage",
    "resolve_canonical_wave_damage_for_attack_wave",
    "validate_boss_survivability_spec",
]


def canonical_stat_inputs_for_wave(
    *,
    registry,
    stat_inputs: List[StatInput],
    scenario,
    wave: int,
) -> Tuple[List[StatInput], Dict[str, object]]:
    if scenario.mode == "tournament":
        return stat_inputs, {"enabled": False, "reason": "tournament_mode"}
    return apply_perk_timeline_to_inputs(
        registry=registry,
        stat_inputs=stat_inputs,
        perk_timeline_path=getattr(scenario, "perk_timeline_path", None),
        current_wave=wave,
    )




def wave_state_from_row(wave_row: Dict[str, object]) -> RunWaveState:
    if (
        "wave" not in wave_row
        or "enemy_attack_wave" not in wave_row
        or "enemy_health_wave" not in wave_row
    ):
        raise StatSnapshotError(
            "Wave row missing required keys: wave/enemy_attack_wave/enemy_health_wave"
        )
    return RunWaveState(
        W_actual=int(wave_row["wave"]),
        W_attack=int(wave_row["enemy_attack_wave"]),
        W_health=int(wave_row["enemy_health_wave"]),
    )


def build_canonical_wave_snapshot(
    *,
    ids_snapshot,
    wave: int,
    stat_inputs: List[StatInput],
    engine_result,
    registry,
    tier_rules,
    run_context,
    heat_magnitudes,
    wave_row: Dict[str, object],
):
    workshop_at_wave, workshop_missing = compile_workshop_values_at_wave(ids_snapshot, wave=wave)
    if workshop_missing:
        return None, workshop_missing
    snapshot = build_at_wave_snapshot(
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=tier_rules,
        battle_conditions=None,
        wave_state=wave_state_from_row(wave_row),
        wave=wave,
        run_context=run_context,
        heat_magnitudes=heat_magnitudes,
        per_wave_overrides=workshop_at_wave,
    )
    return snapshot, []

def resolve_canonical_wave_damage(
    *,
    problem_spec,
    wave_state,
) -> Tuple[Optional[float], List[str], Dict[str, object]]:
    diagnostics: Dict[str, object] = {}
    missing: List[str] = []
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None, missing, diagnostics

    lib = EnemyWaveDamageLib.from_repo_tables()
    wave = scenario.wave if wave_state is None else wave_state.W_attack
    try:
        damage = lib.wave_damage(wave_tier, wave)
    except KeyError as exc:
        missing.append("wave_damage_table")
        diagnostics["wave_damage_error"] = str(exc)
        return None, missing, diagnostics
    diagnostics["wave_damage_tier"] = wave_tier
    diagnostics["wave_damage_wave"] = wave
    diagnostics["wave_damage"] = damage
    return damage, missing, diagnostics


def default_wave_damage_tier(scenario) -> Optional[str]:
    if scenario.mode == "farming":
        return f"Tier {scenario.tier}"
    if scenario.league:
        return scenario.league
    return None


def validate_boss_survivability_spec(problem_spec: object) -> Tuple[List[str], Dict[str, str]]:
    diagnostics: Dict[str, str] = {}
    missing: List[str] = []
    spec = getattr(problem_spec.scenario, "boss_survivability", None)
    if spec is None:
        missing.append("boss_survivability")
        return missing, diagnostics

    boss = spec.boss
    tower = spec.tower
    if boss.hp is not None and boss.hp <= 0:
        diagnostics["boss_hp"] = "non_positive"
    if boss.attack <= 0:
        diagnostics["boss_attack"] = "non_positive"
    if boss.attack_interval <= 0:
        diagnostics["boss_attack_interval"] = "non_positive"
    if boss.enrage_mult is not None and boss.enrage_mult <= 0:
        diagnostics["boss_enrage_mult"] = "non_positive"
    if tower.dr_frac < 0 or tower.dr_frac > 1:
        diagnostics["tower_dr_frac"] = "out_of_range"
    if tower.regen_per_sec < 0:
        diagnostics["tower_regen_per_sec"] = "negative"
    if tower.shields < 0:
        diagnostics["tower_shields"] = "negative"

    if diagnostics:
        missing.append("boss_survivability_invalid")
    return missing, diagnostics



def resolve_runtime_bot_effects(
    *,
    ids_snapshot,
    snapshot_values: Dict[str, object],
) -> Tuple[List[Dict[str, float]], Dict[str, float]]:
    """Resolve canonical bot runtime effects before timing-uptime aggregation.

    Bot table levels and stat-engine-composed scalar channels are resolved here so
    the timing engine only consumes effective duration/cooldown/effect values.
    """

    def _scalar(stat_id: str) -> float:
        raw = snapshot_values.get(stat_id)
        if raw is None:
            return 1.0
        value = float(raw)
        if value <= 0:
            raise ValueError(f"{stat_id} must be > 0, got {value}.")
        return value

    scalars = {
        "bot_duration_multiplier": _scalar("bot_duration_multiplier"),
        "bot_cooldown_multiplier": _scalar("bot_cooldown_multiplier"),
        "bot_bonus_multiplier": _scalar("bot_bonus_multiplier"),
        "flame_bot_damage_reduction_multiplier": _scalar("flame_bot_damage_reduction_multiplier"),
    }

    profiles: List[Dict[str, float]] = []
    bot_levels = ids_snapshot.bot_upgrades

    if "Flame Bot" in bot_levels:
        bot = bot_levels["Flame Bot"]
        if {"Duration", "Cooldown", "Damage R."}.issubset(bot):
            duration, _, _ = get_bot_attribute("Flame Bot", "Duration", bot["Duration"])
            cooldown, _, _ = get_bot_attribute("Flame Bot", "Cooldown", bot["Cooldown"])
            damage_r, _, _ = get_bot_attribute("Flame Bot", "Damage R.", bot["Damage R."])
            profiles.append(
                {
                    "name": "Flame Bot",
                    "duration_s": float(duration) * scalars["bot_duration_multiplier"],
                    "cooldown_s": float(cooldown) * scalars["bot_cooldown_multiplier"],
                    "damage_reduction": float(damage_r)
                    * scalars["bot_bonus_multiplier"]
                    * scalars["flame_bot_damage_reduction_multiplier"],
                    "coin_multiplier": 1.0,
                    "damage_multiplier": 1.0,
                }
            )

    if "Golden Bot" in bot_levels:
        bot = bot_levels["Golden Bot"]
        if {"Duration", "Cooldown", "Bonus"}.issubset(bot):
            duration, _, _ = get_bot_attribute("Golden Bot", "Duration", bot["Duration"])
            cooldown, _, _ = get_bot_attribute("Golden Bot", "Cooldown", bot["Cooldown"])
            bonus, _, _ = get_bot_attribute("Golden Bot", "Bonus", bot["Bonus"])
            profiles.append(
                {
                    "name": "Golden Bot",
                    "duration_s": float(duration) * scalars["bot_duration_multiplier"],
                    "cooldown_s": float(cooldown) * scalars["bot_cooldown_multiplier"],
                    "coin_multiplier": float(bonus) * scalars["bot_bonus_multiplier"],
                    "damage_reduction": 0.0,
                    "damage_multiplier": 1.0,
                }
            )

    if "Amplify Bot" in bot_levels:
        bot = bot_levels["Amplify Bot"]
        if {"Duration", "Cooldown", "Bonus"}.issubset(bot):
            duration, _, _ = get_bot_attribute("Amplify Bot", "Duration", bot["Duration"])
            cooldown, _, _ = get_bot_attribute("Amplify Bot", "Cooldown", bot["Cooldown"])
            bonus, _, _ = get_bot_attribute("Amplify Bot", "Bonus", bot["Bonus"])
            profiles.append(
                {
                    "name": "Amplify Bot",
                    "duration_s": float(duration) * scalars["bot_duration_multiplier"],
                    "cooldown_s": float(cooldown) * scalars["bot_cooldown_multiplier"],
                    "damage_multiplier": float(bonus) * scalars["bot_bonus_multiplier"],
                    "damage_reduction": 0.0,
                    "coin_multiplier": 1.0,
                }
            )

    return profiles, scalars

def resolve_canonical_wave_damage_for_attack_wave(
    *,
    problem_spec,
    attack_wave: int,
) -> Tuple[Optional[float], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None, missing
    lib = EnemyWaveDamageLib.from_repo_tables()
    try:
        damage = lib.wave_damage(wave_tier, int(attack_wave))
    except KeyError:
        missing.append("wave_damage_table")
        return None, missing
    return damage, []
