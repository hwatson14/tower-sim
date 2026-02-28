from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, List, Optional
import re

from tower_sim.engines.combat_stat_derivation import (
    build_canonical_stat_inputs,
    build_canonical_wave_snapshot,
    build_canonical_wave_row,
    canonical_stat_inputs_for_wave,
)
from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.engines.stat_input_compiler import (
    _UW_TRACK_SPECS,
    _parse_uw_tracks,
    compile_full_stat_inputs,
)
from tower_sim.engines.survivability_pipeline import (
    compile_survivability_base_stat_inputs,
    compile_survivability_loadout_stat_inputs,
)
from tower_sim.engines.tier_rule_apply import SUPPORTED_BC
from tower_sim.engines.tier_rules import build_tier_rules
from tower_sim.engines.wave_engine import RunWaveState, SkipRamp, make_wave_state
from tower_sim.registry.combat_stat_contract import (
    required_combat_stat_ids,
    required_max_wave_stat_input_ids,
)
from tower_sim.loaders.table_paths import resolve_table_path
from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.libs.step1_tables import load_dag_table
from tower_sim.run.context import RunContext
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.loaders.perk_timeline_loader import PerkTimelineError


class StatPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContributorRecord:
    stat_id: str
    phase: str
    provenance: str
    level: Optional[float]
    resolved_value: float


@dataclass(frozen=True)
class BaseStatStage:
    values: Dict[str, float]
    contributors: List[ContributorRecord]


@dataclass(frozen=True)
class StartOfRunStage:
    values: Dict[str, float]
    contributors: List[ContributorRecord]
    merge_policy: str


@dataclass(frozen=True)
class WaveStateRecord:
    W_actual: int
    W_attack: int
    W_health: int


@dataclass(frozen=True)
class AtWaveStage:
    values: Dict[str, float]
    wave_state: WaveStateRecord
    applied_bc: Dict[str, float]
    applied_heat: Dict[str, float]


@dataclass(frozen=True)
class CanonicalPipelineResult:
    base_stage: BaseStatStage
    start_stage: StartOfRunStage
    at_wave_stage: Optional[AtWaveStage]
    diagnostics: Dict[str, Any]
    missing: List[str]
    stat_inputs: List[StatInput]
    run_context: RunContext
    tier_rules: Any
    wave_state: Optional[RunWaveState]
    start_engine_result: Any


def build_canonical_stat_pipeline(
    *,
    snapshot,
    scenario,
    preset: str | None,
    wave: int | None,
    include_perk_timeline: bool,
) -> CanonicalPipelineResult:
    scenario_spec = scenario
    if preset is not None and getattr(scenario, "preset", None) is None:
        scenario_spec = replace(scenario, preset=str(preset))
    problem_spec = ProblemSpec(scenario=scenario_spec, stat_inputs=[])
    return build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=wave,
        include_perk_timeline=include_perk_timeline,
    )


