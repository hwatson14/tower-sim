"""Simulator smoke tests for progression/timing public APIs."""
from __future__ import annotations

import sys
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest

from input.loader import load_inputs
from input.runtime_state import build_runtime_state

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


@lru_cache(maxsize=1)
def _base_account_state():
    bundle = load_inputs()
    return build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )


def test_progression_public_api_is_importable__query_callables_exposed():
    from simulators.progression import (
        resolve_progression_consumer_bundle,
        resolve_progression_family_query,
        resolve_run_stats_progression_bundle,
    )

    assert callable(resolve_progression_family_query)
    assert callable(resolve_progression_consumer_bundle)
    assert callable(resolve_run_stats_progression_bundle)


def test_v28_overheat_normal_tier_and_tournament_conditions_are_projected():
    from simulators.scenario import ScenarioConfig, compute_scenario_surfaces, overheat_start_wave_for_tier

    assert overheat_start_wave_for_tier(1) == 15000
    assert overheat_start_wave_for_tier(10) == 12750
    assert overheat_start_wave_for_tier(20) == 10250

    normal = compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=10, current_wave=12750))
    assert normal.overheat_active is True
    assert normal.overheat_enemy_skip_decay_active is True
    assert normal.overheat_damage_decay_active is False
    assert normal.overheat_more_fleets_active is False

    tournament = compute_scenario_surfaces(ScenarioConfig(mode_id='tournament', tier=20, league='legend', tournament_wave=10350))
    assert tournament.overheat_active is True
    assert tournament.overheat_damage_decay_active is True
    assert tournament.overheat_health_decay_active is True
    assert tournament.overheat_more_fleets_active is True
    assert tournament.overheat_more_elites_active is True
    assert tournament.overheat_damage_decay_steps == 10
    assert tournament.overheat_extra_fleets == 1
    assert tournament.overheat_extra_elites == 20


def test_timing_public_api_is_importable__query_callables_exposed():
    from simulators.timing import compute_timing_surfaces, resolve_timing_consumer_bundle, resolve_timing_family_query

    assert callable(compute_timing_surfaces)
    assert callable(resolve_timing_family_query)
    assert callable(resolve_timing_consumer_bundle)


