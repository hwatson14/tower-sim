"""
app/pipeline.py -- Layer wiring.

Owns: wiring input -> qe -> simulators -> evaluators -> advisors,
output assembly, pipeline configuration.
Must not own: domain logic.

T12: bridge removed; all _h.* calls resolved to real owners.
Domain helpers live in their real owners (evaluators.compare, input.loader).
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from dataclasses import asdict, replace
from collections import Counter, OrderedDict
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Mapping

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
from simulators.timing import compile_timing_family_rows, merge_scenario_publication_rows as merge_timing_scenario_publication_rows, resolve_timing_consumer_bundle
from input.state_types import ScenarioRuntimeInputs
from qe.models import BoundStatInputs, StatRow, bind_state_identity

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
    'state::labs.dissonant_echo.defense.level',
    'state::dissonance.defense.active_boost_multiplier',
    'state::dissonance.defense.echo_source_bonus',
    'state::tower.thorns_damage_pct',
    'state::wall.thorns_damage_pct',
    'state::cards.damage.mastery_effect',
    'state::cards.berserker.assumed_bonus_multiplier',
    'state::cards.ultimate_crit.chance_pct',
    'state::cards.plasma_cannon.effect_pct',
    'state::cards.energy_net.duration_seconds',
    'state::cards.energy_net.mastery_effect',
    'state::module.anti_cube_portal.shockwave_damage_taken_mult_x',
    'state::module.dimension_core.max_shock_stacks',
    'state::module.project_funding.cash_digit_multiplier_pct',
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
    'state::shock.damage_multiplier',
    'state::bot.flame.owned',
    'state::bot.flame.damage_reduction_pct',
    'state::bot.flame.cooldown_seconds',
    'state::bot.flame.range_m',
    'support_surface::dissonance.attack_run_active',
    'support_surface::dissonance.defense_run_active',
    'support_surface::dissonance.utility_run_active',
    'support_surface::dissonance.ultimate_weapons_run_active',
)
BOSS_WAVE_OPTIONAL_PRIMITIVE_SURFACE_IDS: tuple[str, ...] = (
    'state::cards.slow_aura.enemy_speed_pct',
    'state::cards.slow_aura.mastery_effect',
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
    'source_owned_v28_damage_health_decay_magnitudes',
    'source_owned_full_gc_boss_applicable_damage_semantics',
)


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


def _boss_wave_explicit_terminal_pressure_closed(runtime_inputs: ScenarioRuntimeInputs | None) -> bool:
    return all(
        _runtime_input_positive(runtime_inputs, field_name)
        for field_name in (
            'fleet_terminal_max_wave',
            'elite_terminal_max_wave',
            'protector_terminal_max_wave',
            'armored_terminal_max_wave',
        )
    )


def _boss_wave_explicit_damage_health_decay_closed(runtime_inputs: ScenarioRuntimeInputs | None) -> bool:
    return (
        _runtime_input_positive(runtime_inputs, 'tower_damage_decay_pct')
        and _runtime_input_positive(runtime_inputs, 'tower_health_decay_pct')
    )


def _boss_wave_explicit_gc_bridge_closed(
    runtime_inputs: ScenarioRuntimeInputs | None,
    *,
    gc_boss_damage_source: str | None = None,
) -> bool:
    if str(gc_boss_damage_source or '').startswith('runtime_input_'):
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


def _boss_wave_selected_model_requires_full_gc_bridge(
    *,
    selected_model: object,
    gc_boss_damage_source: object | None,
) -> bool:
    model = str(selected_model or '')
    if model.startswith('ehp_hit_by_hit') or model.startswith('unified_hit_by_hit'):
        return False
    if (
        model.startswith('cl_only_pre_contact_boss_kill')
        and str(gc_boss_damage_source or '') in {
            'qe_derived_boss_applicable_dps_cl_only_fail_closed_default',
            'qe_derived_edamage_boss_fail_closed_default',
            'qe_derived_edamage_boss_runtime_exposure_model',
            'qe_derived_edamage_ep_boss_exposure_model',
        }
    ):
        return False
    return True


def _boss_wave_model_certification_payload(
    *,
    contact_time_source: str | None = None,
    runtime_inputs: ScenarioRuntimeInputs | None = None,
    gc_boss_damage_source: str | None = None,
    damage_health_decay_required: bool = True,
    gc_boss_applicable_damage_required: bool = True,
) -> dict[str, object]:
    blockers = list(_BOSS_WAVE_MODEL_COMPLETION_BLOCKERS)
    if not damage_health_decay_required or _boss_wave_explicit_damage_health_decay_closed(runtime_inputs):
        blockers.remove('source_owned_v28_damage_health_decay_magnitudes')
    if (
        not bool(gc_boss_applicable_damage_required)
        or _boss_wave_explicit_gc_bridge_closed(runtime_inputs, gc_boss_damage_source=gc_boss_damage_source)
    ):
        blockers.remove('source_owned_full_gc_boss_applicable_damage_semantics')
    if str(contact_time_source or '') == 'matrix_default_assumption':
        blockers.append('matrix_default_boss_contact_time_is_uncertified_assumption')
    return {
        'certified_full_max_wave_model': False,
        'model_certification_status': 'partial_boss_contact_model',
        'certified_scope': 'boss_contact_survivability_with_explicit_runtime_overrides',
        'model_completion_blockers': blockers,
        'runtime_override_closure': {
            'non_boss_terminal_pressure': _boss_wave_explicit_terminal_pressure_closed(runtime_inputs),
            'v28_damage_health_decay_magnitudes': _boss_wave_explicit_damage_health_decay_closed(runtime_inputs),
            'gc_boss_applicable_damage_semantics': _boss_wave_explicit_gc_bridge_closed(
                runtime_inputs,
                gc_boss_damage_source=gc_boss_damage_source,
            ),
        },
        'model_requirement_applicability': {
            'non_boss_terminal_pressure': False,
            'v28_damage_health_decay_magnitudes': bool(damage_health_decay_required),
            'gc_boss_applicable_damage_semantics': bool(gc_boss_applicable_damage_required),
        },
        'explicit_runtime_overrides_supported': [
            'boss_time_to_contact_seconds',
            'orb_boss_total_damage_pct',
            'boss_applicable_damage_per_second',
            'boss_applicable_damage_factor',
            'boss_edamage_target_share',
            'boss_edamage_cadence_uptime_factor',
            'boss_edamage_reliability_factor',
            'boss_edamage_semantic_normalizer',
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


def _boss_wave_loadout_type(perk_policy_preset: str | None) -> str:
    policy = str(perk_policy_preset or '').strip().lower()
    if 'farming' in policy or policy.endswith(' farm'):
        return 'farm'
    if policy.startswith('gc '):
        return 'gc'
    if policy.startswith('ehp '):
        return 'ehp'
    return 'loadout'


def _bounded_boss_wave_pct(value: object) -> float:
    try:
        raw = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if raw <= 0.0:
        return 0.0
    return min(100.0, raw) / 100.0


def _boss_wave_contact_time_seconds(
    runtime_inputs: ScenarioRuntimeInputs,
    *,
    primitives: Mapping[str, object],
) -> tuple[float, str, dict[str, float]]:
    explicit_contact_time = getattr(runtime_inputs, 'boss_time_to_contact_seconds')
    if explicit_contact_time is not None:
        contact_time = max(0.0, float(explicit_contact_time))
        return (
            contact_time,
            'runtime_input_boss_time_to_contact_seconds',
            {
                'base_seconds': 2.0,
                'chrono_field_average_slow_fraction': 0.0,
                'slow_aura_fraction': 0.0,
                'speed_remaining_fraction': 1.0,
                'energy_net_hold_seconds': 0.0,
            },
        )
    base_seconds = 2.0
    cf_duration = max(0.0, float(primitives.get('chrono_field_duration_seconds') or 0.0))
    cf_cooldown = max(0.0, float(primitives.get('chrono_field_cooldown_seconds') or 0.0))
    cf_uptime = min(1.0, cf_duration / cf_cooldown) if cf_duration > 0.0 and cf_cooldown > 0.0 else 0.0
    cf_average_slow = _bounded_boss_wave_pct(primitives.get('chrono_field_slow_pct')) * cf_uptime
    slow_aura = _bounded_boss_wave_pct(primitives.get('slow_aura_enemy_speed_pct'))
    speed_remaining = max(0.01, (1.0 - cf_average_slow) * (1.0 - slow_aura))
    energy_net_hold = max(0.0, float(primitives.get('energy_net_duration_seconds') or 0.0))
    contact_time = (base_seconds / speed_remaining) + energy_net_hold
    return (
        contact_time,
        'derived_base_2s_cf_slow_aura_energy_net',
        {
            'base_seconds': base_seconds,
            'chrono_field_average_slow_fraction': cf_average_slow,
            'slow_aura_fraction': slow_aura,
            'speed_remaining_fraction': speed_remaining,
            'energy_net_hold_seconds': energy_net_hold,
        },
    )


def _boss_wave_spotlight_coverage(*, count: object, angle_degrees: object) -> float:
    try:
        count_value = max(0.0, float(count or 0.0))
        angle_value = max(0.0, float(angle_degrees or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, (count_value * angle_value) / 360.0)


def _boss_wave_acp_active_fraction(*, contact_time_seconds: object, shockwave_interval_seconds: object) -> tuple[float, float]:
    try:
        contact_time = max(0.0, float(contact_time_seconds or 0.0))
        shockwave_interval = max(0.0, float(shockwave_interval_seconds or 0.0))
    except (TypeError, ValueError):
        return 0.0, 0.0
    if contact_time <= 0.0 or shockwave_interval <= 0.0:
        return 0.0, 0.0
    hit_probability = min(1.0, contact_time / shockwave_interval)
    # ACP lasts 7s after a Shockwave hit; Boss Waves models this as expected uptime
    # over the boss travel/contact window with random Shockwave phase.
    active_fraction = min(1.0, hit_probability * min(1.0, 7.0 / contact_time))
    return hit_probability, active_fraction


def _positive_factor(value: object, *, default: float = 1.0) -> float:
    try:
        factor = float(value or 0.0)
    except (TypeError, ValueError):
        return default
    return factor if factor > 0.0 else default


def _boss_wave_hit_interval_seconds(
    runtime_inputs: ScenarioRuntimeInputs,
    *,
    scenario_surfaces: Mapping[str, object],
    primitives: Mapping[str, object],
) -> tuple[float, str, dict[str, float]]:
    explicit_hit_interval = getattr(runtime_inputs, 'boss_hit_interval_seconds')
    if explicit_hit_interval is not None:
        return (
            max(0.0, float(explicit_hit_interval)),
            'runtime_input_boss_hit_interval_seconds',
            {
                'scenario_base_seconds': float(scenario_surfaces.get('boss_hit_interval_seconds') or 2.0),
                'slow_aura_mastery_attack_interval_multiplier': 1.0,
            },
        )
    scenario_base = max(0.0, float(scenario_surfaces.get('boss_hit_interval_seconds') or 2.0))
    slow_aura_mastery_multiplier = _positive_factor(
        primitives.get('slow_aura_mastery_attack_interval_multiplier'),
        default=1.0,
    )
    return (
        scenario_base * slow_aura_mastery_multiplier,
        'scenario_boss_hit_interval_plus_slow_aura_mastery',
        {
            'scenario_base_seconds': scenario_base,
            'slow_aura_mastery_attack_interval_multiplier': slow_aura_mastery_multiplier,
        },
    )


def _boss_wave_apply_pre_contact_damage_window_diagnostics(primitives: dict[str, object]) -> None:
    damage_per_second = max(0.0, float(primitives.get('gc_boss_damage_per_second') or 0.0))
    contact_seconds = max(0.0, float(primitives.get('boss_time_to_contact_seconds') or 0.0))
    base_contact_seconds = max(0.0, float(primitives.get('boss_time_to_contact_base_seconds') or 0.0))
    energy_net_hold_seconds = max(0.0, float(primitives.get('boss_time_to_contact_energy_net_hold_seconds') or 0.0))
    movement_seconds = max(0.0, contact_seconds - energy_net_hold_seconds)
    energy_net_multiplier = _positive_factor(primitives.get('energy_net_mastery_multiplier'))
    energy_net_multiplier_window = max(
        0.0,
        float(primitives.get('energy_net_damage_multiplier_duration_seconds') or 0.0),
    )
    boosted_seconds = min(contact_seconds, energy_net_multiplier_window) if energy_net_multiplier > 1.0 else 0.0
    base_window_damage = damage_per_second * contact_seconds
    energy_net_incremental_damage = damage_per_second * max(0.0, energy_net_multiplier - 1.0) * boosted_seconds
    primitives['edamage_boss_contact_time_exposure_factor'] = (
        contact_seconds / base_contact_seconds if base_contact_seconds > 0.0 else 1.0
    )
    primitives['edamage_boss_movement_time_exposure_factor'] = (
        movement_seconds / base_contact_seconds if base_contact_seconds > 0.0 else 1.0
    )
    primitives['edamage_boss_pre_contact_base_window_damage'] = base_window_damage
    primitives['edamage_boss_pre_contact_energy_net_boosted_seconds'] = boosted_seconds
    primitives['edamage_boss_pre_contact_energy_net_incremental_damage'] = energy_net_incremental_damage
    primitives['edamage_boss_pre_contact_timed_window_damage'] = (
        base_window_damage + energy_net_incremental_damage
    )


def _boss_wave_apply_default_edamage_boss_runtime_factors(primitives: dict[str, object]) -> None:
    source = str(primitives.get('gc_boss_damage_source') or '')
    ep_damage = max(0.0, float(primitives.get('edamage_ep') or 0.0))
    cl_base_dps = max(0.0, float(primitives.get('qe_boss_applicable_cl_only_damage_per_second') or 0.0))
    base_dps = ep_damage if ep_damage > 0.0 else cl_base_dps
    primitives['edamage_boss_base_damage_per_second'] = base_dps
    primitives['edamage_boss_base_ep_damage'] = ep_damage
    primitives['edamage_boss_base_cl_damage_per_second'] = cl_base_dps
    if source != 'qe_derived_edamage_boss_fail_closed_default':
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
        primitives['edamage_boss_damage_per_second'] = float(primitives.get('gc_boss_damage_per_second') or 0.0)
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
    shockwave_hit_probability, acp_active_fraction = _boss_wave_acp_active_fraction(
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
    primitives['gc_boss_damage_per_second'] = final_dps
    primitives['gc_boss_damage_source'] = 'qe_derived_edamage_ep_boss_exposure_model'
    _boss_wave_apply_pre_contact_damage_window_diagnostics(primitives)


def _boss_wave_replacement_primitive_surface_ids(account_state, *, preset_name: str) -> tuple[str, ...]:
    surface_ids = list(BOSS_WAVE_REPLACEMENT_PRIMITIVE_SURFACE_IDS)
    equipped_cards = set((getattr(account_state, 'card_presets', {}) or {}).get(preset_name, []) or [])
    if 'Slow Aura' in equipped_cards:
        surface_ids.extend(BOSS_WAVE_OPTIONAL_PRIMITIVE_SURFACE_IDS)
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


def _resolve_boss_wave_run_context(
    account_state,
    *,
    preset_name: str,
    tier_number: int,
    checkpoint_every_bosses: int,
) -> dict[str, object]:
    from simulators.scenario import ScenarioConfig, compute_scenario_surfaces

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
            _extract_optional_wave_number(account_state.player_meta.get('Tournament Wave'))
            or _extract_optional_wave_number(account_state.player_meta.get('Tourney Wave'))
        )
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
                'checkpoint_every_bosses': max(1, int(checkpoint_every_bosses)),
                'context_error': 'missing_tournament_wave',
                'context_error_message': 'Boss Waves Tourney mode requires a resolved tournament wave. This repo baseline does not ship that context for the active account snapshot.',
            }
        scenario_config = ScenarioConfig(
            mode_id='tournament',
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
        'tier_number': int(tier_number),
        'tier_column': f'Tier {int(tier_number)}',
        'league': scenario_config.league,
        'tournament_wave': int(scenario_config.tournament_wave or 0) or None,
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
    config = {
        'execution_mode': 'table_sweep',
        'preset_name': preset_name,
        'mode_id': str(resolved_context.get('mode_id') or 'farming'),
        'tier_number': int(resolved_context.get('tier_number') or tier_number),
        'tier_column': str(resolved_context.get('tier_column') or f'Tier {int(tier_number)}'),
        'league': resolved_context.get('league'),
        'tournament_wave': int(resolved_context.get('tournament_wave') or 0),
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
        'perk_policy_preset': str(perk_policy.get('_selected_policy_preset') or ''),
        'loadout_profile_preset': _boss_wave_loadout_profile_preset(
            boss_preset_name=preset_name,
            perk_policy_preset=str(perk_policy.get('_selected_policy_preset') or ''),
        ),
        'perk_contract_owner': perk_contract_owner,
        'perk_mode_source': perk_mode_source,
        'perk_state_source': perk_state_source,
        'perk_request_resolution': perk_request_resolution,
        'perk_application_mode': perk_application_mode,
        'perk_config_resolution': dict(perk_config_resolution),
        'perk_policy_validation': dict(perk_policy_validation),
        'account_state_cache_hit': bool(account_state_cache_hit),
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
    tower_damage_mode = 'v21_event_plus_gc_boss_continuous_damage'
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
            'gc_pre_contact_max_wave': int(selected_summary.get('gc_pre_contact_max_wave') or 0),
            'gc_pre_contact_first_failed_wave': int(selected_summary.get('gc_pre_contact_first_failed_wave') or 0),
            'gc_pre_contact_max_independent_wave': int(selected_summary.get('gc_pre_contact_max_independent_wave') or 0),
            'gc_pre_contact_model': selected_summary.get('gc_pre_contact_model'),
            'terminal_pressure_limits': dict(selected_summary.get('terminal_pressure_limits') or {}),
            'terminal_pressure_limiter': selected_summary.get('terminal_pressure_limiter'),
            'terminal_pressure_limited': bool(selected_summary.get('terminal_pressure_limited')),
            'row_count': int(selected_summary.get('row_count') or len(operator_rows)),
            'terminal_display_wave': int(selected_summary.get('terminal_display_wave') or 0),
            'survives_through_end': bool(selected_summary.get('survives_through_end')),
            'contact_envelope_survives_through_end': bool(selected_summary.get('contact_envelope_survives_through_end')),
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
                'gc_pre_contact_max_wave': int(summary.get('gc_pre_contact_max_wave') or 0),
                'status': summary.get('status') or diagnostics.get('context_status') or 'complete',
                'post_failure_truncation_kind': summary.get('post_failure_truncation_kind'),
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
    requirement_applicability = dict(certification.get('model_requirement_applicability') or {})
    requirement_applicability['non_boss_terminal_pressure'] = False
    requirement_applicability['v28_damage_health_decay_magnitudes'] = (
        'source_owned_v28_damage_health_decay_magnitudes' in blockers
    )
    requirement_applicability['gc_boss_applicable_damage_semantics'] = (
        'source_owned_full_gc_boss_applicable_damage_semantics' in blockers
    )
    certification['model_requirement_applicability'] = requirement_applicability
    return certification


def _boss_wave_matrix_comparison_inputs_from_args(args) -> dict[str, float] | None:
    mapping = {
        'boss_wave_bridge_target_share': 'boss_edamage_target_share',
        'boss_wave_bridge_cadence_uptime': 'boss_edamage_cadence_uptime_factor',
        'boss_wave_bridge_reliability': 'boss_edamage_reliability_factor',
        'boss_wave_bridge_semantic_normalizer': 'boss_edamage_semantic_normalizer',
    }
    values: dict[str, float] = {}
    for arg_name, runtime_name in mapping.items():
        value = float(getattr(args, arg_name, 0.0) or 0.0)
        if value > 0.0:
            values[runtime_name] = value
    return values or None


def _boss_wave_matrix_runtime_inputs_from_args(args) -> dict[str, float] | None:
    mapping = {
        'boss_wave_contact_time_seconds': 'boss_time_to_contact_seconds',
        'boss_wave_orb_boss_total_damage_pct': 'orb_boss_total_damage_pct',
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
        str(config.get('league') or ''),
        int(config.get('tournament_wave') or 0),
        bool(perks_enabled),
        str(config.get('dissonance_run_category') or 'none'),
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
    perk_mode: str,
    perk_policy_preset: str | None,
):
    cache_key = (
        _path_cache_token(ids_path),
        _path_cache_token(_effective_manual_inputs_path(manual_inputs_path)),
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
    account_state = build_runtime_state(
        input_bundle.ids_raw,
        loadout_config=input_bundle.loadout_config,
        perk_config=perk_config,
    )
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


def _select_summary_lane(summary: dict[str, object], *, prefix: str, model: str) -> None:
    max_key = f'{prefix}_max_wave'
    failed_key = f'{prefix}_first_failed_wave'
    independent_key = (
        f'{prefix}_max_independent_surviving_wave'
        if prefix == 'contact_envelope'
        else f'{prefix}_max_independent_wave'
    )
    summary.update(
        {
            'selected_max_wave': int(summary.get(max_key) or 0),
            'selected_first_failed_wave': int(summary.get(failed_key) or 0),
            'selected_max_independent_wave': int(summary.get(independent_key) or 0),
            'selected_model': model,
        }
    )


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

    categories = tuple(_normalize_boss_wave_dissonance_run_category(category) for category in dissonance_run_categories)
    policy_presets = tuple(loadout_policy_presets)
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
                candidates.append(
                    {
                        'loadout_policy_preset': str(policy_preset),
                        'loadout_profile_preset': diagnostics.get('loadout_profile_preset'),
                        'selected_loadout_type': summary.get('selected_loadout_type') or diagnostics.get('selected_loadout_type'),
                        'selected_model': summary.get('selected_model'),
                        'selected_max_wave': selected_wave,
                        'selected_first_failed_wave': int(summary.get('selected_first_failed_wave') or 0),
                        'hit_by_hit_max_wave': int(summary.get('hit_by_hit_max_wave') or 0),
                        'contact_envelope_max_wave': int(summary.get('contact_envelope_max_wave') or 0),
                        'gc_pre_contact_max_wave': int(summary.get('gc_pre_contact_max_wave') or 0),
                        'gc_boss_damage_source': primitive_values.get('gc_boss_damage_source'),
                        'status': summary.get('status') or diagnostics.get('context_status') or 'complete',
                        'model_certification_status': dict(
                            diagnostics.get('model_certification') or matrix_model_certification
                        ).get('model_certification_status'),
                        'certified_full_max_wave_model': bool(
                            dict(diagnostics.get('model_certification') or matrix_model_certification).get(
                                'certified_full_max_wave_model'
                            )
                        ),
                        'model_completion_blockers': list(
                            dict(diagnostics.get('model_certification') or matrix_model_certification).get(
                                'model_completion_blockers'
                            )
                            or []
                        ),
                        'survives_through_end': bool(summary.get('survives_through_end')),
                        'contact_envelope_survives_through_end': bool(summary.get('contact_envelope_survives_through_end')),
                        'gc_pre_contact_survives_through_end': bool(summary.get('gc_pre_contact_survives_through_end')),
                        'post_failure_truncation_kind': summary.get('post_failure_truncation_kind'),
                        'reference_kind': milestone_alignment.get('active_reference_kind'),
                        'reference_source': milestone_alignment.get('active_reference_source'),
                        'reference_wave': active_reference_wave,
                        'dissonance_pb_reference_wave': milestone_alignment.get('dissonance_pb_reference_wave'),
                        'delta_vs_reference_wave': delta_vs_reference_wave,
                        'alignment': milestone_alignment,
                    }
                )

            best = max(candidates, key=lambda row: _boss_wave_milestone_matrix_selection_rank(row, policy_presets))
            category_label = _BOSS_WAVE_DISSONANCE_RUN_LABELS[category]
            category_key = 'regular' if category == 'none' else category
            best_wave = int(best.get('selected_max_wave') or 0)
            best_reference_wave = _extract_optional_wave_number(best.get('reference_wave'))
            best_gc_boss_damage_source = (
                best.get('gc_boss_damage_source')
                if str(best.get('selected_loadout_type') or '') == 'gc'
                else None
            )
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
                'dissonance_pb_reference_wave': best.get('dissonance_pb_reference_wave'),
                'best_selected_max_wave': best_wave,
                'best_loadout_policy_preset': best.get('loadout_policy_preset'),
                'best_loadout_profile_preset': best.get('loadout_profile_preset'),
                'best_selected_loadout_type': best.get('selected_loadout_type'),
                'best_selected_model': best.get('selected_model'),
                'best_gc_boss_damage_source': best_gc_boss_damage_source,
                'best_status': best.get('status'),
                'best_model_certification_status': best.get('model_certification_status'),
                'certified_full_max_wave_model': bool(best.get('certified_full_max_wave_model')),
                'model_completion_blockers': list(best.get('model_completion_blockers') or []),
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
            wide[f'{category_key}_best_loadout'] = best.get('loadout_policy_preset')
            wide[f'{category_key}_best_model'] = best.get('selected_model')
            wide[f'{category_key}_best_gc_boss_damage_source'] = best_gc_boss_damage_source
            wide[f'{category_key}_status'] = best.get('status')
            wide[f'{category_key}_model_certification_status'] = best.get('model_certification_status')
            wide[f'{category_key}_certified_full_max_wave_model'] = bool(best.get('certified_full_max_wave_model'))
            wide[f'{category_key}_display'] = row['best_display']
            wide[f'{category_key}_reference_kind'] = best.get('reference_kind')
            wide[f'{category_key}_reference_wave'] = best_reference_wave
            wide[f'{category_key}_delta_vs_reference_wave'] = row.get('delta_vs_reference_wave')
        wide['milestone_reference_wave'] = tier_reference_wave
        wide_rows.append(wide)

    selected_model_certification = _boss_wave_matrix_certification_from_selected_rows(
        matrix_model_certification,
        rows,
    )
    payload = {
        'artifact': 'boss_wave_milestone_matrix',
        'schema_version': 1,
        'contract': {
            'payload_owner': 'app.pipeline.build_boss_wave_milestone_matrix',
            'row_owner': 'app.pipeline.build_boss_wave_payload',
            'simulator_owner': 'simulators.evaluator_kernel.evaluate_overlay_row',
            'scope': 'milestone_all_tiers_best_loadout_by_dissonant_run_category',
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification': selected_model_certification,
            'selection_policy': 'complete candidates first, then highest selected_max_wave across named loadout presets',
        },
        'preset_name': 'Milestone',
        'tiers': [int(tier) for tier in tiers],
        'end_wave': int(end_wave),
        'boss_wave_step': int(boss_wave_step),
        'stop_on_failure': bool(stop_on_failure),
        'scenario_runtime_inputs': runtime_inputs,
        'scenario_runtime_input_sources': runtime_input_sources,
        'model_certification': selected_model_certification,
        'contact_time_contract': {
            'boss_time_to_contact_seconds': {
                'value': runtime_inputs.get('boss_time_to_contact_seconds'),
                'source': runtime_input_sources.get(
                    'boss_time_to_contact_seconds',
                    'per_candidate_derived_base_2s_cf_slow_aura_energy_net',
                ),
                'ownership': 'runtime_input_override_or_per_candidate_simulator_derivation',
                'derived_by_simulator': 'boss_time_to_contact_seconds' not in runtime_inputs,
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
            comparison_rows.append(comparison_row)
        payload['comparison'] = {
            'label': str(comparison_label or 'bridge_assumptions'),
            'scenario_runtime_inputs': comparison_runtime_inputs,
            'matrix': comparison_matrix,
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
    wall_thorns_damage_increase_per_hit = _boss_wave_wall_thorns_damage_increase_per_hit(
        account_state,
        preset_name=loadout_profile_preset,
    )
    if 'wall_thorns_damage_increase_per_hit' in primitives:
        wall_thorns_damage_increase_per_hit = max(
            0.0,
            float(primitives['wall_thorns_damage_increase_per_hit'] or 0.0),
        )
    boss_time_to_contact_seconds, boss_time_to_contact_source, boss_time_to_contact_components = (
        _boss_wave_contact_time_seconds(runtime_inputs, primitives=primitives)
    )
    boss_hit_interval_seconds, boss_hit_interval_source, boss_hit_interval_components = _boss_wave_hit_interval_seconds(
        runtime_inputs,
        scenario_surfaces=scenario_surfaces,
        primitives=primitives,
    )
    primitives['boss_time_to_contact_seconds'] = boss_time_to_contact_seconds
    primitives['boss_time_to_contact_source'] = boss_time_to_contact_source
    primitives['boss_time_to_contact_base_seconds'] = boss_time_to_contact_components['base_seconds']
    primitives['boss_time_to_contact_chrono_field_average_slow_fraction'] = boss_time_to_contact_components[
        'chrono_field_average_slow_fraction'
    ]
    primitives['boss_time_to_contact_slow_aura_fraction'] = boss_time_to_contact_components['slow_aura_fraction']
    primitives['boss_time_to_contact_speed_remaining_fraction'] = boss_time_to_contact_components[
        'speed_remaining_fraction'
    ]
    primitives['boss_time_to_contact_energy_net_hold_seconds'] = boss_time_to_contact_components[
        'energy_net_hold_seconds'
    ]
    primitives['boss_hit_interval_seconds'] = boss_hit_interval_seconds
    primitives['boss_hit_interval_source'] = boss_hit_interval_source
    primitives['boss_hit_interval_scenario_base_seconds'] = boss_hit_interval_components['scenario_base_seconds']
    primitives['boss_hit_interval_slow_aura_mastery_multiplier'] = boss_hit_interval_components[
        'slow_aura_mastery_attack_interval_multiplier'
    ]
    _boss_wave_apply_default_edamage_boss_runtime_factors(primitives)
    scenario = ScenarioOverlayInputs(
        scenario_key='boss_waves_replacement_product',
        tier_column=str(config['tier_column']),
        tournament_perks_enabled=True,
        tower_damage_decay_start_wave=tower_damage_decay_start_wave if tower_damage_decay_fraction > 0.0 else 0,
        tower_damage_decay_fraction_per_step=tower_damage_decay_fraction,
        tower_damage_decay_interval_waves=10,
        tower_health_decay_start_wave=tower_health_decay_start_wave if tower_health_decay_fraction > 0.0 else 0,
        tower_health_decay_fraction_per_step=tower_health_decay_fraction,
        tower_health_decay_interval_waves=10,
        survivability_transforms=ScenarioSurvivabilityTransforms(
            incoming_damage_multiplier=incoming_mult,
        ),
    )
    combat = CombatInputs(
        plasma_cannon_effect_pct=float(primitives['plasma_cannon_effect_pct']),
        tower_thorns_damage_pct=float(primitives['wall_thorns_contact_damage_pct']),
        continuous_boss_damage_per_second=float(primitives.get('gc_boss_damage_per_second') or 0.0),
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
        operator_rows.append(
            _replacement_operator_row_from_overlay(
                overlay=overlay,
                active_source=active_source,
                combat=combat,
                incoming_damage_multiplier=incoming_mult,
            )
        )
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
    scenario_context = {
        'mode_id': str(config.get('mode_id') or 'farming'),
        'tier': int(config.get('tier_number') or 1),
        'league': config.get('league'),
        'tournament_wave': config.get('tournament_wave'),
        'dissonance_run_category': str(config.get('dissonance_run_category') or 'none'),
    }
    primitive_surface_ids = _boss_wave_replacement_primitive_surface_ids(
        account_state,
        preset_name=primitive_preset_name,
    )
    response = resolve_checkpoint_surfaces(
        account_state,
        requested_surface_ids=primitive_surface_ids,
        preset_name=primitive_preset_name,
        card_preset_name=primitive_preset_name,
        module_preset_name=primitive_preset_name,
        state_mode='start_of_run',
        perks_enabled=False,
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs),
        scenario_context=scenario_context,
    )
    statbook = query_response_to_statbook(response, notes='Boss Waves replacement primitive resolution.')
    dissonance_run_category = _normalize_boss_wave_dissonance_run_category(
        config.get('dissonance_run_category') or 'none'
    )
    publish_query_surfaces(statbook.rows, account_state_labs=getattr(account_state, 'labs', {}) or {})
    damage_statbook = statbook
    damage_state_mode = 'start_of_run'
    damage_perks_enabled = False
    if bool(perks_enabled):
        damage_response = resolve_checkpoint_surfaces(
            account_state,
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
        publish_query_surfaces(damage_statbook.rows, account_state_labs=getattr(account_state, 'labs', {}) or {})
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
    energy_net_damage_multiplier_duration_seconds = (
        max(0.0, energy_net_duration_seconds) + 10.0
        if energy_net_duration_seconds > 0.0 and energy_net_mastery_multiplier > 1.0
        else 0.0
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
    scenario_config = config.get('scenario_config')
    if scenario_config is None:
        scenario_config = ScenarioConfig(
            mode_id=str(config.get('mode_id') or 'farming'),
            tier=int(config.get('tier_number') or 1),
            league=config.get('league'),
            tournament_wave=(int(config.get('tournament_wave') or 0) or None),
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
        timing_family_id = 'timing_tournament_no_perks' if str(config.get('mode_id') or '') == 'tournament' else 'timing_scenario_probe'
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
    return {
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
        'edamage_attack_dissonance_restricted': _optional_statbook_float(statbook, 'derived::edamage.attack_dissonance_restricted', default=0.0),
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
        'gc_boss_damage_per_second': gc_boss_damage_per_second,
        'gc_boss_damage_source': gc_boss_damage_source,
        'energy_net_duration_seconds': energy_net_duration_seconds,
        'energy_net_mastery_multiplier': energy_net_mastery_multiplier,
        'energy_net_damage_multiplier_duration_seconds': energy_net_damage_multiplier_duration_seconds,
        'spotlight_bonus_multiplier': spotlight_bonus_multiplier,
        'spotlight_count': spotlight_count,
        'spotlight_angle_degrees': spotlight_angle_degrees,
        'om_chip_equipped': om_chip_equipped,
        'anti_cube_portal_shockwave_damage_taken_mult_x': anti_cube_portal_shockwave_damage_taken_mult_x,
        'orbital_augment_electron_count': _optional_statbook_float(statbook, 'state::module.orbital_augment.electron_count', default=0.0),
        'primordial_collapse_bh_damage_reduction_pct': _optional_statbook_float(statbook, 'state::module.primordial_collapse.bh_damage_reduction_pct', default=0.0),
        'black_hole_duration_seconds': black_hole_duration_seconds,
        'black_hole_cooldown_seconds': black_hole_cooldown_seconds,
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
            'state_mode': 'start_of_run_static_primitives_plus_row_evolved_workshop_skip_state',
            'primitive_resolution_owner': 'qe.routing.resolve_checkpoint_surfaces (split by ownership)',
            'table1_owner': 'qe.run_plan',
            'table2_owner': 'simulators.evaluator_kernel',
            'product_render_owner': 'app.streamlit_inspector consumes operator_rows',
        },
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
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::wall.regen)',
                'canonical_truth_source': 'formula_surface_policy state::wall.regen',
                'semantic_meaning': 'QE-published wall regen percent-points primitive; Boss Waves combines it with resolved tower regen for displayed HP/sec',
                'exact_value': float(primitives['wall_regen_percent_points']),
                'primitive_vs_displayed': 'partial_primitive_input_not_displayed_directly',
                'fortification_transform': 'not_fortification_scaled',
                'state_phase': 'start_of_run',
                'row_evolution': 'Table 1 can rederive if an owned wall-regen workshop primitive changes',
                'owner_layer': 'QE publishes tower_regen and wall_regen percent primitive; app assembles primitive bundle; run_plan row-rederives; evaluator applies scenario wall_regen transforms',
                'classification': 'transformed',
                'boss_waves_semantic_decision': 'transformed_percent_points_primitive_not_final_hp_per_second',
                'boss_waves_final_display_field': 'operator_rows.wall_regen',
                'repo_wide_rename_or_split': 'defer_followup_if_needed; Boss Waves contract is explicit and does not treat state::wall.regen as final displayed HP/sec',
                'row_input_value': float(row_input_wall_regen),
            },
            'state::tower.regen': {
                'boss_waves_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.regen)',
                'canonical_truth_source': 'qe.routing.resolve_checkpoint_surfaces(state::tower.regen)',
                'semantic_meaning': 'QE-published resolved tower regen HP/sec used as the base for wall regen',
                'exact_value': float(primitives['tower_regen']),
                'primitive_vs_displayed': 'primitive_input_transform_for_wall_regen',
                'fortification_transform': 'none',
                'state_phase': 'start_of_run',
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
            'state::combat.gc_boss_damage_per_second': _primitive_ledger_entry(
                source=str(primitives.get('gc_boss_damage_source') or ''),
                value=float(primitives.get('gc_boss_damage_per_second') or 0.0),
                meaning='Final continuous boss damage used by the GC/pre-contact lane. Defaults to derived::edamage_ep with EP Spotlight, ACP, and slow/exposure factors replaced by Boss Waves runtime equivalents; it can still be explicitly overridden or bridged from derived::edamage_ep by caller-owned factors.',
                owner='app selects explicit runtime scenario input or QE-owned eDamage with Boss Waves exposure replacements; evaluator integrates the final continuous damage value event-by-event',
            ),
            'state::combat.edamage_boss_runtime_factor': _primitive_ledger_entry(
                source='app.pipeline._boss_wave_apply_default_edamage_boss_runtime_factors',
                value=float(primitives.get('edamage_boss_runtime_factor') or 1.0),
                meaning='Boss Waves default replacement multiplier applied to QE derived::edamage_ep. It removes EP Spotlight, ACP, and slow/exposure factors, then applies Boss Waves Spotlight/Om Chip and travel-window ACP factors. EN mastery remains a separate timed TTK multiplier.',
                owner='app assembles scenario/loadout runtime exposure replacements; QE remains the base eDamage source and evaluator consumes the final continuous damage primitive',
            ),
            'state::combat.edamage_boss_pre_contact_timed_window_damage': _primitive_ledger_entry(
                source='app.pipeline._boss_wave_apply_pre_contact_damage_window_diagnostics',
                value=float(primitives.get('edamage_boss_pre_contact_timed_window_damage') or 0.0),
                meaning='Diagnostic total continuous boss damage available before contact from final boss DPS over boss travel/contact time, with Energy Net mastery applied only for its timed window. CF and Slow Aura contribute through contact time rather than as a DPS multiplier.',
                owner='app publishes diagnostic budget; evaluator remains the authoritative TTK integrator',
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
                meaning='QE-published Flame Bot DR track value after the _IDS bot owned flag is applied. Boss Waves combines this with a manual Flame Bot boss-hit chance runtime surface for average expected DR, or with explicit duration/cooldown if those runtime primitives are supplied.',
                owner='QE publishes bot owned flag and gated DR track; app assembles average or timed DR semantics from explicit runtime inputs',
            ),
            'state::bot.flame.cooldown_seconds': _primitive_ledger_entry(
                source='qe.routing.resolve_checkpoint_surfaces(state::bot.flame.cooldown_seconds)',
                value=float(primitives.get('flame_bot_cooldown_seconds') or 0.0),
                meaning='QE-published Flame Bot cooldown. Boss Waves uses it only when explicit duration/cooldown timed-DR runtime inputs are supplied; average boss-hit-chance modeling does not consume cooldown.',
                owner='QE publishes bot track; app selects average or timed DR semantics from explicit runtime inputs',
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
            'policy': 'displayed Wall Regen = resolved tower regen HP/sec * QE wall regen percent-points primitive / 100',
        },
        'boss_waves_wall_surface_semantic_contract': {
            'state::wall.hp': {
                'decision': 'transformed_primitive_not_final_display_value',
                'product_value': 'operator_rows.wall_pre_fort_hp is pre-fort row-derived HP; operator_rows.wall_hp is fortified Wall HP',
                'fortification_policy': 'state::wall.fortification_multiplier is applied exactly once by evaluator TTD to produce displayed Wall HP',
            },
            'state::wall.regen': {
                'decision': 'transformed_percent_points_primitive_not_final_hp_per_second',
                'product_value': 'operator_rows.wall_regen is tower_regen * state::wall.regen / 100 after owned row/scenario transforms',
                'fortification_policy': 'not fortification-scaled',
            },
        },
        'timed_dr_semantic_contract': {
            'owner_layer': 'app assembles explicit runtime primitives; run_plan carries staged timed DR primitives and CF/BH duration perk contributions; evaluator combines DR multiplicatively per row',
            'lane_policy': 'same average uptime contribution is applied to min/avg/max until a lane-specific encounter model is owned',
            'sources': dict(timed_dr_sources),
            'perk_duration_contributions': {
                'PERK_BLACK_HOLE_DURATION_12_0S': 'black_hole_duration_seconds_add',
                'PERK_CHRONO_FIELD_DURATION_5S': 'chrono_field_duration_seconds_add',
            },
            'concern': 'KB de-scopes exact same-tick Flame Bot overlap and PBH/BH encounter micro-precedence; current path models explicit average overlap, not frame-accurate overlap. Flame Bot uses manual boss-hit chance times Flame Bot DR for expected average DR, or explicit runtime duration/cooldown if supplied; no owned Defense Field primitive was found in the active repo.',
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
        'gc_pre_contact_max_wave': gc_pre_contact['last_contiguous_surviving_wave'],
        'gc_pre_contact_first_failed_wave': gc_pre_contact['first_failed_wave'],
        'gc_pre_contact_max_independent_wave': gc_pre_contact['max_independent_surviving_wave'],
        'gc_pre_contact_model': 'boss_ttk_seconds_less_than_or_equal_to_boss_time_to_contact_seconds',
        'row_count': len(operator_rows),
        'terminal_display_wave': terminal,
        'survives_through_end': bool(operator_rows) and hit_by_hit['first_failed_wave'] == 0,
        'contact_envelope_survives_through_end': bool(operator_rows) and contact_envelope['first_failed_wave'] == 0,
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
    certification_gc_boss_damage_source = str((primitive_inputs or {}).get('gc_boss_damage_source') or '')
    certification_payload = _boss_wave_model_certification_payload(
        contact_time_source=dict(config.get('scenario_runtime_input_sources') or {}).get(
            'boss_time_to_contact_seconds'
        ),
        runtime_inputs=certification_runtime_inputs,
        gc_boss_damage_source=certification_gc_boss_damage_source,
        damage_health_decay_required=str(config.get('mode_id') or '') == 'tournament',
        gc_boss_applicable_damage_required=_boss_wave_selected_model_requires_full_gc_bridge(
            selected_model=summary.get('selected_model'),
            gc_boss_damage_source=certification_gc_boss_damage_source,
        ),
    )
    return {
        'preset_name': preset_name,
        'mode_id': config['mode_id'],
        'tier_number': int(config['tier_number']),
        'tier_column': config['tier_column'],
        'league': config.get('league'),
        'tournament_wave': int(config.get('tournament_wave') or 0) or None,
        'perks_enabled': bool(config['perks_enabled']),
        'perk_mode': str(config.get('perk_mode') or ''),
        'perk_state': str(config.get('perk_state') or ''),
        'requested_perk_mode': str(config.get('requested_perk_mode') or ''),
        'requested_perk_state': str(config.get('requested_perk_state') or ''),
        'requested_perk_policy_preset': str(config.get('requested_perk_policy_preset') or ''),
        'perk_policy_preset': str(config.get('perk_policy_preset') or ''),
        'loadout_profile_preset': str(config.get('loadout_profile_preset') or ''),
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
        'model_scope': 'boss_contact_survivability',
        'not_full_max_wave_model': True,
        'model_certification': certification_payload,
        'unsupported_terminal_pressures': [],
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
                'chrono_field_average_slow_fraction': (primitive_inputs or {}).get(
                    'boss_time_to_contact_chrono_field_average_slow_fraction'
                ),
                'slow_aura_fraction': (primitive_inputs or {}).get('boss_time_to_contact_slow_aura_fraction'),
                'speed_remaining_fraction': (primitive_inputs or {}).get(
                    'boss_time_to_contact_speed_remaining_fraction'
                ),
                'energy_net_hold_seconds': (primitive_inputs or {}).get(
                    'boss_time_to_contact_energy_net_hold_seconds'
                ),
            },
        },
        'scenario_surfaces': dict(config.get('scenario_surfaces') or {}),
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
            'boss_ttk_contract': 'v21_events_plus_gc_boss_continuous_damage',
            'boss_kill_sources': ['plasma_cannon', 'orbs', 'electrons', 'gc_boss_continuous_damage', 'thorns_contact'],
            'contact_resolution_sources': ['wall_thorns_contact'],
            'thorns_contact_source': 'wall_thorns_contact_damage_pct_derived_from_tower_thorns_and_wall_thorns_lab',
            'wall_thorns_repeated_hit_multiplier': 'Sharp Fortitude primary armor adds +1% wall-thorns damage taken per subsequent contact hit',
            'boss_survival_model': 'max_waves_compares_v21_plus_gc_boss_ttk_against_hit_by_hit_wall_ttd_with_between_hit_regen_only',
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
            'gc_pre_contact_model': summary.get('gc_pre_contact_model'),
            'lane_order': lane_order,
            'summary_lane_id': 'avg',
            'field_map_artifact': str(BOSS_WAVE_FIELD_MAP_PATH.relative_to(ROOT)),
            'intentional_semantic_differences': {
                'boss_ttk': 'replacement uses v21 boss-event kill sources plus QE-owned EP eDamage with Boss Waves exposure replacement; QE-owned Chain Lightning boss DPS remains diagnostic/fallback context',
            },
        },
        'replacement_primitive_inputs': {
            'layer': 'start_of_run_static_primitives_plus_row_evolved_workshop_skip_inputs_not_final_displayed_rows',
            'values': dict(primitive_inputs or {}),
        },
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
    reference_wave = _extract_optional_wave_number(raw_reference)
    dissonance_pbs = dict((getattr(account_state, 'dissonance_pbs_by_tier', {}) or {}).get(tier_label) or {})
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
        'dissonance_pb_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'dissonance_pb_reference_wave': dissonance_pb_reference_wave,
        'active_reference_kind': active_reference_kind,
        'active_reference_source': active_reference_source,
        'active_reference_wave': active_reference_wave,
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

    sources = {
        'flame_bot': _timed_dr_source(
            damage_reduction_pct=flame_bot_dr_pct,
            duration_seconds=flame_bot_duration,
            cooldown_seconds=flame_bot_cooldown,
            explicit_uptime_fraction=(
                max(0.0, min(1.0, float(flame_bot_hit_chance_pct) / 100.0))
                if flame_bot_hit_chance_pct is not None
                else None
            ),
            explicit_uptime_source=(
                'manual_boss_hit_chance_fraction'
                if flame_bot_hit_chance_pct is not None
                else 'explicit_uptime_fraction'
            ),
            primitive_status=(
                'manual_boss_hit_chance_average_model'
                if flame_bot_hit_chance_pct is not None
                else 'blocked_missing_duration_seconds_primitive'
                if flame_bot_dr_pct is not None and flame_bot_duration is None
                else 'runtime_or_qe_primitives'
            ),
        ),
        'defense_field': _timed_dr_source(
            damage_reduction_pct=defense_field_dr_pct,
            duration_seconds=defense_field_duration,
            cooldown_seconds=defense_field_cooldown,
            primitive_status=(
                'explicit_runtime_only_no_qe_surface_found'
                if defense_field_dr_pct is None and defense_field_duration is None and defense_field_cooldown is None
                else 'runtime_primitives'
            ),
        ),
        'black_hole_pbh': _timed_dr_source(
            damage_reduction_pct=black_hole_dr_pct,
            duration_seconds=black_hole_duration,
            cooldown_seconds=black_hole_cooldown,
            explicit_uptime_fraction=pbh_uptime,
            primitive_status='qe_primordial_collapse_black_hole_primitives',
        ),
    }
    lane_products = {'min': 1.0, 'avg': 1.0, 'max': 1.0}
    for source_name, source in sources.items():
        if source_name == 'black_hole_pbh':
            continue
        lane_dr = _timed_dr_source_by_lane(source)
        for lane_id, lane_fraction in lane_dr.items():
            lane_products[lane_id] *= 1.0 - float(lane_fraction)
    return {
        lane_id: max(0.0, min(1.0, 1.0 - product))
        for lane_id, product in lane_products.items()
    }, sources


def _timed_dr_source(
    *,
    damage_reduction_pct: float | None,
    duration_seconds: float | None,
    cooldown_seconds: float | None,
    explicit_uptime_fraction: float | None = None,
    explicit_uptime_source: str = 'explicit_uptime_fraction',
    primitive_status: str = 'runtime_primitives',
) -> dict[str, float | str]:
    dr_fraction = max(0.0, min(1.0, float(damage_reduction_pct or 0.0) / 100.0))
    if explicit_uptime_fraction is not None:
        uptime = max(0.0, min(1.0, float(explicit_uptime_fraction)))
        source = str(explicit_uptime_source)
    elif duration_seconds is None or cooldown_seconds is None or float(cooldown_seconds) <= 0.0:
        uptime = 0.0
        source = 'not_provided'
    else:
        uptime = max(0.0, min(1.0, float(duration_seconds) / float(cooldown_seconds)))
        source = 'duration_over_cooldown'
    return {
        'damage_reduction_pct': float(damage_reduction_pct or 0.0),
        'duration_seconds': float(duration_seconds or 0.0),
        'cooldown_seconds': float(cooldown_seconds or 0.0),
        'uptime_fraction': uptime,
        'uptime_source': source,
        'effective_dr_fraction': dr_fraction * uptime,
        'primitive_status': str(primitive_status),
    }


def _timed_dr_source_by_lane(source: dict[str, float | str]) -> dict[str, float]:
    dr_fraction = max(0.0, min(1.0, float(source.get('damage_reduction_pct') or 0.0) / 100.0))
    uptime_fraction = max(0.0, min(1.0, float(source.get('uptime_fraction') or 0.0)))
    is_permanent = uptime_fraction >= 1.0
    if is_permanent:
        return {'min': dr_fraction, 'avg': dr_fraction, 'max': dr_fraction}
    return {
        'min': 0.0,
        'avg': dr_fraction * uptime_fraction,
        'max': dr_fraction,
    }


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
    for filename in RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS:
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
    _annotate_display_fields(merged)
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
        payload.update(asdict(row))
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
    stable_payload = copy.deepcopy(run_stats_payload)
    diagnostics = dict(stable_payload.get('diagnostics') or {})
    diagnostics.pop('timings_ms', None)
    session = dict(diagnostics.get('session') or {})
    session.pop('account_state_build_ms', None)
    if session:
        diagnostics['session'] = session
    else:
        diagnostics.pop('session', None)
    preset_diagnostics = diagnostics.get('presets') or {}
    for preset_payload in preset_diagnostics.values():
        if not isinstance(preset_payload, dict):
            continue
        for state_mode in ('start_of_run', 'max_progression'):
            state_payload = dict(preset_payload.get(state_mode) or {})
            state_payload.pop('timings_ms', None)
            if state_payload:
                preset_payload[state_mode] = state_payload
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
    account_state = build_runtime_state(
        input_bundle.ids_raw,
        default_preset=preset,
        loadout_config=input_bundle.loadout_config,
        perk_config=perk_config,
    )
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

    def _account_state_cache_key(
        self,
        *,
        ids_path: Path,
        manual_inputs_path: Path | None,
        perk_mode: str,
        perk_policy_preset: str | None,
    ) -> tuple:
        return (
            _path_cache_token(ids_path),
            _path_cache_token(_effective_manual_inputs_path(manual_inputs_path)),
            str(perk_mode),
            str(_normalize_perk_policy_preset_name(perk_policy_preset) or ''),
        )

    def get_account_state_bundle(
        self,
        *,
        ids_path: Path,
        manual_inputs_path: Path | None,
        perk_mode: str,
        perk_policy_preset: str | None,
        diag_output_dir: Path | None,
    ):
        cache_key = self._account_state_cache_key(
            ids_path=ids_path,
            manual_inputs_path=manual_inputs_path,
            perk_mode=perk_mode,
            perk_policy_preset=perk_policy_preset,
        )
        cached = self._account_state_cache.get(cache_key)
        if cached is not None:
            return (*cached, True)
        input_bundle, account_state, perk_config_resolution = _build_account_state(
            ids_path=ids_path,
            manual_inputs_path=manual_inputs_path,
            preset='Farming',
            perk_mode=perk_mode,
            perk_policy_preset=perk_policy_preset,
            diag_output_dir=diag_output_dir,
        )
        cached_value = (input_bundle, account_state, perk_config_resolution)
        self._account_state_cache[cache_key] = cached_value
        return (*cached_value, False)

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
                base_stat_inputs = tuple(compile_stat_inputs(
                    account_state,
                    preset_name=preset_name,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    perks_enabled=perks_enabled,
                    scenario_context=scenario_context,
                ))
                if preset_name == 'Farming' and state_mode == 'start_of_run':
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
                        'state::cards.wave_accelerator.spawn_rate_acceleration',
                        'state::cards.wave_skip.chance_pct',
                        'state::tower.package_chance_pct',
                    ),
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    compiled_family_rows=compiled_timing_family_rows,
                    copy_result=False,
                )
                timing_wave_ms = _elapsed_ms(t)

                t = perf_counter()
                merged_statbook_dict = _merge_query_statbooks(
                    _query_response_to_statbook_dict(
                        progression_response,
                        bundle_id='progression_core_stats',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                        publish_qe_surfaces=True,
                    ),
                    _query_response_to_statbook_dict(
                        timing_core_response,
                        bundle_id='timing_core_cycle',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                    ),
                    _query_response_to_statbook_dict(
                        timing_wave_response,
                        bundle_id='timing_wave_duration',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                    ),
                )
                merged_statbook_dict = _publish_query_surfaces_on_statbook_dict(
                    merged_statbook_dict,
                    manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                    account_state_labs=account_state.labs,
                )
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
        run_stats_payload['diagnostics'] = diagnostics
        return {
            'run_stats_payload': run_stats_payload,
            'diagnostics': diagnostics,
            'account_state': account_state,
            'stat_inputs': primary_stats_stat_inputs_payload or [],
            'start_books_by_preset': start_books_by_preset,
            'max_books_by_preset': max_books_by_preset,
            'state_query_plans': state_query_plans,
        }

    def execute(self, args) -> int:
        args.out.mkdir(parents=True, exist_ok=True)
        _remove_run_stats_current_outputs(args.out)
        _remove_run_stats_legacy_outputs(args.out)
        artifacts = self.build_run_stats_artifacts(args)
        diagnostics = artifacts['diagnostics']
        contract_payload = normalize_contract_payload
        sanitized_account_state = _sanitized_account_state_for_output(artifacts['account_state'], 'Farming')
        module_card_payloads = build_module_card_payloads(artifacts['account_state'])
        write_outputs_ms = 0.0
        write_segment_start = perf_counter()
        (args.out / 'account_state.json').write_text(
            json.dumps(contract_payload(sanitized_account_state), indent=2, default=str)
        )
        (args.out / 'module_card_payloads.json').write_text(
            json.dumps(contract_payload(module_card_payloads), indent=2, default=str)
        )
        input_dashboard_payload = _build_input_dashboard_payload(
            sanitized_account_state,
            diagnostics,
            qe_dashboard_publications={},
            module_card_payloads=module_card_payloads,
        )
        (args.out / 'input_dashboard.json').write_text(
            json.dumps(contract_payload(input_dashboard_payload), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_plan']).write_text(
            json.dumps(contract_payload({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'start_of_run',
                'presets': artifacts['state_query_plans']['start_of_run'],
            }), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_plan']).write_text(
            json.dumps(contract_payload({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'max_progression',
                'presets': artifacts['state_query_plans']['max_progression'],
            }), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_rows']).write_text(
            json.dumps(contract_payload(artifacts['start_books_by_preset']), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']).write_text(
            json.dumps(contract_payload(artifacts['max_books_by_preset']), indent=2, default=str)
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
            json.dumps(contract_payload(stats_dashboard_payload), indent=2, default=str)
        )
        optional_committed_artifacts: list[str] = []
        if bool(getattr(args, 'include_boss_wave_milestone_matrix', False)):
            write_outputs_ms += _elapsed_ms(write_segment_start)
            matrix_request = PipelineRunRequest(
                ids=args.ids,
                out=args.out,
                preset='Milestone',
                manual_inputs=args.manual_inputs,
                perk_mode='max_progression_policy',
                perk_state='auto',
                dissonance_run_category=args.dissonance_run_category,
            )
            matrix_build_start = perf_counter()
            boss_wave_milestone_matrix = build_boss_wave_milestone_matrix(
                matrix_request,
                scenario_runtime_inputs=_boss_wave_matrix_runtime_inputs_from_args(args),
                comparison_scenario_runtime_inputs=_boss_wave_matrix_comparison_inputs_from_args(args),
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
            write_segment_start = perf_counter()
            optional_committed_artifacts.append(BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT)
            diagnostics['boss_wave_milestone_matrix'] = {
                'enabled': True,
                'artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
                'tier_count': len(boss_wave_milestone_matrix.get('tiers') or []),
                'row_count': len(boss_wave_milestone_matrix.get('rows') or []),
                'wide_row_count': len(boss_wave_milestone_matrix.get('wide_rows') or []),
                'selection_policy': boss_wave_milestone_matrix.get('contract', {}).get('selection_policy'),
                'scenario_runtime_inputs': boss_wave_milestone_matrix.get('scenario_runtime_inputs'),
                'comparison_enabled': 'comparison' in boss_wave_milestone_matrix,
            }
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
            json.dumps(contract_payload(stable_run_stats_payload), indent=2, default=str)
        )
        write_outputs_ms += _elapsed_ms(write_segment_start)
        diagnostics['timings_ms']['write_outputs_ms'] = round(write_outputs_ms, 3)
        (args.out / 'diagnostics.json').write_text(
            json.dumps(_json_sanitize(diagnostics), indent=2, default=str)
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
                state = build_runtime_state(ids_raw, default_preset=preset_name, loadout_config=loadout_config, perk_config=perk_config)
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
    all_perk_rows = [row for row in compile_stat_inputs(audit_state, preset_name=account_state.default_preset, state_mode='start_of_run') if row.source_family == 'perk']
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
    diagnostics['perk_support'] = diagnostics['ep_compare_stage_rules']['package_compare_capability']

    audit_surface_manifest = _build_audit_surface_manifest(account_state, args.preset)
    artifact_contract_manifest = _build_artifact_contract_manifest(account_state, args.preset, stat_inputs, statbook_dict)
    family_completeness_matrix = _build_family_completeness_matrix(account_state, stat_inputs)
    optimizer_scores = compute_optimizer_scores(statbook_dict)
    boss_wave_milestone_matrix_payload = None
    if bool(getattr(args, 'include_boss_wave_milestone_matrix', False)):
        matrix_request = PipelineRunRequest(
            ids=args.ids,
            out=args.out,
            preset='Milestone',
            state_mode=args.state_mode,
            manual_inputs=args.manual_inputs,
            perk_mode='max_progression_policy',
            perk_state='auto',
        )
        boss_wave_milestone_matrix_payload = build_boss_wave_milestone_matrix(
            matrix_request,
            scenario_runtime_inputs=_boss_wave_matrix_runtime_inputs_from_args(args),
            comparison_scenario_runtime_inputs=_boss_wave_matrix_comparison_inputs_from_args(args),
        )
        diagnostics['boss_wave_milestone_matrix'] = {
            'enabled': True,
            'artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
            'tier_count': len(boss_wave_milestone_matrix_payload.get('tiers') or []),
            'row_count': len(boss_wave_milestone_matrix_payload.get('rows') or []),
            'wide_row_count': len(boss_wave_milestone_matrix_payload.get('wide_rows') or []),
            'selection_policy': boss_wave_milestone_matrix_payload.get('contract', {}).get('selection_policy'),
            'scenario_runtime_inputs': boss_wave_milestone_matrix_payload.get('scenario_runtime_inputs'),
            'comparison_enabled': 'comparison' in boss_wave_milestone_matrix_payload,
        }
    else:
        stale_matrix = args.out / BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT
        if stale_matrix.exists():
            stale_matrix.unlink()
        diagnostics['boss_wave_milestone_matrix'] = {
            'enabled': False,
            'reason': 'optional_matrix_not_requested',
            'artifact': BOSS_WAVE_MILESTONE_MATRIX_ARTIFACT,
        }

    # Prepare payloads and delegate output writing to publication authority
    account_state_payload = _sanitized_account_state_for_output(account_state, args.preset)
    stat_inputs_payload = [row.to_dict() for row in stat_inputs]
    module_card_payloads_data = build_module_card_payloads(account_state)
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
            outputs_summary={'perk_config_resolution': diagnostics.get('perk_config_resolution', {}), 'perk_support': diagnostics.get('perk_support', {})},
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
            'perk_mode': request.perk_mode,
            'perk_policy_preset': request.perk_policy_preset,
            'include_slow_audits': request.include_slow_audits,
            'perk_state': request.perk_state,
            'tier': request.tier,
            'include_boss_wave_milestone_matrix': request.include_boss_wave_milestone_matrix,
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
    args.perk_mode = request.perk_mode
    args.perk_policy_preset = request.perk_policy_preset
    args.include_slow_audits = request.include_slow_audits
    args.perk_state = request.perk_state
    args.tier = request.tier
    args.include_boss_wave_milestone_matrix = request.include_boss_wave_milestone_matrix
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



