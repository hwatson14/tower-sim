"""
app/pipeline.py -- Layer wiring.

Owns: wiring input -> qe -> simulators -> evaluators -> advisors,
output assembly, pipeline configuration.
Must not own: domain logic.

T12: bridge removed; all _h.* calls resolved to real owners.
Domain helpers live in their real owners (evaluators.compare, input.loader).
"""
from __future__ import annotations

import csv
import json
import math
import re
import shutil
import sys
from dataclasses import asdict, replace
from collections import Counter, OrderedDict
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Active layer imports
from qe.stat_input_compiler import (
    PERK_TARGET_DESTINATION_OVERRIDES,
    TRADE_OFF_BENEFIT_EFFECT_INDEXES,
    compile_stat_inputs,
    load_perk_effects,
    load_perk_entities,
    normalize_state_mode,
    scaled_perk_value,
    SUPPORTED_STATE_MODES,
    state_mode_support,
)
from app.models import (
    PipelineRunRequest,
    PipelineStageRecord,
    PipelineTrace,
    PipelineRunResult,
    VerificationSnapshotSpec,
    FastCheckpointRequest,
    FastCheckpointResult,
    _normalize_perk_state,
)
from app.publication import (
    FULL_PIPELINE_PUBLICATION_ARTIFACTS,
    RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS,
    RUN_STATS_COMMITTED_BASELINE_ARTIFACTS,
    RUN_STATS_LOCAL_SUPPORT_ARTIFACTS,
    _build_input_dashboard_payload,
    _build_stats_dashboard_payload,
    _remove_legacy_outputs,
    _RUN_STATS_LEGACY_OUTPUTS,
    _json_sanitize,
    _relpath_str,
    _load_json_artifact,
    _generated_output_paths,
    write_core_outputs,
    write_pipeline_trace,
)
from app.display import (
    annotate_compare_display_fields as _annotate_compare_display_fields,
    annotate_display_fields as _annotate_display_fields,
)
from input.loader import load_inputs
from input.loader import MANUAL_INPUTS_PATH, write_perk_policy
from input.run_tracker import summarize_run_tracker_csv
from input.runtime_state import build_runtime_state
from qe.contracts import (
    load_section_layout_contract,
    normalize_surface_id_to_contract,
    normalize_contract_payload,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)
from qe.publication import publish_query_surfaces
from qe.routing import QEResolutionPlanner, query_response_to_statbook, resolve_checkpoint_surfaces
from qe.shared_runtime_context import get_default_qe_shared_runtime_context
from qe.query_module_policy import build_module_card_payloads
from simulators.progression import resolve_run_stats_progression_bundle
from simulators.contracts import SimulatorCheckpointState
from simulators.timing import (
    boss_contact_time_seconds as timing_boss_contact_time_seconds,
    boss_hit_interval_seconds as timing_boss_hit_interval_seconds,
    boss_pre_contact_damage_window,
    compile_timing_family_rows,
    energy_net_mastery_damage_window_seconds,
    farming_econ_timing_readiness_summary,
    flame_bot_hit_timing_weighted_boss_hit_chance,
    flame_bot_static_boss_hit_chance,
    merge_scenario_publication_rows as merge_timing_scenario_publication_rows,
    resolve_timing_consumer_bundle,
    shockwave_active_fraction,
    timed_dr_lanes_from_sources,
    timed_dr_source,
)
from simulators.geometry import (
    boss_wall_travel_displayed_proxy_from_tower_range,
    build_run_stats_geometry_artifacts,
)
from input.state_types import ScenarioProjectionState, ScenarioRuntimeInputs
from qe.models import BoundStatInputs, StatRow, bind_state_identity
from qe.materializer import materialized_surface_id_for_contract, query_evidence_surface_id_for_contract

BOSS_WAVE_SOURCE_REPLACEMENT = 'replacement'
BOSS_WAVE_FIELD_MAP_PATH = ROOT / 'app' / 'boss_waves_phase2a_field_map.yaml'
BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS: tuple[str, ...] = (
    'display_wave',
    'attack_wave',
    'health_wave',
    'boss_attack',
    'boss_health',
    'wall_pre_fort_hp',
    'wall_regen',
    'tower_damage_per_second',
    'effective_damage_reduction_pct',
    'boss_ttk_seconds',
    'boss_killed_before_contact',
    'boss_plasma_cannon_damage_to_boss_pct',
    'boss_orb_damage_to_boss_pct',
    'boss_electron_damage_to_boss_pct',
    'boss_wall_thorns_damage_to_boss_pct',
    'boss_expected_wall_thorns_damage_from_hits_pct',
    'boss_wall_thorns_contact_kill_seconds',
    'boss_time_to_contact_seconds',
    'boss_hit_interval_seconds',
    'incoming_damage_multiplier',
    'boss_hits_taken',
    'boss_hits_to_player',
    'boss_wall_thorns_hits',
    'boss_total_damage_taken',
    'boss_survival_margin_hp',
    'wall_hp',
    'wall_regen_gained_hp',
    'survives_boss',
    'fail_reason',
    'replacement_source',
    'summary_lane_id',
    'operator_handle_id',
)
# Selected max-wave rows do not probability-weight all-or-nothing DR, but they
# also should not assume a stochastic tag unless the modeled tag is near-certain.
BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD = 0.95
BOSS_WAVE_REPLACEMENT_PRIMITIVE_SURFACE_IDS: tuple[str, ...] = (
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
    'state::tower.free_attack_upgrade_chance_pct',
    'state::tower.free_defense_upgrade_chance_pct',
    'state::tower.free_utility_upgrade_chance_pct',
    'state::tower.damage',
    'state::tower.hp',
    'state::tower.regen',
    'state::tower.attack_speed',
    'state::tower.crit_chance_pct',
    'state::tower.crit_multiplier',
    'state::tower.range_m',
    'state::tower.damage_per_meter_multiplier',
    'state::tower.shockwave_interval_seconds',
    'state::tower.shockwave_size_m',
    'state::tower.ultimate_damage_multiplier',
    'state::tower.multishot_chance_pct',
    'state::tower.multishot_targets',
    'state::tower.rapid_fire_chance_pct',
    'state::tower.rapid_fire_duration_seconds',
    'state::tower.bounce_shot_chance_pct',
    'state::tower.bounce_shot_targets',
    'state::tower.bounce_shot_range_m',
    'state::tower.supercrit_chance_pct',
    'state::tower.supercrit_multiplier',
    'state::tower.rend_armor_chance_pct',
    'state::tower.rend_armor_multiplier',
    'state::tower.max_rend_multiplier',
    'state::wall.hp',
    'state::wall.regen',
    'state::wall.fortification_multiplier',
    'state::tower.defense_pct',
    'state::tower.defense_absolute',
    'state::labs.dissonant_echo.attack.level',
    'state::dissonance.attack.active_boost_multiplier',
    'state::dissonance.attack.echo_source_bonus',
    'state::labs.dissonant_echo.defense.level',
    'state::dissonance.defense.active_boost_multiplier',
    'state::dissonance.defense.echo_source_bonus',
    'state::labs.dissonant_echo.utility.level',
    'state::dissonance.utility.active_boost_multiplier',
    'state::dissonance.utility.echo_source_bonus',
    'state::labs.dissonant_echo.ultimate_weapons.level',
    'state::dissonance.ultimate_weapons.active_boost_multiplier',
    'state::dissonance.ultimate_weapons.echo_source_bonus',
    'state::tower.thorns_damage_pct',
    'state::wall.thorns_damage_pct',
    'state::tower.death_defy_chance_pct',
    'state::tower.orb_count',
    'state::tower.orb_speed_rpm',
    'state::cards.berserker.assumed_bonus_multiplier',
    'state::cards.super_tower.active',
    'state::cards.super_tower.bonus_multiplier',
    'state::cards.super_tower.cooldown_seconds',
    'state::cards.super_tower.mastery_active',
    'state::cards.super_tower.uw_mastery_multiplier',
    'state::cards.ultimate_crit.chance_pct',
    'state::cards.plasma_cannon.effect_pct',
    'state::cards.energy_net.duration_seconds',
    'state::capability.energy_shield.enabled',
    'state::cards.energy_shield.recharge_cooldown_seconds',
    'state::cards.energy_shield.extra_charge_count',
    'state::module.anti_cube_portal.shockwave_damage_taken_mult_x',
    'state::module.being_annihilator.guaranteed_supercrits_after_supercrit_attacks',
    'state::module.dimension_core.max_shock_stacks',
    'state::module.project_funding.cash_digit_multiplier_pct',
    'support_surface::module.project_funding.current_cash',
    'state::module.orbital_augment.electron_count',
    'state::module.primordial_collapse.bh_damage_reduction_pct',
    'state::uw.chrono_field.duration_seconds',
    'state::uw.chrono_field.cooldown_seconds',
    'state::uw.chrono_field.damage_reduction_pct',
    'state::uw.chrono_field.slow_pct',
    'state::uw.chain_lightning.max_enemy_damage_reduction_pct',
    'state::uw.chain_lightning.damage_multiplier',
    'state::uw.chain_lightning.quantity',
    'state::uw.chain_lightning.chance_pct',
    'state::uw.death_wave.damage_multiplier',
    'state::uw.death_wave.effect_wave_count',
    'state::uw.death_wave.cooldown_seconds',
    'state::uw.spotlight.bonus_multiplier',
    'state::uw.spotlight.angle_degrees',
    'state::uw.spotlight.count',
    'state::uw.black_hole.base_duration_seconds',
    'state::uw.black_hole.base_cooldown_seconds',
    'state::uw.golden_tower.base_duration_seconds',
    'state::uw.golden_tower.base_cooldown_seconds',
    'state::shock.damage_multiplier',
    'state::bot.flame.owned',
    'state::bot.flame.damage_reduction_pct',
    'state::bot.flame.cooldown_seconds',
    'state::bot.flame.range_m',
    'state::bot.flame.effective_range_m',
    'support_surface::dissonance.attack_run_active',
    'support_surface::dissonance.defense_run_active',
    'support_surface::dissonance.utility_run_active',
    'support_surface::dissonance.ultimate_weapons_run_active',
)
BOSS_WAVE_OPTIONAL_PRIMITIVE_SURFACE_IDS: tuple[str, ...] = (
    'state::cards.damage.mastery_effect',
    'state::cards.energy_net.mastery_effect',
    'state::cards.enemy_balance.mastery_effect',
)
BOSS_WAVE_SLOW_AURA_OPTIONAL_PRIMITIVE_SURFACE_IDS: tuple[str, ...] = (
    'state::cards.slow_aura.enemy_speed_pct',
    'state::cards.slow_aura.mastery_effect',
)
BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS: tuple[str, ...] = (
    'bot',
    'card_base',
    'card_mastery',
    'workshop',
    'enhancement',
    'module',
    'relic',
)
BOSS_WAVE_CONSUMED_DERIVED_PRIMITIVE_SURFACE_IDS: tuple[str, ...] = (
    'derived::edamage.uw.chain_lightning_dps',
    'derived::edamage_boss',
    'derived::edamage_ep',
    'derived::edamage.super_tower_factor',
    'derived::edamage.project_funding_factor',
)
BOSS_WAVE_PERK_POLICY_PRESETS: tuple[str, ...] = (
    'eHP Max Waves',
    'eHP Farming',
    'GC Max Waves',
    'GC Farming',
)
BOSS_WAVE_DISSONANCE_RUN_CATEGORIES: tuple[str, ...] = (
    'attack',
    'defense',
    'utility',
    'ultimate_weapons',
)
BOSS_WAVE_MILESTONE_MATRIX_TIERS: tuple[int, ...] = tuple(range(1, 22))
BOSS_WAVE_MILESTONE_MATRIX_DEFAULT_RUNTIME_INPUTS: dict[str, float] = {
    'orb_boss_total_damage_pct': 6.0,
}
BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT = 'boss_wave_milestone_matrix.json'
_BOSS_WAVE_REFERENCE_VOLATILITY_THRESHOLD_WAVE = 3000
_BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE = 5000
_BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES: tuple[str, ...] = (
    'none',
    *BOSS_WAVE_DISSONANCE_RUN_CATEGORIES,
)
_BOSS_WAVE_DISSONANCE_RUN_LABELS: dict[str, str] = {
    'none': 'Regular',
    'attack': 'Attack Dissonant Run',
    'defense': 'Defense Dissonant Run',
    'utility': 'Utility Dissonant Run',
    'ultimate_weapons': 'Ultimate Weapon Dissonant Run',
}
BOSS_WAVE_DISSONANCE_RUN_LABELS = _BOSS_WAVE_DISSONANCE_RUN_LABELS
_BOSS_WAVE_DISSONANCE_RUN_ALIASES: dict[str, str] = {
    '': 'none',
    'none': 'none',
    'regular': 'none',
    'normal': 'none',
    'baseline': 'none',
    'off': 'none',
    'attack': 'attack',
    'atk': 'attack',
    'damage': 'attack',
    'defense': 'defense',
    'defence': 'defense',
    'health': 'defense',
    'ehp': 'defense',
    'utility': 'utility',
    'econ': 'utility',
    'economy': 'utility',
    'uw': 'ultimate_weapons',
    'ultimate': 'ultimate_weapons',
    'ultimate_weapon': 'ultimate_weapons',
    'ultimate_weapons': 'ultimate_weapons',
    'ultimate weapons': 'ultimate_weapons',
}
_BOSS_WAVE_MODEL_COMPLETION_BLOCKERS: tuple[str, ...] = (
    'source_owned_non_boss_terminal_pressure_formulas',
    'source_owned_v28_damage_health_decay_magnitudes',
    'source_owned_full_boss_applicable_damage_semantics',
)
_BOSS_WAVE_TERMINAL_PRESSURE_RUNTIME_FIELDS: tuple[str, ...] = (
    'fleet_terminal_max_wave',
    'elite_terminal_max_wave',
    'protector_terminal_max_wave',
    'armored_terminal_max_wave',
    'boss_terminal_max_wave',
)
_BOSS_WAVE_TERMINAL_PRESSURE_FIELD_BY_PRESSURE: dict[str, tuple[str, ...]] = {
    'armored_enemies_blocked_hits': ('armored_terminal_max_wave',),
    'boss_ultimate_deferred': ('boss_terminal_max_wave',),
    'knockback_resistance_non_boss_pressure': ('fleet_terminal_max_wave',),
    'enemy_speed_non_boss_pressure': ('fleet_terminal_max_wave',),
    'enemy_attack_speed_non_boss_pressure': ('fleet_terminal_max_wave',),
    'more_enemies_non_boss_pressure': ('fleet_terminal_max_wave',),
    'death_defy_down_terminal_pressure': ('fleet_terminal_max_wave',),
    'energy_shields_down_terminal_pressure': ('fleet_terminal_max_wave',),
    'overheat_more_fleets_terminal_pressure': ('fleet_terminal_max_wave',),
    'overheat_more_elites_terminal_pressure': ('elite_terminal_max_wave',),
    'protector_ultimate_deferred': ('protector_terminal_max_wave',),
    'basic_ultimate_deferred': ('fleet_terminal_max_wave',),
    'fast_ultimate_deferred': ('fleet_terminal_max_wave',),
    'scatter_ultimate_deferred': ('fleet_terminal_max_wave',),
    'ray_ultimate_deferred': ('fleet_terminal_max_wave',),
    'vampire_ultimate_deferred': ('fleet_terminal_max_wave',),
    'mass_enforcement_deferred': ('fleet_terminal_max_wave',),
}


def _boss_wave_accepted_approximation_closure(
    non_boss_terminal_pressure_closure: Mapping[str, object],
) -> dict[str, object]:
    closed = bool(non_boss_terminal_pressure_closure.get('pressure_factor_approximation_closed'))
    return {
        'closed': closed,
        'mode': 'boss_wave_pressure_factor_approximation' if closed else 'none',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': (
            non_boss_terminal_pressure_closure.get('boss_wave_pressure_factor')
            if closed
            else None
        ),
        'replaced_blockers': (
            ['source_owned_non_boss_terminal_pressure_formulas'] if closed else []
        ),
        'certification_effect': (
            'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation'
            if closed
            else 'none'
        ),
        'certified_full_max_wave_model': False,
    }


def _boss_wave_model_closure_status(
    *,
    model_completion_blockers: Iterable[object],
    non_boss_terminal_pressure_closure: Mapping[str, object],
) -> str:
    blockers = [str(blocker) for blocker in list(model_completion_blockers or []) if str(blocker)]
    if blockers:
        if bool(non_boss_terminal_pressure_closure.get('pressure_factor_approximation_closed')):
            return 'partial_with_pressure_factor_approximation'
        if bool(non_boss_terminal_pressure_closure.get('exact_terminal_override_closed')):
            return 'partial_with_explicit_terminal_pressure_inputs'
        return 'partial_missing_required_model_inputs'
    if bool(non_boss_terminal_pressure_closure.get('pressure_factor_approximation_closed')):
        return 'closed_with_pressure_factor_approximation'
    if bool(non_boss_terminal_pressure_closure.get('exact_terminal_override_closed')):
        return 'closed_with_explicit_terminal_pressure_inputs'
    return 'closed_for_applicable_requirements'


def _runtime_input_positive(runtime_inputs: ScenarioRuntimeInputs | None, field_name: str) -> bool:
    if runtime_inputs is None:
        return False
    raw_value = getattr(runtime_inputs, field_name, None)
    if raw_value in (None, ''):
        return False
    try:
        return float(raw_value) > 0.0
    except (TypeError, ValueError):
        return False


def _boss_wave_terminal_pressure_runtime_override_status(
    runtime_inputs: ScenarioRuntimeInputs | None,
    unsupported_terminal_pressures: Iterable[str] | None = None,
) -> dict[str, object]:
    pressures = sorted({str(pressure) for pressure in (unsupported_terminal_pressures or ()) if str(pressure)})
    if not pressures:
        required_fields = tuple(_BOSS_WAVE_TERMINAL_PRESSURE_RUNTIME_FIELDS)
        missing_fields = tuple(
            field_name
            for field_name in required_fields
            if not _runtime_input_positive(runtime_inputs, field_name)
        )
        return {
            'closed': not missing_fields,
            'mode': 'all_terminal_pressure_inputs',
            'required_fields': list(required_fields),
            'missing_fields': list(missing_fields),
            'required_fields_by_pressure': {},
            'missing_fields_by_pressure': {},
            'unmapped_pressures': [],
        }

    required_fields_by_pressure: dict[str, list[str]] = {}
    missing_fields_by_pressure: dict[str, list[str]] = {}
    unmapped_pressures: list[str] = []
    required_fields_set: set[str] = set()
    for pressure in pressures:
        fields = _BOSS_WAVE_TERMINAL_PRESSURE_FIELD_BY_PRESSURE.get(pressure)
        if not fields:
            unmapped_pressures.append(pressure)
            continue
        required_fields_by_pressure[pressure] = list(fields)
        required_fields_set.update(fields)
        missing = [
            field_name
            for field_name in fields
            if not _runtime_input_positive(runtime_inputs, field_name)
        ]
        if missing:
            missing_fields_by_pressure[pressure] = missing
    return {
        'closed': not unmapped_pressures and not missing_fields_by_pressure,
        'mode': 'active_unsupported_pressure_inputs',
        'required_fields': sorted(required_fields_set),
        'missing_fields': sorted({field_name for fields in missing_fields_by_pressure.values() for field_name in fields}),
        'required_fields_by_pressure': required_fields_by_pressure,
        'missing_fields_by_pressure': missing_fields_by_pressure,
        'unmapped_pressures': unmapped_pressures,
    }


def _boss_wave_explicit_terminal_pressure_closed(
    runtime_inputs: ScenarioRuntimeInputs | None,
    unsupported_terminal_pressures: Iterable[str] | None = None,
) -> bool:
    return bool(
        _boss_wave_terminal_pressure_runtime_override_status(
            runtime_inputs,
            unsupported_terminal_pressures,
        )['closed']
    )


def _boss_wave_explicit_pressure_factor(runtime_inputs: ScenarioRuntimeInputs | None) -> float | None:
    if runtime_inputs is None:
        return None
    raw_value = getattr(runtime_inputs, 'boss_wave_pressure_factor', None)
    if raw_value in (None, ''):
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0.0 or math.isclose(value, 1.0):
        return None
    return value


def _boss_wave_explicit_damage_health_decay_closed(runtime_inputs: ScenarioRuntimeInputs | None) -> bool:
    return bool(_boss_wave_damage_health_decay_runtime_override_status(runtime_inputs)['closed'])


def _boss_wave_damage_health_decay_runtime_override_status(
    runtime_inputs: ScenarioRuntimeInputs | None,
    *,
    required: bool = True,
) -> dict[str, object]:
    required_fields = ('tower_damage_decay_pct', 'tower_health_decay_pct')
    missing_fields = [
        field_name
        for field_name in required_fields
        if not _runtime_input_positive(runtime_inputs, field_name)
    ]
    start_fields = ('tower_damage_decay_start_wave', 'tower_health_decay_start_wave')
    supplied_start_fields = [
        field_name
        for field_name in start_fields
        if _runtime_input_positive(runtime_inputs, field_name)
    ]
    closed = not missing_fields
    if not required:
        mode = 'not_required'
    elif closed:
        mode = 'explicit_runtime_inputs'
    else:
        mode = 'missing_source_owned_magnitudes'
    return {
        'closed': bool(closed),
        'mode': mode,
        'required': bool(required),
        'required_fields': list(required_fields),
        'missing_fields': missing_fields,
        'optional_start_wave_fields': list(start_fields),
        'supplied_start_wave_fields': supplied_start_fields,
        'source_owned_default_available': False,
    }


def _boss_wave_explicit_boss_bridge_closed(
    runtime_inputs: ScenarioRuntimeInputs | None,
    *,
    boss_damage_source: str | None = None,
) -> bool:
    if str(boss_damage_source or '').startswith('runtime_input_'):
        return True
    if runtime_inputs is None:
        return False
    if _runtime_input_positive(runtime_inputs, 'boss_applicable_damage_per_second'):
        return True
    if _runtime_input_positive(runtime_inputs, 'boss_applicable_damage_factor'):
        return True
    return all(
        _runtime_input_positive(runtime_inputs, field_name)
        for field_name in (
            'boss_edamage_target_share',
            'boss_edamage_cadence_uptime_factor',
            'boss_edamage_reliability_factor',
            'boss_edamage_semantic_normalizer',
        )
    )


def _boss_wave_explicit_gc_bridge_closed(
    runtime_inputs: ScenarioRuntimeInputs | None,
    *,
    gc_boss_damage_source: str | None = None,
) -> bool:
    return _boss_wave_explicit_boss_bridge_closed(
        runtime_inputs,
        boss_damage_source=gc_boss_damage_source,
    )


def _boss_wave_selected_model_requires_full_boss_bridge(
    *,
    selected_model: object,
    boss_damage_source: object | None,
) -> bool:
    model = str(selected_model or '')
    if model.startswith('ehp_hit_by_hit') or model.startswith('unified_hit_by_hit'):
        return False
    if (
        model.startswith('cl_only_pre_contact_boss_kill')
        and str(boss_damage_source or '') in {
            'qe_derived_boss_applicable_dps_cl_only_fail_closed_default',
            'qe_derived_edamage_boss_fail_closed_default',
            'qe_derived_edamage_boss_runtime_exposure_model',
            'qe_derived_edamage_ep_boss_exposure_model',
        }
    ):
        return False
    return True


def _boss_wave_selected_model_requires_full_gc_bridge(
    *,
    selected_model: object,
    gc_boss_damage_source: object | None,
) -> bool:
    return _boss_wave_selected_model_requires_full_boss_bridge(
        selected_model=selected_model,
        boss_damage_source=gc_boss_damage_source,
    )


def _boss_wave_model_certification_payload(
    *,
    contact_time_source: str | None = None,
    runtime_inputs: ScenarioRuntimeInputs | None = None,
    boss_damage_source: str | None = None,
    gc_boss_damage_source: str | None = None,
    non_boss_terminal_pressure_required: bool = False,
    unsupported_terminal_pressures: Iterable[str] | None = None,
    damage_health_decay_required: bool = True,
    boss_applicable_damage_required: bool | None = None,
    gc_boss_applicable_damage_required: bool = True,
) -> dict[str, object]:
    if boss_damage_source is None:
        boss_damage_source = gc_boss_damage_source
    if boss_applicable_damage_required is None:
        boss_applicable_damage_required = bool(gc_boss_applicable_damage_required)
    boss_bridge_closed = _boss_wave_explicit_boss_bridge_closed(
        runtime_inputs,
        boss_damage_source=boss_damage_source,
    )
    terminal_pressure_override_status = _boss_wave_terminal_pressure_runtime_override_status(
        runtime_inputs,
        unsupported_terminal_pressures,
    )
    terminal_pressure_closed = bool(terminal_pressure_override_status['closed'])
    pressure_factor = _boss_wave_explicit_pressure_factor(runtime_inputs)
    terminal_pressure_closed_by_factor = (
        bool(non_boss_terminal_pressure_required)
        and pressure_factor is not None
        and not terminal_pressure_closed
    )
    non_boss_terminal_pressure_closed = terminal_pressure_closed or terminal_pressure_closed_by_factor
    damage_health_decay_status = _boss_wave_damage_health_decay_runtime_override_status(
        runtime_inputs,
        required=bool(damage_health_decay_required),
    )
    blockers = list(_BOSS_WAVE_MODEL_COMPLETION_BLOCKERS)
    if not non_boss_terminal_pressure_required or non_boss_terminal_pressure_closed:
        blockers.remove('source_owned_non_boss_terminal_pressure_formulas')
    if not damage_health_decay_required or bool(damage_health_decay_status['closed']):
        blockers.remove('source_owned_v28_damage_health_decay_magnitudes')
    if not bool(boss_applicable_damage_required) or boss_bridge_closed:
        blockers.remove('source_owned_full_boss_applicable_damage_semantics')
    if str(contact_time_source or '') == 'matrix_default_assumption':
        blockers.append('matrix_default_boss_contact_time_is_uncertified_assumption')
    if not non_boss_terminal_pressure_required:
        non_boss_closure_mode = 'not_required'
    elif terminal_pressure_closed:
        non_boss_closure_mode = 'explicit_terminal_max_wave_inputs'
    elif terminal_pressure_closed_by_factor:
        non_boss_closure_mode = 'boss_wave_pressure_factor_approximation'
    else:
        non_boss_closure_mode = 'missing'
    runtime_override_closure = {
        'non_boss_terminal_pressure': bool(non_boss_terminal_pressure_closed),
        'v28_damage_health_decay_magnitudes': bool(damage_health_decay_status['closed']),
        'boss_applicable_damage_semantics': boss_bridge_closed,
        'gc_boss_applicable_damage_semantics': boss_bridge_closed,
    }
    requirement_applicability = {
        'non_boss_terminal_pressure': bool(non_boss_terminal_pressure_required),
        'v28_damage_health_decay_magnitudes': bool(damage_health_decay_required),
        'boss_applicable_damage_semantics': bool(boss_applicable_damage_required),
        'gc_boss_applicable_damage_semantics': bool(boss_applicable_damage_required),
    }
    effective_model_closure = {
        key: (not bool(requirement_applicability[key])) or bool(runtime_override_closure[key])
        for key in runtime_override_closure
    }
    non_boss_terminal_pressure_closure = {
        'closed': bool(non_boss_terminal_pressure_closed),
        'mode': non_boss_closure_mode,
        'exact_terminal_override_closed': bool(terminal_pressure_closed),
        'pressure_factor_approximation_closed': bool(terminal_pressure_closed_by_factor),
        'boss_wave_pressure_factor': pressure_factor,
    }
    accepted_approximation_closure = _boss_wave_accepted_approximation_closure(
        non_boss_terminal_pressure_closure
    )
    model_closure_status = _boss_wave_model_closure_status(
        model_completion_blockers=blockers,
        non_boss_terminal_pressure_closure=non_boss_terminal_pressure_closure,
    )
    return {
        'certified_full_max_wave_model': False,
        'model_certification_status': 'partial_boss_contact_model',
        'model_closure_status': model_closure_status,
        'certified_scope': 'boss_contact_survivability_with_explicit_runtime_overrides',
        'model_completion_blockers': blockers,
        'unsupported_terminal_pressures': sorted({str(item) for item in (unsupported_terminal_pressures or ())}),
        'terminal_pressure_runtime_override_status': terminal_pressure_override_status,
        'non_boss_terminal_pressure_closure': non_boss_terminal_pressure_closure,
        'accepted_approximation_closure': accepted_approximation_closure,
        'v28_damage_health_decay_closure': damage_health_decay_status,
        'runtime_override_closure': runtime_override_closure,
        'effective_model_closure': effective_model_closure,
        'model_requirement_applicability': requirement_applicability,
        'explicit_runtime_overrides_supported': [
            'boss_time_to_contact_seconds',
            'boss_hit_interval_seconds',
            'effective_damage_reduction_pct',
            'incoming_damage_multiplier',
            'boss_wave_pressure_factor',
            'orb_boss_hit_pct',
            'orb_boss_hit_count',
            'orb_boss_total_damage_pct',
            'electron_hit_count',
            'electron_total_damage_pct',
            'flame_bot_damage_reduction_pct',
            'flame_bot_boss_hit_chance_pct',
            'flame_bot_duration_seconds',
            'flame_bot_cooldown_seconds',
            'defense_field_damage_reduction_pct',
            'defense_field_duration_seconds',
            'defense_field_cooldown_seconds',
            'black_hole_damage_reduction_pct',
            'black_hole_duration_seconds',
            'black_hole_cooldown_seconds',
            'pbh_encounter_uptime_fraction',
            'boss_applicable_damage_per_second',
            'boss_applicable_damage_factor',
            'boss_edamage_target_share',
            'boss_edamage_cadence_uptime_factor',
            'boss_edamage_reliability_factor',
            'boss_edamage_semantic_normalizer',
            'death_wave_health_max_multiplier',
            'death_wave_health_max_wave',
            'enemy_level_skip_reduction_pp',
            'enemy_level_skip_decay_start_wave',
            'enemy_level_skip_decay_pct',
            'enemy_level_skip_decay_interval_waves',
            'tower_damage_decay_start_wave',
            'tower_damage_decay_pct',
            'tower_health_decay_start_wave',
            'tower_health_decay_pct',
            'fleet_terminal_max_wave',
            'elite_terminal_max_wave',
            'protector_terminal_max_wave',
            'armored_terminal_max_wave',
            'boss_terminal_max_wave',
        ],
    }
_BOSS_WAVE_DISSONANCE_RUNTIME_INPUT_KEYS: tuple[str, ...] = (
    'dissonance_run_category',
    'dissonant_run_category',
    'disco_run_category',
    'disco_category',
)
_BOSS_WAVE_SKIP_WORKSHOP_TRACK_BY_SURFACE: dict[str, str] = {
    'state::tower.enemy_attack_level_skip_pct': 'Enemy Attack Level Skip',
    'state::tower.enemy_health_level_skip_pct': 'Enemy Health Level Skip',
}


def _load_json_config(path: Path) -> dict:
    import json
    return json.loads(path.read_text(encoding='utf-8'))


def _safe_pct(n: int, d: int) -> float:
    return round((100.0 * n / d), 2) if d else 0.0


def _normalize_boss_wave_source(source_id: str | None) -> str:
    normalized = str(source_id or BOSS_WAVE_SOURCE_REPLACEMENT).strip()
    if normalized != BOSS_WAVE_SOURCE_REPLACEMENT:
        raise ValueError(f"unsupported Boss Waves source {source_id!r}; Boss Waves product path is replacement-only")
    return normalized


def _normalize_boss_wave_dissonance_run_category(value: object | None) -> str:
    normalized = str(value or '').strip().lower().replace('-', '_')
    normalized = ' '.join(normalized.replace('_', ' ').split())
    category = _BOSS_WAVE_DISSONANCE_RUN_ALIASES.get(normalized)
    if category is None:
        compact = normalized.replace(' ', '_')
        category = _BOSS_WAVE_DISSONANCE_RUN_ALIASES.get(compact)
    if category is None:
        raise ValueError(
            f"unsupported Boss Waves Dissonant Run category {value!r}; "
            f"expected one of {', '.join(_BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES)}"
        )
    return category


def _boss_wave_dissonance_run_category_from_inputs(
    *,
    explicit_category: object | None,
    scenario_runtime_inputs: Mapping[str, object] | None,
) -> str:
    if explicit_category is not None:
        return _normalize_boss_wave_dissonance_run_category(explicit_category)
    raw = scenario_runtime_inputs or {}
    for key in _BOSS_WAVE_DISSONANCE_RUNTIME_INPUT_KEYS:
        if key in raw and raw[key] is not None:
            return _normalize_boss_wave_dissonance_run_category(raw[key])
    return 'none'


def _boss_wave_dissonance_restriction_spec(category: str) -> dict[str, object]:
    from qe.kb_surfaces import load_dissonant_run_restrictions

    normalized = _normalize_boss_wave_dissonance_run_category(category)
    if normalized == 'none':
        return {
            'primitive_restrictions': {},
            'conditional_primitive_restrictions': {},
            'zero_workshop_tracks': (),
            'disabled_runtime_systems': (),
        }
    restrictions = load_dissonant_run_restrictions()
    return dict(restrictions[normalized])


def _boss_wave_dissonance_support_rows(category: str) -> dict[str, StatRow]:
    normalized = _normalize_boss_wave_dissonance_run_category(category)
    if normalized == 'none':
        return {}
    surface_id = f'support_surface::dissonance.{normalized}_run_active'
    return {
        surface_id: StatRow(
            stat_name=surface_id,
            final_value=True,
            value_type='bool',
            source_count=1,
            status='resolved',
            notes=f'boss_waves_dissonant_run_category:{normalized}',
            contributors=[
                {
                    'stat_name': 'context::boss_waves.dissonance_run_category',
                    'source_class': 'runtime_scenario',
                    'contributor_id': f'boss_waves__dissonance_run__{normalized}_mask',
                    'value': True,
                    'value_type': 'bool',
                    'composition_stage': 'gate_enable_disable',
                    'active': True,
                }
            ],
        )
    }


def _boss_wave_decomposed_edamage_bridge_factor(runtime_inputs: ScenarioRuntimeInputs) -> float | None:
    fields = (
        'boss_edamage_target_share',
        'boss_edamage_cadence_uptime_factor',
        'boss_edamage_reliability_factor',
        'boss_edamage_semantic_normalizer',
    )
    values = [getattr(runtime_inputs, field) for field in fields]
    provided = [value is not None for value in values]
    if not any(provided):
        return None
    if not all(provided):
        missing = ', '.join(field for field, is_provided in zip(fields, provided) if not is_provided)
        raise ValueError(
            'Boss Waves decomposed eDamage bridge requires all component factors when any are supplied; '
            f'missing {missing}.'
        )
    factor = 1.0
    for value in values:
        factor *= max(0.0, float(value or 0.0))
    return factor


def _boss_wave_source_selection_payload(
    requested_source: str,
    *,
    active_source: str,
    csv_export_source: str | None = None,
    diagnostics_source: str | None = None,
) -> dict[str, object]:
    selected_csv = csv_export_source or active_source
    selected_diagnostics = diagnostics_source or active_source
    return {
        'requested_source': _normalize_boss_wave_source(requested_source),
        'active_source': _normalize_boss_wave_source(active_source),
        'operator_table_source': active_source,
        'summary_source': active_source,
        'csv_export_source': selected_csv,
        'diagnostics_source': selected_diagnostics,
        'field_map_artifact': str(BOSS_WAVE_FIELD_MAP_PATH.relative_to(ROOT)),
    }


def _boss_wave_mode_id_for_preset(preset_name: str) -> str:
    if preset_name == 'Tourney':
        return 'tournament'
    if preset_name == 'Milestone':
        return 'milestone'
    return 'farming'


def _boss_wave_loadout_profile_preset(*, boss_preset_name: str, perk_policy_preset: str | None) -> str:
    policy = str(perk_policy_preset or '').strip().lower()
    if 'farming' in policy or policy.endswith(' farm'):
        return 'Farming'
    if policy.startswith('gc '):
        return 'Tourney'
    if policy.startswith('ehp '):
        return 'Farming'
    if boss_preset_name in {'Farming', 'Tourney'}:
        return boss_preset_name
    return 'Farming'


def _boss_wave_card_profile_preset(*, loadout_profile_preset: str, perk_policy_preset: str | None) -> str:
    policy = str(perk_policy_preset or '').strip().lower()
    if 'farming' in policy or policy.endswith(' farm'):
        return 'Farming'
    if policy.startswith('gc '):
        return 'Tourney'
    if policy.startswith('ehp '):
        return 'Farming'
    if str(loadout_profile_preset) in {'Farming', 'Tourney'}:
        return str(loadout_profile_preset)
    return 'Farming'


def _boss_wave_loadout_type(perk_policy_preset: str | None) -> str:
    policy = str(perk_policy_preset or '').strip().lower()
    if 'farming' in policy or policy.endswith(' farm'):
        return 'farm'
    if policy.startswith('gc '):
        return 'gc'
    if policy.startswith('ehp '):
        return 'ehp'
    return 'loadout'


def _boss_wave_spotlight_coverage(*, count: object, angle_degrees: object) -> float:
    try:
        count_value = max(0.0, float(count or 0.0))
        angle_value = max(0.0, float(angle_degrees or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, (count_value * angle_value) / 360.0)


def _boss_wave_flame_bot_lifetime_row_timed_dr(
    *,
    primitives: Mapping[str, object],
    timed_dr_sources: Mapping[str, Mapping[str, object]],
    boss_lifetime_seconds: object,
    boss_hits_to_player: object,
    boss_hit_interval_seconds: object,
) -> tuple[dict[str, float], dict[str, object], dict[str, object]] | None:
    if boss_lifetime_seconds in (None, ''):
        return None
    from qe.kb_surfaces import BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT

    flame_source = dict(timed_dr_sources.get('flame_bot') or {})
    static_model = dict(flame_source.get('static_hit_chance_model') or {})
    if static_model.get('status') != 'resolved' or not bool(flame_source.get('binary_outcome')):
        return None
    contact_hit_chance = max(
        0.0,
        min(1.0, float(static_model.get('hit_fraction') or flame_source.get('uptime_fraction') or 0.0)),
    )
    hit_weighted_chance, lifetime_components = flame_bot_hit_timing_weighted_boss_hit_chance(
        tower_range_m=primitives.get('tower_range_m'),
        flame_bot_effective_range_m=primitives.get('flame_bot_effective_range_m'),
        flame_bot_cooldown_seconds=flame_source.get('cooldown_seconds'),
        boss_time_to_contact_seconds=primitives.get('boss_time_to_contact_seconds'),
        energy_net_hold_seconds=primitives.get('boss_time_to_contact_energy_net_hold_seconds'),
        boss_lifetime_seconds=boss_lifetime_seconds,
        boss_hits_to_player=boss_hits_to_player,
        boss_hit_interval_seconds=boss_hit_interval_seconds,
        contact_window_hit_fraction=contact_hit_chance,
        boss_heat_up_damage_per_hit_pct=BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT,
    )
    if lifetime_components.get('status') != 'resolved':
        return None
    updated_flame_source = timed_dr_source(
        damage_reduction_pct=float(flame_source.get('damage_reduction_pct') or 0.0),
        duration_seconds=None,
        cooldown_seconds=float(flame_source.get('cooldown_seconds') or 0.0),
        explicit_uptime_fraction=hit_weighted_chance,
        explicit_uptime_source='static_boss_hit_timing_weighted_overlap_fraction',
        primitive_status='static_boss_hit_timing_weighted_overlap_model',
        binary_outcome=True,
        binary_avg_hit_threshold=BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD,
    )
    updated_flame_source['static_hit_chance_model'] = lifetime_components
    updated_sources: dict[str, dict[str, object]] = {
        str(name): dict(source)
        for name, source in timed_dr_sources.items()
    }
    updated_sources['flame_bot'] = updated_flame_source
    return (
        timed_dr_lanes_from_sources(
            updated_sources,
            binary_avg_hit_threshold=BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD,
            excluded_source_names=('black_hole_pbh',),
        ),
        updated_sources,
        lifetime_components,
    )


def _boss_wave_add_flame_bot_lifetime_row_fields(
    row: dict[str, object],
    *,
    timed_dr_sources: Mapping[str, Mapping[str, object]],
    lifetime_components: Mapping[str, object] | None,
) -> None:
    flame_source = dict(timed_dr_sources.get('flame_bot') or {})
    contact_model = dict(flame_source.get('static_hit_chance_model') or {})
    if contact_model.get('status') != 'resolved' or lifetime_components is None:
        return
    row['flame_bot_contact_window_hit_chance_pct'] = contact_model.get('hit_chance_pct')
    row['flame_bot_lifetime_hit_chance_pct'] = lifetime_components.get('hit_chance_pct')
    row['flame_bot_lifetime_exposure_seconds'] = lifetime_components.get('total_exposure_seconds')
    row['flame_bot_lifetime_post_contact_seconds'] = lifetime_components.get('post_contact_seconds')
    row['flame_bot_lifetime_average_spatial_fraction'] = lifetime_components.get('average_spatial_fraction')
    row['flame_bot_hit_timing_weighted_hit_chance_pct'] = lifetime_components.get(
        'hit_timing_weighted_hit_chance_pct'
    )
    row['flame_bot_hit_timing_sample_count'] = lifetime_components.get('hit_timing_sample_count')
    row['flame_bot_hit_state_semantics'] = lifetime_components.get('hit_state_semantics')
    row['flame_bot_hit_timing_semantics'] = lifetime_components.get('hit_timing_semantics')


def _positive_factor(value: object, *, default: float = 1.0) -> float:
    try:
        factor = float(value or 0.0)
    except (TypeError, ValueError):
        return default
    return factor if factor > 0.0 else default


def _boss_wave_apply_pre_contact_damage_window_diagnostics(primitives: dict[str, object]) -> None:
    damage_per_second = max(
        0.0,
        float(primitives.get('boss_damage_per_second') or primitives.get('gc_boss_damage_per_second') or 0.0),
    )
    timing_window = boss_pre_contact_damage_window(
        damage_per_second=damage_per_second,
        contact_seconds=primitives.get('boss_time_to_contact_seconds'),
        base_contact_seconds=primitives.get('boss_time_to_contact_base_seconds'),
        energy_net_hold_seconds=primitives.get('boss_time_to_contact_energy_net_hold_seconds'),
        energy_net_mastery_multiplier=primitives.get('energy_net_mastery_multiplier'),
        energy_net_damage_multiplier_duration_seconds=primitives.get(
            'energy_net_damage_multiplier_duration_seconds'
        ),
    )
    primitives['edamage_boss_contact_time_exposure_factor'] = timing_window['contact_time_exposure_factor']
    primitives['edamage_boss_movement_time_exposure_factor'] = timing_window['movement_time_exposure_factor']
    primitives['edamage_boss_pre_contact_base_window_damage'] = timing_window['base_window_damage']
    primitives['edamage_boss_pre_contact_energy_net_boosted_seconds'] = timing_window[
        'energy_net_boosted_seconds'
    ]
    primitives['edamage_boss_pre_contact_energy_net_incremental_damage'] = timing_window[
        'energy_net_incremental_damage'
    ]
    primitives['edamage_boss_pre_contact_timed_window_damage'] = (
        timing_window['timed_window_damage']
    )


def _boss_wave_apply_default_edamage_boss_runtime_factors(primitives: dict[str, object]) -> None:
    source = str(primitives.get('boss_damage_source') or primitives.get('gc_boss_damage_source') or '')
    ep_damage = max(0.0, float(primitives.get('edamage_ep') or 0.0))
    cl_base_dps = max(0.0, float(primitives.get('qe_boss_applicable_cl_only_damage_per_second') or 0.0))
    base_dps = ep_damage if ep_damage > 0.0 else cl_base_dps
    primitives['edamage_boss_base_damage_per_second'] = base_dps
    primitives['edamage_boss_base_ep_damage'] = ep_damage
    primitives['edamage_boss_base_cl_damage_per_second'] = cl_base_dps
    if source != 'qe_derived_edamage_boss_fail_closed_default':
        current_boss_dps = max(
            0.0,
            float(primitives.get('boss_damage_per_second') or primitives.get('gc_boss_damage_per_second') or 0.0),
        )
        primitives['boss_damage_per_second'] = current_boss_dps
        primitives['gc_boss_damage_per_second'] = current_boss_dps
        if source:
            primitives['boss_damage_source'] = source
            primitives['gc_boss_damage_source'] = source
        primitives['edamage_boss_ep_spotlight_factor'] = 1.0
        primitives['edamage_boss_ep_acp_factor'] = 1.0
        primitives['edamage_boss_ep_slow_factor'] = 1.0
        primitives['edamage_boss_spotlight_coverage_fraction'] = 0.0
        primitives['edamage_boss_spotlight_exposure_fraction'] = 0.0
        primitives['edamage_boss_spotlight_factor'] = 1.0
        primitives['edamage_boss_om_chip_forces_spotlight'] = False
        primitives['edamage_boss_shockwave_hit_probability'] = 0.0
        primitives['edamage_boss_acp_active_fraction'] = 0.0
        primitives['edamage_boss_acp_factor'] = 1.0
        primitives['edamage_boss_runtime_factor'] = 1.0
        primitives['edamage_boss_damage_per_second'] = current_boss_dps
        _boss_wave_apply_pre_contact_damage_window_diagnostics(primitives)
        return

    ep_spotlight_factor = _positive_factor(primitives.get('ep_edamage_spotlight_factor'))
    ep_acp_factor = _positive_factor(primitives.get('ep_edamage_acp_factor'))
    ep_slow_factor = _positive_factor(primitives.get('ep_edamage_slow_factor'))

    spotlight_coverage = _boss_wave_spotlight_coverage(
        count=primitives.get('spotlight_count'),
        angle_degrees=primitives.get('spotlight_angle_degrees'),
    )
    om_chip_forces_spotlight = bool(primitives.get('om_chip_equipped'))
    spotlight_exposure = 1.0 if om_chip_forces_spotlight else spotlight_coverage
    spotlight_bonus = max(1.0, float(primitives.get('spotlight_bonus_multiplier') or 1.0))
    spotlight_factor = 1.0 + ((spotlight_bonus - 1.0) * spotlight_exposure)

    acp_bonus = max(0.0, float(primitives.get('anti_cube_portal_shockwave_damage_taken_mult_x') or 0.0))
    acp_restricted = bool(primitives.get('dissonance_defense_run_active')) or bool(
        float(primitives.get('edamage_defense_dissonance_shockwave_restricted') or 0.0)
    )
    shockwave_hit_probability, acp_active_fraction = shockwave_active_fraction(
        contact_time_seconds=primitives.get('boss_time_to_contact_seconds'),
        shockwave_interval_seconds=primitives.get('tower_shockwave_interval_seconds'),
    )
    acp_factor = 1.0
    if not acp_restricted and acp_bonus > 1.0:
        acp_factor = 1.0 + ((acp_bonus - 1.0) * acp_active_fraction)

    runtime_factor = (spotlight_factor / ep_spotlight_factor) * (acp_factor / ep_acp_factor) / ep_slow_factor
    final_dps = base_dps * runtime_factor
    primitives['edamage_boss_ep_spotlight_factor'] = ep_spotlight_factor
    primitives['edamage_boss_ep_acp_factor'] = ep_acp_factor
    primitives['edamage_boss_ep_slow_factor'] = ep_slow_factor
    primitives['edamage_boss_spotlight_coverage_fraction'] = spotlight_coverage
    primitives['edamage_boss_spotlight_exposure_fraction'] = spotlight_exposure
    primitives['edamage_boss_spotlight_factor'] = spotlight_factor
    primitives['edamage_boss_om_chip_forces_spotlight'] = om_chip_forces_spotlight
    primitives['edamage_boss_shockwave_hit_probability'] = shockwave_hit_probability
    primitives['edamage_boss_acp_active_fraction'] = 0.0 if acp_restricted else acp_active_fraction
    primitives['edamage_boss_acp_factor'] = acp_factor
    primitives['edamage_boss_runtime_factor'] = runtime_factor
    primitives['edamage_boss_damage_per_second'] = final_dps
    primitives['boss_damage_per_second'] = final_dps
    primitives['boss_damage_source'] = 'qe_derived_edamage_ep_boss_exposure_model'
    primitives['gc_boss_damage_per_second'] = final_dps
    primitives['gc_boss_damage_source'] = 'qe_derived_edamage_ep_boss_exposure_model'
    _boss_wave_apply_pre_contact_damage_window_diagnostics(primitives)


def _boss_wave_replacement_primitive_surface_ids(account_state, *, preset_name: str) -> tuple[str, ...]:
    surface_ids = list(BOSS_WAVE_REPLACEMENT_PRIMITIVE_SURFACE_IDS)
    surface_ids.extend(BOSS_WAVE_OPTIONAL_PRIMITIVE_SURFACE_IDS)
    equipped_cards = set((getattr(account_state, 'card_presets', {}) or {}).get(preset_name, []) or [])
    if 'Slow Aura' in equipped_cards:
        surface_ids.extend(BOSS_WAVE_SLOW_AURA_OPTIONAL_PRIMITIVE_SURFACE_IDS)
    return tuple(dict.fromkeys(surface_ids))


def _extract_optional_wave_number(raw_value) -> int | None:
    if raw_value in (None, ''):
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    digits = ''.join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        value = int(digits)
    except ValueError:
        return None
    return value if value > 0 else None


def _extract_wave_number_including_zero(raw_value) -> int | None:
    if raw_value in (None, ''):
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    digits = ''.join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _boss_wave_reference_gap_reason(reference_raw_wave: int | None) -> str:
    return 'zero_reference_wave' if reference_raw_wave == 0 else 'missing_reference_wave'


def _annotate_boss_wave_dissonance_pb_cap_omissions(
    rows: list[dict[str, object]],
    *,
    account_state=None,
) -> None:
    cap_tier_sources_by_category: dict[str, dict[int, str]] = {}

    def record_cap_tier(category: object, tier: object, source: str) -> None:
        category_id = str(category or 'none')
        if category_id == 'none':
            return
        tier_number = _extract_tier_number(tier)
        if tier_number is None:
            return
        cap_tier_sources_by_category.setdefault(category_id, {}).setdefault(tier_number, source)

    for tier_label, pbs in dict(getattr(account_state, 'dissonance_pbs_by_tier', {}) or {}).items():
        if not isinstance(pbs, Mapping):
            continue
        for category, raw_value in dict(pbs).items():
            reference = _extract_optional_wave_number(raw_value)
            raw_reference = _extract_wave_number_including_zero(raw_value)
            if max(reference or 0, raw_reference or 0) >= _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE:
                record_cap_tier(
                    category,
                    tier_label,
                    'account_state.dissonance_pbs_by_tier',
                )

    for row in rows:
        if str(row.get('reference_kind') or '') != 'ids_dissonant_pb_wave':
            continue
        category = str(row.get('dissonance_run_category') or 'none')
        if category == 'none':
            continue
        reference = _extract_optional_wave_number(row.get('reference_wave'))
        raw_reference = _extract_wave_number_including_zero(row.get('reference_raw_wave'))
        if max(reference or 0, raw_reference or 0) >= _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE:
            record_cap_tier(category, row.get('tier'), 'matrix_rows')

    for row in rows:
        context = {
            'applies': False,
            'mode': 'not_applicable',
            'dissonance_pb_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
        }
        row['dissonance_pb_cap_omitted_reference'] = False
        row['dissonance_pb_cap_omission_context'] = context
        if str(row.get('reference_kind') or '') != 'ids_dissonant_pb_wave':
            continue
        category = str(row.get('dissonance_run_category') or 'none')
        if category == 'none':
            continue
        reference = _extract_optional_wave_number(row.get('reference_wave'))
        raw_reference = _extract_wave_number_including_zero(row.get('reference_raw_wave'))
        if reference is not None or raw_reference != 0:
            continue
        tier = int(row.get('tier') or 0)
        cap_tier_sources = dict(cap_tier_sources_by_category.get(category) or {})
        cap_tiers = sorted(cap_tier for cap_tier in cap_tier_sources if cap_tier and cap_tier < tier)
        if not cap_tiers:
            continue
        evidence_source = (
            'account_state.dissonance_pbs_by_tier'
            if any(
                cap_tier_sources.get(cap_tier) == 'account_state.dissonance_pbs_by_tier'
                for cap_tier in cap_tiers
            )
            else 'matrix_rows'
        )
        context = {
            'applies': True,
            'mode': 'zero_ids_dissonant_pb_after_bonus_cap_reached',
            'reference_interpretation': 'intentionally_unfilled_after_dissonance_bonus_cap_reached',
            'dissonance_pb_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
            'cap_reached_tiers': cap_tiers,
            'nearest_cap_tier': cap_tiers[-1],
            'evidence_source': evidence_source,
        }
        row['dissonance_pb_cap_omitted_reference'] = True
        row['dissonance_pb_cap_omission_context'] = context


def _extract_runtime_wave_number(raw_value) -> int | None:
    if raw_value in (None, ''):
        return None
    if isinstance(raw_value, (int, float)):
        value = int(raw_value)
        return value if value > 0 else None
    return _extract_optional_wave_number(raw_value)


def _resolve_boss_wave_run_context(
    account_state,
    *,
    preset_name: str,
    tier_number: int,
    checkpoint_every_bosses: int,
    tournament_wave_override: int | None = None,
) -> dict[str, object]:
    from simulators.scenario import (
        ScenarioConfig,
        compute_scenario_surfaces,
        tournament_tier_for_league,
    )

    mode_id = _boss_wave_mode_id_for_preset(preset_name)
    league = None
    tournament_wave = None
    if mode_id == 'tournament':
        league = (
            account_state.player_meta.get('Tourney League')
            or account_state.player_meta.get('Tournament League')
            or account_state.player_meta.get('League')
        )
        tournament_wave = (
            int(tournament_wave_override)
            if tournament_wave_override is not None and int(tournament_wave_override) > 0
            else None
        ) or (
            _extract_optional_wave_number(account_state.player_meta.get('Tournament Wave'))
            or _extract_optional_wave_number(account_state.player_meta.get('Tourney Wave'))
        )
        tournament_wave_source = 'runtime_override' if tournament_wave_override is not None and int(tournament_wave_override) > 0 else 'IDS::Player & Stuff'
        if not league:
            return {
                'resolved': False,
                'mode_id': mode_id,
                'preset_name': preset_name,
                'tier_number': int(tier_number),
                'tier_column': f'Tier {int(tier_number)}',
                'checkpoint_every_bosses': max(1, int(checkpoint_every_bosses)),
                'context_error': 'missing_tournament_league',
                'context_error_message': 'Boss Waves Tourney mode requires a resolved tournament league in player metadata.',
            }
        if tournament_wave is None:
            return {
                'resolved': False,
                'mode_id': mode_id,
                'preset_name': preset_name,
                'tier_number': int(tier_number),
                'tier_column': f'Tier {int(tier_number)}',
                'league': league,
                'tournament_wave_source': tournament_wave_source,
                'checkpoint_every_bosses': max(1, int(checkpoint_every_bosses)),
                'context_error': 'missing_tournament_wave',
                'context_error_message': 'Boss Waves Tourney mode requires a resolved tournament wave. This repo baseline does not ship that context for the active account snapshot.',
            }
        tournament_tier = tournament_tier_for_league(league)
        if tournament_tier is None:
            return {
                'resolved': False,
                'mode_id': mode_id,
                'preset_name': preset_name,
                'tier_number': int(tier_number),
                'tier_column': f'Tier {int(tier_number)}',
                'league': league,
                'tournament_wave_source': tournament_wave_source,
                'checkpoint_every_bosses': max(1, int(checkpoint_every_bosses)),
                'context_error': 'unsupported_tournament_league',
                'context_error_message': (
                    'Boss Waves Tourney mode only supports tournament leagues with '
                    'source-owned tier mappings.'
                ),
            }
        scenario_config = ScenarioConfig(
            mode_id='tournament',
            tier=int(tournament_tier),
            league=str(league),
            tournament_wave=int(tournament_wave),
        )
    else:
        scenario_config = ScenarioConfig(mode_id=mode_id, tier=int(tier_number))

    scenario_surfaces = compute_scenario_surfaces(scenario_config)
    actual_boss_interval_waves = max(1, int(getattr(scenario_surfaces, 'boss_wave_interval', None) or 10))
    checkpoint_every_bosses = max(1, int(checkpoint_every_bosses))
    perks_enabled = mode_id != 'tournament'
    scenario_perk_state = 'off' if mode_id == 'tournament' else 'on'
    scenario_perk_mode = 'none' if mode_id == 'tournament' else 'runtime_timeline'
    return {
        'resolved': True,
        'mode_id': mode_id,
        'preset_name': preset_name,
        'tier_number': int(scenario_config.tier),
        'tier_column': f'Tier {int(scenario_config.tier)}',
        'requested_tier_number': int(tier_number),
        'league': scenario_config.league,
        'tournament_wave': int(scenario_config.tournament_wave or 0) or None,
        'tournament_wave_source': 'runtime_override' if mode_id == 'tournament' and tournament_wave_override is not None and int(tournament_wave_override) > 0 else 'IDS::Player & Stuff',
        'perks_enabled': perks_enabled,
        'perk_state': scenario_perk_state,
        'perk_mode': scenario_perk_mode,
        'perk_contract_owner': 'scenario_policy',
        'perk_state_source': 'scenario_policy_tournament_off_other_runs_on',
        'perk_mode_source': 'scenario_policy_tournament_none_other_runtime_timeline',
        'perk_timeline_mode': 'runtime_policy_projection' if perks_enabled else 'disabled_by_tournament_scenario',
        'actual_boss_interval_waves': actual_boss_interval_waves,
        'checkpoint_every_bosses': checkpoint_every_bosses,
        'checkpoint_stride_waves': actual_boss_interval_waves * checkpoint_every_bosses,
        'requested_start_wave': 1,
        'scenario_config': scenario_config,
        'scenario_surfaces': scenario_surfaces.to_dict(),
    }


def _build_input_dashboard_qe_publications(
    *,
    account_state,
    compare_rows_by_preset: dict[str, dict],
    projected_compare_rows_by_preset: dict[str, dict],
    stat_inputs: list,
    preset_name: str,
) -> dict[str, object]:
    from qe.publication import build_input_dashboard_qe_publications as qe_build_input_dashboard_qe_publications
    return qe_build_input_dashboard_qe_publications(
        account_state=account_state,
        compare_rows_by_preset=compare_rows_by_preset,
        projected_compare_rows_by_preset=projected_compare_rows_by_preset,
        stat_inputs=stat_inputs,
        preset_name=preset_name,
    )


def _contract_json_payload(obj):
    return normalize_contract_payload(_json_sanitize(obj))


def _current_contract_json_payload(obj):
    return obj


def load_streamlit_reference_data(*, ids_path: Path, manual_inputs_path: Path | None) -> dict[str, object]:
    from qe.query_module_policy import load_module_substat_lookup
    from qe.stat_input_compiler import (
        load_card_base_value_display_map,
        load_card_effect_display_names,
        load_card_mastery_values,
        load_perk_effects,
        load_perk_entities,
    )
    bundle = load_inputs(ids_path=ids_path, manual_inputs_path=manual_inputs_path)
    perk_policy = bundle.perk_policy or {}
    manual_banned_names = set(_resolve_manual_banned_perks(perk_policy))
    perk_entity_map = load_perk_entities()
    by_name = {str(row.get('perk_name') or '').strip(): perk_id for perk_id, row in perk_entity_map.items()}
    manual_banned_perk_ids = {by_name[name] for name in manual_banned_names if name in by_name}

    return {
        'card_effects': load_card_effect_display_names(),
        'card_values': load_card_base_value_display_map(),
        'card_mastery_values': load_card_mastery_values(),
        'perk_entity_map': perk_entity_map,
        'perk_entities': perk_entity_map,
        'perk_effects': load_perk_effects(),
        'manual_banned_perk_ids': manual_banned_perk_ids,
        'module_substat_lookup': load_module_substat_lookup(),
    }


def compute_perk_max_effect_displays(
    *,
    perk_id: str,
    standard_bonus_pct: float | None,
    tradeoff_bonus_pct: float | None,
) -> list[tuple[object, object]]:
    from qe.stat_input_compiler import load_perk_effects, load_perk_entities, scaled_perk_value
    perk_entities = load_perk_entities()
    perk_effects = load_perk_effects()
    perk_meta = perk_entities.get(perk_id) or {}
    max_picks = int(perk_meta.get('max_picks') or 0)
    perk_lab_state = {
        'standard_bonus_multiplier': 1.0 + (((standard_bonus_pct or 0.0) / 100.0)),
        'tradeoff_bonus_multiplier': 1.0 + (((tradeoff_bonus_pct or 0.0) / 100.0)),
    }
    rows: list[tuple[object, object]] = []
    for effect in (perk_effects.get(perk_id) or []):
        scaled = scaled_perk_value(
            perk_meta=perk_meta,
            perk_effect_meta=effect,
            perk_id=perk_id,
            operation=str(effect.get('operation') or '').strip(),
            raw_value=str(effect.get('effect_value') or '').strip(),
            picks=max_picks,
            effect_index=str(effect.get('effect_index') or '').strip(),
            perk_lab_state=perk_lab_state,
        )
        rows.append((scaled, effect.get('operation')))
    return rows


def _resolve_boss_wave_perk_request(
    *,
    scenario_mode_id: str,
    requested_perk_mode: str,
    requested_perk_state: str,
) -> dict[str, object]:
    requested_mode = _normalize_perk_mode(requested_perk_mode)
    requested_state = _normalize_perk_state(requested_perk_state)
    if scenario_mode_id == 'tournament':
        matched = requested_mode == 'none' and requested_state in ('auto', 'off')
        return {
            'perks_enabled': False,
            'perk_state': 'off',
            'perk_mode': 'none',
            'perk_contract_owner': 'scenario_policy_with_request_controls',
            'perk_state_source': 'scenario_policy_tournament_off',
            'perk_mode_source': 'scenario_policy_tournament_none',
            'perk_request_resolution': 'matched_scenario_policy' if matched else 'scenario_policy_overrides_request',
            'perk_timeline_mode': 'disabled_by_tournament_scenario',
        }
    if requested_mode == 'none' or requested_state == 'off':
        return {
            'perks_enabled': False,
            'perk_state': 'off',
            'perk_mode': 'none',
            'perk_contract_owner': 'request_policy_with_scenario_guard',
            'perk_state_source': 'request_perk_state_or_mode_disabled',
            'perk_mode_source': 'request_perk_mode_none_or_state_off',
            'perk_request_resolution': 'matched_request',
            'perk_timeline_mode': 'disabled_by_perk_mode_or_state',
        }
    return {
        'perks_enabled': True,
        'perk_state': 'on',
        'perk_mode': requested_mode,
        'perk_contract_owner': 'request_policy_with_scenario_guard',
        'perk_state_source': 'request_perk_state_auto_or_on',
        'perk_mode_source': 'request_perk_mode',
        'perk_request_resolution': 'matched_request',
        'perk_timeline_mode': (
            'runtime_policy_projection'
            if requested_mode == 'runtime_timeline'
            else 'max_progression_policy_static'
        ),
    }


def build_boss_wave_payload(
    request: PipelineRunRequest,
    *,
    preset_name: str,
    tier_number: int,
    end_wave: int,
    boss_wave_step: int,
    stop_on_failure: bool,
    scenario_runtime_inputs: dict[str, float],
    boss_wave_source: str = BOSS_WAVE_SOURCE_REPLACEMENT,
    perk_policy_override: dict[str, object] | None = None,
    dissonance_run_category: str | None = None,
    include_dissonance_run_matrix: bool = False,
    scenario_runtime_input_sources: dict[str, str] | None = None,
) -> dict[str, object]:
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy, perk_state_at_wave
    source_id = _normalize_boss_wave_source(boss_wave_source)
    dissonance_category = _boss_wave_dissonance_run_category_from_inputs(
        explicit_category=(
            dissonance_run_category
            if dissonance_run_category is not None
            else getattr(request, 'dissonance_run_category', None)
        ),
        scenario_runtime_inputs=scenario_runtime_inputs,
    )
    requested_perk_mode = _normalize_perk_mode(getattr(request, 'perk_mode', None))
    requested_perk_state = _normalize_perk_state(getattr(request, 'perk_state', 'auto'))
    requested_policy_preset = _normalize_perk_policy_preset_name(getattr(request, 'perk_policy_preset', None))
    scenario_mode_id = _boss_wave_mode_id_for_preset(preset_name)
    perk_request = _resolve_boss_wave_perk_request(
        scenario_mode_id=scenario_mode_id,
        requested_perk_mode=requested_perk_mode,
        requested_perk_state=requested_perk_state,
    )
    applied_perk_mode = str(perk_request['perk_mode'])
    bundle, account_state, perk_config_resolution, account_state_cache_hit = _get_boss_wave_account_state_bundle(
        ids_path=request.ids,
        manual_inputs_path=request.manual_inputs,
        runtime_state_overlay=request.runtime_state_overlay,
        perk_mode=applied_perk_mode,
        perk_policy_preset=requested_policy_preset,
    )
    perk_policy = _merged_perk_policy(
        _select_perk_policy(getattr(bundle, 'perk_policy', {}) or {}, requested_policy_preset),
        perk_policy_override,
    )
    perk_policy_payload, _perk_context = _perk_policy_context(bundle.ids_raw, perk_policy)
    perk_policy_validation = _perk_policy_validation_ledger(perk_policy_payload, _perk_context)
    resolved_context = _resolve_boss_wave_run_context(
        account_state,
        preset_name=preset_name,
        tier_number=int(tier_number),
        checkpoint_every_bosses=int(boss_wave_step),
        tournament_wave_override=_extract_runtime_wave_number(scenario_runtime_inputs.get('tournament_wave')),
    )
    if bool(resolved_context.get('resolved')):
        resolved_context.update(perk_request)
    applied_perk_state = str(perk_request['perk_state'])
    applied_perk_mode = str(perk_request['perk_mode'])
    perk_contract_owner = str(perk_request['perk_contract_owner'])
    perk_mode_source = str(perk_request['perk_mode_source'])
    perk_state_source = str(perk_request['perk_state_source'])
    perk_request_resolution = str(perk_request['perk_request_resolution'])
    perk_timeline: list[dict[str, object]] = []
    perk_timeline_diag: dict[str, object] = {
        'enabled': False,
        'reason': 'not_runtime_timeline_mode',
        'final_wave': 0,
        'generated_rows': 0,
    }
    effective_perks_enabled = bool(perk_request.get('perks_enabled'))
    perk_application_mode = 'disabled'
    static_perk_counts: dict[str, int] = {}
    if effective_perks_enabled and not perk_policy_validation['ok']:
        raise ValueError(f"Boss Waves perk policy is invalid: {perk_policy_validation['errors']!r}")
    if effective_perks_enabled and applied_perk_mode == 'runtime_timeline':
        perk_timeline, perk_timeline_diag = generate_timeline_from_policy(PerkTimelinePolicy(**perk_policy_payload))
        perk_application_mode = 'runtime_timeline'
    elif effective_perks_enabled and applied_perk_mode == 'max_progression_policy':
        static_perk_counts = _boss_wave_static_perk_counts_from_account_state(account_state)
        perk_timeline_diag = {
            'enabled': True,
            'reason': 'max_progression_policy_static_perk_state',
            'final_wave': 0,
            'generated_rows': 0,
            'static_perk_count': len(static_perk_counts),
            'static_pick_count': sum(int(value) for value in static_perk_counts.values()),
        }
        perk_application_mode = 'max_progression_policy_static'
    elif applied_perk_mode == 'none' or not bool(resolved_context.get('perks_enabled')):
        perk_timeline_diag = {
            'enabled': False,
            'reason': 'disabled_by_perk_mode_or_state',
            'final_wave': 0,
            'generated_rows': 0,
        }
    if not bool(resolved_context.get('resolved')):
        return {
            'artifact': 'boss_wave_dashboard_payload',
            'schema_version': 1,
            'contract': {
                'payload_owner': 'app.pipeline.build_boss_wave_payload',
                'simulator_owner': 'simulators.evaluator_kernel.build_scenario_overlay_table',
                'row_output_kind': 'boss_wave_replacement_selected_operator_rows',
                'summary_kind': 'unified_selected_max_wave_with_diagnostic_lanes',
                'checkpoint_mode': 'actual_boss_cadence_with_sampling',
                'start_state_basis': 'start_of_run',
                'perk_timeline_mode': 'disabled_until_context_resolves',
                'free_upgrade_mode': 'runtime_progression_allocation',
                'wave_progression_mode': 'runtime_wave_progression',
                'enemy_skip_mode': 'runtime_wave_progression',
                'tower_damage_mode': 'v21_event_only_replacement_for_operator_table',
                'survivability_semantics': 'staged_replacement_product_surfaces',
            },
            'rows': [],
            'summary': {
                'preset_name': preset_name,
                'tier_column': resolved_context.get('tier_column'),
                'state_mode': 'start_of_run',
                'max_wave': 0,
                'max_surviving_wave': 0,
                'selected_max_wave': 0,
                'selected_first_failed_wave': 0,
                'selected_max_independent_wave': 0,
                'selected_model': 'unified_hit_by_hit_boss_survival',
                'selected_loadout_type': _boss_wave_loadout_type(str(perk_policy.get('_selected_policy_preset') or '')),
                'selected_policy_preset': str(perk_policy.get('_selected_policy_preset') or ''),
                'last_contiguous_surviving_wave': 0,
                'max_independent_surviving_wave': 0,
                'first_failed_wave': 0,
                'pre_contact_boss_kill_max_wave': 0,
                'pre_contact_boss_kill_first_failed_wave': 0,
                'pre_contact_boss_kill_max_independent_wave': 0,
                'gc_pre_contact_max_wave': 0,
                'gc_pre_contact_first_failed_wave': 0,
                'gc_pre_contact_max_independent_wave': 0,
                'row_count': 0,
                'terminal_display_wave': 0,
                'survives_through_end': False,
                'result_consistent_with_rows': True,
            },
            'diagnostics': {
                'preset_name': preset_name,
                'perk_timeline_rows': len(perk_timeline),
                'perk_timeline_final_wave': int(perk_timeline_diag.get('final_wave') or 0),
                'mode_id': resolved_context.get('mode_id'),
                'tier_number': int(resolved_context.get('tier_number') or 0),
                'tier_column': resolved_context.get('tier_column'),
                'league': resolved_context.get('league'),
                'tournament_wave': resolved_context.get('tournament_wave'),
                'tournament_wave_source': resolved_context.get('tournament_wave_source'),
                'perks_enabled': False,
                'model_scope': 'boss_contact_survivability',
                'not_full_max_wave_model': True,
                'model_certification': _boss_wave_model_certification_payload(
                    contact_time_source=dict(
                        scenario_runtime_input_sources
                        or {str(key): 'caller_supplied_runtime_input' for key in scenario_runtime_inputs}
                    ).get('boss_time_to_contact_seconds'),
                    runtime_inputs=ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs),
                    damage_health_decay_required=scenario_mode_id == 'tournament',
                    gc_boss_applicable_damage_required=False,
                ),
                'unsupported_terminal_pressures': [],
                'perk_timeline_enabled': False,
                'context_status': 'error',
                'context_error': resolved_context.get('context_error'),
                'context_error_message': resolved_context.get('context_error_message'),
                'checkpoint_every_bosses': int(resolved_context.get('checkpoint_every_bosses') or 1),
                'actual_boss_interval_waves': None,
                'checkpoint_stride_waves': None,
                'requested_start_wave': 1,
                'first_checkpoint_wave': None,
                'scenario_runtime_inputs': dict(scenario_runtime_inputs),
                'scenario_runtime_input_sources': dict(
                    scenario_runtime_input_sources
                    or {str(key): 'caller_supplied_runtime_input' for key in scenario_runtime_inputs}
                ),
                'perk_mode': applied_perk_mode,
                'perk_state': applied_perk_state,
                'requested_perk_mode': requested_perk_mode,
                'requested_perk_state': requested_perk_state,
                'requested_perk_policy_preset': requested_policy_preset,
                'perk_policy_preset': str(perk_policy.get('_selected_policy_preset') or ''),
                'perk_contract_owner': perk_contract_owner,
                'perk_mode_source': perk_mode_source,
                'perk_state_source': perk_state_source,
                'perk_request_resolution': perk_request_resolution,
                'perk_config_resolution': dict(perk_config_resolution),
                'account_state_cache_hit': bool(account_state_cache_hit),
            },
            'download': {
                'format': 'csv',
                'file_name': f'{preset_name.lower()}_tier_{int(tier_number)}_boss_waves.csv',
            },
            'source_selection': _boss_wave_source_selection_payload(
                source_id,
                active_source=BOSS_WAVE_SOURCE_REPLACEMENT,
                csv_export_source=BOSS_WAVE_SOURCE_REPLACEMENT,
                diagnostics_source=BOSS_WAVE_SOURCE_REPLACEMENT,
            ),
            'operator_rows': [],
            'download_rows': [],
        }
    selected_policy_preset = str(perk_policy.get('_selected_policy_preset') or '')
    loadout_profile_preset = _boss_wave_loadout_profile_preset(
        boss_preset_name=preset_name,
        perk_policy_preset=selected_policy_preset,
    )
    card_profile_preset = _boss_wave_card_profile_preset(
        loadout_profile_preset=loadout_profile_preset,
        perk_policy_preset=selected_policy_preset,
    )
    config = {
        'execution_mode': 'table_sweep',
        'preset_name': preset_name,
        'mode_id': str(resolved_context.get('mode_id') or 'farming'),
        'tier_number': int(resolved_context.get('tier_number') or tier_number),
        'tier_column': str(resolved_context.get('tier_column') or f'Tier {int(tier_number)}'),
        'requested_tier_number': int(resolved_context.get('requested_tier_number') or tier_number),
        'league': resolved_context.get('league'),
        'tournament_wave': int(resolved_context.get('tournament_wave') or 0),
        'tournament_wave_source': resolved_context.get('tournament_wave_source'),
        'start_wave': int(resolved_context.get('requested_start_wave') or 1),
        'end_wave': int(end_wave),
        'boss_interval_waves': int(resolved_context.get('actual_boss_interval_waves') or 10),
        'checkpoint_every_bosses': int(resolved_context.get('checkpoint_every_bosses') or 1),
        'perks_enabled': effective_perks_enabled,
        'state_mode': 'start_of_run',
        'perk_mode': applied_perk_mode,
        'perk_state': applied_perk_state,
        'requested_perk_mode': requested_perk_mode,
        'requested_perk_state': requested_perk_state,
        'requested_perk_policy_preset': requested_policy_preset,
        'perk_policy_preset': selected_policy_preset,
        'loadout_profile_preset': loadout_profile_preset,
        'card_profile_preset': card_profile_preset,
        'perk_contract_owner': perk_contract_owner,
        'perk_mode_source': perk_mode_source,
        'perk_state_source': perk_state_source,
        'perk_request_resolution': perk_request_resolution,
        'perk_application_mode': perk_application_mode,
        'perk_config_resolution': dict(perk_config_resolution),
        'perk_policy_validation': dict(perk_policy_validation),
        'account_state_cache_hit': bool(account_state_cache_hit),
        'manual_advisory_inputs': dict(getattr(bundle, 'manual_advisory_inputs', {}) or {}),
        'perk_policy_override_active': bool(perk_policy_override),
        'perk_timeline': tuple(dict(row or {}) for row in perk_timeline) if perk_application_mode == 'runtime_timeline' else (),
        'static_perk_count': len(static_perk_counts),
        'static_perk_pick_count': sum(int(value) for value in static_perk_counts.values()),
        'scenario_config': resolved_context.get('scenario_config'),
        'scenario_surfaces': dict(resolved_context.get('scenario_surfaces') or {}),
        'scenario_runtime_input_sources': dict(
            scenario_runtime_input_sources
            or {str(key): 'caller_supplied_runtime_input' for key in scenario_runtime_inputs}
        ),
        'dissonance_run_category': dissonance_category,
    }
    perk_counts = (
        perk_state_at_wave(perk_timeline, 0)
        if perk_application_mode == 'runtime_timeline'
        else dict(static_perk_counts)
    )
    operator_rows, selected_summary, primitive_inputs, primitive_semantics_ledger = _build_replacement_operator_table_and_summary(
        active_source=source_id,
        config=config,
        account_state=account_state,
        preset_name=preset_name,
        perk_counts=perk_counts,
        perk_timeline=tuple(dict(row or {}) for row in perk_timeline) if perk_application_mode == 'runtime_timeline' else (),
        scenario_runtime_inputs=scenario_runtime_inputs,
        stop_on_failure=bool(stop_on_failure),
    )
    _ensure_boss_wave_selected_pressure_factor_reference_hint(
        selected_summary,
        account_state=account_state,
        tier_number=int(config['tier_number']),
        dissonance_run_category=dissonance_category,
        unsupported_terminal_pressures=(
            dict(config.get('scenario_surfaces') or {}).get('unsupported_terminal_pressures') or ()
        ),
        runtime_inputs=ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs),
    )
    download_rows = _build_replacement_download_rows(operator_rows)
    selected_diagnostics = _build_replacement_diagnostics(
        active_source=source_id,
        preset_name=preset_name,
        config=config,
        resolved_context=resolved_context,
        perk_timeline_rows=len(perk_timeline) if perk_application_mode == 'runtime_timeline' else 0,
        perk_timeline_final_wave=int(perk_timeline_diag.get('final_wave') or 0),
        scenario_runtime_inputs=scenario_runtime_inputs,
        operator_rows=operator_rows,
        download_rows=download_rows,
        summary=selected_summary,
        stop_on_failure=bool(stop_on_failure),
        account_state=account_state,
        primitive_inputs=primitive_inputs,
        primitive_semantics_ledger=primitive_semantics_ledger,
    )
    active_owner = 'simulators.evaluator_kernel.evaluate_overlay_row'
    tower_damage_mode = 'v21_event_plus_continuous_boss_damage'
    survivability_semantics = 'staged_replacement_product_surfaces'
    cutover_scope = 'boss_waves_replacement_product_complete'
    csv_export_source = source_id
    diagnostics_source = source_id
    payload = {
        'artifact': 'boss_wave_dashboard_payload',
        'schema_version': 1,
        'contract': {
            'payload_owner': 'app.pipeline.build_boss_wave_payload',
            'simulator_owner': active_owner,
            'row_output_kind': 'boss_wave_replacement_selected_operator_rows',
            'summary_kind': 'unified_selected_max_wave_with_diagnostic_lanes',
            'checkpoint_mode': 'actual_boss_cadence_with_sampling',
            'start_state_basis': 'start_of_run',
            'perk_timeline_mode': (
                'runtime_policy_projection'
                if perk_application_mode == 'runtime_timeline'
                else 'max_progression_policy_static'
                if perk_application_mode == 'max_progression_policy_static'
                else 'disabled_by_perk_mode_or_state'
            ),
            'free_upgrade_mode': 'runtime_progression_allocation',
            'wave_progression_mode': 'runtime_wave_progression',
            'enemy_skip_mode': 'runtime_wave_progression',
            'tower_damage_mode': tower_damage_mode,
            'survivability_semantics': survivability_semantics,
            'replacement_scope': cutover_scope,
            'operator_table_source': source_id,
            'summary_source': source_id,
            'csv_export_source': csv_export_source,
            'diagnostics_source': diagnostics_source,
            'field_map_artifact': str(BOSS_WAVE_FIELD_MAP_PATH.relative_to(ROOT)),
        },
        'rows': operator_rows,
        'operator_rows': operator_rows,
        'download_rows': download_rows,
        'summary': {
            'preset_name': preset_name,
            'tier_column': config['tier_column'],
            'state_mode': config['state_mode'],
            'max_wave': int(selected_summary.get('max_wave') or 0),
            'max_surviving_wave': int(selected_summary.get('max_surviving_wave') or 0),
            'selected_max_wave': int(selected_summary.get('selected_max_wave') or 0),
            'selected_first_failed_wave': int(selected_summary.get('selected_first_failed_wave') or 0),
            'selected_max_independent_wave': int(selected_summary.get('selected_max_independent_wave') or 0),
            'selected_model': selected_summary.get('selected_model'),
            'selected_loadout_type': selected_summary.get('selected_loadout_type'),
            'selected_policy_preset': selected_summary.get('selected_policy_preset'),
            'last_contiguous_surviving_wave': int(selected_summary.get('last_contiguous_surviving_wave') or 0),
            'max_independent_surviving_wave': int(selected_summary.get('max_independent_surviving_wave') or 0),
            'first_failed_wave': int(selected_summary.get('first_failed_wave') or 0),
            'hit_by_hit_max_wave': int(selected_summary.get('hit_by_hit_max_wave') or 0),
            'hit_by_hit_first_failed_wave': int(selected_summary.get('hit_by_hit_first_failed_wave') or 0),
            'contact_envelope_max_wave': int(selected_summary.get('contact_envelope_max_wave') or 0),
            'contact_envelope_first_failed_wave': int(selected_summary.get('contact_envelope_first_failed_wave') or 0),
            'contact_envelope_max_independent_surviving_wave': int(selected_summary.get('contact_envelope_max_independent_surviving_wave') or 0),
            'contact_envelope_model': selected_summary.get('contact_envelope_model'),
            'pre_contact_boss_kill_max_wave': int(selected_summary.get('pre_contact_boss_kill_max_wave') or 0),
            'pre_contact_boss_kill_first_failed_wave': int(selected_summary.get('pre_contact_boss_kill_first_failed_wave') or 0),
            'pre_contact_boss_kill_max_independent_wave': int(selected_summary.get('pre_contact_boss_kill_max_independent_wave') or 0),
            'pre_contact_boss_kill_model': selected_summary.get('pre_contact_boss_kill_model'),
            'gc_pre_contact_max_wave': int(selected_summary.get('gc_pre_contact_max_wave') or 0),
            'gc_pre_contact_first_failed_wave': int(selected_summary.get('gc_pre_contact_first_failed_wave') or 0),
            'gc_pre_contact_max_independent_wave': int(selected_summary.get('gc_pre_contact_max_independent_wave') or 0),
            'gc_pre_contact_model': selected_summary.get('gc_pre_contact_model'),
            'terminal_pressure_limits': dict(selected_summary.get('terminal_pressure_limits') or {}),
            'terminal_pressure_limiter': selected_summary.get('terminal_pressure_limiter'),
            'terminal_pressure_limited': bool(selected_summary.get('terminal_pressure_limited')),
            'unsupported_pressure_reference_limit': dict(
                selected_summary.get('unsupported_pressure_reference_limit') or {}
            ),
            'unsupported_pressure_reference_limited': bool(
                selected_summary.get('unsupported_pressure_reference_limited')
            ),
            'unsupported_pressure_reference_aligned': bool(
                selected_summary.get('unsupported_pressure_reference_aligned')
            ),
            'unsupported_pressure_reference_alignment_direction': selected_summary.get(
                'unsupported_pressure_reference_alignment_direction'
            ),
            'unsupported_pressure_missing_reference_blocked': bool(
                selected_summary.get('unsupported_pressure_missing_reference_blocked')
            ),
            'pressure_factor_reference_hint': dict(
                selected_summary.get('pressure_factor_reference_hint') or {}
            ),
            'row_count': int(selected_summary.get('row_count') or len(operator_rows)),
            'terminal_display_wave': int(selected_summary.get('terminal_display_wave') or 0),
            'survives_through_end': bool(selected_summary.get('survives_through_end')),
            'contact_envelope_survives_through_end': bool(selected_summary.get('contact_envelope_survives_through_end')),
            'pre_contact_boss_kill_survives_through_end': bool(selected_summary.get('pre_contact_boss_kill_survives_through_end')),
            'gc_pre_contact_survives_through_end': bool(selected_summary.get('gc_pre_contact_survives_through_end')),
            'result_consistent_with_rows': bool(selected_summary.get('result_consistent_with_rows')),
            'status': selected_summary.get('status') or 'complete',
            'failure_kind': selected_summary.get('failure_kind'),
            'failure_message': selected_summary.get('failure_message'),
            'first_unresolved_wave': selected_summary.get('first_unresolved_wave'),
            'post_failure_truncation_kind': selected_summary.get('post_failure_truncation_kind'),
            'post_failure_truncation_message': selected_summary.get('post_failure_truncation_message'),
            'dissonance_run_category': dissonance_category,
            'dissonance_run_label': _BOSS_WAVE_DISSONANCE_RUN_LABELS[dissonance_category],
        },
        'diagnostics': selected_diagnostics,
        'download': {
            'format': 'csv',
            'file_name': f'{preset_name.lower()}_tier_{int(tier_number)}_boss_waves.csv',
            'row_source': csv_export_source,
        },
        'source_selection': _boss_wave_source_selection_payload(
            source_id,
            active_source=source_id,
            csv_export_source=csv_export_source,
            diagnostics_source=diagnostics_source,
        ),
    }
    if include_dissonance_run_matrix and dissonance_category == 'none':
        payload['dissonance_run_matrix'] = _build_boss_wave_dissonance_run_matrix(
            request,
            preset_name=preset_name,
            tier_number=int(tier_number),
            end_wave=int(end_wave),
            boss_wave_step=int(boss_wave_step),
            stop_on_failure=bool(stop_on_failure),
            scenario_runtime_inputs=dict(scenario_runtime_inputs),
            boss_wave_source=source_id,
            perk_policy_override=perk_policy_override,
        )
    return payload


def _build_boss_wave_dissonance_run_matrix(
    request: PipelineRunRequest,
    *,
    preset_name: str,
    tier_number: int,
    end_wave: int,
    boss_wave_step: int,
    stop_on_failure: bool,
    scenario_runtime_inputs: dict[str, float],
    boss_wave_source: str,
    perk_policy_override: dict[str, object] | None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for category in _BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES:
        payload = build_boss_wave_payload(
            request,
            preset_name=preset_name,
            tier_number=int(tier_number),
            end_wave=int(end_wave),
            boss_wave_step=int(boss_wave_step),
            stop_on_failure=bool(stop_on_failure),
            scenario_runtime_inputs=dict(scenario_runtime_inputs),
            boss_wave_source=boss_wave_source,
            perk_policy_override=perk_policy_override,
            dissonance_run_category=category,
            include_dissonance_run_matrix=False,
        )
        summary = dict(payload.get('summary') or {})
        diagnostics = dict(payload.get('diagnostics') or {})
        rows.append(
            {
                'dissonance_run_category': category,
                'label': _BOSS_WAVE_DISSONANCE_RUN_LABELS[category],
                'selected_max_wave': int(summary.get('selected_max_wave') or 0),
                'selected_first_failed_wave': int(summary.get('selected_first_failed_wave') or 0),
                'selected_model': summary.get('selected_model'),
                'hit_by_hit_max_wave': int(summary.get('hit_by_hit_max_wave') or 0),
                'contact_envelope_max_wave': int(summary.get('contact_envelope_max_wave') or 0),
                'pre_contact_boss_kill_max_wave': int(summary.get('pre_contact_boss_kill_max_wave') or 0),
                'gc_pre_contact_max_wave': int(summary.get('gc_pre_contact_max_wave') or 0),
                'status': summary.get('status') or diagnostics.get('context_status') or 'complete',
                'post_failure_truncation_kind': summary.get('post_failure_truncation_kind'),
                'terminal_pressure_limits': dict(summary.get('terminal_pressure_limits') or {}),
                'terminal_pressure_limiter': summary.get('terminal_pressure_limiter'),
                'terminal_pressure_limited': bool(summary.get('terminal_pressure_limited')),
                'unsupported_pressure_reference_limit': dict(
                    summary.get('unsupported_pressure_reference_limit') or {}
                ),
                'unsupported_pressure_reference_limited': bool(
                    summary.get('unsupported_pressure_reference_limited')
                ),
                'unsupported_pressure_reference_aligned': bool(
                    summary.get('unsupported_pressure_reference_aligned')
                ),
                'unsupported_pressure_reference_alignment_direction': summary.get(
                    'unsupported_pressure_reference_alignment_direction'
                ),
                'unsupported_pressure_missing_reference_blocked': bool(
                    summary.get('unsupported_pressure_missing_reference_blocked')
                ),
                'unsupported_pressure_uncapped_selected_max_wave': dict(
                    summary.get('unsupported_pressure_reference_limit') or {}
                ).get('uncapped_selected_max_wave'),
                'unsupported_terminal_pressures': list(diagnostics.get('unsupported_terminal_pressures') or []),
                'model_completion_blockers': list(
                    dict(diagnostics.get('model_certification') or {}).get('model_completion_blockers') or []
                ),
                'mask_summary': dict(diagnostics.get('dissonance_run_mask') or {}),
            }
        )
    return rows


def _boss_wave_milestone_matrix_cell(wave: int, loadout: str, *, capped: bool) -> str:
    suffix = '+' if capped and wave > 0 else ''
    return f'{int(wave)}{suffix} ({loadout})'


def _boss_wave_milestone_matrix_selection_rank(row: dict[str, object], policy_presets: tuple[str, ...]) -> tuple[int, int, int]:
    policy = str(row.get('loadout_policy_preset') or '')
    try:
        policy_rank = policy_presets.index(policy)
    except ValueError:
        policy_rank = len(policy_presets)
    return (
        1 if str(row.get('status') or '') == 'complete' else 0,
        int(row.get('selected_max_wave') or 0),
        -policy_rank,
    )


def _boss_wave_clean_reference_alignment(
    *,
    enabled: bool,
    selected_wave: int,
    matrix_end_wave: int | None,
    reference_wave: int | None,
    reference_kind: object,
    reference_source: object,
    model_completion_blockers: list[object],
    unsupported_terminal_pressures: list[object],
    terminal_pressure_limiter: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        'enabled': bool(enabled),
        'applied': False,
        'mode': 'comparison_only',
        'calculated_selected_max_wave': int(selected_wave),
        'aligned_selected_max_wave': int(selected_wave),
        'reference_wave': reference_wave,
        'reference_kind': reference_kind,
        'reference_source': reference_source,
        'calculated_delta_vs_reference_wave': None,
        'calculated_to_reference_ratio': None,
        'alignment_direction': None,
        'reason': 'alignment_not_requested' if not enabled else 'not_applicable',
    }
    if not enabled:
        return payload
    if reference_wave is None or int(reference_wave) <= 0:
        payload['reason'] = 'missing_reference_wave'
        return payload
    reference = int(reference_wave)
    if (
        str(reference_kind or '') == 'ids_dissonant_pb_wave'
        and reference >= _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE
    ):
        payload.update(
            {
                'reason': 'dissonance_pb_at_bonus_cap_not_exact_reference',
                'reference_interpretation': 'lower_bound_at_dissonance_bonus_cap',
                'dissonance_pb_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
            }
        )
        return payload
    payload['calculated_delta_vs_reference_wave'] = int(selected_wave) - reference
    payload['calculated_to_reference_ratio'] = int(selected_wave) / float(reference)
    if matrix_end_wave is not None and reference > int(matrix_end_wave):
        payload['reason'] = 'reference_exceeds_matrix_horizon'
        payload['matrix_end_wave'] = int(matrix_end_wave)
        return payload
    blockers = [str(blocker) for blocker in model_completion_blockers]
    unsupported = [str(pressure) for pressure in unsupported_terminal_pressures]
    if blockers or unsupported or terminal_pressure_limiter:
        payload['reason'] = 'row_not_clean'
        payload['model_completion_blockers'] = blockers
        payload['unsupported_terminal_pressures'] = unsupported
        payload['terminal_pressure_limiter'] = terminal_pressure_limiter
        return payload
    calculated = int(selected_wave)
    if calculated < reference:
        direction = 'raised_to_ids_reference'
    elif calculated > reference:
        direction = 'lowered_to_ids_reference'
    else:
        direction = 'already_at_ids_reference'
    payload.update(
        {
            'applied': True,
            'mode': 'clean_ids_reference_empirical_alignment',
            'aligned_selected_max_wave': reference,
            'alignment_direction': direction,
            'reason': 'clean_row_aligned_to_active_ids_reference',
        }
    )
    return payload


def _boss_wave_reference_nearest_lane(
    *,
    reference_wave: int | None,
    lane_waves: dict[str, object],
) -> dict[str, object]:
    reference = _extract_optional_wave_number(reference_wave)
    payload: dict[str, object] = {
        'reference_wave': reference,
        'nearest_lane': None,
        'nearest_lane_label': None,
        'nearest_lane_wave': None,
        'nearest_lane_delta_vs_reference_wave': None,
        'nearest_lane_abs_delta_wave': None,
    }
    if reference is None:
        return payload
    labels = {
        'hit_by_hit': 'Hit-by-hit',
        'contact_envelope': 'Contact envelope',
        'pre_contact_boss_kill': 'Pre-contact boss kill',
        'gc_pre_contact': 'GC pre-contact',
    }
    candidates: list[tuple[int, int, str, int]] = []
    for rank, (lane, raw_wave) in enumerate(lane_waves.items()):
        wave = _extract_optional_wave_number(raw_wave)
        if wave is None:
            continue
        candidates.append((abs(wave - reference), rank, lane, wave))
    if not candidates:
        return payload
    abs_delta, _, lane, wave = min(candidates)
    payload.update(
        {
            'nearest_lane': lane,
            'nearest_lane_label': labels.get(lane, lane),
            'nearest_lane_wave': wave,
            'nearest_lane_delta_vs_reference_wave': wave - reference,
            'nearest_lane_abs_delta_wave': abs_delta,
        }
    )
    return payload


def _boss_wave_reference_quality(
    *,
    reference_wave: object,
    reference_kind: object,
    reference_source: object,
) -> dict[str, object]:
    reference = _extract_optional_wave_number(reference_wave)
    reference_kind_text = str(reference_kind or '')
    dissonance_pb_cap_reached = bool(
        reference_kind_text == 'ids_dissonant_pb_wave'
        and reference is not None
        and reference >= _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE
    )
    caveats: list[str] = []
    if reference is not None and 0 < reference < _BOSS_WAVE_REFERENCE_VOLATILITY_THRESHOLD_WAVE:
        caveats.append('below_3000_wave_perk_volatility')
    if reference_kind_text == 'ids_dissonant_pb_wave':
        caveats.append('pb_age_unknown_no_source_timestamp')
    if dissonance_pb_cap_reached:
        caveats.append('dissonance_pb_5000_bonus_cap_floor')
    exact_reference = bool(reference is not None and reference > 0 and not dissonance_pb_cap_reached)
    return {
        'reference_wave': reference,
        'reference_kind': reference_kind,
        'reference_source': reference_source,
        'low_wave_threshold': _BOSS_WAVE_REFERENCE_VOLATILITY_THRESHOLD_WAVE,
        'below_low_wave_threshold': bool(
            reference is not None
            and 0 < reference < _BOSS_WAVE_REFERENCE_VOLATILITY_THRESHOLD_WAVE
        ),
        'pb_age_status': (
            'age_unknown_no_source_timestamp'
            if reference_kind_text == 'ids_dissonant_pb_wave'
            else 'not_pb_reference'
        ),
        'dissonance_pb_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
        'dissonance_pb_bonus_cap_reached': dissonance_pb_cap_reached,
        'reference_interpretation': (
            'lower_bound_at_dissonance_bonus_cap'
            if dissonance_pb_cap_reached
            else 'exact_wave_reference'
        ),
        'exact_reference': exact_reference,
        'calibration_candidate': bool(
            reference is not None
            and reference >= _BOSS_WAVE_REFERENCE_VOLATILITY_THRESHOLD_WAVE
            and exact_reference
        ),
        'caveats': caveats,
    }


def _boss_wave_pressure_factor_reference_hint(
    *,
    calculated_wave: object,
    reference_wave: object,
    reference_kind: object,
    reference_source: object,
    calculated_delta_vs_reference_wave: object,
    calculated_to_reference_ratio: object,
) -> dict[str, object]:
    reference = _extract_optional_wave_number(reference_wave)
    calculated = _extract_optional_wave_number(calculated_wave)
    if reference is None or reference <= 0:
        return {
            'enabled': False,
            'mode': 'no_positive_reference_wave',
            'boss_wave_pressure_factor': None,
            'direction': None,
        }
    if (
        str(reference_kind or '') == 'ids_dissonant_pb_wave'
        and reference >= _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE
    ):
        return {
            'enabled': False,
            'mode': 'dissonance_pb_bonus_cap_not_exact_reference',
            'boss_wave_pressure_factor': None,
            'direction': None,
            'calculated_selected_max_wave': calculated,
            'reference_wave': reference,
            'reference_kind': reference_kind,
            'reference_source': reference_source,
            'reference_interpretation': 'lower_bound_at_dissonance_bonus_cap',
            'exact_reference': False,
            'dissonance_pb_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
            'caveats': ['dissonance_pb_5000_bonus_cap_floor'],
        }
    if calculated is None or calculated <= 0:
        return {
            'enabled': False,
            'mode': 'no_positive_calculated_wave',
            'boss_wave_pressure_factor': None,
            'direction': None,
            'reference_wave': reference,
            'reference_kind': reference_kind,
            'reference_source': reference_source,
        }
    try:
        ratio = float(calculated_to_reference_ratio)
    except (TypeError, ValueError):
        ratio = calculated / float(reference)
    delta = (
        int(calculated_delta_vs_reference_wave)
        if calculated_delta_vs_reference_wave is not None
        else calculated - reference
    )
    if delta > 0:
        direction = 'increase_pressure'
    elif delta < 0:
        direction = 'decrease_pressure'
    else:
        direction = 'no_adjustment'
    return {
        'enabled': True,
        'mode': 'raw_calculated_wave_to_reference_ratio_hint',
        'application': 'explicit_comparison_input_only',
        'certification_effect': 'none_not_applied',
        'boss_wave_pressure_factor': ratio,
        'rounded_boss_wave_pressure_factor': round(ratio, 3),
        'direction': direction,
        'calculated_selected_max_wave': calculated,
        'reference_wave': reference,
        'reference_kind': reference_kind,
        'reference_source': reference_source,
        'calculated_delta_vs_reference_wave': delta,
        'calculated_to_reference_ratio': ratio,
        'comparison_scenario_runtime_inputs': {'boss_wave_pressure_factor': ratio},
    }


def _median_numeric(values: Iterable[object]) -> float | None:
    numbers: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            numbers.append(number)
    if not numbers:
        return None
    ordered = sorted(numbers)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _boss_wave_pressure_factor_distribution(hints: Iterable[Mapping[str, object]]) -> dict[str, object]:
    factors: list[float] = []
    for hint in hints:
        try:
            factor = float(hint.get('boss_wave_pressure_factor'))
        except (TypeError, ValueError):
            continue
        if factor > 0.0 and math.isfinite(factor):
            factors.append(factor)
    if not factors:
        return {
            'count': 0,
            'min_factor': None,
            'median_factor': None,
            'mean_factor': None,
            'max_factor': None,
            'rounded_median_factor': None,
            'rounded_mean_factor': None,
            'comparison_scenario_runtime_inputs': {},
        }
    ordered = sorted(factors)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        median_factor = ordered[mid]
    else:
        median_factor = (ordered[mid - 1] + ordered[mid]) / 2.0
    mean_factor = sum(ordered) / float(len(ordered))
    explicit_input = (
        {}
        if math.isclose(median_factor, 1.0)
        else {'boss_wave_pressure_factor': median_factor}
    )
    return {
        'count': len(ordered),
        'min_factor': ordered[0],
        'median_factor': median_factor,
        'mean_factor': mean_factor,
        'max_factor': ordered[-1],
        'rounded_median_factor': round(median_factor, 3),
        'rounded_mean_factor': round(mean_factor, 3),
        'comparison_scenario_runtime_inputs': explicit_input,
        'explicit_comparison_input_available': bool(explicit_input),
        'application': 'explicit_comparison_input_only',
        'certification_effect': 'none_not_applied',
        'mode': 'median_calibration_quality_pressure_factor_hint',
    }


def _boss_wave_pressure_factor_evidence_quality(
    *,
    hinted_count: int,
    calibration_quality_hint_count: int,
    disabled_hint_mode_counts: Mapping[str, object],
) -> str:
    if calibration_quality_hint_count > 0:
        return 'clean_calibration_available'
    if hinted_count > 0:
        return 'caveated_reference_hints_only'
    if disabled_hint_mode_counts:
        return 'disabled_by_reference_quality'
    return 'no_reference_hints'


def _ensure_boss_wave_selected_pressure_factor_reference_hint(
    summary: dict[str, object],
    *,
    account_state,
    tier_number: int,
    dissonance_run_category: str,
    unsupported_terminal_pressures: Iterable[str],
    runtime_inputs: ScenarioRuntimeInputs,
) -> dict[str, object]:
    existing = dict(summary.get('pressure_factor_reference_hint') or {})
    if bool(existing.get('enabled')) or existing.get('mode') not in {None, 'not_applicable'}:
        return existing
    pressures = [str(item) for item in (unsupported_terminal_pressures or ()) if str(item)]
    if pressures or _boss_wave_explicit_pressure_factor(runtime_inputs) is not None:
        return existing
    alignment = _boss_wave_milestone_alignment(
        account_state=account_state,
        tier_number=int(tier_number),
        dissonance_run_category=dissonance_run_category,
        summary=summary,
    )
    reference_wave = _extract_optional_wave_number(alignment.get('active_reference_wave'))
    calculated_wave = _extract_optional_wave_number(alignment.get('calculated_selected_max_wave'))
    calculated_delta_vs_reference_wave = alignment.get('delta_waves')
    calculated_to_reference_ratio = alignment.get('calculated_to_reference_ratio')
    hint = _boss_wave_pressure_factor_reference_hint(
        calculated_wave=calculated_wave,
        reference_wave=reference_wave,
        reference_kind=alignment.get('active_reference_kind'),
        reference_source=alignment.get('active_reference_source'),
        calculated_delta_vs_reference_wave=calculated_delta_vs_reference_wave,
        calculated_to_reference_ratio=calculated_to_reference_ratio,
    )
    summary['pressure_factor_reference_hint'] = hint
    return hint


def _boss_wave_pressure_factor_hint_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    hints: list[dict[str, object]] = []
    calibration_quality_hints: list[dict[str, object]] = []
    disabled_hint_mode_counts: Counter[str] = Counter()
    excluded_caveated_hint_reason_counts: Counter[str] = Counter()
    by_run_type: dict[str, dict[str, object]] = {}
    hints_by_run_type: dict[str, list[dict[str, object]]] = {}
    calibration_quality_hints_by_run_type: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        category = str(row.get('dissonance_run_category') or '')
        label = str(row.get('label') or category or '')
        group_key = f'{category}\0{label}'
        group = by_run_type.setdefault(
            group_key,
            {
                'dissonance_run_category': category,
                'label': label,
                'row_count': 0,
                'rows_with_pressure_factor_hint': 0,
                'direction_counts': {},
                'max_factor_distance_from_one': 0.0,
                'max_factor_distance_row': {},
                'calibration_quality_hint_count': 0,
                'calibration_quality_direction_counts': {},
                'calibration_quality_max_factor_distance_from_one': 0.0,
                'calibration_quality_max_factor_distance_row': {},
                'excluded_caveated_hint_count': 0,
                'excluded_caveated_hint_reason_counts': {},
                'disabled_hint_mode_counts': {},
            },
        )
        group['row_count'] = int(group.get('row_count') or 0) + 1
        hint = dict(row.get('pressure_factor_reference_hint') or {})
        if not bool(hint.get('enabled')):
            mode = str(hint.get('mode') or '')
            if mode and mode != 'not_applicable':
                disabled_hint_mode_counts[mode] += 1
                group_disabled_modes = dict(group.get('disabled_hint_mode_counts') or {})
                group_disabled_modes[mode] = int(group_disabled_modes.get(mode) or 0) + 1
                group['disabled_hint_mode_counts'] = dict(sorted(group_disabled_modes.items()))
            continue
        hint.update(
            {
                'tier': row.get('tier'),
                'tier_column': row.get('tier_column'),
                'dissonance_run_category': row.get('dissonance_run_category'),
                'label': row.get('label'),
                'selected_max_wave': row.get('best_selected_max_wave'),
                'selected_display': row.get('best_display'),
                'calculated_selected_max_wave': row.get('best_calculated_selected_max_wave'),
                'loadout_policy_preset': row.get('best_loadout_policy_preset'),
            }
        )
        hints.append(hint)
        hints_by_run_type.setdefault(group_key, []).append(hint)
        group['rows_with_pressure_factor_hint'] = int(group.get('rows_with_pressure_factor_hint') or 0) + 1
        group_direction_counts = dict(group.get('direction_counts') or {})
        direction = str(hint.get('direction') or '')
        if direction:
            group_direction_counts[direction] = group_direction_counts.get(direction, 0) + 1
        group['direction_counts'] = dict(sorted(group_direction_counts.items()))
        factor_distance = abs(float(hint.get('boss_wave_pressure_factor') or 1.0) - 1.0)
        if factor_distance >= float(group.get('max_factor_distance_from_one') or 0.0):
            group['max_factor_distance_from_one'] = factor_distance
            group['max_factor_distance_row'] = dict(hint)
        reference_quality = dict(row.get('reference_quality') or {})
        is_calibration_quality = bool(reference_quality.get('calibration_candidate')) and not list(
            reference_quality.get('caveats') or []
        )
        if is_calibration_quality:
            calibration_quality_hints.append(hint)
            calibration_quality_hints_by_run_type.setdefault(group_key, []).append(hint)
            group['calibration_quality_hint_count'] = int(
                group.get('calibration_quality_hint_count') or 0
            ) + 1
            group_calibration_direction_counts = dict(
                group.get('calibration_quality_direction_counts') or {}
            )
            if direction:
                group_calibration_direction_counts[direction] = (
                    group_calibration_direction_counts.get(direction, 0) + 1
                )
            group['calibration_quality_direction_counts'] = dict(
                sorted(group_calibration_direction_counts.items())
            )
            if factor_distance >= float(
                group.get('calibration_quality_max_factor_distance_from_one') or 0.0
            ):
                group['calibration_quality_max_factor_distance_from_one'] = factor_distance
                group['calibration_quality_max_factor_distance_row'] = dict(hint)
        else:
            caveats = [str(caveat) for caveat in list(reference_quality.get('caveats') or []) if str(caveat)]
            if caveats:
                group['excluded_caveated_hint_count'] = int(
                    group.get('excluded_caveated_hint_count') or 0
                ) + 1
                group_caveat_counts = dict(group.get('excluded_caveated_hint_reason_counts') or {})
                for caveat in caveats:
                    excluded_caveated_hint_reason_counts[caveat] += 1
                    group_caveat_counts[caveat] = int(group_caveat_counts.get(caveat) or 0) + 1
                group['excluded_caveated_hint_reason_counts'] = dict(
                    sorted(group_caveat_counts.items())
                )
    direction_counts: dict[str, int] = {}
    for hint in hints:
        direction = str(hint.get('direction') or '')
        if direction:
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
    calibration_quality_direction_counts: dict[str, int] = {}
    for hint in calibration_quality_hints:
        direction = str(hint.get('direction') or '')
        if direction:
            calibration_quality_direction_counts[direction] = (
                calibration_quality_direction_counts.get(direction, 0) + 1
            )
    worst_hint = max(
        hints,
        key=lambda hint: abs(float(hint.get('boss_wave_pressure_factor') or 1.0) - 1.0),
        default=None,
    )
    worst_calibration_quality_hint = max(
        calibration_quality_hints,
        key=lambda hint: abs(float(hint.get('boss_wave_pressure_factor') or 1.0) - 1.0),
        default=None,
    )
    for group_key, group in by_run_type.items():
        hinted_count = int(group.get('rows_with_pressure_factor_hint') or 0)
        calibration_quality_hint_count = int(group.get('calibration_quality_hint_count') or 0)
        disabled_modes = dict(group.get('disabled_hint_mode_counts') or {})
        group['pressure_factor_evidence_quality'] = _boss_wave_pressure_factor_evidence_quality(
            hinted_count=hinted_count,
            calibration_quality_hint_count=calibration_quality_hint_count,
            disabled_hint_mode_counts=disabled_modes,
        )
        pressure_factor_distribution = _boss_wave_pressure_factor_distribution(
            hints_by_run_type.get(group_key, ())
        )
        group['pressure_factor_distribution'] = pressure_factor_distribution
        group['explicit_comparison_input_hint'] = dict(
            pressure_factor_distribution.get('comparison_scenario_runtime_inputs') or {}
        )
        group['calibration_quality_factor_distribution'] = _boss_wave_pressure_factor_distribution(
            calibration_quality_hints_by_run_type.get(group_key, ())
        )
    return {
        'row_count': len(rows),
        'rows_with_pressure_factor_hint': len(hints),
        'direction_counts': dict(sorted(direction_counts.items())),
        'max_factor_distance_from_one': (
            abs(float(worst_hint.get('boss_wave_pressure_factor') or 1.0) - 1.0)
            if worst_hint is not None
            else 0.0
        ),
        'max_factor_distance_row': dict(worst_hint) if worst_hint is not None else {},
        'disabled_hint_mode_counts': dict(sorted(disabled_hint_mode_counts.items())),
        'by_run_type': list(by_run_type.values()),
        'mode': 'explicit_comparison_input_hint_only',
        'calibration_quality': {
            'definition': 'calibration_candidate_with_no_reference_caveats',
            'rows_with_pressure_factor_hint': len(calibration_quality_hints),
            'excluded_caveated_hint_count': len(hints) - len(calibration_quality_hints),
            'excluded_caveated_hint_reason_counts': dict(
                sorted(excluded_caveated_hint_reason_counts.items())
            ),
            'direction_counts': dict(sorted(calibration_quality_direction_counts.items())),
            'factor_distribution': _boss_wave_pressure_factor_distribution(
                calibration_quality_hints
            ),
            'max_factor_distance_from_one': (
                abs(float(worst_calibration_quality_hint.get('boss_wave_pressure_factor') or 1.0) - 1.0)
                if worst_calibration_quality_hint is not None
                else 0.0
            ),
            'max_factor_distance_row': (
                dict(worst_calibration_quality_hint)
                if worst_calibration_quality_hint is not None
                else {}
            ),
        },
    }


def _boss_wave_pressure_factor_accuracy_by_run_type(
    pressure_factor_hint_summary: Mapping[str, object],
) -> list[dict[str, object]]:
    category_order = {category: index for index, category in enumerate(_BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES)}
    rows: list[dict[str, object]] = []
    for item in list(pressure_factor_hint_summary.get('by_run_type') or []):
        run_type = dict(item or {})
        distribution = dict(run_type.get('pressure_factor_distribution') or {})
        calibration_distribution = dict(run_type.get('calibration_quality_factor_distribution') or {})
        comparison_inputs = dict(
            distribution.get('comparison_scenario_runtime_inputs')
            or run_type.get('explicit_comparison_input_hint')
            or {}
        )
        rows.append(
            {
                'dissonance_run_category': run_type.get('dissonance_run_category'),
                'label': run_type.get('label'),
                'row_count': int(run_type.get('row_count') or 0),
                'rows_with_pressure_factor_hint': int(
                    run_type.get('rows_with_pressure_factor_hint') or 0
                ),
                'calibration_quality_hint_count': int(
                    run_type.get('calibration_quality_hint_count') or 0
                ),
                'pressure_factor_evidence_quality': (
                    run_type.get('pressure_factor_evidence_quality') or 'unknown'
                ),
                'pressure_factor_median': distribution.get('median_factor'),
                'pressure_factor_rounded_median': distribution.get('rounded_median_factor'),
                'pressure_factor_min': distribution.get('min_factor'),
                'pressure_factor_max': distribution.get('max_factor'),
                'explicit_comparison_input_hint': comparison_inputs,
                'explicit_comparison_scope': {
                    'dissonance_run_category': run_type.get('dissonance_run_category'),
                    'label': run_type.get('label'),
                    'application': 'manual_or_comparison_only',
                    'certification_effect': 'none_not_applied',
                },
                'calibration_quality_pressure_factor_median': calibration_distribution.get(
                    'median_factor'
                ),
                'calibration_quality_pressure_factor_rounded_median': calibration_distribution.get(
                    'rounded_median_factor'
                ),
                'excluded_caveated_hint_count': int(
                    run_type.get('excluded_caveated_hint_count') or 0
                ),
                'excluded_caveated_hint_reason_counts': dict(
                    run_type.get('excluded_caveated_hint_reason_counts') or {}
                ),
                'disabled_hint_mode_counts': dict(run_type.get('disabled_hint_mode_counts') or {}),
            }
        )
    return sorted(
        rows,
        key=lambda row: category_order.get(str(row.get('dissonance_run_category') or ''), 99),
    )


def _boss_wave_dissonance_pressure_factor_evidence(
    pressure_factor_by_run_type: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    rows = [
        dict(row)
        for row in pressure_factor_by_run_type
        if str(row.get('dissonance_run_category') or 'none') != 'none'
    ]
    hinted_count = sum(int(row.get('rows_with_pressure_factor_hint') or 0) for row in rows)
    calibration_quality_hint_count = sum(
        int(row.get('calibration_quality_hint_count') or 0) for row in rows
    )
    excluded_caveated_hint_count = sum(
        int(row.get('excluded_caveated_hint_count') or 0) for row in rows
    )
    caveat_counts: Counter[str] = Counter()
    disabled_counts: Counter[str] = Counter()
    explicit_review_inputs: list[dict[str, object]] = []
    categories_with_hints: list[str] = []
    categories_with_explicit_review_inputs: list[str] = []
    categories_with_clean_calibration: list[str] = []
    categories_without_clean_calibration: list[str] = []
    for row in rows:
        label = str(row.get('label') or row.get('dissonance_run_category') or '')
        if int(row.get('rows_with_pressure_factor_hint') or 0) > 0:
            categories_with_hints.append(label)
            explicit_input_hint = dict(row.get('explicit_comparison_input_hint') or {})
            if explicit_input_hint:
                categories_with_explicit_review_inputs.append(label)
                explicit_review_inputs.append(
                    {
                        'dissonance_run_category': row.get('dissonance_run_category'),
                        'label': row.get('label'),
                        'boss_wave_pressure_factor': row.get('pressure_factor_median'),
                        'rounded_boss_wave_pressure_factor': row.get('pressure_factor_rounded_median'),
                        'evidence_quality': row.get('pressure_factor_evidence_quality'),
                        'calibration_quality_hint_count': int(
                            row.get('calibration_quality_hint_count') or 0
                        ),
                        'excluded_caveated_hint_count': int(
                            row.get('excluded_caveated_hint_count') or 0
                        ),
                        'excluded_caveated_hint_reason_counts': dict(
                            row.get('excluded_caveated_hint_reason_counts') or {}
                        ),
                        'explicit_comparison_input_hint': explicit_input_hint,
                        'comparison_review_request': {
                            'mode': 'comparison_only',
                            'dissonance_run_category': row.get('dissonance_run_category'),
                            'include_boss_wave_milestone_matrix': True,
                            'comparison_scenario_runtime_inputs': explicit_input_hint,
                            'default_account_truth_unchanged': True,
                            'certification_effect': 'none_not_applied',
                        },
                        'application': 'manual_or_comparison_only',
                        'certification_effect': 'none_not_applied',
                    }
                )
        if int(row.get('calibration_quality_hint_count') or 0) > 0:
            categories_with_clean_calibration.append(label)
        else:
            categories_without_clean_calibration.append(label)
        caveat_counts.update({
            str(reason): int(count or 0)
            for reason, count in dict(row.get('excluded_caveated_hint_reason_counts') or {}).items()
        })
        disabled_counts.update({
            str(mode): int(count or 0)
            for mode, count in dict(row.get('disabled_hint_mode_counts') or {}).items()
        })
    if calibration_quality_hint_count > 0:
        status = 'clean_dissonance_calibration_available'
    elif hinted_count > 0:
        status = 'caveated_dissonance_hints_only'
    elif disabled_counts:
        status = 'dissonance_hints_disabled_by_reference_quality'
    else:
        status = 'no_dissonance_pressure_factor_hints'
    return {
        'status': status,
        'run_type_count': len(rows),
        'rows_with_pressure_factor_hint': hinted_count,
        'calibration_quality_hint_count': calibration_quality_hint_count,
        'excluded_caveated_hint_count': excluded_caveated_hint_count,
        'excluded_caveated_hint_reason_counts': dict(sorted(caveat_counts.items())),
        'disabled_hint_mode_counts': dict(sorted(disabled_counts.items())),
        'categories_with_pressure_factor_hints': categories_with_hints,
        'categories_with_explicit_review_inputs': categories_with_explicit_review_inputs,
        'categories_with_clean_calibration': categories_with_clean_calibration,
        'categories_without_clean_calibration': categories_without_clean_calibration,
        'explicit_review_inputs_by_run_type': explicit_review_inputs,
        'explicit_review_request_count': len(explicit_review_inputs),
        'application': 'explicit_manual_or_comparison_input_only',
        'certification_effect': 'none_not_applied',
    }


def _boss_wave_non_boss_pressure_driver_model_summary(
    *,
    certification: Mapping[str, object],
    model_blocker_summary: Mapping[str, object],
    pressure_factor_hint_summary: Mapping[str, object],
    reference_quality_summary: Mapping[str, object],
    pressure_driver_samples: Mapping[str, object] | None = None,
    pressure_driver_candidate_samples: Mapping[str, object] | None = None,
    approve_empirical_pressure_transform_default: bool = False,
) -> dict[str, object]:
    from simulators.scenario import non_boss_pressure_driver_source_summary

    blockers = [str(blocker) for blocker in list(certification.get('model_completion_blockers') or [])]
    closure = dict(certification.get('non_boss_terminal_pressure_closure') or {})
    source_summary = non_boss_pressure_driver_source_summary()
    selected_pressure_samples = dict(pressure_driver_samples or {})
    pressure_blocker_active = 'source_owned_non_boss_terminal_pressure_formulas' in blockers
    if pressure_blocker_active:
        status = 'source_driver_curves_partially_available_terminal_transform_missing'
    elif bool(closure.get('pressure_factor_approximation_closed')):
        status = 'explicit_pressure_factor_override_active_driver_curves_partial'
    elif bool(closure.get('exact_terminal_override_closed')):
        status = 'explicit_terminal_wave_inputs_active_driver_curves_partial'
    else:
        status = 'not_required_for_selected_rows'
    missing_formula_links = list(source_summary.get('missing_terminal_formula_links') or [])
    by_run_type = [
        dict(item)
        for item in list(pressure_factor_hint_summary.get('by_run_type') or [])
    ]
    regular_pressure_factor = next(
        (
            dict(item.get('pressure_factor_distribution') or {})
            for item in by_run_type
            if str(item.get('dissonance_run_category') or 'none') == 'none'
        ),
        {},
    )
    regular_clean_pressure_factor = next(
        (
            dict(item.get('calibration_quality_factor_distribution') or {})
            for item in by_run_type
            if str(item.get('dissonance_run_category') or 'none') == 'none'
        ),
        {},
    )
    source_backed_curve_coverage = dict(source_summary.get('source_backed_curve_coverage') or {})
    source_owned_driver_inputs = [
        {
            'driver': 'enemy_spawn_rate',
            'surface_ids': [
                'kb::normal_spawn_rate_wave_thresholds',
                'context::bc.more_enemies_pct',
            ],
            'kb_sources': [
                'enemies.table.wiki_advanced_analysis_spawn_rate_wave_thresholds',
                'card_base_ladders::Enemy Balance',
                'tournament_battle_condition_magnitudes::more_enemies',
            ],
            'boss_wave_consumption_status': 'source_curve_available_terminal_weight_missing',
        },
        {
            'driver': 'wave_accelerator_mastery_spawn_rate_acceleration',
            'surface_ids': ['state::cards.wave_accelerator.spawn_rate_acceleration'],
            'kb_sources': ['card_masteries::Wave Accelerator'],
            'boss_wave_consumption_status': 'source_curve_modifier_available_terminal_weight_missing',
        },
        {
            'driver': 'elite_spawn_pressure',
            'surface_ids': ['state::cards.enemy_balance.mastery_effect'],
            'kb_sources': [
                'card_masteries::Enemy Balance',
                'enemies.table.wiki_verified_elite_spawn_thresholds',
            ],
            'boss_wave_consumption_status': 'source_curve_available_terminal_weight_missing',
        },
        {
            'driver': 'fleet_spawn_pressure',
            'surface_ids': ['kb::fleet_spawn_rules_by_tier_and_wave'],
            'kb_sources': [
                'enemies.table.wiki_verified_fleet_spawn_thresholds',
                'enemies.source.wiki_fleet_and_special_interactions',
            ],
            'boss_wave_consumption_status': 'source_curve_available_terminal_weight_missing',
        },
        {
            'driver': 'tier_and_wave_pressure',
            'surface_ids': ['scenario::tier_number', 'operator_row::display_wave'],
            'kb_sources': [
                'enemy_notes::wave_progression_system',
                'tournament_rules::tier_battle_conditions',
            ],
            'boss_wave_consumption_status': 'identified_formula_not_consumed',
        },
    ]
    terminal_pressure_transform_readiness = {
        'status': (
            'source_driver_curves_available_terminal_transform_missing'
            if pressure_blocker_active
            else 'terminal_pressure_transform_not_required_or_closed_by_explicit_input'
        ),
        'owner': 'app.pipeline.summary_from_simulators.scenario_source_evidence',
        'application': 'diagnostic_only_not_default_formula',
        'certification_effect': 'none',
        'default_boss_wave_truth_changed': False,
        'source_curve_coverage': source_backed_curve_coverage,
        'source_owned_driver_input_count': len(source_owned_driver_inputs),
        'source_owned_driver_inputs': source_owned_driver_inputs,
        'missing_source_owned_formula_links': missing_formula_links,
        'remaining_to_certify': [
            'normal_spawn_rate_value_to_terminal_pressure',
            'elite_spawn_pressure_weight_to_terminal_pressure',
            'fleet_spawn_pressure_weight_to_terminal_pressure',
            'normal_elite_fleet_pressure_composition_rule',
            'pressure_to_terminal_max_wave_or_boss_pressure_factor_transform',
            'validation_across_regular_and_non_capped_dissonance_references',
        ],
    }
    return {
        'status': status,
        'default_pressure_factor_derived': False,
        'pressure_factor_policy': 'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved',
        'required_formula_owner': 'simulators_with_kb_formula_inputs',
        'driver_emphasis': 'spawn_rate_elite_fleet_tier_wave',
        'simulator_source_summary': source_summary,
        'source_backed_curve_coverage': source_backed_curve_coverage,
        'terminal_pressure_transform_readiness': terminal_pressure_transform_readiness,
        'monotonic_pressure_drivers': [
            'enemy_spawn_rate',
            'wave_accelerator_mastery_spawn_rate_acceleration',
            'elite_spawn_rate',
            'fleet_spawn_rate',
            'fleet_related_enemy_group_load',
            'tier',
            'wave',
        ],
        'source_owned_driver_inputs': source_owned_driver_inputs,
        'missing_source_owned_formula_links': missing_formula_links,
        'empirical_calibration_policy': {
            'basis': 'regular_exact_reference_rows',
            'default_application': 'not_applied_to_account_truth',
            'clean_regular_distribution': regular_clean_pressure_factor,
            'regular_sensitivity_distribution_including_caveated_low_wave_rows': regular_pressure_factor,
            'dissonance_pb_5000_cap_policy': 'excluded_from_calibration_lower_bound_only',
            'below_3000_wave_policy': 'reported_as_caveated_sensitivity_not_clean_calibration',
            'below_3000_wave_reference_count': int(
                reference_quality_summary.get('low_wave_reference_count') or 0
            ),
            'dissonance_pb_5000_cap_count': int(
                reference_quality_summary.get('dissonance_pb_bonus_cap_count') or 0
            ),
        },
        'rows_with_unsupported_terminal_pressures': int(
            model_blocker_summary.get('rows_with_unsupported_terminal_pressures') or 0
        ),
        'unsupported_terminal_pressure_counts': dict(
            model_blocker_summary.get('unsupported_terminal_pressure_counts') or {}
        ),
        'pressure_driver_samples': selected_pressure_samples,
        'pressure_driver_candidate_samples': dict(pressure_driver_candidate_samples or {}),
        'pressure_driver_empirical_calibration': _boss_wave_pressure_driver_empirical_calibration(
            selected_pressure_samples,
            approve_empirical_transform_default=approve_empirical_pressure_transform_default,
        ),
        'operator_decisions_needed': [
            'confirm_spawn_rate_to_terminal_pressure_weight_or_empirical_proxy',
            'confirm_elite_and_fleet_pressure_weights',
            'confirm_pressure_driver_composition_rule',
            'confirm_when_empirical_regular_calibration_may_become_default',
        ],
    }


def _float_from_mapping(
    mapping: Mapping[str, object],
    key: str,
    *,
    default: float,
) -> float:
    try:
        value = mapping.get(key)
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _boss_wave_pressure_driver_probe_from_primitives(
    *,
    tier: int,
    wave: int,
    primitive_values: Mapping[str, object],
) -> dict[str, object]:
    from simulators.scenario import non_boss_pressure_driver_probe

    wave_number = max(0, int(wave or 0))
    if wave_number <= 0:
        return {
            'status': 'not_available_no_positive_wave',
            'default_pressure_factor_derived': False,
        }
    bc_more_enemies_pct = _float_from_mapping(
        primitive_values,
        'bc_more_enemies_pct',
        default=0.0,
    )
    probe = non_boss_pressure_driver_probe(
        tier=int(tier),
        wave=wave_number,
        scenario_surfaces={'bc_more_enemies_pct': bc_more_enemies_pct},
        enemy_balance_spawn_multiplier=1.0,
        wave_accelerator_spawn_rate_acceleration=_float_from_mapping(
            primitive_values,
            'wave_accelerator_spawn_rate_acceleration',
            default=1.0,
        ),
        enemy_balance_mastery_double_elite_chance_pct=_float_from_mapping(
            primitive_values,
            'enemy_balance_mastery_double_elite_chance_pct',
            default=0.0,
        ),
    )
    probe['application'] = 'diagnostic_only_not_terminal_formula'
    probe['default_pressure_factor_derived'] = False
    probe['pressure_factor_policy'] = (
        'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved'
    )
    return probe


def _boss_wave_pressure_driver_sample_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    samples: list[dict[str, object]] = []
    for row in rows:
        probe = dict(row.get('non_boss_pressure_driver_probe') or {})
        if not probe or str(probe.get('status') or '').startswith('not_available'):
            continue
        normal = dict(probe.get('normal_spawn_rate_pressure') or {})
        elite = dict(probe.get('elite_spawn_pressure') or {})
        fleet = dict(probe.get('fleet_spawn_pressure') or {})
        samples.append(
            {
                'tier': int(row.get('tier') or 0),
                'dissonance_run_category': str(row.get('dissonance_run_category') or 'none'),
                'label': row.get('label'),
                'reference_quality': dict(row.get('reference_quality') or {}),
                'loadout_policy_preset': row.get('loadout_policy_preset'),
                'loadout_profile_preset': row.get('loadout_profile_preset'),
                'selected_loadout_type': row.get('selected_loadout_type'),
                'wave': int(probe.get('wave') or 0),
                'calculated_selected_max_wave': int(row.get('best_calculated_selected_max_wave') or 0),
                'reference_wave': row.get('reference_wave'),
                'pressure_factor_hint': dict(row.get('pressure_factor_reference_hint') or {}),
                'displayed_spawn_rate': normal.get('displayed_spawn_rate'),
                'normal_spawn_rate_pressure_index': normal.get('normal_spawn_rate_pressure_index'),
                'wave_accelerator_spawn_rate_acceleration': probe.get(
                    'wave_accelerator_spawn_rate_acceleration'
                ),
                'bc_more_enemies_pct': probe.get('bc_more_enemies_pct'),
                'elite_pressure_index_pct': elite.get('elite_pressure_index_pct'),
                'enemy_balance_mastery_double_elite_chance_pct': elite.get(
                    'enemy_balance_mastery_double_elite_chance_pct'
                ),
                'fleet_events_per_wave_pressure': fleet.get('fleet_events_per_wave_pressure'),
                'fleet_related_enemy_group_expected_enemies_per_wave_pressure': fleet.get(
                    'fleet_related_enemy_group_expected_enemies_per_wave_pressure'
                ),
            }
        )
    if not samples:
        return {
            'status': 'not_available',
            'application': 'diagnostic_only_not_terminal_formula',
            'sample_count': 0,
            'default_pressure_factor_derived': False,
        }

    by_run_type: dict[str, dict[str, object]] = {}
    for sample in samples:
        key = str(sample.get('dissonance_run_category') or 'none')
        current = by_run_type.setdefault(
            key,
            {
                'dissonance_run_category': key,
                'label': sample.get('label'),
                'sample_count': 0,
                'max_wave': 0,
                'max_normal_spawn_rate_pressure_index': None,
                'max_elite_pressure_index_pct': None,
                'max_fleet_events_per_wave_pressure': None,
                'max_fleet_related_enemy_group_expected_enemies_per_wave_pressure': None,
            },
        )
        current['sample_count'] = int(current.get('sample_count') or 0) + 1
        current['max_wave'] = max(int(current.get('max_wave') or 0), int(sample.get('wave') or 0))
        for target_key in (
            'max_normal_spawn_rate_pressure_index',
                'max_elite_pressure_index_pct',
                'max_fleet_events_per_wave_pressure',
                'max_fleet_related_enemy_group_expected_enemies_per_wave_pressure',
            ):
            sample_key = target_key.removeprefix('max_')
            sample_value = sample.get(sample_key)
            if sample_value is None:
                continue
            current_value = current.get(target_key)
            current[target_key] = (
                float(sample_value)
                if current_value is None
                else max(float(current_value), float(sample_value))
            )

    return {
        'status': 'available_terminal_transform_missing',
        'application': 'diagnostic_only_not_terminal_formula',
        'sample_count': len(samples),
        'default_pressure_factor_derived': False,
        'sample_basis': 'selected_matrix_rows_at_raw_calculated_selected_max_wave',
        'source_owner': 'simulators.scenario.non_boss_pressure_driver_probe',
        'by_run_type': list(by_run_type.values()),
        'samples': samples,
    }


def _numeric_sample_value(sample: Mapping[str, object], key: str) -> float | None:
    value = sample.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pearson_correlation(rows: Sequence[Mapping[str, object]], x_key: str, y_key: str) -> float | None:
    pairs: list[tuple[float, float]] = []
    for row in rows:
        x = _numeric_sample_value(row, x_key)
        y = _numeric_sample_value(row, y_key)
        if x is not None and y is not None:
            pairs.append((x, y))
    if len(pairs) < 2:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    denominator = denominator_x * denominator_y
    if denominator <= 0.0:
        return None
    return numerator / denominator


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    size = len(vector)
    if size == 0 or any(len(row) != size for row in matrix):
        return None
    augmented = [list(row) + [float(vector[index])] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        pivot_value = augmented[pivot][column]
        if abs(pivot_value) < 1e-12:
            return None
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        for item in range(column, size + 1):
            augmented[column][item] /= divisor
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            for item in range(column, size + 1):
                augmented[row][item] -= factor * augmented[column][item]
    return [augmented[row][size] for row in range(size)]


def _boss_wave_pressure_driver_empirical_transform_candidate(
    calibration_rows: Sequence[Mapping[str, object]],
    *,
    approve_empirical_transform_default: bool = False,
) -> dict[str, object]:
    target_key = 'pressure_factor_hint'
    requested_features = [
        'tier',
        'wave',
        'normal_spawn_rate_pressure_index',
        'wave_accelerator_spawn_rate_acceleration',
        'elite_pressure_index_pct',
        'fleet_events_per_wave_pressure',
    ]
    usable_rows: list[dict[str, float]] = []
    usable_source_rows: list[Mapping[str, object]] = []
    for row in calibration_rows:
        target = _numeric_sample_value(row, target_key)
        if target is None:
            continue
        values: dict[str, float] = {target_key: target}
        missing = False
        for feature in requested_features:
            value = _numeric_sample_value(row, feature)
            if value is None:
                missing = True
                break
            values[feature] = value
        if not missing:
            usable_rows.append(values)
            usable_source_rows.append(row)
    if len(usable_rows) < 3:
        return {
            'status': 'not_available_insufficient_rows',
            'application': 'diagnostic_only_not_account_truth',
            'default_pressure_factor_derived': False,
            'requested_features': requested_features,
            'row_count': len(usable_rows),
        }

    feature_stats: dict[str, dict[str, float]] = {}
    active_features: list[str] = []
    omitted_features: list[str] = []
    for feature in requested_features:
        values = [row[feature] for row in usable_rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std = math.sqrt(variance)
        feature_stats[feature] = {'mean': mean, 'std': std}
        if std <= 1e-12:
            omitted_features.append(feature)
        else:
            active_features.append(feature)

    if not active_features:
        return {
            'status': 'not_available_no_varying_features',
            'application': 'diagnostic_only_not_account_truth',
            'default_pressure_factor_derived': False,
            'requested_features': requested_features,
            'omitted_constant_features': omitted_features,
            'row_count': len(usable_rows),
        }

    ridge_lambda = 1e-6
    design: list[list[float]] = [
        [1.0]
        + [
            (row[feature] - feature_stats[feature]['mean']) / feature_stats[feature]['std']
            for feature in active_features
        ]
        for row in usable_rows
    ]
    targets: list[float] = [row[target_key] for row in usable_rows]

    def fit_standardized_ridge(
        fit_rows: Sequence[Mapping[str, float]],
    ) -> tuple[list[float], dict[str, dict[str, float]], list[str]] | None:
        fit_feature_stats: dict[str, dict[str, float]] = {}
        fit_features: list[str] = []
        for feature in active_features:
            values = [float(row[feature]) for row in fit_rows]
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            std = math.sqrt(variance)
            if std <= 1e-12:
                continue
            fit_features.append(feature)
            fit_feature_stats[feature] = {'mean': mean, 'std': std}
        if len(fit_rows) <= len(fit_features):
            return None
        fit_design = [
            [1.0]
            + [
                (float(row[feature]) - fit_feature_stats[feature]['mean'])
                / fit_feature_stats[feature]['std']
                for feature in fit_features
            ]
            for row in fit_rows
        ]
        fit_targets = [float(row[target_key]) for row in fit_rows]
        column_count = len(fit_design[0])
        normal_matrix = [[0.0 for _ in range(column_count)] for _ in range(column_count)]
        normal_vector = [0.0 for _ in range(column_count)]
        for row_values, target in zip(fit_design, fit_targets):
            for i in range(column_count):
                normal_vector[i] += row_values[i] * target
                for j in range(column_count):
                    normal_matrix[i][j] += row_values[i] * row_values[j]
        for i in range(1, column_count):
            normal_matrix[i][i] += ridge_lambda
        coefficients = _solve_linear_system(normal_matrix, normal_vector)
        if coefficients is None:
            return None
        return coefficients, fit_feature_stats, fit_features

    fit = fit_standardized_ridge(usable_rows)
    coefficients = fit[0] if fit is not None else None
    if coefficients is None:
        return {
            'status': 'not_available_singular_design',
            'application': 'diagnostic_only_not_account_truth',
            'default_pressure_factor_derived': False,
            'requested_features': requested_features,
            'active_features': active_features,
            'omitted_constant_features': omitted_features,
            'row_count': len(usable_rows),
        }

    predictions: list[dict[str, object]] = []
    errors: list[float] = []
    abs_errors: list[float] = []
    for source_row, row_values, target in zip(usable_source_rows, design, targets):
        predicted = sum(coef * value for coef, value in zip(coefficients, row_values))
        error = predicted - target
        errors.append(error)
        abs_errors.append(abs(error))
        predictions.append(
            {
                'tier': source_row.get('tier'),
                'actual_pressure_factor': target,
                'predicted_pressure_factor': predicted,
                'error': error,
                'abs_error': abs(error),
            }
        )
    mae = sum(abs_errors) / len(abs_errors)
    rmse = math.sqrt(sum(error ** 2 for error in errors) / len(errors))
    max_abs_error = max(abs_errors)
    worst = max(predictions, key=lambda row: float(row.get('abs_error') or 0.0), default={})
    loo_predictions: list[dict[str, object]] = []
    loo_errors: list[float] = []
    loo_abs_errors: list[float] = []
    for index, (source_row, holdout) in enumerate(zip(usable_source_rows, usable_rows)):
        train_rows = [row for train_index, row in enumerate(usable_rows) if train_index != index]
        loo_fit = fit_standardized_ridge(train_rows)
        if loo_fit is None:
            loo_predictions.append(
                {
                    'tier': source_row.get('tier'),
                    'actual_pressure_factor': holdout[target_key],
                    'predicted_pressure_factor': None,
                    'status': 'not_available_singular_or_constant_fold',
                }
            )
            continue
        loo_coefficients, loo_feature_stats, loo_features = loo_fit
        holdout_values = [1.0] + [
            (holdout[feature] - loo_feature_stats[feature]['mean'])
            / loo_feature_stats[feature]['std']
            for feature in loo_features
        ]
        predicted = sum(coef * value for coef, value in zip(loo_coefficients, holdout_values))
        error = predicted - holdout[target_key]
        loo_errors.append(error)
        loo_abs_errors.append(abs(error))
        loo_predictions.append(
            {
                'tier': source_row.get('tier'),
                'actual_pressure_factor': holdout[target_key],
                'predicted_pressure_factor': predicted,
                'error': error,
                'abs_error': abs(error),
                'status': 'validated_holdout_prediction',
            }
        )
    loo_worst = max(
        (row for row in loo_predictions if row.get('abs_error') is not None),
        key=lambda row: float(row.get('abs_error') or 0.0),
        default={},
    )
    loo_validation = {
        'method': 'leave_one_out_by_clean_regular_row',
        'status': 'available_descriptive_only' if loo_abs_errors else 'not_available',
        'validated_row_count': len(loo_abs_errors),
        'unvalidated_row_count': len(usable_rows) - len(loo_abs_errors),
        'mean_absolute_error': (
            sum(loo_abs_errors) / len(loo_abs_errors) if loo_abs_errors else None
        ),
        'root_mean_squared_error': (
            math.sqrt(sum(error ** 2 for error in loo_errors) / len(loo_errors))
            if loo_errors
            else None
        ),
        'max_absolute_error': max(loo_abs_errors) if loo_abs_errors else None,
        'worst_row': loo_worst,
        'predictions': loo_predictions,
    }
    blocking_reasons = [
        'not_source_owned_terminal_pressure_formula',
        'non_capped_dissonance_reference_validation_missing',
        'out_of_sample_validation_beyond_clean_regular_rows_missing',
    ]
    if not approve_empirical_transform_default:
        blocking_reasons.insert(1, 'operator_has_not_approved_empirical_transform_as_default')
    promotion_readiness = {
        'status': 'not_ready',
        'application': 'diagnostic_only_not_account_truth',
        'default_pressure_factor_derived': False,
        'operator_approval_required': True,
        'operator_approved_empirical_transform_default': bool(
            approve_empirical_transform_default
        ),
        'operator_approval_status': (
            'approved_explicit_runtime_input'
            if approve_empirical_transform_default
            else 'not_approved'
        ),
        'approval_runtime_input': 'approve_boss_wave_empirical_pressure_transform',
        'approval_policy': (
            'Explicit approval removes only the operator-approval blocker; '
            'source-owned formula and validation blockers still apply.'
        ),
        'validation_basis': 'clean_regular_rows_leave_one_out_only',
        'validated_row_count': loo_validation['validated_row_count'],
        'mean_absolute_error': loo_validation['mean_absolute_error'],
        'max_absolute_error': loo_validation['max_absolute_error'],
        'blocking_reasons': blocking_reasons,
    }
    return {
        'status': 'fitted_in_sample_descriptive_only',
        'application': 'diagnostic_only_not_account_truth',
        'default_pressure_factor_derived': False,
        'validation_status': 'leave_one_out_descriptive_only_not_promoted',
        'model_form': 'ridge_linear_standardized_pressure_factor',
        'target': 'pressure_factor_hint',
        'requested_features': requested_features,
        'active_features': active_features,
        'omitted_constant_features': omitted_features,
        'row_count': len(usable_rows),
        'ridge_lambda': ridge_lambda,
        'intercept': coefficients[0],
        'standardized_coefficients': {
            feature: coefficients[index + 1]
            for index, feature in enumerate(active_features)
        },
        'feature_standardization': feature_stats,
        'error_metrics': {
            'mean_absolute_error': mae,
            'root_mean_squared_error': rmse,
            'max_absolute_error': max_abs_error,
            'worst_row': worst,
        },
        'predictions': predictions,
        'leave_one_out_validation': loo_validation,
        'promotion_readiness': promotion_readiness,
        'promotion_status': 'not_promoted',
        'missing_to_promote': [
            'approved_pressure_driver_composition_rule',
            'approved_pressure_to_terminal_max_wave_or_pressure_factor_transform',
            'non_capped_dissonance_reference_validation',
            'source_owned_out_of_sample_or_holdout_validation_beyond_clean_regular_rows',
        ],
    }


def _boss_wave_pressure_driver_empirical_calibration(
    pressure_driver_samples: Mapping[str, object],
    *,
    approve_empirical_transform_default: bool = False,
) -> dict[str, object]:
    calibration_rows: list[dict[str, object]] = []
    for sample in list(pressure_driver_samples.get('samples') or []):
        if not isinstance(sample, Mapping):
            continue
        hint = dict(sample.get('pressure_factor_hint') or {})
        reference_quality = dict(sample.get('reference_quality') or {})
        if not bool(hint.get('enabled')):
            continue
        if str(sample.get('dissonance_run_category') or 'none') != 'none':
            continue
        if not bool(reference_quality.get('calibration_candidate')):
            continue
        if list(reference_quality.get('caveats') or []):
            continue
        factor = _numeric_sample_value(hint, 'boss_wave_pressure_factor')
        if factor is None:
            continue
        calibration_rows.append(
            {
                'tier': int(sample.get('tier') or 0),
                'wave': int(sample.get('wave') or 0),
                'reference_wave': sample.get('reference_wave'),
                'pressure_factor_hint': factor,
                'normal_spawn_rate_pressure_index': sample.get('normal_spawn_rate_pressure_index'),
                'displayed_spawn_rate': sample.get('displayed_spawn_rate'),
                'wave_accelerator_spawn_rate_acceleration': sample.get(
                    'wave_accelerator_spawn_rate_acceleration'
                ),
                'elite_pressure_index_pct': sample.get('elite_pressure_index_pct'),
                'fleet_events_per_wave_pressure': sample.get('fleet_events_per_wave_pressure'),
                'fleet_related_enemy_group_expected_enemies_per_wave_pressure': sample.get(
                    'fleet_related_enemy_group_expected_enemies_per_wave_pressure'
                ),
            }
        )
    feature_keys = [
        'tier',
        'wave',
        'reference_wave',
        'normal_spawn_rate_pressure_index',
        'displayed_spawn_rate',
        'wave_accelerator_spawn_rate_acceleration',
        'elite_pressure_index_pct',
        'fleet_events_per_wave_pressure',
        'fleet_related_enemy_group_expected_enemies_per_wave_pressure',
    ]
    correlations = {
        key: _pearson_correlation(calibration_rows, key, 'pressure_factor_hint')
        for key in feature_keys
    }
    factors = [
        float(row['pressure_factor_hint'])
        for row in calibration_rows
        if row.get('pressure_factor_hint') is not None
    ]
    factor_summary = _boss_wave_pressure_factor_distribution(
        {'boss_wave_pressure_factor': factor} for factor in factors
    )
    return {
        'status': 'available_descriptive_only' if calibration_rows else 'not_available',
        'application': 'diagnostic_only_not_account_truth',
        'default_pressure_factor_derived': False,
        'model_fit_status': 'not_fitted_terminal_transform_missing',
        'sample_basis': 'clean_regular_selected_rows_with_exact_reference',
        'calibration_row_count': len(calibration_rows),
        'target': 'raw_calculated_selected_wave / clean_reference_wave',
        'candidate_driver_features': feature_keys,
        'feature_correlations_to_pressure_factor': correlations,
        'pressure_factor_distribution': factor_summary,
        'empirical_transform_candidate': _boss_wave_pressure_driver_empirical_transform_candidate(
            calibration_rows,
            approve_empirical_transform_default=approve_empirical_transform_default,
        ),
        'rows': calibration_rows,
        'missing_to_promote': [
            'approved_pressure_driver_composition_rule',
            'approved_pressure_to_terminal_max_wave_or_pressure_factor_transform',
            'validation_against_non_capped_dissonance_references',
        ],
    }


def _boss_wave_pressure_driver_candidate_sample_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    candidate_rows: list[dict[str, object]] = []
    for row in rows:
        for candidate in list(row.get('candidate_results') or []):
            if not isinstance(candidate, Mapping):
                continue
            probe = dict(candidate.get('non_boss_pressure_driver_probe') or {})
            if not probe or str(probe.get('status') or '').startswith('not_available'):
                continue
            candidate_wave = int(candidate.get('selected_max_wave') or 0)
            candidate_reference_wave = _extract_optional_wave_number(candidate.get('reference_wave'))
            candidate_delta_vs_reference = (
                candidate_wave - int(candidate_reference_wave)
                if candidate_reference_wave is not None and candidate_reference_wave > 0
                else None
            )
            candidate_to_reference_ratio = (
                candidate_wave / float(candidate_reference_wave)
                if candidate_reference_wave is not None
                and candidate_reference_wave > 0
                and candidate_wave > 0
                else None
            )
            candidate_pressure_hint = _boss_wave_pressure_factor_reference_hint(
                calculated_wave=candidate_wave,
                reference_wave=candidate_reference_wave,
                reference_kind=candidate.get('reference_kind'),
                reference_source=candidate.get('reference_source'),
                calculated_delta_vs_reference_wave=candidate_delta_vs_reference,
                calculated_to_reference_ratio=candidate_to_reference_ratio,
            )
            candidate_rows.append(
                {
                    'tier': row.get('tier'),
                    'dissonance_run_category': row.get('dissonance_run_category'),
                    'label': row.get('label'),
                    'best_calculated_selected_max_wave': candidate.get('selected_max_wave'),
                    'reference_wave': candidate.get('reference_wave'),
                    'pressure_factor_reference_hint': candidate_pressure_hint,
                    'non_boss_pressure_driver_probe': probe,
                    'loadout_policy_preset': candidate.get('loadout_policy_preset'),
                    'loadout_profile_preset': candidate.get('loadout_profile_preset'),
                    'selected_loadout_type': candidate.get('selected_loadout_type'),
                }
            )
    summary = _boss_wave_pressure_driver_sample_summary(candidate_rows)
    summary['sample_basis'] = 'all_matrix_candidate_rows_at_candidate_raw_selected_max_wave'
    summary['candidate_sample_count'] = summary.get('sample_count', 0)
    return summary


def _boss_wave_tracker_reference_evidence(
    rows: Sequence[Mapping[str, object]],
    run_tracker_evidence: Mapping[str, object] | None,
) -> dict[str, object]:
    if not isinstance(run_tracker_evidence, Mapping):
        return {
            'status': 'not_supplied',
            'application': 'external_observation_not_account_truth',
            'certification_effect': 'none',
        }
    matrix_by_tier_category = {
        (
            int(row.get('tier') or 0),
            str(row.get('dissonance_run_category') or 'none'),
        ): row
        for row in rows
        if row.get('tier') is not None
    }
    references: list[dict[str, object]] = []
    matched_regular: list[dict[str, object]] = []
    dissonance_category_hints: list[dict[str, object]] = []
    unmapped_dissonance: list[dict[str, object]] = []
    dissonance_bonus_cap_reference_count = 0
    dissonance_below_3000_reference_count = 0
    dissonance_clean_candidate_reference_count = 0
    for item in list(run_tracker_evidence.get('type_tier_summaries') or []):
        if not isinstance(item, Mapping):
            continue
        tier = item.get('tier')
        max_wave = item.get('max_wave')
        run_type = str(item.get('run_type') or 'Unknown')
        try:
            tier_number = int(tier)
            tracker_max_wave = int(max_wave)
        except (TypeError, ValueError):
            continue
        if tier_number <= 0 or tracker_max_wave <= 0:
            continue
        normalized_run_type = run_type.strip().lower()
        reference = {
            'tier': tier_number,
            'run_type': run_type,
            'tracker_max_wave': tracker_max_wave,
            'row_count': item.get('row_count'),
            'latest_wave': dict(item.get('latest') or {}).get('wave'),
            'max_wave_record': item.get('max_wave_record'),
            'application': 'external_observation_not_account_truth',
        }
        if normalized_run_type in {'farming', 'tournament', 'tourney', 'milestone'}:
            matrix_row = matrix_by_tier_category.get((tier_number, 'none'))
            reference['matrix_dissonance_run_category'] = 'none'
            reference['mapping_status'] = (
                'matched_regular_same_tier'
                if matrix_row is not None
                else 'no_same_tier_regular_matrix_row'
            )
            if matrix_row is not None:
                calculated_wave = int(matrix_row.get('best_calculated_selected_max_wave') or 0)
                selected_wave = int(matrix_row.get('best_selected_max_wave') or 0)
                reference.update(
                    {
                        'matrix_calculated_wave': calculated_wave,
                        'matrix_selected_wave': selected_wave,
                        'calculated_delta_vs_tracker_max_wave': calculated_wave - tracker_max_wave,
                        'selected_delta_vs_tracker_max_wave': selected_wave - tracker_max_wave,
                        'calculated_to_tracker_max_wave_ratio': (
                            calculated_wave / float(tracker_max_wave)
                            if tracker_max_wave > 0 and calculated_wave > 0
                            else None
                        ),
                        'selected_to_tracker_max_wave_ratio': (
                            selected_wave / float(tracker_max_wave)
                            if tracker_max_wave > 0 and selected_wave > 0
                            else None
                        ),
                        'matrix_loadout_policy_preset': matrix_row.get('best_loadout_policy_preset'),
                        'matrix_model_closure_status': matrix_row.get('model_closure_status'),
                        'matrix_model_completion_blockers': list(
                            matrix_row.get('model_completion_blockers') or []
                        ),
                    }
                )
                matched_regular.append(reference)
        elif normalized_run_type == 'dissonance':
            hint = _tracker_dissonance_category_hint(reference)
            tracker_at_or_above_bonus_cap = tracker_max_wave >= _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE
            tracker_below_3000 = tracker_max_wave < 3000
            has_category_hint = bool(hint.get('category'))
            if tracker_at_or_above_bonus_cap:
                dissonance_bonus_cap_reference_count += 1
            if tracker_below_3000:
                dissonance_below_3000_reference_count += 1
            clean_tracker_calibration_candidate = (
                has_category_hint
                and not tracker_at_or_above_bonus_cap
                and not tracker_below_3000
            )
            if clean_tracker_calibration_candidate:
                dissonance_clean_candidate_reference_count += 1
            reference['dissonance_bonus_cap_policy'] = {
                'user_reported_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
                'tracker_at_or_above_bonus_cap': tracker_at_or_above_bonus_cap,
                'application': 'reference_context_only_not_selected_wave_cap',
            }
            reference['tracker_dissonance_calibration_filter'] = {
                'status': (
                    'excluded_dissonance_bonus_cap_reference'
                    if tracker_at_or_above_bonus_cap
                    else 'caveated_below_3000_reference'
                    if tracker_below_3000
                    else 'candidate_category_hint_available_not_applied'
                    if has_category_hint
                    else 'unmapped_not_calibration_candidate'
                ),
                'application': 'external_observation_not_account_truth',
                'certification_effect': 'none',
                'user_reported_bonus_cap_wave': _BOSS_WAVE_DISSONANCE_PB_BONUS_CAP_WAVE,
                'tracker_at_or_above_bonus_cap': tracker_at_or_above_bonus_cap,
                'tracker_below_3000_wave': tracker_below_3000,
                'category_hint_available': has_category_hint,
                'clean_tracker_calibration_candidate': clean_tracker_calibration_candidate,
                'policy': (
                    'Exclude Dissonance cap-floor rows; report sub-3000 rows as caveated '
                    'sensitivity because perk variance can dominate; never auto-apply tracker rows.'
                ),
            }
            if has_category_hint:
                category = str(hint['category'])
                matrix_row = matrix_by_tier_category.get((tier_number, category))
                reference['matrix_dissonance_run_category'] = category
                reference['mapping_status'] = 'tracker_dissonance_category_hint_available_not_applied'
                reference['category_hint'] = hint
                reference['available_matrix_categories'] = list(_BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES)
                if matrix_row is not None:
                    calculated_wave = int(matrix_row.get('best_calculated_selected_max_wave') or 0)
                    selected_wave = int(matrix_row.get('best_selected_max_wave') or 0)
                    reference.update(
                        {
                            'matrix_calculated_wave': calculated_wave,
                            'matrix_selected_wave': selected_wave,
                            'calculated_delta_vs_tracker_max_wave': calculated_wave - tracker_max_wave,
                            'selected_delta_vs_tracker_max_wave': selected_wave - tracker_max_wave,
                            'calculated_to_tracker_max_wave_ratio': (
                                calculated_wave / float(tracker_max_wave)
                                if tracker_max_wave > 0 and calculated_wave > 0
                                else None
                            ),
                            'selected_to_tracker_max_wave_ratio': (
                                selected_wave / float(tracker_max_wave)
                                if tracker_max_wave > 0 and selected_wave > 0
                                else None
                            ),
                            'matrix_loadout_policy_preset': matrix_row.get('best_loadout_policy_preset'),
                            'matrix_model_closure_status': matrix_row.get('model_closure_status'),
                            'matrix_model_completion_blockers': list(
                                matrix_row.get('model_completion_blockers') or []
                            ),
                        }
                    )
                dissonance_category_hints.append(reference)
            else:
                reference['matrix_dissonance_run_category'] = None
                reference['mapping_status'] = 'tracker_dissonance_type_category_unmapped'
                reference['available_matrix_categories'] = list(_BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES)
                reference['category_hint'] = hint
                unmapped_dissonance.append(reference)
        else:
            reference['matrix_dissonance_run_category'] = None
            reference['mapping_status'] = 'tracker_run_type_unmapped'
        references.append(reference)

    return {
        'status': (
            'tracker_boss_wave_reference_evidence_available_not_applied'
            if references
            else 'tracker_supplied_without_max_wave_reference_rows'
        ),
        'source': run_tracker_evidence.get('source'),
        'application': run_tracker_evidence.get('application'),
        'certification_effect': 'none',
        'row_count': len(references),
        'matched_regular_reference_count': len(matched_regular),
        'dissonance_category_hint_reference_count': len(dissonance_category_hints),
        'unmapped_dissonance_reference_count': len(unmapped_dissonance),
        'dissonance_tracker_calibration_filter': {
            'status': (
                'tracker_dissonance_filter_evidence_available'
                if dissonance_category_hints or unmapped_dissonance
                else 'not_available'
            ),
            'application': 'external_observation_not_account_truth',
            'certification_effect': 'none',
            'dissonance_pb_5000_cap_policy': 'excluded_from_calibration_lower_bound_only',
            'below_3000_wave_policy': 'reported_as_caveated_sensitivity_not_clean_calibration',
            'dissonance_pb_5000_cap_reference_count': dissonance_bonus_cap_reference_count,
            'below_3000_wave_reference_count': dissonance_below_3000_reference_count,
            'clean_tracker_calibration_candidate_count': dissonance_clean_candidate_reference_count,
        },
        'dissonance_tracker_alignment_summary': _boss_wave_tracker_dissonance_alignment_summary(
            dissonance_category_hints=dissonance_category_hints,
            unmapped_dissonance=unmapped_dissonance,
        ),
        'matching_policy': (
            'Farming/Tournament tracker rows match same-tier regular matrix rows; '
            'Dissonance tracker rows may expose note-derived category hints for inspection, '
            'but hints are not applied as authoritative category mappings.'
        ),
        'matched_regular_references': matched_regular,
        'dissonance_category_hint_references': dissonance_category_hints,
        'unmapped_dissonance_references': unmapped_dissonance,
        'references': references,
        'interpretation': (
            'Tracker max-wave rows are external reference evidence only; they do not alter '
            'selected waves, pressure factors, KB truth, or model certification.'
        ),
    }


def _boss_wave_tracker_dissonance_alignment_summary(
    *,
    dissonance_category_hints: Sequence[Mapping[str, object]],
    unmapped_dissonance: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    status_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    by_category: dict[str, dict[str, object]] = {}
    for reference in list(dissonance_category_hints) + list(unmapped_dissonance):
        filter_payload = dict(reference.get('tracker_dissonance_calibration_filter') or {})
        status = str(filter_payload.get('status') or 'unknown')
        status_counts[status] += 1
    for reference in dissonance_category_hints:
        category = str(reference.get('matrix_dissonance_run_category') or 'unknown')
        category_counts[category] += 1
        group = by_category.setdefault(
            category,
            {
                'dissonance_run_category': category,
                'reference_count': 0,
                'selected_delta_vs_tracker_max_wave_values': [],
                'calculated_delta_vs_tracker_max_wave_values': [],
                'selected_to_tracker_max_wave_ratio_values': [],
                'calculated_to_tracker_max_wave_ratio_values': [],
            },
        )
        group['reference_count'] = int(group['reference_count']) + 1
        for key in (
            'selected_delta_vs_tracker_max_wave',
            'calculated_delta_vs_tracker_max_wave',
            'selected_to_tracker_max_wave_ratio',
            'calculated_to_tracker_max_wave_ratio',
        ):
            value = reference.get(key)
            if value is not None:
                group_values = group[f'{key}_values']
                if isinstance(group_values, list):
                    group_values.append(value)
    category_rows: list[dict[str, object]] = []
    for category, group in sorted(by_category.items()):
        category_rows.append(
            {
                'dissonance_run_category': category,
                'reference_count': int(group['reference_count']),
                'selected_delta_vs_tracker_max_wave_median': _median_numeric(
                    group['selected_delta_vs_tracker_max_wave_values']
                ),
                'calculated_delta_vs_tracker_max_wave_median': _median_numeric(
                    group['calculated_delta_vs_tracker_max_wave_values']
                ),
                'selected_to_tracker_max_wave_ratio_median': _median_numeric(
                    group['selected_to_tracker_max_wave_ratio_values']
                ),
                'calculated_to_tracker_max_wave_ratio_median': _median_numeric(
                    group['calculated_to_tracker_max_wave_ratio_values']
                ),
            }
        )
    return {
        'status': (
            'tracker_dissonance_alignment_available_not_applied'
            if dissonance_category_hints or unmapped_dissonance
            else 'not_available'
        ),
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
        'reference_count': len(dissonance_category_hints) + len(unmapped_dissonance),
        'category_hint_reference_count': len(dissonance_category_hints),
        'unmapped_reference_count': len(unmapped_dissonance),
        'filter_status_counts': dict(sorted(status_counts.items())),
        'category_hint_counts': dict(sorted(category_counts.items())),
        'selected_delta_vs_tracker_max_wave_median': _median_numeric(
            reference.get('selected_delta_vs_tracker_max_wave')
            for reference in dissonance_category_hints
        ),
        'calculated_delta_vs_tracker_max_wave_median': _median_numeric(
            reference.get('calculated_delta_vs_tracker_max_wave')
            for reference in dissonance_category_hints
        ),
        'selected_to_tracker_max_wave_ratio_median': _median_numeric(
            reference.get('selected_to_tracker_max_wave_ratio')
            for reference in dissonance_category_hints
        ),
        'calculated_to_tracker_max_wave_ratio_median': _median_numeric(
            reference.get('calculated_to_tracker_max_wave_ratio')
            for reference in dissonance_category_hints
        ),
        'by_category': category_rows,
        'interpretation': (
            'Category-hinted tracker Dissonance rows are summarized for review only; '
            'cap-floor and sub-3000 policies still decide calibration eligibility.'
        ),
    }


def _tracker_dissonance_category_hint(reference: Mapping[str, object]) -> dict[str, object]:
    """Return a non-authoritative Dissonance category hint from tracker note text."""
    max_wave_record = reference.get('max_wave_record')
    record = max_wave_record if isinstance(max_wave_record, Mapping) else {}
    note = str(record.get('note') or '').strip()
    text = note.lower()
    token_to_category = (
        ('econ', 'utility'),
        ('coin', 'utility'),
        ('cash', 'utility'),
        ('utility', 'utility'),
        ('health', 'defense'),
        ('ehp', 'defense'),
        ('defense', 'defense'),
        ('attack', 'attack'),
        ('damage', 'attack'),
        ('ultimate', 'ultimate_weapons'),
        ('uw', 'ultimate_weapons'),
    )
    for token, category in token_to_category:
        if token in text:
            return {
                'status': 'available_not_authoritative',
                'category': category,
                'matched_token': token,
                'source_field': 'max_wave_record.note',
                'source_text': note,
                'application': 'diagnostic_hint_only_not_category_truth',
            }
    return {
        'status': 'not_available',
        'category': None,
        'source_field': 'max_wave_record.note',
        'source_text': note,
        'application': 'diagnostic_hint_only_not_category_truth',
    }


def _boss_wave_matrix_model_accuracy_summary(
    *,
    certification: Mapping[str, object],
    model_blocker_summary: Mapping[str, object],
    reference_quality_summary: Mapping[str, object],
    pressure_factor_hint_summary: Mapping[str, object],
    reference_gap_summary: Mapping[str, object],
    pressure_driver_samples: Mapping[str, object] | None = None,
    pressure_driver_candidate_samples: Mapping[str, object] | None = None,
    approve_empirical_pressure_transform_default: bool = False,
) -> dict[str, object]:
    accepted_approximation = dict(certification.get('accepted_approximation_closure') or {})
    blockers = [str(blocker) for blocker in list(certification.get('model_completion_blockers') or [])]
    calibration_quality = dict(pressure_factor_hint_summary.get('calibration_quality') or {})
    factor_distribution = dict(calibration_quality.get('factor_distribution') or {})
    comparison_inputs = dict(factor_distribution.get('comparison_scenario_runtime_inputs') or {})
    pressure_factor_by_run_type = _boss_wave_pressure_factor_accuracy_by_run_type(
        pressure_factor_hint_summary
    )
    dissonance_pressure_factor_evidence = _boss_wave_dissonance_pressure_factor_evidence(
        pressure_factor_by_run_type
    )
    pressure_driver_model = _boss_wave_non_boss_pressure_driver_model_summary(
        certification=certification,
        model_blocker_summary=model_blocker_summary,
        pressure_factor_hint_summary=pressure_factor_hint_summary,
        reference_quality_summary=reference_quality_summary,
        pressure_driver_samples=pressure_driver_samples,
        pressure_driver_candidate_samples=pressure_driver_candidate_samples,
        approve_empirical_pressure_transform_default=(
            approve_empirical_pressure_transform_default
        ),
    )
    reference_caveat_counts = {
        'below_3000_wave_perk_volatility': int(
            reference_quality_summary.get('low_wave_reference_count') or 0
        ),
        'pb_age_unknown_no_source_timestamp': int(
            reference_quality_summary.get('pb_age_unknown_count') or 0
        ),
        'dissonance_pb_5000_bonus_cap_floor': int(
            reference_quality_summary.get('dissonance_pb_bonus_cap_count') or 0
        ),
    }
    missing_reference_count = int(reference_gap_summary.get('missing_reference_blocked_count') or 0)
    rows_with_caveats = int(reference_quality_summary.get('rows_with_caveats') or 0)
    has_calibration_input = bool(comparison_inputs)
    if bool(certification.get('certified_full_max_wave_model')):
        status = 'certified_full_model'
    elif bool(accepted_approximation.get('closed')):
        status = 'explicit_pressure_factor_approximation_active'
    elif blockers and has_calibration_input:
        status = 'default_partial_comparison_calibration_available'
    elif blockers:
        status = 'default_partial_missing_required_model_inputs'
    elif missing_reference_count or rows_with_caveats:
        status = 'closed_with_reference_caveats'
    else:
        status = 'closed_with_clean_reference_set'
    if status == 'default_partial_comparison_calibration_available':
        operator_next_step = 'apply_comparison_only_pressure_factor_input_to_review_approximation'
    elif status == 'explicit_pressure_factor_approximation_active':
        operator_next_step = 'review_approximation_against_reference_quality_caveats'
    elif status == 'default_partial_missing_required_model_inputs':
        operator_next_step = 'supply_terminal_max_wave_inputs_or_explicit_pressure_factor'
    elif status == 'closed_with_reference_caveats':
        operator_next_step = 'review_reference_caveats_before_accuracy_claim'
    else:
        operator_next_step = 'none'
    return {
        'status': status,
        'model_scope': 'boss_contact_survivability',
        'not_full_max_wave_model': True,
        'model_certification_status': certification.get('model_certification_status'),
        'model_closure_status': certification.get('model_closure_status'),
        'certified_full_max_wave_model': bool(certification.get('certified_full_max_wave_model')),
        'model_completion_blockers': blockers,
        'rows_with_model_completion_blockers': int(
            model_blocker_summary.get('rows_with_model_completion_blockers') or 0
        ),
        'accepted_approximation_closure': accepted_approximation,
        'comparison_only_pressure_factor_inputs': comparison_inputs,
        'calibration_quality_pressure_factor_distribution': factor_distribution,
        'pressure_factor_by_run_type': pressure_factor_by_run_type,
        'dissonance_pressure_factor_evidence': dissonance_pressure_factor_evidence,
        'non_boss_pressure_driver_model': pressure_driver_model,
        'pressure_factor_application': 'manual_or_comparison_only',
        'reference_row_count': int(reference_quality_summary.get('rows_with_reference') or 0),
        'calibration_candidate_count': int(
            reference_quality_summary.get('calibration_candidate_count') or 0
        ),
        'missing_reference_blocked_count': missing_reference_count,
        'reference_caveat_counts': reference_caveat_counts,
        'rows_with_reference_caveats': rows_with_caveats,
        'operator_next_step': operator_next_step,
    }


def _boss_wave_matrix_certification_from_selected_rows(
    base_certification: dict[str, object],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    blockers = sorted({
        str(blocker)
        for row in rows
        for blocker in list(row.get('model_completion_blockers') or [])
    })
    certification = dict(base_certification)
    certification['model_completion_blockers'] = blockers
    certification['unsupported_terminal_pressures'] = sorted({
        str(pressure)
        for row in rows
        for pressure in list(row.get('unsupported_terminal_pressures') or [])
    })
    selected_terminal_statuses = [
        dict(row.get('terminal_pressure_runtime_override_status') or {})
        for row in rows
        if row.get('terminal_pressure_runtime_override_status')
    ]
    if selected_terminal_statuses and certification['unsupported_terminal_pressures']:
        active_terminal_statuses = [
            status
            for status in selected_terminal_statuses
            if status.get('mode') == 'active_unsupported_pressure_inputs'
            or status.get('required_fields_by_pressure')
        ]
        terminal_statuses = active_terminal_statuses or selected_terminal_statuses
        required_fields_by_pressure: dict[str, list[str]] = {}
        missing_fields_by_pressure: dict[str, list[str]] = {}
        required_fields: set[str] = set()
        missing_fields: set[str] = set()
        unmapped_pressures: set[str] = set()
        for status in terminal_statuses:
            for field_name in list(status.get('required_fields') or []):
                required_fields.add(str(field_name))
            for field_name in list(status.get('missing_fields') or []):
                missing_fields.add(str(field_name))
            for pressure, fields in dict(status.get('required_fields_by_pressure') or {}).items():
                required_fields_by_pressure[str(pressure)] = [str(field_name) for field_name in list(fields or [])]
            for pressure, fields in dict(status.get('missing_fields_by_pressure') or {}).items():
                missing_fields_by_pressure[str(pressure)] = [str(field_name) for field_name in list(fields or [])]
            for pressure in list(status.get('unmapped_pressures') or []):
                unmapped_pressures.add(str(pressure))
        certification['terminal_pressure_runtime_override_status'] = {
            'closed': not unmapped_pressures and not missing_fields_by_pressure,
            'mode': 'active_unsupported_pressure_inputs',
            'required_fields': sorted(required_fields),
            'missing_fields': sorted(missing_fields),
            'required_fields_by_pressure': dict(sorted(required_fields_by_pressure.items())),
            'missing_fields_by_pressure': dict(sorted(missing_fields_by_pressure.items())),
            'unmapped_pressures': sorted(unmapped_pressures),
        }
    selected_pressure_closures = [
        dict(row.get('non_boss_terminal_pressure_closure') or {})
        for row in rows
        if row.get('non_boss_terminal_pressure_closure')
    ]
    if selected_pressure_closures:
        pressure_required = bool(certification['unsupported_terminal_pressures'])
        relevant_pressure_closures = [
            closure
            for closure in selected_pressure_closures
            if str(closure.get('mode') or '') != 'not_required'
        ]
        pressure_closed = bool(pressure_required) and bool(relevant_pressure_closures) and all(
            bool(closure.get('closed'))
            for closure in relevant_pressure_closures
        )
        pressure_factor_closure = next(
            (
                closure
                for closure in selected_pressure_closures
                if bool(closure.get('pressure_factor_approximation_closed'))
            ),
            None,
        )
        exact_terminal_closure = next(
            (
                closure
                for closure in selected_pressure_closures
                if bool(closure.get('exact_terminal_override_closed'))
            ),
            None,
        )
        if pressure_factor_closure is not None:
            certification['non_boss_terminal_pressure_closure'] = dict(pressure_factor_closure)
        elif exact_terminal_closure is not None:
            certification['non_boss_terminal_pressure_closure'] = dict(exact_terminal_closure)
        elif pressure_required:
            certification['non_boss_terminal_pressure_closure'] = {
                'closed': False,
                'mode': 'missing',
                'exact_terminal_override_closed': False,
                'pressure_factor_approximation_closed': False,
                'boss_wave_pressure_factor': None,
            }
        elif not pressure_required:
            certification['non_boss_terminal_pressure_closure'] = {
                'closed': False,
                'mode': 'not_required',
                'exact_terminal_override_closed': False,
                'pressure_factor_approximation_closed': False,
                'boss_wave_pressure_factor': None,
            }
        if pressure_required:
            runtime_override_closure = dict(certification.get('runtime_override_closure') or {})
            runtime_override_closure['non_boss_terminal_pressure'] = bool(pressure_closed)
            certification['runtime_override_closure'] = runtime_override_closure
    requirement_applicability = dict(certification.get('model_requirement_applicability') or {})
    requirement_applicability['non_boss_terminal_pressure'] = (
        'source_owned_non_boss_terminal_pressure_formulas' in blockers
    )
    requirement_applicability['v28_damage_health_decay_magnitudes'] = (
        'source_owned_v28_damage_health_decay_magnitudes' in blockers
    )
    boss_damage_required = 'source_owned_full_boss_applicable_damage_semantics' in blockers
    requirement_applicability['boss_applicable_damage_semantics'] = boss_damage_required
    requirement_applicability['gc_boss_applicable_damage_semantics'] = boss_damage_required
    certification['model_requirement_applicability'] = requirement_applicability
    runtime_override_closure = dict(certification.get('runtime_override_closure') or {})
    certification['effective_model_closure'] = {
        key: (not bool(requirement_applicability.get(key))) or bool(runtime_override_closure.get(key))
        for key in (
            'non_boss_terminal_pressure',
            'v28_damage_health_decay_magnitudes',
            'boss_applicable_damage_semantics',
            'gc_boss_applicable_damage_semantics',
        )
    }
    non_boss_terminal_pressure_closure = dict(
        certification.get('non_boss_terminal_pressure_closure') or {}
    )
    certification['accepted_approximation_closure'] = _boss_wave_accepted_approximation_closure(
        non_boss_terminal_pressure_closure
    )
    certification['model_closure_status'] = _boss_wave_model_closure_status(
        model_completion_blockers=certification.get('model_completion_blockers') or [],
        non_boss_terminal_pressure_closure=non_boss_terminal_pressure_closure,
    )
    return certification


def _boss_wave_matrix_blocker_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    blocker_counts: dict[str, int] = {}
    pressure_counts: dict[str, int] = {}
    rows_with_blockers = 0
    rows_with_unsupported_pressure = 0
    for row in rows:
        blockers = sorted({str(blocker) for blocker in list(row.get('model_completion_blockers') or [])})
        if blockers:
            rows_with_blockers += 1
        for blocker in blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
        pressures = sorted({str(pressure) for pressure in list(row.get('unsupported_terminal_pressures') or [])})
        if pressures:
            rows_with_unsupported_pressure += 1
        for pressure in pressures:
            pressure_counts[pressure] = pressure_counts.get(pressure, 0) + 1
    return {
        'row_count': len(rows),
        'rows_with_model_completion_blockers': rows_with_blockers,
        'model_completion_blocker_counts': dict(sorted(blocker_counts.items())),
        'rows_with_unsupported_terminal_pressures': rows_with_unsupported_pressure,
        'unsupported_terminal_pressure_counts': dict(sorted(pressure_counts.items())),
    }


def _boss_wave_matrix_reference_gap_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    missing_rows = [
        dict(row)
        for row in rows
        if row.get('terminal_pressure_reference_status') == 'missing_empirical_reference_blocked'
    ]
    by_reference_kind: dict[str, int] = {}
    by_run_type: dict[str, dict[str, object]] = {}
    missing_references: list[dict[str, object]] = []
    dissonance_pb_cap_omitted_reference_count = 0
    for row in missing_rows:
        reference_kind = str(row.get('reference_kind') or 'unknown')
        cap_omitted = bool(row.get('dissonance_pb_cap_omitted_reference'))
        if cap_omitted:
            dissonance_pb_cap_omitted_reference_count += 1
        by_reference_kind[reference_kind] = by_reference_kind.get(reference_kind, 0) + 1
        category = str(row.get('dissonance_run_category') or 'none')
        run_summary = by_run_type.setdefault(
            category,
            {
                'dissonance_run_category': category,
                'label': row.get('label') or category,
                'missing_reference_blocked_count': 0,
                'dissonance_pb_cap_omitted_reference_count': 0,
                'ordinary_missing_reference_blocked_count': 0,
                'tiers': [],
            },
        )
        run_summary['missing_reference_blocked_count'] = (
            int(run_summary['missing_reference_blocked_count']) + 1
        )
        if cap_omitted:
            run_summary['dissonance_pb_cap_omitted_reference_count'] = (
                int(run_summary['dissonance_pb_cap_omitted_reference_count']) + 1
            )
        else:
            run_summary['ordinary_missing_reference_blocked_count'] = (
                int(run_summary['ordinary_missing_reference_blocked_count']) + 1
            )
        tiers = list(run_summary.get('tiers') or [])
        tiers.append(int(row.get('tier') or 0))
        run_summary['tiers'] = tiers
        missing_references.append(
            {
                'tier': row.get('tier'),
                'tier_column': row.get('tier_column'),
                'dissonance_run_category': category,
                'label': row.get('label') or category,
                'reference_kind': row.get('reference_kind'),
                'reference_source': row.get('reference_source'),
                'reference_wave': row.get('reference_wave'),
                'reference_raw_wave': row.get('reference_raw_wave'),
                'reference_gap_reason': row.get('reference_gap_reason'),
                'dissonance_pb_cap_omitted_reference': cap_omitted,
                'dissonance_pb_cap_omission_context': dict(
                    row.get('dissonance_pb_cap_omission_context') or {}
                ),
                'best_calculated_selected_max_wave': row.get('best_calculated_selected_max_wave'),
                'unsupported_pressure_uncapped_selected_max_wave': row.get(
                    'unsupported_pressure_uncapped_selected_max_wave'
                ),
                'unsupported_terminal_pressures': list(row.get('unsupported_terminal_pressures') or []),
                'terminal_pressure_required_fields': list(
                    dict(row.get('terminal_pressure_runtime_override_status') or {}).get('required_fields') or []
                ),
                'terminal_pressure_missing_fields': list(
                    dict(row.get('terminal_pressure_runtime_override_status') or {}).get('missing_fields') or []
                ),
                'terminal_pressure_required_fields_by_pressure': dict(
                    dict(row.get('terminal_pressure_runtime_override_status') or {}).get('required_fields_by_pressure')
                    or {}
                ),
                'terminal_pressure_missing_fields_by_pressure': dict(
                    dict(row.get('terminal_pressure_runtime_override_status') or {}).get('missing_fields_by_pressure')
                    or {}
                ),
                'terminal_pressure_unmapped_pressures': list(
                    dict(row.get('terminal_pressure_runtime_override_status') or {}).get('unmapped_pressures') or []
                ),
            }
        )
    category_order = {'none': 0, 'attack': 1, 'defense': 2, 'utility': 3, 'ultimate_weapons': 4}
    return {
        'row_count': len(rows),
        'missing_reference_blocked_count': len(missing_rows),
        'ordinary_missing_reference_blocked_count': (
            len(missing_rows) - dissonance_pb_cap_omitted_reference_count
        ),
        'dissonance_pb_cap_omitted_reference_count': dissonance_pb_cap_omitted_reference_count,
        'by_reference_kind': dict(sorted(by_reference_kind.items())),
        'by_run_type': sorted(
            by_run_type.values(),
            key=lambda item: category_order.get(str(item.get('dissonance_run_category') or ''), 99),
        ),
        'missing_references': missing_references,
    }


def _boss_wave_terminal_pressure_reference_status(source: Mapping[str, object]) -> str | None:
    if bool(source.get('unsupported_pressure_missing_reference_blocked')):
        return 'missing_empirical_reference_blocked'
    if bool(source.get('unsupported_pressure_reference_limited')):
        return 'empirical_reference_limited'
    if bool(source.get('unsupported_pressure_reference_aligned')):
        return 'empirical_reference_aligned'
    blockers = {str(blocker) for blocker in list(source.get('model_completion_blockers') or [])}
    pressures = {str(pressure) for pressure in list(source.get('unsupported_terminal_pressures') or [])}
    if pressures and 'source_owned_non_boss_terminal_pressure_formulas' in blockers:
        return 'unsupported_pressure_open'
    return None


def _boss_wave_reference_quality_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    categories: dict[str, dict[str, object]] = {}
    rows_with_reference = 0
    calibration_candidate_count = 0
    low_wave_reference_count = 0
    pb_age_unknown_count = 0
    dissonance_pb_bonus_cap_count = 0
    rows_with_caveats = 0
    category_order = {'none': 0, 'attack': 1, 'defense': 2, 'utility': 3, 'ultimate_weapons': 4}
    for row in rows:
        category = str(row.get('dissonance_run_category') or 'none')
        group = categories.setdefault(
            category,
            {
                'dissonance_run_category': category,
                'label': row.get('label') or category,
                'row_count': 0,
                'rows_with_reference': 0,
                'calibration_candidate_count': 0,
                'low_wave_reference_count': 0,
                'pb_age_unknown_count': 0,
                'dissonance_pb_bonus_cap_count': 0,
                'rows_with_caveats': 0,
            },
        )
        group['row_count'] = int(group['row_count']) + 1
        reference = _extract_optional_wave_number(row.get('reference_wave'))
        if reference is None or reference <= 0:
            continue
        rows_with_reference += 1
        group['rows_with_reference'] = int(group['rows_with_reference']) + 1
        quality = dict(row.get('reference_quality') or {})
        if bool(quality.get('calibration_candidate')):
            calibration_candidate_count += 1
            group['calibration_candidate_count'] = int(group['calibration_candidate_count']) + 1
        if bool(quality.get('below_low_wave_threshold')):
            low_wave_reference_count += 1
            group['low_wave_reference_count'] = int(group['low_wave_reference_count']) + 1
        if quality.get('pb_age_status') == 'age_unknown_no_source_timestamp':
            pb_age_unknown_count += 1
            group['pb_age_unknown_count'] = int(group['pb_age_unknown_count']) + 1
        if bool(quality.get('dissonance_pb_bonus_cap_reached')):
            dissonance_pb_bonus_cap_count += 1
            group['dissonance_pb_bonus_cap_count'] = (
                int(group['dissonance_pb_bonus_cap_count']) + 1
            )
        if quality.get('caveats'):
            rows_with_caveats += 1
            group['rows_with_caveats'] = int(group['rows_with_caveats']) + 1
    return {
        'row_count': len(rows),
        'rows_with_reference': rows_with_reference,
        'calibration_candidate_count': calibration_candidate_count,
        'low_wave_threshold': _BOSS_WAVE_REFERENCE_VOLATILITY_THRESHOLD_WAVE,
        'low_wave_reference_count': low_wave_reference_count,
        'pb_age_unknown_count': pb_age_unknown_count,
        'dissonance_pb_bonus_cap_count': dissonance_pb_bonus_cap_count,
        'rows_with_caveats': rows_with_caveats,
        'by_run_type': sorted(
            categories.values(),
            key=lambda item: category_order.get(str(item.get('dissonance_run_category') or ''), 99),
        ),
    }


def _boss_wave_reference_alignment_base_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    categories: dict[str, dict[str, object]] = {}
    rows_with_delta: list[dict[str, object]] = []
    aligned_count = 0
    rows_with_reference = 0
    reference_nearest_lane_counts: dict[str, int] = {}
    for row in rows:
        category = str(row.get('dissonance_run_category') or 'none')
        category_summary = categories.setdefault(
            category,
            {
                'dissonance_run_category': category,
                'label': row.get('label') or category,
                'row_count': 0,
                'rows_with_reference': 0,
                'rows_with_calculated_delta': 0,
                'ids_reference_alignment_applied_count': 0,
                'raw_delta_over_reference_count': 0,
                'raw_delta_under_reference_count': 0,
                'raw_delta_match_count': 0,
                'max_abs_calculated_delta_wave': 0,
                'reference_nearest_lane_counts': {},
            },
        )
        category_summary['row_count'] = int(category_summary['row_count']) + 1
        if _extract_optional_wave_number(row.get('reference_wave')) is not None:
            rows_with_reference += 1
            category_summary['rows_with_reference'] = int(category_summary['rows_with_reference']) + 1
        nearest_lane = row.get('reference_nearest_lane')
        if nearest_lane:
            nearest_lane_key = str(nearest_lane)
            reference_nearest_lane_counts[nearest_lane_key] = (
                reference_nearest_lane_counts.get(nearest_lane_key, 0) + 1
            )
            category_counts = dict(category_summary.get('reference_nearest_lane_counts') or {})
            category_counts[nearest_lane_key] = int(category_counts.get(nearest_lane_key, 0)) + 1
            category_summary['reference_nearest_lane_counts'] = category_counts
        alignment = dict(row.get('ids_reference_alignment') or {})
        if bool(alignment.get('applied')):
            aligned_count += 1
            category_summary['ids_reference_alignment_applied_count'] = (
                int(category_summary['ids_reference_alignment_applied_count']) + 1
            )
        raw_delta = row.get('calculated_delta_vs_reference_wave')
        if raw_delta is None:
            continue
        delta = int(raw_delta)
        rows_with_delta.append(row)
        category_summary['rows_with_calculated_delta'] = int(category_summary['rows_with_calculated_delta']) + 1
        if delta > 0:
            category_summary['raw_delta_over_reference_count'] = int(category_summary['raw_delta_over_reference_count']) + 1
        elif delta < 0:
            category_summary['raw_delta_under_reference_count'] = int(category_summary['raw_delta_under_reference_count']) + 1
        else:
            category_summary['raw_delta_match_count'] = int(category_summary['raw_delta_match_count']) + 1
        category_summary['max_abs_calculated_delta_wave'] = max(
            int(category_summary['max_abs_calculated_delta_wave']),
            abs(delta),
        )

    over_count = sum(1 for row in rows_with_delta if int(row.get('calculated_delta_vs_reference_wave') or 0) > 0)
    under_count = sum(1 for row in rows_with_delta if int(row.get('calculated_delta_vs_reference_wave') or 0) < 0)
    match_count = len(rows_with_delta) - over_count - under_count
    worst_row = (
        max(rows_with_delta, key=lambda row: abs(int(row.get('calculated_delta_vs_reference_wave') or 0)))
        if rows_with_delta
        else None
    )
    worst_payload = None
    if worst_row is not None:
        worst_alignment = dict(worst_row.get('ids_reference_alignment') or {})
        worst_payload = {
            'tier': worst_row.get('tier'),
            'tier_column': worst_row.get('tier_column'),
            'dissonance_run_category': worst_row.get('dissonance_run_category'),
            'label': worst_row.get('label'),
            'reference_wave': worst_row.get('reference_wave'),
            'best_selected_max_wave': worst_row.get('best_selected_max_wave'),
            'best_calculated_selected_max_wave': worst_row.get('best_calculated_selected_max_wave'),
            'calculated_delta_vs_reference_wave': worst_row.get('calculated_delta_vs_reference_wave'),
            'calculated_to_reference_ratio': worst_row.get('calculated_to_reference_ratio'),
            'reference_nearest_lane': worst_row.get('reference_nearest_lane'),
            'reference_nearest_lane_label': worst_row.get('reference_nearest_lane_label'),
            'reference_nearest_lane_wave': worst_row.get('reference_nearest_lane_wave'),
            'reference_nearest_lane_delta_vs_reference_wave': worst_row.get(
                'reference_nearest_lane_delta_vs_reference_wave'
            ),
            'ids_reference_alignment_applied': bool(worst_alignment.get('applied')),
            'ids_reference_alignment_direction': worst_alignment.get('alignment_direction'),
        }
    category_order = {'none': 0, 'attack': 1, 'defense': 2, 'utility': 3, 'ultimate_weapons': 4}
    return {
        'row_count': len(rows),
        'rows_with_reference': rows_with_reference,
        'rows_with_calculated_delta': len(rows_with_delta),
        'ids_reference_alignment_applied_count': aligned_count,
        'raw_delta_over_reference_count': over_count,
        'raw_delta_under_reference_count': under_count,
        'raw_delta_match_count': match_count,
        'reference_nearest_lane_counts': dict(sorted(reference_nearest_lane_counts.items())),
        'max_abs_calculated_delta_wave': (
            abs(int(worst_row.get('calculated_delta_vs_reference_wave') or 0)) if worst_row is not None else 0
        ),
        'max_abs_calculated_delta_row': worst_payload,
        'by_run_type': sorted(
            categories.values(),
            key=lambda item: category_order.get(str(item.get('dissonance_run_category') or ''), 99),
        ),
    }


def _boss_wave_reference_alignment_calibration_subset(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    clean_rows: list[dict[str, object]] = []
    excluded_by_category: dict[str, dict[str, object]] = {}
    excluded_from_calibration_reference_count = 0
    excluded_caveated_reference_count = 0
    excluded_non_candidate_reference_count = 0
    category_order = {'none': 0, 'attack': 1, 'defense': 2, 'utility': 3, 'ultimate_weapons': 4}
    for row in rows:
        reference = _extract_optional_wave_number(row.get('reference_wave'))
        if reference is None:
            continue
        quality = dict(row.get('reference_quality') or {})
        caveats = list(quality.get('caveats') or [])
        calibration_candidate = bool(quality.get('calibration_candidate'))
        if calibration_candidate and not caveats:
            clean_rows.append(row)
            continue
        category = str(row.get('dissonance_run_category') or 'none')
        excluded = excluded_by_category.setdefault(
            category,
            {
                'dissonance_run_category': category,
                'label': row.get('label') or category,
                'excluded_from_calibration_reference_count': 0,
                'excluded_caveated_reference_count': 0,
                'excluded_non_candidate_reference_count': 0,
            },
        )
        excluded_from_calibration_reference_count += 1
        excluded['excluded_from_calibration_reference_count'] = (
            int(excluded['excluded_from_calibration_reference_count']) + 1
        )
        if caveats:
            excluded_caveated_reference_count += 1
            excluded['excluded_caveated_reference_count'] = (
                int(excluded['excluded_caveated_reference_count']) + 1
            )
        if not calibration_candidate:
            excluded_non_candidate_reference_count += 1
            excluded['excluded_non_candidate_reference_count'] = (
                int(excluded['excluded_non_candidate_reference_count']) + 1
            )

    summary = _boss_wave_reference_alignment_base_summary(clean_rows)
    summary['definition'] = 'calibration_candidate_with_no_reference_caveats'
    summary['excluded_from_calibration_reference_count'] = (
        excluded_from_calibration_reference_count
    )
    summary['excluded_caveated_reference_count'] = excluded_caveated_reference_count
    summary['excluded_non_candidate_reference_count'] = excluded_non_candidate_reference_count
    summary['excluded_by_run_type'] = sorted(
        excluded_by_category.values(),
        key=lambda item: category_order.get(str(item.get('dissonance_run_category') or ''), 99),
    )
    return summary


def _boss_wave_reference_alignment_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    summary = _boss_wave_reference_alignment_base_summary(rows)
    summary['calibration_reference_alignment'] = (
        _boss_wave_reference_alignment_calibration_subset(rows)
    )
    return summary


def _boss_wave_matrix_comparison_inputs_from_args(args) -> dict[str, float] | None:
    mapping = {
        'boss_wave_bridge_target_share': 'boss_edamage_target_share',
        'boss_wave_bridge_cadence_uptime': 'boss_edamage_cadence_uptime_factor',
        'boss_wave_bridge_reliability': 'boss_edamage_reliability_factor',
        'boss_wave_bridge_semantic_normalizer': 'boss_edamage_semantic_normalizer',
    }
    terminal_mapping = {
        'boss_wave_comparison_fleet_terminal_max_wave': 'fleet_terminal_max_wave',
        'boss_wave_comparison_elite_terminal_max_wave': 'elite_terminal_max_wave',
        'boss_wave_comparison_protector_terminal_max_wave': 'protector_terminal_max_wave',
        'boss_wave_comparison_armored_terminal_max_wave': 'armored_terminal_max_wave',
        'boss_wave_comparison_boss_terminal_max_wave': 'boss_terminal_max_wave',
    }
    values: dict[str, float] = {}
    for arg_name, runtime_name in mapping.items():
        value = float(getattr(args, arg_name, 0.0) or 0.0)
        if value > 0.0:
            values[runtime_name] = value
    pressure_factor = float(getattr(args, 'boss_wave_comparison_pressure_factor', 0.0) or 0.0)
    if pressure_factor > 0.0 and pressure_factor != 1.0:
        values['boss_wave_pressure_factor'] = pressure_factor
    for arg_name, runtime_name in terminal_mapping.items():
        value = float(getattr(args, arg_name, 0.0) or 0.0)
        if value > 0.0:
            values[runtime_name] = value
    return values or None


def _boss_wave_matrix_comparison_label_from_runtime_inputs(values: dict[str, object] | None) -> str:
    runtime_values = dict(values or {})
    has_bridge = any(
        float(runtime_values.get(runtime_name, 0.0) or 0.0) > 0.0
        for runtime_name in (
            'boss_edamage_target_share',
            'boss_edamage_cadence_uptime_factor',
            'boss_edamage_reliability_factor',
            'boss_edamage_semantic_normalizer',
        )
    )
    pressure_factor = float(runtime_values.get('boss_wave_pressure_factor', 0.0) or 0.0)
    has_pressure_factor = pressure_factor > 0.0 and pressure_factor != 1.0
    has_terminal_pressure = any(
        float(runtime_values.get(runtime_name, 0.0) or 0.0) > 0.0
        for runtime_name in (
            'fleet_terminal_max_wave',
            'elite_terminal_max_wave',
            'protector_terminal_max_wave',
            'armored_terminal_max_wave',
            'boss_terminal_max_wave',
        )
    )
    parts: list[str] = []
    if has_bridge:
        parts.append('bridge')
    if has_pressure_factor:
        parts.append('pressure_factor')
    if has_terminal_pressure:
        parts.append('terminal_pressure')
    if not parts:
        return 'bridge_assumptions'
    return f"{'_and_'.join(parts)}_assumptions"


def _boss_wave_matrix_comparison_label_from_args(args) -> str:
    return _boss_wave_matrix_comparison_label_from_runtime_inputs(
        _boss_wave_matrix_comparison_inputs_from_args(args)
    )


def _boss_wave_matrix_runtime_inputs_from_args(args) -> dict[str, float] | None:
    mapping = {
        'boss_wave_contact_time_seconds': 'boss_time_to_contact_seconds',
        'boss_wave_orb_boss_total_damage_pct': 'orb_boss_total_damage_pct',
        'boss_wave_pressure_factor': 'boss_wave_pressure_factor',
        'approve_boss_wave_pressure_factor_review_default': (
            'approve_boss_wave_pressure_factor_review_default'
        ),
        'approve_boss_wave_empirical_pressure_transform': (
            'approve_boss_wave_empirical_pressure_transform'
        ),
        'boss_wave_flame_bot_boss_hit_chance_pct': 'flame_bot_boss_hit_chance_pct',
        'boss_wave_flame_bot_damage_reduction_pct': 'flame_bot_damage_reduction_pct',
        'boss_wave_flame_bot_duration_seconds': 'flame_bot_duration_seconds',
        'boss_wave_flame_bot_cooldown_seconds': 'flame_bot_cooldown_seconds',
        'boss_wave_fleet_terminal_max_wave': 'fleet_terminal_max_wave',
        'boss_wave_elite_terminal_max_wave': 'elite_terminal_max_wave',
        'boss_wave_protector_terminal_max_wave': 'protector_terminal_max_wave',
        'boss_wave_armored_terminal_max_wave': 'armored_terminal_max_wave',
        'boss_wave_boss_terminal_max_wave': 'boss_terminal_max_wave',
    }
    values: dict[str, float] = {}
    for arg_name, runtime_name in mapping.items():
        raw_value = getattr(args, arg_name, None)
        if raw_value is None:
            continue
        value = float(raw_value)
        if value > 0.0:
            values[runtime_name] = value
    return values or None


def _boss_wave_matrix_tiers_from_args(args) -> tuple[int, ...]:
    tier = getattr(args, 'tier', None)
    if tier is None:
        return tuple(BOSS_WAVE_MILESTONE_MATRIX_TIERS)
    return (int(tier),)


def _boss_wave_matrix_dissonance_categories_from_args(args) -> tuple[str, ...]:
    raw_category = getattr(args, 'dissonance_run_category', None)
    if raw_category is None:
        return _BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES
    category = _normalize_boss_wave_dissonance_run_category(raw_category)
    if category == 'none':
        return _BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES
    return (category,)


def _boss_wave_matrix_comparison_calculated_delta_summary(
    comparison_rows: list[dict[str, object]],
) -> dict[str, object]:
    by_category: dict[str, dict[str, object]] = {}
    entries: list[dict[str, object]] = []
    for row_raw in comparison_rows:
        row = dict(row_raw)
        tier = row.get('tier')
        tier_column = row.get('tier_column') or (f"Tier {tier}" if tier is not None else '')
        for key, raw_delta in row.items():
            if not str(key).endswith('_calculated_delta_wave') or raw_delta is None:
                continue
            category_key = str(key)[: -len('_calculated_delta_wave')]
            category = 'none' if category_key == 'regular' else category_key
            label = _BOSS_WAVE_DISSONANCE_RUN_LABELS.get(category, str(category))
            try:
                delta = int(raw_delta)
            except (TypeError, ValueError):
                continue
            default_calculated_wave = row.get(f'{category_key}_default_calculated_wave')
            comparison_calculated_wave = row.get(f'{category_key}_comparison_calculated_wave')
            entry = {
                'tier': tier,
                'tier_column': tier_column,
                'dissonance_run_category': category,
                'label': label,
                'default_selected_wave': row.get(f'{category_key}_default_wave'),
                'comparison_selected_wave': row.get(f'{category_key}_comparison_wave'),
                'selected_delta_wave': row.get(f'{category_key}_delta_wave'),
                'default_calculated_wave': default_calculated_wave,
                'comparison_calculated_wave': comparison_calculated_wave,
                'calculated_delta_wave': delta,
                'default_calculated_delta_vs_reference_wave': row.get(
                    f'{category_key}_default_calculated_delta_vs_reference_wave'
                ),
                'comparison_calculated_delta_vs_reference_wave': row.get(
                    f'{category_key}_comparison_calculated_delta_vs_reference_wave'
                ),
                'default_calculated_to_reference_ratio': row.get(
                    f'{category_key}_default_calculated_to_reference_ratio'
                ),
                'comparison_calculated_to_reference_ratio': row.get(
                    f'{category_key}_comparison_calculated_to_reference_ratio'
                ),
            }
            entries.append(entry)
            category_summary = by_category.setdefault(
                category,
                {
                    'dissonance_run_category': category,
                    'label': label,
                    'row_count': 0,
                    'comparison_raw_wave_higher_count': 0,
                    'comparison_raw_wave_lower_count': 0,
                    'comparison_raw_wave_match_count': 0,
                    'max_abs_calculated_delta_wave': 0,
                },
            )
            category_summary['row_count'] = int(category_summary['row_count']) + 1
            if delta > 0:
                category_summary['comparison_raw_wave_higher_count'] = (
                    int(category_summary['comparison_raw_wave_higher_count']) + 1
                )
            elif delta < 0:
                category_summary['comparison_raw_wave_lower_count'] = (
                    int(category_summary['comparison_raw_wave_lower_count']) + 1
                )
            else:
                category_summary['comparison_raw_wave_match_count'] = (
                    int(category_summary['comparison_raw_wave_match_count']) + 1
                )
            category_summary['max_abs_calculated_delta_wave'] = max(
                int(category_summary['max_abs_calculated_delta_wave']),
                abs(delta),
            )
    worst_entry = max(entries, key=lambda item: abs(int(item.get('calculated_delta_wave') or 0)), default=None)
    return {
        'row_count': len(entries),
        'comparison_raw_wave_higher_count': sum(
            1 for entry in entries if int(entry.get('calculated_delta_wave') or 0) > 0
        ),
        'comparison_raw_wave_lower_count': sum(
            1 for entry in entries if int(entry.get('calculated_delta_wave') or 0) < 0
        ),
        'comparison_raw_wave_match_count': sum(
            1 for entry in entries if int(entry.get('calculated_delta_wave') or 0) == 0
        ),
        'max_abs_calculated_delta_wave': (
            abs(int(worst_entry.get('calculated_delta_wave') or 0)) if worst_entry else 0
        ),
        'max_abs_calculated_delta_row': dict(worst_entry) if worst_entry else {},
        'by_run_type': list(by_category.values()),
    }


def _boss_wave_milestone_matrix_diagnostics_payload(matrix_payload: dict[str, object]) -> dict[str, object]:
    comparison = dict(matrix_payload.get('comparison') or {})
    comparison_matrix = dict(comparison.get('matrix') or {})
    comparison_contract = dict(comparison_matrix.get('contract') or {})
    comparison_certification = dict(
        comparison_matrix.get('model_certification')
        or comparison_contract.get('model_certification')
        or {}
    )
    contract = dict(matrix_payload.get('contract') or {})
    certification = dict(matrix_payload.get('model_certification') or contract.get('model_certification') or {})
    rows = [dict(row) for row in matrix_payload.get('rows') or []]
    payload: dict[str, object] = {
        'enabled': True,
        'artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
        'model_scope': (
            matrix_payload.get('model_scope')
            or contract.get('model_scope')
            or certification.get('certified_scope')
        ),
        'not_full_max_wave_model': bool(
            matrix_payload.get('not_full_max_wave_model')
            if matrix_payload.get('not_full_max_wave_model') is not None
            else contract.get('not_full_max_wave_model')
        ),
        'model_certification_status': certification.get('model_certification_status'),
        'model_closure_status': certification.get('model_closure_status'),
        'certified_full_max_wave_model': bool(certification.get('certified_full_max_wave_model')),
        'model_certification': certification,
        'model_completion_blockers': list(certification.get('model_completion_blockers') or []),
        'accepted_approximation_closure': dict(
            certification.get('accepted_approximation_closure') or {}
        ),
        'runtime_override_closure': dict(certification.get('runtime_override_closure') or {}),
        'effective_model_closure': dict(certification.get('effective_model_closure') or {}),
        'terminal_pressure_runtime_override_status': dict(
            certification.get('terminal_pressure_runtime_override_status') or {}
        ),
        'non_boss_terminal_pressure_closure': dict(
            certification.get('non_boss_terminal_pressure_closure') or {}
        ),
        'model_blocker_summary': (
            matrix_payload.get('model_blocker_summary')
            or _boss_wave_matrix_blocker_summary(rows)
        ),
        'model_accuracy_summary': matrix_payload.get('model_accuracy_summary') or {},
        'approved_pressure_factor_review_default': dict(
            matrix_payload.get('approved_pressure_factor_review_default') or {}
        ),
        'tracker_reference_evidence': (
            matrix_payload.get('tracker_reference_evidence')
            or {
                'status': 'not_supplied',
                'application': 'external_observation_not_account_truth',
                'certification_effect': 'none',
            }
        ),
        'tier_count': len(matrix_payload.get('tiers') or []),
        'row_count': len(rows),
        'wide_row_count': len(matrix_payload.get('wide_rows') or []),
        'selection_policy': contract.get('selection_policy'),
        'ids_reference_alignment_enabled': bool(matrix_payload.get('ids_reference_alignment_enabled')),
        'scenario_runtime_inputs': matrix_payload.get('scenario_runtime_inputs'),
        'reference_alignment_summary': matrix_payload.get('reference_alignment_summary') or {},
        'reference_quality_summary': matrix_payload.get('reference_quality_summary') or {},
        'pressure_factor_hint_summary': matrix_payload.get('pressure_factor_hint_summary') or {},
        'reference_gap_summary': matrix_payload.get('reference_gap_summary') or {},
        'replacement_primitive_family_coverage_summary': (
            matrix_payload.get('replacement_primitive_family_coverage_summary') or {}
        ),
        'comparison_enabled': bool(comparison),
    }
    if comparison:
        comparison_not_full = comparison_matrix.get('not_full_max_wave_model')
        if comparison_not_full is None:
            comparison_not_full = comparison_contract.get('not_full_max_wave_model')
        payload.update(
            {
                'comparison_label': comparison.get('label'),
                'comparison_scenario_runtime_inputs': comparison.get('scenario_runtime_inputs') or {},
                'comparison_runtime_input_overrides': comparison.get('runtime_input_overrides') or {},
                'comparison_base_scenario_runtime_inputs': (
                    comparison.get('base_scenario_runtime_inputs') or {}
                ),
                'comparison_row_count': len(comparison.get('wide_rows') or []),
                'comparison_matrix_row_count': len(comparison_matrix.get('rows') or []),
                'comparison_matrix_wide_row_count': len(comparison_matrix.get('wide_rows') or []),
                'comparison_model_scope': (
                    comparison_matrix.get('model_scope')
                    or comparison_contract.get('model_scope')
                    or comparison_certification.get('certified_scope')
                ),
                'comparison_not_full_max_wave_model': bool(comparison_not_full),
                'comparison_model_certification_status': comparison_certification.get(
                    'model_certification_status'
                ),
                'comparison_model_closure_status': comparison_certification.get(
                    'model_closure_status'
                ),
                'comparison_certified_full_max_wave_model': bool(
                    comparison_certification.get('certified_full_max_wave_model')
                ),
                'comparison_model_certification': comparison_certification,
                'comparison_model_completion_blockers': list(
                    comparison_certification.get('model_completion_blockers') or []
                ),
                'comparison_accepted_approximation_closure': dict(
                    comparison_certification.get('accepted_approximation_closure') or {}
                ),
                'comparison_runtime_override_closure': dict(
                    comparison_certification.get('runtime_override_closure') or {}
                ),
                'comparison_effective_model_closure': dict(
                    comparison_certification.get('effective_model_closure') or {}
                ),
                'comparison_terminal_pressure_runtime_override_status': dict(
                    comparison_certification.get('terminal_pressure_runtime_override_status') or {}
                ),
                'comparison_non_boss_terminal_pressure_closure': dict(
                    comparison_certification.get('non_boss_terminal_pressure_closure') or {}
                ),
                'comparison_model_blocker_summary': (
                    comparison_matrix.get('model_blocker_summary')
                    or _boss_wave_matrix_blocker_summary(
                        [dict(row) for row in comparison_matrix.get('rows') or []]
                    )
                ),
                'comparison_model_accuracy_summary': (
                    comparison_matrix.get('model_accuracy_summary') or {}
                ),
                'comparison_pressure_factor_hint_summary': (
                    comparison_matrix.get('pressure_factor_hint_summary') or {}
                ),
                'comparison_reference_gap_summary': (
                    comparison_matrix.get('reference_gap_summary') or {}
                ),
                'comparison_reference_alignment_summary': (
                    comparison_matrix.get('reference_alignment_summary') or {}
                ),
                'comparison_reference_quality_summary': (
                    comparison_matrix.get('reference_quality_summary') or {}
                ),
                'comparison_replacement_primitive_family_coverage_summary': (
                    comparison_matrix.get('replacement_primitive_family_coverage_summary') or {}
                ),
                'comparison_calculated_delta_summary': (
                    comparison.get('calculated_delta_summary')
                    or _boss_wave_matrix_comparison_calculated_delta_summary(
                        [dict(row) for row in comparison.get('wide_rows') or []]
                    )
                ),
            }
        )
    return payload


_CURRENT_SCOPE_EFFECT_FAMILY_ROUTE_KEYS: dict[str, tuple[str, ...]] = {
    'bot': ('bot',),
    'card_base': ('card',),
    'card_mastery': ('card',),
    'workshop': ('workshop',),
    'enhancement': ('enhancement',),
    'module': ('module', 'module_substat'),
    'relic': ('relic',),
}


_CURRENT_SCOPE_EFFECT_FAMILY_GENERATED_KEYS: dict[str, tuple[str, ...]] = {
    'bot': ('bot',),
    'card_base': ('card',),
    'card_mastery': ('card',),
    'workshop': ('workshop',),
    'enhancement': ('enhancement',),
    'module': ('module', 'module_substat'),
    'relic': ('relic',),
}


_CURRENT_SCOPE_EFFECT_FAMILY_STATBOOK_SOURCE_FAMILIES: dict[str, tuple[str, ...]] = {
    'bot': ('bot',),
    'card_base': ('card',),
    'card_mastery': ('lab', 'card'),
    'workshop': ('workshop',),
    'enhancement': ('enhancement',),
    'module': ('module', 'module_substat'),
    'relic': ('relic',),
}


_CURRENT_SCOPE_EFFECT_FAMILY_PASSING_VERDICTS = {'pass', 'pass_with_compare_limitations'}
_CURRENT_SCOPE_EFFECT_ROUTE_CLOSURE_LEDGER = (
    ROOT / 'kb' / 'ledgers' / 'tables' / 'contributor-routing-closure.csv'
)
_CURRENT_SCOPE_MODULE_UNIQUE_RUNTIME_CATALOG = (
    ROOT / 'kb' / 'modules' / 'contracts' / 'module-unique-runtime-catalog.csv'
)


def _current_scope_slug_text(value: object) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')


def _current_scope_effect_route_rows_by_source_family() -> dict[str, list[dict[str, str]]]:
    with _CURRENT_SCOPE_EFFECT_ROUTE_CLOSURE_LEDGER.open(encoding='utf-8', newline='') as handle:
        rows_by_family: dict[str, list[dict[str, str]]] = {}
        for row in csv.DictReader(handle):
            source_family = str(row.get('source_family') or '').strip()
            if not source_family:
                continue
            rows_by_family.setdefault(source_family, []).append(
                {
                    'source_family': source_family,
                    'contributor_id': str(row.get('contributor_id') or '').strip(),
                    'destination_object_type': str(row.get('destination_object_type') or '').strip(),
                    'destination_id': str(row.get('destination_id') or '').strip(),
                    'registration_status': str(row.get('registration_status') or '').strip(),
                }
            )
    return rows_by_family


def _current_scope_effect_statbook_visibility_index(
    statbook_dict: Mapping[str, object] | None,
) -> dict[str, object]:
    rows = dict((statbook_dict or {}).get('rows') or {}) if isinstance(statbook_dict, Mapping) else {}
    if not rows:
        return {
            'status': 'not_evaluated',
            'reason': 'statbook_not_supplied',
            'surface_ids': set(),
            'contributor_ids': set(),
            'surface_rows': {},
        }
    contributor_ids: set[str] = set()
    for row in rows.values():
        for contributor in dict(row or {}).get('contributors') or ():
            contributor_id = str(dict(contributor or {}).get('contributor_id') or '').strip()
            if contributor_id:
                contributor_ids.add(contributor_id)
    return {
        'status': 'evaluated',
        'surface_ids': {str(surface_id) for surface_id in rows},
        'contributor_ids': contributor_ids,
        'surface_rows': {str(surface_id): dict(row or {}) for surface_id, row in rows.items()},
    }


def _current_scope_query_book_visibility_index(
    query_rows_start_of_run: Mapping[str, object] | None = None,
    query_rows_max_progression: Mapping[str, object] | None = None,
) -> dict[str, object]:
    books_by_state_mode = {
        'start_of_run': query_rows_start_of_run,
        'max_progression': query_rows_max_progression,
    }
    surface_rows: dict[str, list[dict[str, object]]] = {}
    book_count = 0
    for state_mode, books_payload in books_by_state_mode.items():
        if not isinstance(books_payload, Mapping):
            continue
        for preset_name, book_payload in dict(books_payload or {}).items():
            if not isinstance(book_payload, Mapping):
                continue
            rows = dict(book_payload.get('rows') or {})
            if not rows:
                continue
            book_count += 1
            for raw_surface_id, raw_row in rows.items():
                surface_id = normalize_surface_id_to_contract(str(raw_surface_id))
                row = dict(raw_row or {})
                surface_rows.setdefault(surface_id, []).append(
                    {
                        'preset': str(preset_name),
                        'state_mode': state_mode,
                        'surface_id': surface_id,
                        'status': str(row.get('status') or ''),
                        'final_value': row.get('final_value'),
                        'value_type': row.get('value_type'),
                    }
                )
    return {
        'status': 'evaluated' if book_count else 'not_evaluated',
        'book_count': book_count,
        'surface_rows': surface_rows,
        'surface_ids': set(surface_rows),
    }


def _current_scope_query_book_surface_evidence(
    query_book_visibility_index: Mapping[str, object],
    destination_surface_id: str,
) -> dict[str, object]:
    if str(query_book_visibility_index.get('status') or '') != 'evaluated':
        return {'status': 'not_evaluated', 'entries': []}
    surface_rows = dict(query_book_visibility_index.get('surface_rows') or {})
    direct_surface_id = normalize_surface_id_to_contract(destination_surface_id)
    materialized_surface_id = materialized_surface_id_for_contract(direct_surface_id)
    query_evidence_surface_id = query_evidence_surface_id_for_contract(direct_surface_id)
    entries = [dict(row or {}) for row in surface_rows.get(direct_surface_id, ())]
    materialized_entries: list[dict[str, object]] = []
    if materialized_surface_id != direct_surface_id:
        materialized_entries = [
            dict(row or {})
            for row in surface_rows.get(materialized_surface_id, ())
        ]
        entries.extend(materialized_entries)
    equivalent_entries: list[dict[str, object]] = []
    if query_evidence_surface_id not in {direct_surface_id, materialized_surface_id}:
        equivalent_entries = [
            dict(row or {})
            for row in surface_rows.get(query_evidence_surface_id, ())
        ]
        entries.extend(equivalent_entries)
    resolved_presets = sorted(
        {
            str(entry.get('preset'))
            for entry in entries
            if str(entry.get('status') or '') == 'resolved' and entry.get('preset')
        }
    )
    gated_presets = sorted(
        {
            str(entry.get('preset'))
            for entry in entries
            if str(entry.get('status') or '') == 'gated_off' and entry.get('preset')
        }
    )
    visible_presets = sorted(
        {
            str(entry.get('preset'))
            for entry in entries
            if entry.get('preset')
        }
    )
    return {
        'status': 'evaluated',
        'destination_surface_id': direct_surface_id,
        'materialized_surface_id': materialized_surface_id,
        'query_evidence_surface_id': query_evidence_surface_id,
        'entry_count': len(entries),
        'direct_entry_count': len(entries) - len(materialized_entries) - len(equivalent_entries),
        'materialized_entry_count': len(materialized_entries),
        'equivalent_entry_count': len(equivalent_entries),
        'visible_query_presets': visible_presets,
        'resolved_query_presets': resolved_presets,
        'gated_query_presets': gated_presets,
        'entries': entries[:12],
    }


def _current_scope_module_unique_catalog() -> dict[str, dict[str, str]]:
    with _CURRENT_SCOPE_MODULE_UNIQUE_RUNTIME_CATALOG.open(encoding='utf-8', newline='') as handle:
        return {
            _current_scope_slug_text(row.get('module_name')): {
                str(key): str(value or '')
                for key, value in dict(row or {}).items()
            }
            for row in csv.DictReader(handle)
            if _current_scope_slug_text(row.get('module_name'))
        }


def _current_scope_module_payload_context(
    module_card_payloads: Mapping[str, object] | None,
    *,
    selected_preset: str | None = None,
) -> dict[str, object]:
    active_modules: dict[str, list[str]] = {}
    selected_modules: dict[str, list[str]] = {}
    presets = dict((module_card_payloads or {}).get('presets') or {}) if isinstance(module_card_payloads, Mapping) else {}
    for preset_name, slots_payload in presets.items():
        for slot_name, roles_payload in dict(slots_payload or {}).items():
            for role_name, module_payload in dict(roles_payload or {}).items():
                if not isinstance(module_payload, Mapping):
                    continue
                module_slug = _current_scope_slug_text(module_payload.get('module_name'))
                if not module_slug:
                    continue
                location = f'{preset_name}:{slot_name}:{role_name}'
                active_modules.setdefault(module_slug, []).append(location)
                if selected_preset and str(preset_name) == str(selected_preset):
                    selected_modules.setdefault(module_slug, []).append(location)
    return {
        'status': 'evaluated' if presets else 'not_supplied',
        'active_module_slugs': active_modules,
        'selected_preset': selected_preset,
        'selected_module_slugs': selected_modules,
    }


def _current_scope_route_gap_classification(
    row: Mapping[str, object],
    *,
    module_catalog: Mapping[str, Mapping[str, str]],
    module_payload_context: Mapping[str, object],
    statbook_visibility_index: Mapping[str, object],
    query_book_visibility_index: Mapping[str, object],
) -> dict[str, object]:
    contributor_id = str(row.get('contributor_id') or '')
    source_family = str(row.get('source_family') or '')
    destination_id = str(row.get('destination_id') or '')
    destination_object_type = str(row.get('destination_object_type') or '')
    active_module_slugs = dict(module_payload_context.get('active_module_slugs') or {})
    selected_module_slugs = dict(module_payload_context.get('selected_module_slugs') or {})
    selected_preset = str(module_payload_context.get('selected_preset') or '')
    if source_family == 'module' and destination_id.startswith('module.'):
        parts = destination_id.split('.')
        module_slug = parts[1] if len(parts) > 2 else ''
        catalog_row = dict(module_catalog.get(module_slug) or {})
        active_locations = sorted(str(location) for location in active_module_slugs.get(module_slug, ()))
        selected_locations = sorted(str(location) for location in selected_module_slugs.get(module_slug, ()))
        destination_surface_id = normalize_surface_id_to_contract(f'{destination_object_type}::{destination_id}')
        query_book_evidence = _current_scope_query_book_surface_evidence(
            query_book_visibility_index,
            destination_surface_id,
        )
        if selected_locations:
            status = 'selected_preset_module_card_payload_visible_statbook_route_missing'
            reason = 'selected-preset module unique appears in module_card_payloads but route destination is not a current statbook row'
        elif active_locations:
            if int(query_book_evidence.get('entry_count') or 0) > 0:
                status = 'other_preset_module_card_payload_visible_in_query_books'
                reason = (
                    'module unique appears in module_card_payloads for another preset and is visible in '
                    'the committed preset query books; current statbook remains selected-preset scoped'
                )
            else:
                status = 'other_preset_module_card_payload_not_in_committed_query_books'
                reason = (
                    'module unique appears in module_card_payloads for another preset, but no committed '
                    'preset query book currently exposes the route destination'
                )
        elif catalog_row:
            status = 'inactive_module_unique_registered_not_current_account_route'
            reason = 'module unique is registered in KB catalog but no current preset primary/assist module uses it'
        else:
            status = 'unclassified_module_route_gap'
            reason = 'module route destination did not match module unique runtime catalog'
        return {
            'status': status,
            'reason': reason,
            'module_slug': module_slug,
            'module_name': catalog_row.get('module_name') or module_slug,
            'active_module_locations': active_locations,
            'selected_preset': selected_preset or None,
            'selected_module_locations': selected_locations,
            'query_book_visibility': query_book_evidence,
            'runtime_catalog_trigger': catalog_row.get('trigger'),
            'runtime_catalog_target': catalog_row.get('target'),
            'runtime_catalog_confidence': catalog_row.get('rule_confidence'),
        }
    if source_family == 'card' and destination_object_type == 'capability':
        surface_rows = dict(statbook_visibility_index.get('surface_rows') or {})
        parts = destination_id.split('.')
        card_slug = parts[1] if len(parts) >= 3 and parts[0] == 'capability' else ''
        card_surface_prefix = f'state::cards.{card_slug}.'
        related_card_rows = {
            str(surface_id): dict(surface_row or {})
            for surface_id, surface_row in surface_rows.items()
            if str(surface_id).startswith(card_surface_prefix)
        }
        resolved_related_rows = {
            surface_id: surface_row
            for surface_id, surface_row in related_card_rows.items()
            if str(surface_row.get('status') or '') == 'resolved'
            and bool(surface_row.get('publishable') is not False)
        }
        gated_related_rows = {
            surface_id: surface_row
            for surface_id, surface_row in related_card_rows.items()
            if str(surface_row.get('status') or '') == 'gated_off'
        }
        if resolved_related_rows:
            return {
                'status': 'active_card_capability_route_missing_boolean_surface',
                'reason': (
                    'card has a resolved current statbook runtime surface, but the registered '
                    'capability boolean route is not visible in the current statbook'
                ),
                'card_slug': card_slug,
                'resolved_related_surfaces': sorted(resolved_related_rows)[:8],
                'gated_related_surfaces': sorted(gated_related_rows)[:8],
            }
        if gated_related_rows:
            return {
                'status': 'inactive_card_capability_route_gated_off_current_statbook',
                'reason': (
                    'card capability route is registered, but current statbook evidence only has '
                    'gated-off related card surfaces for the selected preset/account state'
                ),
                'card_slug': card_slug,
                'resolved_related_surfaces': [],
                'gated_related_surfaces': sorted(gated_related_rows)[:8],
            }
        return {
            'status': 'card_capability_route_split_to_runtime_effect_or_combat_exception',
            'reason': (
                'card capability route is registered, while current statbook/Boss Waves evidence '
                'uses runtime effect, mastery, or combat exception surfaces rather than this boolean surface'
            ),
        }
    return {
        'status': 'unclassified_route_visibility_gap',
        'reason': 'registered route is not visible as current statbook contributor or destination surface',
    }


def _current_scope_effect_individual_route_evidence(
    *,
    family: str,
    route_source_family_ids: Sequence[str],
    route_rows_by_source_family: Mapping[str, Sequence[Mapping[str, str]]],
    statbook_visibility_index: Mapping[str, object],
    query_book_visibility_index: Mapping[str, object],
    module_catalog: Mapping[str, Mapping[str, str]],
    module_payload_context: Mapping[str, object],
) -> dict[str, object]:
    route_rows = [
        dict(row)
        for source_family in route_source_family_ids
        for row in route_rows_by_source_family.get(source_family, ())
    ]
    status_counts = Counter(str(row.get('registration_status') or '') for row in route_rows)
    destination_keys = {
        (
            str(row.get('destination_object_type') or ''),
            str(row.get('destination_id') or ''),
        )
        for row in route_rows
        if row.get('destination_object_type') and row.get('destination_id')
    }
    unregistered = sorted(
        str(row.get('contributor_id') or '')
        for row in route_rows
        if str(row.get('registration_status') or '') != 'registered'
    )
    statbook_visibility_status = str(statbook_visibility_index.get('status') or '')
    visible_surface_ids = {
        str(surface_id) for surface_id in (statbook_visibility_index.get('surface_ids') or set())
    }
    visible_contributor_ids = {
        str(contributor_id)
        for contributor_id in (statbook_visibility_index.get('contributor_ids') or set())
    }
    visibility_mode_counts: Counter[str] = Counter()
    gap_classification_counts: Counter[str] = Counter()
    not_visible_examples: list[dict[str, object]] = []
    not_visible_classified_examples: list[dict[str, object]] = []
    destination_surface_examples: list[dict[str, object]] = []
    exact_contributor_examples: list[dict[str, object]] = []
    if statbook_visibility_status == 'evaluated':
        for row in route_rows:
            contributor_id = str(row.get('contributor_id') or '')
            destination_surface_id = normalize_surface_id_to_contract(
                f"{row.get('destination_object_type')}::{row.get('destination_id')}"
            )
            example = {
                'contributor_id': contributor_id,
                'destination_surface_id': destination_surface_id,
            }
            if contributor_id in visible_contributor_ids:
                visibility_mode = 'exact_statbook_contributor'
                if len(exact_contributor_examples) < 12:
                    exact_contributor_examples.append(example)
            elif destination_surface_id in visible_surface_ids:
                visibility_mode = 'destination_surface_visible'
                if len(destination_surface_examples) < 12:
                    destination_surface_examples.append(example)
            else:
                visibility_mode = 'not_visible_in_current_statbook'
                gap_classification = _current_scope_route_gap_classification(
                    row,
                    module_catalog=module_catalog,
                    module_payload_context=module_payload_context,
                    statbook_visibility_index=statbook_visibility_index,
                    query_book_visibility_index=query_book_visibility_index,
                )
                gap_classification_counts[
                    str(gap_classification.get('status') or 'unclassified_route_visibility_gap')
                ] += 1
                if len(not_visible_examples) < 24:
                    not_visible_examples.append(
                        {
                            **example,
                            'destination_object_type': str(row.get('destination_object_type') or ''),
                            'destination_id': str(row.get('destination_id') or ''),
                        }
                    )
                if len(not_visible_classified_examples) < 24:
                    not_visible_classified_examples.append(
                        {
                            **example,
                            'destination_object_type': str(row.get('destination_object_type') or ''),
                            'destination_id': str(row.get('destination_id') or ''),
                            'classification': gap_classification,
                        }
                    )
            visibility_mode_counts[visibility_mode] += 1
        statbook_route_visibility = (
            'covered'
            if route_rows and not visibility_mode_counts.get('not_visible_in_current_statbook')
            else 'partial'
        )
    else:
        statbook_route_visibility = 'not_evaluated'
    return {
        'status': 'closed' if route_rows and not unregistered else 'needs_work',
        'family': str(family),
        'ledger': 'kb/ledgers/tables/contributor-routing-closure.csv',
        'source_families': list(route_source_family_ids),
        'route_contributor_count': len(route_rows),
        'registered_route_contributor_count': int(status_counts.get('registered') or 0),
        'unregistered_route_contributor_count': len(unregistered),
        'registration_status_counts': dict(sorted(status_counts.items())),
        'destination_count': len(destination_keys),
        'destination_object_type_counts': dict(
            sorted(Counter(str(row.get('destination_object_type') or '') for row in route_rows).items())
        ),
        'contributor_id_examples': sorted(
            str(row.get('contributor_id') or '')
            for row in route_rows
            if row.get('contributor_id')
        )[:12],
        'unregistered_contributor_ids': unregistered[:24],
        'statbook_route_visibility_status': statbook_route_visibility,
        'statbook_route_visibility_mode_counts': dict(sorted(visibility_mode_counts.items())),
        'not_visible_route_classification_counts': dict(sorted(gap_classification_counts.items())),
        'statbook_exact_contributor_examples': exact_contributor_examples,
        'statbook_destination_surface_examples': destination_surface_examples,
        'statbook_not_visible_examples': not_visible_examples,
        'statbook_not_visible_classified_examples': not_visible_classified_examples,
    }


def _current_scope_card_mastery_statbook_evidence(
    surface_id: str,
    statbook_row: Mapping[str, object],
    contributor: Mapping[str, object],
) -> bool:
    text = ' '.join(
        str(value or '').strip().lower()
        for value in (
            surface_id,
            statbook_row.get('notes'),
            contributor.get('stat_name'),
            contributor.get('source_name'),
            contributor.get('destination_id'),
            contributor.get('provenance'),
            contributor.get('notes'),
            contributor.get('contributor_id'),
        )
        if value is not None
    )
    return (
        str(surface_id).startswith('state::cards.')
        and str(surface_id).endswith('.mastery_effect')
    ) or (
        'card-masteries.csv' in text
        or 'kb_card_mastery' in text
        or '.mastery_effect' in text
        or ' mastery' in text
    )


def _current_scope_effect_family_statbook_contributors(
    *,
    family: str,
    surface_id: str,
    statbook_row: Mapping[str, object],
) -> tuple[list[dict[str, object]], str]:
    contributors = [dict(contributor or {}) for contributor in (statbook_row.get('contributors') or [])]
    if family == 'card_base':
        return [
            contributor
            for contributor in contributors
            if str(contributor.get('source_family') or '') == 'card'
            and not _current_scope_card_mastery_statbook_evidence(surface_id, statbook_row, contributor)
        ], 'active_card_base_runtime_contributors'
    if family == 'card_mastery':
        return [
            contributor
            for contributor in contributors
            if _current_scope_card_mastery_statbook_evidence(surface_id, statbook_row, contributor)
        ], 'card_mastery_registry_and_applied_runtime_surfaces'

    source_families = _CURRENT_SCOPE_EFFECT_FAMILY_STATBOOK_SOURCE_FAMILIES.get(family, (family,))
    source_family_set = {str(item) for item in source_families}
    return [
        contributor
        for contributor in contributors
        if str(contributor.get('source_family') or '') in source_family_set
    ], 'source_family_contributors'


def _current_scope_effect_family_line_verification_summary(
    *,
    statbook_dict: dict[str, object] | None,
    line_verification: dict[str, object] | None,
) -> dict[str, object]:
    if statbook_dict is None or line_verification is None:
        return {
            'status': 'not_evaluated',
            'reason': 'statbook_or_line_verification_not_supplied',
            'statbook_artifact': 'statbook_publishable.json',
            'line_verification_artifact': 'line_by_line_verification.json',
            'families': {},
        }

    statbook_rows = dict((statbook_dict or {}).get('rows') or {})
    verification_rows = dict(line_verification or {})
    families: dict[str, dict[str, object]] = {}
    missing_statbook_families: list[str] = []
    missing_line_verification_families: list[str] = []
    unmapped_statbook_contributor_families: list[str] = []
    unknown_value_type_families: list[str] = []
    non_pass_verdict_families: list[str] = []
    issue_families: list[str] = []

    for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS:
        source_families = _CURRENT_SCOPE_EFFECT_FAMILY_STATBOOK_SOURCE_FAMILIES.get(family, (family,))
        surface_ids: set[str] = set()
        source_family_counts: Counter[str] = Counter()
        contributor_count = 0
        kb_mapped_contributor_count = 0
        unmapped_contributor_count = 0
        unmapped_examples: list[dict[str, object]] = []
        selection_mode = 'source_family_contributors'

        for surface_id, raw_row in statbook_rows.items():
            row = dict(raw_row or {})
            matching_contributors, selection_mode = _current_scope_effect_family_statbook_contributors(
                family=family,
                surface_id=str(surface_id),
                statbook_row=row,
            )
            if not matching_contributors:
                continue
            normalized_surface_id = str(surface_id)
            surface_ids.add(normalized_surface_id)
            for contributor in matching_contributors:
                contributor_count += 1
                source_family_counts[str(contributor.get('source_family') or '')] += 1
                if contributor.get('kb_mapped') is True:
                    kb_mapped_contributor_count += 1
                else:
                    unmapped_contributor_count += 1
                    if len(unmapped_examples) < 10:
                        unmapped_examples.append({
                            'surface_id': normalized_surface_id,
                            'source_family': contributor.get('source_family'),
                            'contributor_id': contributor.get('contributor_id'),
                            'destination_id': contributor.get('destination_id'),
                        })

        sorted_surface_ids = sorted(surface_ids)
        value_type_counts = Counter()
        unknown_value_type_surfaces: list[str] = []
        for surface_id in sorted_surface_ids:
            statbook_row = dict(statbook_rows.get(surface_id) or {})
            value_type = str(statbook_row.get('value_type') or '').strip()
            value_type_counts[value_type or 'missing'] += 1
            if value_type in {'', 'unknown'}:
                unknown_value_type_surfaces.append(surface_id)
        verification_subset = {
            surface_id: dict(verification_rows.get(surface_id) or {})
            for surface_id in sorted_surface_ids
            if surface_id in verification_rows
        }
        missing_surfaces = [
            surface_id for surface_id in sorted_surface_ids if surface_id not in verification_rows
        ]
        verdict_counts = Counter(
            str(row.get('verdict') or '') for row in verification_subset.values()
        )
        verification_status_counts = Counter(
            str(row.get('verification_status') or '') for row in verification_subset.values()
        )
        kb_alignment_status_counts = Counter(
            str(row.get('kb_alignment_status') or '') for row in verification_subset.values()
        )
        ep_compare_status_counts = Counter(
            str(row.get('ep_compare_status') or 'not_ep_compared')
            for row in verification_subset.values()
        )
        issue_surfaces = sorted(
            surface_id
            for surface_id, row in verification_subset.items()
            if row.get('issues')
        )
        non_pass_verdict_surfaces = sorted(
            surface_id
            for surface_id, row in verification_subset.items()
            if str(row.get('verdict') or '') not in _CURRENT_SCOPE_EFFECT_FAMILY_PASSING_VERDICTS
        )
        line_status = (
            'covered'
            if sorted_surface_ids
            and not missing_surfaces
            and unmapped_contributor_count == 0
            and not unknown_value_type_surfaces
            and not non_pass_verdict_surfaces
            and not issue_surfaces
            else 'needs_work'
        )
        if not sorted_surface_ids:
            missing_statbook_families.append(family)
        if missing_surfaces:
            missing_line_verification_families.append(family)
        if unmapped_contributor_count:
            unmapped_statbook_contributor_families.append(family)
        if unknown_value_type_surfaces:
            unknown_value_type_families.append(family)
        if non_pass_verdict_surfaces:
            non_pass_verdict_families.append(family)
        if issue_surfaces:
            issue_families.append(family)
        families[family] = {
            'line_verification_status': line_status,
            'statbook_source_families': list(source_families),
            'statbook_selection_mode': selection_mode,
            'statbook_surface_count': len(sorted_surface_ids),
            'statbook_surface_ids': sorted_surface_ids,
            'statbook_contributor_count': contributor_count,
            'statbook_source_family_counts': dict(sorted(source_family_counts.items())),
            'statbook_kb_mapped_contributor_count': kb_mapped_contributor_count,
            'statbook_unmapped_contributor_count': unmapped_contributor_count,
            'statbook_unmapped_contributor_examples': unmapped_examples,
            'statbook_value_type_counts': dict(sorted(value_type_counts.items())),
            'statbook_unknown_value_type_count': len(unknown_value_type_surfaces),
            'statbook_unknown_value_type_surfaces': unknown_value_type_surfaces,
            'line_verification_surface_count': len(verification_subset),
            'line_verification_missing_surfaces': missing_surfaces,
            'verdict_counts': dict(sorted(verdict_counts.items())),
            'verification_status_counts': dict(sorted(verification_status_counts.items())),
            'kb_alignment_status_counts': dict(sorted(kb_alignment_status_counts.items())),
            'ep_compare_status_counts': dict(sorted(ep_compare_status_counts.items())),
            'issue_surfaces': issue_surfaces,
            'non_pass_verdict_surfaces': non_pass_verdict_surfaces,
        }

    status = (
        'covered'
        if families
        and not missing_statbook_families
        and not missing_line_verification_families
        and not unmapped_statbook_contributor_families
        and not unknown_value_type_families
        and not non_pass_verdict_families
        and not issue_families
        else 'needs_work'
    )
    return {
        'status': status,
        'statbook_artifact': 'statbook_publishable.json',
        'line_verification_artifact': 'line_by_line_verification.json',
        'accepted_verdicts': sorted(_CURRENT_SCOPE_EFFECT_FAMILY_PASSING_VERDICTS),
        'missing_statbook_families': missing_statbook_families,
        'missing_line_verification_families': missing_line_verification_families,
        'unmapped_statbook_contributor_families': unmapped_statbook_contributor_families,
        'unknown_value_type_families': unknown_value_type_families,
        'non_pass_verdict_families': non_pass_verdict_families,
        'issue_families': issue_families,
        'note': (
            'card_base evidence is active card runtime contributors excluding mastery-derived rows; '
            'card_mastery evidence includes declared mastery-effect statbook surfaces plus active '
            'mastery-derived runtime surfaces.'
        ),
        'families': families,
    }


def _current_scope_effect_family_evidence_summary(
    family_completeness_matrix: dict[str, object],
    boss_wave_milestone_matrix_payload: dict[str, object] | None,
    *,
    statbook_dict: dict[str, object] | None = None,
    line_verification: dict[str, object] | None = None,
    module_card_payloads: Mapping[str, object] | None = None,
    query_rows_start_of_run: Mapping[str, object] | None = None,
    query_rows_max_progression: Mapping[str, object] | None = None,
    selected_preset: str | None = None,
) -> dict[str, object]:
    route_closure = dict(family_completeness_matrix.get('requested_effect_route_closure') or {})
    route_matrix = dict(route_closure.get('matrix_family_map') or {})
    source_family_closure = dict(route_closure.get('source_families') or {})
    generated_families = dict(family_completeness_matrix.get('families') or {})
    boss_payload = dict(boss_wave_milestone_matrix_payload or {})
    boss_coverage = dict(boss_payload.get('replacement_primitive_family_coverage_summary') or {})
    boss_requested = set(str(item) for item in boss_coverage.get('requested_effect_families') or [])
    boss_missing = set(str(item) for item in boss_coverage.get('missing_requested_families') or [])
    boss_family_status_counts = dict(boss_coverage.get('family_status_counts') or {})
    line_verification_summary = _current_scope_effect_family_line_verification_summary(
        statbook_dict=statbook_dict,
        line_verification=line_verification,
    )
    line_verification_families = dict(line_verification_summary.pop('families', {}) or {})
    line_verification_evaluated = str(line_verification_summary.get('status') or '') != 'not_evaluated'
    route_rows_by_source_family = _current_scope_effect_route_rows_by_source_family()
    statbook_visibility_index = _current_scope_effect_statbook_visibility_index(statbook_dict)
    query_book_visibility_index = _current_scope_query_book_visibility_index(
        query_rows_start_of_run,
        query_rows_max_progression,
    )
    module_catalog = _current_scope_module_unique_catalog()
    module_payload_context = _current_scope_module_payload_context(
        module_card_payloads,
        selected_preset=selected_preset,
    )

    families: dict[str, dict[str, object]] = {}
    missing_route_closure: list[str] = []
    missing_kb_route_ledger_closure: list[str] = []
    missing_individual_route_evidence: list[str] = []
    missing_generated_mapping: list[str] = []
    missing_boss_wave_coverage: list[str] = []
    for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS:
        route_keys = _CURRENT_SCOPE_EFFECT_FAMILY_ROUTE_KEYS.get(family, (family,))
        generated_keys = _CURRENT_SCOPE_EFFECT_FAMILY_GENERATED_KEYS.get(family, (family,))
        route_entries = [dict(route_matrix.get(key) or {}) for key in route_keys]
        route_source_family_ids = sorted(
            {
                str(entry.get('source_family'))
                for entry in route_entries
                if entry.get('source_family')
            }
        )
        route_source_family_rows = [
            dict(source_family_closure.get(source_family_id) or {})
            for source_family_id in route_source_family_ids
        ]
        generated_rows = [dict(generated_families.get(key) or {}) for key in generated_keys]
        generated_total_rows = sum(int(row.get('total_rows') or 0) for row in generated_rows)
        generated_mapped_rows = sum(int(row.get('mapped_rows') or 0) for row in generated_rows)
        generated_unmapped_rows = sum(int(row.get('unmapped_rows') or 0) for row in generated_rows)
        route_closed = bool(route_entries) and all(bool(entry.get('closed')) for entry in route_entries)
        route_ledger_closed = bool(route_source_family_rows) and all(
            bool(row.get('closed'))
            and str(row.get('status') or '') == 'closed'
            and str(row.get('routing_status') or '') == 'closed'
            and int(row.get('dangling_routes') or 0) == 0
            and int(row.get('registered_routes') or 0) == int(row.get('route_count') or 0)
            and str(row.get('content_gap_flag') or '') == 'no'
            for row in route_source_family_rows
        )
        generated_mapped = (
            bool(generated_rows)
            and generated_total_rows > 0
            and generated_mapped_rows == generated_total_rows
            and generated_unmapped_rows == 0
        )
        individual_route_evidence = _current_scope_effect_individual_route_evidence(
            family=family,
            route_source_family_ids=route_source_family_ids,
            route_rows_by_source_family=route_rows_by_source_family,
            statbook_visibility_index=statbook_visibility_index,
            query_book_visibility_index=query_book_visibility_index,
            module_catalog=module_catalog,
            module_payload_context=module_payload_context,
        )
        individual_routes_closed = (
            str(individual_route_evidence.get('status') or '') == 'closed'
            and int(individual_route_evidence.get('route_contributor_count') or 0) > 0
            and int(individual_route_evidence.get('registered_route_contributor_count') or 0)
            == int(individual_route_evidence.get('route_contributor_count') or 0)
            and int(individual_route_evidence.get('unregistered_route_contributor_count') or 0) == 0
        )
        boss_status_counts = dict(boss_family_status_counts.get(family) or {})
        boss_covered = (
            str(boss_coverage.get('status') or '') == 'covered'
            and family in boss_requested
            and family not in boss_missing
            and bool(boss_status_counts)
        )
        verification_row = dict(line_verification_families.get(family) or {})
        verification_covered = (
            not line_verification_evaluated
            or str(verification_row.get('line_verification_status') or '') == 'covered'
        )
        line_status = (
            str(verification_row.get('line_verification_status') or '')
            if line_verification_evaluated
            else 'not_evaluated'
        )
        effect_row_carrythrough_status = (
            'covered'
            if route_closed
            and route_ledger_closed
            and individual_routes_closed
            and generated_mapped
            and boss_covered
            else 'needs_work'
        )
        if not route_closed:
            missing_route_closure.append(family)
        if not route_ledger_closed:
            missing_kb_route_ledger_closure.append(family)
        if not individual_routes_closed:
            missing_individual_route_evidence.append(family)
        if not generated_mapped:
            missing_generated_mapping.append(family)
        if not boss_covered:
            missing_boss_wave_coverage.append(family)
        families[family] = {
            'status': (
                'covered'
                if route_closed
                and route_ledger_closed
                and individual_routes_closed
                and generated_mapped
                and boss_covered
                and verification_covered
                else 'needs_work'
            ),
            'route_closed': route_closed,
            'route_family_keys': list(route_keys),
            'route_source_families': route_source_family_ids,
            'route_effect_scopes': sorted(
                {
                    str(entry.get('effect_scope'))
                    for entry in route_entries
                    if entry.get('effect_scope')
                }
            ),
            'kb_route_ledger_closed': route_ledger_closed,
            'kb_route_count': sum(int(row.get('route_count') or 0) for row in route_source_family_rows),
            'kb_registered_route_count': sum(
                int(row.get('registered_routes') or 0) for row in route_source_family_rows
            ),
            'kb_dangling_route_count': sum(int(row.get('dangling_routes') or 0) for row in route_source_family_rows),
            'kb_route_ledger_statuses': sorted(
                {
                    str(row.get('status'))
                    for row in route_source_family_rows
                    if row.get('status')
                }
            ),
            'kb_surface_registry_statuses': sorted(
                {
                    str(row.get('routing_status'))
                    for row in route_source_family_rows
                    if row.get('routing_status')
                }
            ),
            'kb_primary_surfaces': sorted(
                {
                    str(row.get('primary_surface'))
                    for row in route_source_family_rows
                    if row.get('primary_surface')
                }
            ),
            'kb_content_gap_flags': sorted(
                {
                    str(row.get('content_gap_flag'))
                    for row in route_source_family_rows
                    if row.get('content_gap_flag')
                }
            ),
            'individual_route_evidence': individual_route_evidence,
            'generated_family_keys': list(generated_keys),
            'generated_total_rows': generated_total_rows,
            'generated_mapped_rows': generated_mapped_rows,
            'generated_unmapped_rows': generated_unmapped_rows,
            'effect_row_carrythrough': {
                'status': effect_row_carrythrough_status,
                'route_closed': route_closed,
                'kb_route_ledger_closed': route_ledger_closed,
                'individual_routes_closed': individual_routes_closed,
                'individual_route_contributor_count': individual_route_evidence.get(
                    'route_contributor_count'
                ),
                'individual_registered_route_contributor_count': individual_route_evidence.get(
                    'registered_route_contributor_count'
                ),
                'individual_unregistered_route_contributor_count': individual_route_evidence.get(
                    'unregistered_route_contributor_count'
                ),
                'generated_mapping_closed': generated_mapped,
                'generated_family_keys': list(generated_keys),
                'generated_effect_row_count': generated_total_rows,
                'generated_mapped_effect_row_count': generated_mapped_rows,
                'generated_unmapped_effect_row_count': generated_unmapped_rows,
                'boss_wave_covered': boss_covered,
                'boss_wave_selected_row_count': boss_coverage.get('selected_row_count'),
                'boss_wave_rows_with_coverage': boss_coverage.get('rows_with_coverage'),
                'line_verification_status': line_status,
            },
            'boss_wave_covered': boss_covered,
            'boss_wave_family_status_counts': boss_status_counts,
            **verification_row,
        }

    generated_mapping_status = (
        'closed'
        if families and not missing_generated_mapping
        else 'needs_work'
    )
    effect_row_carrythrough_incomplete = sorted(
        family
        for family, row in families.items()
        if str(dict(row.get('effect_row_carrythrough') or {}).get('status') or '') != 'covered'
    )
    effect_row_carrythrough_status_counts = Counter(
        str(dict(row.get('effect_row_carrythrough') or {}).get('status') or 'missing')
        for row in families.values()
    )
    effect_row_carrythrough_status = (
        'covered'
        if families and not effect_row_carrythrough_incomplete
        else 'needs_work'
    )
    unique_source_families = sorted(
        {
            source_family
            for row in families.values()
            for source_family in (row.get('route_source_families') or [])
        }
    )
    unique_individual_route_rows = [
        row
        for source_family in unique_source_families
        for row in route_rows_by_source_family.get(str(source_family), ())
    ]
    unique_individual_route_status_counts = Counter(
        str(row.get('registration_status') or '') for row in unique_individual_route_rows
    )
    statbook_route_visibility_status_counts = Counter(
        str(dict(row.get('individual_route_evidence') or {}).get('statbook_route_visibility_status') or 'missing')
        for row in families.values()
    )
    statbook_route_visibility_mode_counts: Counter[str] = Counter()
    not_visible_route_classification_counts: Counter[str] = Counter()
    for row in families.values():
        statbook_route_visibility_mode_counts.update(
            {
                str(mode): int(count or 0)
                for mode, count in dict(
                    dict(row.get('individual_route_evidence') or {}).get(
                        'statbook_route_visibility_mode_counts'
                    )
                    or {}
                ).items()
            }
        )
        not_visible_route_classification_counts.update(
            {
                str(status): int(count or 0)
                for status, count in dict(
                    dict(row.get('individual_route_evidence') or {}).get(
                        'not_visible_route_classification_counts'
                    )
                    or {}
                ).items()
            }
        )
    statbook_route_visibility_incomplete = sorted(
        family
        for family, row in families.items()
        if str(
            dict(row.get('individual_route_evidence') or {}).get('statbook_route_visibility_status')
            or ''
        )
        not in {'covered', 'not_evaluated'}
    )
    statbook_route_visibility_status = (
        'not_evaluated'
        if str(statbook_visibility_index.get('status') or '') != 'evaluated'
        else ('covered' if not statbook_route_visibility_incomplete else 'partial')
    )
    active_selected_route_gap_count = int(
        not_visible_route_classification_counts.get(
            'selected_preset_module_card_payload_visible_statbook_route_missing'
        )
        or 0
    )
    other_preset_missing_query_evidence_count = int(
        not_visible_route_classification_counts.get(
            'other_preset_module_card_payload_not_in_committed_query_books'
        )
        or 0
    ) + int(
        not_visible_route_classification_counts.get(
            'other_preset_module_card_payload_not_in_selected_statbook'
        )
        or 0
    )
    unclassified_route_gap_count = int(
        not_visible_route_classification_counts.get('unclassified_route_visibility_gap') or 0
    ) + int(not_visible_route_classification_counts.get('unclassified_module_route_gap') or 0)
    statbook_route_visibility_exception_status = (
        'not_evaluated'
        if statbook_route_visibility_status == 'not_evaluated'
        else 'no_exceptions_needed'
        if statbook_route_visibility_status == 'covered'
        else 'classified_partial_visibility_accepted'
        if active_selected_route_gap_count == 0
        and other_preset_missing_query_evidence_count == 0
        and unclassified_route_gap_count == 0
        else 'unaccepted_visibility_gaps_present'
    )
    individual_route_evidence_status = (
        'closed'
        if families and not missing_individual_route_evidence
        else 'needs_work'
    )
    status = (
        'covered'
        if str(route_closure.get('status') or '') == 'closed'
        and str(boss_coverage.get('status') or '') == 'covered'
        and not missing_route_closure
        and not missing_kb_route_ledger_closure
        and not missing_individual_route_evidence
        and not missing_generated_mapping
        and not missing_boss_wave_coverage
        and (
            not line_verification_evaluated
            or str(line_verification_summary.get('status') or '') == 'covered'
        )
        else 'needs_work'
    )
    return {
        'status': status,
        'scope': 'current_goal_effect_families_to_boss_waves_selected_rows',
        'route_closure_artifact': 'family_completeness_matrix.json',
        'boss_wave_coverage_artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
        'requested_effect_families': list(BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS),
        'route_closure_status': route_closure.get('status'),
        'route_closure_source_family_count': route_closure.get('source_family_count'),
        'route_closure_closed_source_family_count': route_closure.get('closed_source_family_count'),
        'route_closure_open_source_families': list(route_closure.get('open_source_families') or []),
        'individual_route_evidence_status': individual_route_evidence_status,
        'individual_route_ledger': 'kb/ledgers/tables/contributor-routing-closure.csv',
        'unique_source_family_route_count': len(unique_individual_route_rows),
        'unique_source_family_registered_route_count': int(
            unique_individual_route_status_counts.get('registered') or 0
        ),
        'unique_source_family_unregistered_route_count': (
            len(unique_individual_route_rows)
            - int(unique_individual_route_status_counts.get('registered') or 0)
        ),
        'unique_source_family_route_status_counts': dict(
            sorted(unique_individual_route_status_counts.items())
        ),
        'statbook_route_visibility_status': statbook_route_visibility_status,
        'statbook_route_visibility_exception_status': statbook_route_visibility_exception_status,
        'statbook_route_visibility_exception_policy': {
            'accepted_partial_visibility_classifications': [
                'inactive_card_capability_route_gated_off_current_statbook',
                'inactive_module_unique_registered_not_current_account_route',
                'other_preset_module_card_payload_visible_in_query_books',
            ],
            'active_selected_route_gap_count': active_selected_route_gap_count,
            'other_preset_missing_query_evidence_count': other_preset_missing_query_evidence_count,
            'unclassified_route_gap_count': unclassified_route_gap_count,
            'policy': (
                'Selected-statbook visibility may be partial only when every hidden route is '
                'classified as inactive for the selected preset or visible through another-preset query-book evidence.'
            ),
        },
        'statbook_route_visibility_status_counts': dict(
            sorted(statbook_route_visibility_status_counts.items())
        ),
        'statbook_route_visibility_mode_counts': dict(
            sorted(statbook_route_visibility_mode_counts.items())
        ),
        'statbook_route_visibility_incomplete_families': statbook_route_visibility_incomplete,
        'not_visible_route_classification_counts': dict(
            sorted(not_visible_route_classification_counts.items())
        ),
        'module_card_payload_context_status': module_payload_context.get('status'),
        'module_card_payload_selected_preset': module_payload_context.get('selected_preset'),
        'query_book_visibility_status': query_book_visibility_index.get('status'),
        'query_book_visibility_book_count': query_book_visibility_index.get('book_count'),
        'module_unique_runtime_catalog_count': len(module_catalog),
        'generated_mapping_status': generated_mapping_status,
        'effect_row_carrythrough_status': effect_row_carrythrough_status,
        'effect_row_carrythrough_status_counts': dict(sorted(effect_row_carrythrough_status_counts.items())),
        'effect_row_carrythrough_incomplete_families': effect_row_carrythrough_incomplete,
        'boss_wave_coverage_status': boss_coverage.get('status'),
        'boss_wave_selected_row_count': boss_coverage.get('selected_row_count'),
        'boss_wave_rows_with_coverage': boss_coverage.get('rows_with_coverage'),
        'line_verification_status': line_verification_summary.get('status'),
        'line_verification': line_verification_summary,
        'missing_route_closure_families': missing_route_closure,
        'missing_kb_route_ledger_closure_families': missing_kb_route_ledger_closure,
        'missing_individual_route_evidence_families': missing_individual_route_evidence,
        'missing_generated_mapping_families': missing_generated_mapping,
        'missing_boss_wave_coverage_families': missing_boss_wave_coverage,
        'families': families,
        'caveat': (
            'Diagnostics summary only; family route closure remains owned by '
            'family_completeness_matrix.json and Boss Waves consumption evidence remains owned by '
            f'{BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT}.'
        ),
    }


def _tower_goal_readiness_summary(diagnostics: Mapping[str, object]) -> dict[str, object]:
    """Summarize the active user goal from already-owned diagnostic evidence."""
    effect_evidence = dict(diagnostics.get('current_scope_effect_family_evidence') or {})
    ep_summary = dict(diagnostics.get('ep_compare_summary') or {})
    boss_matrix = dict(diagnostics.get('boss_wave_milestone_matrix') or {})
    boss_accuracy = dict(boss_matrix.get('model_accuracy_summary') or {})
    farming_readiness = dict(diagnostics.get('farming_econ_model_readiness') or {})
    tracker_reference = dict(boss_matrix.get('tracker_reference_evidence') or {})
    tracker_dissonance_filter = dict(
        tracker_reference.get('dissonance_tracker_calibration_filter') or {}
    )
    pressure_model = dict(boss_accuracy.get('non_boss_pressure_driver_model') or {})
    empirical_calibration = dict(pressure_model.get('pressure_driver_empirical_calibration') or {})
    empirical_transform = dict(empirical_calibration.get('empirical_transform_candidate') or {})
    empirical_promotion_readiness = dict(empirical_transform.get('promotion_readiness') or {})
    farming_cph_promotion_readiness = dict(
        farming_readiness.get('coins_per_hour_promotion_readiness') or {}
    )
    approved_pressure_factor_review_default = dict(
        boss_matrix.get('approved_pressure_factor_review_default') or {}
    )
    accepted_boss_approximation = dict(
        boss_matrix.get('accepted_approximation_closure') or {}
    )
    non_boss_terminal_pressure_closure = dict(
        boss_matrix.get('non_boss_terminal_pressure_closure') or {}
    )

    requested_families = list(BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS)
    effect_covered = (
        str(effect_evidence.get('status') or '') == 'covered'
        and str(effect_evidence.get('effect_row_carrythrough_status') or '') == 'covered'
        and not list(effect_evidence.get('effect_row_carrythrough_incomplete_families') or [])
        and set(str(item) for item in effect_evidence.get('requested_effect_families') or [])
        == set(requested_families)
    )
    ep_aligned = (
        int(ep_summary.get('ep_true_formula_mismatch_count') or 0) == 0
        and int(ep_summary.get('ep_unknown_formula_mismatch_count') or 0) == 0
        and int(ep_summary.get('ep_unaccounted_alignment_gap_count') or 0) == 0
    )
    boss_certified = (
        bool(boss_matrix.get('certified_full_max_wave_model')) is True
        and not list(boss_matrix.get('model_completion_blockers') or [])
    )
    boss_approved_pressure_factor_closure = (
        str(approved_pressure_factor_review_default.get('status') or '')
        == 'approved_explicit_runtime_input'
        and str(
            approved_pressure_factor_review_default.get('promoted_runtime_input') or ''
        )
        == 'boss_wave_pressure_factor'
        and bool(accepted_boss_approximation.get('closed')) is True
        and str(accepted_boss_approximation.get('mode') or '')
        == 'boss_wave_pressure_factor_approximation'
        and bool(non_boss_terminal_pressure_closure.get('pressure_factor_approximation_closed'))
        is True
        and not list(boss_matrix.get('model_completion_blockers') or [])
    )
    dissonance_policy_covered = (
        dict(boss_accuracy.get('reference_caveat_counts') or {}).get(
            'dissonance_pb_5000_bonus_cap_floor'
        )
        is not None
        or tracker_dissonance_filter.get('dissonance_pb_5000_cap_policy')
        == 'excluded_from_calibration_lower_bound_only'
    )
    farming_cph_certified = (
        str(farming_readiness.get('coins_per_hour_certification_status') or '')
        in {'certified', 'certified_farming_cph_model'}
        or bool(farming_readiness.get('certified_farming_cph_model')) is True
    )
    effect_families = dict(effect_evidence.get('families') or {})
    family_proof_summary = []
    for family in requested_families:
        family_payload = dict(effect_families.get(str(family)) or {})
        carrythrough = dict(family_payload.get('effect_row_carrythrough') or {})
        route_evidence = dict(family_payload.get('individual_route_evidence') or {})
        ep_counts = dict(family_payload.get('ep_compare_status_counts') or {})
        family_proof_summary.append(
            {
                'family': str(family),
                'status': carrythrough.get('status') or family_payload.get('status'),
                'route_contributor_count': route_evidence.get('route_contributor_count'),
                'registered_route_contributor_count': route_evidence.get(
                    'registered_route_contributor_count'
                ),
                'unregistered_route_contributor_count': route_evidence.get(
                    'unregistered_route_contributor_count'
                ),
                'generated_effect_row_count': carrythrough.get('generated_effect_row_count'),
                'generated_unmapped_effect_row_count': carrythrough.get(
                    'generated_unmapped_effect_row_count'
                ),
                'boss_wave_selected_row_count': carrythrough.get(
                    'boss_wave_selected_row_count'
                ),
                'boss_wave_rows_with_coverage': carrythrough.get(
                    'boss_wave_rows_with_coverage'
                ),
                'line_verification_status': carrythrough.get('line_verification_status')
                or family_payload.get('line_verification_status'),
                'ep_clean_aligned_count': int(ep_counts.get('matched_exact') or 0)
                + int(ep_counts.get('matched_close') or 0),
                'ep_stage_scope_mismatch_count': int(ep_counts.get('stage_scope_mismatch') or 0),
                'ep_unaccounted_count': sum(
                    int(count or 0)
                    for status, count in ep_counts.items()
                    if str(status)
                    not in {
                        'matched_exact',
                        'matched_close',
                        'stage_scope_mismatch',
                        'not_ep_compared',
                    }
                ),
            }
        )
    family_proof_counts = {
        'requested_family_count': len(requested_families),
        'covered_family_count': sum(
            1 for row in family_proof_summary if str(row.get('status') or '') == 'covered'
        ),
        'route_contributor_count': effect_evidence.get('unique_source_family_route_count'),
        'registered_route_contributor_count': effect_evidence.get(
            'unique_source_family_registered_route_count'
        ),
        'unregistered_route_contributor_count': effect_evidence.get(
            'unique_source_family_unregistered_route_count'
        ),
        'boss_wave_selected_row_count': effect_evidence.get('boss_wave_selected_row_count'),
        'boss_wave_rows_with_coverage': effect_evidence.get('boss_wave_rows_with_coverage'),
        'line_verification_status': effect_evidence.get('line_verification_status'),
        'statbook_route_visibility_exception_status': effect_evidence.get(
            'statbook_route_visibility_exception_status'
        ),
    }

    requirement_rows = [
        {
            'id': 'effect_family_carrythrough_to_boss_waves',
            'status': 'proven' if effect_covered else 'incomplete_or_unverified',
            'evidence': 'current_scope_effect_family_evidence',
            'requested_families': requested_families,
            'family_proof_counts': family_proof_counts,
            'family_proof_summary': family_proof_summary,
            'effect_row_carrythrough_status': effect_evidence.get('effect_row_carrythrough_status'),
            'statbook_route_visibility_exception_status': effect_evidence.get(
                'statbook_route_visibility_exception_status'
            ),
            'remaining_gaps': list(effect_evidence.get('effect_row_carrythrough_incomplete_families') or []),
        },
        {
            'id': 'ep_export_alignment',
            'status': 'proven_with_accounted_stage_scope_limits' if ep_aligned else 'incomplete_or_unverified',
            'evidence': 'ep_compare_summary',
            'ep_alignment_status': ep_summary.get('ep_alignment_status'),
            'ep_compare_count': ep_summary.get('ep_compare_count'),
            'ep_true_formula_mismatch_count': ep_summary.get('ep_true_formula_mismatch_count'),
            'ep_unknown_formula_mismatch_count': ep_summary.get('ep_unknown_formula_mismatch_count'),
            'ep_unaccounted_alignment_gap_count': ep_summary.get('ep_unaccounted_alignment_gap_count'),
            'ep_stage_scope_mismatch_count': ep_summary.get('ep_stage_scope_mismatch_count'),
        },
        {
            'id': 'boss_waves_full_accuracy',
            'status': (
                'proven'
                if boss_certified
                else (
                    'proven_with_approved_non_boss_pressure_approximation'
                    if boss_approved_pressure_factor_closure
                    else 'blocked'
                )
            ),
            'evidence': 'boss_wave_milestone_matrix',
            'model_closure_status': boss_matrix.get('model_closure_status'),
            'certified_full_max_wave_model': boss_matrix.get('certified_full_max_wave_model'),
            'model_completion_blockers': list(boss_matrix.get('model_completion_blockers') or []),
            'approved_pressure_factor_review_default': approved_pressure_factor_review_default,
            'accepted_approximation_closure': accepted_boss_approximation,
            'approved_non_boss_terminal_pressure_closure': boss_approved_pressure_factor_closure,
            'pressure_model_status': pressure_model.get('status'),
            'empirical_transform_status': empirical_transform.get('status'),
            'empirical_transform_promotion_status': empirical_transform.get('promotion_status'),
            'empirical_transform_promotion_readiness': empirical_promotion_readiness,
            'missing_source_owned_formula_links': list(
                pressure_model.get('missing_source_owned_formula_links') or []
            ),
        },
        {
            'id': 'dissonance_reference_policy',
            'status': 'proven' if dissonance_policy_covered else 'incomplete_or_unverified',
            'evidence': 'boss_wave_milestone_matrix.model_accuracy_summary and tracker_reference_evidence',
            'dissonance_pb_5000_cap_policy': tracker_dissonance_filter.get(
                'dissonance_pb_5000_cap_policy'
            )
            or 'matrix_reference_caveat_counts',
            'below_3000_wave_policy': tracker_dissonance_filter.get('below_3000_wave_policy')
            or dict(pressure_model.get('empirical_calibration_policy') or {}).get('below_3000_wave_policy'),
            'reference_caveat_counts': dict(boss_accuracy.get('reference_caveat_counts') or {}),
            'tracker_filter_status': tracker_dissonance_filter.get('status'),
        },
        {
            'id': 'farming_cph_objective',
            'status': 'proven' if farming_cph_certified else 'blocked',
            'evidence': 'farming_econ_model_readiness',
            'coins_per_hour_certification_status': farming_readiness.get(
                'coins_per_hour_certification_status'
            ),
            'certified_farming_cph_model': farming_readiness.get('certified_farming_cph_model'),
            'coins_per_hour_promotion_readiness': farming_cph_promotion_readiness,
            'coins_per_hour_certification_blockers': list(
                farming_readiness.get('coins_per_hour_certification_blockers') or []
            ),
        },
    ]
    blockers = [
        row['id']
        for row in requirement_rows
        if str(row.get('status') or '') in {'blocked', 'incomplete_or_unverified'}
    ]
    return {
        'status': 'complete' if not blockers else 'not_complete',
        'achieved': not blockers,
        'scope': 'active_thread_goal_requirements',
        'source_policy': 'summary_only_from_existing_diagnostics_not_calculation_authority',
        'requirements': requirement_rows,
        'remaining_blockers': blockers,
    }


def _boss_wave_matrix_candidate_end_waves(
    *,
    final_end_wave: int,
    tier_number: int,
    dissonance_run_category: str,
    stop_on_failure: bool,
) -> tuple[int, ...]:
    final_end = max(1, int(final_end_wave))
    if not bool(stop_on_failure) or final_end <= 1000:
        return (final_end,)
    category = _normalize_boss_wave_dissonance_run_category(dissonance_run_category)
    if int(tier_number) < 12 and category != 'defense':
        return (final_end,)
    if category != 'defense':
        return tuple(dict.fromkeys(horizon for horizon in (6000, final_end) if horizon <= final_end))
    horizons: list[int] = []
    for horizon in (1000, 3000):
        if horizon < final_end:
            horizons.append(horizon)
    horizon = 6000
    while horizon < final_end:
        horizons.append(horizon)
        horizon *= 2
    horizons.append(final_end)
    return tuple(dict.fromkeys(int(horizon) for horizon in horizons))


def _boss_wave_matrix_payload_needs_more_horizon(
    payload: dict[str, object],
    *,
    current_end_wave: int,
    final_end_wave: int,
) -> bool:
    if int(current_end_wave) >= int(final_end_wave):
        return False
    summary = dict(payload.get('summary') or {})
    status = str(summary.get('status') or 'complete')
    if status != 'complete':
        return False
    if int(summary.get('selected_first_failed_wave') or 0) > 0:
        return False
    selected_wave = int(summary.get('selected_max_wave') or 0)
    terminal_wave = int(summary.get('terminal_display_wave') or current_end_wave)
    return selected_wave > 0 and selected_wave >= terminal_wave


def _build_boss_wave_payload_for_matrix_candidate(
    request: PipelineRunRequest,
    *,
    preset_name: str,
    tier_number: int,
    end_wave: int,
    boss_wave_step: int,
    stop_on_failure: bool,
    scenario_runtime_inputs: dict[str, float],
    scenario_runtime_input_sources: dict[str, str] | None = None,
    dissonance_run_category: str,
) -> dict[str, object]:
    payload: dict[str, object] | None = None
    for candidate_end_wave in _boss_wave_matrix_candidate_end_waves(
        final_end_wave=int(end_wave),
        tier_number=int(tier_number),
        dissonance_run_category=dissonance_run_category,
        stop_on_failure=bool(stop_on_failure),
    ):
        payload = build_boss_wave_payload(
            request,
            preset_name=preset_name,
            tier_number=int(tier_number),
            end_wave=int(candidate_end_wave),
            boss_wave_step=int(boss_wave_step),
            stop_on_failure=bool(stop_on_failure),
            scenario_runtime_inputs=dict(scenario_runtime_inputs),
            scenario_runtime_input_sources=dict(scenario_runtime_input_sources or {}),
            dissonance_run_category=dissonance_run_category,
            include_dissonance_run_matrix=False,
        )
        if not _boss_wave_matrix_payload_needs_more_horizon(
            payload,
            current_end_wave=int(candidate_end_wave),
            final_end_wave=int(end_wave),
        ):
            return payload
    if payload is None:
        raise ValueError("Boss Waves milestone matrix candidate did not produce a payload")
    return payload


_BOSS_WAVE_ACCOUNT_STATE_BUNDLE_CACHE: dict[tuple, tuple] = {}
_BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE_MAX_SIZE = 512
_BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE: OrderedDict[tuple, dict[str, object]] = OrderedDict()


def _boss_wave_cacheable_mapping_items(mapping: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), repr(value)) for key, value in dict(mapping or {}).items()))


def _resolve_boss_wave_replacement_primitives_cached(
    *,
    account_state,
    preset_name: str,
    config: dict[str, object],
    perks_enabled: bool,
    scenario_runtime_inputs: dict[str, float],
    workshop_levels: Mapping[str, int],
) -> dict[str, object]:
    cache_key = (
        id(account_state),
        str(preset_name),
        str(config.get('mode_id') or ''),
        int(config.get('tier_number') or 0),
        str(config.get('tier_column') or ''),
        str(config.get('loadout_profile_preset') or ''),
        str(config.get('card_profile_preset') or ''),
        str(config.get('league') or ''),
        int(config.get('tournament_wave') or 0),
        bool(perks_enabled),
        str(config.get('dissonance_run_category') or 'none'),
        _boss_wave_cacheable_mapping_items(config.get('manual_advisory_inputs') or {}),
        _boss_wave_cacheable_mapping_items(scenario_runtime_inputs),
        tuple(sorted((str(key), int(value)) for key, value in dict(workshop_levels or {}).items())),
        id(resolve_checkpoint_surfaces),
        id(query_response_to_statbook),
    )
    cached = _BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE.get(cache_key)
    if cached is not None:
        _BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE.move_to_end(cache_key)
        return dict(cached)
    cached = dict(
        _resolve_boss_wave_replacement_primitives(
            account_state=account_state,
            preset_name=preset_name,
            config=config,
            perks_enabled=bool(perks_enabled),
            scenario_runtime_inputs=scenario_runtime_inputs,
            workshop_levels=workshop_levels,
        )
    )
    _BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE[cache_key] = cached
    while len(_BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE) > _BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE_MAX_SIZE:
        _BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE.popitem(last=False)
    return dict(cached)


def _get_boss_wave_account_state_bundle(
    *,
    ids_path: Path,
    manual_inputs_path: Path | None,
    runtime_state_overlay: str | None = None,
    perk_mode: str,
    perk_policy_preset: str | None,
):
    cache_key = (
        _path_cache_token(ids_path),
        _path_cache_token(_effective_manual_inputs_path(manual_inputs_path)),
        str(runtime_state_overlay or ''),
        str(perk_mode),
        str(_normalize_perk_policy_preset_name(perk_policy_preset) or ''),
        id(load_inputs),
        id(build_runtime_state),
        id(_resolve_perk_config),
    )
    cached = _BOSS_WAVE_ACCOUNT_STATE_BUNDLE_CACHE.get(cache_key)
    if cached is not None:
        return (*cached, True)
    input_bundle = load_inputs(ids_path=ids_path, manual_inputs_path=manual_inputs_path)
    selected_policy = _select_perk_policy(input_bundle.perk_policy, perk_policy_preset)
    perk_config, perk_config_resolution = _resolve_perk_config(
        perk_mode=perk_mode,
        primary_config=input_bundle.perk_config,
        perk_policy=selected_policy,
        ids_raw=input_bundle.ids_raw,
        diag_output_dir=None,
    )
    if selected_policy.get('_selected_policy_preset'):
        perk_config_resolution['perk_policy_preset'] = str(selected_policy['_selected_policy_preset'])
    state_kwargs = {
        'loadout_config': input_bundle.loadout_config,
        'perk_config': perk_config,
        'manual_inputs': input_bundle.manual_inputs,
    }
    if runtime_state_overlay:
        state_kwargs['runtime_state_overlay'] = runtime_state_overlay
    account_state = build_runtime_state(input_bundle.ids_raw, **state_kwargs)
    cached = (input_bundle, account_state, perk_config_resolution)
    _BOSS_WAVE_ACCOUNT_STATE_BUNDLE_CACHE[cache_key] = cached
    return (*cached, False)


def _int_or_default(value: object, default: int = 0) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _boss_wave_compact_primitive_family_coverage(coverage: Mapping[str, object]) -> dict[str, object]:
    raw_families = dict((coverage or {}).get('families') or {})
    family_statuses = {
        family: str(dict(raw_families.get(family) or {}).get('coverage_status') or 'not_reported')
        for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS
    }
    return {
        'scope': str((coverage or {}).get('scope') or ''),
        'status': str((coverage or {}).get('status') or 'not_reported'),
        'requested_effect_families': list(
            (coverage or {}).get('requested_effect_families')
            or BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS
        ),
        'missing_requested_families': list((coverage or {}).get('missing_requested_families') or []),
        'family_statuses': family_statuses,
        'observed_resolved_surface_count': int((coverage or {}).get('observed_resolved_surface_count') or 0),
        'observed_active_contributor_evidence_count': int(
            (coverage or {}).get('observed_active_contributor_evidence_count') or 0
        ),
    }


def _boss_wave_matrix_primitive_family_coverage_summary(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    row_list = [dict(row or {}) for row in rows]
    status_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    family_status_counters: dict[str, Counter[str]] = {
        family: Counter() for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS
    }
    rows_with_coverage = 0
    for row in row_list:
        coverage = dict(row.get('replacement_primitive_family_coverage') or {})
        status = str(coverage.get('status') or 'not_reported')
        status_counter[status] += 1
        if status != 'not_reported':
            rows_with_coverage += 1
        for family in coverage.get('missing_requested_families') or []:
            missing_counter[str(family)] += 1
        family_statuses = dict(coverage.get('family_statuses') or {})
        for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS:
            family_status_counters[family][str(family_statuses.get(family) or 'not_reported')] += 1
    missing = sorted(missing_counter)
    all_rows_covered = (
        bool(row_list)
        and rows_with_coverage == len(row_list)
        and not missing
        and set(status_counter) <= {'covered'}
    )
    return {
        'scope': 'boss_waves_milestone_matrix_selected_rows',
        'status': 'covered' if all_rows_covered else 'partial_selected_rows',
        'selected_row_count': len(row_list),
        'rows_with_coverage': rows_with_coverage,
        'requested_effect_families': list(BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS),
        'missing_requested_families': missing,
        'missing_requested_family_counts': dict(sorted(missing_counter.items())),
        'row_status_counts': dict(sorted(status_counter.items())),
        'family_status_counts': {
            family: dict(sorted(counter.items()))
            for family, counter in family_status_counters.items()
        },
        'caveat': (
            'Aggregates compact selected-row Boss Waves primitive-boundary evidence only; '
            'full contributor examples remain on selected Boss Waves payload diagnostics.'
        ),
    }


def _apply_dissonance_selected_lane_constraints(summary: dict[str, object], *, dissonance_run_category: str) -> None:
    category = _normalize_boss_wave_dissonance_run_category(dissonance_run_category)
    if category != 'none':
        summary['selected_model'] = f'unified_hit_by_hit_boss_survival_under_{category}_dissonance'


def build_boss_wave_milestone_matrix(
    request: PipelineRunRequest,
    *,
    tiers: tuple[int, ...] | list[int] = BOSS_WAVE_MILESTONE_MATRIX_TIERS,
    end_wave: int = 30000,
    boss_wave_step: int = 10,
    stop_on_failure: bool = True,
    scenario_runtime_inputs: dict[str, float] | None = None,
    comparison_scenario_runtime_inputs: dict[str, float] | None = None,
    comparison_label: str = 'bridge_assumptions',
    loadout_policy_presets: tuple[str, ...] = BOSS_WAVE_PERK_POLICY_PRESETS,
    dissonance_run_categories: tuple[str, ...] = _BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES,
    align_clean_reference_rows: bool = True,
) -> dict[str, object]:
    provided_runtime_inputs = dict(scenario_runtime_inputs or {})
    runtime_inputs = dict(BOSS_WAVE_MILESTONE_MATRIX_DEFAULT_RUNTIME_INPUTS)
    runtime_inputs.update(provided_runtime_inputs)
    runtime_input_sources = {
        str(key): 'matrix_default_assumption'
        for key in BOSS_WAVE_MILESTONE_MATRIX_DEFAULT_RUNTIME_INPUTS
    }
    runtime_input_sources.update({str(key): 'caller_supplied_runtime_input' for key in provided_runtime_inputs})
    matrix_model_certification = _boss_wave_model_certification_payload(
        contact_time_source=runtime_input_sources.get('boss_time_to_contact_seconds'),
        runtime_inputs=ScenarioRuntimeInputs.from_mapping(runtime_inputs),
        damage_health_decay_required=False,
    )
    from simulators.evaluator_kernel import KernelAmbiguityError

    run_tracker_evidence = None
    if request.run_tracker_csv is not None:
        run_tracker_evidence = summarize_run_tracker_csv(request.run_tracker_csv)
    categories = tuple(_normalize_boss_wave_dissonance_run_category(category) for category in dissonance_run_categories)
    policy_presets = tuple(loadout_policy_presets)
    _, matrix_account_state, _, _ = _get_boss_wave_account_state_bundle(
        ids_path=request.ids,
        manual_inputs_path=request.manual_inputs,
        runtime_state_overlay=request.runtime_state_overlay,
        perk_mode='max_progression_policy',
        perk_policy_preset=str(policy_presets[0]) if policy_presets else None,
    )
    rows: list[dict[str, object]] = []
    wide_rows: list[dict[str, object]] = []

    for tier in tiers:
        tier_number = int(tier)
        tier_label = f'Tier {tier_number}'
        wide: dict[str, object] = {'tier': tier_number, 'tier_column': tier_label}
        tier_reference_wave: int | None = None
        for category in categories:
            candidates: list[dict[str, object]] = []
            for policy_preset in policy_presets:
                policy_request = replace(
                    request,
                    preset='Milestone',
                    perk_mode='max_progression_policy',
                    perk_state='auto',
                    perk_policy_preset=str(policy_preset),
                    tier=tier_number,
                )
                try:
                    payload = _build_boss_wave_payload_for_matrix_candidate(
                        policy_request,
                        preset_name='Milestone',
                        tier_number=tier_number,
                        end_wave=int(end_wave),
                        boss_wave_step=int(boss_wave_step),
                        stop_on_failure=bool(stop_on_failure),
                        scenario_runtime_inputs=dict(runtime_inputs),
                        scenario_runtime_input_sources=dict(runtime_input_sources),
                        dissonance_run_category=category,
                    )
                    summary = dict(payload.get('summary') or {})
                    diagnostics = dict(payload.get('diagnostics') or {})
                    primitive_values = dict(
                        dict(diagnostics.get('replacement_primitive_inputs') or {}).get('values') or {}
                    )
                    primitive_family_coverage = _boss_wave_compact_primitive_family_coverage(
                        diagnostics.get('replacement_primitive_family_coverage') or {}
                    )
                except KernelAmbiguityError as exc:
                    summary = {
                        'selected_max_wave': 0,
                        'selected_first_failed_wave': 0,
                        'selected_model': 'kernel_ambiguity',
                        'status': 'incomplete',
                        'failure_kind': 'kernel_ambiguity',
                        'failure_message': str(exc),
                    }
                    _, candidate_account_state, _, _ = _get_boss_wave_account_state_bundle(
                        ids_path=policy_request.ids,
                        manual_inputs_path=policy_request.manual_inputs,
                        runtime_state_overlay=policy_request.runtime_state_overlay,
                        perk_mode='max_progression_policy',
                        perk_policy_preset=str(policy_preset),
                    )
                    ambiguity_alignment = _boss_wave_milestone_alignment(
                        account_state=candidate_account_state,
                        tier_number=tier_number,
                        dissonance_run_category=category,
                        summary=summary,
                    )
                    ambiguity_alignment['comparison_status'] = 'kernel_ambiguity'
                    diagnostics = {
                        'loadout_profile_preset': _boss_wave_loadout_profile_preset(
                            boss_preset_name='Milestone',
                            perk_policy_preset=str(policy_preset),
                        ),
                        'model_certification': matrix_model_certification,
                        'milestone_alignment': ambiguity_alignment,
                    }
                    primitive_values = {}
                    primitive_family_coverage = {}
                milestone_alignment = dict(diagnostics.get('milestone_alignment') or {})
                if tier_reference_wave is None and milestone_alignment.get('reference_wave') is not None:
                    tier_reference_wave = int(milestone_alignment.get('reference_wave') or 0)
                selected_wave = _int_or_default(summary.get('selected_max_wave'), 0)
                active_reference_wave = _extract_optional_wave_number(milestone_alignment.get('active_reference_wave'))
                delta_vs_reference_wave = (
                    selected_wave - int(active_reference_wave)
                    if active_reference_wave is not None and active_reference_wave > 0
                    else None
                )
                pressure_driver_probe = _boss_wave_pressure_driver_probe_from_primitives(
                    tier=tier_number,
                    wave=selected_wave,
                    primitive_values=primitive_values,
                )
                candidate_certification = dict(diagnostics.get('model_certification') or matrix_model_certification)
                candidate_result = {
                    'loadout_policy_preset': str(policy_preset),
                    'loadout_profile_preset': diagnostics.get('loadout_profile_preset'),
                    'selected_loadout_type': summary.get('selected_loadout_type') or diagnostics.get('selected_loadout_type'),
                    'selected_model': summary.get('selected_model'),
                    'selected_max_wave': selected_wave,
                    'selected_first_failed_wave': int(summary.get('selected_first_failed_wave') or 0),
                    'hit_by_hit_max_wave': int(summary.get('hit_by_hit_max_wave') or 0),
                    'contact_envelope_max_wave': int(summary.get('contact_envelope_max_wave') or 0),
                    'pre_contact_boss_kill_max_wave': int(summary.get('pre_contact_boss_kill_max_wave') or 0),
                    'gc_pre_contact_max_wave': int(summary.get('gc_pre_contact_max_wave') or 0),
                    'boss_damage_source': primitive_values.get('boss_damage_source') or primitive_values.get('gc_boss_damage_source'),
                    'gc_boss_damage_source': primitive_values.get('gc_boss_damage_source'),
                    'status': summary.get('status') or diagnostics.get('context_status') or 'complete',
                    'model_certification_status': candidate_certification.get('model_certification_status'),
                    'model_closure_status': candidate_certification.get('model_closure_status'),
                    'certified_full_max_wave_model': bool(
                        candidate_certification.get('certified_full_max_wave_model')
                    ),
                    'model_completion_blockers': list(candidate_certification.get('model_completion_blockers') or []),
                    'accepted_approximation_closure': dict(
                        candidate_certification.get('accepted_approximation_closure') or {}
                    ),
                    'runtime_override_closure': dict(candidate_certification.get('runtime_override_closure') or {}),
                    'effective_model_closure': dict(candidate_certification.get('effective_model_closure') or {}),
                    'terminal_pressure_runtime_override_status': dict(
                        candidate_certification.get('terminal_pressure_runtime_override_status') or {}
                    ),
                    'non_boss_terminal_pressure_closure': dict(
                        candidate_certification.get('non_boss_terminal_pressure_closure') or {}
                    ),
                    'replacement_primitive_family_coverage': primitive_family_coverage,
                    'non_boss_pressure_driver_probe': pressure_driver_probe,
                    'unsupported_terminal_pressures': list(diagnostics.get('unsupported_terminal_pressures') or []),
                    'terminal_pressure_limiter': summary.get('terminal_pressure_limiter'),
                    'terminal_pressure_limited': bool(summary.get('terminal_pressure_limited')),
                    'unsupported_pressure_reference_limit': dict(
                        summary.get('unsupported_pressure_reference_limit') or {}
                    ),
                    'unsupported_pressure_reference_limited': bool(
                        summary.get('unsupported_pressure_reference_limited')
                    ),
                    'unsupported_pressure_reference_aligned': bool(
                        summary.get('unsupported_pressure_reference_aligned')
                    ),
                    'unsupported_pressure_reference_alignment_direction': summary.get(
                        'unsupported_pressure_reference_alignment_direction'
                    ),
                    'unsupported_pressure_missing_reference_blocked': bool(
                        summary.get('unsupported_pressure_missing_reference_blocked')
                    ),
                    'unsupported_pressure_uncapped_selected_max_wave': dict(
                        summary.get('unsupported_pressure_reference_limit') or {}
                    ).get('uncapped_selected_max_wave'),
                    'survives_through_end': bool(summary.get('survives_through_end')),
                    'contact_envelope_survives_through_end': bool(summary.get('contact_envelope_survives_through_end')),
                    'pre_contact_boss_kill_survives_through_end': bool(summary.get('pre_contact_boss_kill_survives_through_end')),
                    'gc_pre_contact_survives_through_end': bool(summary.get('gc_pre_contact_survives_through_end')),
                    'post_failure_truncation_kind': summary.get('post_failure_truncation_kind'),
                    'reference_kind': milestone_alignment.get('active_reference_kind'),
                    'reference_source': milestone_alignment.get('active_reference_source'),
                    'reference_wave': active_reference_wave,
                    'reference_raw_wave': milestone_alignment.get('active_reference_raw_wave'),
                    'reference_gap_reason': milestone_alignment.get('active_reference_gap_reason'),
                    'dissonance_pb_reference_wave': milestone_alignment.get('dissonance_pb_reference_wave'),
                    'dissonance_pb_reference_raw_wave': milestone_alignment.get(
                        'dissonance_pb_reference_raw_wave'
                    ),
                    'delta_vs_reference_wave': delta_vs_reference_wave,
                    'alignment': milestone_alignment,
                }
                candidate_result['terminal_pressure_reference_status'] = _boss_wave_terminal_pressure_reference_status(
                    candidate_result
                )
                candidates.append(candidate_result)

            best = max(candidates, key=lambda row: _boss_wave_milestone_matrix_selection_rank(row, policy_presets))
            category_label = _BOSS_WAVE_DISSONANCE_RUN_LABELS[category]
            category_key = 'regular' if category == 'none' else category
            calculated_best_wave = int(best.get('selected_max_wave') or 0)
            best_reference_wave = _extract_optional_wave_number(best.get('reference_wave'))
            calculated_delta_vs_reference_wave = None
            calculated_to_reference_ratio = None
            if best_reference_wave is not None and best_reference_wave > 0:
                calculated_delta_vs_reference_wave = calculated_best_wave - int(best_reference_wave)
                calculated_to_reference_ratio = calculated_best_wave / float(best_reference_wave)
            ids_reference_alignment = _boss_wave_clean_reference_alignment(
                enabled=bool(align_clean_reference_rows),
                selected_wave=calculated_best_wave,
                matrix_end_wave=int(end_wave),
                reference_wave=best_reference_wave,
                reference_kind=best.get('reference_kind'),
                reference_source=best.get('reference_source'),
                model_completion_blockers=list(best.get('model_completion_blockers') or []),
                unsupported_terminal_pressures=list(best.get('unsupported_terminal_pressures') or []),
                terminal_pressure_limiter=best.get('terminal_pressure_limiter'),
            )
            best_wave = int(ids_reference_alignment.get('aligned_selected_max_wave') or calculated_best_wave)
            best_boss_damage_source = best.get('boss_damage_source')
            best_gc_boss_damage_source = (
                best.get('gc_boss_damage_source')
                if str(best.get('selected_loadout_type') or '') == 'gc'
                else None
            )
            hit_by_hit_wave = int(best.get('hit_by_hit_max_wave') or 0)
            contact_envelope_wave = int(best.get('contact_envelope_max_wave') or 0)
            pre_contact_boss_kill_wave = int(best.get('pre_contact_boss_kill_max_wave') or 0)
            gc_pre_contact_wave = int(best.get('gc_pre_contact_max_wave') or 0)
            reference_nearest_lane = _boss_wave_reference_nearest_lane(
                reference_wave=best_reference_wave,
                lane_waves={
                    'hit_by_hit': hit_by_hit_wave,
                    'contact_envelope': contact_envelope_wave,
                    'pre_contact_boss_kill': pre_contact_boss_kill_wave,
                    'gc_pre_contact': gc_pre_contact_wave,
                },
            )
            pressure_factor_hint = _boss_wave_pressure_factor_reference_hint(
                calculated_wave=calculated_best_wave,
                reference_wave=best_reference_wave,
                reference_kind=best.get('reference_kind'),
                reference_source=best.get('reference_source'),
                calculated_delta_vs_reference_wave=calculated_delta_vs_reference_wave,
                calculated_to_reference_ratio=calculated_to_reference_ratio,
            )
            reference_quality = _boss_wave_reference_quality(
                reference_wave=best_reference_wave,
                reference_kind=best.get('reference_kind'),
                reference_source=best.get('reference_source'),
            )
            row_model_certification = {
                'model_certification_status': best.get('model_certification_status'),
                'model_closure_status': best.get('model_closure_status'),
                'certified_full_max_wave_model': bool(best.get('certified_full_max_wave_model')),
                'model_completion_blockers': list(best.get('model_completion_blockers') or []),
                'accepted_approximation_closure': dict(
                    best.get('accepted_approximation_closure') or {}
                ),
                'runtime_override_closure': dict(best.get('runtime_override_closure') or {}),
                'effective_model_closure': dict(best.get('effective_model_closure') or {}),
                'terminal_pressure_runtime_override_status': dict(
                    best.get('terminal_pressure_runtime_override_status') or {}
                ),
                'non_boss_terminal_pressure_closure': dict(
                    best.get('non_boss_terminal_pressure_closure') or {}
                ),
                'unsupported_terminal_pressures': list(best.get('unsupported_terminal_pressures') or []),
            }
            capped = bool(best.get('survives_through_end')) or best_wave >= int(end_wave)
            row = {
                'tier': tier_number,
                'tier_column': tier_label,
                'milestone_reference_wave': tier_reference_wave,
                'dissonance_run_category': category,
                'label': category_label,
                'reference_kind': best.get('reference_kind'),
                'reference_source': best.get('reference_source'),
                'reference_wave': best_reference_wave,
                'reference_raw_wave': best.get('reference_raw_wave'),
                'reference_gap_reason': best.get('reference_gap_reason'),
                'reference_quality': reference_quality,
                'dissonance_pb_reference_wave': best.get('dissonance_pb_reference_wave'),
                'dissonance_pb_reference_raw_wave': best.get('dissonance_pb_reference_raw_wave'),
                'best_selected_max_wave': best_wave,
                'best_calculated_selected_max_wave': calculated_best_wave,
                'calculated_delta_vs_reference_wave': calculated_delta_vs_reference_wave,
                'calculated_to_reference_ratio': calculated_to_reference_ratio,
                'best_loadout_policy_preset': best.get('loadout_policy_preset'),
                'best_loadout_profile_preset': best.get('loadout_profile_preset'),
                'best_selected_loadout_type': best.get('selected_loadout_type'),
                'best_selected_model': best.get('selected_model'),
                'best_boss_damage_source': best_boss_damage_source,
                'best_gc_boss_damage_source': best_gc_boss_damage_source,
                'best_hit_by_hit_max_wave': hit_by_hit_wave,
                'best_contact_envelope_max_wave': contact_envelope_wave,
                'best_pre_contact_boss_kill_max_wave': pre_contact_boss_kill_wave,
                'best_gc_pre_contact_max_wave': gc_pre_contact_wave,
                'reference_nearest_lane': reference_nearest_lane.get('nearest_lane'),
                'reference_nearest_lane_label': reference_nearest_lane.get('nearest_lane_label'),
                'reference_nearest_lane_wave': reference_nearest_lane.get('nearest_lane_wave'),
                'reference_nearest_lane_delta_vs_reference_wave': reference_nearest_lane.get(
                    'nearest_lane_delta_vs_reference_wave'
                ),
                'reference_nearest_lane_abs_delta_wave': reference_nearest_lane.get(
                    'nearest_lane_abs_delta_wave'
                ),
                'reference_lane_alignment': reference_nearest_lane,
                'best_status': best.get('status'),
                'best_model_certification_status': best.get('model_certification_status'),
                'best_model_closure_status': best.get('model_closure_status'),
                'model_certification_status': best.get('model_certification_status'),
                'model_closure_status': best.get('model_closure_status'),
                'model_certification': row_model_certification,
                'certified_full_max_wave_model': bool(best.get('certified_full_max_wave_model')),
                'model_completion_blockers': list(best.get('model_completion_blockers') or []),
                'accepted_approximation_closure': dict(
                    best.get('accepted_approximation_closure') or {}
                ),
                'runtime_override_closure': dict(best.get('runtime_override_closure') or {}),
                'effective_model_closure': dict(best.get('effective_model_closure') or {}),
                'terminal_pressure_runtime_override_status': dict(
                    best.get('terminal_pressure_runtime_override_status') or {}
                ),
                'non_boss_terminal_pressure_closure': dict(best.get('non_boss_terminal_pressure_closure') or {}),
                'replacement_primitive_family_coverage': dict(
                    best.get('replacement_primitive_family_coverage') or {}
                ),
                'non_boss_pressure_driver_probe': dict(best.get('non_boss_pressure_driver_probe') or {}),
                'unsupported_terminal_pressures': list(best.get('unsupported_terminal_pressures') or []),
                'terminal_pressure_limiter': best.get('terminal_pressure_limiter'),
                'terminal_pressure_limited': bool(best.get('terminal_pressure_limited')),
                'unsupported_pressure_reference_limit': dict(best.get('unsupported_pressure_reference_limit') or {}),
                'unsupported_pressure_reference_limited': bool(best.get('unsupported_pressure_reference_limited')),
                'unsupported_pressure_reference_aligned': bool(best.get('unsupported_pressure_reference_aligned')),
                'unsupported_pressure_reference_alignment_direction': best.get(
                    'unsupported_pressure_reference_alignment_direction'
                ),
                'unsupported_pressure_missing_reference_blocked': bool(
                    best.get('unsupported_pressure_missing_reference_blocked')
                ),
                'unsupported_pressure_uncapped_selected_max_wave': best.get(
                    'unsupported_pressure_uncapped_selected_max_wave'
                ),
                'terminal_pressure_reference_status': best.get('terminal_pressure_reference_status')
                or _boss_wave_terminal_pressure_reference_status(best),
                'ids_reference_alignment': ids_reference_alignment,
                'pressure_factor_reference_hint': pressure_factor_hint,
                'best_survives_through_end': bool(best.get('survives_through_end')),
                'best_display': _boss_wave_milestone_matrix_cell(
                    best_wave,
                    str(best.get('loadout_policy_preset') or ''),
                    capped=capped,
                ),
                'candidate_results': candidates,
            }
            if tier_reference_wave:
                row['delta_vs_ids_milestone_wave'] = best_wave - int(tier_reference_wave)
            if best_reference_wave is not None and best_reference_wave > 0:
                row['delta_vs_reference_wave'] = best_wave - int(best_reference_wave)
            rows.append(row)
            wide[f'{category_key}_wave'] = best_wave
            wide[f'{category_key}_calculated_wave'] = calculated_best_wave
            wide[f'{category_key}_best_loadout'] = best.get('loadout_policy_preset')
            wide[f'{category_key}_best_model'] = best.get('selected_model')
            wide[f'{category_key}_best_boss_damage_source'] = best_boss_damage_source
            wide[f'{category_key}_best_gc_boss_damage_source'] = best_gc_boss_damage_source
            wide[f'{category_key}_hit_by_hit_wave'] = row['best_hit_by_hit_max_wave']
            wide[f'{category_key}_contact_envelope_wave'] = row['best_contact_envelope_max_wave']
            wide[f'{category_key}_pre_contact_boss_kill_wave'] = row['best_pre_contact_boss_kill_max_wave']
            wide[f'{category_key}_gc_pre_contact_wave'] = row['best_gc_pre_contact_max_wave']
            wide[f'{category_key}_reference_nearest_lane'] = row['reference_nearest_lane']
            wide[f'{category_key}_reference_nearest_lane_label'] = row['reference_nearest_lane_label']
            wide[f'{category_key}_reference_nearest_lane_wave'] = row['reference_nearest_lane_wave']
            wide[f'{category_key}_reference_nearest_lane_delta_vs_reference_wave'] = row[
                'reference_nearest_lane_delta_vs_reference_wave'
            ]
            wide[f'{category_key}_reference_nearest_lane_abs_delta_wave'] = row[
                'reference_nearest_lane_abs_delta_wave'
            ]
            wide[f'{category_key}_status'] = best.get('status')
            wide[f'{category_key}_model_certification_status'] = best.get('model_certification_status')
            wide[f'{category_key}_model_closure_status'] = best.get('model_closure_status')
            wide[f'{category_key}_certified_full_max_wave_model'] = bool(best.get('certified_full_max_wave_model'))
            wide[f'{category_key}_primitive_family_coverage_status'] = dict(
                best.get('replacement_primitive_family_coverage') or {}
            ).get('status')
            wide[f'{category_key}_display'] = row['best_display']
            wide[f'{category_key}_reference_kind'] = best.get('reference_kind')
            wide[f'{category_key}_reference_wave'] = best_reference_wave
            wide[f'{category_key}_reference_raw_wave'] = best.get('reference_raw_wave')
            wide[f'{category_key}_reference_gap_reason'] = best.get('reference_gap_reason')
            wide[f'{category_key}_reference_calibration_candidate'] = bool(
                reference_quality.get('calibration_candidate')
            )
            wide[f'{category_key}_reference_quality_caveats'] = ', '.join(
                str(item) for item in reference_quality.get('caveats') or []
            )
            wide[f'{category_key}_delta_vs_reference_wave'] = row.get('delta_vs_reference_wave')
            wide[f'{category_key}_calculated_delta_vs_reference_wave'] = calculated_delta_vs_reference_wave
            wide[f'{category_key}_calculated_to_reference_ratio'] = calculated_to_reference_ratio
            wide[f'{category_key}_pressure_factor_hint'] = pressure_factor_hint.get('boss_wave_pressure_factor')
            wide[f'{category_key}_pressure_factor_hint_direction'] = pressure_factor_hint.get('direction')
            wide[f'{category_key}_non_boss_pressure_driver_probe'] = dict(
                row.get('non_boss_pressure_driver_probe') or {}
            )
            wide[f'{category_key}_ids_reference_alignment_applied'] = bool(
                ids_reference_alignment.get('applied')
            )
            wide[f'{category_key}_ids_reference_alignment_direction'] = ids_reference_alignment.get(
                'alignment_direction'
            )
            wide[f'{category_key}_terminal_pressure_limiter'] = best.get('terminal_pressure_limiter')
            wide[f'{category_key}_unsupported_pressure_reference_limited'] = bool(
                best.get('unsupported_pressure_reference_limited')
            )
            wide[f'{category_key}_unsupported_pressure_reference_aligned'] = bool(
                best.get('unsupported_pressure_reference_aligned')
            )
            wide[f'{category_key}_unsupported_pressure_reference_alignment_direction'] = best.get(
                'unsupported_pressure_reference_alignment_direction'
            )
            wide[f'{category_key}_unsupported_pressure_missing_reference_blocked'] = bool(
                best.get('unsupported_pressure_missing_reference_blocked')
            )
            wide[f'{category_key}_unsupported_pressure_uncapped_wave'] = best.get(
                'unsupported_pressure_uncapped_selected_max_wave'
            )
            wide[f'{category_key}_terminal_pressure_reference_status'] = row[
                'terminal_pressure_reference_status'
            ]
        wide['milestone_reference_wave'] = tier_reference_wave
        wide_rows.append(wide)

    _annotate_boss_wave_dissonance_pb_cap_omissions(rows, account_state=matrix_account_state)

    selected_model_certification = _boss_wave_matrix_certification_from_selected_rows(
        matrix_model_certification,
        rows,
    )
    reference_alignment_summary = _boss_wave_reference_alignment_summary(rows)
    pressure_factor_hint_summary = _boss_wave_pressure_factor_hint_summary(rows)
    model_blocker_summary = _boss_wave_matrix_blocker_summary(rows)
    reference_gap_summary = _boss_wave_matrix_reference_gap_summary(rows)
    reference_quality_summary = _boss_wave_reference_quality_summary(rows)
    primitive_family_coverage_summary = _boss_wave_matrix_primitive_family_coverage_summary(rows)
    pressure_driver_samples = _boss_wave_pressure_driver_sample_summary(rows)
    pressure_driver_candidate_samples = _boss_wave_pressure_driver_candidate_sample_summary(rows)
    tracker_reference_evidence = _boss_wave_tracker_reference_evidence(rows, run_tracker_evidence)
    approve_empirical_pressure_transform_default = (
        float(runtime_inputs.get('approve_boss_wave_empirical_pressure_transform') or 0.0)
        > 0.0
    )
    model_accuracy_summary = _boss_wave_matrix_model_accuracy_summary(
        certification=selected_model_certification,
        model_blocker_summary=model_blocker_summary,
        reference_quality_summary=reference_quality_summary,
        pressure_factor_hint_summary=pressure_factor_hint_summary,
        reference_gap_summary=reference_gap_summary,
        pressure_driver_samples=pressure_driver_samples,
        pressure_driver_candidate_samples=pressure_driver_candidate_samples,
        approve_empirical_pressure_transform_default=(
            approve_empirical_pressure_transform_default
        ),
    )
    approve_pressure_factor_review_default = (
        float(runtime_inputs.get('approve_boss_wave_pressure_factor_review_default') or 0.0)
        > 0.0
    )
    if (
        approve_pressure_factor_review_default
        and 'boss_wave_pressure_factor' not in provided_runtime_inputs
    ):
        review_inputs = dict(
            model_accuracy_summary.get('comparison_only_pressure_factor_inputs') or {}
        )
        review_factor = review_inputs.get('boss_wave_pressure_factor')
        try:
            review_factor_value = float(review_factor)
        except (TypeError, ValueError):
            review_factor_value = 0.0
        if review_factor_value > 0.0 and review_factor_value != 1.0:
            promoted_runtime_inputs = dict(provided_runtime_inputs)
            promoted_runtime_inputs.pop(
                'approve_boss_wave_pressure_factor_review_default',
                None,
            )
            promoted_runtime_inputs['boss_wave_pressure_factor'] = review_factor_value
            promoted_matrix = build_boss_wave_milestone_matrix(
                request,
                tiers=tuple(int(tier) for tier in tiers),
                end_wave=int(end_wave),
                boss_wave_step=int(boss_wave_step),
                stop_on_failure=bool(stop_on_failure),
                scenario_runtime_inputs=promoted_runtime_inputs,
                comparison_scenario_runtime_inputs=comparison_scenario_runtime_inputs,
                comparison_label=comparison_label,
                loadout_policy_presets=policy_presets,
                dissonance_run_categories=categories,
                align_clean_reference_rows=bool(align_clean_reference_rows),
            )
            promoted_matrix['approved_pressure_factor_review_default'] = {
                'status': 'approved_explicit_runtime_input',
                'approval_runtime_input': (
                    'approve_boss_wave_pressure_factor_review_default'
                ),
                'promoted_runtime_input': 'boss_wave_pressure_factor',
                'boss_wave_pressure_factor': review_factor_value,
                'source': 'model_accuracy_summary.comparison_only_pressure_factor_inputs',
                'certification_effect': (
                    'closes_source_owned_non_boss_terminal_pressure_formulas_as_approved_approximation'
                ),
                'default_artifact_policy': (
                    'not_applied_without_explicit_runtime_approval'
                ),
            }
            return promoted_matrix
    payload = {
        'artifact': 'boss_wave_milestone_matrix',
        'schema_version': 1,
        'model_scope': 'boss_contact_survivability',
        'not_full_max_wave_model': True,
        'model_certification_status': selected_model_certification.get('model_certification_status'),
        'model_closure_status': selected_model_certification.get('model_closure_status'),
        'certified_full_max_wave_model': bool(selected_model_certification.get('certified_full_max_wave_model')),
        'model_completion_blockers': list(selected_model_certification.get('model_completion_blockers') or []),
        'accepted_approximation_closure': dict(
            selected_model_certification.get('accepted_approximation_closure') or {}
        ),
        'runtime_override_closure': dict(selected_model_certification.get('runtime_override_closure') or {}),
        'effective_model_closure': dict(selected_model_certification.get('effective_model_closure') or {}),
        'terminal_pressure_runtime_override_status': dict(
            selected_model_certification.get('terminal_pressure_runtime_override_status') or {}
        ),
        'non_boss_terminal_pressure_closure': dict(
            selected_model_certification.get('non_boss_terminal_pressure_closure') or {}
        ),
        'contract': {
            'payload_owner': 'app.pipeline.build_boss_wave_milestone_matrix',
            'row_owner': 'app.pipeline.build_boss_wave_payload',
            'simulator_owner': 'simulators.evaluator_kernel.evaluate_overlay_row',
            'scope': 'milestone_all_tiers_best_loadout_by_dissonant_run_category',
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification': selected_model_certification,
            'selection_policy': 'complete candidates first, then highest selected_max_wave across named loadout presets',
            'ids_reference_alignment_policy': (
                'clean_rows_empirically_aligned_to_ids_reference'
                if bool(align_clean_reference_rows)
                else 'comparison_only_requested'
            ),
        },
        'preset_name': 'Milestone',
        'tiers': [int(tier) for tier in tiers],
        'end_wave': int(end_wave),
        'boss_wave_step': int(boss_wave_step),
        'stop_on_failure': bool(stop_on_failure),
        'scenario_runtime_inputs': runtime_inputs,
        'scenario_runtime_input_sources': runtime_input_sources,
        'ids_reference_alignment_enabled': bool(align_clean_reference_rows),
        'model_certification': selected_model_certification,
        'model_accuracy_summary': model_accuracy_summary,
        'tracker_reference_evidence': tracker_reference_evidence,
        'model_blocker_summary': model_blocker_summary,
        'reference_alignment_summary': reference_alignment_summary,
        'reference_quality_summary': reference_quality_summary,
        'pressure_factor_hint_summary': pressure_factor_hint_summary,
        'reference_gap_summary': reference_gap_summary,
        'replacement_primitive_family_coverage_summary': primitive_family_coverage_summary,
        'contact_time_contract': {
            'boss_time_to_contact_seconds': {
                'value': runtime_inputs.get('boss_time_to_contact_seconds'),
                'source': runtime_input_sources.get(
                    'boss_time_to_contact_seconds',
                    'per_candidate_derived_geometry_displayed_proxy_base_cf_slow_aura_energy_net',
                ),
                'ownership': 'runtime_input_override_or_per_candidate_geometry_proxy_simulator_derivation',
                'derived_by_simulator': 'boss_time_to_contact_seconds' not in runtime_inputs,
                'geometry_proxy_status': (
                    None
                    if 'boss_time_to_contact_seconds' in runtime_inputs
                    else 'per_candidate_displayed_proxy_base'
                ),
                'geometry_proxy_truth_status': (
                    None
                    if 'boss_time_to_contact_seconds' in runtime_inputs
                    else 'displayed_proxy_candidate_not_wall_contact_truth'
                ),
                'matrix_default_is_uncertified_assumption': (
                    runtime_input_sources.get('boss_time_to_contact_seconds') == 'matrix_default_assumption'
                ),
            },
        },
        'loadout_policy_presets': list(policy_presets),
        'dissonance_run_categories': list(categories),
        'rows': rows,
        'wide_rows': wide_rows,
    }
    if comparison_scenario_runtime_inputs:
        comparison_runtime_inputs = dict(runtime_inputs)
        comparison_runtime_inputs.update(dict(comparison_scenario_runtime_inputs))
        comparison_matrix = build_boss_wave_milestone_matrix(
            request,
            tiers=tuple(int(tier) for tier in tiers),
            end_wave=int(end_wave),
            boss_wave_step=int(boss_wave_step),
            stop_on_failure=bool(stop_on_failure),
            scenario_runtime_inputs=comparison_runtime_inputs,
            comparison_scenario_runtime_inputs=None,
            comparison_label=comparison_label,
            loadout_policy_presets=policy_presets,
            dissonance_run_categories=categories,
            align_clean_reference_rows=bool(align_clean_reference_rows),
        )
        comparison_wide_by_tier = {
            int(row.get('tier') or 0): row
            for row in comparison_matrix.get('wide_rows') or []
        }
        comparison_rows: list[dict[str, object]] = []
        for base_wide in wide_rows:
            tier_number = int(base_wide.get('tier') or 0)
            bridge_wide = dict(comparison_wide_by_tier.get(tier_number) or {})
            comparison_row: dict[str, object] = {
                'tier': tier_number,
                'tier_column': base_wide.get('tier_column'),
                'milestone_reference_wave': base_wide.get('milestone_reference_wave'),
            }
            for category in categories:
                category_key = 'regular' if category == 'none' else category
                base_wave = int(base_wide.get(f'{category_key}_wave') or 0)
                bridge_wave = int(bridge_wide.get(f'{category_key}_wave') or 0)
                comparison_row[f'{category_key}_default_wave'] = base_wave
                comparison_row[f'{category_key}_comparison_wave'] = bridge_wave
                comparison_row[f'{category_key}_delta_wave'] = bridge_wave - base_wave
                comparison_row[f'{category_key}_default_display'] = base_wide.get(f'{category_key}_display')
                comparison_row[f'{category_key}_comparison_display'] = bridge_wide.get(f'{category_key}_display')
                base_calculated_wave = base_wide.get(f'{category_key}_calculated_wave')
                bridge_calculated_wave = bridge_wide.get(f'{category_key}_calculated_wave')
                comparison_row[f'{category_key}_default_calculated_wave'] = base_calculated_wave
                comparison_row[f'{category_key}_comparison_calculated_wave'] = bridge_calculated_wave
                comparison_row[f'{category_key}_calculated_delta_wave'] = (
                    int(bridge_calculated_wave) - int(base_calculated_wave)
                    if base_calculated_wave is not None and bridge_calculated_wave is not None
                    else None
                )
                comparison_row[
                    f'{category_key}_default_calculated_delta_vs_reference_wave'
                ] = base_wide.get(f'{category_key}_calculated_delta_vs_reference_wave')
                comparison_row[
                    f'{category_key}_comparison_calculated_delta_vs_reference_wave'
                ] = bridge_wide.get(f'{category_key}_calculated_delta_vs_reference_wave')
                comparison_row[
                    f'{category_key}_default_calculated_to_reference_ratio'
                ] = base_wide.get(f'{category_key}_calculated_to_reference_ratio')
                comparison_row[
                    f'{category_key}_comparison_calculated_to_reference_ratio'
                ] = bridge_wide.get(f'{category_key}_calculated_to_reference_ratio')
                comparison_row[f'{category_key}_default_pressure_factor_hint'] = base_wide.get(
                    f'{category_key}_pressure_factor_hint'
                )
                comparison_row[f'{category_key}_comparison_pressure_factor_hint'] = bridge_wide.get(
                    f'{category_key}_pressure_factor_hint'
                )
                comparison_row[f'{category_key}_default_pressure_factor_hint_direction'] = base_wide.get(
                    f'{category_key}_pressure_factor_hint_direction'
                )
                comparison_row[f'{category_key}_comparison_pressure_factor_hint_direction'] = bridge_wide.get(
                    f'{category_key}_pressure_factor_hint_direction'
                )
                for lane_suffix in (
                    'hit_by_hit_wave',
                    'contact_envelope_wave',
                    'pre_contact_boss_kill_wave',
                    'gc_pre_contact_wave',
                    'reference_nearest_lane',
                    'reference_nearest_lane_label',
                    'reference_nearest_lane_wave',
                    'reference_nearest_lane_delta_vs_reference_wave',
                    'reference_nearest_lane_abs_delta_wave',
                    'terminal_pressure_reference_status',
                ):
                    comparison_row[f'{category_key}_default_{lane_suffix}'] = base_wide.get(
                        f'{category_key}_{lane_suffix}'
                    )
                    comparison_row[f'{category_key}_comparison_{lane_suffix}'] = bridge_wide.get(
                        f'{category_key}_{lane_suffix}'
                    )
                comparison_row[f'{category_key}_default_terminal_pressure_limiter'] = base_wide.get(
                    f'{category_key}_terminal_pressure_limiter'
                )
                comparison_row[f'{category_key}_comparison_terminal_pressure_limiter'] = bridge_wide.get(
                    f'{category_key}_terminal_pressure_limiter'
                )
                comparison_row[f'{category_key}_default_unsupported_pressure_reference_limited'] = bool(
                    base_wide.get(f'{category_key}_unsupported_pressure_reference_limited')
                )
                comparison_row[f'{category_key}_comparison_unsupported_pressure_reference_limited'] = bool(
                    bridge_wide.get(f'{category_key}_unsupported_pressure_reference_limited')
                )
                comparison_row[f'{category_key}_default_unsupported_pressure_reference_aligned'] = bool(
                    base_wide.get(f'{category_key}_unsupported_pressure_reference_aligned')
                )
                comparison_row[f'{category_key}_comparison_unsupported_pressure_reference_aligned'] = bool(
                    bridge_wide.get(f'{category_key}_unsupported_pressure_reference_aligned')
                )
                comparison_row[
                    f'{category_key}_default_unsupported_pressure_reference_alignment_direction'
                ] = base_wide.get(f'{category_key}_unsupported_pressure_reference_alignment_direction')
                comparison_row[
                    f'{category_key}_comparison_unsupported_pressure_reference_alignment_direction'
                ] = bridge_wide.get(f'{category_key}_unsupported_pressure_reference_alignment_direction')
                comparison_row[f'{category_key}_default_unsupported_pressure_missing_reference_blocked'] = bool(
                    base_wide.get(f'{category_key}_unsupported_pressure_missing_reference_blocked')
                )
                comparison_row[f'{category_key}_comparison_unsupported_pressure_missing_reference_blocked'] = bool(
                    bridge_wide.get(f'{category_key}_unsupported_pressure_missing_reference_blocked')
                )
                comparison_row[f'{category_key}_default_unsupported_pressure_uncapped_wave'] = base_wide.get(
                    f'{category_key}_unsupported_pressure_uncapped_wave'
                )
                comparison_row[f'{category_key}_comparison_unsupported_pressure_uncapped_wave'] = bridge_wide.get(
                    f'{category_key}_unsupported_pressure_uncapped_wave'
                )
            comparison_rows.append(comparison_row)
        comparison_calculated_delta_summary = _boss_wave_matrix_comparison_calculated_delta_summary(comparison_rows)
        payload['comparison'] = {
            'label': str(comparison_label or 'bridge_assumptions'),
            'scenario_runtime_inputs': comparison_runtime_inputs,
            'runtime_input_overrides': dict(comparison_scenario_runtime_inputs),
            'base_scenario_runtime_inputs': dict(runtime_inputs),
            'matrix': comparison_matrix,
            'calculated_delta_summary': comparison_calculated_delta_summary,
            'wide_rows': comparison_rows,
        }
    return payload


def _build_replacement_operator_table_and_summary(
    *,
    active_source: str,
    config: dict[str, object],
    account_state,
    preset_name: str,
    perk_counts: dict[str, int],
    perk_timeline: tuple[dict[str, object], ...],
    scenario_runtime_inputs: dict[str, float],
    stop_on_failure: bool,
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object], dict[str, object]]:
    from qe.run_plan import (
        CommonTrajectoryInputs,
        SurvivabilityContributorBundle,
        build_common_trajectory,
        default_category_track_order,
        workshop_value_for_level,
    )
    from qe.kb_surfaces import ELECTRON_BOSS_REMAINING_HP_PCT
    from simulators.evaluator_kernel import (
        CombatInputs,
        KernelAmbiguityError,
        ScenarioOverlayInputs,
        ScenarioSurvivabilityTransforms,
        evaluate_overlay_row,
    )
    from simulators.scenario import normalize_els_reduction_to_fraction, overheat_enemy_skip_decay_schedule

    loadout_profile_preset = str(config.get('loadout_profile_preset') or preset_name)
    workshop_levels, track_max_levels = _boss_wave_workshop_level_inputs(account_state, preset_name=loadout_profile_preset)
    primitives = _resolve_boss_wave_replacement_primitives_cached(
        account_state=account_state,
        preset_name=loadout_profile_preset,
        config=config,
        perks_enabled=bool(config['perks_enabled']),
        scenario_runtime_inputs=scenario_runtime_inputs,
        workshop_levels=workshop_levels,
    )
    dissonance_run_category = _normalize_boss_wave_dissonance_run_category(
        config.get('dissonance_run_category') or 'none'
    )
    dissonance_mask = _boss_wave_apply_dissonance_run_mask(
        dissonance_run_category,
        primitives=primitives,
        workshop_levels=workshop_levels,
        track_max_levels=track_max_levels,
    )
    runtime_inputs = ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs)
    scenario_surfaces = dict(config.get('scenario_surfaces') or {})
    boss_ttk_defaults = _boss_wave_default_ttk_inputs(
        runtime_inputs,
        primitives=primitives,
        electron_boss_remaining_hp_pct=float(ELECTRON_BOSS_REMAINING_HP_PCT),
    )
    boss_contact_geometry_proxy = boss_wall_travel_displayed_proxy_from_tower_range(
        tower_range_theoretical_m=primitives.get('tower_range_m'),
    )
    geometry_base_contact_time_seconds = (
        boss_contact_geometry_proxy.get('boss_contact_time_displayed_proxy_seconds')
        if boss_contact_geometry_proxy.get('status') == 'resolved_displayed_proxy_candidate'
        else None
    )
    boss_time_to_contact_seconds, boss_time_to_contact_source, boss_time_to_contact_components = (
        timing_boss_contact_time_seconds(
            explicit_contact_time_seconds=getattr(runtime_inputs, 'boss_time_to_contact_seconds'),
            chrono_field_duration_seconds=primitives.get('chrono_field_duration_seconds'),
            chrono_field_cooldown_seconds=primitives.get('chrono_field_cooldown_seconds'),
            chrono_field_slow_pct=primitives.get('chrono_field_slow_pct'),
            slow_aura_enemy_speed_pct=primitives.get('slow_aura_enemy_speed_pct'),
            enemy_speed_increase_pct=scenario_surfaces.get('bc_enemy_speed_increase_pct'),
            boss_speed_multiplier=scenario_surfaces.get('env_boss_speed_multiplier'),
            energy_net_duration_seconds=primitives.get('energy_net_duration_seconds'),
            geometry_base_contact_time_seconds=geometry_base_contact_time_seconds,
            geometry_base_components=boss_contact_geometry_proxy,
        )
    )
    boss_hit_interval_seconds, boss_hit_interval_source, boss_hit_interval_components = timing_boss_hit_interval_seconds(
        explicit_hit_interval_seconds=getattr(runtime_inputs, 'boss_hit_interval_seconds'),
        scenario_base_seconds=scenario_surfaces.get('boss_hit_interval_seconds'),
        slow_aura_mastery_attack_interval_multiplier=primitives.get(
            'slow_aura_mastery_attack_interval_multiplier'
        ),
    )
    primitives['boss_time_to_contact_seconds'] = boss_time_to_contact_seconds
    primitives['boss_time_to_contact_source'] = boss_time_to_contact_source
    primitives['boss_time_to_contact_base_seconds'] = boss_time_to_contact_components['base_seconds']
    primitives['boss_time_to_contact_chrono_field_average_slow_fraction'] = boss_time_to_contact_components[
        'chrono_field_average_slow_fraction'
    ]
    primitives['boss_time_to_contact_slow_aura_fraction'] = boss_time_to_contact_components['slow_aura_fraction']
    primitives['boss_time_to_contact_enemy_speed_increase_fraction'] = boss_time_to_contact_components[
        'enemy_speed_increase_fraction'
    ]
    primitives['boss_time_to_contact_boss_speed_multiplier'] = boss_time_to_contact_components[
        'boss_speed_multiplier'
    ]
    primitives['boss_time_to_contact_movement_speed_multiplier'] = boss_time_to_contact_components[
        'movement_speed_multiplier'
    ]
    primitives['boss_time_to_contact_speed_remaining_fraction'] = boss_time_to_contact_components[
        'speed_remaining_fraction'
    ]
    primitives['boss_time_to_contact_energy_net_hold_seconds'] = boss_time_to_contact_components[
        'energy_net_hold_seconds'
    ]
    primitives['boss_time_to_contact_base_seconds_source'] = boss_time_to_contact_components[
        'base_seconds_source'
    ]
    primitives['boss_time_to_contact_geometry_proxy_status'] = boss_time_to_contact_components[
        'geometry_base_status'
    ]
    primitives['boss_time_to_contact_geometry_proxy_truth_status'] = boss_time_to_contact_components[
        'geometry_proxy_truth_status'
    ]
    primitives['boss_time_to_contact_geometry_tower_range_theoretical_m'] = boss_time_to_contact_components.get(
        'geometry_tower_range_theoretical_m'
    )
    primitives['boss_time_to_contact_geometry_tower_range_displayed_m'] = boss_time_to_contact_components.get(
        'geometry_tower_range_displayed_m'
    )
    primitives['boss_time_to_contact_geometry_wall_radius_displayed_m'] = boss_time_to_contact_components.get(
        'geometry_wall_radius_displayed_m'
    )
    primitives['boss_time_to_contact_geometry_path_distance_to_wall_displayed_candidate_m'] = (
        boss_time_to_contact_components.get('geometry_path_distance_to_wall_displayed_candidate_m')
    )
    primitives['boss_time_to_contact_geometry_reference_path_distance_to_wall_displayed_m'] = (
        boss_time_to_contact_components.get('geometry_reference_path_distance_to_wall_displayed_m')
    )
    primitives['boss_hit_interval_seconds'] = boss_hit_interval_seconds
    primitives['boss_hit_interval_source'] = boss_hit_interval_source
    primitives['boss_hit_interval_scenario_base_seconds'] = boss_hit_interval_components['scenario_base_seconds']
    primitives['boss_hit_interval_slow_aura_mastery_multiplier'] = boss_hit_interval_components[
        'slow_aura_mastery_attack_interval_multiplier'
    ]
    tower_defense_pct = float(primitives['tower_defense_pct'])
    death_wave_health_max_multiplier = _boss_wave_death_wave_health_max_multiplier(
        account_state,
        scenario_runtime_inputs=scenario_runtime_inputs,
    )
    if dissonance_run_category == 'ultimate_weapons':
        death_wave_health_max_multiplier = 1.0
    death_wave_health_max_wave = int(
        _optional_runtime_float(scenario_runtime_inputs, 'death_wave_health_max_wave') or 1000
    )
    timed_dr_by_lane, timed_dr_sources = _boss_wave_timed_dr_inputs(runtime_inputs, primitives=primitives)
    bh_dr_pct = float(timed_dr_sources['black_hole_pbh']['damage_reduction_pct'])
    bh_duration_seconds = float(timed_dr_sources['black_hole_pbh']['duration_seconds'])
    bh_cooldown_seconds = float(timed_dr_sources['black_hole_pbh']['cooldown_seconds'])
    bh_explicit_uptime_fraction = (
        float(timed_dr_sources['black_hole_pbh']['uptime_fraction'])
        if timed_dr_sources['black_hole_pbh'].get('uptime_source') == 'explicit_uptime_fraction'
        else None
    )
    cf_dr_pct = float(primitives['chrono_field_damage_reduction_pct'])
    cf_duration_seconds = float(primitives['chrono_field_duration_seconds'])
    cf_cooldown_seconds = float(primitives['chrono_field_cooldown_seconds'])
    category_track_order = default_category_track_order(workshop_levels, track_max_levels)
    tower_hp_level = _boss_wave_optional_workshop_level(workshop_levels, 'Health', primitive_name='state::tower.hp')
    wall_hp_level = _boss_wave_optional_workshop_level(workshop_levels, 'Wall Health', primitive_name='state::wall.hp')
    wall_regen_level = _boss_wave_optional_workshop_level(workshop_levels, 'Health Regen', primitive_name='state::wall.regen')
    wall_fortification_multiplier = float(primitives['wall_fortification_multiplier'])
    if wall_fortification_multiplier <= 0.0:
        raise ValueError("Boss Waves replacement input state::wall.fortification_multiplier must be positive")
    wall_hp_value = float(primitives['wall_hp'])
    wall_regen_value = float(primitives['wall_regen'])
    wall_hp_workshop_percent_points = (
        workshop_value_for_level('Wall Health', wall_hp_level)
        if wall_hp_level and wall_hp_level > 0
        else 0.0
    )
    tower_hp_workshop_value = (
        workshop_value_for_level('Health', tower_hp_level)
        if tower_hp_level and tower_hp_level > 0
        else 0.0
    )
    survivability = SurvivabilityContributorBundle(
        base_wall_hp=0.0 if wall_hp_level and wall_hp_level > 0 else wall_hp_value,
        workshop_wall_hp=wall_hp_value if wall_hp_level and wall_hp_level > 0 else 0.0,
        wall_hp_workshop_track='Wall Health' if wall_hp_level and wall_hp_level > 0 else None,
        wall_hp_workshop_baseline_level=wall_hp_level if wall_hp_level and wall_hp_level > 0 else None,
        wall_hp_workshop_value_per_level=float(primitives['wall_hp_per_workshop_level_pre_fort']) if wall_hp_level and wall_hp_level > 0 else 0.0,
        wall_hp_static_ratio_percent_points=max(
            0.0,
            float(primitives['wall_hp_percent_points']) - float(wall_hp_workshop_percent_points),
        ),
        wall_hp_effect_multiplier=float(primitives['wall_hp_multiplier']),
        tower_hp_workshop_track='Health' if tower_hp_level and tower_hp_level > 0 and tower_hp_workshop_value > 0 else None,
        tower_hp_workshop_baseline_level=tower_hp_level if tower_hp_level and tower_hp_level > 0 else None,
        tower_hp_workshop_multiplier=(float(primitives['tower_hp']) / float(tower_hp_workshop_value)) if tower_hp_workshop_value > 0 else 1.0,
        base_wall_regen=0.0 if wall_regen_level and wall_regen_level > 0 else wall_regen_value,
        workshop_wall_regen=wall_regen_value if wall_regen_level and wall_regen_level > 0 else 0.0,
        wall_regen_workshop_track='Health Regen' if wall_regen_level and wall_regen_level > 0 else None,
        wall_regen_workshop_baseline_level=wall_regen_level if wall_regen_level and wall_regen_level > 0 else None,
        wall_regen_workshop_value_per_level=(wall_regen_value / float(wall_regen_level)) if wall_regen_level and wall_regen_level > 0 else 0.0,
        wall_fortification_multiplier=wall_fortification_multiplier,
        tower_defense_pct=tower_defense_pct,
        tower_defense_absolute=float(primitives['tower_defense_absolute']),
        timed_dr_by_lane=timed_dr_by_lane,
        black_hole_damage_reduction_pct=bh_dr_pct,
        black_hole_duration_seconds=bh_duration_seconds,
        black_hole_cooldown_seconds=bh_cooldown_seconds,
        black_hole_explicit_uptime_fraction=bh_explicit_uptime_fraction,
        chrono_field_damage_reduction_pct=cf_dr_pct,
        chrono_field_duration_seconds=cf_duration_seconds,
        chrono_field_cooldown_seconds=cf_cooldown_seconds,
        source_policy='explicit_staged_contributors_v1',
    )
    perk_counts_by_wave = _boss_wave_perk_counts_by_wave(perk_timeline)
    perk_contributions_by_wave = _boss_wave_perk_contributions_by_wave(
        perk_counts_by_wave,
        standard_bonus_pct=float((getattr(account_state, 'labs', {}) or {}).get('Standard Perks Bonus') or 0.0),
        tradeoff_bonus_pct=float((getattr(account_state, 'labs', {}) or {}).get('Improve Trade-off Perks') or 0.0),
    )
    static_perk_contributions = _boss_wave_perk_contributions_for_counts(
        perk_counts,
        standard_bonus_pct=float((getattr(account_state, 'labs', {}) or {}).get('Standard Perks Bonus') or 0.0),
        tradeoff_bonus_pct=float((getattr(account_state, 'labs', {}) or {}).get('Improve Trade-off Perks') or 0.0),
    )
    runtime_skip_reduction = getattr(runtime_inputs, 'enemy_level_skip_reduction_pp')
    skip_reduction_raw = (
        float(runtime_skip_reduction)
        if runtime_skip_reduction is not None
        else float(scenario_surfaces.get('bc_enemy_level_skip_reduction_pp') or 0.0)
    )
    skip_reduction_fraction = normalize_els_reduction_to_fraction(skip_reduction_raw)
    skip_delta = -skip_reduction_fraction
    overheat_start_wave = int(
        getattr(runtime_inputs, 'enemy_level_skip_decay_start_wave') or scenario_surfaces.get('overheat_start_wave') or 0
    )
    skip_decay_fraction = normalize_els_reduction_to_fraction(
        getattr(runtime_inputs, 'enemy_level_skip_decay_pct')
    )
    skip_decay_interval = int(getattr(runtime_inputs, 'enemy_level_skip_decay_interval_waves') or 0)
    skip_decay_schedule: dict[int, float] = {}
    skip_decay_source = 'not_active'
    if skip_decay_fraction > 0.0 and skip_decay_interval > 0:
        skip_decay_source = 'scenario_runtime_input'
    elif overheat_start_wave > 0:
        skip_decay_schedule = overheat_enemy_skip_decay_schedule()
        skip_decay_source = 'kb.tournaments.tables.battle-condition-magnitudes.csv:enemy_level_skip'
    if (
        str(config.get('mode_id') or '') == 'tournament'
        and getattr(runtime_inputs, 'enemy_level_skip_reduction_pp') is None
    ):
        skip_decay_schedule = overheat_enemy_skip_decay_schedule()
        skip_decay_source = 'kb.tournaments.tables.battle-condition-magnitudes.csv:enemy_level_skip'
        overheat_start_wave = 0
        skip_delta = 0.0
        skip_reduction_raw = 0.0
        skip_reduction_fraction = 0.0
    tower_damage_decay_fraction = normalize_els_reduction_to_fraction(
        getattr(runtime_inputs, 'tower_damage_decay_pct')
    )
    tower_damage_decay_start_wave = int(
        getattr(runtime_inputs, 'tower_damage_decay_start_wave') or scenario_surfaces.get('overheat_start_wave') or 0
    )
    tower_health_decay_fraction = normalize_els_reduction_to_fraction(
        getattr(runtime_inputs, 'tower_health_decay_pct')
    )
    tower_health_decay_start_wave = int(
        getattr(runtime_inputs, 'tower_health_decay_start_wave') or scenario_surfaces.get('overheat_start_wave') or 0
    )
    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=int(config['start_wave']),
            end_wave=int(config['end_wave']),
            boss_interval_waves=int(config['boss_interval_waves']),
            checkpoint_every_bosses=int(config['checkpoint_every_bosses']),
            tier_column=str(config['tier_column']),
            attack_skip_chance=float(primitives['attack_skip_chance']),
            health_skip_chance=float(primitives['health_skip_chance']),
            attack_skip_chance_delta=skip_delta,
            health_skip_chance_delta=skip_delta,
            enemy_skip_decay_start_wave=overheat_start_wave if (skip_decay_fraction > 0.0 and skip_decay_interval > 0) or skip_decay_schedule else 0,
            enemy_skip_decay_fraction_per_step=skip_decay_fraction,
            enemy_skip_decay_interval_waves=skip_decay_interval,
            enemy_skip_decay_schedule=skip_decay_schedule,
            attack_skip_static_percent_points=float(primitives['attack_skip_static_percent_points']),
            attack_skip_multiplier=float(primitives['attack_skip_multiplier']),
            attack_skip_workshop_track=str(primitives['attack_skip_workshop_track'] or ''),
            attack_skip_workshop_baseline_level=int(primitives['attack_skip_workshop_baseline_level']),
            health_skip_static_percent_points=float(primitives['health_skip_static_percent_points']),
            health_skip_multiplier=float(primitives['health_skip_multiplier']),
            health_skip_workshop_track=str(primitives['health_skip_workshop_track'] or ''),
            health_skip_workshop_baseline_level=int(primitives['health_skip_workshop_baseline_level']),
            free_upgrade_chance_by_category={
                'attack': float(primitives['free_attack_upgrade_chance']),
                'defense': float(primitives['free_defense_upgrade_chance']),
                'utility': float(primitives['free_utility_upgrade_chance']),
            },
            category_track_order=category_track_order,
            track_max_levels=track_max_levels,
            workshop_levels=workshop_levels,
            perk_counts=dict(perk_counts),
            perk_contributions=static_perk_contributions,
            perk_counts_by_wave=perk_counts_by_wave,
            perk_contributions_by_wave=perk_contributions_by_wave,
            survivability_contributors=survivability,
            death_wave_health_max_multiplier=death_wave_health_max_multiplier,
            death_wave_health_max_wave=death_wave_health_max_wave,
        )
    )
    runtime_incoming_mult = getattr(runtime_inputs, 'incoming_damage_multiplier')
    incoming_mult = (
        float(runtime_incoming_mult)
        if runtime_incoming_mult is not None
        else float(scenario_surfaces.get('env_enemy_damage_multiplier') or 1.0)
    )
    boss_wave_pressure_factor = _runtime_nonnegative_float(runtime_inputs, 'boss_wave_pressure_factor')
    if boss_wave_pressure_factor is None:
        boss_wave_pressure_factor = 1.0
    incoming_mult *= float(boss_wave_pressure_factor)
    boss_health_multiplier = (
        float(scenario_surfaces.get('env_boss_health_multiplier') or 1.0)
        * float(boss_wave_pressure_factor)
    )
    primitives['incoming_damage_multiplier'] = float(incoming_mult)
    primitives['boss_health_multiplier'] = float(boss_health_multiplier)
    primitives['boss_wave_pressure_factor'] = float(boss_wave_pressure_factor)
    wall_thorns_damage_increase_per_hit = _boss_wave_wall_thorns_damage_increase_per_hit(
        account_state,
        preset_name=loadout_profile_preset,
    )
    if 'wall_thorns_damage_increase_per_hit' in primitives:
        wall_thorns_damage_increase_per_hit = max(
            0.0,
            float(primitives['wall_thorns_damage_increase_per_hit'] or 0.0),
        )
    _boss_wave_apply_default_edamage_boss_runtime_factors(primitives)
    scenario = ScenarioOverlayInputs(
        scenario_key='boss_waves_replacement_product',
        tier_column=str(config['tier_column']),
        tournament_perks_enabled=bool(config['perks_enabled']),
        tower_damage_decay_start_wave=tower_damage_decay_start_wave if tower_damage_decay_fraction > 0.0 else 0,
        tower_damage_decay_fraction_per_step=tower_damage_decay_fraction,
        tower_damage_decay_interval_waves=10,
        tower_health_decay_start_wave=tower_health_decay_start_wave if tower_health_decay_fraction > 0.0 else 0,
        tower_health_decay_fraction_per_step=tower_health_decay_fraction,
        tower_health_decay_interval_waves=10,
        survivability_transforms=ScenarioSurvivabilityTransforms(
            incoming_damage_multiplier=incoming_mult,
            enemy_health_multiplier=boss_health_multiplier,
        ),
    )
    combat = CombatInputs(
        plasma_cannon_effect_pct=float(primitives['plasma_cannon_effect_pct']),
        tower_thorns_damage_pct=float(primitives['wall_thorns_contact_damage_pct']),
        continuous_boss_damage_per_second=float(
            primitives.get('boss_damage_per_second') or primitives.get('gc_boss_damage_per_second') or 0.0
        ),
        continuous_boss_damage_multiplier=float(primitives.get('energy_net_mastery_multiplier') or 1.0),
        continuous_boss_damage_multiplier_duration_seconds=float(primitives.get('energy_net_damage_multiplier_duration_seconds') or 0.0),
        orb_boss_hit_pct=float(getattr(runtime_inputs, 'orb_boss_hit_pct') or 0.0),
        orb_boss_total_damage_pct=(
            0.0
            if dissonance_run_category == 'defense'
            else float(boss_ttk_defaults['orb_boss_total_damage_pct'])
        ),
        orb_boss_hit_count=getattr(runtime_inputs, 'orb_boss_hit_count'),
        electron_total_damage_pct=(
            0.0
            if dissonance_run_category == 'defense'
            else float(boss_ttk_defaults['electron_total_damage_pct'])
        ),
        electron_hit_count=getattr(runtime_inputs, 'electron_hit_count'),
        boss_time_to_contact_seconds=boss_time_to_contact_seconds,
        boss_hit_interval_seconds=boss_hit_interval_seconds,
        energy_shield_hit_charges=float(primitives.get('energy_shield_effective_charge_count') or 0.0),
        max_ttk_seconds=600.0,
        plasma_cannon_resistance_multiplier=float(scenario_surfaces.get('bc_plasma_cannon_resistance') or 1.0),
        orb_resistance_multiplier=float(scenario_surfaces.get('bc_orb_resistance') or 1.0),
        thorns_resistance_multiplier=float(scenario_surfaces.get('bc_thorns_resistance') or 1.0),
        wall_thorns_damage_increase_per_hit=wall_thorns_damage_increase_per_hit,
    )
    operator_rows: list[dict[str, object]] = []
    kernel_failure: dict[str, object] | None = None
    if combat.boss_time_to_contact_seconds is None:
        contact_error = KernelAmbiguityError(
            "boss_time_to_contact_seconds is required for the self-closing Boss Waves farming path; "
            "no owned scenario/QE primitive currently defines boss spawn-to-wall contact time"
        )
        if bool(stop_on_failure):
            raise contact_error
        first_row = table1.rows[0] if table1.rows else None
        kernel_failure = {
            'status': 'incomplete',
            'failure_kind': 'kernel_ambiguity',
            'failure_message': str(contact_error),
            'first_unresolved_wave': int(first_row.display_wave) if first_row is not None else None,
        }
    for table1_row in table1.rows:
        if kernel_failure:
            break
        try:
            overlay = evaluate_overlay_row(table1_row, scenario=scenario, combat=combat)
        except KernelAmbiguityError as exc:
            if bool(stop_on_failure):
                raise
            kernel_failure = {
                'status': 'incomplete',
                'failure_kind': 'kernel_ambiguity',
                'failure_message': str(exc),
                'first_unresolved_wave': int(table1_row.display_wave),
            }
            break
        flame_bot_lifetime_components: dict[str, object] | None = None
        flame_bot_lifetime_row = _boss_wave_flame_bot_lifetime_row_timed_dr(
            primitives=primitives,
            timed_dr_sources=timed_dr_sources,
            boss_lifetime_seconds=overlay.summary_combat.ttk_seconds,
            boss_hits_to_player=overlay.summary_combat.boss_hits_taken,
            boss_hit_interval_seconds=boss_hit_interval_seconds,
        )
        if flame_bot_lifetime_row is not None:
            lifetime_timed_dr_by_lane, _, flame_bot_lifetime_components = flame_bot_lifetime_row
            current_timed_dr_by_lane = {
                str(lane_id): float(value)
                for lane_id, value in table1_row.survivability_contributors.timed_dr_by_lane.items()
            }
            if any(
                abs(float(lifetime_timed_dr_by_lane.get(lane_id, 0.0)) - current_timed_dr_by_lane.get(lane_id, 0.0)) > 1e-12
                for lane_id in ('min', 'avg', 'max')
            ):
                lifetime_survivability = replace(
                    table1_row.survivability_contributors,
                    timed_dr_by_lane=lifetime_timed_dr_by_lane,
                )
                lifetime_table1_row = replace(
                    table1_row,
                    survivability_contributors=lifetime_survivability,
                )
                overlay = evaluate_overlay_row(lifetime_table1_row, scenario=scenario, combat=combat)
        operator_row = _replacement_operator_row_from_overlay(
            overlay=overlay,
            active_source=active_source,
            combat=combat,
            primitives=primitives,
            incoming_damage_multiplier=incoming_mult,
        )
        _boss_wave_add_flame_bot_lifetime_row_fields(
            operator_row,
            timed_dr_sources=timed_dr_sources,
            lifetime_components=flame_bot_lifetime_components,
        )
        operator_rows.append(operator_row)
        if (
            bool(stop_on_failure)
            and not bool(operator_rows[-1].get('survives_boss'))
            and not bool(operator_rows[-1].get('contact_envelope_survives_boss'))
        ):
            break
    semantic_ledger = _boss_wave_primitive_semantics_ledger(
        primitives=primitives,
        workshop_levels=workshop_levels,
        track_max_levels=track_max_levels,
        lab_levels=getattr(account_state, 'labs', {}) or {},
        row_input_wall_hp=wall_hp_value,
        row_input_wall_regen=wall_regen_value,
        timed_dr_sources=timed_dr_sources,
        death_wave_health_max_multiplier=death_wave_health_max_multiplier,
        death_wave_health_max_wave=death_wave_health_max_wave,
        boss_ttk_defaults=boss_ttk_defaults,
        wall_thorns_damage_increase_per_hit=wall_thorns_damage_increase_per_hit,
    )
    summary = _replacement_summary_from_operator_rows(
        operator_rows,
        perk_policy_preset=str(config.get('perk_policy_preset') or ''),
        terminal_pressure_limits=_boss_wave_terminal_pressure_limits(runtime_inputs),
    )
    _apply_dissonance_selected_lane_constraints(
        summary,
        dissonance_run_category=dissonance_run_category,
    )
    scenario_surfaces = dict(config.get('scenario_surfaces') or {})
    _apply_unsupported_terminal_pressure_reference_limit(
        summary,
        account_state=account_state,
        tier_number=int(config['tier_number']),
        dissonance_run_category=dissonance_run_category,
        unsupported_terminal_pressures=scenario_surfaces.get('unsupported_terminal_pressures') or (),
        runtime_inputs=runtime_inputs,
    )
    if kernel_failure:
        selected_first_failed = int(summary.get('selected_first_failed_wave') or 0)
        first_unresolved = int(kernel_failure.get('first_unresolved_wave') or 0)
        if selected_first_failed > 0 and first_unresolved > selected_first_failed:
            summary.update(
                {
                    'status': 'complete',
                    'failure_kind': None,
                    'failure_message': None,
                    'first_unresolved_wave': first_unresolved,
                    'post_failure_truncation_kind': str(kernel_failure.get('failure_kind') or ''),
                    'post_failure_truncation_message': str(kernel_failure.get('failure_message') or ''),
                }
            )
        else:
            summary.update(kernel_failure)
    else:
        summary.setdefault('status', 'complete')
    returned_primitives = dict(primitives)
    returned_primitives.update({
        'enemy_level_skip_reduction_raw': skip_reduction_raw,
        'enemy_level_skip_reduction_fraction': skip_reduction_fraction,
        'enemy_level_skip_chance_delta': skip_delta,
        'enemy_level_skip_decay_fraction_per_step': skip_decay_fraction,
        'enemy_level_skip_decay_interval_waves': skip_decay_interval,
        'enemy_level_skip_decay_start_wave': overheat_start_wave if (skip_decay_fraction > 0.0 and skip_decay_interval > 0) or skip_decay_schedule else 0,
        'enemy_level_skip_decay_schedule': skip_decay_schedule,
        'enemy_level_skip_decay_source': skip_decay_source,
        'tower_damage_decay_fraction_per_step': tower_damage_decay_fraction,
        'tower_damage_decay_start_wave': tower_damage_decay_start_wave if tower_damage_decay_fraction > 0.0 else 0,
        'tower_health_decay_fraction_per_step': tower_health_decay_fraction,
        'tower_health_decay_start_wave': tower_health_decay_start_wave if tower_health_decay_fraction > 0.0 else 0,
        'dissonance_run_category': dissonance_run_category,
    })
    if dissonance_mask:
        returned_primitives['dissonance_run_mask'] = dict(dissonance_mask)
        semantic_ledger['dissonance_run_mask'] = dict(dissonance_mask)
        summary['dissonance_run_category'] = dissonance_run_category
        summary['dissonance_run_label'] = _BOSS_WAVE_DISSONANCE_RUN_LABELS[dissonance_run_category]
    return operator_rows, summary, returned_primitives, semantic_ledger


def _boss_wave_apply_dissonance_run_mask(
    category: str,
    *,
    primitives: dict[str, object],
    workshop_levels: dict[str, int],
    track_max_levels: dict[str, int],
) -> dict[str, object]:
    normalized = _normalize_boss_wave_dissonance_run_category(category)
    if normalized == 'none':
        return {
            'category': 'none',
            'label': _BOSS_WAVE_DISSONANCE_RUN_LABELS['none'],
            'applied': False,
            'disabled_runtime_systems': [],
            'restricted_primitives': {},
            'zeroed_workshop_tracks': [],
            'conditional_primitive_restrictions': {},
        }

    restricted_primitives: dict[str, object] = {}
    zeroed_tracks: list[str] = []
    disabled_systems: list[str] = []
    conditional_primitive_restrictions: dict[str, dict[str, object]] = {}
    spec = _boss_wave_dissonance_restriction_spec(normalized)

    def restrict_primitive(key: str, value: object) -> None:
        if isinstance(value, str):
            primitives[key] = value
            restricted_primitives[key] = value
            return
        primitives[key] = float(value)
        restricted_primitives[key] = float(value)

    def zero_track(track_name: str) -> None:
        if track_name not in zeroed_tracks:
            zeroed_tracks.append(track_name)
        if track_name in workshop_levels:
            workshop_levels[track_name] = 0
        if track_name in track_max_levels:
            track_max_levels[track_name] = 0

    for key, value in dict(spec.get('primitive_restrictions') or {}).items():
        restrict_primitive(str(key), value)
    for track in sorted(str(track) for track in (spec.get('zero_workshop_tracks') or ())):
        zero_track(track)
    disabled_systems.extend(str(item) for item in (spec.get('disabled_runtime_systems') or ()))
    for key, conditional in dict(spec.get('conditional_primitive_restrictions') or {}).items():
        conditional_payload = dict(conditional or {})
        unless_source = str(conditional_payload.get('unless_gc_boss_damage_source') or '')
        if key == 'gc_boss_damage_per_second' and primitives.get('gc_boss_damage_source') == unless_source:
            continue
        restrict_primitive(str(key), conditional_payload.get('value', 0.0))
        conditional_primitive_restrictions[str(key)] = conditional_payload
        masked_source = str(conditional_payload.get('masked_source') or '')
        if key == 'gc_boss_damage_per_second' and masked_source:
            primitives['boss_damage_per_second'] = primitives.get('gc_boss_damage_per_second')
            primitives['boss_damage_source'] = masked_source
            primitives['gc_boss_damage_source'] = masked_source
    return {
        'category': normalized,
        'label': _BOSS_WAVE_DISSONANCE_RUN_LABELS[normalized],
        'applied': normalized != 'none',
        'disabled_runtime_systems': disabled_systems,
        'restricted_primitives': restricted_primitives,
        'zeroed_workshop_tracks': zeroed_tracks,
        'conditional_primitive_restrictions': conditional_primitive_restrictions,
    }


def _boss_wave_card_source_preset(account_state, *, preset_name: str) -> str:
    card_presets = getattr(account_state, 'card_presets', {}) or {}
    if preset_name in card_presets:
        return preset_name
    fallback_preset = str(getattr(account_state, 'default_preset', None) or 'Farming')
    if fallback_preset in card_presets:
        return fallback_preset
    return 'Farming'


def _boss_wave_account_state_with_card_profile(
    account_state,
    *,
    target_preset_name: str,
    card_profile_preset: str,
):
    target = str(target_preset_name or '').strip()
    source = str(card_profile_preset or '').strip()
    if not target or not source or source == target:
        return account_state
    card_presets = getattr(account_state, 'card_presets', {}) or {}
    source_cards = card_presets.get(source)
    if source_cards is None:
        return account_state
    updated_card_presets = {str(name): list(cards or []) for name, cards in card_presets.items()}
    updated_card_presets[target] = list(source_cards or [])
    return replace(account_state, card_presets=updated_card_presets, active_card_preset=target)


def _boss_wave_effect_families_from_surface_id(surface_id: str) -> tuple[str, ...]:
    text = str(surface_id or '').strip().lower()
    families: set[str] = set()
    if text.startswith('state::bot.'):
        families.add('bot')
    if text.startswith('state::cards.') or text == 'state::capability.energy_shield.enabled':
        if 'mastery' in text:
            families.add('card_mastery')
        else:
            families.add('card_base')
    if text == 'derived::edamage.super_tower_factor':
        families.update(('card_base', 'card_mastery'))
    if (
        text.startswith('state::module.')
        or text.startswith('support_surface::module.')
        or text.startswith('module::')
        or text == 'derived::edamage.project_funding_factor'
    ):
        families.add('module')
    return tuple(family for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS if family in families)


def _boss_wave_effect_families_from_contributor(contributor: Mapping[str, object]) -> tuple[str, ...]:
    contributor_id = str(contributor.get('contributor_id') or '').strip().lower()
    fields = (
        contributor.get('source_family'),
        contributor.get('source_class'),
        contributor.get('source_name'),
        contributor.get('input_id'),
        contributor.get('contributor_id'),
    )
    text = ' '.join(str(value or '').strip().lower() for value in fields if value is not None)
    families: set[str] = set()
    if 'workshop' in text or contributor_id.startswith('workshop__'):
        families.add('workshop')
    if 'enhancement' in text or contributor_id.startswith('enhancements__'):
        families.add('enhancement')
    if 'relic' in text or contributor_id.startswith('relic__'):
        families.add('relic')
    if 'module' in text or contributor_id.startswith('module__'):
        families.add('module')
    if 'bot' in text or contributor_id.startswith('bot__'):
        families.add('bot')
    if 'card' in text or 'cards' in text or contributor_id.startswith('card__') or contributor_id.startswith('cards__'):
        if 'mastery' in text:
            families.add('card_mastery')
        else:
            families.add('card_base')
    return tuple(family for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS if family in families)


def _boss_wave_add_family_coverage_evidence(
    coverage: dict[str, dict[str, set[str]]],
    family: str,
    *,
    evidence_kind: str,
    state_mode: str,
    surface_id: str,
    contributor: Mapping[str, object] | None = None,
) -> None:
    row = coverage[family]
    row['evidence_kinds'].add(str(evidence_kind))
    row['state_modes'].add(str(state_mode))
    row['surface_ids'].add(str(surface_id))
    if contributor is None:
        return
    contributor_id = str(contributor.get('contributor_id') or '').strip()
    source_class = str(contributor.get('source_class') or '').strip()
    source_family = str(contributor.get('source_family') or '').strip()
    if contributor_id:
        row['contributor_ids'].add(contributor_id)
    if source_class:
        row['source_classes'].add(source_class)
    if source_family:
        row['source_families'].add(source_family)


def _boss_wave_replacement_primitive_family_coverage(
    *,
    primitive_surface_ids: tuple[str, ...],
    statbook,
    damage_statbook,
    damage_state_mode: str,
    damage_perks_enabled: bool,
) -> dict[str, object]:
    coverage: dict[str, dict[str, set[str]]] = {
        family: {
            'evidence_kinds': set(),
            'state_modes': set(),
            'surface_ids': set(),
            'contributor_ids': set(),
            'source_classes': set(),
            'source_families': set(),
        }
        for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS
    }
    relevant_surface_ids = set(str(surface_id) for surface_id in primitive_surface_ids)
    relevant_surface_ids.update(BOSS_WAVE_CONSUMED_DERIVED_PRIMITIVE_SURFACE_IDS)
    statbook_entries: list[tuple[str, object]] = [('start_of_run', statbook)]
    if damage_statbook is not statbook or str(damage_state_mode) != 'start_of_run':
        statbook_entries.append((str(damage_state_mode), damage_statbook))
    observed_surface_count = 0
    observed_contributor_count = 0
    for state_mode, current_statbook in statbook_entries:
        for surface_id, row in (getattr(current_statbook, 'rows', {}) or {}).items():
            surface_key = str(surface_id)
            if surface_key not in relevant_surface_ids:
                continue
            if str(getattr(row, 'status', '') or '').strip() != 'resolved':
                continue
            observed_surface_count += 1
            for family in _boss_wave_effect_families_from_surface_id(surface_key):
                _boss_wave_add_family_coverage_evidence(
                    coverage,
                    family,
                    evidence_kind='resolved_qe_surface',
                    state_mode=state_mode,
                    surface_id=surface_key,
                )
            for raw_contributor in getattr(row, 'contributors', None) or ():
                contributor = dict(raw_contributor or {})
                if not bool(contributor.get('active', True)):
                    continue
                contributor_families = _boss_wave_effect_families_from_contributor(contributor)
                if not contributor_families:
                    continue
                observed_contributor_count += 1
                for family in contributor_families:
                    _boss_wave_add_family_coverage_evidence(
                        coverage,
                        family,
                        evidence_kind='active_qe_contributor',
                        state_mode=state_mode,
                        surface_id=surface_key,
                        contributor=contributor,
                    )
    family_rows: dict[str, dict[str, object]] = {}
    for family in BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS:
        row = coverage[family]
        has_surface = 'resolved_qe_surface' in row['evidence_kinds']
        has_contributor = 'active_qe_contributor' in row['evidence_kinds']
        if has_surface and has_contributor:
            coverage_status = 'covered_by_qe_surface_and_contributor'
        elif has_contributor:
            coverage_status = 'covered_by_qe_contributor'
        elif has_surface:
            coverage_status = 'covered_by_qe_surface'
        else:
            coverage_status = 'not_observed_in_selected_payload'
        family_rows[family] = {
            'coverage_status': coverage_status,
            'evidence_kinds': sorted(row['evidence_kinds']),
            'state_modes': sorted(row['state_modes']),
            'surface_count': len(row['surface_ids']),
            'contributor_count': len(row['contributor_ids']),
            'surface_ids': sorted(row['surface_ids'])[:24],
            'contributor_ids': sorted(row['contributor_ids'])[:24],
            'source_classes': sorted(row['source_classes'])[:24],
            'source_families': sorted(row['source_families'])[:24],
        }
    missing = [
        family
        for family, row in family_rows.items()
        if row['coverage_status'] == 'not_observed_in_selected_payload'
    ]
    return {
        'scope': 'boss_waves_replacement_primitive_boundary',
        'owner_path': 'QE resolves requested primitive surfaces and contributors; app.pipeline records carry-through diagnostics; simulators consume assembled primitives',
        'status': 'covered' if not missing else 'partial_selected_payload',
        'requested_effect_families': list(BOSS_WAVE_REPLACEMENT_EFFECT_FAMILY_IDS),
        'missing_requested_families': missing,
        'observed_resolved_surface_count': observed_surface_count,
        'observed_active_contributor_evidence_count': observed_contributor_count,
        'requested_surface_count': len(tuple(dict.fromkeys(primitive_surface_ids))),
        'damage_state_mode': str(damage_state_mode),
        'damage_perks_enabled': bool(damage_perks_enabled),
        'families': family_rows,
        'caveat': (
            'This is selected Boss Waves payload boundary evidence, not a second stat authority. '
            'Full route closure remains governed by the generated family completeness artifact, '
            'and source-owned non-boss terminal-pressure formulas remain the full max-wave blocker.'
        ),
    }


def _resolve_boss_wave_replacement_primitives(
    *,
    account_state,
    preset_name: str,
    config: dict[str, object],
    perks_enabled: bool,
    scenario_runtime_inputs: dict[str, float],
    workshop_levels: Mapping[str, int],
) -> dict[str, object]:
    from qe.run_plan import (
        derive_wall_hp_from_qe_primitives,
        derive_wall_regen_hp_per_second,
    )
    from simulators.scenario import ScenarioConfig
    from simulators.timing import resolve_timing_consumer_bundle

    primitive_profile_preset = str(config.get('loadout_profile_preset') or preset_name)
    primitive_preset_name = _boss_wave_workshop_source_preset(account_state, preset_name=primitive_profile_preset)
    primitive_card_profile_preset = _boss_wave_card_source_preset(
        account_state,
        preset_name=str(config.get('card_profile_preset') or primitive_profile_preset),
    )
    primitive_account_state = _boss_wave_account_state_with_card_profile(
        account_state,
        target_preset_name=primitive_preset_name,
        card_profile_preset=primitive_card_profile_preset,
    )
    scenario_context = {
        'mode_id': str(config.get('mode_id') or 'farming'),
        'tier': int(config.get('tier_number') or 1),
        'league': config.get('league'),
        'tournament_wave': config.get('tournament_wave'),
        'dissonance_run_category': str(config.get('dissonance_run_category') or 'none'),
    }
    primitive_surface_ids = _boss_wave_replacement_primitive_surface_ids(
        primitive_account_state,
        preset_name=primitive_preset_name,
    )
    manual_advisory_inputs = dict(config.get('manual_advisory_inputs') or {})
    survivability_projection_state = ScenarioProjectionState(second_wind_mastery_regen=True)
    response = resolve_checkpoint_surfaces(
        primitive_account_state,
        requested_surface_ids=primitive_surface_ids,
        preset_name=primitive_preset_name,
        card_preset_name=primitive_preset_name,
        module_preset_name=primitive_preset_name,
        state_mode='start_of_run',
        perks_enabled=False,
        scenario_projection_state=survivability_projection_state,
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs),
        scenario_context=scenario_context,
    )
    statbook = query_response_to_statbook(response, notes='Boss Waves replacement primitive resolution.')
    dissonance_run_category = _normalize_boss_wave_dissonance_run_category(
        config.get('dissonance_run_category') or 'none'
    )
    publish_query_surfaces(
        statbook.rows,
        manual_advisory_inputs=manual_advisory_inputs,
        account_state_labs=getattr(account_state, 'labs', {}) or {},
    )
    damage_statbook = statbook
    damage_state_mode = 'start_of_run'
    damage_perks_enabled = False
    if bool(perks_enabled):
        damage_response = resolve_checkpoint_surfaces(
            primitive_account_state,
            requested_surface_ids=primitive_surface_ids,
            preset_name=primitive_preset_name,
            card_preset_name=primitive_preset_name,
            module_preset_name=primitive_preset_name,
            state_mode='max_progression',
            perks_enabled=True,
            scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs),
            scenario_context=scenario_context,
        )
        damage_statbook = query_response_to_statbook(
            damage_response,
            notes='Boss Waves replacement active-policy damage primitive resolution.',
        )
        publish_query_surfaces(
            damage_statbook.rows,
            manual_advisory_inputs=manual_advisory_inputs,
            account_state_labs=getattr(account_state, 'labs', {}) or {},
        )
        damage_state_mode = 'max_progression'
        damage_perks_enabled = True
    chain_lightning_boss_dps = _optional_statbook_float(
        damage_statbook,
        'derived::edamage.uw.chain_lightning_dps',
        default=0.0,
    )
    qe_boss_applicable_cl_only_dps = _optional_statbook_float(
        damage_statbook,
        'derived::edamage_boss',
        default=chain_lightning_boss_dps,
    )
    edamage_ep = _optional_statbook_float(damage_statbook, 'derived::edamage_ep', default=0.0)
    ep_edamage_spotlight_factor = _optional_statbook_float(
        damage_statbook,
        'derived::edamage.spotlight_factor',
        default=1.0,
    )
    ep_edamage_acp_factor = _optional_statbook_float(
        damage_statbook,
        'derived::edamage.acp_factor',
        default=1.0,
    )
    ep_edamage_slow_factor = _optional_statbook_float(
        damage_statbook,
        'derived::edamage.slow_factor',
        default=1.0,
    )
    runtime_inputs = ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs)
    scenario_surfaces = dict(config.get('scenario_surfaces') or {})
    explicit_boss_dps = _runtime_nonnegative_float(runtime_inputs, 'boss_applicable_damage_per_second')
    explicit_boss_damage_factor = _runtime_nonnegative_float(runtime_inputs, 'boss_applicable_damage_factor')
    decomposed_boss_damage_factor = _boss_wave_decomposed_edamage_bridge_factor(runtime_inputs)
    if explicit_boss_dps is not None:
        gc_boss_damage_per_second = float(explicit_boss_dps)
        gc_boss_damage_source = 'runtime_input_boss_applicable_damage_per_second'
    elif explicit_boss_damage_factor is not None and explicit_boss_damage_factor > 0.0:
        gc_boss_damage_per_second = max(0.0, edamage_ep) * float(explicit_boss_damage_factor)
        gc_boss_damage_source = 'runtime_input_edamage_ep_times_boss_applicable_damage_factor'
    elif decomposed_boss_damage_factor is not None:
        gc_boss_damage_per_second = max(0.0, edamage_ep) * float(decomposed_boss_damage_factor)
        gc_boss_damage_source = 'runtime_input_edamage_ep_times_decomposed_boss_bridge'
    else:
        gc_boss_damage_per_second = qe_boss_applicable_cl_only_dps
        gc_boss_damage_source = 'qe_derived_edamage_boss_fail_closed_default'
    energy_net_duration_seconds = _optional_statbook_float(
        statbook,
        'state::cards.energy_net.duration_seconds',
        default=0.0,
    )
    energy_net_mastery_multiplier = _optional_statbook_float(
        statbook,
        'state::cards.energy_net.mastery_effect',
        default=1.0,
    )
    energy_net_damage_multiplier_duration_seconds = energy_net_mastery_damage_window_seconds(
        energy_net_duration_seconds=energy_net_duration_seconds,
        energy_net_mastery_multiplier=energy_net_mastery_multiplier,
    )
    energy_shield_enabled = _optional_statbook_bool(
        statbook,
        'state::capability.energy_shield.enabled',
        default=False,
    )
    energy_shield_recharge_cooldown_seconds = _optional_statbook_float(
        statbook,
        'state::cards.energy_shield.recharge_cooldown_seconds',
        default=0.0,
    )
    energy_shield_extra_charge_count = _optional_statbook_float(
        statbook,
        'state::cards.energy_shield.extra_charge_count',
        default=0.0,
    )
    energy_shield_base_charge_count = 1.0 if energy_shield_enabled else 0.0
    energy_shield_total_charge_count = (
        max(0.0, energy_shield_base_charge_count + energy_shield_extra_charge_count)
        if energy_shield_enabled
        else 0.0
    )
    energy_shields_down_fraction = max(
        0.0,
        min(1.0, float(scenario_surfaces.get('bc_energy_shields_down_fraction') or 0.0)),
    )
    energy_shield_effective_charge_count = math.floor(
        max(0.0, energy_shield_total_charge_count * (1.0 - energy_shields_down_fraction))
    )
    spotlight_bonus_multiplier = _optional_statbook_float(
        damage_statbook,
        'state::uw.spotlight.bonus_multiplier',
        default=1.0,
    )
    spotlight_count = _optional_statbook_float(
        damage_statbook,
        'state::uw.spotlight.count',
        default=0.0,
    )
    spotlight_angle_degrees = _optional_statbook_float(
        damage_statbook,
        'state::uw.spotlight.angle_degrees',
        default=0.0,
    )
    anti_cube_portal_shockwave_damage_taken_mult_x = _optional_statbook_float(
        statbook,
        'state::module.anti_cube_portal.shockwave_damage_taken_mult_x',
        default=0.0,
    )
    om_chip_equipped = _boss_wave_module_equipped(
        account_state,
        preset_name=primitive_preset_name,
        module_name='Om Chip',
    )
    attack_skip_seed = _boss_wave_skip_seed_from_qe_row(
        surface_id='state::tower.enemy_attack_level_skip_pct',
        statbook_row=_required_statbook_row(statbook, 'state::tower.enemy_attack_level_skip_pct'),
        workshop_levels=workshop_levels,
    )
    health_skip_seed = _boss_wave_skip_seed_from_qe_row(
        surface_id='state::tower.enemy_health_level_skip_pct',
        statbook_row=_required_statbook_row(statbook, 'state::tower.enemy_health_level_skip_pct'),
        workshop_levels=workshop_levels,
    )
    tower_hp_qe_surface = _required_statbook_float(statbook, 'state::tower.hp')
    tower_hp = _optional_statbook_float(
        statbook,
        'derived::ehp.health_factor',
        default=tower_hp_qe_surface,
    )
    tower_regen = _required_statbook_float(statbook, 'state::tower.regen')
    wall_hp_row = _required_statbook_row(statbook, 'state::wall.hp')
    wall_hp_derivation = derive_wall_hp_from_qe_primitives(
        tower_hp=tower_hp,
        wall_hp_contributors=tuple(dict(row or {}) for row in (getattr(wall_hp_row, 'contributors', None) or ())),
    )
    wall_regen_pct_points = _required_statbook_float(statbook, 'state::wall.regen')
    tower_thorns_damage_pct = _required_statbook_float(statbook, 'state::tower.thorns_damage_pct')
    wall_thorns_level = int((getattr(account_state, 'labs', {}) or {}).get('Wall Thorns') or 0)
    wall_thorns_contact_damage_pct = _required_statbook_float(statbook, 'state::wall.thorns_damage_pct')
    death_defy_chance_pct = _optional_statbook_float(
        statbook,
        'state::tower.death_defy_chance_pct',
        default=0.0,
    )
    death_defy_down_percent_points = float(scenario_surfaces.get('bc_death_defy_down_pp') or 0.0) * 100.0
    death_defy_effective_chance_pct = max(
        0.0,
        min(100.0, death_defy_chance_pct + death_defy_down_percent_points),
    )
    enemy_balance_mastery_double_elite_chance_pct = _optional_statbook_float(
        statbook,
        'state::cards.enemy_balance.mastery_effect',
        default=0.0,
    )
    scenario_config = config.get('scenario_config')
    if scenario_config is None:
        scenario_config = ScenarioConfig(
            mode_id=str(config.get('mode_id') or 'farming'),
            tier=int(config.get('tier_number') or 1),
            league=config.get('league'),
            tournament_wave=(int(config.get('tournament_wave') or 0) or None),
        )
    timing_family_id = 'timing_tournament_no_perks' if str(config.get('mode_id') or '') == 'tournament' else 'timing_scenario_probe'
    timing_wave_response = resolve_timing_consumer_bundle(
        account_state=account_state,
        consumer_id='run_stats',
        bundle_id='timing_wave_duration',
        family_id=timing_family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        perks_enabled=False,
        state_mode='start_of_run',
        include_optional_surface_ids=(
            'state::cards.wave_accelerator.spawn_rate_acceleration',
        ),
    )
    timing_wave_statbook = query_response_to_statbook(
        timing_wave_response,
        notes='Boss Waves replacement pressure timing primitive resolution.',
    )
    wave_accelerator_spawn_rate_acceleration = _optional_statbook_float(
        timing_wave_statbook,
        'state::cards.wave_accelerator.spawn_rate_acceleration',
        default=1.0,
    )
    if (
        'state::uw.black_hole.duration_seconds' in statbook.rows
        and 'state::uw.black_hole.cooldown_seconds' in statbook.rows
        and statbook.rows['state::uw.black_hole.duration_seconds'].final_value is not None
        and statbook.rows['state::uw.black_hole.cooldown_seconds'].final_value is not None
    ):
        black_hole_duration_seconds = _required_statbook_float(statbook, 'state::uw.black_hole.duration_seconds')
        black_hole_cooldown_seconds = _required_statbook_float(statbook, 'state::uw.black_hole.cooldown_seconds')
    else:
        timing_response = resolve_timing_consumer_bundle(
            account_state=account_state,
            consumer_id='run_stats',
            bundle_id='timing_core_cycle',
            family_id=timing_family_id,
            preset_name=preset_name,
            scenario_config=scenario_config,
            perks_enabled=False,
            state_mode='start_of_run',
        )
        timing_statbook = query_response_to_statbook(
            timing_response,
            notes='Boss Waves replacement effective UW timing primitive resolution.',
        )
        black_hole_duration_seconds = _required_statbook_float(timing_statbook, 'state::uw.black_hole.duration_seconds')
        black_hole_cooldown_seconds = _required_statbook_float(timing_statbook, 'state::uw.black_hole.cooldown_seconds')
    primitive_family_coverage = _boss_wave_replacement_primitive_family_coverage(
        primitive_surface_ids=primitive_surface_ids,
        statbook=statbook,
        damage_statbook=damage_statbook,
        damage_state_mode=damage_state_mode,
        damage_perks_enabled=damage_perks_enabled,
    )
    return {
        'loadout_profile_preset': primitive_preset_name,
        'card_profile_preset': primitive_card_profile_preset,
        'replacement_primitive_family_coverage': primitive_family_coverage,
        'survivability_projection_state': survivability_projection_state.to_debug_dict(),
        'bc_more_enemies_pct': float(scenario_surfaces.get('bc_more_enemies_pct') or 0.0),
        'wave_accelerator_spawn_rate_acceleration': float(
            wave_accelerator_spawn_rate_acceleration or 1.0
        ),
        'enemy_balance_mastery_double_elite_chance_pct': float(
            enemy_balance_mastery_double_elite_chance_pct or 0.0
        ),
        'attack_skip_chance': float(attack_skip_seed['chance_fraction']),
        'attack_skip_static_percent_points': float(attack_skip_seed['static_percent_points']),
        'attack_skip_multiplier': float(attack_skip_seed['multiplier']),
        'attack_skip_workshop_track': str(attack_skip_seed['workshop_track']),
        'attack_skip_workshop_baseline_level': int(attack_skip_seed['workshop_baseline_level']),
        'health_skip_chance': float(health_skip_seed['chance_fraction']),
        'health_skip_static_percent_points': float(health_skip_seed['static_percent_points']),
        'health_skip_multiplier': float(health_skip_seed['multiplier']),
        'health_skip_workshop_track': str(health_skip_seed['workshop_track']),
        'health_skip_workshop_baseline_level': int(health_skip_seed['workshop_baseline_level']),
        'free_attack_upgrade_chance': _required_statbook_fraction(statbook, 'state::tower.free_attack_upgrade_chance_pct'),
        'free_defense_upgrade_chance': _required_statbook_fraction(statbook, 'state::tower.free_defense_upgrade_chance_pct'),
        'free_utility_upgrade_chance': _required_statbook_fraction(statbook, 'state::tower.free_utility_upgrade_chance_pct'),
        'tower_damage': _optional_statbook_float(statbook, 'state::tower.damage', default=0.0),
        'tower_attack_speed': _optional_statbook_float(statbook, 'state::tower.attack_speed', default=0.0),
        'tower_crit_chance_pct': _optional_statbook_float(statbook, 'state::tower.crit_chance_pct', default=0.0),
        'tower_crit_multiplier': _optional_statbook_float(statbook, 'state::tower.crit_multiplier', default=1.0),
        'tower_range_m': _optional_statbook_float(statbook, 'state::tower.range_m', default=0.0),
        'tower_damage_per_meter_multiplier': _optional_statbook_float(statbook, 'state::tower.damage_per_meter_multiplier', default=0.0),
        'tower_shockwave_size_m': _optional_statbook_float(statbook, 'state::tower.shockwave_size_m', default=0.0),
        'tower_shockwave_interval_seconds': _optional_statbook_float(statbook, 'state::tower.shockwave_interval_seconds', default=0.0),
        'tower_multishot_chance_pct': _optional_statbook_float(statbook, 'state::tower.multishot_chance_pct', default=0.0),
        'tower_multishot_targets': _optional_statbook_float(statbook, 'state::tower.multishot_targets', default=0.0),
        'tower_rapid_fire_chance_pct': _optional_statbook_float(statbook, 'state::tower.rapid_fire_chance_pct', default=0.0),
        'tower_rapid_fire_duration_seconds': _optional_statbook_float(statbook, 'state::tower.rapid_fire_duration_seconds', default=0.0),
        'tower_bounce_shot_chance_pct': _optional_statbook_float(statbook, 'state::tower.bounce_shot_chance_pct', default=0.0),
        'tower_bounce_shot_targets': _optional_statbook_float(statbook, 'state::tower.bounce_shot_targets', default=0.0),
        'tower_bounce_shot_range_m': _optional_statbook_float(statbook, 'state::tower.bounce_shot_range_m', default=0.0),
        'tower_supercrit_chance_pct': _optional_statbook_float(statbook, 'state::tower.supercrit_chance_pct', default=0.0),
        'tower_supercrit_multiplier': _optional_statbook_float(statbook, 'state::tower.supercrit_multiplier', default=1.0),
        'tower_rend_armor_chance_pct': _optional_statbook_float(statbook, 'state::tower.rend_armor_chance_pct', default=0.0),
        'tower_rend_armor_multiplier': _optional_statbook_float(statbook, 'state::tower.rend_armor_multiplier', default=1.0),
        'tower_max_rend_multiplier': _optional_statbook_float(statbook, 'state::tower.max_rend_multiplier', default=1.0),
        'dissonance_attack_active_boost_multiplier': _optional_statbook_float(statbook, 'state::dissonance.attack.active_boost_multiplier', default=1.0),
        'dissonance_attack_echo_source_bonus': _optional_statbook_float(statbook, 'state::dissonance.attack.echo_source_bonus', default=0.0),
        'dissonance_attack_echo_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.attack.echo_multiplier', default=0.0),
        'dissonance_attack_echo_bonus_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.attack.echo_bonus_multiplier', default=0.0),
        'dissonance_attack_total_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.attack.total_multiplier', default=1.0),
        'dissonance_defense_active_boost_multiplier': _optional_statbook_float(statbook, 'state::dissonance.defense.active_boost_multiplier', default=1.0),
        'dissonance_defense_echo_source_bonus': _optional_statbook_float(statbook, 'state::dissonance.defense.echo_source_bonus', default=0.0),
        'dissonance_defense_echo_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.defense.echo_multiplier', default=0.0),
        'dissonance_defense_echo_bonus_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.defense.echo_bonus_multiplier', default=0.0),
        'dissonance_defense_total_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.defense.total_multiplier', default=1.0),
        'dissonance_utility_active_boost_multiplier': _optional_statbook_float(statbook, 'state::dissonance.utility.active_boost_multiplier', default=1.0),
        'dissonance_utility_echo_source_bonus': _optional_statbook_float(statbook, 'state::dissonance.utility.echo_source_bonus', default=0.0),
        'dissonance_utility_echo_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.utility.echo_multiplier', default=0.0),
        'dissonance_utility_echo_bonus_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.utility.echo_bonus_multiplier', default=0.0),
        'dissonance_utility_total_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.utility.total_multiplier', default=1.0),
        'dissonance_ultimate_weapons_active_boost_multiplier': _optional_statbook_float(statbook, 'state::dissonance.ultimate_weapons.active_boost_multiplier', default=1.0),
        'dissonance_ultimate_weapons_echo_source_bonus': _optional_statbook_float(statbook, 'state::dissonance.ultimate_weapons.echo_source_bonus', default=0.0),
        'dissonance_ultimate_weapons_echo_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.ultimate_weapons.echo_multiplier', default=0.0),
        'dissonance_ultimate_weapons_echo_bonus_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.ultimate_weapons.echo_bonus_multiplier', default=0.0),
        'dissonance_ultimate_weapons_total_multiplier': _optional_statbook_float(statbook, 'derived::dissonance.ultimate_weapons.total_multiplier', default=1.0),
        'edamage_attack_dissonance_factor': _optional_statbook_float(damage_statbook, 'derived::edamage.attack_dissonance_factor', default=1.0),
        'edamage_attack_dissonance_restricted': _optional_statbook_float(statbook, 'derived::edamage.attack_dissonance_restricted', default=0.0),
        'edamage_uw_dissonance_factor': _optional_statbook_float(damage_statbook, 'derived::edamage.uw_dissonance_factor', default=1.0),
        'ehp_defense_dissonance_factor': _optional_statbook_float(statbook, 'derived::ehp.defense_dissonance_factor', default=1.0),
        'edamage_defense_dissonance_shockwave_restricted': _optional_statbook_float(statbook, 'derived::edamage.defense_dissonance_shockwave_restricted', default=0.0),
        'tower_hp': tower_hp,
        'tower_hp_qe_surface': tower_hp_qe_surface,
        'tower_regen': tower_regen,
        'wall_hp_qe_surface': _required_statbook_float(statbook, 'state::wall.hp'),
        'wall_hp': float(wall_hp_derivation['wall_hp_pre_fort']),
        'wall_hp_percent_points': float(wall_hp_derivation['wall_hp_percent_points']),
        'wall_hp_ratio': float(wall_hp_derivation['wall_hp_ratio']),
        'wall_hp_multiplier': float(wall_hp_derivation['wall_hp_multiplier']),
        'wall_hp_per_workshop_level_pre_fort': float(wall_hp_derivation['wall_hp_per_workshop_level_pre_fort']),
        'wall_regen': derive_wall_regen_hp_per_second(
            tower_regen_hp_per_second=tower_regen,
            wall_regen_percent_points=wall_regen_pct_points,
        ),
        'wall_regen_percent_points': wall_regen_pct_points,
        'wall_fortification_multiplier': _required_statbook_float(statbook, 'state::wall.fortification_multiplier'),
        'tower_defense_pct': _required_statbook_float(statbook, 'state::tower.defense_pct'),
        'tower_defense_absolute': _optional_statbook_float(statbook, 'state::tower.defense_absolute', default=0.0),
        'tower_thorns_damage_pct': tower_thorns_damage_pct,
        'wall_thorns_level': float(wall_thorns_level),
        'wall_thorns_contact_damage_pct': wall_thorns_contact_damage_pct,
        'death_defy_chance_pct': death_defy_chance_pct,
        'death_defy_down_percent_points': death_defy_down_percent_points,
        'death_defy_effective_chance_pct': death_defy_effective_chance_pct,
        'death_defy_model_policy': 'diagnostic_only_stochastic_survival_not_applied_to_deterministic_boss_contact_ttd',
        'tower_orb_count': _optional_statbook_float(statbook, 'state::tower.orb_count', default=0.0),
        'tower_orb_speed_rpm': _optional_statbook_float(statbook, 'state::tower.orb_speed_rpm', default=0.0),
        'plasma_cannon_effect_pct': _required_statbook_float(statbook, 'state::cards.plasma_cannon.effect_pct'),
        'chain_lightning_boss_damage_per_second': chain_lightning_boss_dps,
        'qe_boss_applicable_cl_only_damage_per_second': qe_boss_applicable_cl_only_dps,
        'edamage_boss_base_damage_per_second': qe_boss_applicable_cl_only_dps,
        'edamage_boss_base_cl_damage_per_second': qe_boss_applicable_cl_only_dps,
        'edamage_ep': edamage_ep,
        'edamage': edamage_ep,
        'ep_edamage_spotlight_factor': ep_edamage_spotlight_factor,
        'ep_edamage_acp_factor': ep_edamage_acp_factor,
        'ep_edamage_slow_factor': ep_edamage_slow_factor,
        'super_tower_active': _optional_statbook_bool(damage_statbook, 'state::cards.super_tower.active', default=False),
        'super_tower_bonus_multiplier': _optional_statbook_float(damage_statbook, 'state::cards.super_tower.bonus_multiplier', default=1.0),
        'super_tower_cooldown_seconds': _optional_statbook_float(damage_statbook, 'state::cards.super_tower.cooldown_seconds', default=0.0),
        'super_tower_mastery_active': _optional_statbook_bool(damage_statbook, 'state::cards.super_tower.mastery_active', default=False),
        'super_tower_uw_mastery_multiplier': _optional_statbook_float(damage_statbook, 'state::cards.super_tower.uw_mastery_multiplier', default=1.0),
        'edamage_super_tower_factor': _optional_statbook_float(damage_statbook, 'derived::edamage.super_tower_factor', default=1.0),
        'project_funding_cash_digit_multiplier_pct': _optional_statbook_float(damage_statbook, 'state::module.project_funding.cash_digit_multiplier_pct', default=0.0),
        'project_funding_current_cash': _optional_statbook_float(damage_statbook, 'support_surface::module.project_funding.current_cash', default=0.0),
        'edamage_project_funding_factor': _optional_statbook_float(damage_statbook, 'derived::edamage.project_funding_factor', default=1.0),
        'boss_damage_state_mode': damage_state_mode,
        'boss_damage_perks_enabled': 1.0 if damage_perks_enabled else 0.0,
        'dissonance_attack_run_active': _optional_statbook_bool(statbook, 'support_surface::dissonance.attack_run_active'),
        'dissonance_defense_run_active': _optional_statbook_bool(statbook, 'support_surface::dissonance.defense_run_active'),
        'dissonance_utility_run_active': _optional_statbook_bool(statbook, 'support_surface::dissonance.utility_run_active'),
        'dissonance_ultimate_weapons_run_active': _optional_statbook_bool(statbook, 'support_surface::dissonance.ultimate_weapons_run_active'),
        'boss_applicable_damage_factor': float(explicit_boss_damage_factor or 0.0),
        'boss_edamage_target_share': float(runtime_inputs.boss_edamage_target_share or 0.0),
        'boss_edamage_cadence_uptime_factor': float(runtime_inputs.boss_edamage_cadence_uptime_factor or 0.0),
        'boss_edamage_reliability_factor': float(runtime_inputs.boss_edamage_reliability_factor or 0.0),
        'boss_edamage_semantic_normalizer': float(runtime_inputs.boss_edamage_semantic_normalizer or 0.0),
        'boss_edamage_decomposed_bridge_factor': float(decomposed_boss_damage_factor or 0.0),
        'boss_damage_per_second': gc_boss_damage_per_second,
        'boss_damage_source': gc_boss_damage_source,
        'gc_boss_damage_per_second': gc_boss_damage_per_second,
        'gc_boss_damage_source': gc_boss_damage_source,
        'energy_net_duration_seconds': energy_net_duration_seconds,
        'energy_net_mastery_multiplier': energy_net_mastery_multiplier,
        'energy_net_damage_multiplier_duration_seconds': energy_net_damage_multiplier_duration_seconds,
        'energy_shield_enabled': energy_shield_enabled,
        'energy_shield_recharge_cooldown_seconds': energy_shield_recharge_cooldown_seconds,
        'energy_shield_base_charge_count': energy_shield_base_charge_count,
        'energy_shield_extra_charge_count': energy_shield_extra_charge_count,
        'energy_shield_total_charge_count': energy_shield_total_charge_count,
        'energy_shields_down_fraction': energy_shields_down_fraction,
        'energy_shield_effective_charge_count': float(energy_shield_effective_charge_count),
        'spotlight_bonus_multiplier': spotlight_bonus_multiplier,
        'spotlight_count': spotlight_count,
        'spotlight_angle_degrees': spotlight_angle_degrees,
        'om_chip_equipped': om_chip_equipped,
        'anti_cube_portal_shockwave_damage_taken_mult_x': anti_cube_portal_shockwave_damage_taken_mult_x,
        'orbital_augment_electron_count': _optional_statbook_float(statbook, 'state::module.orbital_augment.electron_count', default=0.0),
        'primordial_collapse_bh_damage_reduction_pct': _optional_statbook_float(statbook, 'state::module.primordial_collapse.bh_damage_reduction_pct', default=0.0),
        'black_hole_duration_seconds': black_hole_duration_seconds,
        'black_hole_cooldown_seconds': black_hole_cooldown_seconds,
        'black_hole_base_duration_seconds': _optional_statbook_float(statbook, 'state::uw.black_hole.base_duration_seconds', default=black_hole_duration_seconds),
        'black_hole_base_cooldown_seconds': _optional_statbook_float(statbook, 'state::uw.black_hole.base_cooldown_seconds', default=black_hole_cooldown_seconds),
        'golden_tower_base_duration_seconds': _optional_statbook_float(statbook, 'state::uw.golden_tower.base_duration_seconds', default=0.0),
        'golden_tower_base_cooldown_seconds': _optional_statbook_float(statbook, 'state::uw.golden_tower.base_cooldown_seconds', default=0.0),
        'chrono_field_duration_seconds': _required_statbook_float(statbook, 'state::uw.chrono_field.duration_seconds'),
        'chrono_field_cooldown_seconds': _required_statbook_float(statbook, 'state::uw.chrono_field.cooldown_seconds'),
        'chrono_field_damage_reduction_pct': _required_statbook_float(statbook, 'state::uw.chrono_field.damage_reduction_pct'),
        'chrono_field_slow_pct': _required_statbook_float(statbook, 'state::uw.chrono_field.slow_pct'),
        'slow_aura_enemy_speed_pct': _optional_statbook_float(statbook, 'state::cards.slow_aura.enemy_speed_pct', default=0.0),
        'slow_aura_mastery_attack_interval_multiplier': _optional_statbook_float(statbook, 'state::cards.slow_aura.mastery_effect', default=1.0),
        'flame_bot_owned': _optional_statbook_bool(statbook, 'state::bot.flame.owned', default=False),
        'flame_bot_damage_reduction_pct': _optional_statbook_float(statbook, 'state::bot.flame.damage_reduction_pct', default=0.0),
        'flame_bot_cooldown_seconds': _optional_statbook_float(statbook, 'state::bot.flame.cooldown_seconds', default=0.0),
        'flame_bot_range_m': _optional_statbook_float(statbook, 'state::bot.flame.range_m', default=0.0),
        'flame_bot_effective_range_m': _optional_statbook_float(statbook, 'state::bot.flame.effective_range_m', default=0.0),
    }


def _boss_wave_workshop_level_inputs(account_state, *, preset_name: str) -> tuple[dict[str, int], dict[str, int]]:
    workshop = getattr(account_state, 'workshop', {}) or {}
    levels: dict[str, int] = {}
    max_levels: dict[str, int] = {}
    source_preset = _boss_wave_workshop_source_preset(account_state, preset_name=preset_name)
    for track_name, entry in workshop.items():
        preset_levels = getattr(entry, 'preset_levels', {}) or {}
        level = preset_levels.get(source_preset)
        max_level = getattr(entry, 'max_level', None)
        if level is None or max_level is None:
            continue
        levels[str(track_name)] = int(level)
        max_levels[str(track_name)] = int(max_level)
    return levels, max_levels


def _boss_wave_workshop_source_preset(account_state, *, preset_name: str) -> str:
    if preset_name in {'Farming', 'Tourney'}:
        return preset_name
    workshop = getattr(account_state, 'workshop', {}) or {}
    if any((getattr(entry, 'preset_levels', {}) or {}).get(preset_name) is not None for entry in workshop.values()):
        return preset_name
    fallback_preset = str(getattr(account_state, 'default_preset', None) or 'Farming')
    if any((getattr(entry, 'preset_levels', {}) or {}).get(fallback_preset) is not None for entry in workshop.values()):
        return fallback_preset
    return 'Farming'


def _boss_wave_uw_track_value(account_state, uw_name: str, track_name: str) -> float:
    weapon = (getattr(account_state, 'ultimate_weapons', {}) or {}).get(uw_name)
    if weapon is not None and str(getattr(weapon, 'unlocked', '') or '').strip().lower() not in {'true', 'yes', '1'}:
        return 0.0
    for track in (getattr(account_state, 'uw_tracks', {}) or {}).get(uw_name, []) or []:
        if str(getattr(track, 'track_name', '') or '').strip() == track_name:
            value = getattr(track, 'resolved_value', None)
            return float(value or 0.0)
    return 0.0


def _boss_wave_optional_workshop_level(
    workshop_levels: dict[str, int],
    track_name: str,
    *,
    primitive_name: str,
) -> int | None:
    if not workshop_levels:
        return None
    if track_name not in workshop_levels:
        raise ValueError(f"Boss Waves replacement input {primitive_name!r} requires workshop track {track_name!r}")
    return int(workshop_levels[track_name])


def _boss_wave_skip_seed_from_qe_row(
    *,
    surface_id: str,
    statbook_row,
    workshop_levels: Mapping[str, int],
) -> dict[str, object]:
    from qe.run_plan import workshop_value_for_level

    contributors = tuple(dict(row or {}) for row in (getattr(statbook_row, 'contributors', None) or ()))
    if not contributors:
        raise ValueError(f"Boss Waves skip surface {surface_id!r} is missing contributor metadata")
    if any(str(contributor.get('contributor_id') or '').startswith('dissonance_restriction_override::') for contributor in contributors):
        return {
            'chance_fraction': 0.0,
            'static_percent_points': 0.0,
            'multiplier': 1.0,
            'workshop_track': '',
            'workshop_baseline_level': 0,
        }
    workshop_track = _BOSS_WAVE_SKIP_WORKSHOP_TRACK_BY_SURFACE.get(surface_id)
    if not workshop_track:
        raise ValueError(f"Boss Waves skip surface {surface_id!r} has no workshop-track mapping")
    if workshop_track not in workshop_levels:
        raise ValueError(f"Boss Waves skip surface {surface_id!r} requires workshop level for {workshop_track!r}")
    static_percent_points = 0.0
    multiplier = 1.0
    saw_workshop = False
    for contributor in contributors:
        if not bool(contributor.get('active', True)):
            continue
        value = float(contributor.get('value') or 0.0)
        contributor_id = str(contributor.get('contributor_id') or '')
        stage = str(contributor.get('composition_stage') or '')
        if contributor_id.startswith('workshop__tower__') and contributor_id.endswith('__pct'):
            saw_workshop = True
            continue
        if stage == 'additive_pre_cap':
            static_percent_points += value
            continue
        if stage == 'multiplicative':
            multiplier *= value
            continue
        raise ValueError(
            f"unsupported Boss Waves skip contributor semantics for {surface_id!r} contributor {contributor_id!r}"
        )
    if not saw_workshop:
        raise ValueError(f"Boss Waves skip surface {surface_id!r} is missing its workshop contributor")
    baseline_level = int(workshop_levels[workshop_track])
    baseline_workshop_value = workshop_value_for_level(workshop_track, baseline_level)
    reconstructed = (static_percent_points + baseline_workshop_value) * multiplier
    final_value = float(getattr(statbook_row, 'final_value', 0.0) or 0.0)
    if abs(reconstructed - final_value) > 1e-6:
        raise ValueError(
            f"Boss Waves skip seed mismatch for {surface_id!r}: reconstructed {reconstructed} != resolved {final_value}"
        )
    return {
        'chance_fraction': reconstructed / 100.0,
        'static_percent_points': static_percent_points,
        'multiplier': multiplier,
        'workshop_track': workshop_track,
        'workshop_baseline_level': baseline_level,
    }


def _boss_wave_perk_counts_by_wave(perk_timeline: tuple[dict[str, object], ...]) -> dict[int, dict[str, int]]:
    counts: dict[str, int] = {}
    out: dict[int, dict[str, int]] = {}
    for row in sorted(perk_timeline, key=lambda item: int(item.get('wave') or 0)):
        wave = int(row.get('wave') or 0)
        perk_name = row.get('perk_taken') or row.get('picked_perk') or row.get('perk_name')
        if not perk_name:
            continue
        counts[str(perk_name)] = counts.get(str(perk_name), 0) + 1
        out[wave] = dict(counts)
    return out


def _boss_wave_static_perk_counts_from_account_state(account_state) -> dict[str, int]:
    active_preset = getattr(account_state, 'active_perk_preset', None)
    if not active_preset:
        return {}
    preset = (getattr(account_state, 'perk_presets', {}) or {}).get(active_preset) or ()
    entities = load_perk_entities()
    counts: dict[str, int] = {}
    for selection in preset:
        perk_id = str(getattr(selection, 'perk_id', '') or '').strip()
        if not perk_id and isinstance(selection, dict):
            perk_id = str(selection.get('perk_id') or '').strip()
        if not perk_id:
            continue
        raw_picks = getattr(selection, 'picks', None)
        if raw_picks is None and isinstance(selection, dict):
            raw_picks = selection.get('picks')
        try:
            picks = int(raw_picks or 0)
        except (TypeError, ValueError):
            picks = 0
        if picks <= 0:
            continue
        perk_name = str((entities.get(perk_id) or {}).get('perk_name') or '').strip()
        if not perk_name:
            raise ValueError(f"Boss Waves max_progression_policy references unknown perk id {perk_id!r}")
        counts[perk_name] = counts.get(perk_name, 0) + picks
    return counts


def _boss_wave_perk_contributions_for_counts(
    perk_counts: dict[str, int],
    *,
    standard_bonus_pct: float,
    tradeoff_bonus_pct: float,
) -> dict[str, float]:
    if not perk_counts:
        return {}
    return _boss_wave_perk_contributions_by_wave(
        {0: dict(perk_counts)},
        standard_bonus_pct=standard_bonus_pct,
        tradeoff_bonus_pct=tradeoff_bonus_pct,
    ).get(0, {})


def _boss_wave_perk_contributions_by_wave(
    perk_counts_by_wave: dict[int, dict[str, int]],
    *,
    standard_bonus_pct: float,
    tradeoff_bonus_pct: float,
) -> dict[int, dict[str, float]]:
    entities = load_perk_entities()
    effects = load_perk_effects()
    name_to_id = {
        str(meta.get('perk_name') or '').strip(): str(perk_id)
        for perk_id, meta in entities.items()
        if str(meta.get('perk_name') or '').strip()
    }
    perk_lab_state = {
        'standard_bonus_multiplier': 1.0 + (float(standard_bonus_pct) / 100.0),
        'tradeoff_bonus_multiplier': 1.0 + (float(tradeoff_bonus_pct) / 100.0),
    }
    target_to_contribution = {
        'tower_hp': 'wall_hp_multiplier',
        'tower_regen': 'wall_regen_multiplier',
        'def_pct': 'tower_defense_pct_points_add',
        'absolute_defense': 'tower_defense_absolute_multiplier',
        'uw_black_hole_duration_seconds': 'black_hole_duration_seconds_add',
        'uw_chrono_field_duration_seconds': 'chrono_field_duration_seconds_add',
    }
    out: dict[int, dict[str, float]] = {}
    for wave, counts in sorted(perk_counts_by_wave.items(), key=lambda item: int(item[0])):
        contributions: dict[str, float] = {}
        for perk_name, picks in sorted(counts.items()):
            perk_id = name_to_id.get(str(perk_name))
            if not perk_id:
                raise ValueError(f"Boss Waves perk timeline emitted unknown perk {perk_name!r}")
            perk_meta = entities.get(perk_id) or {}
            for effect in effects.get(perk_id, []):
                target = str(effect.get('target_stat_id') or '').strip()
                contribution_effect = target_to_contribution.get(target)
                if not contribution_effect:
                    continue
                operation = str(effect.get('operation') or '').strip()
                effect_index = str(effect.get('effect_index') or '').strip()
                value = scaled_perk_value(
                    perk_meta=perk_meta,
                    perk_effect_meta=effect,
                    perk_id=perk_id,
                    operation=operation,
                    raw_value=str(effect.get('effect_value') or '').strip(),
                    picks=int(picks),
                    effect_index=effect_index,
                    perk_lab_state=perk_lab_state,
                )
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Boss Waves perk contribution for {perk_id!r} effect {effect_index!r} "
                        f"resolved to unsupported non-numeric value {value!r}"
                    )
                contributions[f"perk_{perk_id}_effect_{effect_index}:{contribution_effect}"] = float(value)
        out[int(wave)] = contributions
    return out


def _boss_wave_primitive_semantics_ledger(
    *,
    primitives: dict[str, float],
    workshop_levels: dict[str, int],
    track_max_levels: dict[str, int],
    lab_levels: dict[str, object],
    row_input_wall_hp: float,
    row_input_wall_regen: float,
    timed_dr_sources: dict[str, object],
    death_wave_health_max_multiplier: float,
    death_wave_health_max_wave: int,
    boss_ttk_defaults: dict[str, object],
    wall_thorns_damage_increase_per_hit: float,
) -> dict[str, object]:
    fort = float(primitives['wall_fortification_multiplier'])
    return {
        'request_path': {
            'account_source': 'PipelineRunRequest.ids -> load_inputs -> build_runtime_state',
            'preset_name': 'Farming-or-requested-preset',
            'state_mode': 'start_of_run_static_primitives_plus_second_wind_mastery_regen_projection_plus_row_evolved_workshop_skip_state',
            'primitive_resolution_owner': 'qe.routing.resolve_checkpoint_surfaces (split by ownership)',
            'table1_owner': 'qe.run_plan',
            'table2_owner': 'simulators.evaluator_kernel',
            'product_render_owner': 'app.streamlit_inspector consumes operator_rows',
        },
        'replacement_primitive_family_coverage': dict(
            primitives.get('replacement_primitive_family_coverage') or {}
        ),
        'primitives': {
            'state::tower.enemy_attack_level_skip_pct': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.enemy_attack_level_skip_pct, state_mode=start_of_run, perks_enabled=False) + contributor decomposition into static additive + workshop track + multiplier',
                'canonical_truth_source': 'QE skip contributor row: additive_pre_cap contributors plus workshop__tower__enemy_attack_level_skip__pct times multiplicative enhancements',
                'semantic_meaning': 'QE-published enemy attack level skip surface is decomposed into static additive skip plus the Enemy Attack Level Skip workshop track and enhancement multiplier; Table 1 rederives the effective skip chance each checkpoint from current workshop levels',
                'exact_value': float(primitives['attack_skip_chance']),
                'primitive_vs_displayed': 'primitive_input',
                'fortification_transform': 'none',
                'state_phase': 'start_of_run',
                'row_evolution': 'Table 1 rederives skip chance from current Enemy Attack Level Skip workshop level each checkpoint',
                'owner_layer': 'QE publishes the contributor bundle; run_plan owns row-evolved checkpoint recurrence',
                'classification': 'transformed',
                'static_percent_points': float(primitives['attack_skip_static_percent_points']),
                'multiplier': float(primitives['attack_skip_multiplier']),
                'workshop_track': str(primitives['attack_skip_workshop_track']),
                'workshop_baseline_level': int(primitives['attack_skip_workshop_baseline_level']),
            },
            'state::tower.enemy_health_level_skip_pct': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.enemy_health_level_skip_pct, state_mode=start_of_run, perks_enabled=False) + contributor decomposition into static additive + workshop track + multiplier',
                'canonical_truth_source': 'QE skip contributor row: additive_pre_cap contributors plus workshop__tower__enemy_health_level_skip__pct times multiplicative enhancements',
                'semantic_meaning': 'QE-published enemy health level skip surface is decomposed into static additive skip plus the Enemy Health Level Skip workshop track and enhancement multiplier; Table 1 rederives the effective skip chance each checkpoint from current workshop levels',
                'exact_value': float(primitives['health_skip_chance']),
                'primitive_vs_displayed': 'primitive_input',
                'fortification_transform': 'none',
                'state_phase': 'start_of_run',
                'row_evolution': 'Table 1 rederives skip chance from current Enemy Health Level Skip workshop level each checkpoint',
                'owner_layer': 'QE publishes the contributor bundle; run_plan owns row-evolved checkpoint recurrence',
                'classification': 'transformed',
                'static_percent_points': float(primitives['health_skip_static_percent_points']),
                'multiplier': float(primitives['health_skip_multiplier']),
                'workshop_track': str(primitives['health_skip_workshop_track']),
                'workshop_baseline_level': int(primitives['health_skip_workshop_baseline_level']),
            },
            'state::tower.hp': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.hp)',
                'canonical_truth_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.hp)',
                'semantic_meaning': 'QE-published tower HP baseline used before Boss Waves row-owned Death Wave and wall-health transforms',
                'exact_value': float(primitives['tower_hp']),
                'primitive_vs_displayed': 'primitive_input_transform_for_wall_hp',
                'fortification_transform': 'none',
                'state_phase': 'start_of_run',
                'row_evolution': 'Table 1 applies Death Wave multiplier and downstream wall-health transforms per checkpoint',
                'owner_layer': 'QE publishes baseline; run_plan and evaluator derive row-facing wall HP',
                'classification': 'equivalent',
            },
            'state::wall.hp': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::wall.hp)',
                'canonical_truth_source': 'kb wall_hp = tower_hp * wall_health_ratio; qe.run_plan.derive_wall_hp_from_qe_primitives',
                'semantic_meaning': 'QE wall HP surface currently carries wall-health ratio contributors; Boss Waves derives pre-fort HP from tower HP and those contributor semantics',
                'exact_value': float(primitives['wall_hp_qe_surface']),
                'primitive_vs_displayed': 'partial_primitive_input_not_displayed_directly',
                'fortification_transform': 'not_used_as_final_wall_hp',
                'state_phase': 'start_of_run',
                'row_evolution': 'Table 1 starts from derived pre-fort wall HP and evolves by owned Wall Health workshop state',
                'owner_layer': 'QE publishes tower_hp and wall-health contributors; app assembles primitive bundle; run_plan derives and row-rederives; evaluator applies fortification once',
                'classification': 'transformed',
                'boss_waves_semantic_decision': 'transformed_primitive_not_final_display_value',
                'boss_waves_final_display_field': 'operator_rows.wall_pre_fort_hp for pre-fort HP and operator_rows.wall_hp for fortified Wall HP',
                'repo_wide_rename_or_split': 'defer_followup_if_needed; Boss Waves contract is explicit and does not treat state::wall.hp as final displayed Wall HP',
                'row_input_value': float(row_input_wall_hp),
                'tower_hp': float(primitives['tower_hp']),
                'wall_hp_percent_points': float(primitives['wall_hp_percent_points']),
                'wall_hp_ratio': float(primitives['wall_hp_ratio']),
                'wall_hp_multiplier': float(primitives['wall_hp_multiplier']),
            },
            'state::wall.regen': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::wall.regen, state_mode=start_of_run, scenario_projection_state.second_wind_mastery_regen=True)',
                'canonical_truth_source': 'formula_surface_policy state::wall.regen',
                'semantic_meaning': 'QE-published wall regen percent-points primitive; Boss Waves combines it with resolved tower regen for displayed HP/sec, with Second Wind mastery regen projection applied through the tower regen surface when active',
                'exact_value': float(primitives['wall_regen_percent_points']),
                'primitive_vs_displayed': 'partial_primitive_input_not_displayed_directly',
                'fortification_transform': 'not_fortification_scaled',
                'state_phase': 'start_of_run_percent_points_with_second_wind_mastery_regen_projection_on_tower_regen',
                'row_evolution': 'Table 1 can rederive if an owned wall-regen workshop primitive changes',
                'owner_layer': 'QE publishes tower_regen and wall_regen percent primitive; app assembles primitive bundle; run_plan row-rederives; evaluator applies scenario wall_regen transforms',
                'classification': 'transformed',
                'boss_waves_semantic_decision': 'transformed_percent_points_primitive_not_final_hp_per_second',
                'boss_waves_final_display_field': 'operator_rows.wall_regen',
                'repo_wide_rename_or_split': 'defer_followup_if_needed; Boss Waves contract is explicit and does not treat state::wall.regen as final displayed HP/sec',
                'row_input_value': float(row_input_wall_regen),
            },
            'state::tower.regen': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.regen, state_mode=start_of_run, scenario_projection_state.second_wind_mastery_regen=True)',
                'canonical_truth_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.regen) with QE ScenarioProjectionState(second_wind_mastery_regen=True)',
                'semantic_meaning': 'QE-published resolved tower regen HP/sec used as the base for wall regen; max-wave survivability assumes Second Wind mastery has triggered when the card is equipped and mastery is unlocked',
                'exact_value': float(primitives['tower_regen']),
                'primitive_vs_displayed': 'primitive_input_transform_for_wall_regen',
                'fortification_transform': 'none',
                'state_phase': 'start_of_run_with_second_wind_mastery_regen_projection',
                'row_evolution': 'static until owned row-evolved tower regen primitives exist',
                'owner_layer': 'QE publishes; Boss Waves primitive assembly combines with wall regen percent points',
                'classification': 'equivalent',
            },
            'state::wall.fortification_multiplier': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::wall.fortification_multiplier)',
                'canonical_truth_source': 'qe.materializer._scale_wall_fortification_lab_value',
                'semantic_meaning': 'multiplicative wall fortification factor applied once to pre-fort wall HP for Boss Waves displayed Wall HP',
                'exact_value': fort,
                'primitive_vs_displayed': 'primitive_input_transform_for_wall_hp',
                'fortification_transform': 'applied_once_in_evaluator_ttd',
                'state_phase': 'start_of_run',
                'row_evolution': 'static until an owned row-evolved fortification primitive exists',
                'owner_layer': 'QE publishes; evaluator consumes',
                'classification': 'equivalent',
            },
            'state::tower.defense_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::tower.defense_pct)',
                value=float(primitives['tower_defense_pct']),
                meaning='QE-published tower defense percent; evaluator adds active Defense Percent perk point contributions per row before timed BH/CF DR',
                owner='QE publishes baseline; run_plan carries Defense Percent perk contributions; evaluator consumes damage reduction',
            ),
            'state::tower.defense_absolute': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::tower.defense_absolute)',
                value=float(primitives['tower_defense_absolute']),
                meaning='QE-published Defense Absolute value; evaluator applies it after Defense Percent and before BH/CF/Flame Bot timed damage reduction.',
                owner='QE publishes baseline; run_plan carries Defense Absolute perk multiplier contributions; evaluator consumes post-defense-pct survivability reduction',
            ),
            'state::tower.thorns_damage_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::tower.thorns_damage_pct)',
                value=float(primitives['tower_thorns_damage_pct']),
                meaning='QE-published tower thorns percent; Boss Waves uses it only as the upstream base for Wall Thorns contact damage',
                owner='QE publishes; app derives wall contact thorns from tower thorns and Wall Thorns lab; evaluator consumes derived contact input',
            ),
            'state::wall.thorns_contact_damage_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::wall.thorns_damage_pct)',
                value=float(primitives['wall_thorns_contact_damage_pct']),
                meaning='Boss Waves-local wall contact thorns percent before boss thorns effectiveness; this is the contact-resolution source included in total v21 event-only TTK when the boss reaches contact',
                owner='QE publishes wall thorns from tower thorns and Wall Thorns lab; app assembles combat input; evaluator applies boss thorns effectiveness',
            ),
            'state::tower.death_defy_chance_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::tower.death_defy_chance_pct)',
                value=float(primitives.get('death_defy_chance_pct') or 0.0),
                meaning='QE-published Death Defy chance percent carried as Boss Waves survivability provenance. The current deterministic boss-contact model does not apply stochastic Death Defy survival.',
                owner='QE publishes Death Defy chance; app carries diagnostic provenance; stochastic lethal-hit policy remains outside this deterministic tranche',
            ),
            'state::combat.death_defy_effective_chance_pct': _primitive_ledger_entry(
                source='app.pipeline death_defy_chance_pct plus scenario bc_death_defy_down_pp',
                value=float(primitives.get('death_defy_effective_chance_pct') or 0.0),
                meaning='Death Defy chance after Death Defy Down battle-condition adjustment. Diagnostic only; not consumed by hit-by-hit wall TTD until a stochastic survival policy is owned.',
                owner='app assembles scenario-adjusted diagnostic from QE-owned chance and simulator-owned battle-condition surface',
            ),
            'state::tower.orb_count': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::tower.orb_count)',
                value=float(primitives.get('tower_orb_count') or 0.0),
                meaning='QE-published tower orb count carried for Boss Waves provenance. Boss Waves uses explicit total orb boss-damage runtime inputs rather than deriving boss hits from orb count in this tranche.',
                owner='QE publishes orb count; app carries diagnostic provenance; evaluator consumes explicit orb total damage input',
            ),
            'state::tower.orb_speed_rpm': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::tower.orb_speed_rpm)',
                value=float(primitives.get('tower_orb_speed_rpm') or 0.0),
                meaning='QE-published tower orb speed carried for Boss Waves provenance. Boss Waves does not infer boss orb hit cadence from this value without an owned formula.',
                owner='QE publishes orb speed; app carries diagnostic provenance; evaluator consumes explicit orb total damage input',
            ),
            'module::Sharp Fortitude.wall_thorns_damage_increase_per_hit': _primitive_ledger_entry(
                source='module unique runtime contract -> active armor module preset',
                value=float(wall_thorns_damage_increase_per_hit),
                meaning='Sharp Fortitude repeated-hit vulnerability for wall-thorns contact events, applied as +1% wall-thorns damage taken per subsequent hit on the same boss when Sharp Fortitude is the primary armor module',
                owner='KB owns module unique contract; app assembles active preset flag; evaluator applies event multiplier in v21 thorns contact events',
            ),
            'state::cards.plasma_cannon.effect_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.plasma_cannon.effect_pct)',
                value=float(primitives['plasma_cannon_effect_pct']),
                meaning='QE-published Plasma Cannon opening reduction percent used by v21 event-only TTK',
                owner='QE publishes; evaluator consumes combat input',
            ),
            'derived::edamage.uw.chain_lightning_dps': _primitive_ledger_entry(
                source='qe.publication.publish_query_surfaces(derived::edamage.uw.chain_lightning_dps)',
                value=float(primitives.get('chain_lightning_boss_damage_per_second') or 0.0),
                meaning=f"QE-published Chain Lightning DPS support surface resolved for Boss Waves damage state_mode={primitives.get('boss_damage_state_mode')} perks_enabled={bool(primitives.get('boss_damage_perks_enabled'))}. Boss Waves keeps this as a diagnostic and fallback lane while the default boss damage path starts from derived::edamage_ep.",
                owner='QE publishes derived CL DPS; app consumes it as diagnostic/fallback context for Boss Waves',
            ),
            'derived::edamage_boss': _primitive_ledger_entry(
                source='qe.publication.publish_query_surfaces(derived::edamage_boss)',
                value=float(primitives.get('qe_boss_applicable_cl_only_damage_per_second') or 0.0),
                meaning=f"QE-published TowerSim Boss Waves legacy base damage surface resolved for state_mode={primitives.get('boss_damage_state_mode')} perks_enabled={bool(primitives.get('boss_damage_perks_enabled'))}. It supplies confirmed constant Chain Lightning boss DPS for diagnostics and fallback; the default Boss Waves lane now starts from derived::edamage_ep and replaces EP exposure factors with boss-specific exposure factors.",
                owner='QE owns the CL diagnostic/fallback Boss Waves damage surface; app owns scenario/loadout runtime exposure factors and explicit bridge selection',
            ),
            'derived::edamage_ep': _primitive_ledger_entry(
                source='qe.publication.publish_query_surfaces(derived::edamage_ep)',
                value=float(primitives.get('edamage_ep') or primitives.get('edamage') or 0.0),
                meaning=f"QE-published exact Effective Paths eDamage objective surface resolved for Boss Waves damage state_mode={primitives.get('boss_damage_state_mode')} perks_enabled={bool(primitives.get('boss_damage_perks_enabled'))}. The Boss Waves default starts from this EP objective and replaces EP exposure terms with boss-specific runtime exposure terms; explicit runtime bridge inputs can still override the default when a caller owns boss-applicable DPS semantics.",
                owner='QE publishes eDamage; app owns Boss Waves exposure replacement and explicit runtime bridge selection',
            ),
            'derived::edamage.super_tower_factor': _primitive_ledger_entry(
                source='qe.publication.publish_query_surfaces(derived::edamage.super_tower_factor)',
                value=float(primitives.get('edamage_super_tower_factor') or 1.0),
                meaning=f"QE-published Super Tower factor included in derived::edamage_ep for Boss Waves damage state_mode={primitives.get('boss_damage_state_mode')} perks_enabled={bool(primitives.get('boss_damage_perks_enabled'))}. The app records this as provenance only; QE owns the card/mastery math.",
                owner='QE publishes Super Tower eDamage contribution; app carries it as Boss Waves diagnostic provenance',
            ),
            'state::module.project_funding.cash_digit_multiplier_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::module.project_funding.cash_digit_multiplier_pct)',
                value=float(primitives.get('project_funding_cash_digit_multiplier_pct') or 0.0),
                meaning='QE-published Project Funding cash-digit multiplier percent used by the QE eDamage objective when paired with the explicit current-cash support surface.',
                owner='QE publishes module unique value; app carries it as Boss Waves diagnostic provenance',
            ),
            'support_surface::module.project_funding.current_cash': _primitive_ledger_entry(
                source='input.manual_inputs.module.project_funding.current_cash',
                value=float(primitives.get('project_funding_current_cash') or 0.0),
                meaning='Input-owned current-cash assumption consumed by QE to calculate the Project Funding runtime eDamage factor.',
                owner='input owns manual current-cash assumption; QE publishes the support surface; app carries it as Boss Waves diagnostic provenance',
            ),
            'derived::edamage.project_funding_factor': _primitive_ledger_entry(
                source='qe.publication.publish_query_surfaces(derived::edamage.project_funding_factor)',
                value=float(primitives.get('edamage_project_funding_factor') or 1.0),
                meaning=f"QE-published Project Funding factor included in derived::edamage_ep for Boss Waves damage state_mode={primitives.get('boss_damage_state_mode')} perks_enabled={bool(primitives.get('boss_damage_perks_enabled'))}.",
                owner='QE publishes Project Funding eDamage contribution; app carries it as Boss Waves diagnostic provenance',
            ),
            'state::combat.boss_damage_per_second': _primitive_ledger_entry(
                source=str(primitives.get('boss_damage_source') or primitives.get('gc_boss_damage_source') or ''),
                value=float(primitives.get('boss_damage_per_second') or primitives.get('gc_boss_damage_per_second') or 0.0),
                meaning='Final continuous boss damage used by the shared boss-contact model for every loadout. Defaults to derived::edamage_ep with EP Spotlight, ACP, and slow/exposure factors replaced by Boss Waves runtime equivalents; explicit runtime bridge inputs can still override it when a caller owns boss-applicable DPS semantics.',
                owner='app selects explicit runtime scenario input or QE-owned eDamage with Boss Waves exposure replacements; evaluator integrates the final continuous boss damage value event-by-event',
            ),
            'state::combat.gc_boss_damage_per_second': _primitive_ledger_entry(
                source=str(primitives.get('gc_boss_damage_source') or primitives.get('boss_damage_source') or ''),
                value=float(primitives.get('gc_boss_damage_per_second') or primitives.get('boss_damage_per_second') or 0.0),
                meaning='Legacy alias for state::combat.boss_damage_per_second retained for existing Boss Waves consumers.',
                owner='compatibility alias for the shared boss-contact damage primitive',
            ),
            'state::combat.edamage_boss_runtime_factor': _primitive_ledger_entry(
                source='app.pipeline._boss_wave_apply_default_edamage_boss_runtime_factors',
                value=float(primitives.get('edamage_boss_runtime_factor') or 1.0),
                meaning='Boss Waves default replacement multiplier applied to QE derived::edamage_ep. It removes EP Spotlight, ACP, and slow/exposure factors, then applies Boss Waves Spotlight/Om Chip and travel-window ACP factors. EN mastery remains a separate timed TTK multiplier.',
                owner='app assembles scenario/loadout runtime exposure replacements; QE remains the base eDamage source and evaluator consumes the final continuous damage primitive',
            ),
            'state::combat.edamage_boss_pre_contact_timed_window_damage': _primitive_ledger_entry(
                source='simulators.timing.boss_pre_contact_damage_window',
                value=float(primitives.get('edamage_boss_pre_contact_timed_window_damage') or 0.0),
                meaning='Diagnostic total continuous boss damage available before contact from final boss DPS over boss travel/contact time, with Energy Net mastery applied only for its timed window. CF and Slow Aura contribute through contact time rather than as a DPS multiplier.',
                owner='timing engine owns the window calculation; app publishes diagnostic budget; evaluator remains the authoritative TTK integrator',
            ),
            'state::combat.boss_edamage_decomposed_bridge_factor': _primitive_ledger_entry(
                source='scenario_runtime_inputs.boss_edamage_target_share * boss_edamage_cadence_uptime_factor * boss_edamage_reliability_factor * boss_edamage_semantic_normalizer',
                value=float(primitives.get('boss_edamage_decomposed_bridge_factor') or 0.0),
                meaning='Explicit decomposed eDamage-to-boss bridge factor. The simulator requires all component factors before using this path so missing assumptions do not silently default to 1.0.',
                owner='manual_or_explicit_runtime_input',
            ),
            'state::cards.energy_net.duration_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.energy_net.duration_seconds)',
                value=float(primitives.get('energy_net_duration_seconds') or 0.0),
                meaning='QE-published Energy Net base duration used to time the Energy Net mastery boss-damage multiplier window.',
                owner='QE publishes card duration; app assembles duration+mastery combat primitive; evaluator consumes generic continuous-damage multiplier timing',
            ),
            'state::cards.energy_net.mastery_effect': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.energy_net.mastery_effect)',
                value=float(primitives.get('energy_net_mastery_multiplier') or 1.0),
                meaning='QE-published Energy Net mastery boss damage multiplier. The app applies it only for Energy Net duration plus the mastery 10s after-window.',
                owner='QE publishes card mastery effect; app assembles generic continuous-damage multiplier primitive; evaluator consumes it without card-specific branching',
            ),
            'state::cards.wave_accelerator.spawn_rate_acceleration': _primitive_ledger_entry(
                source='simulators.timing.resolve_timing_consumer_bundle(timing_wave_duration -> state::cards.wave_accelerator.spawn_rate_acceleration)',
                value=float(primitives.get('wave_accelerator_spawn_rate_acceleration') or 1.0),
                meaning='Timing-family Wave Accelerator Mastery spawn-rate acceleration. Boss Waves carries it into non-boss pressure diagnostics only; it does not change default boss-contact max-wave selection without an owned terminal-pressure transform.',
                owner='simulators.timing resolves timing-owned card mastery effect; simulators.scenario owns source-backed pressure-driver probes; app carries diagnostic provenance',
            ),
            'state::cards.enemy_balance.mastery_effect': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.enemy_balance.mastery_effect)',
                value=float(primitives.get('enemy_balance_mastery_double_elite_chance_pct') or 0.0),
                meaning='QE-published Enemy Balance Mastery double-elite chance percent. Boss Waves carries it into non-boss pressure diagnostics only; it does not change default boss-contact max-wave selection without an owned terminal-pressure transform.',
                owner='QE publishes card mastery effect; simulators.scenario owns source-backed pressure-driver probes; app carries diagnostic provenance',
            ),
            'state::capability.energy_shield.enabled': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::capability.energy_shield.enabled)',
                value=1.0 if bool(primitives.get('energy_shield_enabled')) else 0.0,
                meaning='QE-published Energy Shield equipped capability. Boss Waves treats the equipped card as one base shield charge for boss-contact hit absorption.',
                owner='QE publishes card capability; app assembles total/effective shield charges; evaluator consumes generic absorbed-hit charges',
            ),
            'state::cards.energy_shield.recharge_cooldown_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.energy_shield.recharge_cooldown_seconds)',
                value=float(primitives.get('energy_shield_recharge_cooldown_seconds') or 0.0),
                meaning='QE-published Energy Shield recharge cooldown carried as provenance. This boss-contact tranche assumes available charges for the modeled boss contact and does not simulate cross-boss recharge sequencing.',
                owner='QE publishes card cooldown; app carries provenance; cross-boss recharge sequencing remains outside this boss-contact model',
            ),
            'state::cards.energy_shield.extra_charge_count': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.energy_shield.extra_charge_count)',
                value=float(primitives.get('energy_shield_extra_charge_count') or 0.0),
                meaning='QE-published Energy Shield Extra Hit lab count bonus. Boss Waves adds this to the equipped-card base charge before applying Energy Shields Down.',
                owner='QE publishes lab-derived extra charges; app assembles total/effective shield charges; evaluator consumes generic absorbed-hit charges',
            ),
            'state::combat.energy_shield_effective_charge_count': _primitive_ledger_entry(
                source='app.pipeline Energy Shield total charges after scenario bc_energy_shields_down_fraction',
                value=float(primitives.get('energy_shield_effective_charge_count') or 0.0),
                meaning='Final whole-number Energy Shield charges available to absorb modeled boss-contact hits after applying Energy Shields Down as a charge-count reduction.',
                owner='app assembles scenario-adjusted combat primitive from QE-owned card/lab surfaces and simulator-owned scenario battle-condition surface; evaluator consumes absorbed-hit charges',
            ),
            'state::uw.chrono_field.slow_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.chrono_field.slow_pct)',
                value=float(primitives.get('chrono_field_slow_pct') or 0.0),
                meaning='QE-published Chrono Field enemy slow percent. Boss Waves applies average uptime-weighted slow to derived boss travel time; Ultimate Weapon dissonance masks it to zero.',
                owner='QE publishes UW slow; app assembles contact-time primitive; evaluator consumes final boss time-to-contact',
            ),
            'state::cards.slow_aura.enemy_speed_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.slow_aura.enemy_speed_pct)',
                value=float(primitives.get('slow_aura_enemy_speed_pct') or 0.0),
                meaning='QE-published Slow Aura enemy speed reduction. Boss Waves applies it to derived boss travel time when contact time is not explicitly overridden.',
                owner='QE publishes card slow; app assembles contact-time primitive; evaluator consumes final boss time-to-contact',
            ),
            'state::cards.slow_aura.mastery_effect': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::cards.slow_aura.mastery_effect)',
                value=float(primitives.get('slow_aura_mastery_attack_interval_multiplier') or 1.0),
                meaning='QE-published Slow Aura mastery effect. Boss Waves applies it to the boss hit interval after contact, not to pre-contact movement speed.',
                owner='QE publishes card mastery effect; app assembles boss hit interval primitive; evaluator consumes the final interval',
            ),
            'state::module.orbital_augment.electron_count': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::module.orbital_augment.electron_count)',
                value=float(primitives.get('orbital_augment_electron_count') or 0.0),
                meaning='QE-published equipped Orbital Augment electron count; Boss Waves uses it to default total electron boss damage when runtime electron total is omitted',
                owner='QE publishes module unique count; app assembles default TTK input; evaluator consumes combat input',
            ),
            'state::module.primordial_collapse.bh_damage_reduction_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::module.primordial_collapse.bh_damage_reduction_pct)',
                value=float(primitives.get('primordial_collapse_bh_damage_reduction_pct') or 0.0),
                meaning='QE-published Primordial Collapse damage reduction percent while the boss is inside Black Hole; Boss Waves uses this for the PBH timed DR source when runtime PBH inputs are not explicitly provided',
                owner='QE publishes module unique DR; app assembles timed DR primitive; evaluator consumes multiplicative DR lane input',
            ),
            'state::uw.black_hole.duration_seconds': _primitive_ledger_entry(
                source='simulators.timing.resolve_timing_consumer_bundle(state::uw.black_hole.duration_seconds)',
                value=float(primitives.get('black_hole_duration_seconds') or 0.0),
                meaning='Effective current-account Black Hole duration used to calculate PBH uptime for Boss Waves timed DR; BH does not damage the boss in this tranche',
                owner='simulators.timing publishes effective UW timing; app assembles timed DR primitive; run_plan applies BH duration perk per row; evaluator consumes multiplicative DR lane input',
            ),
            'state::uw.black_hole.cooldown_seconds': _primitive_ledger_entry(
                source='simulators.timing.resolve_timing_consumer_bundle(state::uw.black_hole.cooldown_seconds)',
                value=float(primitives.get('black_hole_cooldown_seconds') or 0.0),
                meaning='Effective current-account Black Hole cooldown used to calculate PBH uptime for Boss Waves timed DR',
                owner='simulators.timing publishes effective UW timing; app assembles timed DR primitive; evaluator consumes multiplicative DR lane input',
            ),
            'state::uw.black_hole.base_duration_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.black_hole.base_duration_seconds)',
                value=float(primitives.get('black_hole_base_duration_seconds') or 0.0),
                meaning='QE-published raw Black Hole duration carried as Boss Waves provenance; effective combat timing remains assembled through the timing path.',
                owner='QE publishes raw UW timing; app carries diagnostic provenance; simulators.timing owns effective timing',
            ),
            'state::uw.black_hole.base_cooldown_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.black_hole.base_cooldown_seconds)',
                value=float(primitives.get('black_hole_base_cooldown_seconds') or 0.0),
                meaning='QE-published raw Black Hole cooldown carried as Boss Waves provenance; effective combat timing remains assembled through the timing path.',
                owner='QE publishes raw UW timing; app carries diagnostic provenance; simulators.timing owns effective timing',
            ),
            'state::uw.golden_tower.base_duration_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.golden_tower.base_duration_seconds)',
                value=float(primitives.get('golden_tower_base_duration_seconds') or 0.0),
                meaning='QE-published raw Golden Tower duration carried as Boss Waves provenance. Boss Waves does not apply GT timing as a combat primitive in this tranche.',
                owner='QE publishes raw UW timing; app carries diagnostic provenance',
            ),
            'state::uw.golden_tower.base_cooldown_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.golden_tower.base_cooldown_seconds)',
                value=float(primitives.get('golden_tower_base_cooldown_seconds') or 0.0),
                meaning='QE-published raw Golden Tower cooldown carried as Boss Waves provenance. Boss Waves does not apply GT timing as a combat primitive in this tranche.',
                owner='QE publishes raw UW timing; app carries diagnostic provenance',
            ),
            'state::uw.chrono_field.duration_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.chrono_field.duration_seconds)',
                value=float(primitives.get('chrono_field_duration_seconds') or 0.0),
                meaning='Effective current-account Chrono Field duration primitive; evaluator adds active Chrono Field Duration perk seconds per row before computing average CF DR',
                owner='QE publishes effective UW timing primitive; app assembles named primitive; run_plan carries CF duration perk contribution; evaluator consumes multiplicative DR lane input',
            ),
            'state::uw.chrono_field.cooldown_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.chrono_field.cooldown_seconds)',
                value=float(primitives.get('chrono_field_cooldown_seconds') or 0.0),
                meaning='Chrono Field cooldown primitive used to calculate average CF DR uptime',
                owner='QE publishes effective UW timing primitive; evaluator consumes multiplicative DR lane input',
            ),
            'state::uw.chrono_field.damage_reduction_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::uw.chrono_field.damage_reduction_pct)',
                value=float(primitives.get('chrono_field_damage_reduction_pct') or 0.0),
                meaning='Effective current-account Chrono Field damage reduction percent, used as a separate DR source after defense',
                owner='QE publishes effective UW timing primitive; app assembles named primitive; evaluator consumes multiplicative DR lane input',
            ),
            'state::bot.flame.owned': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::bot.flame.owned)',
                value=1.0 if primitives.get('flame_bot_owned') else 0.0,
                meaning='_IDS-owned Flame Bot unlock flag. When false, QE gates Flame Bot track primitives to zero before Boss Waves consumes them.',
                owner='input parses _IDS bot unlock flag; QE publishes owned state and gated bot tracks; app consumes the resolved state',
            ),
            'state::bot.flame.damage_reduction_pct': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::bot.flame.damage_reduction_pct)',
                value=float(primitives.get('flame_bot_damage_reduction_pct') or 0.0),
                meaning='QE-published Flame Bot DR track value after the _IDS bot owned flag is applied. Boss Waves combines this with an explicit manual hit-chance override, explicit duration/cooldown inputs, or the static boss-path overlap model for expected DR.',
                owner='QE publishes bot owned flag and gated DR track; app assembles Boss Waves encounter semantics without changing QE truth',
            ),
            'state::bot.flame.cooldown_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::bot.flame.cooldown_seconds)',
                value=float(primitives.get('flame_bot_cooldown_seconds') or 0.0),
                meaning='QE-published Flame Bot cooldown. Boss Waves uses it for explicit duration/cooldown timed DR and for the static boss-path overlap hit-chance model.',
                owner='QE publishes bot track; app consumes cooldown in the simulator-owned encounter model',
            ),
            'state::bot.flame.effective_range_m': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::bot.flame.effective_range_m)',
                value=float(primitives.get('flame_bot_effective_range_m') or 0.0),
                meaning='QE-published effective Flame Bot active range: raw Flame Bot range plus shared bot range bonus, amplified by tower range per the KB bot-runtime contract.',
                owner='QE publishes effective bot range; app consumes it only for the static Boss Waves Flame Bot hit-chance estimate',
            ),
        },
        'workshop_levels': {
            'Wall Health': _workshop_ledger_entry(workshop_levels, track_max_levels, 'Wall Health', 'row-evolved pre-fort wall HP contributor basis'),
            'Health Regen': _workshop_ledger_entry(workshop_levels, track_max_levels, 'Health Regen', 'row-evolved wall regen contributor basis when owned semantics are present'),
            'Wall Fortification': {
                'boss_waves_source': "input.runtime_state.AccountState.labs['Wall Fortification']",
                'canonical_truth_source': 'input.runtime_state.build_runtime_state lab snapshot',
                'semantic_meaning': 'lab level provenance for state::wall.fortification_multiplier',
                'exact_value': int(lab_levels.get('Wall Fortification') or 0),
                'primitive_vs_displayed': 'primitive_provenance_input',
                'fortification_transform': 'lab level is converted by QE into state::wall.fortification_multiplier',
                'state_phase': 'start_of_run',
                'owner_layer': 'input publishes lab level; QE materializer scales to fortification multiplier',
                'classification': 'equivalent' if lab_levels.get('Wall Fortification') is not None else 'unresolved',
            },
        },
        'fortification_double_application_check': {
            'state_wall_hp_includes_fortification': True,
            'row_input_wall_hp': float(row_input_wall_hp),
            'fortification_multiplier': fort,
            'reconstructed_wall_hp': float(row_input_wall_hp) * fort,
            'qe_state_wall_hp_surface': float(primitives['wall_hp_qe_surface']),
            'policy': 'derive pre-fort wall HP from tower_hp and wall-health ratio contributors; evaluator multiplies by fortification once for displayed Wall HP',
        },
        'wall_hp_formula_check': {
            'tower_hp': float(primitives['tower_hp']),
            'death_wave_health_max_multiplier': float(death_wave_health_max_multiplier),
            'death_wave_health_max_wave': int(death_wave_health_max_wave),
            'wall_hp_percent_points': float(primitives['wall_hp_percent_points']),
            'wall_hp_ratio': float(primitives['wall_hp_ratio']),
            'wall_hp_multiplier': float(primitives['wall_hp_multiplier']),
            'displayed_wall_hp_pre_fort': float(row_input_wall_hp),
            'reconstructed_displayed_wall_hp_pre_fort': float(primitives['tower_hp']) * float(primitives['wall_hp_ratio']) * float(primitives['wall_hp_multiplier']),
            'policy': 'displayed pre-fort Wall HP = row-evolved tower HP including Table 1 Death Wave health multiplier * wall health ratio * non-fort wall health multipliers',
        },
        'wall_regen_formula_check': {
            'tower_regen': float(primitives['tower_regen']),
            'wall_regen_percent_points': float(primitives['wall_regen_percent_points']),
            'wall_regen_multiplier': float(primitives['wall_regen_percent_points']) / 100.0,
            'displayed_wall_regen': float(row_input_wall_regen),
            'reconstructed_displayed_wall_regen': float(primitives['tower_regen']) * (float(primitives['wall_regen_percent_points']) / 100.0),
            'policy': 'displayed Wall Regen = resolved tower regen HP/sec, including Second Wind mastery regen projection when active, * QE wall regen percent-points primitive / 100',
        },
        'boss_waves_wall_surface_semantic_contract': {
            'state::wall.hp': {
                'decision': 'transformed_primitive_not_final_display_value',
                'product_value': 'operator_rows.wall_pre_fort_hp is pre-fort row-derived HP; operator_rows.wall_hp is fortified Wall HP',
                'fortification_policy': 'state::wall.fortification_multiplier is applied exactly once by evaluator TTD to produce displayed Wall HP',
            },
            'state::wall.regen': {
                'decision': 'transformed_percent_points_primitive_not_final_hp_per_second',
                'product_value': 'operator_rows.wall_regen is projected tower_regen * state::wall.regen / 100 after owned row/scenario transforms',
                'fortification_policy': 'not fortification-scaled',
            },
        },
        'timed_dr_semantic_contract': {
            'owner_layer': 'app assembles explicit runtime primitives; run_plan carries staged timed DR primitives and CF/BH duration perk contributions; evaluator combines DR multiplicatively per row',
            'lane_policy': 'duration-style timed DR uses uptime-weighted average lanes; Flame Bot hit-chance sources are binary per boss, so min is miss, avg assumes the hit only when the modeled tag chance is near-certain, max is the full-hit lane, and hit probability is surfaced separately',
            'sources': dict(timed_dr_sources),
            'perk_duration_contributions': {
                'PERK_BLACK_HOLE_DURATION_12_0S': 'black_hole_duration_seconds_add',
                'PERK_CHRONO_FIELD_DURATION_5S': 'chrono_field_duration_seconds_add',
            },
            'concern': 'KB de-scopes exact same-tick Flame Bot overlap and PBH/BH encounter micro-precedence; current path models expected overlap, not frame-accurate overlap. Flame Bot uses an explicit manual boss-hit chance override when supplied, otherwise a static uniform-center boss-path overlap estimate from effective Flame Bot range, cooldown, wall radius, and boss contact time at primitive assembly, with operator rows recomputing the static estimate over row boss lifetime when TTK is known. Explicit runtime duration/cooldown remains supported. No owned Defense Field primitive was found in the active repo.',
        },
        'boss_ttk_input_contract': dict(boss_ttk_defaults),
    }


def _primitive_ledger_entry(*, source: str, value: float, meaning: str, owner: str) -> dict[str, object]:
    return {
        'boss_waves_source': source,
        'canonical_truth_source': source,
        'semantic_meaning': meaning,
        'exact_value': float(value),
        'primitive_vs_displayed': 'primitive_input',
        'fortification_transform': 'none',
        'state_phase': 'start_of_run',
        'row_evolution': 'static unless scenario/runtime transform applies',
        'owner_layer': owner,
        'classification': 'equivalent',
    }


def _boss_wave_default_ttk_inputs(
    runtime_inputs: ScenarioRuntimeInputs,
    *,
    primitives: dict[str, float],
    electron_boss_remaining_hp_pct: float,
) -> dict[str, object]:
    explicit_orb_total = getattr(runtime_inputs, 'orb_boss_total_damage_pct')
    explicit_electron_total = getattr(runtime_inputs, 'electron_total_damage_pct')
    oa_electron_count = max(0.0, float(primitives.get('orbital_augment_electron_count') or 0.0))
    default_electron_total_pct = max(0.0, min(100.0, oa_electron_count * float(electron_boss_remaining_hp_pct) * 100.0))
    return {
        'orb_boss_total_damage_pct': float(explicit_orb_total) if explicit_orb_total is not None else 6.0,
        'orb_boss_total_damage_source': 'runtime_input' if explicit_orb_total is not None else 'default_orb_boss_total_damage_pct_6',
        'electron_total_damage_pct': float(explicit_electron_total) if explicit_electron_total is not None else default_electron_total_pct,
        'electron_total_damage_source': 'runtime_input' if explicit_electron_total is not None else 'orbital_augment_electron_count_times_boss_electron_pct',
        'orbital_augment_electron_count': oa_electron_count,
        'orbital_augment_equipped': oa_electron_count > 0.0,
        'electron_boss_remaining_hp_pct': float(electron_boss_remaining_hp_pct),
    }


def _workshop_ledger_entry(
    workshop_levels: dict[str, int],
    track_max_levels: dict[str, int],
    track_name: str,
    meaning: str,
) -> dict[str, object]:
    return {
        'boss_waves_source': f'input.runtime_state.AccountState.workshop[{track_name!r}].preset_levels',
        'canonical_truth_source': 'input.runtime_state.build_runtime_state account snapshot',
        'semantic_meaning': meaning,
        'exact_value': int(workshop_levels.get(track_name, 0)),
        'max_level': int(track_max_levels.get(track_name, 0)),
        'primitive_vs_displayed': 'row_evolution_input',
        'fortification_transform': 'provenance_only' if track_name == 'Wall Fortification' else 'none',
        'state_phase': 'start_of_run_seed_then_row_evolved_by_freeups',
        'owner_layer': 'input publishes account state; app assembles; run_plan evolves',
        'classification': 'equivalent' if track_name in workshop_levels else 'unresolved',
    }


def _required_statbook_float(statbook, surface_id: str) -> float:
    row = _required_statbook_row(statbook, surface_id)
    if str(getattr(row, 'status', '') or '').strip() != 'resolved':
        raise ValueError(f"Boss Waves replacement input requires resolved QE surface {surface_id!r}")
    value = getattr(row, 'final_value', None)
    if value is None:
        raise ValueError(f"Boss Waves replacement input requires non-null QE surface {surface_id!r}")
    return float(value)


def _optional_statbook_float(statbook, surface_id: str, *, default: float = 0.0) -> float:
    row = (getattr(statbook, 'rows', {}) or {}).get(surface_id)
    if row is None or str(getattr(row, 'status', '') or '').strip() != 'resolved':
        return float(default)
    value = getattr(row, 'final_value', None)
    if value is None:
        return float(default)
    return float(value)


def _optional_statbook_bool(statbook, surface_id: str, *, default: bool = False) -> bool:
    row = (getattr(statbook, 'rows', {}) or {}).get(surface_id)
    if row is None or str(getattr(row, 'status', '') or '').strip() != 'resolved':
        return bool(default)
    value = getattr(row, 'final_value', None)
    if value is None:
        return bool(default)
    if isinstance(value, str):
        return value.strip().lower() == 'true'
    return bool(value)


def _required_statbook_row(statbook, surface_id: str):
    row = (getattr(statbook, 'rows', {}) or {}).get(surface_id)
    if row is None:
        raise ValueError(f"Boss Waves replacement input requires QE surface {surface_id!r}")
    return row


def _required_statbook_fraction(statbook, surface_id: str) -> float:
    return max(0.0, min(1.0, _required_statbook_float(statbook, surface_id) / 100.0))


def _replacement_operator_row_from_overlay(
    *,
    overlay,
    active_source: str,
    combat,
    primitives: Mapping[str, object],
    incoming_damage_multiplier: float,
) -> dict[str, object]:
    summary = overlay.summary_combat
    boss_damage = overlay.boss_damage_breakdown
    boss_time_to_contact = combat.boss_time_to_contact_seconds
    boss_ttk = summary.ttk_seconds
    boss_killed_before_contact = (
        boss_time_to_contact is not None
        and boss_ttk is not None
        and float(boss_ttk) <= float(boss_time_to_contact)
    )
    heat = dict(getattr(overlay, 'heat', {}) or {})
    tower_damage_decay_multiplier = float(heat.get('tower_damage_decay_multiplier') or 1.0)
    return {
        'display_wave': overlay.display_wave,
        'attack_wave': overlay.effective_attack_wave,
        'health_wave': overlay.effective_health_wave,
        'boss_attack': overlay.enemy_attack,
        'boss_health': overlay.enemy_health,
        'wall_pre_fort_hp': overlay.final_wall_hp,
        'wall_regen': overlay.final_wall_regen,
        'tower_damage_per_second': float(combat.continuous_boss_damage_per_second) * tower_damage_decay_multiplier,
        'effective_damage_reduction_pct': overlay.damage_reduction_pct,
        'boss_ttk_seconds': summary.ttk_seconds,
        'boss_killed_before_contact': boss_killed_before_contact,
        'boss_plasma_cannon_damage_to_boss_pct': boss_damage.plasma_cannon_damage_pct,
        'boss_orb_damage_to_boss_pct': boss_damage.orb_damage_pct,
        'boss_electron_damage_to_boss_pct': boss_damage.electron_damage_pct,
        'boss_continuous_damage_to_boss_pct': boss_damage.continuous_damage_pct,
        'boss_wall_thorns_damage_to_boss_pct': boss_damage.thorns_damage_pct,
        'boss_expected_wall_thorns_damage_from_hits_pct': boss_damage.thorns_expected_damage_pct_from_hits,
        'boss_wall_thorns_contact_kill_seconds': summary.contact_thorns_kill_seconds,
        'boss_time_to_contact_seconds': combat.boss_time_to_contact_seconds,
        'boss_hit_interval_seconds': combat.boss_hit_interval_seconds,
        'energy_shield_enabled': bool(primitives.get('energy_shield_enabled')),
        'energy_shield_effective_charge_count': float(primitives.get('energy_shield_effective_charge_count') or 0.0),
        'energy_shields_down_fraction': float(primitives.get('energy_shields_down_fraction') or 0.0),
        'incoming_damage_multiplier': incoming_damage_multiplier,
        'overheat_effects': heat,
        'boss_hits_taken': summary.boss_hits_taken,
        'boss_hits_to_player': summary.boss_hits_taken,
        'boss_wall_thorns_hits': boss_damage.thorns_hits,
        'boss_total_damage_taken': summary.total_damage_taken,
        'boss_survival_margin_hp': summary.survival_margin_hp,
        'wall_hp': summary.wall_hp,
        'wall_regen_gained_hp': summary.wall_regen_gained_hp,
        'contact_envelope_total_damage_taken': summary.contact_envelope_total_damage_taken,
        'contact_envelope_survival_margin_hp': summary.contact_envelope_survival_margin_hp,
        'contact_envelope_wall_regen_gained_hp': summary.contact_envelope_wall_regen_gained_hp,
        'contact_envelope_survives_boss': summary.contact_envelope_survives,
        'contact_envelope_fail_reason': summary.contact_envelope_fail_reason,
        'survives_boss': summary.survives,
        'fail_reason': summary.fail_reason,
        'replacement_source': active_source,
        'summary_lane_id': overlay.summary_lane_id,
        'operator_handle_id': overlay.operator_handle.handle_id,
        'lane_handle_ids': dict(overlay.operator_handle.lane_handle_ids),
    }


def _replacement_summary_from_operator_rows(
    operator_rows: list[dict[str, object]],
    *,
    perk_policy_preset: str | None = None,
    terminal_pressure_limits: Mapping[str, int] | None = None,
) -> dict[str, object]:
    hit_by_hit = _summary_wave_fields(operator_rows, survive_field='survives_boss')
    contact_envelope = _summary_wave_fields(operator_rows, survive_field='contact_envelope_survives_boss')
    gc_pre_contact = _summary_wave_fields(operator_rows, survive_field='boss_killed_before_contact')
    loadout_type = _boss_wave_loadout_type(perk_policy_preset)
    selected = hit_by_hit
    selected_model = 'unified_hit_by_hit_boss_survival'
    terminal = int(operator_rows[-1].get('display_wave') or 0) if operator_rows else 0
    summary = {
        'max_wave': hit_by_hit['last_contiguous_surviving_wave'],
        'max_surviving_wave': hit_by_hit['last_contiguous_surviving_wave'],
        'selected_max_wave': selected['last_contiguous_surviving_wave'],
        'selected_first_failed_wave': selected['first_failed_wave'],
        'selected_max_independent_wave': selected['max_independent_surviving_wave'],
        'selected_model': selected_model,
        'selected_loadout_type': loadout_type,
        'selected_policy_preset': str(perk_policy_preset or ''),
        'last_contiguous_surviving_wave': hit_by_hit['last_contiguous_surviving_wave'],
        'max_independent_surviving_wave': hit_by_hit['max_independent_surviving_wave'],
        'first_failed_wave': hit_by_hit['first_failed_wave'],
        'hit_by_hit_max_wave': hit_by_hit['last_contiguous_surviving_wave'],
        'hit_by_hit_first_failed_wave': hit_by_hit['first_failed_wave'],
        'contact_envelope_max_wave': contact_envelope['last_contiguous_surviving_wave'],
        'contact_envelope_first_failed_wave': contact_envelope['first_failed_wave'],
        'contact_envelope_max_independent_surviving_wave': contact_envelope['max_independent_surviving_wave'],
        'contact_envelope_model': 'wall_pool_plus_contact_window_regen_vs_first_boss_hit',
        'pre_contact_boss_kill_max_wave': gc_pre_contact['last_contiguous_surviving_wave'],
        'pre_contact_boss_kill_first_failed_wave': gc_pre_contact['first_failed_wave'],
        'pre_contact_boss_kill_max_independent_wave': gc_pre_contact['max_independent_surviving_wave'],
        'pre_contact_boss_kill_model': 'boss_ttk_seconds_less_than_or_equal_to_boss_time_to_contact_seconds',
        'gc_pre_contact_max_wave': gc_pre_contact['last_contiguous_surviving_wave'],
        'gc_pre_contact_first_failed_wave': gc_pre_contact['first_failed_wave'],
        'gc_pre_contact_max_independent_wave': gc_pre_contact['max_independent_surviving_wave'],
        'gc_pre_contact_model': 'boss_ttk_seconds_less_than_or_equal_to_boss_time_to_contact_seconds',
        'row_count': len(operator_rows),
        'terminal_display_wave': terminal,
        'survives_through_end': bool(operator_rows) and hit_by_hit['first_failed_wave'] == 0,
        'contact_envelope_survives_through_end': bool(operator_rows) and contact_envelope['first_failed_wave'] == 0,
        'pre_contact_boss_kill_survives_through_end': bool(operator_rows) and gc_pre_contact['first_failed_wave'] == 0,
        'gc_pre_contact_survives_through_end': bool(operator_rows) and gc_pre_contact['first_failed_wave'] == 0,
        'result_consistent_with_rows': True,
    }
    _apply_terminal_pressure_limits(summary, terminal_pressure_limits or {})
    return summary


def _apply_terminal_pressure_limits(summary: dict[str, object], terminal_pressure_limits: Mapping[str, int]) -> None:
    normalized: dict[str, int] = {
        str(cause): int(max_wave)
        for cause, max_wave in terminal_pressure_limits.items()
        if int(max_wave or 0) > 0
    }
    summary['terminal_pressure_limits'] = dict(sorted(normalized.items()))
    summary['terminal_pressure_limiter'] = None
    summary['terminal_pressure_limited'] = False
    if not normalized:
        return
    limiting_cause, limiting_wave = min(normalized.items(), key=lambda item: item[1])
    selected_wave = int(summary.get('selected_max_wave') or 0)
    if selected_wave <= 0 or limiting_wave >= selected_wave:
        return
    previous_model = str(summary.get('selected_model') or '')
    summary.update(
        {
            'selected_max_wave': int(limiting_wave),
            'selected_first_failed_wave': int(limiting_wave) + 1,
            'selected_max_independent_wave': min(
                int(summary.get('selected_max_independent_wave') or limiting_wave),
                int(limiting_wave),
            ),
            'selected_model': f'{previous_model}_limited_by_{limiting_cause}',
            'terminal_pressure_limiter': limiting_cause,
            'terminal_pressure_limited': True,
        }
    )


def _apply_unsupported_terminal_pressure_reference_limit(
    summary: dict[str, object],
    *,
    account_state,
    tier_number: int,
    dissonance_run_category: str,
    unsupported_terminal_pressures: Iterable[str],
    runtime_inputs: ScenarioRuntimeInputs,
) -> None:
    pressures = sorted({str(item) for item in (unsupported_terminal_pressures or ()) if str(item)})
    limit_payload: dict[str, object] = {
        'applicable': False,
        'limited': False,
        'reference_wave': None,
        'reference_kind': None,
        'reference_source': None,
        'uncapped_selected_max_wave': int(summary.get('selected_max_wave') or 0),
        'unsupported_terminal_pressures': pressures,
    }
    summary['unsupported_pressure_reference_limit'] = limit_payload
    summary['unsupported_pressure_reference_limited'] = False
    summary['unsupported_pressure_reference_aligned'] = False
    summary['unsupported_pressure_reference_alignment_direction'] = None
    summary['pressure_factor_reference_hint'] = {
        'enabled': False,
        'mode': 'not_applicable',
        'boss_wave_pressure_factor': None,
        'direction': None,
    }
    if (
        not pressures
        or _boss_wave_explicit_terminal_pressure_closed(runtime_inputs, pressures)
        or _boss_wave_explicit_pressure_factor(runtime_inputs) is not None
    ):
        return
    alignment = _boss_wave_milestone_alignment(
        account_state=account_state,
        tier_number=int(tier_number),
        dissonance_run_category=dissonance_run_category,
        summary=summary,
    )
    reference_wave = _extract_optional_wave_number(alignment.get('active_reference_wave'))
    limit_payload.update(
        {
            'applicable': True,
            'reference_wave': reference_wave,
            'reference_raw_wave': alignment.get('active_reference_raw_wave'),
            'reference_gap_reason': alignment.get('active_reference_gap_reason'),
            'reference_kind': alignment.get('active_reference_kind'),
            'reference_source': alignment.get('active_reference_source'),
        }
    )
    calculated_wave_for_hint = int(limit_payload.get('uncapped_selected_max_wave') or 0)
    calculated_delta_vs_reference_wave = None
    calculated_to_reference_ratio = None
    if reference_wave is not None and reference_wave > 0 and calculated_wave_for_hint > 0:
        calculated_delta_vs_reference_wave = calculated_wave_for_hint - int(reference_wave)
        calculated_to_reference_ratio = calculated_wave_for_hint / float(reference_wave)
    pressure_factor_hint = _boss_wave_pressure_factor_reference_hint(
        calculated_wave=calculated_wave_for_hint,
        reference_wave=reference_wave,
        reference_kind=alignment.get('active_reference_kind'),
        reference_source=alignment.get('active_reference_source'),
        calculated_delta_vs_reference_wave=calculated_delta_vs_reference_wave,
        calculated_to_reference_ratio=calculated_to_reference_ratio,
    )
    summary['pressure_factor_reference_hint'] = pressure_factor_hint
    limit_payload['pressure_factor_reference_hint'] = dict(pressure_factor_hint)
    if reference_wave is None or reference_wave <= 0:
        previous_model = str(summary.get('selected_model') or '')
        limit_payload['missing_reference'] = True
        limit_payload['blocked'] = True
        summary.update(
            {
                'selected_max_wave': 0,
                'selected_first_failed_wave': 0,
                'selected_max_independent_wave': 0,
                'selected_model': (
                    f'{previous_model}_blocked_by_unsupported_pressure_missing_empirical_reference'
                    if previous_model
                    else 'blocked_by_unsupported_pressure_missing_empirical_reference'
                ),
                'terminal_pressure_limiter': 'unsupported_pressure_missing_empirical_reference',
                'terminal_pressure_limited': True,
                'unsupported_pressure_missing_reference_blocked': True,
                'status': 'incomplete',
                'failure_kind': 'unsupported_terminal_pressure_without_reference_limit',
                'failure_message': (
                    'Unsupported non-boss terminal pressure is present and no positive empirical reference wave '
                    'is available.'
                ),
            }
        )
        return
    selected_wave = int(summary.get('selected_max_wave') or 0)
    if selected_wave <= 0:
        return
    previous_model = str(summary.get('selected_model') or '')
    if selected_wave == reference_wave:
        limit_payload.update(
            {
                'aligned': True,
                'alignment_direction': 'already_at_empirical_reference',
            }
        )
        summary.update(
            {
                'unsupported_pressure_reference_aligned': True,
                'unsupported_pressure_reference_alignment_direction': 'already_at_empirical_reference',
            }
        )
        return
    alignment_direction = (
        'capped_to_empirical_reference'
        if selected_wave > reference_wave
        else 'raised_to_empirical_reference'
    )
    limit_payload.update(
        {
            'limited': selected_wave > reference_wave,
            'aligned': True,
            'alignment_direction': alignment_direction,
            'uncapped_selected_max_wave': selected_wave,
        }
    )
    update_payload = {
        'selected_max_wave': int(reference_wave),
        'selected_first_failed_wave': int(reference_wave) + 1,
        'unsupported_pressure_reference_aligned': True,
        'unsupported_pressure_reference_alignment_direction': alignment_direction,
    }
    if selected_wave > reference_wave:
        terminal_limits = dict(summary.get('terminal_pressure_limits') or {})
        terminal_limits['unsupported_pressure_empirical_reference'] = int(reference_wave)
        update_payload.update(
            {
                'selected_max_independent_wave': min(
                    int(summary.get('selected_max_independent_wave') or reference_wave),
                    int(reference_wave),
                ),
                'selected_model': f'{previous_model}_limited_by_unsupported_pressure_empirical_reference',
                'terminal_pressure_limits': dict(sorted(terminal_limits.items())),
                'terminal_pressure_limiter': 'unsupported_pressure_empirical_reference',
                'terminal_pressure_limited': True,
                'unsupported_pressure_reference_limited': True,
            }
        )
    else:
        update_payload.update(
            {
                'selected_max_independent_wave': max(
                    int(summary.get('selected_max_independent_wave') or selected_wave),
                    int(reference_wave),
                ),
                'selected_model': f'{previous_model}_aligned_to_unsupported_pressure_empirical_reference',
            }
        )
    summary.update(update_payload)


def _summary_wave_fields(
    operator_rows: list[dict[str, object]],
    *,
    survive_field: str,
) -> dict[str, int]:
    first_failed = 0
    last_contiguous_surviving = 0
    independent_surviving_waves: list[int] = []
    reached_failure = False
    for row in operator_rows:
        wave = int(row.get('display_wave') or 0)
        survives = bool(row.get(survive_field))
        if survives:
            independent_surviving_waves.append(wave)
            if not reached_failure:
                last_contiguous_surviving = wave
        elif not reached_failure:
            first_failed = wave
            reached_failure = True
    max_independent_surviving = max(independent_surviving_waves) if independent_surviving_waves else 0
    return {
        'last_contiguous_surviving_wave': last_contiguous_surviving,
        'max_independent_surviving_wave': max_independent_surviving,
        'first_failed_wave': first_failed,
    }


def _build_replacement_download_rows(operator_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for index, row in enumerate(operator_rows):
        missing = [field for field in BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS if field not in row]
        if missing:
            raise ValueError(f"Boss Waves Phase 2B export row {index} missing required replacement fields: {missing!r}")
        out.append({field: row.get(field) for field in BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS})
    return out


def _build_replacement_diagnostics(
    *,
    active_source: str,
    preset_name: str,
    config: dict[str, object],
    resolved_context: dict[str, object],
    perk_timeline_rows: int,
    perk_timeline_final_wave: int,
    scenario_runtime_inputs: dict[str, float],
    operator_rows: list[dict[str, object]],
    download_rows: list[dict[str, object]],
    summary: dict[str, object],
    stop_on_failure: bool,
    account_state,
    primitive_inputs: dict[str, float] | None = None,
    primitive_semantics_ledger: dict[str, object] | None = None,
) -> dict[str, object]:
    lane_order = ['avg', 'min', 'max']
    first_row = operator_rows[0] if operator_rows else {}
    milestone_alignment = _boss_wave_milestone_alignment(
        account_state=account_state,
        tier_number=int(config['tier_number']),
        dissonance_run_category=str(config.get('dissonance_run_category') or 'none'),
        summary=summary,
    )
    certification_runtime_inputs = ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs)
    certification_boss_damage_source = str(
        (primitive_inputs or {}).get('boss_damage_source')
        or (primitive_inputs or {}).get('gc_boss_damage_source')
        or ''
    )
    scenario_surfaces = dict(config.get('scenario_surfaces') or {})
    unsupported_terminal_pressures = sorted(
        {
            str(item)
            for item in (scenario_surfaces.get('unsupported_terminal_pressures') or ())
            if str(item)
        }
    )
    certification_payload = _boss_wave_model_certification_payload(
        contact_time_source=dict(config.get('scenario_runtime_input_sources') or {}).get(
            'boss_time_to_contact_seconds'
        ),
        runtime_inputs=certification_runtime_inputs,
        boss_damage_source=certification_boss_damage_source,
        non_boss_terminal_pressure_required=bool(unsupported_terminal_pressures),
        unsupported_terminal_pressures=unsupported_terminal_pressures,
        damage_health_decay_required=str(config.get('mode_id') or '') == 'tournament',
        boss_applicable_damage_required=_boss_wave_selected_model_requires_full_boss_bridge(
            selected_model=summary.get('selected_model'),
            boss_damage_source=certification_boss_damage_source,
        ),
    )
    primitive_family_coverage = dict(
        (primitive_inputs or {}).get('replacement_primitive_family_coverage')
        or (primitive_semantics_ledger or {}).get('replacement_primitive_family_coverage')
        or {}
    )
    primitive_input_values = {
        str(key): value
        for key, value in dict(primitive_inputs or {}).items()
        if str(key) != 'replacement_primitive_family_coverage'
    }
    return {
        'preset_name': preset_name,
        'mode_id': config['mode_id'],
        'tier_number': int(config['tier_number']),
        'tier_column': config['tier_column'],
        'requested_tier_number': int(config.get('requested_tier_number') or config['tier_number']),
        'league': config.get('league'),
        'tournament_wave': int(config.get('tournament_wave') or 0) or None,
        'tournament_wave_source': config.get('tournament_wave_source'),
        'perks_enabled': bool(config['perks_enabled']),
        'perk_mode': str(config.get('perk_mode') or ''),
        'perk_state': str(config.get('perk_state') or ''),
        'requested_perk_mode': str(config.get('requested_perk_mode') or ''),
        'requested_perk_state': str(config.get('requested_perk_state') or ''),
        'requested_perk_policy_preset': str(config.get('requested_perk_policy_preset') or ''),
        'perk_policy_preset': str(config.get('perk_policy_preset') or ''),
        'loadout_profile_preset': str(config.get('loadout_profile_preset') or ''),
        'card_profile_preset': str(config.get('card_profile_preset') or ''),
        'selected_loadout_type': _boss_wave_loadout_type(str(config.get('perk_policy_preset') or '')),
        'perk_contract_owner': str(config.get('perk_contract_owner') or ''),
        'perk_mode_source': str(config.get('perk_mode_source') or ''),
        'perk_state_source': str(config.get('perk_state_source') or ''),
        'perk_request_resolution': str(config.get('perk_request_resolution') or ''),
        'perk_application_mode': str(config.get('perk_application_mode') or ''),
        'perk_config_resolution': dict(config.get('perk_config_resolution') or {}),
        'perk_policy_validation': dict(config.get('perk_policy_validation') or {}),
        'perk_policy_override_active': bool(config.get('perk_policy_override_active')),
        'perk_timeline_enabled': str(config.get('perk_application_mode') or '') == 'runtime_timeline',
        'perk_timeline_rows': int(perk_timeline_rows),
        'perk_timeline_final_wave': int(perk_timeline_final_wave),
        'perk_static_count': int(config.get('static_perk_count') or 0),
        'perk_static_pick_count': int(config.get('static_perk_pick_count') or 0),
        'context_status': summary.get('status') or 'complete',
        'context_error': summary.get('failure_kind'),
        'context_error_message': summary.get('failure_message'),
        'post_failure_truncation_kind': summary.get('post_failure_truncation_kind'),
        'post_failure_truncation_message': summary.get('post_failure_truncation_message'),
        'terminal_pressure_limits': dict(summary.get('terminal_pressure_limits') or {}),
        'terminal_pressure_limiter': summary.get('terminal_pressure_limiter'),
        'terminal_pressure_limited': bool(summary.get('terminal_pressure_limited')),
        'unsupported_pressure_reference_limit': dict(summary.get('unsupported_pressure_reference_limit') or {}),
        'unsupported_pressure_reference_limited': bool(summary.get('unsupported_pressure_reference_limited')),
        'unsupported_pressure_reference_aligned': bool(summary.get('unsupported_pressure_reference_aligned')),
        'unsupported_pressure_reference_alignment_direction': summary.get(
            'unsupported_pressure_reference_alignment_direction'
        ),
        'unsupported_pressure_missing_reference_blocked': bool(
            summary.get('unsupported_pressure_missing_reference_blocked')
        ),
        'pressure_factor_reference_hint': dict(summary.get('pressure_factor_reference_hint') or {}),
        'model_scope': 'boss_contact_survivability',
        'not_full_max_wave_model': True,
        'model_certification_status': certification_payload.get('model_certification_status'),
        'model_closure_status': certification_payload.get('model_closure_status'),
        'certified_full_max_wave_model': bool(certification_payload.get('certified_full_max_wave_model')),
        'model_completion_blockers': list(certification_payload.get('model_completion_blockers') or []),
        'accepted_approximation_closure': dict(
            certification_payload.get('accepted_approximation_closure') or {}
        ),
        'runtime_override_closure': dict(certification_payload.get('runtime_override_closure') or {}),
        'effective_model_closure': dict(certification_payload.get('effective_model_closure') or {}),
        'terminal_pressure_runtime_override_status': dict(
            certification_payload.get('terminal_pressure_runtime_override_status') or {}
        ),
        'non_boss_terminal_pressure_closure': dict(
            certification_payload.get('non_boss_terminal_pressure_closure') or {}
        ),
        'model_certification': certification_payload,
        'unsupported_terminal_pressures': list(unsupported_terminal_pressures),
        'dissonance_run_category': str(config.get('dissonance_run_category') or 'none'),
        'dissonance_run_label': _BOSS_WAVE_DISSONANCE_RUN_LABELS[
            _normalize_boss_wave_dissonance_run_category(config.get('dissonance_run_category') or 'none')
        ],
        'dissonance_run_mask': dict((primitive_semantics_ledger or {}).get('dissonance_run_mask') or {}),
        'pbh_explicit_uptime_supported': True,
        'pbh_explicit_uptime_mode': 'active_when_runtime_input_present_else_duration_over_cooldown',
        'actual_boss_interval_waves': int(config['boss_interval_waves']),
        'checkpoint_every_bosses': int(config['checkpoint_every_bosses']),
        'checkpoint_stride_waves': int(config['boss_interval_waves']) * int(config['checkpoint_every_bosses']),
        'requested_start_wave': int(config['start_wave']),
        'first_checkpoint_wave': int(operator_rows[0].get('display_wave') or 0) if operator_rows else None,
        'state_mode': config['state_mode'],
        'checkpoint_mode': 'actual_boss_cadence_with_sampling',
        'stop_on_failure': bool(stop_on_failure),
        'scenario_runtime_inputs': dict(scenario_runtime_inputs),
        'scenario_runtime_input_sources': dict(config.get('scenario_runtime_input_sources') or {}),
        'contact_time_contract': {
            'boss_time_to_contact_seconds': {
                'value': (primitive_inputs or {}).get('boss_time_to_contact_seconds'),
                'source': (primitive_inputs or {}).get('boss_time_to_contact_source')
                or dict(config.get('scenario_runtime_input_sources') or {}).get(
                    'boss_time_to_contact_seconds',
                    'not_supplied',
                ),
                'ownership': 'runtime_input_override_or_simulator_derived_from_base_travel_and_slow_effects',
                'derived_by_simulator': (primitive_inputs or {}).get('boss_time_to_contact_source')
                != 'runtime_input_boss_time_to_contact_seconds',
                'required_for_self_closing_boss_waves': True,
                'base_seconds': (primitive_inputs or {}).get('boss_time_to_contact_base_seconds'),
                'base_seconds_source': (primitive_inputs or {}).get(
                    'boss_time_to_contact_base_seconds_source'
                ),
                'geometry_proxy_status': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_proxy_status'
                ),
                'geometry_proxy_truth_status': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_proxy_truth_status'
                ),
                'geometry_tower_range_theoretical_m': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_tower_range_theoretical_m'
                ),
                'geometry_tower_range_displayed_m': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_tower_range_displayed_m'
                ),
                'geometry_wall_radius_displayed_m': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_wall_radius_displayed_m'
                ),
                'geometry_path_distance_to_wall_displayed_candidate_m': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_path_distance_to_wall_displayed_candidate_m'
                ),
                'geometry_reference_path_distance_to_wall_displayed_m': (primitive_inputs or {}).get(
                    'boss_time_to_contact_geometry_reference_path_distance_to_wall_displayed_m'
                ),
                'chrono_field_average_slow_fraction': (primitive_inputs or {}).get(
                    'boss_time_to_contact_chrono_field_average_slow_fraction'
                ),
                'slow_aura_fraction': (primitive_inputs or {}).get('boss_time_to_contact_slow_aura_fraction'),
                'enemy_speed_increase_fraction': (primitive_inputs or {}).get(
                    'boss_time_to_contact_enemy_speed_increase_fraction'
                ),
                'boss_speed_multiplier': (primitive_inputs or {}).get(
                    'boss_time_to_contact_boss_speed_multiplier'
                ),
                'movement_speed_multiplier': (primitive_inputs or {}).get(
                    'boss_time_to_contact_movement_speed_multiplier'
                ),
                'speed_remaining_fraction': (primitive_inputs or {}).get(
                    'boss_time_to_contact_speed_remaining_fraction'
                ),
                'energy_net_hold_seconds': (primitive_inputs or {}).get(
                    'boss_time_to_contact_energy_net_hold_seconds'
                ),
            },
        },
        'scenario_surfaces': dict(scenario_surfaces),
        'execution_mode': 'staged_replacement',
        'checkpoint_resolution_mode': 'replacement_table1_table2_overlay',
        'qe_resolution_count': 0,
        'timing_recompute_count': 0,
        'snapshot_reuse_count': 0,
        'qe_dirty_reresolve_count': 0,
        'delta_fallback_count': 0,
        'source_selection': {
            'operator_table_source': active_source,
            'summary_source': active_source,
            'csv_export_source': active_source,
            'diagnostics_source': active_source,
        },
        'replacement_model': {
            'run_plan_owner': 'qe.run_plan',
            'combat_owner': 'simulators.evaluator_kernel',
            'contract_version': 'boss_waves_replacement_v1',
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification': certification_payload,
            'table1_source_basis': 'app_pipeline_qe_checkpoint_surfaces_to_run_plan',
            'table2_source_basis': 'replacement_scenario_overlay',
            'survivability_derivation': 'baseline_qe_primitives_rederived_per_table1_row_from_workshop_levels_then_finalized_by_table2',
            'perk_state_derivation': 'table1_compiled_perk_state_per_checkpoint_from_runtime_policy_projection',
            'death_wave_health_multiplier_applies_to': 'table1_row_evolved_tower_hp_then_wall_hp_not_wall_regen_or_enemy_health',
            'boss_ttk_contract': 'v21_events_plus_continuous_boss_damage',
            'boss_kill_sources': ['plasma_cannon', 'orbs', 'electrons', 'continuous_boss_damage', 'thorns_contact'],
            'contact_resolution_sources': ['wall_thorns_contact'],
            'thorns_contact_source': 'wall_thorns_contact_damage_pct_derived_from_tower_thorns_and_wall_thorns_lab',
            'wall_thorns_repeated_hit_multiplier': 'Sharp Fortitude primary armor adds +1% wall-thorns damage taken per subsequent contact hit',
            'boss_survival_model': 'max_waves_compares_v21_plus_continuous_boss_ttk_against_hit_by_hit_wall_ttd_with_between_hit_regen_only',
            'stochastic_survival_policy': {
                'death_defy': 'diagnostic_only_not_applied_to_deterministic_boss_contact_ttd',
                'death_defy_chance_pct': (primitive_inputs or {}).get('death_defy_chance_pct'),
                'death_defy_effective_chance_pct': (primitive_inputs or {}).get('death_defy_effective_chance_pct'),
            },
            'flame_bot_hit_model': 'static_uniform_center_overlap_recomputed_per_operator_row_over_boss_lifetime_when_ttk_is_known',
            'flame_bot_hit_state_semantics': 'persistent_until_boss_death_after_first_flame_bot_hit',
            'damage_reduction_perk_sources': [
                'PERK_DEFENSE_PERCENT_4_00:tower_defense_pct_points_add',
                'PERK_X1_15_DEFENSE_ABSOLUTE:tower_defense_absolute_multiplier',
                'PERK_BLACK_HOLE_DURATION_12_0S:black_hole_duration_seconds_add',
                'PERK_CHRONO_FIELD_DURATION_5S:chrono_field_duration_seconds_add',
            ],
            'timed_dr_perk_sources': ['PERK_BLACK_HOLE_DURATION_12_0S:black_hole_duration_seconds_add', 'PERK_CHRONO_FIELD_DURATION_5S:chrono_field_duration_seconds_add'],
            'perk_contract_owner': str(config.get('perk_contract_owner') or ''),
            'perk_policy_preset': str(config.get('perk_policy_preset') or ''),
            'loadout_profile_preset': str(config.get('loadout_profile_preset') or ''),
            'perk_mode_source': str(config.get('perk_mode_source') or ''),
            'perk_state_source': str(config.get('perk_state_source') or ''),
            'perk_request_resolution': str(config.get('perk_request_resolution') or ''),
            'perk_application_mode': str(config.get('perk_application_mode') or ''),
            'perk_mode': str(config.get('perk_mode') or ''),
            'perk_state': str(config.get('perk_state') or ''),
            'timed_dr_sources': list(
                ((primitive_semantics_ledger or {}).get('timed_dr_semantic_contract') or {}).get('sources', {}).keys()
            ),
            'continuous_tower_dps_included': True,
            'selected_max_wave_model': summary.get('selected_model'),
            'dissonance_run_category': str(config.get('dissonance_run_category') or 'none'),
            'dissonance_run_mask_owner': 'kb/global-rules/contracts/dissonant-run-restrictions.yaml via qe.kb_surfaces; app.pipeline applies the loaded mask before qe.run_plan Table 1',
            'unsupported_terminal_pressures': list(unsupported_terminal_pressures),
            'pre_contact_boss_kill_model': summary.get('pre_contact_boss_kill_model'),
            'gc_pre_contact_model': summary.get('gc_pre_contact_model'),
            'lane_order': lane_order,
            'summary_lane_id': 'avg',
            'field_map_artifact': str(BOSS_WAVE_FIELD_MAP_PATH.relative_to(ROOT)),
            'intentional_semantic_differences': {
                'boss_ttk': 'replacement uses v21 boss-event kill sources plus QE-owned EP eDamage with Boss Waves exposure replacement; QE-owned Chain Lightning boss DPS remains diagnostic/fallback context',
            },
        },
        'replacement_primitive_inputs': {
            'layer': 'start_of_run_static_primitives_plus_second_wind_mastery_regen_projection_plus_row_evolved_workshop_skip_inputs_not_final_displayed_rows',
            'loadout_profile_preset': str(config.get('loadout_profile_preset') or ''),
            'card_profile_preset': str(config.get('card_profile_preset') or ''),
            'values': primitive_input_values,
        },
        'replacement_primitive_family_coverage': primitive_family_coverage,
        'replacement_primitive_semantics_ledger': dict(primitive_semantics_ledger or {}),
        'milestone_alignment': milestone_alignment,
        'replacement_display_derivation': {
            'wall_hp': 'operator_rows.wall_hp = table2.final_wall_hp_pre_fort * table1.wall_fortification_multiplier * scenario.wall_fortification_multiplier; pre-fort wall HP is derived from tower_hp * wall_health_ratio * wall_health_multipliers',
            'wall_regen': 'operator_rows.wall_regen = resolved tower_regen * wall_regen_percent_points / 100, after Table 1 contributor re-derivation and Table 2 scenario transforms',
            'wall_pre_fort_hp': 'operator_rows.wall_pre_fort_hp = table2.final_wall_hp_pre_fort; not shown as the primary Wall HP product column',
        },
        'boss_wave_debug_ledger': _boss_wave_debug_ledger(operator_rows),
        'replacement_outputs': {
            'operator_row_count': len(operator_rows),
            'download_row_count': len(download_rows),
            'export_field_count': len(BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS),
            'export_fields': list(BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS),
            'operator_handle_count': sum(1 for row in operator_rows if row.get('operator_handle_id')),
            'first_operator_handle_id': first_row.get('operator_handle_id'),
            'first_lane_handle_ids': dict(first_row.get('lane_handle_ids') or {}),
            'max_surviving_wave': int(summary.get('max_surviving_wave') or 0),
            'last_contiguous_surviving_wave': int(summary.get('last_contiguous_surviving_wave') or 0),
            'max_independent_surviving_wave': int(summary.get('max_independent_surviving_wave') or 0),
            'first_failed_wave': int(summary.get('first_failed_wave') or 0),
            'execution_status': summary.get('status') or 'complete',
            'failure_kind': summary.get('failure_kind'),
            'first_unresolved_wave': summary.get('first_unresolved_wave'),
        },
    }


def _boss_wave_milestone_alignment(
    *,
    account_state,
    tier_number: int,
    dissonance_run_category: str = 'none',
    summary: dict[str, object],
) -> dict[str, object]:
    tier_label = f'Tier {int(tier_number)}'
    category = _normalize_boss_wave_dissonance_run_category(dissonance_run_category)
    raw_reference = (getattr(account_state, 'tier_progression_waves', {}) or {}).get(tier_label)
    reference_raw_wave = _extract_wave_number_including_zero(raw_reference)
    reference_wave = _extract_optional_wave_number(raw_reference)
    dissonance_pbs = dict((getattr(account_state, 'dissonance_pbs_by_tier', {}) or {}).get(tier_label) or {})
    dissonance_pb_reference_raw_wave = (
        _extract_wave_number_including_zero(dissonance_pbs.get(category))
        if category != 'none'
        else None
    )
    dissonance_pb_reference_wave = (
        _extract_optional_wave_number(dissonance_pbs.get(category))
        if category != 'none'
        else None
    )
    active_reference_kind = 'ids_milestone_wave' if category == 'none' else 'ids_dissonant_pb_wave'
    active_reference_source = (
        'IDS::Player & Stuff.tier_progression_waves'
        if category == 'none'
        else 'IDS::Player & Stuff.dissonance_pbs_by_tier'
    )
    active_reference_wave = reference_wave if category == 'none' else dissonance_pb_reference_wave
    active_reference_raw_wave = reference_raw_wave if category == 'none' else dissonance_pb_reference_raw_wave
    selected_wave = summary.get('selected_max_wave')
    calculated_wave = (
        int(selected_wave)
        if selected_wave is not None
        else int(summary.get('max_surviving_wave') or summary.get('max_wave') or 0)
    )
    out: dict[str, object] = {
        'source': 'IDS::Player & Stuff.tier_progression_waves',
        'tier_column': tier_label,
        'dissonance_run_category': category,
        'reference_wave': reference_wave,
        'reference_raw_wave': reference_raw_wave,
        'dissonance_pb_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'dissonance_pb_reference_wave': dissonance_pb_reference_wave,
        'dissonance_pb_reference_raw_wave': dissonance_pb_reference_raw_wave,
        'active_reference_kind': active_reference_kind,
        'active_reference_source': active_reference_source,
        'active_reference_wave': active_reference_wave,
        'active_reference_raw_wave': active_reference_raw_wave,
        'active_reference_gap_reason': (
            None
            if active_reference_wave is not None and active_reference_wave > 0
            else _boss_wave_reference_gap_reason(active_reference_raw_wave)
        ),
        'calculated_max_surviving_wave': calculated_wave,
        'calculated_selected_max_wave': calculated_wave,
        'selected_model': summary.get('selected_model'),
        'comparison_status': f'no_{active_reference_kind}',
    }
    if active_reference_wave is None or active_reference_wave <= 0:
        return out
    delta = calculated_wave - int(active_reference_wave)
    out.update(
        {
            'comparison_status': (
                'solver_incomplete'
                if str(summary.get('status') or 'complete') != 'complete'
                else 'comparison_available'
            ),
            'delta_waves': delta,
            'abs_delta_waves': abs(delta),
            'calculated_to_reference_ratio': calculated_wave / float(active_reference_wave),
        }
    )
    return out


def _boss_wave_debug_ledger(operator_rows: list[dict[str, object]]) -> dict[str, object]:
    if not operator_rows:
        return {'sample_rows': [], 'first_failed_wave': 0}
    sample_waves = {9, 999, 3000, 4000, 5000, 6000}
    failed = next((row for row in operator_rows if not bool(row.get('survives_boss'))), None)
    if failed:
        sample_waves.add(int(failed.get('display_wave') or 0))
    rows_by_wave = {int(row.get('display_wave') or 0): row for row in operator_rows}
    selected: list[dict[str, object]] = []
    for target in sorted(wave for wave in sample_waves if wave > 0):
        candidate_wave = min(rows_by_wave, key=lambda wave: abs(wave - target))
        row = rows_by_wave[candidate_wave]
        selected.append(
            {
                'requested_wave': target,
                'display_wave': int(row.get('display_wave') or 0),
                'effective_attack_wave': int(row.get('attack_wave') or 0),
                'effective_health_wave': int(row.get('health_wave') or 0),
                'boss_hp': row.get('boss_health'),
                'boss_attack': row.get('boss_attack'),
                'ttk_seconds': row.get('boss_ttk_seconds'),
                'boss_killed_before_contact': bool(row.get('boss_killed_before_contact')),
                'plasma_cannon_damage_to_boss_pct': row.get('boss_plasma_cannon_damage_to_boss_pct'),
                'orb_damage_to_boss_pct': row.get('boss_orb_damage_to_boss_pct'),
                'electron_damage_to_boss_pct': row.get('boss_electron_damage_to_boss_pct'),
                'continuous_damage_to_boss_pct': row.get('boss_continuous_damage_to_boss_pct'),
                'wall_thorns_damage_to_boss_pct': row.get('boss_wall_thorns_damage_to_boss_pct'),
                'expected_wall_thorns_damage_from_hits_pct': row.get('boss_expected_wall_thorns_damage_from_hits_pct'),
                'wall_thorns_contact_kill_seconds': row.get('boss_wall_thorns_contact_kill_seconds'),
                'boss_time_to_contact_seconds': row.get('boss_time_to_contact_seconds'),
                'boss_hits_taken': row.get('boss_hits_taken'),
                'boss_hits_to_player': row.get('boss_hits_to_player'),
                'wall_thorns_hits': row.get('boss_wall_thorns_hits'),
                'dr_used_pct': row.get('effective_damage_reduction_pct'),
                'wall_pre_fort_hp': row.get('wall_pre_fort_hp'),
                'wall_hp': row.get('wall_hp'),
                'wall_regen': row.get('wall_regen'),
                'regen_gained': row.get('wall_regen_gained_hp'),
                'total_damage_taken': row.get('boss_total_damage_taken'),
                'survival_margin': row.get('boss_survival_margin_hp'),
                'survives': bool(row.get('survives_boss')),
                'contact_envelope_regen_gained': row.get('contact_envelope_wall_regen_gained_hp'),
                'contact_envelope_damage_taken': row.get('contact_envelope_total_damage_taken'),
                'contact_envelope_survival_margin': row.get('contact_envelope_survival_margin_hp'),
                'contact_envelope_survives': bool(row.get('contact_envelope_survives_boss')),
                'fail_reason': row.get('fail_reason'),
            }
        )
    return {
        'sample_rows': selected,
        'first_failed_wave': int(failed.get('display_wave') or 0) if failed else 0,
        'ledger_purpose': 'separates player stats, boss stats, TTK, and TTD for T14 Farming-style sanity debugging',
    }


def _optional_runtime_float(payload: dict[str, float], key: str) -> float | None:
    raw_value = payload.get(key)
    if raw_value in (None, ''):
        return None
    try:
        return float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Boss Waves replacement runtime input {key!r} must be numeric, got {raw_value!r}") from exc


def _boss_wave_death_wave_health_max_multiplier(account_state, *, scenario_runtime_inputs: dict[str, float]) -> float:
    runtime_value = _optional_runtime_float(scenario_runtime_inputs, 'death_wave_health_max_multiplier')
    if runtime_value is not None:
        return max(0.0, float(runtime_value))
    lab_level = int((getattr(account_state, 'labs', {}) or {}).get('Death Wave Health') or 0)
    if lab_level <= 0:
        return 1.0
    return 5.0 + (0.25 * lab_level)


def _boss_wave_wall_thorns_damage_increase_per_hit(account_state, *, preset_name: str) -> float:
    module_presets = getattr(account_state, 'module_presets', {}) or {}
    preset = module_presets.get(preset_name) or {}
    armor = preset.get('armor') if isinstance(preset, dict) else None
    primary = str(getattr(armor, 'primary', '') or '').strip()
    assist = str(getattr(armor, 'assist', '') or '').strip()
    if primary == 'Sharp Fortitude':
        return 0.01
    if assist == 'Sharp Fortitude':
        raise ValueError(
            "Boss Waves cannot derive Sharp Fortitude assist wall-thorns vulnerability without an owned assist-efficiency primitive"
        )
    return 0.0


def _boss_wave_module_equipped(account_state, *, preset_name: str, module_name: str) -> bool:
    module_presets = getattr(account_state, 'module_presets', {}) or {}
    preset = module_presets.get(preset_name) or {}
    if not isinstance(preset, dict):
        return False
    wanted = str(module_name).strip()
    for selection in preset.values():
        primary = str(getattr(selection, 'primary', '') or '').strip()
        assist = str(getattr(selection, 'assist', '') or '').strip()
        if wanted in {primary, assist}:
            return True
    return False


def _boss_wave_timed_dr_inputs(
    runtime_inputs: ScenarioRuntimeInputs,
    *,
    primitives: dict[str, float],
) -> tuple[dict[str, float], dict[str, object]]:
    flame_bot_dr_pct = _runtime_nonnegative_float(runtime_inputs, 'flame_bot_damage_reduction_pct')
    flame_bot_hit_chance_pct = _runtime_nonnegative_float(runtime_inputs, 'flame_bot_boss_hit_chance_pct')
    flame_bot_duration = _runtime_nonnegative_float(runtime_inputs, 'flame_bot_duration_seconds')
    flame_bot_runtime_enabled = (
        flame_bot_dr_pct is not None
        or flame_bot_hit_chance_pct is not None
        or flame_bot_duration is not None
    )
    flame_bot_cooldown = _runtime_nonnegative_float(runtime_inputs, 'flame_bot_cooldown_seconds') if flame_bot_runtime_enabled else None
    if flame_bot_dr_pct is None:
        flame_bot_dr_pct = _qe_ratio_or_percent_to_pct(float(primitives.get('flame_bot_damage_reduction_pct') or 0.0))
    if flame_bot_cooldown is None:
        flame_bot_cooldown = _positive_or_none(primitives.get('flame_bot_cooldown_seconds'))
    flame_bot_static_hit_chance: float | None = None
    flame_bot_static_hit_components: dict[str, object] | None = None
    if flame_bot_hit_chance_pct is None and flame_bot_duration is None:
        static_hit_chance, static_hit_components = flame_bot_static_boss_hit_chance(
            tower_range_m=primitives.get('tower_range_m'),
            flame_bot_effective_range_m=primitives.get('flame_bot_effective_range_m'),
            flame_bot_cooldown_seconds=flame_bot_cooldown,
            boss_time_to_contact_seconds=primitives.get('boss_time_to_contact_seconds'),
            energy_net_hold_seconds=primitives.get('boss_time_to_contact_energy_net_hold_seconds'),
        )
        flame_bot_static_hit_components = static_hit_components
        primitives['flame_bot_static_boss_hit_chance_pct'] = float(static_hit_components.get('hit_chance_pct') or 0.0)
        primitives['flame_bot_static_boss_hit_chance_status'] = str(static_hit_components.get('status') or '')
        if static_hit_components.get('status') == 'resolved':
            flame_bot_static_hit_chance = static_hit_chance

    defense_field_dr_pct = _runtime_nonnegative_float(runtime_inputs, 'defense_field_damage_reduction_pct')
    defense_field_duration = _runtime_nonnegative_float(runtime_inputs, 'defense_field_duration_seconds')
    defense_field_runtime_enabled = defense_field_dr_pct is not None or defense_field_duration is not None
    defense_field_cooldown = _runtime_nonnegative_float(runtime_inputs, 'defense_field_cooldown_seconds') if defense_field_runtime_enabled else None

    black_hole_dr_pct = _runtime_nonnegative_float(runtime_inputs, 'black_hole_damage_reduction_pct')
    black_hole_duration = _runtime_nonnegative_float(runtime_inputs, 'black_hole_duration_seconds')
    pbh_uptime = _runtime_nonnegative_float(runtime_inputs, 'pbh_encounter_uptime_fraction')
    black_hole_runtime_enabled = black_hole_dr_pct is not None or black_hole_duration is not None or pbh_uptime is not None
    black_hole_cooldown = _runtime_nonnegative_float(runtime_inputs, 'black_hole_cooldown_seconds') if black_hole_runtime_enabled else None
    if black_hole_dr_pct is None:
        black_hole_dr_pct = _positive_or_none(primitives.get('primordial_collapse_bh_damage_reduction_pct'))
    if black_hole_duration is None:
        black_hole_duration = _positive_or_none(primitives.get('black_hole_duration_seconds'))
    if black_hole_cooldown is None:
        black_hole_cooldown = _positive_or_none(primitives.get('black_hole_cooldown_seconds'))

    flame_bot_explicit_uptime = None
    flame_bot_uptime_source = 'explicit_uptime_fraction'
    flame_bot_status = 'runtime_or_qe_primitives'
    if flame_bot_hit_chance_pct is not None:
        flame_bot_explicit_uptime = max(0.0, min(1.0, float(flame_bot_hit_chance_pct) / 100.0))
        flame_bot_uptime_source = 'manual_boss_hit_chance_fraction'
        flame_bot_status = 'manual_boss_hit_chance_binary_model'
    elif flame_bot_static_hit_chance is not None:
        flame_bot_explicit_uptime = flame_bot_static_hit_chance
        flame_bot_uptime_source = 'static_boss_path_overlap_fraction'
        flame_bot_status = 'static_boss_path_overlap_model'
    elif flame_bot_dr_pct is not None and flame_bot_duration is None:
        flame_bot_status = 'blocked_missing_static_hit_primitives'

    flame_bot_source = timed_dr_source(
        damage_reduction_pct=flame_bot_dr_pct,
        duration_seconds=flame_bot_duration,
        cooldown_seconds=flame_bot_cooldown,
        explicit_uptime_fraction=flame_bot_explicit_uptime,
        explicit_uptime_source=flame_bot_uptime_source,
        primitive_status=flame_bot_status,
        binary_outcome=flame_bot_hit_chance_pct is not None or flame_bot_static_hit_chance is not None,
        binary_avg_hit_threshold=BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD,
    )
    if flame_bot_static_hit_components is not None:
        flame_bot_source['static_hit_chance_model'] = flame_bot_static_hit_components

    sources = {
        'flame_bot': flame_bot_source,
        'defense_field': timed_dr_source(
            damage_reduction_pct=defense_field_dr_pct,
            duration_seconds=defense_field_duration,
            cooldown_seconds=defense_field_cooldown,
            primitive_status=(
                'explicit_runtime_only_no_qe_surface_found'
                if defense_field_dr_pct is None and defense_field_duration is None and defense_field_cooldown is None
                else 'runtime_primitives'
            ),
            binary_avg_hit_threshold=BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD,
        ),
        'black_hole_pbh': timed_dr_source(
            damage_reduction_pct=black_hole_dr_pct,
            duration_seconds=black_hole_duration,
            cooldown_seconds=black_hole_cooldown,
            explicit_uptime_fraction=pbh_uptime,
            primitive_status='qe_primordial_collapse_black_hole_primitives',
            binary_avg_hit_threshold=BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD,
        ),
    }
    return (
        timed_dr_lanes_from_sources(
            sources,
            binary_avg_hit_threshold=BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD,
            excluded_source_names=('black_hole_pbh',),
        ),
        sources,
    )


def _runtime_nonnegative_float(runtime_inputs: ScenarioRuntimeInputs, name: str) -> float | None:
    raw_value = getattr(runtime_inputs, name)
    if raw_value in (None, ''):
        return None
    value = float(raw_value)
    return value if value >= 0.0 else None


def _boss_wave_terminal_pressure_limits(runtime_inputs: ScenarioRuntimeInputs) -> dict[str, int]:
    fields = {
        'fleet_non_boss_pressure': 'fleet_terminal_max_wave',
        'elite_non_boss_pressure': 'elite_terminal_max_wave',
        'protector_non_boss_pressure': 'protector_terminal_max_wave',
        'armored_non_boss_pressure': 'armored_terminal_max_wave',
        'boss_deferred_pressure': 'boss_terminal_max_wave',
    }
    limits: dict[str, int] = {}
    for cause, field_name in fields.items():
        raw_value = getattr(runtime_inputs, field_name)
        if raw_value in (None, ''):
            continue
        value = int(float(raw_value))
        if value > 0:
            limits[cause] = value
    return limits


def _positive_or_none(raw_value: object) -> float | None:
    if raw_value in (None, ''):
        return None
    value = float(raw_value)
    return value if value > 0.0 else None


def _qe_ratio_or_percent_to_pct(raw_value: float) -> float | None:
    value = float(raw_value)
    if value <= 0.0:
        return None
    return value * 100.0 if value <= 1.0 else value



def _published_statbook_dict(statbook, *, manual_advisory_inputs: dict, account_state_labs: dict) -> dict:
    from qe.publication import publish_query_surfaces

    publish_query_surfaces(
        statbook.rows,
        manual_advisory_inputs=manual_advisory_inputs,
        account_state_labs=account_state_labs,
    )
    statbook_dict = statbook.to_dict()
    _annotate_display_fields(statbook_dict)
    return statbook_dict


def _annotate_compare_row_payloads_by_preset(rows_by_preset: dict[str, dict]) -> None:
    for rows in (rows_by_preset or {}).values():
        payload = {'rows': rows}
        _annotate_display_fields(payload)


def _manual_input_numeric_value(
    manual_advisory_inputs: dict,
    input_id: str,
    *,
    default: float | None = None,
) -> float | None:
    entry = (manual_advisory_inputs or {}).get(input_id)
    if not isinstance(entry, dict):
        return default
    if not entry.get('is_set', False) and entry.get('value') in (None, ''):
        return default
    try:
        return float(entry.get('value'))
    except (TypeError, ValueError):
        return default


def _merge_scenario_publication_rows(
    statbook,
    *,
    account_state,
    stat_inputs,
    preset_name: str,
    state_mode: str,
    perks_enabled: bool,
    manual_advisory_inputs: dict,
) -> None:
    scenario_config = _run_stats_scenario_config(account_state, preset_name=preset_name)
    scenario_perks_enabled = bool(perks_enabled)
    if scenario_config.mode_id == 'tournament':
        scenario_perks_enabled = False
    timing_family_id = _run_stats_timing_family_id(preset_name=preset_name, perks_enabled=scenario_perks_enabled)
    farming_hours_per_day = _manual_input_numeric_value(
        manual_advisory_inputs,
        'module.farming.hours_per_day',
        default=23.5,
    )
    merge_timing_scenario_publication_rows(
        statbook,
        account_state=account_state,
        stat_inputs=stat_inputs,
        family_id=timing_family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=scenario_perks_enabled,
        farming_hours_per_day=farming_hours_per_day,
    )
def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


def _perks_enabled_for_state(active_perk_preset: str | None, perk_state: str) -> bool:
    normalized = _normalize_perk_state(perk_state)
    if normalized == 'on':
        return True
    if normalized == 'off':
        return False
    return bool(active_perk_preset)


def _sanitized_account_state_for_output(account_state, canonical_output_preset: str) -> dict:
    payload = account_state.to_dict()
    namespace_class = getattr(account_state, 'perk_preset_namespace_class', 'canonical')
    payload['perk_presets'] = sanitize_perk_presets_for_canonical_output(
        payload.get('perk_presets') or {},
        namespace_class=namespace_class,
        fallback_preset_name=canonical_output_preset,
        active_preset_name=getattr(account_state, 'active_perk_preset', None),
    )
    payload['active_perk_preset'] = sanitize_preset_name_for_canonical_output(
        getattr(account_state, 'active_perk_preset', None),
        namespace_class=namespace_class,
        fallback_preset_name=canonical_output_preset,
    )
    return payload


def _sanitized_configured_perk_presets(account_state, canonical_output_preset: str) -> dict[str, list[str]]:
    raw = {name: [selection.perk_id for selection in selections] for name, selections in account_state.perk_presets.items()}
    return sanitize_perk_presets_for_canonical_output(
        raw,
        namespace_class=getattr(account_state, 'perk_preset_namespace_class', 'canonical'),
        fallback_preset_name=canonical_output_preset,
        active_preset_name=getattr(account_state, 'active_perk_preset', None),
    )


def _sanitized_active_perk_preset(account_state, canonical_output_preset: str) -> str | None:
    return sanitize_preset_name_for_canonical_output(
        getattr(account_state, 'active_perk_preset', None),
        namespace_class=getattr(account_state, 'perk_preset_namespace_class', 'canonical'),
        fallback_preset_name=canonical_output_preset,
    )


def _effective_perk_preset_for_publication(
    account_state,
    *,
    perk_preset_name: str | None,
    perks_enabled: bool,
    canonical_output_preset: str,
) -> str | None:
    if not perks_enabled or perk_preset_name is None:
        return None
    return sanitize_preset_name_for_canonical_output(
        perk_preset_name,
        namespace_class=getattr(account_state, 'perk_preset_namespace_class', 'canonical'),
        fallback_preset_name=canonical_output_preset,
    )


def _perk_selection_payload(account_state, perk_preset_name: str | None) -> dict:
    selections = account_state.perk_presets.get(perk_preset_name or '', []) if perk_preset_name else []
    return {
        'perk_preset_name': perk_preset_name,
        'selections': [
            {'perk_id': selection.perk_id, 'picks': selection.picks}
            for selection in selections
        ],
    }


def _preset_loadout_summary(account_state, *, preset_name: str, perk_preset_name: str | None) -> dict:
    module_preset = account_state.module_presets.get(preset_name, {})
    return {
        'preset_name': preset_name,
        'cards': list(account_state.card_presets.get(preset_name, [])),
        'modules': {
            slot_type: {
                'primary': selection.primary,
                'assist': selection.assist,
            }
            for slot_type, selection in module_preset.items()
        },
        'perks': _perk_selection_payload(account_state, perk_preset_name),
        'bots': {
            'enabled': list(account_state.bots),
            'upgrades': dict(account_state.bot_upgrades),
        },
    }


def _query_response_to_statbook_dict(
    response,
    *,
    bundle_id: str,
    trace_mode: str,
    manual_advisory_inputs: dict | None = None,
    account_state_labs: dict | None = None,
    publish_qe_surfaces: bool = False,
    annotate_display: bool = True,
) -> dict:
    statbook = query_response_to_statbook(
        response,
        notes='Resolved through run_stats bounded query bundle.',
        diagnostics={
            'bundle_id': bundle_id,
            'resolved_surface_count': len(response.resolved_surface_rows),
            'contributor_row_count': len(response.contributor_rows),
            'trace_mode': trace_mode,
        },
    )
    if publish_qe_surfaces:
        publish_query_surfaces(
            statbook.rows,
            manual_advisory_inputs=manual_advisory_inputs,
            account_state_labs=account_state_labs,
        )
    statbook_dict = statbook.to_dict()
    for surface_id, row in (statbook_dict.get('rows') or {}).items():
        row['stat_name'] = surface_id
        row['bundle_id'] = bundle_id
        row['family_id'] = response.family_id
        row['trace_mode'] = trace_mode
    statbook_dict['diagnostics'] = {
        **dict(statbook_dict.get('diagnostics') or {}),
        'family_id': response.family_id,
        'bundle_id': bundle_id,
        'resolved_surface_count': len(statbook_dict.get('rows') or {}),
        'contributor_row_count': len(response.contributor_rows),
        'trace_mode': trace_mode,
    }
    if annotate_display:
        _annotate_display_fields(statbook_dict)
    return statbook_dict


_RUN_STATS_QUERY_OUTPUTS = {
    'start_of_run_rows': 'run_stats_query_rows_start_of_run.json',
    'max_progression_rows': 'run_stats_query_rows_max_progression.json',
    'start_of_run_plan': 'run_stats_query_plan_start_of_run.json',
    'max_progression_plan': 'run_stats_query_plan_max_progression.json',
}

def _remove_run_stats_legacy_outputs(out_dir: Path) -> None:
    _remove_legacy_outputs(out_dir, _RUN_STATS_LEGACY_OUTPUTS)


def _remove_run_stats_current_outputs(out_dir: Path) -> None:
    stale_full_pipeline_outputs = [
        name
        for name in FULL_PIPELINE_PUBLICATION_ARTIFACTS
        if name not in RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS
    ]
    for filename in dict.fromkeys(
        [*RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS, *stale_full_pipeline_outputs, 'pipeline_trace.json']
    ):
        path = out_dir / filename
        if path.exists():
            try:
                path.unlink()
            except FileNotFoundError:
                continue
    perk_diag_dir = out_dir / 'diagnostics' / 'perks'
    if perk_diag_dir.exists():
        shutil.rmtree(perk_diag_dir, ignore_errors=True)


def _merge_query_statbooks(*statbook_dicts: dict) -> dict:
    rows: dict[str, dict] = {}
    bundle_ids: list[str] = []
    family_ids: list[str] = []
    contributor_row_count = 0
    for statbook_dict in statbook_dicts:
        diag = statbook_dict.get('diagnostics', {})
        bundle_id = diag.get('bundle_id')
        family_id = diag.get('family_id')
        if bundle_id is not None:
            bundle_ids.append(bundle_id)
        if family_id is not None:
            family_ids.append(family_id)
        contributor_row_count += int(diag.get('contributor_row_count', 0) or 0)
        for surface_id, row in (statbook_dict.get('rows') or {}).items():
            rows[surface_id] = row
    merged = {
        'rows': dict(sorted(rows.items())),
        'diagnostics': {
            'bundle_ids': bundle_ids,
            'family_ids': family_ids,
            'resolved_surface_count': len(rows),
            'contributor_row_count': contributor_row_count,
        },
    }
    return merged


def _publish_query_surfaces_on_statbook_dict(
    statbook_dict: dict,
    *,
    manual_advisory_inputs: dict | None = None,
    account_state_labs: dict | None = None,
) -> dict:
    row_payloads = statbook_dict.get('rows') or {}
    rows: dict[str, StatRow] = {}
    for surface_id, payload in row_payloads.items():
        if not isinstance(payload, dict):
            continue
        contributors = payload.get('contributors') or []
        rows[surface_id] = StatRow(
            stat_name=str(payload.get('stat_name') or surface_id),
            final_value=payload.get('final_value'),
            value_type=str(payload.get('value_type') or 'scalar'),
            source_count=int(payload.get('source_count') or len(contributors)),
            status=str(payload.get('status') or 'unresolved'),
            notes=payload.get('notes'),
            contributors=list(contributors),
            schema=payload.get('schema'),
        )
    publish_query_surfaces(
        rows,
        manual_advisory_inputs=manual_advisory_inputs,
        account_state_labs=account_state_labs,
    )
    republished_rows = {}
    for surface_id, row in rows.items():
        payload = dict(row_payloads.get(surface_id) or {})
        payload.update(row.to_dict())
        republished_rows[surface_id] = payload
    for surface_id, row in republished_rows.items():
        row.setdefault('stat_name', surface_id)
        row.setdefault('bundle_id', 'merged_query_surfaces')
        row.setdefault('family_id', 'merged_query_surfaces')
        row.setdefault('trace_mode', 'full_trace')
    statbook_dict['rows'] = dict(sorted(republished_rows.items()))
    diagnostics = dict(statbook_dict.get('diagnostics') or {})
    diagnostics['post_merge_qe_publication'] = True
    diagnostics['resolved_surface_count'] = len(republished_rows)
    statbook_dict['diagnostics'] = diagnostics
    _annotate_display_fields(statbook_dict)
    return statbook_dict


def _extract_tier_number(value) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    digits = ''.join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _run_stats_progression_family_id(*, state_mode: str, perks_enabled: bool) -> str:
    if state_mode == 'start_of_run' and not perks_enabled:
        return 'progression_start_of_run'
    return 'progression_runtime_with_perks' if perks_enabled else 'progression_runtime_no_perks'


def _run_stats_timing_family_id(*, preset_name: str, perks_enabled: bool) -> str:
    if preset_name == 'Tourney':
        return 'timing_tournament_no_perks'
    if perks_enabled:
        return 'timing_farm_with_perks'
    return 'timing_scenario_probe'


def _run_stats_scenario_config(account_state, *, preset_name: str, tier_number: int | None = None):
    from simulators.scenario import ScenarioConfig

    if preset_name == 'Tourney':
        league = (
            account_state.player_meta.get('Tourney League')
            or account_state.player_meta.get('Tournament League')
            or account_state.player_meta.get('League')
        )
        return ScenarioConfig(mode_id='tournament', league=league)
    tier = (
        int(tier_number) if tier_number else None
    ) or (
        _extract_tier_number(account_state.player_meta.get('Farming Tier'))
        or _extract_tier_number(account_state.highest_tier_unlocked_label)
        or account_state.highest_tier_unlocked_number
        or 14
    )
    return ScenarioConfig(mode_id='farming', tier=int(tier))


def _run_stats_scenario_context(
    scenario_config,
    *,
    dissonance_run_category: object | None = None,
) -> dict[str, object]:
    context = {
        'mode_id': scenario_config.mode_id,
        'tier': scenario_config.tier,
        'league': scenario_config.league,
        'tournament_wave': scenario_config.tournament_wave,
    }
    category = _normalize_boss_wave_dissonance_run_category(dissonance_run_category or 'none')
    if category != 'none':
        context['dissonance_run_category'] = category
    return context


def _run_stats_perk_state(account_state, *, preset_name: str, perk_state: str, perk_mode: str, state_mode: str) -> tuple[str | None, bool]:
    if state_mode == 'start_of_run':
        return None, False
    if preset_name == 'Tourney':
        return None, False
    current_perk_preset_name = preset_name if preset_name in account_state.perk_presets else None
    current_perks_enabled = _perks_enabled_for_state(current_perk_preset_name, perk_state)
    if state_mode != 'max_progression':
        return current_perk_preset_name, current_perks_enabled
    if perk_mode != 'none' and account_state.active_perk_preset is not None:
        projected_preset_name = account_state.active_perk_preset
        return projected_preset_name, _perks_enabled_for_state(projected_preset_name, perk_state)
    return current_perk_preset_name, current_perks_enabled


def _build_dual_state_stats_view(start_statbook_dict: dict, max_statbook_dict: dict) -> dict:
    start_rows = start_statbook_dict.get('rows', {})
    max_rows = max_statbook_dict.get('rows', {})
    all_keys = sorted(set(start_rows) | set(max_rows))
    rows = {}
    changed_count = 0
    for key in all_keys:
        if key.startswith('raw::'):
            continue
        start_row = start_rows.get(key)
        max_row = max_rows.get(key)
        start_value = None if start_row is None else start_row.get('final_value')
        max_value = None if max_row is None else max_row.get('final_value')
        changed = (
            start_row is None
            or max_row is None
            or start_value != max_value
            or (start_row.get('status') if start_row else None) != (max_row.get('status') if max_row else None)
        )
        if changed:
            changed_count += 1
        rows[key] = {
            'stat_name': key,
            'changed_in_max_progression': changed,
            'start_of_run': None if start_row is None else {
                'final_value': start_value,
                'display_value': start_row.get('display_value'),
                'value_type': start_row.get('value_type'),
                'status': start_row.get('status'),
            },
            'max_progression': None if max_row is None else {
                'final_value': max_value,
                'display_value': max_row.get('display_value'),
                'value_type': max_row.get('value_type'),
                'status': max_row.get('status'),
            },
        }
    return {
        'rows': rows,
        'diagnostics': {
            'row_count': len(rows),
            'changed_in_max_progression_count': changed_count,
        },
    }


def _stable_run_stats_payload_for_commit(run_stats_payload: dict) -> dict:
    """Strip local timing telemetry from the committed run_stats baseline."""
    stable_payload = dict(run_stats_payload)
    diagnostics = dict(run_stats_payload.get('diagnostics') or {})
    diagnostics.pop('timings_ms', None)
    session = dict(diagnostics.get('session') or {})
    session.pop('account_state_build_ms', None)
    if session:
        diagnostics['session'] = session
    else:
        diagnostics.pop('session', None)
    preset_diagnostics = dict(diagnostics.get('presets') or {})
    copied_preset_diagnostics: dict[object, object] = {}
    for preset_name, preset_payload in preset_diagnostics.items():
        if not isinstance(preset_payload, dict):
            copied_preset_diagnostics[preset_name] = preset_payload
            continue
        preset_copy = dict(preset_payload)
        for state_mode in ('start_of_run', 'max_progression'):
            state_payload = dict(preset_payload.get(state_mode) or {})
            state_payload.pop('timings_ms', None)
            if state_payload:
                preset_copy[state_mode] = state_payload
            else:
                preset_copy.pop(state_mode, None)
        copied_preset_diagnostics[preset_name] = preset_copy
    diagnostics['presets'] = copied_preset_diagnostics
    stable_payload['diagnostics'] = diagnostics
    return stable_payload


def _perk_config_has_active_preset(config: dict) -> bool:
    if not isinstance(config, dict):
        return False
    active = config.get('active_perk_preset')
    presets = config.get('perk_presets') or {}
    return bool(active) and active in presets and bool(presets.get(active))


def _normalize_perk_mode(perk_mode: str | None) -> str:
    value = str(perk_mode or 'max_progression_policy').strip().lower()
    if value not in {'none', 'max_progression_policy', 'runtime_timeline'}:
        raise ValueError(f'Unsupported perk mode: {perk_mode}')
    return value


def _default_tradeoff_alias_map() -> dict[str, str]:
    return {
        "TO1": "x1.50 Tower Damage, but Bosses Have 8x Health",
        "TO2": "x1.80 coins, but Tower Max Health -70%",
        "TO3": "Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%",
        "TO4": "Enemies Damage -50%, but Tower Damage -50%",
        "TO5": "Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3",
        "TO6": "Enemies Speed -40%, But Enemies Damage x2.5",
        "TO7": "x12.00 Cash Per Wave, But Enemy Kill Don't Give Cash",
        "TO8": "Tower Health Regen x8.00, But Tower Max Max Health -60%",
        "TO9": "Boss Health -70%, But Boss Speed +50%",
        "TO10": "Lifesteal x2.50, But Knockback force -70%",
    }


def _resolve_policy_banned_perk_names(raw_policy: dict) -> list[str]:
    alias_map = _default_tradeoff_alias_map()
    ordered: list[str] = []
    seen: set[str] = set()
    for alias in list(raw_policy.get("banned_perk_aliases", []) or []):
        key = str(alias).strip().upper()
        name = alias_map.get(key)
        if name and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in list(raw_policy.get("banned_perks", []) or []):
        perk_name = str(name).strip()
        if perk_name and perk_name not in seen:
            ordered.append(perk_name)
            seen.add(perk_name)
    return ordered


def _ids_player_value(ids_raw, name: str, default: int = 0) -> int:
    sections = ('Player & Stuff', 'Labs')
    for section in sections:
        rows = ids_raw.raw_sections.get(section, []) if ids_raw else []
        for row in rows:
            if row and str(row[0]).strip() == name:
                token = str(row[1]).strip() if len(row) > 1 else ''
                try:
                    return int(float(token.replace(',', '')))
                except Exception:
                    return default
    return default


def _ids_unlocked_ultimate_weapons(ids_raw) -> list[str]:
    rows = ids_raw.raw_sections.get('UWs', []) if ids_raw else []
    if not rows:
        return []
    uw_layout = load_section_layout_contract()['uw']
    block_size = int(uw_layout['block_size'])
    name_col = int(uw_layout['name_column'])
    stat_rows_per_block = int(uw_layout['stat_rows_per_block'])
    unlocked: list[str] = []
    for idx in range(0, len(rows), block_size):
        block = rows[idx: idx + block_size]
        unlock_row_index = stat_rows_per_block - 1
        if len(block) <= unlock_row_index:
            continue
        uw_name = str(block[0][name_col] if len(block[0]) > name_col else '').strip()
        token = str(block[unlock_row_index][name_col] if len(block[unlock_row_index]) > name_col else '').strip().lower()
        if uw_name and token in {'true', 'yes', '1', 'unlocked'}:
            unlocked.append(uw_name)
    return sorted(unlocked)


def _resolve_manual_banned_perks(perk_policy: dict) -> list[str]:
    return _resolve_policy_banned_perk_names(perk_policy or {})


def _perk_policy_presets(perk_policy: dict | None) -> dict[str, dict]:
    raw = (perk_policy or {}).get('policy_presets') or {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(name).strip(): dict(payload)
        for name, payload in raw.items()
        if str(name).strip() and isinstance(payload, dict)
    }


def _normalize_perk_policy_preset_name(value: str | None) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    lowered = text.lower().replace('-', ' ').replace('_', ' ')
    compact = ' '.join(lowered.split())
    aliases = {
        'ehp max waves': 'eHP Max Waves',
        'ehp max wave': 'eHP Max Waves',
        'ehp milestone': 'eHP Max Waves',
        'ehp farming': 'eHP Farming',
        'ehp farm': 'eHP Farming',
        'gc max waves': 'GC Max Waves',
        'gc max wave': 'GC Max Waves',
        'gc milestone': 'GC Max Waves',
        'gc farming': 'GC Farming',
        'gc farm': 'GC Farming',
    }
    return aliases.get(compact, text)


def _base_perk_policy_fields(perk_policy: dict | None) -> dict:
    policy = dict(perk_policy or {})
    policy.pop('policy_presets', None)
    policy.pop('active_policy_preset', None)
    return policy


def _select_perk_policy(base_policy: dict | None, policy_preset: str | None) -> dict:
    base = dict(base_policy or {})
    presets = _perk_policy_presets(base)
    requested = _normalize_perk_policy_preset_name(policy_preset)
    selected = requested or _normalize_perk_policy_preset_name(str(base.get('active_policy_preset') or ''))
    policy = _base_perk_policy_fields(base)
    if selected:
        if selected not in presets:
            raise ValueError(f"Unknown perk_policy_preset {selected!r}; expected one of {sorted(presets)}")
        policy.update(dict(presets[selected]))
        policy['_selected_policy_preset'] = selected
    return policy


def _store_selected_perk_policy(base_policy: dict | None, selected_policy: dict, policy_preset: str | None) -> dict:
    selected = _normalize_perk_policy_preset_name(policy_preset)
    clean = {
        key: value
        for key, value in dict(selected_policy or {}).items()
        if not str(key).startswith('_')
    }
    if not selected:
        return clean
    out = dict(base_policy or {})
    presets = _perk_policy_presets(out)
    presets[selected] = clean
    out['policy_presets'] = presets
    out['active_policy_preset'] = selected
    return out


def _merged_perk_policy(base_policy: dict | None, override: dict[str, object] | None) -> dict:
    merged = dict(base_policy or {})
    if not override:
        return merged
    merged['_policy_override_active'] = True
    merged['_base_banned_perks_count'] = len(_resolve_policy_banned_perk_names(base_policy or {}))
    for key in ("seed", "target_wave", "banned_perks", "priority_order", "first_perk_choice"):
        if key not in override:
            continue
        value = override.get(key)
        if key in {"banned_perks", "priority_order"}:
            merged[key] = [str(item).strip() for item in (value or []) if str(item).strip()]
            if key == "banned_perks":
                merged.pop("banned_perk_aliases", None)
        elif key == "first_perk_choice":
            text = str(value or "").strip()
            if text:
                merged[key] = text
            else:
                merged.pop(key, None)
        elif value not in (None, ""):
            merged[key] = int(value)
    return merged


_PERK_FIXED_OPENERS: tuple[str, str] = (
    "Perk Wave Requirement -20.00%",
    "Increase Max Game Speed by +1.00",
)

_PERK_GOAL_TARGET_WEIGHTS: dict[str, dict[str, float]] = {
    "eHP Max Waves": {
        "tower_hp": 110.0,
        "tower_regen": 70.0,
        "def_pct": 12.0,
        "absolute_defense": 8.0,
        "enemy_damage": -95.0,
        "boss_health": -35.0,
        "boss_speed": -35.0,
        "enemy_health": -10.0,
        "tower_damage": 10.0,
        "uw_black_hole_duration_seconds": 24.0,
        "uw_chrono_field_duration_seconds": 24.0,
        "uw_death_wave_waves": 35.0,
        "orb_count": 12.0,
        "free_upgrade_chance_all": 8.0,
    },
    "eHP Farming": {
        "coins_per_kill_bonus": 120.0,
        "uw_golden_tower_bonus": 110.0,
        "uw_black_hole_duration_seconds": 90.0,
        "free_upgrade_chance_all": 15.0,
        "tower_hp": 45.0,
        "tower_regen": 25.0,
        "def_pct": 8.0,
        "enemy_damage": -70.0,
        "boss_health": -25.0,
        "boss_speed": -20.0,
        "uw_death_wave_waves": 35.0,
        "uw_chrono_field_duration_seconds": 18.0,
        "cash_bonus": 5.0,
        "cash_per_wave": 2.0,
        "enemy_kill_cash": 3.0,
        "tower_damage": 4.0,
        "uw_chain_lightning_damage": 6.0,
    },
    "GC Max Waves": {
        "tower_damage": 120.0,
        "uw_spotlight_damage_bonus": 110.0,
        "uw_chain_lightning_damage": 110.0,
        "boss_health": -145.0,
        "boss_speed": -30.0,
        "enemy_health": -25.0,
        "bounce_shot_count": 28.0,
        "orb_count": 22.0,
        "uw_chrono_field_duration_seconds": 18.0,
        "uw_black_hole_duration_seconds": 10.0,
        "enemy_damage": -25.0,
        "tower_hp": 5.0,
        "coins_per_kill_bonus": 1.0,
    },
    "GC Farming": {
        "coins_per_kill_bonus": 120.0,
        "uw_golden_tower_bonus": 110.0,
        "uw_black_hole_duration_seconds": 95.0,
        "free_upgrade_chance_all": 14.0,
        "tower_damage": 55.0,
        "uw_spotlight_damage_bonus": 45.0,
        "uw_chain_lightning_damage": 45.0,
        "boss_health": -50.0,
        "boss_speed": -20.0,
        "bounce_shot_count": 12.0,
        "orb_count": 8.0,
        "tower_hp": 18.0,
        "tower_regen": 10.0,
        "enemy_damage": -45.0,
        "uw_death_wave_waves": 15.0,
    },
}

_PERK_GOAL_NAME_SCORE_BIAS: dict[str, dict[str, float]] = {
    "eHP Max Waves": {
        "Interest x1.50": -8.0,
        "Land Mine Damage x3.50": -8.0,
        "x1.15 Cash Bonus": -6.0,
        "4 More Smart Missiles": -5.0,
        "Swamp Radius x1.5": -5.0,
        "Extra Set of Inner Mines": -5.0,
        "Unlock a Random Ultimate Weapon": -4.0,
    },
    "eHP Farming": {
        "Interest x1.50": -8.0,
        "Land Mine Damage x3.50": -8.0,
        "x1.15 Cash Bonus": -6.0,
        "4 More Smart Missiles": -5.0,
        "Swamp Radius x1.5": -5.0,
        "Extra Set of Inner Mines": -5.0,
        "Unlock a Random Ultimate Weapon": -4.0,
    },
    "GC Max Waves": {
        "Interest x1.50": -8.0,
        "Land Mine Damage x3.50": -8.0,
        "x1.15 Cash Bonus": -6.0,
        "x1.15 All Coin Bonuses": -4.0,
        "Golden Tower Bonus x1.5": -4.0,
        "x12.00 Cash Per Wave, But Enemy Kill Don't Give Cash": -6.0,
    },
    "GC Farming": {
        "Interest x1.50": -8.0,
        "Land Mine Damage x3.50": -8.0,
        "x1.15 Cash Bonus": -6.0,
        "4 More Smart Missiles": -5.0,
        "Swamp Radius x1.5": -5.0,
        "Extra Set of Inner Mines": -5.0,
        "Unlock a Random Ultimate Weapon": -4.0,
    },
}


def _perk_goal_effect_delta(*, operation: str, value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if operation in {'multiplier', 'remaining_fraction'}:
        return numeric - 1.0
    if operation == 'percentage_points_add':
        return numeric / 5.0
    if operation == 'seconds_add':
        return numeric / 10.0
    if operation in {'count_add', 'raw_add'}:
        return numeric
    if operation == 'set_to':
        return numeric - 1.0
    return 0.0


def _perk_goal_score_matrix(*, labs: dict[str, int]) -> tuple[list[dict[str, object]], dict[str, dict[str, float]]]:
    effects = load_perk_effects()
    perk_lab_state = {
        'standard_bonus_multiplier': 1.0 + (float(labs.get('Standard Perks Bonus', 0) or 0) / 100.0),
        'tradeoff_bonus_multiplier': 1.0 + (float(labs.get('Improve Trade-off Perks', 0) or 0) / 100.0),
    }
    matrix: list[dict[str, object]] = []
    score_by_goal: dict[str, dict[str, float]] = {goal: {} for goal in BOSS_WAVE_PERK_POLICY_PRESETS}
    for perk_id, perk_meta in sorted(load_perk_entities().items(), key=lambda item: str(item[1].get('perk_name') or item[0])):
        perk_name = str(perk_meta.get('perk_name') or perk_id)
        try:
            max_picks = max(1, int(perk_meta.get('max_picks') or 1))
        except (TypeError, ValueError):
            max_picks = 1
        scores = {goal: 0.0 for goal in BOSS_WAVE_PERK_POLICY_PRESETS}
        for effect in effects.get(perk_id, []):
            target = str(effect.get('target_stat_id') or '').strip()
            operation = str(effect.get('operation') or '').strip()
            if not target or not operation:
                continue
            effect_index = str(effect.get('effect_index') or '').strip()
            scaled = scaled_perk_value(
                perk_meta=perk_meta,
                perk_id=perk_id,
                operation=operation,
                raw_value=str(effect.get('effect_value') or ''),
                picks=max_picks,
                effect_index=effect_index,
                perk_lab_state=perk_lab_state,
                perk_effect_meta=effect,
            )
            delta = _perk_goal_effect_delta(operation=operation, value=scaled)
            for goal, weights in _PERK_GOAL_TARGET_WEIGHTS.items():
                scores[goal] += float(weights.get(target, 0.0)) * delta
        row: dict[str, object] = {'perk': perk_name}
        for goal in BOSS_WAVE_PERK_POLICY_PRESETS:
            scores[goal] += _PERK_GOAL_NAME_SCORE_BIAS.get(goal, {}).get(perk_name, 0.0)
            score = round(scores[goal], 6)
            row[goal] = score
            score_by_goal[goal][perk_name] = score
        matrix.append(row)
    return matrix, score_by_goal


def _generated_goal_perk_policy(
    *,
    policy: dict,
    preset_name: str,
    labs: dict[str, int],
    ban_capacity: int,
    unlocked_ultimate_weapons: list[str],
) -> tuple[dict[str, object], dict[str, object]]:
    from qe.perk_tables import load_perk_definitions

    matrix, score_by_goal = _perk_goal_score_matrix(labs=labs)
    scores = score_by_goal[preset_name]
    unlocked_uw = {str(name).strip().lower() for name in unlocked_ultimate_weapons if str(name).strip()}
    locked_uw_perks = {
        perk.perk_name
        for perk in load_perk_definitions()
        if perk.category == 'ultimate_weapon' and str(perk.required_uw or '').strip().lower() not in unlocked_uw
    }
    fixed = [name for name in _PERK_FIXED_OPENERS if name in scores]
    candidates = [name for name in scores if name not in fixed and name not in locked_uw_perks]
    banned = sorted(candidates, key=lambda name: (scores[name], name))[: max(0, int(ban_capacity))]
    banned_set = set(banned)
    priority = fixed + [
        name
        for name in sorted(candidates, key=lambda name: (-scores[name], name))
        if name not in banned_set and scores[name] > 0.0
    ]
    generated = dict(policy)
    generated['first_perk_choice'] = fixed[0] if fixed else policy.get('first_perk_choice')
    generated['priority_order'] = priority
    generated['banned_perks'] = banned
    generated.pop('banned_perk_aliases', None)
    return generated, {
        'generator': 'goal_benefit_matrix_v1',
        'preset_name': preset_name,
        'ban_capacity': int(ban_capacity),
        'fixed_openers': fixed,
        'generated_priority_order': priority,
        'generated_banned_perks': banned,
        'locked_uw_perks_excluded_before_ban_ranking': sorted(locked_uw_perks),
        'perk_goal_benefit_matrix': matrix,
    }


def _perk_policy_validation_ledger(policy_payload: dict, context: dict) -> dict[str, object]:
    from qe.perk_tables import load_perk_definitions

    definitions = {perk.perk_name: perk for perk in load_perk_definitions()}
    unlocked_uw = {str(name).strip().lower() for name in (policy_payload.get("unlocked_ultimate_weapons") or [])}
    errors: list[str] = []
    warnings: list[str] = []

    def _check_known(name: str, field_name: str) -> None:
        if name not in definitions:
            errors.append(f"{field_name} references unknown perk {name!r}")

    banned = [str(name).strip() for name in (policy_payload.get("banned_perks") or []) if str(name).strip()]
    priority = [str(name).strip() for name in (policy_payload.get("priority_order") or []) if str(name).strip()]
    first_choice = str(policy_payload.get("first_perk_choice") or "").strip()
    lab_ban_capacity = int(policy_payload.get("ban_perks_capacity") or context.get("ban_perks_capacity_ids") or 0)
    if len(banned) > lab_ban_capacity:
        errors.append(f"banned_perks has {len(banned)} entries but Ban Perks lab capacity is {lab_ban_capacity}")
    for name in banned:
        _check_known(name, "banned_perks")
    for name in priority:
        _check_known(name, "priority_order")
    if first_choice:
        _check_known(first_choice, "first_perk_choice")
        first_choice_unlocked = int(context.get("first_perk_choice_level") or 0) > 0 or bool(context.get("configured_first_perk_choice"))
        if not first_choice_unlocked:
            errors.append("first_perk_choice is configured but First Perk Choice lab is not unlocked")
        if first_choice in banned:
            errors.append(f"first_perk_choice {first_choice!r} is also banned")
    for field_name, names in (("banned_perks", banned), ("priority_order", priority), ("first_perk_choice", [first_choice] if first_choice else [])):
        for name in names:
            definition = definitions.get(name)
            if (
                definition is not None
                and definition.category == "ultimate_weapon"
                and str(definition.required_uw or "").strip().lower() not in unlocked_uw
            ):
                warnings.append(f"{field_name} perk {name!r} requires locked UW {definition.required_uw!r} and will be excluded")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "ban_perks_used": len(banned),
        "ban_perks_capacity": lab_ban_capacity,
        "first_perk_choice_unlocked": int(context.get("first_perk_choice_level") or 0) > 0 or bool(context.get("configured_first_perk_choice")),
    }


def build_perk_timeline_preview(
    request: PipelineRunRequest,
    *,
    perk_policy_override: dict[str, object] | None = None,
) -> dict[str, object]:
    from qe.perk_tables import load_perk_definitions
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy

    bundle = load_inputs(ids_path=request.ids, manual_inputs_path=request.manual_inputs)
    selected_policy_preset = _normalize_perk_policy_preset_name(getattr(request, 'perk_policy_preset', None))
    base_policy = getattr(bundle, "perk_policy", {}) or {}
    policy = _merged_perk_policy(_select_perk_policy(base_policy, selected_policy_preset), perk_policy_override)
    policy_payload, context = _perk_policy_context(bundle.ids_raw, policy)
    validation = _perk_policy_validation_ledger(policy_payload, context)
    timeline: list[dict[str, object]] = []
    diagnostics: dict[str, object] = {
        "enabled": False,
        "reason": "validation_failed",
        "generated_rows": 0,
        "final_wave": 0,
    }
    if validation["ok"]:
        timeline, diagnostics = generate_timeline_from_policy(PerkTimelinePolicy(**policy_payload))
    definitions = load_perk_definitions()
    eligible_perks = sorted(
        perk.perk_name
        for perk in definitions
        if perk.perk_name not in (diagnostics.get("uw_locked_perks_excluded") or {})
    )
    return {
        "artifact": "perk_timeline_preview",
        "schema_version": 1,
        "owner": "app.pipeline.build_perk_timeline_preview",
        "generator_owner": "simulators.perk_timeline_generator",
        "policy_source": "manual_inputs.yaml:perk_policy.policy_presets + streamlit_session_override",
        "available_policy_presets": sorted(_perk_policy_presets(base_policy)),
        "policy_preset": str(policy.get('_selected_policy_preset') or ''),
        "resolved_policy": dict(policy_payload),
        "policy_override": dict(perk_policy_override or {}),
        "validation": validation,
        "timeline": tuple(dict(row or {}) for row in timeline),
        "diagnostics": dict(diagnostics),
        "eligible_perks": eligible_perks,
        "all_perks": sorted(perk.perk_name for perk in definitions),
        "context": dict(context),
    }


def save_perk_policy_override(
    request: PipelineRunRequest,
    *,
    perk_policy_override: dict[str, object],
) -> dict[str, object]:
    bundle = load_inputs(ids_path=request.ids, manual_inputs_path=request.manual_inputs)
    selected_policy_preset = _normalize_perk_policy_preset_name(getattr(request, 'perk_policy_preset', None))
    base_policy = getattr(bundle, "perk_policy", {}) or {}
    policy = _merged_perk_policy(_select_perk_policy(base_policy, selected_policy_preset), perk_policy_override)
    policy_payload, context = _perk_policy_context(bundle.ids_raw, policy)
    validation = _perk_policy_validation_ledger(policy_payload, context)
    if not validation["ok"]:
        raise ValueError(f"Perk policy is invalid: {validation['errors']!r}")
    saved_policy = write_perk_policy(
        _store_selected_perk_policy(base_policy, policy, selected_policy_preset or str(policy.get('_selected_policy_preset') or '')),
        manual_inputs_path=request.manual_inputs,
    )
    return {
        "artifact": "perk_policy_save_result",
        "schema_version": 1,
        "owner": "app.pipeline.save_perk_policy_override",
        "input_owner": "input.loader.write_perk_policy",
        "manual_inputs_path": str(request.manual_inputs or MANUAL_INPUTS_PATH),
        "policy_preset": str(policy.get('_selected_policy_preset') or selected_policy_preset or ''),
        "saved_policy": dict(saved_policy),
        "resolved_policy": dict(policy_payload),
        "validation": validation,
    }


def _perk_policy_context(ids_raw, perk_policy: dict) -> tuple[dict, dict]:
    policy = perk_policy or {}
    if 'policy_presets' in policy and not policy.get('_selected_policy_preset'):
        policy = _select_perk_policy(policy, None)
    lab_rows = ids_raw.raw_sections.get('Labs', []) if ids_raw else []
    labs = {}
    for row in lab_rows:
        if row and str(row[0]).strip():
            try:
                labs[str(row[0]).strip()] = int(float(str(row[1]).strip().replace(',', '')))
            except Exception:
                pass

    standard_perk_bonus_level = labs.get('Standard Perks Bonus', 0)
    tradeoff_bonus_level = labs.get('Improve Trade-off Perks', 0)
    target_wave = int(policy.get('target_wave', 50000) or 50000)
    first_perk_choice_level = _ids_player_value(ids_raw, 'First Perk Choice', 0)
    ban_perks_capacity_ids = _ids_player_value(ids_raw, 'Ban Perks', 0)
    unlocked_ultimate_weapons = _ids_unlocked_ultimate_weapons(ids_raw)
    generated_policy_context: dict[str, object] = {}
    selected_policy_preset = str(policy.get('_selected_policy_preset') or '')
    policy_strategy = str(policy.get('strategy') or '').strip().lower()
    if (
        selected_policy_preset in BOSS_WAVE_PERK_POLICY_PRESETS
        and policy_strategy != 'manual_explicit_v1'
        and not bool(policy.get('_policy_override_active'))
    ):
        policy, generated_policy_context = _generated_goal_perk_policy(
            policy=policy,
            preset_name=selected_policy_preset,
            labs=labs,
            ban_capacity=ban_perks_capacity_ids,
            unlocked_ultimate_weapons=unlocked_ultimate_weapons,
        )
    banned_names = _resolve_manual_banned_perks(policy)
    configured_priority = list(policy.get('priority_order', []) or [])
    configured_first_perk_choice = policy.get('first_perk_choice')
    if first_perk_choice_level > 0 and 'first_perk_choice' in policy and not configured_first_perk_choice:
        raise ValueError(
            "First Perk Choice lab is unlocked, but manual_inputs.yaml:perk_policy.first_perk_choice is not configured."
        )
    payload = {
        'seed': int(policy.get('seed', 42) or 42),
        'target_wave': target_wave,
        'waves_required_lab': int(labs.get('Waves Required', 0) or 0),
        'standard_perk_bonus': float(standard_perk_bonus_level) / 100.0,
        'perk_option_quantity': _ids_player_value(ids_raw, 'Perk Option Quantity', 0),
        'ban_perks_capacity': max(ban_perks_capacity_ids, int(policy.get('_base_banned_perks_count', len(banned_names)) or 0)),
        'banned_perks': banned_names,
        'priority_order': configured_priority,
        'first_perk_choice': configured_first_perk_choice,
        'unlocked_ultimate_weapons': unlocked_ultimate_weapons,
    }
    context = {
        'selected_policy_preset': str(policy.get('_selected_policy_preset') or ''),
        'policy_strategy': str(policy.get('strategy') or ''),
        'policy_source_note': str(policy.get('source_note') or ''),
        'banned_names': banned_names,
        'standard_perk_bonus_level': standard_perk_bonus_level,
        'tradeoff_bonus_level': tradeoff_bonus_level,
        'first_perk_choice_level': first_perk_choice_level,
        'configured_first_perk_choice': configured_first_perk_choice,
        'configured_priority_order': configured_priority,
        'ban_perks_capacity_ids': ban_perks_capacity_ids,
        'banned_perk_aliases': list(policy.get('banned_perk_aliases', []) or []),
        'unlocked_ultimate_weapons': unlocked_ultimate_weapons,
        'policy_generated_from_goal_matrix': bool(generated_policy_context),
        'generated_policy_context': dict(generated_policy_context),
    }
    return payload, context


def _build_max_progression_policy_perk_config(ids_raw, perk_policy: dict) -> tuple[dict, dict]:
    from qe.stat_input_compiler import load_perk_entity_rows
    from qe.perk_tables import load_perk_definitions

    metadata = {
        'requested_perks_path': 'manual_inputs.yaml:perk_policy',
        'resolved_perks_path': 'manual_inputs.yaml:perk_policy',
        'fallback_applied': False,
        'fallback_reason': None,
    }
    policy_payload, context = _perk_policy_context(ids_raw, perk_policy)
    entities = load_perk_entity_rows()
    perk_definitions = {perk.perk_name: perk for perk in load_perk_definitions()}
    unlocked_uw = {name.strip().lower() for name in context['unlocked_ultimate_weapons']}
    banned_names = set(context['banned_names'])
    locked_uw_exclusions = {}
    selections = []
    for row in entities:
        perk_id = row.get('perk_id')
        perk_name = row.get('perk_name')
        if not perk_id or not perk_name or perk_name in banned_names:
            continue
        perk_definition = perk_definitions.get(perk_name)
        if (
            perk_definition is not None
            and perk_definition.category == 'ultimate_weapon'
            and str(perk_definition.required_uw or '').strip().lower() not in unlocked_uw
        ):
            locked_uw_exclusions[perk_name] = perk_definition.required_uw
            continue
        try:
            picks = int(row.get('max_picks') or 1)
        except Exception:
            picks = 1
        selections.append({'perk_id': perk_id, 'picks': max(1, picks)})

    generated = {
        'preset_namespace_class': 'transient',
        'perk_presets': {'ProjectedMaxPolicy_AllExceptManualBans': selections},
        'active_perk_preset': 'ProjectedMaxPolicy_AllExceptManualBans',
        'notes': 'Deterministic max-progression forecasting assumption: all perks except manual bans from the input-owned perk policy.',
        'generator': {
            'perk_mode': 'max_progression_policy',
            'perk_policy_preset': context['selected_policy_preset'],
            'manual_banned_perks': sorted(banned_names),
            'manual_banned_perk_aliases': context['banned_perk_aliases'],
            'selection_rule': 'all_perks_except_manual_bans_using_registry_max_picks',
            'target_wave': policy_payload['target_wave'],
            'unlocked_ultimate_weapons': context['unlocked_ultimate_weapons'],
            'uw_locked_perks_excluded': dict(sorted(locked_uw_exclusions.items())),
        },
    }
    metadata.update(
        {
            'resolved_perks_path': 'manual_inputs.yaml:perk_policy',
            'perk_mode': 'max_progression_policy',
            'manual_banned_perk_count': len(banned_names),
            'unlocked_ultimate_weapons': context['unlocked_ultimate_weapons'],
            'uw_locked_perks_excluded': dict(sorted(locked_uw_exclusions.items())),
        }
    )
    return generated, metadata


def _build_runtime_timeline_perk_config(ids_raw, perk_policy: dict, *, diag_output_dir: Path | None = None) -> tuple[dict, dict]:
    from qe.stat_input_compiler import load_perk_entity_rows
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy, perk_state_at_wave

    policy_payload, context = _perk_policy_context(ids_raw, perk_policy)
    policy = PerkTimelinePolicy(**policy_payload)
    timeline, diag = generate_timeline_from_policy(policy)
    taken_counts = perk_state_at_wave(timeline, policy.target_wave)
    entities = load_perk_entity_rows()
    by_name = {row.get('perk_name'): row for row in entities if row.get('perk_name')}
    selections = []
    unknown_names = []
    for perk_name, picks in sorted(taken_counts.items()):
        meta = by_name.get(perk_name)
        if not meta or not meta.get('perk_id'):
            unknown_names.append(perk_name)
            continue
        selections.append({'perk_id': meta['perk_id'], 'picks': int(picks)})

    generated = {
        'preset_namespace_class': 'transient',
        'perk_presets': {'ProjectedRuntimeTimeline': selections},
        'active_perk_preset': 'ProjectedRuntimeTimeline',
        'notes': 'Simulator-owned runtime perk timeline projected to target_wave from the input-owned perk policy.',
        'generator': {
            'perk_mode': 'runtime_timeline',
            'perk_policy_preset': context['selected_policy_preset'],
            'target_wave': policy.target_wave,
            'manual_banned_perks': context['banned_names'],
            'manual_banned_perk_aliases': context['banned_perk_aliases'],
            'unknown_generated_perk_names': unknown_names,
            'priority_order': policy.priority_order or [],
            'first_perk_choice': policy.first_perk_choice,
            'waves_required_lab': policy.waves_required_lab,
            'standard_perk_bonus_level': context['standard_perk_bonus_level'],
            'perk_option_quantity': policy.perk_option_quantity,
            'ban_perks_capacity_ids': context['ban_perks_capacity_ids'],
            'ban_perks_capacity_effective': policy.ban_perks_capacity,
            'unlocked_ultimate_weapons': policy.unlocked_ultimate_weapons or [],
            'uw_locked_perks_excluded': diag.get('uw_locked_perks_excluded', {}),
        },
    }
    if diag_output_dir is not None:
        diag_output_dir.mkdir(parents=True, exist_ok=True)
        (diag_output_dir / 'perk_generation_diagnostics.json').write_text(
            json.dumps(_contract_json_payload(diag), indent=2),
            encoding='utf-8',
        )

    metadata = {
        'requested_perks_path': 'manual_inputs.yaml:perk_policy',
        'resolved_perks_path': 'simulator::runtime_timeline',
        'fallback_applied': False,
        'fallback_reason': None,
        'perk_mode': 'runtime_timeline',
        'perk_policy_preset': context['selected_policy_preset'],
        'target_wave': policy.target_wave,
    }
    if diag_output_dir is not None:
        metadata['generated_diagnostics_path'] = str(diag_output_dir / 'perk_generation_diagnostics.json')
    return generated, metadata


def _resolve_perk_config(
    *,
    perk_mode: str,
    primary_config: dict,
    perk_policy: dict,
    ids_raw,
    diag_output_dir: Path | None = None,
) -> tuple[dict, dict]:
    mode = _normalize_perk_mode(perk_mode)
    primary = primary_config if isinstance(primary_config, dict) else {}
    if mode == 'none':
        return {
            'perk_presets': {},
            'active_perk_preset': None,
        }, {
            'requested_perks_path': 'manual_inputs.yaml:perk_config',
            'resolved_perks_path': 'none',
            'fallback_applied': False,
            'fallback_reason': None,
            'perk_mode': 'none',
        }
    if mode == 'max_progression_policy':
        return _build_max_progression_policy_perk_config(ids_raw, perk_policy)
    if _perk_config_has_active_preset(primary):
        return primary, {
            'requested_perks_path': 'manual_inputs.yaml:perk_config',
            'resolved_perks_path': 'manual_inputs.yaml:perk_config',
            'fallback_applied': False,
            'fallback_reason': None,
            'perk_mode': 'runtime_timeline',
            'runtime_policy_source': 'existing_active_perk_config',
        }
    return _build_runtime_timeline_perk_config(ids_raw, perk_policy, diag_output_dir=diag_output_dir)


def _build_account_state(
    *,
    ids_path: Path,
    manual_inputs_path: Path | None,
    runtime_state_overlay: str | None = None,
    preset: str,
    perk_mode: str,
    perk_policy_preset: str | None = None,
    diag_output_dir: Path | None = None,
):
    input_bundle = load_inputs(ids_path=ids_path, manual_inputs_path=manual_inputs_path)
    selected_policy = _select_perk_policy(input_bundle.perk_policy, perk_policy_preset)
    perk_config, perk_config_resolution = _resolve_perk_config(
        perk_mode=perk_mode,
        primary_config=input_bundle.perk_config,
        perk_policy=selected_policy,
        ids_raw=input_bundle.ids_raw,
        diag_output_dir=diag_output_dir,
    )
    if selected_policy.get('_selected_policy_preset'):
        perk_config_resolution['perk_policy_preset'] = str(selected_policy['_selected_policy_preset'])
    state_kwargs = {
        'default_preset': preset,
        'loadout_config': input_bundle.loadout_config,
        'perk_config': perk_config,
        'manual_inputs': input_bundle.manual_inputs,
    }
    if runtime_state_overlay:
        state_kwargs['runtime_state_overlay'] = runtime_state_overlay
    account_state = build_runtime_state(input_bundle.ids_raw, **state_kwargs)
    return input_bundle, account_state, perk_config_resolution


def _effective_manual_inputs_path(path: Path | None) -> Path:
    return path if path is not None else ROOT / 'input' / 'manual_inputs.yaml'


def _path_cache_token(path: Path) -> tuple[str, int | None, int | None]:
    resolved = path.resolve()
    try:
        stat = resolved.stat()
        return (str(resolved), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return (str(resolved), None, None)


class RunStatsSession:
    """Warm in-process session for repeated bounded run_stats queries."""

    def __init__(self) -> None:
        self.qe_shared_runtime_context = get_default_qe_shared_runtime_context()
        self.query_kernel = self.qe_shared_runtime_context.query_kernel
        self._account_state_cache: dict[tuple, tuple] = {}
        self._stat_inputs_cache: dict[tuple, tuple] = {}

    def _account_state_cache_key(
        self,
        *,
        ids_path: Path,
        manual_inputs_path: Path | None,
        runtime_state_overlay: str | None = None,
        perk_mode: str,
        perk_policy_preset: str | None,
    ) -> tuple:
        return (
            _path_cache_token(ids_path),
            _path_cache_token(_effective_manual_inputs_path(manual_inputs_path)),
            str(runtime_state_overlay or ''),
            str(perk_mode),
            str(_normalize_perk_policy_preset_name(perk_policy_preset) or ''),
        )

    def get_account_state_bundle(
        self,
        *,
        ids_path: Path,
        manual_inputs_path: Path | None,
        runtime_state_overlay: str | None = None,
        perk_mode: str,
        perk_policy_preset: str | None,
        diag_output_dir: Path | None,
    ):
        cache_key = self._account_state_cache_key(
            ids_path=ids_path,
            manual_inputs_path=manual_inputs_path,
            runtime_state_overlay=runtime_state_overlay,
            perk_mode=perk_mode,
            perk_policy_preset=perk_policy_preset,
        )
        cached = self._account_state_cache.get(cache_key)
        if cached is not None:
            return (*cached, True)
        input_bundle, account_state, perk_config_resolution = _build_account_state(
            ids_path=ids_path,
            manual_inputs_path=manual_inputs_path,
            runtime_state_overlay=runtime_state_overlay,
            preset='Farming',
            perk_mode=perk_mode,
            perk_policy_preset=perk_policy_preset,
            diag_output_dir=diag_output_dir,
        )
        cached_value = (input_bundle, account_state, perk_config_resolution)
        self._account_state_cache[cache_key] = cached_value
        return (*cached_value, False)

    def _stat_inputs_cache_key(
        self,
        *,
        account_state,
        preset_name: str,
        state_mode: str,
        perk_preset_name: str | None,
        perks_enabled: bool,
        scenario_context: Mapping[str, object],
    ) -> tuple:
        return (
            id(account_state),
            str(preset_name),
            str(state_mode),
            str(perk_preset_name or ''),
            bool(perks_enabled),
            _boss_wave_cacheable_mapping_items(scenario_context),
            id(compile_stat_inputs),
        )

    def _compile_stat_inputs_cached(
        self,
        *,
        account_state,
        preset_name: str,
        state_mode: str,
        perk_preset_name: str | None,
        perks_enabled: bool,
        scenario_context: Mapping[str, object],
    ) -> tuple:
        cache_key = self._stat_inputs_cache_key(
            account_state=account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
            scenario_context=scenario_context,
        )
        cached = self._stat_inputs_cache.get(cache_key)
        if cached is not None:
            return cached
        compiled = tuple(compile_stat_inputs(
            account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
            scenario_context=scenario_context,
        ))
        self._stat_inputs_cache[cache_key] = compiled
        return compiled

    def build_run_stats_artifacts(self, args):
        args.perk_state = _normalize_perk_state(args.perk_state)
        args.perk_mode = _normalize_perk_mode(getattr(args, 'perk_mode', None))
        args.perk_policy_preset = _normalize_perk_policy_preset_name(getattr(args, 'perk_policy_preset', None))
        args.dissonance_run_category = _normalize_boss_wave_dissonance_run_category(
            getattr(args, 'dissonance_run_category', None) or 'none'
        )

        build_start = perf_counter()
        input_bundle, account_state, perk_config_resolution, account_state_cache_hit = self.get_account_state_bundle(
            ids_path=args.ids,
            manual_inputs_path=getattr(args, 'manual_inputs', None),
            runtime_state_overlay=getattr(args, 'runtime_state_overlay', None),
            perk_mode=args.perk_mode,
            perk_policy_preset=args.perk_policy_preset,
            diag_output_dir=args.out / 'diagnostics' / 'perks',
        )
        account_state_build_ms = _elapsed_ms(build_start)
        requested_perk_policy_preset = args.perk_policy_preset
        resolved_perk_policy_preset = (
            str(perk_config_resolution.get('perk_policy_preset') or requested_perk_policy_preset or '').strip() or None
        )

        preset_names = ['Farming', 'Tourney']
        run_stats_payload = {'presets': {}, 'diagnostics': {}}
        preset_diagnostics = {}
        start_books_by_preset = {}
        max_books_by_preset = {}
        state_query_plans = {'start_of_run': {}, 'max_progression': {}}
        pipeline_timings = {'presets': {}}
        perk_application_by_preset = {}
        primary_stats_stat_inputs_payload = None
        primary_stats_stat_inputs = None

        for preset_name in preset_names:
            preset_state_timings: dict[str, dict] = {}
            start_perk_preset_name, start_perks_enabled = _run_stats_perk_state(
                account_state,
                preset_name=preset_name,
                perk_state=args.perk_state,
                perk_mode=args.perk_mode,
                state_mode='start_of_run',
            )
            max_perk_preset_name, max_perks_enabled = _run_stats_perk_state(
                account_state,
                preset_name=preset_name,
                perk_state=args.perk_state,
                perk_mode=args.perk_mode,
                state_mode='max_progression',
            )
            perk_application_by_preset[preset_name] = {
                'start_of_run': {
                    'perk_preset_name': start_perk_preset_name,
                    'perks_enabled': start_perks_enabled,
                },
                'max_progression': {
                    'perk_preset_name': max_perk_preset_name,
                    'perks_enabled': max_perks_enabled,
                },
            }

            for state_mode, perk_preset_name, perks_enabled in (
                ('start_of_run', start_perk_preset_name, start_perks_enabled),
                ('max_progression', max_perk_preset_name, max_perks_enabled),
            ):
                state_start = perf_counter()
                progression_family_id = _run_stats_progression_family_id(state_mode=state_mode, perks_enabled=perks_enabled)
                timing_family_id = _run_stats_timing_family_id(preset_name=preset_name, perks_enabled=perks_enabled)
                scenario_config = _run_stats_scenario_config(
                    account_state,
                    preset_name=preset_name,
                    tier_number=getattr(args, 'tier', None),
                )
                scenario_context = _run_stats_scenario_context(
                    scenario_config,
                    dissonance_run_category=args.dissonance_run_category,
                )
                base_stat_inputs = self._compile_stat_inputs_cached(
                    account_state=account_state,
                    preset_name=preset_name,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    perks_enabled=perks_enabled,
                    scenario_context=scenario_context,
                )
                if preset_name == 'Farming' and state_mode == 'start_of_run':
                    primary_stats_stat_inputs = base_stat_inputs
                    primary_stats_stat_inputs_payload = [row.to_dict() for row in base_stat_inputs]
                progression_bound = BoundStatInputs(
                    binding=bind_state_identity(
                        account_state,
                        preset_name=preset_name,
                        state_mode=state_mode,
                        perk_preset_name=perk_preset_name,
                        perks_enabled=perks_enabled,
                        scenario_context=scenario_context,
                    ),
                    stat_inputs=base_stat_inputs,
                )
                timing_bound = BoundStatInputs(
                    binding=bind_state_identity(
                        account_state,
                        state_mode=state_mode,
                        preset_name=preset_name,
                        perk_preset_name=perk_preset_name,
                        perks_enabled=perks_enabled,
                        scenario_context={
                            'mode_id': scenario_config.mode_id,
                            'tier': scenario_config.tier,
                            'league': scenario_config.league,
                            'tournament_wave': scenario_config.tournament_wave,
                            **(
                                {'dissonance_run_category': args.dissonance_run_category}
                                if args.dissonance_run_category != 'none'
                                else {}
                            ),
                        },
                    ),
                    stat_inputs=base_stat_inputs,
                )
                compiled_timing_family_rows = compile_timing_family_rows(
                    account_state=account_state,
                    family_id=timing_family_id,
                    preset_name=preset_name,
                    scenario_config=scenario_config,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    bound_stat_inputs=timing_bound,
                )

                t = perf_counter()
                progression_response = resolve_run_stats_progression_bundle(
                    account_state=account_state,
                    family_id=progression_family_id,
                    preset_name=preset_name,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    bound_stat_inputs=progression_bound,
                    copy_result=False,
                )
                progression_ms = _elapsed_ms(t)

                t = perf_counter()
                timing_core_response = resolve_timing_consumer_bundle(
                    account_state=account_state,
                    consumer_id='run_stats',
                    bundle_id='timing_core_cycle',
                    family_id=timing_family_id,
                    preset_name=preset_name,
                    scenario_config=scenario_config,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    include_optional_surface_ids=('support_surface::timing.gcomp_cooldown_reduction_seconds',),
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    compiled_family_rows=compiled_timing_family_rows,
                    copy_result=False,
                )
                timing_core_ms = _elapsed_ms(t)

                t = perf_counter()
                timing_wave_response = resolve_timing_consumer_bundle(
                    account_state=account_state,
                    consumer_id='run_stats',
                    bundle_id='timing_wave_duration',
                    family_id=timing_family_id,
                    preset_name=preset_name,
                    scenario_config=scenario_config,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    include_optional_surface_ids=(
                        'state::cards.wave_accelerator.wave_cooldown_reduction_pct',
                        'state::cards.wave_accelerator.spawn_rate_acceleration',
                        'state::cards.wave_skip.chance_pct',
                        'state::cards.wave_skip.mastery_effect',
                        'state::tower.package_chance_pct',
                    ),
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    compiled_family_rows=compiled_timing_family_rows,
                    copy_result=False,
                )
                timing_wave_ms = _elapsed_ms(t)
                timing_econ_statbook_dict: dict[str, object] = {}
                if scenario_config.mode_id == 'farming':
                    timing_econ_statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
                        identity=timing_bound.binding.identity,
                        stat_inputs=compiled_timing_family_rows[1],
                        family_id=timing_family_id,
                        requested_surface_ids=(
                            'state::cards.intro_sprint.waves',
                            'state::meta.game_speed_multiplier',
                            'state::perk.max_game_speed',
                        ),
                        notes='farming_econ_timing_readiness_supplemental_surfaces',
                        diagnostics={
                            'source': 'app.pipeline.run_stats_farming_econ_readiness',
                        },
                    )
                    timing_econ_statbook_dict = timing_econ_statbook.to_dict()

                t = perf_counter()
                merged_statbook_dict = _merge_query_statbooks(
                    _query_response_to_statbook_dict(
                        progression_response,
                        bundle_id='progression_core_stats',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                        publish_qe_surfaces=True,
                        annotate_display=False,
                    ),
                    _query_response_to_statbook_dict(
                        timing_core_response,
                        bundle_id='timing_core_cycle',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                        annotate_display=False,
                    ),
                    _query_response_to_statbook_dict(
                        timing_wave_response,
                        bundle_id='timing_wave_duration',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                        annotate_display=False,
                    ),
                    timing_econ_statbook_dict,
                )
                merged_statbook_dict = _publish_query_surfaces_on_statbook_dict(
                    merged_statbook_dict,
                    manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                    account_state_labs=account_state.labs,
                )
                rows_payload = dict(merged_statbook_dict.get('rows') or {})
                wave_duration_row = dict(
                    rows_payload.get('support_surface::timing.wave_duration_seconds_effective') or {}
                )
                try:
                    effective_wave_duration_seconds = float(
                        wave_duration_row.get('final_value')
                    )
                except (TypeError, ValueError):
                    effective_wave_duration_seconds = None
                if effective_wave_duration_seconds is not None:
                    from simulators.scenario import farming_throughput_support_row_payloads

                    rows_payload.update(
                        farming_throughput_support_row_payloads(
                            account_state=account_state,
                            config=scenario_config,
                            stat_inputs=base_stat_inputs,
                            effective_wave_duration_seconds=effective_wave_duration_seconds,
                            farming_hours_per_day=_manual_input_numeric_value(
                                input_bundle.manual_advisory_inputs,
                                'module.farming.hours_per_day',
                                default=23.5,
                            ) or 23.5,
                        )
                    )
                    merged_statbook_dict['rows'] = rows_payload
                formatting_ms = _elapsed_ms(t)

                if state_mode == 'start_of_run':
                    start_statbook_dict = merged_statbook_dict
                else:
                    max_statbook_dict = merged_statbook_dict

                state_query_plans[state_mode][preset_name] = {
                    'progression': {
                        'bundle_id': 'progression_core_stats',
                        'family_id': progression_family_id,
                        'resolved_surface_ids': [row.surface_id for row in progression_response.resolved_surface_rows],
                    },
                    'timing': [
                        {
                            'bundle_id': 'timing_core_cycle',
                            'family_id': timing_family_id,
                            'resolved_surface_ids': [row.surface_id for row in timing_core_response.resolved_surface_rows],
                        },
                        {
                            'bundle_id': 'timing_wave_duration',
                            'family_id': timing_family_id,
                            'resolved_surface_ids': [row.surface_id for row in timing_wave_response.resolved_surface_rows],
                        },
                    ],
                }
                preset_state_timings[state_mode] = {
                    'resolve_progression_ms': progression_ms,
                    'resolve_timing_core_ms': timing_core_ms,
                    'resolve_timing_wave_ms': timing_wave_ms,
                    'publication_ms': 0.0,
                    'formatting_ms': formatting_ms,
                    'total_state_ms': _elapsed_ms(state_start),
                }

            dual_state_stats = _build_dual_state_stats_view(start_statbook_dict, max_statbook_dict)
            run_stats_payload['presets'][preset_name] = {
                'loadout': {
                    'start_of_run': _preset_loadout_summary(
                        account_state,
                        preset_name=preset_name,
                        perk_preset_name=start_perk_preset_name,
                    ),
                    'max_progression': _preset_loadout_summary(
                        account_state,
                        preset_name=preset_name,
                        perk_preset_name=max_perk_preset_name,
                    ),
                },
                'stats': dual_state_stats,
            }
            preset_diagnostics[preset_name] = {
                'start_of_run': {
                    'query_backend': 'bounded_qe_bundle',
                    'perk_preset_name': start_perk_preset_name,
                    'perks_enabled': start_perks_enabled,
                    'statbook_row_count': len(start_statbook_dict.get('rows', {})),
                    'bundle_ids': start_statbook_dict.get('diagnostics', {}).get('bundle_ids', []),
                    'family_ids': start_statbook_dict.get('diagnostics', {}).get('family_ids', []),
                    'resolved_surface_count': start_statbook_dict.get('diagnostics', {}).get('resolved_surface_count'),
                    'contributor_row_count': start_statbook_dict.get('diagnostics', {}).get('contributor_row_count'),
                    'timings_ms': preset_state_timings['start_of_run'],
                },
                'max_progression': {
                    'query_backend': 'bounded_qe_bundle',
                    'perk_preset_name': max_perk_preset_name,
                    'perks_enabled': max_perks_enabled,
                    'statbook_row_count': len(max_statbook_dict.get('rows', {})),
                    'bundle_ids': max_statbook_dict.get('diagnostics', {}).get('bundle_ids', []),
                    'family_ids': max_statbook_dict.get('diagnostics', {}).get('family_ids', []),
                    'resolved_surface_count': max_statbook_dict.get('diagnostics', {}).get('resolved_surface_count'),
                    'contributor_row_count': max_statbook_dict.get('diagnostics', {}).get('contributor_row_count'),
                    'timings_ms': preset_state_timings['max_progression'],
                },
                'dual_state_stats': dual_state_stats.get('diagnostics', {}),
            }
            start_books_by_preset[preset_name] = start_statbook_dict
            max_books_by_preset[preset_name] = max_statbook_dict
            pipeline_timings['presets'][preset_name] = preset_state_timings

        any_perks_materialized = any(
            bool(state_payload.get('perks_enabled'))
            for preset_payload in perk_application_by_preset.values()
            for state_payload in preset_payload.values()
        )
        diagnostics = {
            'pipeline_kind': 'stats',
            'query_backend': 'bounded_qe_bundle',
            'preset_names': preset_names,
            'state_modes': ['start_of_run', 'max_progression'],
            'perk_state': args.perk_state,
            'perk_mode': args.perk_mode,
            'dissonance_run_category': args.dissonance_run_category,
            'requested_perk_policy_preset': requested_perk_policy_preset,
            'perk_policy_preset': resolved_perk_policy_preset,
            'perk_config_resolution': perk_config_resolution,
            'runtime_state_overlay': getattr(args, 'runtime_state_overlay', None),
            'perk_support': {
                'perk_policy_source': 'manual_inputs.yaml:perk_policy.policy_presets',
                'available_policy_presets': list(BOSS_WAVE_PERK_POLICY_PRESETS),
                'perk_state': args.perk_state,
                'perk_mode': args.perk_mode,
                'requested_perk_policy_preset': requested_perk_policy_preset,
                'perk_policy_preset': resolved_perk_policy_preset,
                'perk_materialization': any_perks_materialized,
                'perk_materialization_scope': 'any_preset_state',
                'perk_application_by_preset': perk_application_by_preset,
            },
            'qe_shared_runtime_context': self.qe_shared_runtime_context.to_dict(),
            'session': {
                'kind': 'run_stats_session',
                'account_state_cache_hit': account_state_cache_hit,
                'account_state_build_ms': account_state_build_ms,
            },
            'presets': preset_diagnostics,
            'query_plans': state_query_plans,
            'timings_ms': pipeline_timings,
        }
        geometry_artifacts = build_run_stats_geometry_artifacts(
            start_books_by_preset=start_books_by_preset,
            max_books_by_preset=max_books_by_preset,
        )
        diagnostics['geometry_engine'] = geometry_artifacts['diagnostics']
        farming_max_rows = dict(
            ((max_books_by_preset.get('Farming') or {}).get('rows') or {})
        )
        run_tracker_evidence: dict[str, object] | None = None
        run_tracker_csv = getattr(args, 'run_tracker_csv', None)
        if run_tracker_csv is not None:
            run_tracker_evidence = summarize_run_tracker_csv(run_tracker_csv)
            diagnostics['run_tracker_calibration_evidence'] = run_tracker_evidence
        diagnostics['farming_econ_model_readiness'] = (
            farming_econ_timing_readiness_summary(
                farming_max_rows,
                run_tracker_evidence=run_tracker_evidence,
                approve_tracker_empirical_cph_default=bool(
                    getattr(args, 'approve_tracker_empirical_farming_cph', False)
                ),
                approve_tracker_empirical_run_coin_duration_integrals=bool(
                    getattr(
                        args,
                        'approve_tracker_empirical_run_coin_duration_integrals',
                        False,
                    )
                ),
                approve_tracker_current_export_account_state_validation=bool(
                    getattr(
                        args,
                        'approve_tracker_current_export_account_state_validation',
                        False,
                    )
                ),
                approve_tracker_empirical_run_duration_projection=bool(
                    getattr(
                        args,
                        'approve_tracker_empirical_run_duration_projection',
                        False,
                    )
                ),
                approve_tracker_empirical_wave_skip_reward=bool(
                    getattr(args, 'approve_tracker_empirical_wave_skip_reward', False)
                ),
                approve_tracker_wave_skip_intro_semantics=bool(
                    getattr(args, 'approve_tracker_wave_skip_intro_semantics', False)
                ),
                approve_source_intro_sprint_coin_window=bool(
                    getattr(args, 'approve_source_intro_sprint_coin_window', False)
                ),
                approve_tracker_empirical_econ_window_overlap=bool(
                    getattr(args, 'approve_tracker_empirical_econ_window_overlap', False)
                ),
                approve_tracker_empirical_kill_density_transform=bool(
                    getattr(args, 'approve_tracker_empirical_kill_density_transform', False)
                ),
            )
        )
        run_stats_payload['diagnostics'] = diagnostics
        return {
            'run_stats_payload': run_stats_payload,
            'diagnostics': diagnostics,
            'account_state': account_state,
            'primary_stats_stat_inputs': primary_stats_stat_inputs or [],
            'stat_inputs': primary_stats_stat_inputs_payload or [],
            'start_books_by_preset': start_books_by_preset,
            'max_books_by_preset': max_books_by_preset,
            'state_query_plans': state_query_plans,
            'geometry_artifacts': geometry_artifacts,
        }

    def execute(self, args) -> int:
        args.out.mkdir(parents=True, exist_ok=True)
        _remove_run_stats_current_outputs(args.out)
        _remove_run_stats_legacy_outputs(args.out)
        artifacts = self.build_run_stats_artifacts(args)
        diagnostics = artifacts['diagnostics']
        contract_payload = _current_contract_json_payload
        sanitized_account_state = _sanitized_account_state_for_output(artifacts['account_state'], 'Farming')
        module_card_payloads = build_module_card_payloads(artifacts['account_state'])
        write_outputs_ms = 0.0
        write_segment_start = perf_counter()
        (args.out / 'account_state.json').write_text(
            json.dumps(contract_payload(sanitized_account_state), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / 'module_card_payloads.json').write_text(
            json.dumps(contract_payload(module_card_payloads), indent=2, default=str),
            encoding='utf-8',
        )
        input_dashboard_payload = _build_input_dashboard_payload(
            sanitized_account_state,
            diagnostics,
            qe_dashboard_publications={},
            module_card_payloads=module_card_payloads,
        )
        (args.out / 'input_dashboard.json').write_text(
            json.dumps(contract_payload(input_dashboard_payload), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_plan']).write_text(
            json.dumps(contract_payload({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'start_of_run',
                'presets': artifacts['state_query_plans']['start_of_run'],
            }), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_plan']).write_text(
            json.dumps(contract_payload({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'max_progression',
                'presets': artifacts['state_query_plans']['max_progression'],
            }), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_rows']).write_text(
            json.dumps(contract_payload(artifacts['start_books_by_preset']), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']).write_text(
            json.dumps(contract_payload(artifacts['max_books_by_preset']), indent=2, default=str),
            encoding='utf-8',
        )
        stats_dashboard_payload = _build_stats_dashboard_payload(
            account_state_payload=sanitized_account_state,
            diagnostics=diagnostics,
            input_dashboard_payload=input_dashboard_payload,
            module_card_payloads=module_card_payloads,
            query_rows_start_of_run=artifacts['start_books_by_preset'],
            query_rows_max_progression=artifacts['max_books_by_preset'],
            qe_dashboard_publications=artifacts.get('qe_dashboard_publications'),
            stat_inputs_payload=artifacts.get('stat_inputs'),
            ep_compare_publishable={},
            line_verification={},
            selected_preset='Farming',
            selected_state_mode='start_of_run',
        )
        (args.out / 'stats_dashboard.json').write_text(
            json.dumps(contract_payload(stats_dashboard_payload), indent=2, default=str),
            encoding='utf-8',
        )
        geometry_artifacts = artifacts['geometry_artifacts']
        (args.out / 'geometry_engine_payload.json').write_text(
            json.dumps(contract_payload(geometry_artifacts['geometry_engine_payload']), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / 'geometry_range_report.json').write_text(
            json.dumps(contract_payload(geometry_artifacts['geometry_range_report']), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / 'geometry_range_report.csv').write_text(
            str(geometry_artifacts['geometry_range_report_csv']),
            encoding='utf-8',
        )
        (args.out / 'geometry_consumer_interfaces.json').write_text(
            json.dumps(contract_payload(geometry_artifacts['geometry_consumer_interfaces']), indent=2, default=str),
            encoding='utf-8',
        )
        (args.out / 'geometry_proxy_governance.json').write_text(
            json.dumps(contract_payload(geometry_artifacts['geometry_proxy_governance']), indent=2, default=str),
            encoding='utf-8',
        )
        optional_committed_artifacts: list[str] = []
        if bool(getattr(args, 'include_boss_wave_milestone_matrix', False)):
            write_outputs_ms += _elapsed_ms(write_segment_start)
            matrix_request = PipelineRunRequest(
                ids=args.ids,
                out=args.out,
                preset='Milestone',
                manual_inputs=args.manual_inputs,
                runtime_state_overlay=getattr(args, 'runtime_state_overlay', None),
                perk_mode='max_progression_policy',
                perk_state='auto',
                dissonance_run_category=args.dissonance_run_category,
                run_tracker_csv=getattr(args, 'run_tracker_csv', None),
            )
            matrix_build_start = perf_counter()
            boss_wave_milestone_matrix = build_boss_wave_milestone_matrix(
                matrix_request,
                tiers=_boss_wave_matrix_tiers_from_args(args),
                scenario_runtime_inputs=_boss_wave_matrix_runtime_inputs_from_args(args),
                comparison_scenario_runtime_inputs=_boss_wave_matrix_comparison_inputs_from_args(args),
                comparison_label=_boss_wave_matrix_comparison_label_from_args(args),
                dissonance_run_categories=_boss_wave_matrix_dissonance_categories_from_args(args),
                align_clean_reference_rows=bool(getattr(args, 'boss_wave_align_clean_reference_rows', True)),
            )
            diagnostics['timings_ms']['boss_wave_milestone_matrix_build_ms'] = _elapsed_ms(matrix_build_start)
            matrix_write_start = perf_counter()
            (args.out / BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT).write_text(
                json.dumps(contract_payload(boss_wave_milestone_matrix), indent=2, default=str),
                encoding='utf-8',
            )
            matrix_write_ms = _elapsed_ms(matrix_write_start)
            diagnostics['timings_ms']['boss_wave_milestone_matrix_write_ms'] = matrix_write_ms
            write_outputs_ms += matrix_write_ms
            optional_committed_artifacts.append(BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT)
            diagnostics['boss_wave_milestone_matrix'] = _boss_wave_milestone_matrix_diagnostics_payload(
                boss_wave_milestone_matrix
            )
            from evaluators.compare import _build_family_completeness_matrix

            family_completeness_matrix = _build_family_completeness_matrix(
                artifacts['account_state'],
                artifacts.get('primary_stats_stat_inputs') or [],
            )
            diagnostics['current_scope_effect_family_evidence'] = _current_scope_effect_family_evidence_summary(
                family_completeness_matrix,
                boss_wave_milestone_matrix,
                module_card_payloads=module_card_payloads,
                query_rows_start_of_run=artifacts['start_books_by_preset'],
                query_rows_max_progression=artifacts['max_books_by_preset'],
                selected_preset=getattr(args, 'preset', None) or 'Farming',
            )
            diagnostics['current_scope_effect_family_evidence']['caveat'] = (
                'Bounded run_stats diagnostics summary only; route closure was recomputed from the '
                'current bounded stat-input set and Boss Waves consumption evidence remains owned by '
                f'{BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT}. Full EP compare evidence remains owned by '
                'full-pipeline diagnostics.json / ep_oracle_compare.json.'
            )
            diagnostics['tower_goal_readiness'] = _tower_goal_readiness_summary(diagnostics)
            write_segment_start = perf_counter()
        else:
            diagnostics['boss_wave_milestone_matrix'] = {
                'enabled': False,
                'reason': 'optional_matrix_not_requested',
                'artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
            }
        diagnostics['output_contract'] = {
            'contract_kind': 'run_stats_bounded',
            'committed_baseline_artifacts': list(RUN_STATS_COMMITTED_BASELINE_ARTIFACTS),
            'local_support_artifacts': list(RUN_STATS_LOCAL_SUPPORT_ARTIFACTS),
            'optional_committed_artifacts': optional_committed_artifacts,
            'optional_local_artifacts': [],
            'all_local_output_artifacts': [*RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS, *optional_committed_artifacts],
            'product_artifact': 'run_stats.json',
            'query_row_artifacts': [_RUN_STATS_QUERY_OUTPUTS['start_of_run_rows'], _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']],
            'query_plan_artifacts': [_RUN_STATS_QUERY_OUTPUTS['start_of_run_plan'], _RUN_STATS_QUERY_OUTPUTS['max_progression_plan']],
            'removed_legacy_fast_path_artifacts': list(_RUN_STATS_LEGACY_OUTPUTS),
            'ui_payload_artifacts': ['input_dashboard.json', 'module_card_payloads.json', 'stats_dashboard.json'],
        }
        stable_run_stats_payload = _stable_run_stats_payload_for_commit(artifacts['run_stats_payload'])
        (args.out / 'run_stats.json').write_text(
            json.dumps(contract_payload(stable_run_stats_payload), indent=2, default=str),
            encoding='utf-8',
        )
        write_outputs_ms += _elapsed_ms(write_segment_start)
        diagnostics['timings_ms']['write_outputs_ms'] = round(write_outputs_ms, 3)
        (args.out / 'diagnostics.json').write_text(
            json.dumps(_json_sanitize(diagnostics), indent=2, default=str),
            encoding='utf-8',
        )
        return 0


@lru_cache(maxsize=1)
def get_default_run_stats_session() -> RunStatsSession:
    return RunStatsSession()


def run_stats_pipeline(args) -> int:
    """
    Execute the fast stats pipeline.

    Wires: input -> qe -> out.
    Produces side-by-side start_of_run and max_progression composite stat views.
    Runs through the warm in-process run_stats session.
    """
    return get_default_run_stats_session().execute(args)


def _bounded_compare_rows_from_statbooks(books_by_preset: dict[str, dict]) -> dict[str, dict]:
    rows_by_preset: dict[str, dict] = {}
    for preset_name, statbook_payload in (books_by_preset or {}).items():
        rows = {
            str(surface_id): dict(row or {})
            for surface_id, row in dict((statbook_payload or {}).get('rows') or {}).items()
        }
        rows_by_preset[str(preset_name)] = rows
    if 'Tourney' in rows_by_preset:
        rows_by_preset['Tourney__perks_off'] = rows_by_preset['Tourney']
    if 'Farming' in rows_by_preset:
        rows_by_preset['Farming__perks_on'] = rows_by_preset['Farming']
        rows_by_preset['Farming__perks_auto'] = rows_by_preset['Farming']
    return rows_by_preset


def run_analysis_pipeline(args) -> int:
    """
    Execute the full stat pipeline.

    Wires: input -> qe -> evaluators -> out.
    Transitional domain helpers sourced from run_stats module until T7.
    """
    args.state_mode = normalize_state_mode(args.state_mode)
    args.perk_state = _normalize_perk_state(args.perk_state)
    args.perk_mode = _normalize_perk_mode(getattr(args, 'perk_mode', None))
    args.perk_policy_preset = _normalize_perk_policy_preset_name(getattr(args, 'perk_policy_preset', None))
    args.out.mkdir(parents=True, exist_ok=True)

    from evaluators.compare import (
        COMPARE_DESTINATION_RUN_PERK_FACETS,
        COMPARE_PRESET_OVERRIDES,
        _apply_projected_runtime_compare_assumptions,
        _build_artifact_contract_manifest,
        _build_audit_surface_manifest,
        _build_compare_rows_by_preset,
        _build_compare_situation_fit_matrix,
        build_compare_status_summary as _build_compare_status_summary,
        _build_damage_defabs_scope_audit,
        build_ep_compare as _build_ep_compare,
        _build_family_completeness_matrix,
        _build_kb_gap_register,
        _build_kb_incomplete_areas,
        _build_kb_only_health_family_audit,
        build_line_by_line_verification as _build_line_by_line_verification,
        _build_perk_contributor_audit,
        _build_perk_coverage_audit,
        _build_publish_gate_audits,
        _build_publishable_statbook,
        _build_run_perk_residue_analysis,
        build_survivability_residue_analysis as _build_survivability_residue_analysis,
        build_survivor_closure_report as _build_survivor_closure_report,
        _build_tower_damage_residue_analysis,
        _build_tower_damage_runtime_gap_report,
        _build_tower_defense_absolute_semantic_gap_report,
        _build_tower_hp_semantic_gap_report,
        _build_tower_regen_closure_report,
        _build_tower_regen_ep_semantic_gap_report,
        _build_tradeoff_routing_audit,
        _compare_state_key_for_destination,
        _contributor_snapshot,
        _ep_stage_context_for_destination,
        _formula_contract,
        _is_calculator_scope_row,
        load_ep_oracle,
        load_formula_ledger,
        _normalize_compare_values,
        ensure_compare_authoritative_verdict_fields as _ensure_compare_authoritative_verdict_fields,
        ensure_line_verification_authoritative_verdict_fields as _ensure_line_verification_authoritative_verdict_fields,
    )
    from evaluators.compare_core import PreparedCompareRowsBundle
    from qe.query_routing import compiler_routing_indexes
    from input.state_types import PerkSelection
    from dataclasses import replace
    from evaluators.scorer import MissingGovernedSurfaceError
    from evaluators.scorer import compute_optimizer_scores

    _manual_inputs_path = getattr(args, 'manual_inputs', None)
    _input_bundle = load_inputs(ids_path=args.ids, manual_inputs_path=_manual_inputs_path)
    ids_raw = _input_bundle.ids_raw
    loadout_config = _input_bundle.loadout_config
    selected_perk_policy = _select_perk_policy(_input_bundle.perk_policy, args.perk_policy_preset)
    perk_config, perk_config_resolution = _resolve_perk_config(
        perk_mode=args.perk_mode,
        primary_config=_input_bundle.perk_config,
        perk_policy=selected_perk_policy,
        ids_raw=ids_raw,
        diag_output_dir=args.out / 'diagnostics' / 'perks',
    )
    if selected_perk_policy.get('_selected_policy_preset'):
        perk_config_resolution['perk_policy_preset'] = str(selected_perk_policy['_selected_policy_preset'])
    requested_perk_policy_preset = args.perk_policy_preset
    resolved_perk_policy_preset = (
        str(perk_config_resolution.get('perk_policy_preset') or requested_perk_policy_preset or '').strip() or None
    )
    formula_ledger = load_formula_ledger()
    ep_oracle = load_ep_oracle()
    qe_planner = QEResolutionPlanner()

    def _prepare_compare_rows_bundle(state_mode: str, default_preset: str, perk_state: str) -> PreparedCompareRowsBundle:
        compare_rows_by_preset = {}
        compare_publishable_rows_by_preset = {}
        perk_state_by_preset = {}
        perk_materialized_by_preset = {}
        state_cache = {}

        def _state_for_preset(preset_name: str):
            state = state_cache.get(preset_name)
            if state is None:
                state_kwargs = {
                    'default_preset': preset_name,
                    'loadout_config': loadout_config,
                    'perk_config': perk_config,
                    'manual_inputs': _input_bundle.manual_inputs,
                }
                runtime_state_overlay = getattr(args, 'runtime_state_overlay', None)
                if runtime_state_overlay:
                    state_kwargs['runtime_state_overlay'] = runtime_state_overlay
                state = build_runtime_state(ids_raw, **state_kwargs)
                state_cache[preset_name] = state
            return state

        def _materialize(preset_name: str, forced_perk_state: str | None = None):
            state = _state_for_preset(preset_name)
            preset_perk_state = _normalize_perk_state(forced_perk_state) if forced_perk_state is not None else ('off' if preset_name == 'Tourney' else perk_state)
            perks_enabled_local = _perks_enabled_for_state(state.active_perk_preset, preset_perk_state)
            state_key = f'{preset_name}__perks_{preset_perk_state}' if forced_perk_state is not None else preset_name
            perk_state_by_preset[state_key] = preset_perk_state
            perk_materialized_by_preset[state_key] = perks_enabled_local
            scenario_config = _run_stats_scenario_config(
                state,
                preset_name=preset_name,
                tier_number=getattr(args, 'tier', None),
            )
            snapshot = qe_planner.resolve_report_snapshot(
                state,
                preset_name=preset_name,
                state_mode=state_mode,
                perks_enabled=perks_enabled_local,
                scenario_context=_run_stats_scenario_context(scenario_config),
            )
            statbook = snapshot.statbook
            supplemental_timing_surface_ids = (
                'state::tower.package_chance_pct',
                'state::cards.wave_skip.chance_pct',
            )
            if scenario_config.mode_id == 'farming':
                supplemental_timing_surface_ids = (
                    *supplemental_timing_surface_ids,
                    'state::cards.intro_sprint.waves',
                    'state::meta.game_speed_multiplier',
                    'state::perk.max_game_speed',
                )
            missing_timing_surface_ids = tuple(
                surface_id for surface_id in supplemental_timing_surface_ids if surface_id not in statbook.rows
            )
            if missing_timing_surface_ids:
                timing_perks_enabled = perks_enabled_local and scenario_config.mode_id != 'tournament'
                timing_response = resolve_checkpoint_surfaces(
                    state,
                    requested_surface_ids=missing_timing_surface_ids,
                    preset_name=preset_name,
                    family_id=_run_stats_timing_family_id(
                        preset_name=preset_name,
                        perks_enabled=timing_perks_enabled,
                    ),
                    state_mode=state_mode,
                    perks_enabled=timing_perks_enabled,
                    scenario_context=_run_stats_scenario_context(scenario_config),
                    trace_mode='contributors',
                )
                timing_statbook = query_response_to_statbook(
                    timing_response,
                    notes='Compare supplemental timing-owned surfaces.',
                )
                statbook.rows.update(timing_statbook.rows)
            publish_query_surfaces(
                statbook.rows,
                manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
                account_state_labs=state.labs,
            )
            statbook_dict_local = statbook.to_dict()
            for destination, row in statbook_dict_local.get('rows', {}).items():
                row['formula_contract'] = _formula_contract(formula_ledger, destination)
            publishable = _build_publishable_statbook(statbook_dict_local, formula_ledger)
            compare_rows_by_preset[state_key] = {str(k): v for k, v in statbook_dict_local.get('rows', {}).items()}
            compare_publishable_rows_by_preset[state_key] = {str(k): v for k, v in publishable.get('rows', {}).items()}
            return state

        default_state = _materialize(default_preset)
        _materialize('Tourney')
        _materialize('Tourney', forced_perk_state='on')
        _materialize('Farming', forced_perk_state='on')
        compare_context_presets = sorted({default_preset, 'Tourney', 'Farming'})

        def _module_selection_payload(selection) -> dict[str, str | None]:
            return {
                'primary': getattr(selection, 'primary', None),
                'assist': getattr(selection, 'assist', None),
            }

        def _module_preset_payload(preset_name: str) -> dict[str, dict[str, str | None]]:
            preset = getattr(default_state, 'module_presets', {}).get(preset_name) or {}
            return {
                str(slot): _module_selection_payload(selection)
                for slot, selection in preset.items()
            }

        stage_context = {
            'state_mode': state_mode,
            'perk_state': perk_state,
            'perk_state_by_preset': dict(sorted(perk_state_by_preset.items())),
            'perk_materialized_by_preset': dict(sorted(perk_materialized_by_preset.items())),
            'active_perk_preset': _sanitized_active_perk_preset(default_state, default_preset),
            'default_compare_preset': default_preset,
            'active_cards_by_preset': {
                preset_name: list(default_state.card_presets.get(preset_name, []))
                for preset_name in compare_context_presets
            },
            'active_modules_by_preset': {
                preset_name: _module_preset_payload(preset_name)
                for preset_name in compare_context_presets
            },
            'modules_inventory': {
                str(name): asdict(snapshot)
                for name, snapshot in getattr(default_state, 'modules_inventory', {}).items()
            },
        }
        return PreparedCompareRowsBundle(default_state, compare_rows_by_preset, compare_publishable_rows_by_preset, stage_context)

    prepared_bundle = _prepare_compare_rows_bundle(args.state_mode, args.preset, args.perk_state)
    (
        account_state,
        compare_rows_by_preset,
        compare_publishable_rows_by_preset,
        package_stage_context,
    ) = _build_compare_rows_by_preset(prepared_bundle)
    _annotate_compare_row_payloads_by_preset(compare_rows_by_preset)
    _annotate_compare_row_payloads_by_preset(compare_publishable_rows_by_preset)

    perk_preset_name, perks_enabled = _run_stats_perk_state(
        account_state,
        preset_name=args.preset,
        perk_state=args.perk_state,
        perk_mode=args.perk_mode,
        state_mode=args.state_mode,
    )
    main_snapshot = qe_planner.resolve_report_snapshot(
        account_state,
        preset_name=args.preset,
        state_mode=args.state_mode,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
        scenario_context=_run_stats_scenario_context(
            _run_stats_scenario_config(
                account_state,
                preset_name=args.preset,
                tier_number=getattr(args, 'tier', None),
            )
        ),
    )
    stat_inputs = list(main_snapshot.stat_inputs)
    statbook = main_snapshot.statbook
    _merge_scenario_publication_rows(
        statbook,
        account_state=account_state,
        stat_inputs=stat_inputs,
        preset_name=args.preset,
        state_mode=args.state_mode,
        perks_enabled=perks_enabled,
        manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
    )
    publish_query_surfaces(
        statbook.rows,
        manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
        account_state_labs=account_state.labs,
    )
    statbook_dict = statbook.to_dict()
    for destination, row in statbook_dict.get('rows', {}).items():
        row['formula_contract'] = _formula_contract(formula_ledger, destination)
    _annotate_display_fields(statbook_dict)
    statbook_publishable_dict = _build_publishable_statbook(statbook_dict, formula_ledger)
    _annotate_display_fields(statbook_publishable_dict)

    state_matrix = {}
    for state_mode in SUPPORTED_STATE_MODES:
        matrix_perk_preset_name, matrix_perks_enabled = _run_stats_perk_state(
            account_state,
            preset_name=args.preset,
            perk_state=args.perk_state,
            perk_mode=args.perk_mode,
            state_mode=state_mode,
        )
        matrix_snapshot = qe_planner.resolve_report_snapshot(
            account_state,
            preset_name=args.preset,
            state_mode=state_mode,
            perk_preset_name=matrix_perk_preset_name,
            perks_enabled=matrix_perks_enabled,
            scenario_context=_run_stats_scenario_context(
                _run_stats_scenario_config(
                    account_state,
                    preset_name=args.preset,
                    tier_number=getattr(args, 'tier', None),
                )
            ),
        )
        matrix_inputs = list(matrix_snapshot.stat_inputs)
        matrix_statbook_obj = matrix_snapshot.statbook
        _merge_scenario_publication_rows(
            matrix_statbook_obj,
            account_state=account_state,
            stat_inputs=matrix_inputs,
            preset_name=args.preset,
            state_mode=state_mode,
            perks_enabled=matrix_perks_enabled,
            manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
        )
        publish_query_surfaces(
            matrix_statbook_obj.rows,
            manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
            account_state_labs=account_state.labs,
        )
        matrix_statbook = matrix_statbook_obj.to_dict()
        state_matrix[state_mode] = {
            'support': state_mode_support(state_mode),
            'input_count': len(matrix_inputs),
            'mapped_input_count': sum(1 for r in matrix_inputs if r.destination_id),
            'resolved_stat_count': matrix_statbook.get('diagnostics', {}).get('resolved_stat_count', 0),
            'partially_resolved_stat_count': matrix_statbook.get('diagnostics', {}).get('partially_resolved_stat_count', 0),
            'perk_preset_name': matrix_perk_preset_name,
            'perks_enabled': matrix_perks_enabled,
        }

    _ep_kwargs = dict(
        ep_stage_context_for_destination=_ep_stage_context_for_destination,
        compare_state_key_for_destination=_compare_state_key_for_destination,
        contributor_snapshot=_contributor_snapshot,
        apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions,
        formula_contract=_formula_contract,
        normalize_compare_values=_normalize_compare_values,
    )
    ep_compare = _build_ep_compare(
        ep_oracle, compare_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
    )
    ep_compare_publishable = _build_ep_compare(
        ep_oracle, compare_publishable_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
    )
    _annotate_compare_display_fields(ep_compare)
    _annotate_compare_display_fields(ep_compare_publishable)
    current_compare_summary = _build_compare_status_summary(ep_compare_publishable)

    if args.state_mode == 'max_progression':
        projected_account_state = account_state
        projected_compare_rows_by_preset = compare_rows_by_preset
        projected_compare_publishable_rows_by_preset = compare_publishable_rows_by_preset
        projected_stage_context = package_stage_context
    else:
        projected_bundle = _prepare_compare_rows_bundle('max_progression', args.preset, args.perk_state)
        (
            projected_account_state,
            projected_compare_rows_by_preset,
            projected_compare_publishable_rows_by_preset,
            projected_stage_context,
        ) = _build_compare_rows_by_preset(projected_bundle)
        _annotate_compare_row_payloads_by_preset(projected_compare_rows_by_preset)
        _annotate_compare_row_payloads_by_preset(projected_compare_publishable_rows_by_preset)
    projected_ep_compare_publishable = _build_ep_compare(
        ep_oracle, projected_compare_publishable_rows_by_preset, formula_ledger,
        projected_stage_context, **_ep_kwargs
    )
    _annotate_compare_display_fields(projected_ep_compare_publishable)
    projected_compare_summary = _build_compare_status_summary(projected_ep_compare_publishable)

    run_stats_artifacts = get_default_run_stats_session().build_run_stats_artifacts(args)
    run_stats_bounded_diagnostics = dict(run_stats_artifacts.get('diagnostics') or {})
    bounded_compare_rows_by_preset = _bounded_compare_rows_from_statbooks(
        run_stats_artifacts.get('max_books_by_preset') or {}
    )
    if bounded_compare_rows_by_preset:
        ep_compare = _build_ep_compare(
            ep_oracle, bounded_compare_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
        )
        ep_compare_publishable = _build_ep_compare(
            ep_oracle, bounded_compare_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
        )
        _annotate_compare_display_fields(ep_compare)
        _annotate_compare_display_fields(ep_compare_publishable)
        current_compare_summary = _build_compare_status_summary(ep_compare_publishable)
        projected_ep_compare_publishable = _build_ep_compare(
            ep_oracle, bounded_compare_rows_by_preset, formula_ledger,
            projected_stage_context, **_ep_kwargs
        )
        _annotate_compare_display_fields(projected_ep_compare_publishable)
        projected_compare_summary = _build_compare_status_summary(projected_ep_compare_publishable)

    def _query_rows_payload(books_by_preset: dict[str, dict], *, state_mode: str) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        for preset_name, statbook_payload in (books_by_preset or {}).items():
            payload[str(preset_name)] = {
                'rows': {str(surface_id): dict(row or {}) for surface_id, row in dict((statbook_payload or {}).get('rows') or {}).items()},
                'diagnostics': {
                    'pipeline_kind': 'run_stats_bounded_query',
                    'state_mode': state_mode,
                    'family_ids': list(((statbook_payload or {}).get('diagnostics') or {}).get('family_ids') or []),
                    'bundle_ids': list(((statbook_payload or {}).get('diagnostics') or {}).get('bundle_ids') or []),
                },
            }
        return payload

    dashboard_query_rows_start_payload = _query_rows_payload(
        run_stats_artifacts.get('start_books_by_preset') or {},
        state_mode='start_of_run',
    )
    dashboard_query_rows_max_payload = _query_rows_payload(
        run_stats_artifacts.get('max_books_by_preset') or {},
        state_mode='max_progression',
    )

    routing_class_counts = statbook.diagnostics.get('input_routing_class_counts', {})
    routed_input_count = statbook.diagnostics.get('mapped_input_count', sum(1 for row in stat_inputs if row.destination_id))
    truly_unrouted_input_count = statbook.diagnostics.get('unmapped_input_count', sum(1 for row in stat_inputs if not row.destination_id))
    unmapped_examples = {}
    for row in stat_inputs:
        if not row.destination_id and row.source_family not in unmapped_examples:
            unmapped_examples[row.source_family] = row.stat_name

    mapped_counter = Counter(row.source_family for row in stat_inputs if row.destination_id)
    total_counter = Counter(row.source_family for row in stat_inputs)

    card_preset_sizes = {name: len(cards) for name, cards in account_state.card_presets.items()}
    card_slot_limit_exceeded = {
        name: size
        for name, size in card_preset_sizes.items()
        if account_state.card_slots_unlocked is not None and size > account_state.card_slots_unlocked
    }

    resolved_surface_count = statbook.diagnostics.get('resolved_stat_count', 0)
    partial_surface_count = statbook.diagnostics.get('partially_resolved_stat_count', 0)
    total_input_count = len(stat_inputs)
    family_burn_down = {
        family: {
            'routed': mapped_counter.get(family, 0),
            'total': total_counter.get(family, 0),
            'pct': _safe_pct(mapped_counter.get(family, 0), total_counter.get(family, 0)),
        }
        for family in sorted(total_counter)
    }
    scoped_rows = [row for row in stat_inputs if _is_calculator_scope_row(row)]
    scoped_total = len(scoped_rows)
    scoped_mapped = sum(1 for row in scoped_rows if row.destination_id)
    scope_excluded_rows = [row for row in stat_inputs if not _is_calculator_scope_row(row)]
    scoped_family_totals = Counter(row.source_family for row in scoped_rows)
    perk_entities = load_perk_entities()
    perk_effects = load_perk_effects()
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()
    audit_perk_presets = {
        '__audit_all_perks__': [PerkSelection(perk_id=perk_id, picks=int(meta.get('max_picks') or 1)) for perk_id, meta in sorted(perk_entities.items())]
    }
    audit_state = replace(
        account_state,
        perk_presets=audit_perk_presets,
        perk_preset_namespace_class='transient',
        active_perk_preset='__audit_all_perks__',
    )
    all_perk_rows = [
        row
        for row in compile_stat_inputs(
            audit_state,
            preset_name=account_state.default_preset,
            state_mode='max_progression',
        )
        if row.source_family == 'perk'
    ]
    contributor_stat_inputs_by_preset = {}
    for preset_name in ("Farming", "Tourney"):
        contributor_perk_preset_name, contributor_perks_enabled = _run_stats_perk_state(
            account_state,
            preset_name=preset_name,
            perk_state=args.perk_state,
            perk_mode=args.perk_mode,
            state_mode=args.state_mode,
        )
        contributor_stat_inputs_by_preset[preset_name] = compile_stat_inputs(
            account_state,
            preset_name=preset_name,
            state_mode=args.state_mode,
            perk_preset_name=contributor_perk_preset_name,
            perks_enabled=contributor_perks_enabled,
        )

    audits = _build_publish_gate_audits(
        stat_inputs, statbook_publishable_dict, ep_compare_publishable, formula_ledger
    )
    kb_incomplete_areas = _build_kb_incomplete_areas(
        stat_inputs, statbook_publishable_dict, formula_ledger
    )
    kb_gap_register = _build_kb_gap_register(kb_incomplete_areas, audits)
    ep_compare_publishable = _ensure_compare_authoritative_verdict_fields(ep_compare_publishable)
    line_verification = _build_line_by_line_verification(
        statbook_publishable_dict, ep_compare_publishable, formula_ledger, _formula_contract
    )
    line_verification = _ensure_line_verification_authoritative_verdict_fields(line_verification)
    survivor_closure_report = _build_survivor_closure_report(ep_compare_publishable, line_verification)
    verification_counter = Counter(v['verification_status'] for v in line_verification.values())
    effective_perk_preset_name = _effective_perk_preset_for_publication(
        account_state,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
        canonical_output_preset=args.preset,
    )

    diagnostics = {
        'section_names': list(ids_raw.raw_sections.keys()),
        'section_row_counts': {k: len(v) for k, v in ids_raw.raw_sections.items()},
        'default_preset': args.preset,
        'state_mode': args.state_mode,
        'perk_mode': args.perk_mode,
        'requested_perk_policy_preset': requested_perk_policy_preset,
        'perk_policy_preset': resolved_perk_policy_preset,
        'perk_config_resolution': perk_config_resolution,
        'state_mode_support': state_mode_support(args.state_mode),
        'supported_state_modes': list(SUPPORTED_STATE_MODES),
        'state_matrix': state_matrix,
        'stat_input_count': len(stat_inputs),
        'statbook_row_count': len(statbook.rows),
        'engine_status': statbook.diagnostics.get('resolver_status'),
        'qe_resolution_interface': statbook.diagnostics.get('qe_resolution_interface'),
        'qe_resolution_backend': statbook.diagnostics.get('qe_resolution_backend'),
        'qe_native_family_available': statbook.diagnostics.get('qe_native_family_available'),
        'qe_native_family_id': statbook.diagnostics.get('qe_native_family_id'),
        'qe_native_family_merge': statbook.diagnostics.get('qe_native_family_merge'),
        'publish_status': statbook_publishable_dict.get('diagnostics', {}).get('oracle_policy'),
        'formula_ledger_version': formula_ledger.get('version'),
        'ep_compare_stage_rules': {
            'default_compare_preset': 'Farming',
            'preset_overrides': COMPARE_PRESET_OVERRIDES,
            'ep_progression_state': 'max_progression',
            'ep_workshop_state': 'derived_from_max_progression',
            'ep_run_state_default': 'farming',
            'ep_run_state_tourney_offense': 'tourney_present',
            'package_compare_capability': {
                'progression_state': 'dynamic_current_or_projected_max_by_state_mode',
                'workshop_state': 'dynamic_current_or_projected_max_by_state_mode',
                'perk_state': args.perk_state,
                'perk_mode': args.perk_mode,
                'requested_perk_policy_preset': requested_perk_policy_preset,
                'perk_policy_preset': resolved_perk_policy_preset,
                'perk_materialization': perks_enabled,
                'perk_ids_parser_support': False,
                'perk_external_config_support': True,
                'perk_account_state_support': True,
                'perk_stat_input_support': True,
                'perk_resolver_support': True,
                'perk_account_state_support': True,
                'active_perk_preset': effective_perk_preset_name,
                'configured_active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
                'state_mode': args.state_mode,
            },
            'notes': [
                'EP export compare uses run-situation policy: offense surfaces use Tourney loadout with perks off; non-offense surfaces use Farming by default and follow the selected perk state/mode.',
                'EP export max progression implies max workshop and farming-side perk application beyond the current IDS/loadout-present package state.',
                'Perk policy is input-owned; pipeline selects explicit perk mode none|max_progression_policy|runtime_timeline.',
                'Perk selections are not parsed from IDS itself; they must be supplied explicitly when a run state needs them.',
                'Perk application is controlled at pipeline scope via --perk-mode plus --perk-state auto|on|off.',
                'When values do not match and EP uses unsupported stage facets, compare status is stage_scope_mismatch rather than a hard formula mismatch.',
                'Max Recovery EP export is treated as a non-comparable health-at-cap surface, not a multiplier.',
            ],
        },
        'destination_type_schema': statbook.diagnostics.get('destination_type_schema', {}),
        'mapped_stat_input_count': routed_input_count,
        'unmapped_stat_input_count': truly_unrouted_input_count,
        'input_routing_class_counts': routing_class_counts,
        'resolved_stat_count': resolved_surface_count,
        'partially_resolved_stat_count': partial_surface_count,
        'burn_down': {
            'input_mapping_pct': _safe_pct(routed_input_count, total_input_count),
            'fully_resolved_surface_pct_of_inputs': _safe_pct(resolved_surface_count, total_input_count),
            'resolved_or_partial_surface_pct_of_inputs': _safe_pct(
                resolved_surface_count + partial_surface_count, total_input_count
            ),
            'family_mapping_pct': family_burn_down,
            'calculator_scope_total_inputs': scoped_total,
            'calculator_scope_mapped_inputs': scoped_mapped,
            'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
            'calculator_scope_excluded_inputs': len(scope_excluded_rows),
            'calculator_scope_excluded_examples': sorted({row.stat_name for row in scope_excluded_rows})[:20],
            'calculator_scope_family_totals': dict(sorted(scoped_family_totals.items())),
            'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.destination_id})[:20],
            'note': 'calculator_scope tracks true unrouted inputs only; routed metadata/capability/runtime-only classes no longer inflate unmapped counts.',
        },
        'tests_passed': 'not_run_by_run_stats',
        'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
        'calculator_scope_excluded_inputs': len(scope_excluded_rows),
        'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.destination_id})[:20],
        'card_slots_unlocked': account_state.card_slots_unlocked,
        'active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
        'configured_perk_presets': _sanitized_configured_perk_presets(account_state, args.preset),
        'active_card_preset': account_state.active_card_preset,
        'active_module_preset': account_state.active_module_preset,
        'perk_input_file': 'manual_inputs.yaml',
        'compare_package_value_provenance': {
            'statbook_default_output_preset': args.preset,
            'ep_compare_uses_rows_by_preset': True,
            'preset_overrides': COMPARE_PRESET_OVERRIDES,
            'note': 'ep_oracle_compare package_value may differ from statbook.json when compare_preset differs from the default output preset.',
        },
        'kb_incomplete_areas': kb_incomplete_areas,
        'kb_gap_register': kb_gap_register,
        'active_unmapped_input_count': kb_incomplete_areas['summary']['active_unmapped_input_count'],
        'resolved_unknown_schema_unit_count': kb_incomplete_areas['summary']['resolved_unknown_schema_unit_count'],
        'ambiguous_relic_semantic_hint_count': kb_incomplete_areas['summary']['ambiguous_relic_semantic_hint_count'],
        'perk_support': {
            'perk_ids_parser_support': False,
            'perk_ids_parser_note': 'Perk selections are not parsed from IDS; they are supplied through external perk config.',
            'perk_external_config_support': True,
            'perk_account_state_support': True,
            'perk_stat_input_support': True,
            'perk_resolver_support': True,
            'perk_state': args.perk_state,
            'perk_mode': args.perk_mode,
            'requested_perk_policy_preset': requested_perk_policy_preset,
            'perk_policy_preset': resolved_perk_policy_preset,
            'perk_materialization': perks_enabled,
        },
        'card_preset_sizes': card_preset_sizes,
        'card_slot_limit_exceeded': card_slot_limit_exceeded,
        'mapped_count_by_family': dict(sorted(mapped_counter.items())),
        'total_count_by_family': dict(sorted(total_counter.items())),
        'unmapped_example_by_family': unmapped_examples,
        'ep_compare_summary': current_compare_summary,
        **current_compare_summary,
        'ep_compare_projection_views': {
            'current_state_mode': {
                'state_mode': args.state_mode,
                'perk_state': args.perk_state,
                'active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
                **current_compare_summary,
            },
            'projected_max_progression': {
                'state_mode': 'max_progression',
                'perk_state': args.perk_state,
                'active_perk_preset': _sanitized_active_perk_preset(projected_account_state, args.preset),
                **projected_compare_summary,
            },
        },
        'lineage_backed_run_perk_destinations': sorted(COMPARE_DESTINATION_RUN_PERK_FACETS.keys()),
        'compare_layer_destination_unit_inconsistencies': audits.get('compare_layer_destination_unit_inconsistencies', []),
        'audits': audits,
        'line_verification_summary': dict(sorted(verification_counter.items())),
        'slow_audits': {
            'include_slow_audits': bool(getattr(args, 'include_slow_audits', False)),
            'compare_situation_fit_matrix': 'enabled' if bool(getattr(args, 'include_slow_audits', False)) else 'skipped_by_default',
        },
        'presentation': {
            'scope': 'display_fields_only',
            'raw_value_policy': 'preserve_full_precision_raw_numeric_values',
            'abbreviations': ['k', 'M', 'B', 'T', 'q', 'Q', 's', 'S'],
            'percent_policy': 'pct_and_percent_display_render_with_percent_sign',
            'multiplier_policy': 'multiplier_and_multiplier_display_render_with_leading_x',
        },
        'kb_only_health_family_audit': _build_kb_only_health_family_audit(
            stat_inputs, statbook_publishable_dict['rows']
        ),
        'kb_only_damage_defense_absolute_scope_audit': _build_damage_defabs_scope_audit(
            account_state, stat_inputs, statbook_publishable_dict['rows']
        ),
        'perk_coverage_audit': _build_perk_coverage_audit(
            perk_entities,
            perk_effects,
            PERK_TARGET_DESTINATION_OVERRIDES,
            all_perk_rows,
            canon_stats,
            alias_index,
            None,
        ),
        'tower_damage_residue_analysis': _build_tower_damage_residue_analysis(
            projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable
        ),
        'run_perk_residue_analysis': _build_run_perk_residue_analysis(
            projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable
        ),
        'tradeoff_routing_audit': _build_tradeoff_routing_audit(
            compile_stat_inputs(
                account_state,
                preset_name=args.preset,
                state_mode=args.state_mode,
                perk_preset_name=perk_preset_name,
                perks_enabled=perks_enabled,
            ),
            perk_entities,
            TRADE_OFF_BENEFIT_EFFECT_INDEXES,
            {str(item).strip() for item in (perk_config or {}).get('banned_perk_ids', []) if str(item).strip()},
            preset=args.preset, state_mode=args.state_mode, perk_state=args.perk_state,
        ),
        'perk_contributor_audit': _build_perk_contributor_audit(
            contributor_stat_inputs_by_preset
        ),
        'compare_situation_fit_matrix': {
            'status': 'skipped',
            'reason': 'disabled_by_default_use_include_slow_audits',
            'destination_count': 0,
            'best_fit_by_destination': {},
            'best_fit_state_counts': {},
            'best_fit_status_counts': {},
            'states': {},
        },
    }
    if bool(getattr(args, 'include_slow_audits', False)):
        compare_states = {
            'current': {'preset': args.preset, 'perk_state': args.perk_state, 'compare': ep_compare_publishable},
            'projected': {'preset': args.preset, 'perk_state': args.perk_state, 'compare': projected_ep_compare_publishable},
        }
        diagnostics['compare_situation_fit_matrix'] = _build_compare_situation_fit_matrix(compare_states)
    diagnostics['survivability_residue_analysis'] = _build_survivability_residue_analysis(
        ep_compare_publishable, diagnostics['compare_situation_fit_matrix'], statbook_dict
    )
    diagnostics['tower_regen_closure_report'] = _build_tower_regen_closure_report(ep_compare_publishable)
    diagnostics['tower_hp_semantic_gap_report'] = _build_tower_hp_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_regen_ep_semantic_gap_report'] = _build_tower_regen_ep_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_defense_absolute_semantic_gap_report'] = _build_tower_defense_absolute_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_damage_runtime_gap_report'] = _build_tower_damage_runtime_gap_report(ep_compare_publishable)
    diagnostics['compare_situation_policy'] = {
        'ep_oracle_shortcut_context': {
            'scope': 'compare_only',
            'edamage': 'EP export uses Tournament loadout with perks off.',
            'ehp_eecon': 'EP export uses Farming loadout with perks on and account Farming Tier Dissonance unless an explicit scenario override is requested.',
            'runtime_policy': 'QE and simulator calculations remain preset, tier, perk, and scenario parameterized; EP shortcut context must not become runtime truth.',
        },
        'tournament': {
            'preset': 'Tourney',
            'perk_state': package_stage_context.get('perk_state_by_preset', {}).get('Tourney', 'off'),
        },
        'farming': {
            'preset': 'Farming',
            'perk_state': package_stage_context.get('perk_state_by_preset', {}).get('Farming', args.perk_state),
        },
        'milestone_engine': {
            'preset': args.preset,
            'perk_state': package_stage_context.get('perk_state_by_preset', {}).get(args.preset, args.perk_state),
        },
        'milestone_compare_policy': {
            'preset': 'Milestone',
            'perk_state': 'on',
            'note': 'Milestone is a real preset with perks on, but EP compare excludes milestone loadout.',
        },
        'policy_note': 'Perks are controlled by run situation. Tournament compare uses Tourney loadout with perks off; farming follows the selected perk state/mode; milestone is a real preset with perks on, but EP compare excludes milestone loadout. EP export shortcut context is compare-only and does not hardcode runtime calculations.',
    }
    if 'run_tracker_calibration_evidence' in run_stats_bounded_diagnostics:
        diagnostics['run_tracker_calibration_evidence'] = (
            run_stats_bounded_diagnostics['run_tracker_calibration_evidence']
        )
    if 'farming_econ_model_readiness' in run_stats_bounded_diagnostics:
        diagnostics['farming_econ_model_readiness'] = (
            run_stats_bounded_diagnostics['farming_econ_model_readiness']
        )
    diagnostics['perk_support'] = diagnostics['ep_compare_stage_rules']['package_compare_capability']

    audit_surface_manifest = _build_audit_surface_manifest(account_state, args.preset)
    artifact_contract_manifest = _build_artifact_contract_manifest(account_state, args.preset, stat_inputs, statbook_dict)
    family_completeness_matrix = _build_family_completeness_matrix(account_state, stat_inputs)
    try:
        optimizer_scores = compute_optimizer_scores(statbook_dict)
        diagnostics['optimizer_scores'] = {
            'status': 'resolved',
            'missing_surface_policy': 'fail_closed',
            'local_canonical_formula_fallback': False,
        }
    except MissingGovernedSurfaceError as exc:
        optimizer_scores = {
            'objectives': {},
            'meta': {
                'version': 'v4',
                'status': 'unavailable',
                'reason': 'missing_governed_surface',
                'message': str(exc),
                'requires': 'derived::ehp, derived::edamage, and derived::eecon must already be published by Query Engine surfaces',
                'missing_surface_policy': 'fail_closed',
                'local_canonical_formula_fallback': False,
            },
        }
        diagnostics['optimizer_scores'] = dict(optimizer_scores['meta'])
    boss_wave_milestone_matrix_payload = None
    if bool(getattr(args, 'include_boss_wave_milestone_matrix', False)):
        matrix_request = PipelineRunRequest(
            ids=args.ids,
            out=args.out,
            preset='Milestone',
            state_mode=args.state_mode,
            manual_inputs=args.manual_inputs,
            runtime_state_overlay=getattr(args, 'runtime_state_overlay', None),
            perk_mode='max_progression_policy',
            perk_state='auto',
            run_tracker_csv=getattr(args, 'run_tracker_csv', None),
        )
        boss_wave_milestone_matrix_payload = build_boss_wave_milestone_matrix(
            matrix_request,
            tiers=_boss_wave_matrix_tiers_from_args(args),
            scenario_runtime_inputs=_boss_wave_matrix_runtime_inputs_from_args(args),
            comparison_scenario_runtime_inputs=_boss_wave_matrix_comparison_inputs_from_args(args),
            comparison_label=_boss_wave_matrix_comparison_label_from_args(args),
            dissonance_run_categories=_boss_wave_matrix_dissonance_categories_from_args(args),
            align_clean_reference_rows=bool(getattr(args, 'boss_wave_align_clean_reference_rows', True)),
        )
        diagnostics['boss_wave_milestone_matrix'] = _boss_wave_milestone_matrix_diagnostics_payload(
            boss_wave_milestone_matrix_payload
        )
    else:
        stale_matrix = args.out / BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT
        if stale_matrix.exists():
            stale_matrix.unlink()
        diagnostics['boss_wave_milestone_matrix'] = {
            'enabled': False,
            'reason': 'optional_matrix_not_requested',
            'artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
        }
    module_card_payloads_data = build_module_card_payloads(account_state)
    diagnostics['current_scope_effect_family_evidence'] = (
        _current_scope_effect_family_evidence_summary(
            family_completeness_matrix,
            boss_wave_milestone_matrix_payload,
            statbook_dict=statbook_publishable_dict,
            line_verification=line_verification,
            module_card_payloads=module_card_payloads_data,
            query_rows_start_of_run=dashboard_query_rows_start_payload,
            query_rows_max_progression=dashboard_query_rows_max_payload,
            selected_preset=args.preset,
        )
    )
    diagnostics['tower_goal_readiness'] = _tower_goal_readiness_summary(diagnostics)
    run_stats_artifacts['run_stats_payload']['diagnostics'] = diagnostics

    # Prepare payloads and delegate output writing to publication authority
    account_state_payload = _sanitized_account_state_for_output(account_state, args.preset)
    stat_inputs_payload = [row.to_dict() for row in stat_inputs]
    qe_dashboard_publications = _build_input_dashboard_qe_publications(
        account_state=account_state,
        compare_rows_by_preset=compare_rows_by_preset,
        projected_compare_rows_by_preset=projected_compare_rows_by_preset,
        stat_inputs=stat_inputs,
        preset_name=args.preset,
    )

    write_core_outputs(
        out_dir=args.out,
        diagnostics=diagnostics,
        account_state_payload=account_state_payload,
        stat_inputs_payload=stat_inputs_payload,
        statbook_dict=statbook_dict,
        statbook_publishable_dict=statbook_publishable_dict,
        ep_compare_publishable=ep_compare_publishable,
        line_verification=line_verification,
        survivor_closure_report=survivor_closure_report,
        state_matrix=state_matrix,
        optimizer_scores=optimizer_scores,
        audit_surface_manifest=audit_surface_manifest,
        artifact_contract_manifest=artifact_contract_manifest,
        family_completeness_matrix=family_completeness_matrix,
        root_path=ROOT,
        module_card_payloads=module_card_payloads_data,
        qe_dashboard_publications=qe_dashboard_publications,
        query_rows_start_of_run=dashboard_query_rows_start_payload,
        query_rows_max_progression=dashboard_query_rows_max_payload,
        selected_preset=args.preset,
        selected_state_mode=args.state_mode,
    )
    run_stats_path = args.out / 'run_stats.json'
    if run_stats_path.exists():
        run_stats_payload = _load_json_artifact(run_stats_path)
        run_stats_payload['diagnostics'] = diagnostics
        run_stats_path.write_text(
            json.dumps(_contract_json_payload(run_stats_payload), indent=2, default=str),
            encoding='utf-8',
        )
    if boss_wave_milestone_matrix_payload is not None:
        (args.out / BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT).write_text(
            json.dumps(_contract_json_payload(boss_wave_milestone_matrix_payload), indent=2, default=str),
            encoding='utf-8',
        )

    # Write module card payloads (QE-generated orchestration artifact, PR329)
    (args.out / 'module_card_payloads.json').write_text(
        json.dumps(_contract_json_payload(module_card_payloads_data), indent=2, default=str)
    )

    # Remove stale output files
    stale_outputs = [
        'ep_oracle_compare_backfilled.json',
        'statbook_oracle_backfilled.json',
        'destination_formula_ledger.json',
        'forensic_debug_focus.json',
    ]
    for stale_name in stale_outputs:
        stale_path = args.out / stale_name
        if stale_path.exists():
            try:
                stale_path.unlink()
            except FileNotFoundError:
                continue

    return 0


def _build_pipeline_trace_from_artifacts(
    *,
    request: PipelineRunRequest,
    total_elapsed_ms: float,
    diagnostics: dict[str, object],
) -> PipelineTrace:
    execution_path = {
        'recompute_mode': diagnostics.get('qe_resolution_backend') or diagnostics.get('query_backend') or 'analysis_pipeline',
        'execution_branch': diagnostics.get('qe_resolution_interface') or diagnostics.get('pipeline_kind') or 'analysis_pipeline',
        'cache_status': 'warm' if ((diagnostics.get('session') or {}).get('account_state_cache_hit')) else 'cold',
        'fallback_required': False,
        'fallback_reason': None,
        'bundle_used': None,
        'consumer_id': None,
        'family_id': diagnostics.get('qe_native_family_id'),
        'runtime_consumers': [],
        'cache_fingerprint': None,
        'cache_validation': None,
        'incremental_plan': None,
        'parity': None,
        'runtime_publication': None,
        'total_elapsed_ms': total_elapsed_ms,
    }
    timings = diagnostics.get('timings_ms') or {}
    stages = [
        PipelineStageRecord(
            stage_id='input_load',
            title='Input load',
            owner_module='input.loader',
            entry_function='load_inputs',
            status='ok',
            elapsed_ms=float(((diagnostics.get('session') or {}).get('account_state_build_ms')) or 0.0),
            outputs_summary={
                'ids_path': _relpath_str(request.ids),
                'manual_inputs_path': (
                    request.manual_inputs.as_posix()
                    if request.manual_inputs is not None
                    else _relpath_str(_effective_manual_inputs_path(request.manual_inputs))
                ),
                'run_tracker_csv': (
                    None if request.run_tracker_csv is None else _relpath_str(request.run_tracker_csv)
                ),
                'approve_tracker_empirical_farming_cph': bool(
                    getattr(request, 'approve_tracker_empirical_farming_cph', False)
                ),
                'approve_tracker_empirical_run_coin_duration_integrals': bool(
                    getattr(
                        request,
                        'approve_tracker_empirical_run_coin_duration_integrals',
                        False,
                    )
                ),
                'approve_tracker_current_export_account_state_validation': bool(
                    getattr(
                        request,
                        'approve_tracker_current_export_account_state_validation',
                        False,
                    )
                ),
                'approve_tracker_empirical_run_duration_projection': bool(
                    getattr(
                        request,
                        'approve_tracker_empirical_run_duration_projection',
                        False,
                    )
                ),
                'approve_tracker_empirical_wave_skip_reward': bool(
                    getattr(request, 'approve_tracker_empirical_wave_skip_reward', False)
                ),
                'approve_tracker_wave_skip_intro_semantics': bool(
                    getattr(request, 'approve_tracker_wave_skip_intro_semantics', False)
                ),
                'approve_source_intro_sprint_coin_window': bool(
                    getattr(request, 'approve_source_intro_sprint_coin_window', False)
                ),
                'approve_tracker_empirical_econ_window_overlap': bool(
                    getattr(
                        request,
                        'approve_tracker_empirical_econ_window_overlap',
                        False,
                    )
                ),
            'approve_tracker_empirical_kill_density_transform': bool(
                getattr(request, 'approve_tracker_empirical_kill_density_transform', False)
            ),
            'approve_boss_wave_pressure_factor_review_default': bool(
                getattr(
                    request,
                    'approve_boss_wave_pressure_factor_review_default',
                    False,
                )
            ),
            'runtime_state_overlay': request.runtime_state_overlay,
            'section_names': diagnostics.get('section_names', []),
            'section_row_counts': diagnostics.get('section_row_counts', {}),
            },
        ),
        PipelineStageRecord(
            stage_id='runtime_account_assembly',
            title='Runtime/account assembly',
            owner_module='input.runtime_state',
            entry_function='build_runtime_state',
            status='ok',
            elapsed_ms=float(((diagnostics.get('session') or {}).get('account_state_build_ms')) or 0.0),
            outputs_summary={
                'runtime_state_overlay': request.runtime_state_overlay,
                'perk_config_resolution': diagnostics.get('perk_config_resolution', {}),
                'perk_support': diagnostics.get('perk_support', {}),
            },
        ),
        PipelineStageRecord(
            stage_id='compare_materialization',
            title='Compare materialization',
            owner_module='evaluators.compare',
            entry_function='_build_compare_rows_by_preset',
            status='ok',
            elapsed_ms=0.0,
            outputs_summary={
                'default_preset': diagnostics.get('default_preset'),
                'state_mode': diagnostics.get('state_mode'),
                'perk_state': diagnostics.get('perk_support', {}).get('perk_state'),
            },
        ),
        PipelineStageRecord(
            stage_id='stat_resolution',
            title='Stat-input compilation and resolution',
            owner_module='qe.routing',
            entry_function='QEResolutionPlanner.resolve_report_snapshot',
            status='ok',
            elapsed_ms=float((((timings.get('presets') or {}).get(request.preset, {}) or {}).get(request.state_mode, {}) or {}).get('total_state_ms', 0.0)),
            outputs_summary={
                'stat_input_count': diagnostics.get('stat_input_count'),
                'statbook_row_count': diagnostics.get('statbook_row_count'),
                'engine_status': diagnostics.get('engine_status'),
                'qe_resolution_backend': diagnostics.get('qe_resolution_backend'),
            },
        ),
        PipelineStageRecord(
            stage_id='checks_generation',
            title='Compare/verification generation',
            owner_module='evaluators.compare',
            entry_function='build_line_by_line_verification',
            status='ok',
            elapsed_ms=0.0,
            outputs_summary={
                'ep_compare_summary': diagnostics.get('ep_compare_summary', {}),
                'line_verification_summary': diagnostics.get('line_verification_summary', {}),
                'state_matrix_modes': list((diagnostics.get('state_matrix') or {}).keys()),
            },
        ),
        PipelineStageRecord(
            stage_id='artifact_write',
            title='Artifact write',
            owner_module='app.publication',
            entry_function='write_core_outputs',
            status='ok',
            elapsed_ms=float(timings.get('write_outputs_ms') or 0.0),
            outputs_summary={'out_dir': _relpath_str(request.out)},
        ),
    ]
    return PipelineTrace(
        request={
            'ids': _relpath_str(request.ids),
            'out': _relpath_str(request.out),
            'preset': request.preset,
            'state_mode': request.state_mode,
            'manual_inputs': None if request.manual_inputs is None else _relpath_str(request.manual_inputs),
            'runtime_state_overlay': request.runtime_state_overlay,
            'perk_mode': request.perk_mode,
            'perk_policy_preset': request.perk_policy_preset,
            'include_slow_audits': request.include_slow_audits,
            'perk_state': request.perk_state,
            'tier': request.tier,
            'include_boss_wave_milestone_matrix': request.include_boss_wave_milestone_matrix,
            'boss_wave_align_clean_reference_rows': request.boss_wave_align_clean_reference_rows,
            'run_tracker_csv': None if request.run_tracker_csv is None else _relpath_str(request.run_tracker_csv),
            'approve_tracker_empirical_farming_cph': bool(
                getattr(request, 'approve_tracker_empirical_farming_cph', False)
            ),
            'approve_tracker_empirical_run_coin_duration_integrals': bool(
                getattr(
                    request,
                    'approve_tracker_empirical_run_coin_duration_integrals',
                    False,
                )
            ),
            'approve_tracker_current_export_account_state_validation': bool(
                getattr(
                    request,
                    'approve_tracker_current_export_account_state_validation',
                    False,
                )
            ),
            'approve_tracker_empirical_run_duration_projection': bool(
                getattr(
                    request,
                    'approve_tracker_empirical_run_duration_projection',
                    False,
                )
            ),
            'approve_tracker_empirical_wave_skip_reward': bool(
                getattr(request, 'approve_tracker_empirical_wave_skip_reward', False)
            ),
            'approve_tracker_wave_skip_intro_semantics': bool(
                getattr(request, 'approve_tracker_wave_skip_intro_semantics', False)
            ),
            'approve_source_intro_sprint_coin_window': bool(
                getattr(request, 'approve_source_intro_sprint_coin_window', False)
            ),
            'approve_tracker_empirical_econ_window_overlap': bool(
                getattr(
                    request,
                    'approve_tracker_empirical_econ_window_overlap',
                    False,
                )
            ),
            'approve_tracker_empirical_kill_density_transform': bool(
                getattr(request, 'approve_tracker_empirical_kill_density_transform', False)
            ),
            'approve_boss_wave_pressure_factor_review_default': bool(
                getattr(
                    request,
                    'approve_boss_wave_pressure_factor_review_default',
                    False,
                )
            ),
        },
        execution_path=execution_path,
        stages=stages,
        artifacts_written=[],
    )


def execute_pipeline(request: PipelineRunRequest) -> PipelineRunResult:
    started_at = perf_counter()
    args = type('PipelineArgs', (), {})()
    args.ids = request.ids
    args.out = request.out
    args.preset = request.preset
    args.state_mode = request.state_mode
    args.manual_inputs = request.manual_inputs
    args.runtime_state_overlay = request.runtime_state_overlay
    args.perk_mode = request.perk_mode
    args.perk_policy_preset = request.perk_policy_preset
    args.include_slow_audits = request.include_slow_audits
    args.perk_state = request.perk_state
    args.tier = request.tier
    args.dissonance_run_category = request.dissonance_run_category
    args.include_boss_wave_milestone_matrix = request.include_boss_wave_milestone_matrix
    args.boss_wave_align_clean_reference_rows = request.boss_wave_align_clean_reference_rows
    args.run_tracker_csv = request.run_tracker_csv
    args.approve_tracker_empirical_farming_cph = bool(
        getattr(request, 'approve_tracker_empirical_farming_cph', False)
    )
    args.approve_tracker_empirical_run_coin_duration_integrals = bool(
        getattr(
            request,
            'approve_tracker_empirical_run_coin_duration_integrals',
            False,
        )
    )
    args.approve_tracker_current_export_account_state_validation = bool(
        getattr(
            request,
            'approve_tracker_current_export_account_state_validation',
            False,
        )
    )
    args.approve_tracker_empirical_run_duration_projection = bool(
        getattr(request, 'approve_tracker_empirical_run_duration_projection', False)
    )
    args.approve_tracker_empirical_wave_skip_reward = bool(
        getattr(request, 'approve_tracker_empirical_wave_skip_reward', False)
    )
    args.approve_tracker_wave_skip_intro_semantics = bool(
        getattr(request, 'approve_tracker_wave_skip_intro_semantics', False)
    )
    args.approve_source_intro_sprint_coin_window = bool(
        getattr(request, 'approve_source_intro_sprint_coin_window', False)
    )
    args.approve_tracker_empirical_econ_window_overlap = bool(
        getattr(request, 'approve_tracker_empirical_econ_window_overlap', False)
    )
    args.approve_tracker_empirical_kill_density_transform = bool(
        getattr(request, 'approve_tracker_empirical_kill_density_transform', False)
    )
    args.approve_boss_wave_pressure_factor_review_default = bool(
        getattr(request, 'approve_boss_wave_pressure_factor_review_default', False)
    )
    exit_code = run_analysis_pipeline(args)
    diagnostics = _load_json_artifact(request.out / 'diagnostics.json')
    total_elapsed_ms = round((perf_counter() - started_at) * 1000.0, 3)
    pipeline_trace = _build_pipeline_trace_from_artifacts(
        request=request,
        total_elapsed_ms=total_elapsed_ms,
        diagnostics=diagnostics,
    )
    generated_files = _generated_output_paths(request.out)
    pipeline_trace = PipelineTrace(
        request=pipeline_trace.request,
        execution_path=pipeline_trace.execution_path,
        stages=pipeline_trace.stages,
        artifacts_written=[_relpath_str(path) for path in generated_files],
    )
    write_pipeline_trace(request.out, pipeline_trace, ROOT)
    generated_files = _generated_output_paths(request.out)
    return PipelineRunResult(
        exit_code=int(exit_code),
        request=request,
        out_dir=request.out,
        diagnostics=diagnostics,
        generated_files=tuple(generated_files),
        pipeline_trace=pipeline_trace,
    )


def build_verification_snapshot_set(
    base_request: PipelineRunRequest,
    specs: tuple[VerificationSnapshotSpec, ...] | list[VerificationSnapshotSpec] | None = None,
) -> list[PipelineRunResult]:
    requests = _default_verification_matrix_requests(base_request) if specs is None else tuple(
        PipelineRunRequest(
            ids=base_request.ids,
            out=base_request.out / (spec.out_subdir or f'{spec.preset.lower()}_{spec.state_mode}'),
            preset=spec.preset,
            state_mode=spec.state_mode,
            manual_inputs=base_request.manual_inputs,
            runtime_state_overlay=base_request.runtime_state_overlay,
            perk_mode=base_request.perk_mode,
            perk_policy_preset=base_request.perk_policy_preset,
            include_slow_audits=base_request.include_slow_audits,
            perk_state=spec.perk_state,
            tier=base_request.tier,
        )
        for spec in specs
    )
    results: list[PipelineRunResult] = []
    for request in requests:
        results.append(execute_pipeline(request))
    return results


def _default_verification_matrix_requests(base_request: PipelineRunRequest) -> tuple[PipelineRunRequest, ...]:
    specs = (
        VerificationSnapshotSpec('Farming', 'start_of_run'),
        VerificationSnapshotSpec('Farming', 'max_progression'),
        VerificationSnapshotSpec('Tourney', 'start_of_run', perk_state='off'),
        VerificationSnapshotSpec('Tourney', 'max_progression', perk_state='off'),
    )
    return tuple(
        PipelineRunRequest(
            ids=base_request.ids,
            out=base_request.out / (spec.out_subdir or f'{spec.preset.lower()}_{spec.state_mode}'),
            preset=spec.preset,
            state_mode=spec.state_mode,
            manual_inputs=base_request.manual_inputs,
            runtime_state_overlay=base_request.runtime_state_overlay,
            perk_mode=base_request.perk_mode,
            perk_policy_preset=base_request.perk_policy_preset,
            include_slow_audits=base_request.include_slow_audits,
            perk_state=spec.perk_state,
            tier=base_request.tier,
        )
        for spec in specs
    )


def resolve_fast_checkpoint(request: FastCheckpointRequest) -> FastCheckpointResult:
    from simulators.snapshot_resolver import SimulatorSnapshotResolver
    if not request.requested_surface_ids:
        raise ValueError('requested_surface_ids must not be empty: fast checkpoint resolution requires at least one surface id.')

    input_bundle, account_state, _perk_config_resolution = _build_account_state(
        ids_path=request.ids,
        manual_inputs_path=request.manual_inputs,
        runtime_state_overlay=request.runtime_state_overlay,
        preset=request.preset,
        perk_mode=request.perk_mode,
        perk_policy_preset=request.perk_policy_preset,
        diag_output_dir=None,
    )
    perk_preset_name, perks_enabled = _run_stats_perk_state(
        account_state,
        preset_name=request.preset,
        perk_state=request.perk_state,
        perk_mode=request.perk_mode,
        state_mode=request.state_mode,
    )
    checkpoint_resolution = SimulatorSnapshotResolver().resolve_checkpoint(
        account_state=account_state,
        checkpoint_state=SimulatorCheckpointState(),
        preset_name=request.preset,
        requested_surface_ids=request.requested_surface_ids,
        state_mode=request.state_mode,
        card_preset_name=account_state.active_card_preset,
        module_preset_name=account_state.active_module_preset,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
    )
    response = resolve_checkpoint_surfaces(
        account_state,
        requested_surface_ids=request.requested_surface_ids,
        preset_name=request.preset,
        state_mode=request.state_mode,
        card_preset_name=account_state.active_card_preset,
        module_preset_name=account_state.active_module_preset,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
        trace_mode='full_trace',
    )
    statbook = query_response_to_statbook(
        response,
        notes='Lightweight QE checkpoint resolution for interactive stat verification.',
        diagnostics={
            'resolver_kind': checkpoint_resolution.diagnostics.get('resolver_kind'),
            'phase_timing_ms': checkpoint_resolution.diagnostics.get('phase_timing_ms'),
            'requested_surface_ids': list(request.requested_surface_ids),
            'state_mode': request.state_mode,
            'preset': request.preset,
            'perk_state': request.perk_state,
            'perk_preset_name': perk_preset_name,
            'perks_enabled': perks_enabled,
        },
    )
    statbook_dict = statbook.to_dict()
    _annotate_display_fields(statbook_dict)
    return FastCheckpointResult(
        request=request,
        statbook=statbook_dict,
        diagnostics={
            **dict(checkpoint_resolution.diagnostics),
            'perk_preset_name': perk_preset_name,
            'perks_enabled': perks_enabled,
        },
    )