def test_timing_engine_owns_boss_contact_dr_and_damage_windows():
    from simulators.timing import (
        boss_contact_time_seconds,
        energy_net_mastery_damage_window_seconds,
        flame_bot_static_boss_hit_chance,
        shockwave_active_fraction,
        time_limited_multiplier_damage,
        time_limited_multiplier_kill_seconds,
        timed_dr_lanes_from_sources,
        timed_dr_source,
        timed_effect_lane_fractions,
    )

    contact_time, source, components = boss_contact_time_seconds(
        chrono_field_duration_seconds=50.0,
        chrono_field_cooldown_seconds=60.0,
        chrono_field_slow_pct=30.0,
        slow_aura_enemy_speed_pct=0.0,
        energy_net_duration_seconds=4.3,
    )
    assert source == 'derived_base_2s_cf_slow_aura_energy_net'
    assert components['chrono_field_average_slow_fraction'] == pytest.approx(0.25)
    assert components['energy_net_hold_seconds'] == pytest.approx(4.3)
    assert contact_time == pytest.approx((2.0 / 0.75) + 4.3)

    fast_contact_time, fast_source, fast_components = boss_contact_time_seconds(
        chrono_field_duration_seconds=50.0,
        chrono_field_cooldown_seconds=60.0,
        chrono_field_slow_pct=30.0,
        enemy_speed_increase_pct=120.0,
        boss_speed_multiplier=1.5,
        energy_net_duration_seconds=4.3,
    )
    assert fast_source == 'derived_base_2s_cf_slow_aura_enemy_speed_energy_net'
    assert fast_components['enemy_speed_increase_fraction'] == pytest.approx(1.2)
    assert fast_components['boss_speed_multiplier'] == pytest.approx(1.5)
    assert fast_components['movement_speed_multiplier'] == pytest.approx(3.3)
    assert fast_components['speed_remaining_fraction'] == pytest.approx(0.75 * 3.3)
    assert fast_contact_time == pytest.approx((2.0 / (0.75 * 3.3)) + 4.3)

    geometry_contact_time, geometry_source, geometry_components = boss_contact_time_seconds(
        chrono_field_duration_seconds=50.0,
        chrono_field_cooldown_seconds=60.0,
        chrono_field_slow_pct=30.0,
        geometry_base_contact_time_seconds=3.0,
        geometry_base_components={
            'status': 'resolved_displayed_proxy_candidate',
            'truth_status': 'displayed_proxy_candidate_not_wall_contact_truth',
            'boss_path_distance_to_wall_displayed_candidate_m': 60.0,
        },
    )
    assert geometry_source == 'derived_geometry_displayed_proxy_base_cf_slow_aura_energy_net'
    assert geometry_components['base_seconds_source'] == 'geometry_displayed_proxy_candidate'
    assert geometry_components['geometry_proxy_truth_status'] == 'displayed_proxy_candidate_not_wall_contact_truth'
    assert geometry_contact_time == pytest.approx(3.0 / 0.75)

    assert energy_net_mastery_damage_window_seconds(
        energy_net_duration_seconds=4.3,
        energy_net_mastery_multiplier=8.0,
    ) == pytest.approx(14.3)
    assert energy_net_mastery_damage_window_seconds(
        energy_net_duration_seconds=4.3,
        energy_net_mastery_multiplier=1.0,
    ) == pytest.approx(0.0)

    hit_probability, active_fraction = shockwave_active_fraction(
        contact_time_seconds=10.0,
        shockwave_interval_seconds=14.0,
    )
    assert hit_probability == pytest.approx(10.0 / 14.0)
    assert active_fraction == pytest.approx(0.5)

    dr_lanes = timed_effect_lane_fractions(
        effect_fraction=0.8,
        duration_seconds=36.0,
        cooldown_seconds=46.0,
    )
    assert dr_lanes == pytest.approx({'min': 0.0, 'avg': 0.8 * (36.0 / 46.0), 'max': 0.8})

    flame_dr_source = timed_dr_source(
        damage_reduction_pct=95.0,
        duration_seconds=None,
        cooldown_seconds=5.0,
        explicit_uptime_fraction=0.97,
        primitive_status='test_binary_hit_model',
        binary_outcome=True,
        binary_avg_hit_threshold=0.95,
    )
    assert flame_dr_source['deterministic_hit_dr_fraction'] == pytest.approx(0.95)
    assert flame_dr_source['probability_weighted_dr_fraction'] == pytest.approx(0.95 * 0.97)
    assert timed_dr_lanes_from_sources(
        {'flame_bot': flame_dr_source, 'black_hole_pbh': {'damage_reduction_pct': 80.0, 'uptime_fraction': 1.0}},
        binary_avg_hit_threshold=0.95,
        excluded_source_names=('black_hole_pbh',),
    ) == pytest.approx({'min': 0.0, 'avg': 0.95, 'max': 0.95})

    assert time_limited_multiplier_damage(
        start_seconds=0.0,
        end_seconds=10.0,
        damage_per_second=100.0,
        multiplier=2.0,
        multiplier_duration_seconds=3.0,
    ) == pytest.approx(1300.0)
    assert time_limited_multiplier_kill_seconds(
        start_seconds=0.0,
        end_seconds=10.0,
        hp_to_kill=1000.0,
        damage_per_second=100.0,
        multiplier=2.0,
        multiplier_duration_seconds=3.0,
    ) == pytest.approx(7.0)

    flame_hit_chance, flame_components = flame_bot_static_boss_hit_chance(
        tower_range_m=69.5,
        flame_bot_effective_range_m=91.0,
        flame_bot_cooldown_seconds=5.0,
        boss_time_to_contact_seconds=6.3,
        energy_net_hold_seconds=4.3,
    )
    assert flame_components['status'] == 'resolved'
    assert flame_components['model'] == 'static_uniform_flame_bot_center_vs_boss_path'
    assert flame_hit_chance == pytest.approx(flame_components['hit_fraction'])
    assert flame_components['energy_net_hold_seconds'] == pytest.approx(4.3)


def test_tier_enemy_level_skip_reduction_continues_expected_late_tier_pattern():
    from simulators.scenario import ScenarioConfig, _load_tier_battle_conditions, compute_scenario_surfaces, normalize_els_reduction_to_fraction

    tier_bcs = _load_tier_battle_conditions()

    assert normalize_els_reduction_to_fraction(0.025) == pytest.approx(0.025)
    assert normalize_els_reduction_to_fraction(-0.08) == pytest.approx(0.08)
    assert normalize_els_reduction_to_fraction(2.5) == pytest.approx(0.025)
    assert 0.35 - normalize_els_reduction_to_fraction(0.025) == pytest.approx(0.325)
    assert compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=14)).bc_enemy_level_skip_reduction_pp == pytest.approx(0.025)
    assert compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=15)).bc_enemy_level_skip_reduction_pp == pytest.approx(0.05)
    tournament = compute_scenario_surfaces(ScenarioConfig(mode_id='tournament', league='Legends', tournament_wave=100))
    assert tournament.boss_wave_interval == 6
    assert tournament.bc_enemy_level_skip_reduction_pp == pytest.approx(-0.08)
    assert normalize_els_reduction_to_fraction(tournament.bc_enemy_level_skip_reduction_pp) == pytest.approx(0.08)
    assert float(tier_bcs[19]['enemy_level_skip_reduction']['value']) == pytest.approx(0.15)
    assert float(tier_bcs[20]['enemy_level_skip_reduction']['value']) == pytest.approx(0.175)
    assert float(tier_bcs[21]['enemy_level_skip_reduction']['value']) == pytest.approx(0.2)