def build_canonical_stat_pipeline_for_problem_spec(
    *,
    snapshot,
    problem_spec: ProblemSpec,
    wave: int | None,
    include_perk_timeline: bool,
    materialize_stages: bool = True,
    precomputed_canonical_inputs=None,
) -> CanonicalPipelineResult:
    diagnostics: Dict[str, Any] = {}
    missing: List[str] = []
    registry = default_registry()
    run_context = RunContext.from_mode(
        problem_spec.scenario.mode,
        tier=str(problem_spec.scenario.tier),
    )

    canonical_inputs = precomputed_canonical_inputs
    if canonical_inputs is None:
        canonical_inputs = build_canonical_stat_inputs(
            problem_spec=problem_spec,
            ids_snapshot=snapshot,
            registry=registry,
        )
    diagnostics["core_stat_override_policy"] = canonical_inputs.core_stat_override_policy
    if canonical_inputs.module_contribution_ledger:
        diagnostics["module_contribution_ledger"] = canonical_inputs.module_contribution_ledger
    diagnostics["module_unmapped_by_layer"] = canonical_inputs.module_unmapped_by_layer
    diagnostics["canonical_unmapped_by_source"] = canonical_inputs.canonical_unmapped_by_source
    diagnostics["observed_contributors_by_stat_input_id"] = (
        canonical_inputs.observed_contributors_by_stat_input_id
    )

    dag_contract, dag_missing = _load_runtime_dag_contract()
    if dag_contract is not None:
        diagnostics["runtime_dag"] = dag_contract
    if dag_missing:
        diagnostics["missing_dag_runtime_binding"] = dag_missing
        missing.extend(dag_missing)
    if canonical_inputs.compiled_missing:
        diagnostics["compiled_missing"] = canonical_inputs.compiled_missing
    if canonical_inputs.blocked_core_overrides:
        diagnostics["blocked_core_stat_overrides"] = canonical_inputs.blocked_core_overrides
    if canonical_inputs.invalid_stat_inputs:
        diagnostics["invalid_stat_inputs"] = canonical_inputs.invalid_stat_inputs
        missing.extend(canonical_inputs.invalid_stat_inputs)
    if canonical_inputs.preset_resolution_errors:
        diagnostics["preset_resolution_errors"] = canonical_inputs.preset_resolution_errors
        missing.extend(canonical_inputs.preset_resolution_errors)
    if canonical_inputs.missing_required_stat_inputs:
        diagnostics["missing_stat_inputs"] = canonical_inputs.missing_required_stat_inputs
        missing.extend(canonical_inputs.missing_required_stat_inputs)

    stage1_inputs: List[StatInput] = []
    stage2_inputs: List[StatInput] = list(canonical_inputs.stat_inputs)
    start_result = None
    if materialize_stages:
        compiled = compile_full_stat_inputs(snapshot)
        base_inputs = compile_survivability_base_stat_inputs(snapshot, allow_provisional=True)
        stage1_inputs = compiled.stat_inputs + base_inputs

        diagnostics["start_stage_source"] = (
            "precomputed_canonical_inputs"
            if precomputed_canonical_inputs is not None
            else "canonical_stat_inputs"
        )
        stage2_inputs = list(canonical_inputs.stat_inputs)

        engine = StatEngine(registry=registry)
        base_result = engine.build(stage1_inputs)
        start_result = engine.build(stage2_inputs)

        base_stage = BaseStatStage(
            values=_start_values(base_result),
            contributors=_contributors(stage1_inputs, snapshot=snapshot),
        )
        start_stage = StartOfRunStage(
            values=_start_values(start_result),
            contributors=_contributors(stage2_inputs, snapshot=snapshot),
            merge_policy=canonical_inputs.core_stat_override_policy,
        )
        missing_start = _missing_required_stage_stats(
            start_stage.values,
            required=list(required_max_wave_stat_input_ids()),
        )
        if missing_start:
            diagnostics["missing_required_start_stage_stats"] = missing_start
            missing.extend(f"start_stage_missing:{stat_id}" for stat_id in missing_start)
    else:
        diagnostics["stages_materialized"] = False
        base_stage = BaseStatStage(values={}, contributors=[])
        start_stage = StartOfRunStage(
            values={},
            contributors=_contributors(stage2_inputs, snapshot=snapshot),
            merge_policy=canonical_inputs.core_stat_override_policy,
        )

    tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
    if tier_rule_missing:
        diagnostics["missing_tier_rules"] = tier_rule_missing
        missing.extend(tier_rule_missing)

    wave_state: Optional[RunWaveState] = None
    at_wave_stage: Optional[AtWaveStage] = None
    target_wave = problem_spec.scenario.wave if wave is None else wave
    if target_wave is not None:
        wave_state, wave_state_missing = _build_wave_state(problem_spec, wave=target_wave)
        if wave_state_missing:
            diagnostics["missing_wave_state"] = wave_state_missing
            missing.extend(wave_state_missing)
        else:
            diagnostics["wave_state"] = asdict(wave_state)

        if wave_state is not None:
            wave_inputs = stage2_inputs
            if include_perk_timeline:
                try:
                    wave_inputs, perk_diag = canonical_stat_inputs_for_wave(
                        registry=registry,
                        stat_inputs=stage2_inputs,
                        scenario=problem_spec.scenario,
                        wave=target_wave,
                    )
                    diagnostics["perk_timeline"] = perk_diag
                except PerkTimelineError as exc:
                    reason = getattr(exc, "reason", "invalid_precomputed_table")
                    diagnostics["perk_timeline"] = {
                        "enabled": False,
                        "reason": reason,
                        "error": str(exc),
                    }
                    explicit_perk_table = getattr(problem_spec.scenario, "perk_timeline_path", None)
                    if reason != "missing_precomputed_table" or explicit_perk_table:
                        missing.append(f"perk_timeline:{reason}")
                    wave_inputs = stage2_inputs

            wave_row, wave_row_missing = build_canonical_wave_row(
                problem_spec,
                registry,
                wave=target_wave,
            )
            if wave_row_missing:
                diagnostics["missing_heat"] = wave_row_missing
                missing.extend(wave_row_missing)
            if wave_row is None:
                raise StatPipelineError("Missing canonical wave row for at-wave stage build.")

            if start_result is None:
                diagnostics["at_wave_stage_skipped"] = "stages_not_materialized"
                at_wave_snapshot = None
                at_wave_missing = []
            else:
                at_wave_snapshot, at_wave_missing = build_canonical_wave_snapshot(
                    ids_snapshot=snapshot,
                    wave=target_wave,
                    stat_inputs=wave_inputs,
                    engine_result=start_result,
                    registry=registry,
                    tier_rules=tier_rules,
                    run_context=run_context,
                    heat_magnitudes=wave_row.get("heat_magnitudes"),
                    wave_row=wave_row,
                )
            if at_wave_missing:
                diagnostics["missing_at_wave"] = at_wave_missing
                missing.extend(at_wave_missing)
            elif at_wave_snapshot is not None:
                at_wave_stage = AtWaveStage(
                    values=dict(at_wave_snapshot.values),
                    wave_state=WaveStateRecord(
                        W_actual=wave_state.W_actual,
                        W_attack=wave_state.W_attack,
                        W_health=wave_state.W_health,
                    ),
                    applied_bc=dict(at_wave_snapshot.applied_bc),
                    applied_heat=dict(at_wave_snapshot.applied_heat),
                )
                missing_wave = _missing_required_stage_stats(
                    at_wave_stage.values,
                    required=list(required_combat_stat_ids()),
                )
                if missing_wave:
                    diagnostics["missing_required_at_wave_stats"] = missing_wave
                    missing.extend(f"at_wave_stage_missing:{stat_id}" for stat_id in missing_wave)

    return CanonicalPipelineResult(
        base_stage=base_stage,
        start_stage=start_stage,
        at_wave_stage=at_wave_stage,
        diagnostics=diagnostics,
        missing=sorted(set(missing)),
        stat_inputs=stage2_inputs,
        run_context=run_context,
        tier_rules=tier_rules,
        wave_state=wave_state,
        start_engine_result=start_result,
    )



