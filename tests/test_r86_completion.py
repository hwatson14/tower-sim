from __future__ import annotations

import statistics
from pathlib import Path
import sys
from time import perf_counter

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import compilers.stat_input_compiler as stat_input_compiler
from compilers.stat_input_compiler import compile_stat_inputs
from engine import query_routing
from engine.incremental_recalc_runtime import IncrementalRecalcRuntime
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.progression_recalc_bridge import (
    ProgressionRecalcBridge,
    ProgressionRecalcRequest,
    materialize_progression_family_baseline,
    resolve_progression_family_query,
)
from engine.scenario_engine import ScenarioConfig
from engine.stat_engine import resolve_stats
from engine.stat_query_kernel import StatQueryKernel
from engine.timing_engine import (
    compile_timing_family_rows,
    materialize_timing_family_baseline,
    resolve_timing_family_query,
)
from helpers import build_family_baseline, build_state, timing_family_context


def _state():
    return build_state()


def _timing_family_config(family_id: str) -> tuple[ScenarioConfig, bool, str]:
    return timing_family_context(family_id)


def test_stat_input_compiler_uses_query_engine_owned_routing_authority():
    assert stat_input_compiler.compiler_routing_indexes is query_routing.compiler_routing_indexes
    assert stat_input_compiler.bind_kb_fields is query_routing.bind_kb_fields
    assert stat_input_compiler.bind_alias_destination is query_routing.bind_alias_destination
    assert stat_input_compiler.bind_destination is query_routing.bind_destination
    assert stat_input_compiler.bind_perk_effect_destination is query_routing.bind_perk_effect_destination
    assert stat_input_compiler.WORKSHOP_IDS_TO_CONTRIBUTOR is query_routing.WORKSHOP_IDS_TO_CONTRIBUTOR
    assert stat_input_compiler.LAB_APPLICATION_TARGET_TO_DESTINATION is query_routing.LAB_APPLICATION_TARGET_TO_DESTINATION
    assert not hasattr(stat_input_compiler, '_load_mapping_index')
    assert not hasattr(stat_input_compiler, '_bind_kb_fields')
    assert not hasattr(stat_input_compiler, '_bind_alias_destination')
    assert not hasattr(stat_input_compiler, '_bind_destination')
    assert not hasattr(stat_input_compiler, '_bind_perk_effect_destination')


@pytest.mark.parametrize(
    ('family_id', 'requested_surface_ids'),
    [
        (
            'progression_runtime_no_perks',
            (
                'support_surface::free_upgrade_multiplier',
            ),
        ),
        (
            'progression_runtime_with_perks',
            (
                'support_surface::free_upgrade_multiplier',
            ),
        ),
    ],
)
def test_progression_query_kernel_support_surfaces_match_canonical_stat_engine(family_id: str, requested_surface_ids: tuple[str, ...]):
    state = _state()
    perks_enabled = family_id.endswith('with_perks')
    stat_inputs = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=perks_enabled,
    )
    reference = resolve_stats(stat_inputs)
    response = resolve_progression_family_query(
        account_state=state,
        family_id=family_id,
        preset_name='Farming',
        perks_enabled=perks_enabled,
        requested_surface_ids=requested_surface_ids,
        trace_mode='contributors',
    )

    for row in response.resolved_surface_rows:
        reference_surface_id = {
            'support_surface::free_upgrade_multiplier': 'canonical_stat::free_upgrade_multiplier',
        }.get(row.surface_id, row.surface_id)
        assert reference_surface_id in reference.rows
        reference_row = reference.rows[reference_surface_id]
        assert reference_row.status == 'resolved'
        assert row.status == reference_row.status
        assert row.final_value == pytest.approx(reference_row.final_value, rel=1e-9, abs=1e-9)