def test_overheat_enemy_skip_decay_schedule_uses_imported_bc_curve():
    from simulators.scenario import overheat_enemy_skip_decay_schedule

    schedule = overheat_enemy_skip_decay_schedule()

    assert schedule[0] == pytest.approx(0.01)
    assert schedule[20] == pytest.approx(0.02)
    assert schedule[1000] == pytest.approx(0.3333)


def test_scenario_surface_owns_boss_interval_by_tier():
    from simulators.scenario import ScenarioConfig, compute_scenario_surfaces

    assert compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=13)).boss_wave_interval == 10
    assert compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=14)).boss_wave_interval == 9
    assert compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=15)).boss_wave_interval == 8
    assert compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=16)).boss_wave_interval == 7


def test_scenario_surface_flags_unsupported_terminal_pressure_by_tier():
    from simulators.scenario import ScenarioConfig, compute_scenario_surfaces

    t14 = compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=14))
    assert t14.unsupported_terminal_pressures == ()

    t16 = compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=16))
    assert {
        'armored_enemies_blocked_hits',
        'knockback_resistance_non_boss_pressure',
        'protector_ultimate_deferred',
    } <= set(t16.unsupported_terminal_pressures)

    t17 = compute_scenario_surfaces(ScenarioConfig(mode_id='farming', tier=17))
    assert {
        'armored_enemies_blocked_hits',
        'knockback_resistance_non_boss_pressure',
        'protector_ultimate_deferred',
        'boss_ultimate_deferred',
        'mass_enforcement_deferred',
    } <= set(t17.unsupported_terminal_pressures)


def test_non_boss_pressure_driver_probe_uses_kb_spawn_elite_and_fleet_curves():
    from simulators.scenario import (
        elite_spawn_pressure_driver,
        fleet_spawn_pressure_driver,
        non_boss_pressure_driver_probe,
        non_boss_pressure_driver_source_summary,
        normal_spawn_rate_pressure_driver,
    )

    normal = normal_spawn_rate_pressure_driver(
        wave=2778,
        enemy_balance_spawn_multiplier=1.9,
        wave_accelerator_spawn_rate_acceleration=1.8,
        more_enemies_pct=25.0,
    )
    assert normal['displayed_spawn_rate'] == pytest.approx(50.0)
    assert normal['threshold_standard_wave'] == 5000
    assert normal['threshold_actual_wave_with_wave_accelerator'] == 2778
    assert normal['next_displayed_spawn_rate'] == pytest.approx(52.0)
    assert normal['normal_spawn_rate_pressure_index'] == pytest.approx(50.0 * 1.9 * 1.25)
    assert normal['formula_status'] == (
        'source_spawn_rate_curve_available_terminal_pressure_transform_missing'
    )

    elite = elite_spawn_pressure_driver(
        tier=14,
        wave=2033,
        enemy_balance_mastery_double_elite_chance_pct=12.0,
    )
    assert elite['single_elite_displayed_chance_pct'] == pytest.approx(33.0)
    assert elite['double_elite_displayed_chance_pct'] == pytest.approx(0.33)
    assert elite['elite_pressure_index_pct'] == pytest.approx(45.33)
    assert elite['formula_status'] == 'source_spawn_curve_available_terminal_pressure_transform_missing'

    fleet = fleet_spawn_pressure_driver(tier=21, wave=10000)
    assert fleet['regular']['active'] is True
    assert fleet['regular']['count_per_event'] == pytest.approx(2.0)
    assert fleet['regular']['events_per_wave_pressure'] == pytest.approx(0.2)
    assert fleet['regular']['related_enemy_group_count_min'] == pytest.approx(10.0)
    assert fleet['regular']['related_enemy_group_count_max'] == pytest.approx(14.0)
    assert fleet['regular']['related_enemy_group_expected_count'] == pytest.approx(12.0)
    assert fleet['regular']['related_enemy_group_expected_enemies_per_wave_pressure'] == pytest.approx(2.4)
    assert fleet['bonus']['active'] is True
    assert fleet['bonus']['events_per_wave_pressure'] == pytest.approx(0.01)
    assert fleet['fleet_events_per_wave_pressure'] == pytest.approx(0.21)
    assert fleet['fleet_related_enemy_group_expected_enemies_per_wave_pressure'] == pytest.approx(2.52)
    assert fleet['fleet_related_enemy_group_count_range'] == [10, 14]

    probe = non_boss_pressure_driver_probe(
        tier=21,
        wave=10000,
        scenario_surfaces={'bc_more_enemies_pct': 25.0},
        enemy_balance_spawn_multiplier=1.9,
        wave_accelerator_spawn_rate_acceleration=1.8,
        enemy_balance_mastery_double_elite_chance_pct=12.0,
    )
    assert probe['status'] == 'driver_inputs_available_terminal_transform_missing'
    assert probe['enemy_spawn_rate_multiplier_pressure'] == pytest.approx(1.9 * 1.8 * 1.25)
    assert probe['normal_spawn_rate_pressure']['displayed_spawn_rate'] == pytest.approx(56.0)
    assert probe['normal_spawn_rate_pressure']['normal_spawn_rate_pressure_index'] == pytest.approx(
        56.0 * 1.9 * 1.25
    )
    assert probe['normal_enemy_spawn_rate_curve_available'] is True
    assert probe['normal_enemy_spawn_count_curve_available'] is False
    assert probe['source_backed_curve_coverage'] == {
        'normal_spawn_rate_curve_by_wave_and_wave_accelerator': True,
        'elite_spawn_curve_by_tier_and_wave': True,
        'fleet_spawn_curve_by_tier_and_wave': True,
        'fleet_related_enemy_group_count_range': True,
        'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase': False,
    }
    assert 'normal_spawn_rate_value_to_terminal_pressure' in probe['missing_terminal_formula_links']
    assert 'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase' not in probe[
        'missing_terminal_formula_links'
    ]

    source_summary = non_boss_pressure_driver_source_summary()
    assert source_summary['source_table_counts'] == {
        'normal_spawn_rate_wave_threshold_rows': 28,
        'elite_spawn_threshold_rows': 21,
        'fleet_spawn_tier_rows': 21,
    }
    assert source_summary['status'] == 'source_driver_curves_partially_available_terminal_transform_missing'