def _load_runtime_dag_contract() -> tuple[Optional[Dict[str, Any]], List[str]]:
    try:
        dag_payload = load_dag_table()
    except FileNotFoundError:
        return None, ["dag_runtime_binding:missing_dag_table"]
    except ValueError:
        return None, ["dag_runtime_binding:invalid_dag_table"]

    nodes = dag_payload.get("nodes", {})
    if not isinstance(nodes, dict) or not nodes:
        return None, ["dag_runtime_binding:missing_nodes"]

    return {
        "enabled": True,
        "node_count": len(nodes),
    }, []


def _missing_required_stage_stats(values: Dict[str, float], *, required: List[str]) -> List[str]:
    missing: List[str] = []
    for stat_id in required:
        if stat_id not in values:
            missing.append(stat_id)
    return missing

def _start_values(engine_result) -> Dict[str, float]:
    start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
    if start_stats is None:
        raise StatPipelineError("Missing START_OF_RUN stage values.")
    return dict(start_stats.values)


def _contributors(stat_inputs: List[StatInput], *, snapshot) -> List[ContributorRecord]:
    rows: List[ContributorRecord] = []
    for row in stat_inputs:
        rows.append(
            ContributorRecord(
                stat_id=row.stat_id,
                phase=row.phase.value,
                provenance=row.provenance or "unknown",
                level=_level_from_provenance(row, snapshot=snapshot),
                resolved_value=_resolved_stat_input_value(row),
            )
        )
    return rows



