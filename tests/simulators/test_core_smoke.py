"""Simulator smoke tests for progression/timing public APIs."""
from __future__ import annotations

import sys
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


def test_tier_enemy_level_skip_reduction_continues_expected_late_tier_pattern():
    from simulators.scenario import _load_tier_battle_conditions

    tier_bcs = _load_tier_battle_conditions()

    assert float(tier_bcs[19]['enemy_level_skip_reduction']['value']) == pytest.approx(0.15)
    assert float(tier_bcs[20]['enemy_level_skip_reduction']['value']) == pytest.approx(0.175)
    assert float(tier_bcs[21]['enemy_level_skip_reduction']['value']) == pytest.approx(0.2)


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

    assert timing_statbook.rows["support_surface::scenario.bosses_per_day_effective"].status == "resolved"


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
    assert resolved["state::uw.black_hole.cooldown_seconds"].final_value == pytest.approx(200.0)
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
    assert response.family_id == 'progression_start_of_run'
    assert 'state::tower.hp' in surface_ids
    assert 'state::tower.defense_pct' in surface_ids
    assert 'state::tower.free_attack_upgrade_chance_pct' in surface_ids


def test_run_stats_progression_bundle__applies_exact_max_rend_formula():
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

    resolved = {row.surface_id: row for row in response.resolved_surface_rows}
    assert resolved['state::tower.max_rend_multiplier'].status == 'resolved'
    assert resolved['state::tower.max_rend_multiplier'].final_value == pytest.approx(8.0)


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