def test_simulator_modules_reference_qe_imports__expected_qe_strings_present():
    import simulators.progression as progression_module
    import simulators.timing as timing_module

    for mod, name in [(progression_module, "simulators.progression"), (timing_module, "simulators.timing")]:
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "qe." in src or "from qe" in src, f"{name} must import from qe.*"


def test_simulator_default_family_query_paths_reference_shared_qe_planner():
    import simulators.progression as progression_module
    import simulators.timing as timing_module

    progression_src = Path(progression_module.__file__).read_text(encoding="utf-8")
    timing_src = Path(timing_module.__file__).read_text(encoding="utf-8")

    assert "QEResolutionPlanner" in progression_src
    assert "resolve_declared_family_query" in progression_src
    assert "QEResolutionPlanner" in timing_src
    assert "resolve_rows_declared_family_query" in timing_src


def test_progression_bounded_reference_statbook_is_native_family_backed():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.progression import ProgressionRecalcBridge, ProgressionRecalcRequest

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    request = ProgressionRecalcRequest(
        account_state=state,
        preset_name="Farming",
        workshop_levels_current={},
        perks_enabled=True,
    )

    statbook = ProgressionRecalcBridge()._bounded_reference_statbook(
        patched=state,
        request=request,
    )

    assert statbook.diagnostics["qe_resolution_interface"] == "native_family_query"
    assert statbook.diagnostics["qe_resolution_backend"] == "native_family_query"
    assert statbook.diagnostics["qe_native_family_id"] == "progression_runtime_with_perks"


def test_timing_family_statbook_is_native_family_backed():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from qe.routing import QEResolutionPlanner
    from simulators.scenario import ScenarioConfig
    from simulators.timing import compile_timing_family_rows

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    bound, rows = compile_timing_family_rows(
        account_state=state,
        family_id="timing_farm_with_perks",
        preset_name="Farming",
        scenario_config=ScenarioConfig(mode_id="farming", tier=14),
        perks_enabled=True,
    )
    statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id="timing_farm_with_perks",
        requested_surface_ids=(
            "state::uw.black_hole.cooldown_seconds",
            "support_surface::timing.wave_duration_seconds_effective",
        ),
        notes="simulator timing native family smoke",
        diagnostics={"source": "test"},
    )

    assert statbook.diagnostics["qe_resolution_interface"] == "native_family_query"
    assert statbook.diagnostics["qe_resolution_backend"] == "native_family_query"
    assert statbook.diagnostics["qe_native_family_id"] == "timing_farm_with_perks"
    assert statbook.rows["support_surface::timing.wave_duration_seconds_effective"].status == "resolved"