@pytest.mark.parametrize(
    ('family_id', 'requested_surface_ids'),
    [
        (
            'progression_runtime_no_perks',
            (
                'state::tower.enemy_attack_level_skip_pct',
                'state::tower.enemy_health_level_skip_pct',
            ),
        ),
        (
            'progression_runtime_with_perks',
            (
                'state::tower.free_attack_upgrade_chance_pct',
                'state::tower.free_defense_upgrade_chance_pct',
                'state::tower.free_utility_upgrade_chance_pct',
            ),
        ),
    ],
)
def test_progression_bounded_executor_publishable_surfaces_match_canonical_stat_engine(family_id: str, requested_surface_ids: tuple[str, ...]):
    state = _state()
    perks_enabled = family_id.endswith('with_perks')
    stat_inputs = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=perks_enabled,
    )
    reference = resolve_stats(stat_inputs)
    candidate = IncrementalSubsetExecutor().execute(
        stat_inputs,
        requested_surface_ids,
        family_id=family_id,
    )

    for surface_id in requested_surface_ids:
        reference_surface_id = {
            'state::tower.enemy_attack_level_skip_pct': 'canonical_stat::enemy_attack_level_skip_pct',
            'state::tower.enemy_health_level_skip_pct': 'canonical_stat::enemy_health_level_skip_pct',
            'state::tower.free_attack_upgrade_chance_pct': 'canonical_stat::free_attack_upgrade_chance_pct',
            'state::tower.free_defense_upgrade_chance_pct': 'canonical_stat::free_defense_upgrade_chance_pct',
            'state::tower.free_utility_upgrade_chance_pct': 'canonical_stat::free_utility_upgrade_chance_pct',
        }.get(surface_id, surface_id)
        assert surface_id in candidate
        assert reference_surface_id in reference.rows
        assert candidate[surface_id].status == reference.rows[reference_surface_id].status == 'resolved'
        assert candidate[surface_id].final_value == pytest.approx(reference.rows[reference_surface_id].final_value, rel=1e-9, abs=1e-9)


@pytest.mark.parametrize(
    'family_id',
    [
        'timing_tournament_no_perks',
        'timing_farm_with_perks',
        'timing_scenario_probe',
    ],
)
def test_timing_declared_query_surfaces_match_canonical_stat_engine(family_id: str):
    state = _state()
    scenario_config, perks_enabled, preset_name = _timing_family_config(family_id)
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        perks_enabled=perks_enabled,
    )
    reference = resolve_stats(list(timing_rows))
    requested_surface_ids = tuple(
        surface_id
        for surface_id in (
            'canonical_stat::package_chance_pct',
            'support_surface::timing.gcomp_cooldown_reduction_seconds',
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
        )
        if surface_id in reference.rows
    )
    assert requested_surface_ids

    response = resolve_timing_family_query(
        account_state=state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        requested_surface_ids=requested_surface_ids,
        perks_enabled=perks_enabled,
        trace_mode='contributors',
    )

    for row in response.resolved_surface_rows:
        reference_row = reference.rows[row.surface_id]
        assert reference_row.status == 'resolved'
        assert row.status == reference_row.status
        assert row.final_value == pytest.approx(reference_row.final_value, rel=1e-9, abs=1e-9)


def test_progression_overlay_and_invalidation_plan_publish_guarded_matches_bounded_reference():
    state = _state()
    original_level = int(state.workshop['Enemy Attack Level Skip'].preset_levels['Farming'])
    plan = IncrementalRecalcRuntime().plan_from_workshop_overrides({'Enemy Attack Level Skip': original_level + 1})
    assert plan.fallback_required is False
    assert 'state::tower.enemy_attack_level_skip_pct' in plan.dirty_nodes
    assert 'runtime_consumer::wave_progression.attack_wave' in plan.runtime_consumer_ids

    bridge = ProgressionRecalcBridge()
    patched_state = bridge.apply_workshop_overrides(
        state,
        preset_name='Farming',
        workshop_levels_current={'Enemy Attack Level Skip': original_level + 1},
    )
    patched_reference = resolve_stats(
        compile_stat_inputs(
            patched_state,
            preset_name='Farming',
            state_mode='start_of_run',
            perks_enabled=False,
        )
    )
    cached_reference = bridge.recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Enemy Attack Level Skip': original_level},
            recompute_mode='full_safe',
        )
    )
    published = bridge.recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Enemy Attack Level Skip': original_level + 1},
            recompute_mode='incremental_cached_publish_guarded',
            cached_reference_statbook=cached_reference.statbook,
            cached_reference_workshop_levels_current={'Enemy Attack Level Skip': original_level},
            cached_reference_fingerprint=cached_reference.incremental_diagnostics['cache_fingerprint'],
        )
    )

    assert published.incremental_diagnostics['status'] == 'published_candidate_overlay_over_cached_reference'
    assert published.incremental_diagnostics['cache_validation']['is_valid'] is True
    for surface_id in plan.publishable_dirty_nodes:
        reference_surface_id = {
            'state::tower.enemy_attack_level_skip_pct': 'canonical_stat::enemy_attack_level_skip_pct',
            'state::tower.enemy_health_level_skip_pct': 'canonical_stat::enemy_health_level_skip_pct',
            'state::tower.free_attack_upgrade_chance_pct': 'canonical_stat::free_attack_upgrade_chance_pct',
            'state::tower.free_defense_upgrade_chance_pct': 'canonical_stat::free_defense_upgrade_chance_pct',
            'state::tower.free_utility_upgrade_chance_pct': 'canonical_stat::free_utility_upgrade_chance_pct',
        }.get(surface_id, surface_id)
        assert surface_id in published.statbook.rows
        assert reference_surface_id in patched_reference.rows
        assert published.statbook.rows[surface_id].final_value == pytest.approx(
            patched_reference.rows[reference_surface_id].final_value,
            rel=1e-9,
            abs=1e-9,
        )