_WORKSHOP_PROVENANCE_RE = re.compile(r"^workshop_(?:table|alias):([^->]+)")


_WORKSHOP_FORMULA_STAT_TO_WORKSHOP_NAME = {
    "workshop_attack_speed": "Attack Speed",
    "workshop_critical_chance": "Critical Chance",
    "workshop_range_meters": "Range",
    "workshop_multishot_chance": "Multishot Chance",
    "workshop_multishot_targets": "Multishot Targets",
    "workshop_rapid_fire_chance": "Rapid Fire Chance",
    "workshop_rapid_fire_duration": "Rapid Fire Duration",
    "workshop_bounce_shot_chance": "Bounce Shot Chance",
    "workshop_bounce_shot_targets": "Bounce Shot Targets",
    "workshop_bounce_shot_range": "Bounce Shot Range",
    "workshop_super_crit_chance": "Super Critical Chance",
    "workshop_super_crit_mult_alt": "Super Critical Mult",
    "workshop_rend_armor_chance": "Rend Armor Chance",
    "workshop_rend_armor_mult": "Rend Armor Mult",
    "workshop_defense_percent": "Defense %",
    "workshop_thorn_damage": "Thorn Damage",
    "workshop_knockback_chance": "Knockback Chance",
    "workshop_knockback_force": "Knockback Force",
    "workshop_orb_speed": "Orb Speed",
    "workshop_orbs": "Orbs",
    "workshop_shockwave_size": "Shockwave Size",
    "workshop_shockwave_frequency": "Shockwave Frequency",
    "workshop_land_mine_chance": "Land Mine Chance",
    "workshop_land_mine_radius": "Land Mine Radius",
    "workshop_death_defy": "Death Defy",
    "workshop_wall_health": "Wall Health",
    "workshop_wall_rebuild": "Wall Rebuild",
    "workshop_cash_per_wave": "Cash / Wave",
    "workshop_coins_per_kill_bonus": "Coin / Kill Bonus",
    "workshop_coins_per_wave": "Coin / Wave",
    "workshop_free_attack_upgrade": "Free Attack Upgrade",
    "workshop_free_defense_upgrade": "Free Defense Upgrade",
    "workshop_free_utility_upgrade": "Free Utility Upgrade",
    "workshop_interest": "Interest / Wave",
    "workshop_recovery_amount": "Recovery Amount",
    "workshop_max_recovery": "Max Amount",
    "workshop_package_chance": "Package Chance",
    "workshop_enemy_attack_level_skip": "Enemy Attack Level Skip",
    "workshop_enemy_health_level_skip": "Enemy Health Level Skip",
}


_CARD_PROVENANCE_TO_NAME = {
    "attack_speed": "Attack Speed",
    "berserker": "Berserker",
    "cash": "Cash",
    "coins": "Coins",
    "critical_chance": "Critical Chance",
    "extra_defense": "Extra Defense",
    "fortress": "Fortress",
    "free_upgrades": "Free Upgrades",
    "health": "Health",
    "health_regen": "Health Regen",
    "plasma_cannon": "Plasma Cannon",
    "range": "Range",
    "recovery_package_chance": "Recovery Package Chance",
    "ultimate_crit": "Ultimate Crit",
    "damage": "Damage",
}