def test_timing_wave_duration_consumes_wave_accelerator_cooldown_not_mastery_spawn_rate():
    from qe.routing import QEResolutionPlanner
    from simulators.scenario import ScenarioConfig
    from simulators.timing import wave_duration_seconds_after_cooldown_reduction, compile_timing_family_rows

    state = _base_account_state()
    wave_accelerator = replace(
        state.cards_inventory["Wave Accelerator"],
        mastery_unlocked=True,
        mastery_lab_level=7,
    )
    mutated = replace(
        state,
        labs={**state.labs, "Wave Accelerator Mastery": 7},
        cards_inventory={**state.cards_inventory, "Wave Accelerator": wave_accelerator},
        card_presets={**state.card_presets, state.default_preset: ["Wave Accelerator"]},
    )

    bound, rows = compile_timing_family_rows(
        account_state=mutated,
        family_id="timing_farm_with_perks",
        preset_name="Farming",
        scenario_config=ScenarioConfig(mode_id="farming", tier=14),
        perks_enabled=True,
    )
    statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id="timing_farm_with_perks",
        requested_surface_ids=(
            "state::cards.wave_accelerator.wave_cooldown_reduction_pct",
            "state::cards.wave_accelerator.spawn_rate_acceleration",
            "support_surface::timing.wave_duration_seconds_effective",
        ),
        notes="wave accelerator cooldown-only timing regression",
        diagnostics={"source": "test"},
    )

    expected_duration = wave_duration_seconds_after_cooldown_reduction("farming", 54.0)
    assert expected_duration == pytest.approx(30.14)
    assert statbook.rows["state::cards.wave_accelerator.wave_cooldown_reduction_pct"].final_value == pytest.approx(54.0)
    assert statbook.rows["state::cards.wave_accelerator.spawn_rate_acceleration"].final_value == pytest.approx(1.8)
    assert statbook.rows["support_surface::timing.wave_duration_seconds_effective"].final_value == pytest.approx(expected_duration)


def test_progression_native_family_statbook_does_not_touch_report_fallback(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    import qe.routing as qe_routing
    from simulators.progression import ProgressionRecalcBridge, ProgressionRecalcRequest

    def _no_report_fallback(_stat_inputs):
        raise AssertionError("native progression statbook must not call report fallback")

    monkeypatch.setattr(qe_routing, "_fallback_resolve_stats", _no_report_fallback)

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    request = ProgressionRecalcRequest(
        account_state=state,
        preset_name="Farming",
        workshop_levels_current={},
        perks_enabled=True,
    )

    statbook = ProgressionRecalcBridge()._bounded_reference_statbook(
        patched=state,
        request=request,
    )

    assert statbook.diagnostics["qe_resolution_backend"] == "native_family_query"
    assert statbook.rows["state::tower.enemy_attack_level_skip_pct"].status == "resolved"


def test_timing_native_family_statbook_does_not_touch_report_fallback(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    import qe.routing as qe_routing
    from qe.routing import QEResolutionPlanner
    from simulators.scenario import ScenarioConfig
    from simulators.timing import compile_timing_family_rows

    def _no_report_fallback(_stat_inputs):
        raise AssertionError("native timing statbook must not call report fallback")

    monkeypatch.setattr(qe_routing, "_fallback_resolve_stats", _no_report_fallback)

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    bound, rows = compile_timing_family_rows(
        account_state=state,
        family_id="timing_farm_with_perks",
        preset_name="Farming",
        scenario_config=ScenarioConfig(mode_id="farming", tier=14),
        perks_enabled=True,
    )
    statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id="timing_farm_with_perks",
        requested_surface_ids=(
            "state::uw.black_hole.cooldown_seconds",
            "support_surface::timing.wave_duration_seconds_effective",
        ),
        notes="simulator timing native fallback guard",
        diagnostics={"source": "test"},
    )

    assert statbook.diagnostics["qe_resolution_backend"] == "native_family_query"
    assert statbook.rows["support_surface::timing.wave_duration_seconds_effective"].status == "resolved"


def test_scenario_farming_throughput_publication_is_importable_and_emits_scenario_owned_surface():
    from simulators.scenario import ScenarioConfig, publish_farming_throughput_support_surfaces
    from simulators.timing import compile_timing_family_rows
    from qe.routing import QEResolutionPlanner

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    bound, rows = compile_timing_family_rows(
        account_state=state,
        family_id="timing_farm_with_perks",
        preset_name="Farming",
        scenario_config=ScenarioConfig(mode_id="farming", tier=14),
        perks_enabled=True,
    )
    timing_statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id="timing_farm_with_perks",
        requested_surface_ids=("support_surface::timing.wave_duration_seconds_effective",),
        notes="scenario throughput prerequisite",
        diagnostics={"source": "test"},
    )
    publish_farming_throughput_support_surfaces(
        timing_statbook.rows,
        account_state=state,
        config=ScenarioConfig(mode_id="farming", tier=14),
        stat_inputs=bound.stat_inputs,
        farming_hours_per_day=23.5,
    )

    intro_sprint_waves = next(
        row.value
        for row in bound.stat_inputs
        if row.destination_object_type == "runtime_mechanic_param"
        and row.destination_id == "cards.intro_sprint.waves"
        and row.active
    )
    wave_skip_pct = next(
        row.value
        for row in bound.stat_inputs
        if row.destination_object_type == "runtime_mechanic_param"
        and row.destination_id == "cards.wave_skip.chance_pct"
        and row.active
    )
    target_farming_wave = timing_statbook.rows["support_surface::scenario.target_farming_wave"].final_value
    expected_waves_per_run = (
        target_farming_wave * (1.0 + (wave_skip_pct / 100.0))
        + min(intro_sprint_waves, target_farming_wave)
    )

    assert intro_sprint_waves > 0.0
    assert timing_statbook.rows["support_surface::scenario.bosses_per_day_effective"].status == "resolved"
    assert timing_statbook.rows["support_surface::scenario.waves_per_run_effective"].final_value == pytest.approx(expected_waves_per_run)


