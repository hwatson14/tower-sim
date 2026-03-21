from __future__ import annotations

from dataclasses import FrozenInstanceError
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.family_baseline_materializer import FamilyBaselineMaterializer
from engine.state_identity import compile_stat_inputs_with_identity
from tests.helpers import build_state



def test_progression_family_materializer_is_deterministic_and_immutable():
    state = build_state()
    materializer = FamilyBaselineMaterializer()

    bound_a = compile_stat_inputs_with_identity(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
        perks_enabled=False,
    )
    bound_b = compile_stat_inputs_with_identity(
        build_state(),
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
        perks_enabled=False,
    )

    baseline_a = materializer.materialize(bound_a, 'progression_runtime_no_perks')
    baseline_b = materializer.materialize(bound_b, 'progression_runtime_no_perks')

    assert baseline_a.fingerprint() == baseline_b.fingerprint()
    assert baseline_a.family_id == 'progression_runtime_no_perks'
    assert dict(baseline_a.baseline_semantics) == {
        'deterministic': True,
        'immutable': True,
        'overlay_free': True,
        'bounded_to_declared_surface_set': True,
    }
    assert baseline_a.contributor_rows
    with pytest.raises(FrozenInstanceError):
        baseline_a.contributor_rows += ()



def test_progression_family_materializer_normalizes_rows_to_contract_shape():
    state = build_state()
    materializer = FamilyBaselineMaterializer()
    bound = compile_stat_inputs_with_identity(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
        perks_enabled=False,
    )

    baseline = materializer.materialize(bound, 'progression_runtime_no_perks')
    rows_by_surface = baseline.contributor_rows_by_surface

    assert set(rows_by_surface).issubset(
        {
            'canonical_stat::tower_hp',
            'canonical_stat::wall_hp',
            'canonical_stat::tower_defense_pct',
            'canonical_stat::tower_thorns_damage_pct',
            'canonical_stat::tower_orb_count',
            'canonical_stat::tower_orb_speed_rpm',
            'canonical_stat::free_attack_upgrade_chance_pct',
            'canonical_stat::free_defense_upgrade_chance_pct',
            'canonical_stat::free_utility_upgrade_chance_pct',
            'canonical_stat::enemy_attack_level_skip_pct',
            'canonical_stat::enemy_health_level_skip_pct',
            'support_surface::free_upgrade_multiplier',
        }
    )
    free_upgrade_support = rows_by_surface['support_surface::free_upgrade_multiplier']
    assert all(row.composition_stage == 'multiplicative' for row in free_upgrade_support)
    assert all(row.surface_class == 'context_resource' for row in free_upgrade_support)
    assert all(row.domain == 'progression' for row in free_upgrade_support)
    tower_hp_sources = {row.source_class for row in rows_by_surface['canonical_stat::tower_hp']}
    assert {'labs', 'workshop'}.issubset(tower_hp_sources)
    assert all(row.surface_class == 'surface' for row in rows_by_surface['canonical_stat::tower_hp'])
    assert all(row.domain == 'progression' for row in rows_by_surface['canonical_stat::tower_hp'])
    assert all(row.provenance_ref for row in baseline.contributor_rows)
    assert all(row.contributor_id for row in baseline.contributor_rows)



def test_timing_family_materializer_is_bounded_to_timing_surface_set():
    state = build_state()
    materializer = FamilyBaselineMaterializer()
    bound = compile_stat_inputs_with_identity(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
        perks_enabled=False,
    )

    baseline = materializer.materialize(bound, 'timing_tournament_no_perks')

    assert baseline.family_id == 'timing_tournament_no_perks'
    assert baseline.contributor_rows
    assert {row.surface_id for row in baseline.contributor_rows}.issubset(
        {
            'canonical_stat::package_chance_pct',
            'mechanic_param::uw.black_hole.cooldown_seconds',
            'mechanic_param::uw.black_hole.duration_seconds',
            'mechanic_param::uw.golden_tower.cooldown_seconds',
            'mechanic_param::uw.golden_tower.duration_seconds',
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
        }
    )
    assert 'canonical_stat::tower_hp' not in {row.surface_id for row in baseline.contributor_rows}
    assert all(row.domain in {'timing', 'ultimate_weapons', 'modules', 'cards'} for row in baseline.contributor_rows)



def test_materialize_from_rows_rejects_unknown_family_before_iterating_inputs():
    materializer = FamilyBaselineMaterializer()

    def _rows():
        raise AssertionError('stat_inputs iterable should not be consumed for unsupported family ids')
        yield

    with pytest.raises(ValueError, match='Unsupported family_id'):
        materializer.materialize_from_rows(
            identity=compile_stat_inputs_with_identity(
                build_state(),
                preset_name='Farming',
                state_mode='start_of_run',
                runtime_branch_id='branch_base',
                perks_enabled=False,
            ).binding.identity,
            family_id='not_a_real_family',
            stat_inputs=_rows(),
        )


@pytest.mark.parametrize(
    ('family_id', 'state_mode', 'perks_enabled', 'scenario_mode_id', 'match'),
    [
        ('progression_runtime_no_perks', 'max_progression', False, 'progression', 'requires state_mode'),
        ('progression_runtime_no_perks', 'start_of_run', True, 'progression', 'requires perks_enabled'),
        ('progression_runtime_no_perks', 'start_of_run', False, 'farming', 'requires scenario mode_id'),
    ],
)
def test_family_compatibility_assertions_fail_closed(family_id, state_mode, perks_enabled, scenario_mode_id, match):
    with pytest.raises(ValueError, match=match):
        FamilyBaselineMaterializer().assert_family_compatibility(
            family_id=family_id,
            state_mode=state_mode,
            perks_enabled=perks_enabled,
            scenario_mode_id=scenario_mode_id,
        )