def _level_from_provenance(stat_input: StatInput, *, snapshot) -> Optional[float]:
    provenance = stat_input.provenance or ""
    if provenance.startswith("relics:"):
        return None
    if provenance.startswith("uw_section:"):
        return _uw_level_from_snapshot(stat_input.stat_id, snapshot=snapshot)
    if provenance.startswith("cards:"):
        key = provenance.split(":", 1)[1].strip()
        card_name = _CARD_PROVENANCE_TO_NAME.get(key)
        if card_name is None:
            return None
        card = snapshot.cards_inventory.get(card_name)
        if card is None:
            return None
        return float(card.level)
    if provenance.startswith("workshop_formula:"):
        workshop_name = _WORKSHOP_FORMULA_STAT_TO_WORKSHOP_NAME.get(stat_input.stat_id)
        if workshop_name is None:
            return None
        workshop_entry = snapshot.workshop.get(workshop_name)
        if workshop_entry is None or workshop_entry.coin_level is None:
            return None
        return float(workshop_entry.coin_level)
    match = _WORKSHOP_PROVENANCE_RE.match(provenance)
    if match is None:
        return None
    workshop_name = match.group(1).strip()
    workshop_entry = snapshot.workshop.get(workshop_name)
    if workshop_entry is None or workshop_entry.coin_level is None:
        return None
    return float(workshop_entry.coin_level)



def _uw_level_from_snapshot(stat_id: str, *, snapshot) -> Optional[float]:
    rows = getattr(snapshot, "raw_sections", {}).get("UWs", [])
    tracks, _missing = _parse_uw_tracks(rows)
    for uw_name, track_name, level_index, _raw_value, next_cost in tracks:
        mapping = _UW_TRACK_SPECS.get(uw_name)
        if mapping is None:
            continue
        spec = mapping.get(track_name)
        if spec is None:
            continue
        if spec.stat_id == stat_id:
            return float(level_index)
        if next_cost is not None and f"{spec.stat_id}_next_cost" == stat_id:
            return float(level_index)
    return None

def _resolved_stat_input_value(stat_input: StatInput) -> float:
    if stat_input.derived_value is not None:
        return float(stat_input.derived_value)
    if stat_input.base_value is None:
        return 0.0
    resolved = float(stat_input.base_value)
    if stat_input.loadout_delta is not None:
        resolved += float(stat_input.loadout_delta)
    if stat_input.tier_rule_delta is not None:
        resolved += float(stat_input.tier_rule_delta)
    if stat_input.enhancement_multiplier is not None:
        resolved *= float(stat_input.enhancement_multiplier)
    if stat_input.tier_rule_multiplier is not None:
        resolved *= float(stat_input.tier_rule_multiplier)
    return resolved



def _resolve_loadout_inputs(problem_spec: ProblemSpec, snapshot) -> tuple[list[StatInput], list[str]]:
    preset = getattr(problem_spec.scenario, "preset", None)
    if preset is not None:
        module_context = str(preset)
    else:
        module_context = "Tourney" if problem_spec.scenario.mode == "tournament" else "Farming"
    selected_cards = None
    card_presets = getattr(snapshot, "card_presets", None)
    if isinstance(card_presets, dict):
        selected_cards = card_presets.get(module_context)
    try:
        return (
            compile_survivability_loadout_stat_inputs(
                snapshot,
                module_context=module_context,
                selected_cards=selected_cards,
                allow_provisional=True,
            ),
            [],
        )
    except Exception as exc:  # noqa: BLE001
        return [], [f"survivability_loadout:{exc}"]

def _build_wave_state(problem_spec: ProblemSpec, *, wave: int) -> tuple[Optional[RunWaveState], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    if scenario.eals_ramp is None:
        missing.append("skip_ramp:eals")
    if scenario.ehls_ramp is None:
        missing.append("skip_ramp:ehls")
    if scenario.eals_ramp is None or scenario.ehls_ramp is None:
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
    return make_wave_state(wave, eals, ehls), missing


def _load_tier_rules(problem_spec: ProblemSpec, run_context: RunContext):
    missing: List[str] = []
    if problem_spec.scenario.tier < 14:
        return None, missing
    try:
        catalog = load_tier_battle_conditions(resolve_table_path("tier_battle_conditions"), allow_incomplete=True)
    except FileNotFoundError:
        return None, ["tier_battle_conditions_table"]
    try:
        rules = build_tier_rules(problem_spec.scenario.tier, run_context, catalog)
    except ValueError:
        return None, ["tier_battle_conditions"]
    unsupported = [
        condition
        for condition in rules.conditions
        if (condition.name, condition.kind, condition.unit) not in SUPPORTED_BC
    ]
    if unsupported:
        missing.append("tier_battle_conditions_unsupported")
        return None, missing
    return rules, missing