def test_runtime_consumer_bundles_stay_within_declared_native_family_surfaces():
    from qe.consumer_registry import declared_family_surface_ids, resolve_consumer_bundle

    cases = [
        ("runtime_consumer::wave_progression.attack_wave", "progression_wave_skips", "progression_runtime_with_perks"),
        ("runtime_consumer::wave_progression.health_wave", "progression_wave_skips", "progression_runtime_with_perks"),
        ("progression_runtime", "progression_free_upgrades", "progression_runtime_with_perks"),
    ]

    families = declared_family_surface_ids()
    for consumer_id, bundle_id, family_id in cases:
        bundle = resolve_consumer_bundle(consumer_id, bundle_id, family_id=family_id)
        assert set(bundle.surface_ids) <= set(families[family_id])


def test_incremental_progression_plan_for_workshop_overrides_stays_native_and_non_fallback():
    from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime

    plan = IncrementalRecalcRuntime().plan_from_workshop_overrides(
        {"Health": 1}
    )

    assert plan.family_id == "progression_runtime_no_perks"
    assert plan.fallback_required is False
    assert plan.baseline_required is True
    assert isinstance(plan.runtime_consumer_ids, list)


def test_declared_consumer_bundle_plan_stays_non_fallback():
    from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime

    plan = IncrementalRecalcRuntime().plan_consumer_bundle(
        consumer_id="progression_runtime",
        bundle_id="progression_wave_skips",
        family_id="progression_runtime_with_perks",
    )

    assert plan.fallback_required is False
    assert plan.requested_surfaces == [
        "state::tower.enemy_attack_level_skip_pct",
        "state::tower.enemy_health_level_skip_pct",
    ]


def test_invalid_consumer_bundle_request_fails_closed_to_fallback():
    from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime

    plan = IncrementalRecalcRuntime().plan_consumer_bundle(
        consumer_id="progression_runtime",
        bundle_id="progression_wave_skips",
        family_id="timing_farm_with_perks",
    )

    assert plan.fallback_required is True
    assert "timing_farm_with_perks" in (plan.fallback_reason or "")