@pytest.mark.expensive
def test_progression_overlay_and_invalidation_plan_runtime_publication_matches_bounded_bundle():
    state = _state()
    original_level = int(state.workshop['Enemy Attack Level Skip'].preset_levels['Farming'])
    bridge = ProgressionRecalcBridge()
    patched_state = bridge.apply_workshop_overrides(
        state,
        preset_name='Farming',
        workshop_levels_current={'Enemy Attack Level Skip': original_level + 1},
    )
    patched_reference = resolve_stats(
        compile_stat_inputs(
            patched_state,
            preset_name='Farming',
            state_mode='start_of_run',
            perks_enabled=False,
        )
    )
    cached_reference = ProgressionRecalcBridge().recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Enemy Attack Level Skip': original_level},
            recompute_mode='full_safe',
            runtime_target_display_wave=120,
            perks_enabled=False,
        )
    )
    result = ProgressionRecalcBridge().recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Enemy Attack Level Skip': original_level + 1},
            recompute_mode='incremental_cached_publish_guarded',
            runtime_target_display_wave=120,
            perks_enabled=False,
            cached_reference_statbook=cached_reference.statbook,
            cached_reference_workshop_levels_current={'Enemy Attack Level Skip': original_level},
            cached_reference_fingerprint=cached_reference.incremental_diagnostics['cache_fingerprint'],
        )
    )
    assert result.incremental_diagnostics['runtime_publication']['status'] == 'published_from_bounded_progression_bundle'
    assert result.statbook.rows['state::tower.enemy_attack_level_skip_pct'].final_value == pytest.approx(
        patched_reference.rows['canonical_stat::enemy_attack_level_skip_pct'].final_value,
        rel=1e-9,
        abs=1e-9,
    )


@pytest.mark.expensive
def test_progression_family_query_still_matches_direct_kernel_for_support_surface_reference_path():
    state = _state()
    baseline = build_family_baseline('progression_runtime_no_perks')
    direct_response = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('support_surface::free_upgrade_multiplier',),
        trace_mode='contributors',
    )
    helper_response = resolve_progression_family_query(
        account_state=state,
        family_id='progression_runtime_no_perks',
        preset_name='Farming',
        perks_enabled=False,
        requested_surface_ids=('support_surface::free_upgrade_multiplier',),
        trace_mode='contributors',
    )
    assert helper_response == direct_response


def _median_ms(fn, iterations: int = 11) -> float:
    samples = []
    for _ in range(iterations):
        start = perf_counter()
        fn()
        samples.append((perf_counter() - start) * 1000.0)
    return statistics.median(samples)


@pytest.mark.expensive
def test_r86_benchmarks_show_positive_value_for_progression_and_timing_queries():
    state = _state()

    progression_stat_inputs = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )
    progression_baseline = build_family_baseline('progression_runtime_no_perks')
    progression_request = (
        'state::tower.enemy_attack_level_skip_pct',
        'state::tower.enemy_health_level_skip_pct',
        'support_surface::free_upgrade_multiplier',
    )

    timing_config = ScenarioConfig(mode_id='farming', tier=14)
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=timing_config,
        perks_enabled=True,
    )
    timing_baseline = build_family_baseline('timing_farm_with_perks')
    timing_request = (
        'state::tower.package_chance_pct',
        'support_surface::timing.gcomp_cooldown_reduction_seconds',
    )

    kernel = StatQueryKernel()

    resolve_stats(progression_stat_inputs)
    kernel.resolve_surfaces(progression_baseline, progression_request, trace_mode='contributors')
    resolve_stats(list(timing_rows))
    kernel.resolve_surfaces(timing_baseline, timing_request, trace_mode='contributors')

    progression_reference_ms = _median_ms(lambda: resolve_stats(progression_stat_inputs))
    progression_query_ms = _median_ms(lambda: kernel.resolve_surfaces(progression_baseline, progression_request, trace_mode='contributors'))
    timing_reference_ms = _median_ms(lambda: resolve_stats(list(timing_rows)))
    timing_query_ms = _median_ms(lambda: kernel.resolve_surfaces(timing_baseline, timing_request, trace_mode='contributors'))

    assert progression_query_ms < progression_reference_ms
    assert timing_query_ms < timing_reference_ms
