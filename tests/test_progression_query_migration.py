from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.progression_recalc_bridge import (
    materialize_progression_family_baseline,
    resolve_progression_consumer_bundle,
    resolve_progression_family_query,
)
from engine.stat_query_kernel import StatQueryKernel
from tests.helpers import build_state


def test_progression_query_helper_matches_direct_kernel_resolution_without_perks():
    state = build_state()
    requested_surface_ids = (
        'canonical_stat::enemy_attack_level_skip_pct',
        'canonical_stat::enemy_health_level_skip_pct',
        'support_surface::free_upgrade_multiplier',
    )

    helper_response = resolve_progression_family_query(
        account_state=state,
        family_id='progression_runtime_no_perks',
        preset_name='Farming',
        perks_enabled=False,
        requested_surface_ids=requested_surface_ids,
        trace_mode='full_trace',
    )
    baseline = materialize_progression_family_baseline(
        account_state=state,
        family_id='progression_runtime_no_perks',
        preset_name='Farming',
        perks_enabled=False,
    )
    direct_response = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=requested_surface_ids,
        trace_mode='full_trace',
    )

    assert helper_response.family_id == direct_response.family_id
    assert helper_response.resolved_surface_rows == direct_response.resolved_surface_rows
    assert helper_response.contributor_rows == direct_response.contributor_rows
    assert helper_response.dependency_trace == direct_response.dependency_trace


def test_progression_query_helper_matches_direct_kernel_resolution_with_perks():
    state = build_state()
    requested_surface_ids = (
        'canonical_stat::free_attack_upgrade_chance_pct',
        'canonical_stat::free_defense_upgrade_chance_pct',
        'canonical_stat::free_utility_upgrade_chance_pct',
    )

    helper_response = resolve_progression_family_query(
        account_state=state,
        family_id='progression_runtime_with_perks',
        preset_name='Farming',
        perks_enabled=True,
        requested_surface_ids=requested_surface_ids,
        trace_mode='contributors',
    )
    baseline = materialize_progression_family_baseline(
        account_state=state,
        family_id='progression_runtime_with_perks',
        preset_name='Farming',
        perks_enabled=True,
    )
    direct_response = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=requested_surface_ids,
        trace_mode='contributors',
    )

    assert helper_response.family_id == direct_response.family_id
    assert helper_response.resolved_surface_rows == direct_response.resolved_surface_rows
    assert helper_response.contributor_rows == direct_response.contributor_rows
    assert helper_response.dependency_trace == direct_response.dependency_trace


def test_progression_consumer_bundle_helper_matches_family_query_for_declared_bundle():
    state = build_state()
    bundle_response = resolve_progression_consumer_bundle(
        account_state=state,
        consumer_id='progression_runtime',
        bundle_id='progression_free_upgrades',
        family_id='progression_runtime_with_perks',
        preset_name='Farming',
        perks_enabled=True,
        include_optional_surface_ids=('support_surface::free_upgrade_multiplier',),
        trace_mode='contributors',
    )
    family_response = resolve_progression_family_query(
        account_state=state,
        family_id='progression_runtime_with_perks',
        preset_name='Farming',
        perks_enabled=True,
        requested_surface_ids=(
            'canonical_stat::free_attack_upgrade_chance_pct',
            'canonical_stat::free_defense_upgrade_chance_pct',
            'canonical_stat::free_utility_upgrade_chance_pct',
            'support_surface::free_upgrade_multiplier',
        ),
        trace_mode='contributors',
    )

    assert bundle_response.family_id == family_response.family_id
    assert bundle_response.resolved_surface_rows == family_response.resolved_surface_rows
    assert bundle_response.contributor_rows == family_response.contributor_rows
    assert bundle_response.dependency_trace == family_response.dependency_trace