def test_progression_consumer_bundle_stays_native_without_report_fallback(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    import qe.routing as qe_routing
    from simulators.progression import resolve_progression_consumer_bundle

    def _no_report_fallback(_stat_inputs):
        raise AssertionError("progression consumer bundle must not call report fallback")

    monkeypatch.setattr(qe_routing, "_fallback_resolve_stats", _no_report_fallback)

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    response = resolve_progression_consumer_bundle(
        account_state=state,
        consumer_id="progression_runtime",
        bundle_id="progression_free_upgrades",
        family_id="progression_runtime_with_perks",
        preset_name="Farming",
        perks_enabled=True,
    )

    resolved = {row.surface_id: row for row in response.resolved_surface_rows}
    assert resolved["state::tower.free_attack_upgrade_chance_pct"].status == "resolved"
    assert resolved["state::tower.free_defense_upgrade_chance_pct"].status == "resolved"
    assert resolved["state::tower.free_utility_upgrade_chance_pct"].status == "resolved"


def test_timing_consumer_bundle_stays_native_without_report_fallback(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    import qe.routing as qe_routing
    from simulators.scenario import ScenarioConfig
    from simulators.timing import resolve_timing_consumer_bundle

    def _no_report_fallback(_stat_inputs):
        raise AssertionError("timing consumer bundle must not call report fallback")

    monkeypatch.setattr(qe_routing, "_fallback_resolve_stats", _no_report_fallback)

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    response = resolve_timing_consumer_bundle(
        account_state=state,
        consumer_id="run_stats",
        bundle_id="timing_core_cycle",
        family_id="timing_farm_with_perks",
        preset_name="Farming",
        scenario_config=ScenarioConfig(mode_id="farming", tier=14),
        perks_enabled=True,
    )

    resolved = {row.surface_id: row for row in response.resolved_surface_rows}
    assert resolved["state::uw.black_hole.cooldown_seconds"].status == "resolved"
    assert resolved["state::uw.black_hole.duration_seconds"].status == "resolved"
    assert resolved["state::uw.golden_tower.cooldown_seconds"].status == "resolved"
    assert resolved["state::uw.golden_tower.duration_seconds"].status == "resolved"


def test_incremental_subset_executor_resolves_progression_wave_skip_bundle_natively():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    import qe.routing as qe_routing
    from qe.stat_input_compiler import compile_stat_inputs
    from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime
    from simulators.incremental_subset_executor import IncrementalSubsetExecutor

    assert not hasattr(qe_routing, "_bounded_resolve_bucket")

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    plan = IncrementalRecalcRuntime().plan_consumer_bundle(
        consumer_id="progression_runtime",
        bundle_id="progression_wave_skips",
        family_id="progression_runtime_with_perks",
    )
    stat_inputs = compile_stat_inputs(
        state,
        preset_name="Farming",
        state_mode="start_of_run",
        card_preset_name="Farming",
        module_preset_name="Farming",
        perk_preset_name="Farming",
        perks_enabled=True,
    )

    rows = IncrementalSubsetExecutor().execute(
        stat_inputs,
        plan.requested_surfaces,
        family_id=plan.family_id,
    )

    for surface_id in plan.requested_surfaces:
        row = rows[surface_id]
        assert row.status == "resolved"
        assert row.final_value is not None


def test_incremental_subset_executor_resolves_timing_family_surfaces_natively():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    import qe.routing as qe_routing
    from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime
    from simulators.incremental_subset_executor import IncrementalSubsetExecutor
    from simulators.scenario import ScenarioConfig
    from simulators.timing import compile_timing_family_rows

    assert not hasattr(qe_routing, "_bounded_resolve_bucket")

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    _bound, rows = compile_timing_family_rows(
        account_state=state,
        family_id="timing_farm_with_perks",
        preset_name="Farming",
        scenario_config=ScenarioConfig(mode_id="farming", tier=14),
        perks_enabled=True,
    )
    plan = IncrementalRecalcRuntime().plan_surface_request(
        family_id="timing_farm_with_perks",
        surface_ids=(
            "state::uw.black_hole.cooldown_seconds",
            "support_surface::timing.wave_duration_seconds_effective",
        ),
    )

    resolved = IncrementalSubsetExecutor().execute(
        rows,
        plan.requested_surfaces,
        family_id=plan.family_id,
        scenario_mode_id="farming",
    )

    assert resolved["state::uw.black_hole.cooldown_seconds"].status == "resolved"
    assert resolved["state::uw.black_hole.cooldown_seconds"].final_value > 0.0
    assert resolved["support_surface::timing.wave_duration_seconds_effective"].status == "resolved"
    assert resolved["support_surface::timing.wave_duration_seconds_effective"].final_value is not None


def test_run_stats_progression_bundle__resolves_declared_surfaces():
    from simulators.progression import resolve_run_stats_progression_bundle

    state = _base_account_state()
    response = resolve_run_stats_progression_bundle(
        account_state=state,
        family_id='progression_start_of_run',
        preset_name=state.default_preset,
        perks_enabled=False,
        state_mode='start_of_run',
        trace_mode='contributors',
    )

    surface_ids = {row.surface_id for row in response.resolved_surface_rows}
    resolved = {row.surface_id: row for row in response.resolved_surface_rows}
    assert response.family_id == 'progression_start_of_run'
    assert 'state::tower.hp' in surface_ids
    assert 'state::tower.defense_pct' in surface_ids
    assert 'state::tower.free_attack_upgrade_chance_pct' in surface_ids
    module_visibility_surfaces = {
        'state::module.multiverse_nexus.synced_uw_cooldown_offset_s',
        'state::module.om_chip.boss_reflection_multiplier',
        'state::module.om_chip.reflected_damage_taken_mult_x',
        'state::module.singularity_harness.bot_range_bonus_m',
    }
    assert module_visibility_surfaces <= surface_ids
    assert resolved[
        'state::module.multiverse_nexus.synced_uw_cooldown_offset_s'
    ].final_value == pytest.approx(-10.0)
    assert resolved['state::module.multiverse_nexus.synced_uw_cooldown_offset_s'].status == 'resolved'
    assert resolved['state::module.om_chip.boss_reflection_multiplier'].status == 'gated_off'
    assert resolved['state::module.om_chip.reflected_damage_taken_mult_x'].status == 'gated_off'
    assert resolved['state::module.singularity_harness.bot_range_bonus_m'].status == 'gated_off'
    assert resolved['state::economy.interest_per_wave_pct'].status == 'resolved'
    assert resolved['state::economy.interest_per_wave_pct'].final_value == pytest.approx(7.16)
    expected_bot_plus = {
        'state::bot.plus.wildfire.unlocked': False,
        'state::bot.plus.titan_shock.unlocked': False,
        'state::bot.plus.bonus_cell.unlocked': False,
        'state::bot.plus.echoing_shot.unlocked': False,
        'state::bot.plus.maximum_power.unlocked': True,
    }
    for surface_id, expected_value in expected_bot_plus.items():
        assert surface_id in surface_ids
        assert resolved[surface_id].status == 'resolved'
        assert resolved[surface_id].value_type == 'bool'
        assert resolved[surface_id].final_value is expected_value


def test_run_stats_progression_bundle__applies_exact_max_rend_formula():
    from simulators.progression import resolve_run_stats_progression_bundle

    state = _base_account_state()
    start_response = resolve_run_stats_progression_bundle(
        account_state=state,
        family_id='progression_start_of_run',
        preset_name=state.default_preset,
        perks_enabled=False,
        state_mode='start_of_run',
        trace_mode='contributors',
    )

    start_resolved = {row.surface_id: row for row in start_response.resolved_surface_rows}
    assert start_resolved['state::tower.rend_armor_chance_pct'].status == 'resolved'
    assert start_resolved['state::tower.rend_armor_chance_pct'].final_value == pytest.approx(0.0)
    assert start_resolved['state::tower.rend_armor_multiplier'].status == 'resolved'
    assert start_resolved['state::tower.rend_armor_multiplier'].final_value == pytest.approx(0.0)

    response = resolve_run_stats_progression_bundle(
        account_state=state,
        family_id='progression_start_of_run',
        preset_name=state.default_preset,
        perks_enabled=False,
        state_mode='max_progression',
        trace_mode='contributors',
    )

    resolved = {row.surface_id: row for row in response.resolved_surface_rows}
    assert resolved['state::tower.rend_armor_chance_pct'].status == 'resolved'
    assert resolved['state::tower.rend_armor_chance_pct'].final_value == pytest.approx(36.0)
    assert resolved['state::tower.rend_armor_multiplier'].status == 'resolved'
    assert resolved['state::tower.rend_armor_multiplier'].final_value == pytest.approx(0.3672)
    assert resolved['state::tower.max_rend_multiplier'].status == 'resolved'
    assert resolved['state::tower.max_rend_multiplier'].final_value == pytest.approx(9.6)


def test_qe_checkpoint_surface_resolution__resolves_only_requested_progression_surfaces():
    from qe.routing import resolve_checkpoint_surfaces

    state = _base_account_state()
    response = resolve_checkpoint_surfaces(
        state,
        requested_surface_ids=(
            'state::tower.hp',
            'state::wall.hp',
        ),
        preset_name='Farming',
        family_id='progression_runtime_with_perks',
        perks_enabled=True,
    )

    surface_ids = tuple(row.surface_id for row in response.resolved_surface_rows)
    assert surface_ids == ('state::tower.hp', 'state::wall.hp')


def test_simulator_snapshot_resolver__avoids_progression_recalc_bridge(monkeypatch):
    import simulators.progression as progression_module
    from simulators.contracts import SimulatorCheckpointState
    from simulators.snapshot_resolver import SimulatorSnapshotResolver

    def _no_bridge(*args, **kwargs):
        raise AssertionError('snapshot resolver must not call ProgressionRecalcBridge.recompute')

    monkeypatch.setattr(progression_module.ProgressionRecalcBridge, 'recompute', _no_bridge)

    state = _base_account_state()
    resolution = SimulatorSnapshotResolver().resolve_checkpoint(
        account_state=state,
        checkpoint_state=SimulatorCheckpointState(workshop_levels_current={'Health': 1}),
        preset_name='Farming',
        requested_surface_ids=(
            'state::tower.hp',
            'state::wall.hp',
        ),
        family_id='progression_runtime_with_perks',
        perks_enabled=True,
    )

    assert resolution.diagnostics['resolver_kind'] == 'simulator_checkpoint_qe_light'
    assert set(resolution.resolved_values) == {'state::tower.hp', 'state::wall.hp'}


def test_simulator_snapshot_resolver__warm_checkpoint_resolution_is_subsecond():
    from simulators.contracts import SimulatorCheckpointState
    from simulators.snapshot_resolver import SimulatorSnapshotResolver

    state = _base_account_state()
    resolver = SimulatorSnapshotResolver()
    checkpoint = SimulatorCheckpointState(workshop_levels_current={'Health': 1})
    first = resolver.resolve_checkpoint(
        account_state=state,
        checkpoint_state=checkpoint,
        preset_name='Farming',
        requested_surface_ids=('state::tower.hp', 'state::wall.hp'),
        family_id='progression_runtime_with_perks',
        perks_enabled=True,
    )
    second = resolver.resolve_checkpoint(
        account_state=state,
        checkpoint_state=checkpoint,
        preset_name='Farming',
        requested_surface_ids=('state::tower.hp', 'state::wall.hp'),
        family_id='progression_runtime_with_perks',
        perks_enabled=True,
    )

    assert first.diagnostics['phase_timing_ms']['resolve_checkpoint_surfaces'] >= 0.0
    assert second.diagnostics['phase_timing_ms']['total_measured_ms'] < 1000.0
