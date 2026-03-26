from __future__ import annotations

from dataclasses import FrozenInstanceError
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.family_baseline_materializer import (
    BaselineContributorRow,
    FamilyBaselineMaterializer,
    _inject_free_upgrade_cross_surface_multipliers,
    _scale_enemy_skip_thorns_relic_values,
    _scale_survivability_relic_vault_values,
    _scale_wall_fortification_lab_value,
    load_family_surface_ids,
)
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

    assert set(rows_by_surface).issubset(load_family_surface_ids()['progression_runtime_no_perks'])
    free_upgrade_support = rows_by_surface['support_surface::free_upgrade_multiplier']
    assert all(row.composition_stage == 'multiplicative' for row in free_upgrade_support)
    assert all(row.surface_class == 'surface' for row in free_upgrade_support)
    assert all(row.domain == 'progression' for row in free_upgrade_support)
    tower_hp_sources = {row.source_class for row in rows_by_surface['state::tower.hp']}
    assert {'labs', 'workshop'}.issubset(tower_hp_sources)
    assert all(row.surface_class == 'surface' for row in rows_by_surface['state::tower.hp'])
    assert all(row.domain == 'progression' for row in rows_by_surface['state::tower.hp'])
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
    assert {row.surface_id for row in baseline.contributor_rows}.issubset(load_family_surface_ids()['timing_tournament_no_perks'])
    assert 'state::tower.hp' not in {row.surface_id for row in baseline.contributor_rows}
    assert all(row.domain in {'timing', 'ultimate_weapons', 'modules', 'cards'} for row in baseline.contributor_rows)


def test_materializer_backfills_declared_surfaces_with_gated_placeholders_when_inputs_are_absent():
    baseline = FamilyBaselineMaterializer().materialize_from_rows(
        identity=compile_stat_inputs_with_identity(
            build_state(),
            preset_name='Tourney',
            state_mode='start_of_run',
            runtime_branch_id='branch_base',
            perks_enabled=False,
        ).binding.identity,
        family_id='timing_tournament_no_perks',
        stat_inputs=(),
    )

    declared = load_family_surface_ids()['timing_tournament_no_perks']
    assert declared.issubset(set(baseline.contributor_rows_by_surface))
    placeholder = baseline.contributor_rows_by_surface['state::cards.wave_accelerator.spawn_rate_acceleration'][0]
    assert placeholder.active is False
    assert placeholder.composition_stage == 'gate_enable_disable'
    assert placeholder.gate_reason == 'surface_absent_from_bound_inputs'



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


# PH4-C tranche 1: free_upgrade cross-surface multiplier injection unit tests


def _make_row(surface_id: str, composition_stage: str, value: float = 1.0, active: bool = True) -> BaselineContributorRow:
    return BaselineContributorRow(
        surface_id=surface_id,
        surface_class='surface',
        domain='progression',
        source_class='workshop',
        composition_stage=composition_stage,
        contributor_id=f'test::{surface_id}',
        value=value,
        value_type='scalar',
        active=active,
        gate_reason=None,
        provenance_ref='test',
    )


_FREE_UPGRADE_SURFACES = frozenset({
    'state::tower.free_attack_upgrade_chance_pct',
    'state::tower.free_defense_upgrade_chance_pct',
    'state::tower.free_utility_upgrade_chance_pct',
    'support_surface::free_upgrade_multiplier',
})


def test_inject_free_upgrade_cross_surface_multipliers_injects_when_base_exists():
    multiplier_row = _make_row('support_surface::free_upgrade_multiplier', 'multiplicative', value=1.5)
    additive_row = _make_row('state::tower.free_attack_upgrade_chance_pct', 'additive_pre_cap', value=10.0)
    result = _inject_free_upgrade_cross_surface_multipliers([multiplier_row, additive_row], _FREE_UPGRADE_SURFACES)

    injected = [r for r in result if r.surface_id == 'state::tower.free_attack_upgrade_chance_pct' and r.composition_stage == 'multiplicative']
    assert len(injected) == 1
    assert injected[0].value == 1.5
    assert injected[0].source_class == 'workshop'


def test_inject_free_upgrade_cross_surface_multipliers_no_injection_without_base():
    multiplier_row = _make_row('support_surface::free_upgrade_multiplier', 'multiplicative', value=1.5)
    # No additive contributor for the chance surface
    result = _inject_free_upgrade_cross_surface_multipliers([multiplier_row], _FREE_UPGRADE_SURFACES)

    injected = [r for r in result if r.surface_id == 'state::tower.free_attack_upgrade_chance_pct' and r.composition_stage == 'multiplicative']
    assert injected == []


def test_inject_free_upgrade_cross_surface_multipliers_no_injection_without_multiplier():
    additive_row = _make_row('state::tower.free_attack_upgrade_chance_pct', 'additive_pre_cap', value=10.0)
    result = _inject_free_upgrade_cross_surface_multipliers([additive_row], _FREE_UPGRADE_SURFACES)

    assert result == [additive_row]


def test_inject_free_upgrade_cross_surface_multipliers_injects_into_all_three_surfaces():
    multiplier_row = _make_row('support_surface::free_upgrade_multiplier', 'multiplicative', value=1.5)
    attack_row = _make_row('state::tower.free_attack_upgrade_chance_pct', 'additive_pre_cap', value=10.0)
    defense_row = _make_row('state::tower.free_defense_upgrade_chance_pct', 'additive_pre_cap', value=5.0)
    # free_utility has no additive contributor - should NOT get injection
    rows = [multiplier_row, attack_row, defense_row]
    result = _inject_free_upgrade_cross_surface_multipliers(rows, _FREE_UPGRADE_SURFACES)

    attack_injected = [r for r in result if r.surface_id == 'state::tower.free_attack_upgrade_chance_pct' and r.composition_stage == 'multiplicative']
    defense_injected = [r for r in result if r.surface_id == 'state::tower.free_defense_upgrade_chance_pct' and r.composition_stage == 'multiplicative']
    utility_injected = [r for r in result if r.surface_id == 'state::tower.free_utility_upgrade_chance_pct' and r.composition_stage == 'multiplicative']

    assert len(attack_injected) == 1
    assert len(defense_injected) == 1
    assert utility_injected == []


# PH4-D: free_upgrade chance pct expensive parity tests (gap from tranche 1 — parity was
# confirmed manually but no @pytest.mark.expensive fixture was added at the time).


@pytest.mark.expensive
def test_progression_qe_matches_legacy_free_attack_upgrade_chance_pct():
    """QE value for state::tower.free_attack_upgrade_chance_pct matches legacy (tranche 1 parity closure)."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.free_attack_upgrade_chance_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.free_attack_upgrade_chance_pct')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::free_attack_upgrade_chance_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for free_attack_upgrade_chance_pct'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_free_defense_upgrade_chance_pct():
    """QE value for state::tower.free_defense_upgrade_chance_pct matches legacy (tranche 1 parity closure)."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.free_defense_upgrade_chance_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.free_defense_upgrade_chance_pct')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::free_defense_upgrade_chance_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for free_defense_upgrade_chance_pct'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_free_utility_upgrade_chance_pct():
    """QE value for state::tower.free_utility_upgrade_chance_pct matches legacy (tranche 1 parity closure)."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.free_utility_upgrade_chance_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.free_utility_upgrade_chance_pct')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::free_utility_upgrade_chance_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for free_utility_upgrade_chance_pct'
    )


# PH4-C tranche 2: enemy-skip and thorns pct composition fixes


_ENEMY_SKIP_THORNS_SURFACES = frozenset({
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
    'state::tower.thorns_damage_pct',
})


def _make_relic_row(surface_id: str, value: float) -> BaselineContributorRow:
    return BaselineContributorRow(
        surface_id=surface_id,
        surface_class='surface',
        domain='progression',
        source_class='relics',
        composition_stage='additive_pre_cap',
        contributor_id=f'relic__{surface_id}__pct',
        value=value,
        value_type='scalar',
        active=True,
        gate_reason=None,
        provenance_ref='test',
    )


def test_scale_enemy_skip_thorns_relic_values_scales_fraction_to_pct():
    """Relic contributor with fractional value [0, 1] on enemy-skip surface is scaled × 100."""
    relic_row = _make_relic_row('state::tower.enemy_attack_level_skip_pct', 0.02)
    result = _scale_enemy_skip_thorns_relic_values([relic_row])
    assert len(result) == 1
    assert result[0].value == pytest.approx(2.0)
    assert result[0].source_class == 'relics'
    assert result[0].composition_stage == 'additive_pre_cap'


def test_scale_enemy_skip_thorns_relic_values_no_scaling_outside_set():
    """Relic contributor on a surface NOT in the set is left unchanged."""
    relic_row = _make_relic_row('state::tower.hp', 0.51)
    result = _scale_enemy_skip_thorns_relic_values([relic_row])
    assert result[0].value == pytest.approx(0.51)


def test_scale_enemy_skip_thorns_relic_values_no_scaling_above_one():
    """Relic contributor with value > 1.0 on an enemy-skip surface is NOT scaled."""
    relic_row = _make_relic_row('state::tower.enemy_health_level_skip_pct', 2.0)
    result = _scale_enemy_skip_thorns_relic_values([relic_row])
    assert result[0].value == pytest.approx(2.0)


def test_scale_enemy_skip_thorns_relic_values_thorns_surface():
    """Relic contributor on thorns_damage_pct is scaled × 100."""
    relic_row = _make_relic_row('state::tower.thorns_damage_pct', 0.11)
    result = _scale_enemy_skip_thorns_relic_values([relic_row])
    assert result[0].value == pytest.approx(11.0)


@pytest.mark.expensive
def test_progression_qe_matches_legacy_enemy_attack_level_skip_pct():
    """QE value for enemy_attack_level_skip_pct matches legacy stat_resolution_core after tranche 2 fixes."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_engine import resolve_stats
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.enemy_attack_level_skip_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.enemy_attack_level_skip_pct')

    legacy_result = resolve_stats(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::enemy_attack_level_skip_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for enemy_attack_level_skip_pct'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_enemy_health_level_skip_pct():
    """QE value for enemy_health_level_skip_pct matches legacy stat_resolution_core after tranche 2 fixes."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_engine import resolve_stats
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.enemy_health_level_skip_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.enemy_health_level_skip_pct')

    legacy_result = resolve_stats(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::enemy_health_level_skip_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for enemy_health_level_skip_pct'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_thorns_damage_pct():
    """QE value for thorns_damage_pct matches legacy stat_resolution_core after tranche 2 fixes."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_engine import resolve_stats
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.thorns_damage_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.thorns_damage_pct')

    legacy_result = resolve_stats(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::tower_thorns_damage_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for thorns_damage_pct'
    )


# PH4-C tranche 4: tower_hp workshop-times-multipliers and wall_fortification_multiplier


def _make_mult_row(surface_id: str, source_class: str, value: float, active: bool = True) -> BaselineContributorRow:
    return BaselineContributorRow(
        surface_id=surface_id,
        surface_class='surface',
        domain='progression',
        source_class=source_class,
        composition_stage='multiplicative',
        contributor_id=f'{source_class}__{surface_id}',
        value=value,
        value_type='scalar',
        active=active,
        gate_reason=None,
        provenance_ref='test',
    )


def test_scale_survivability_relic_vault_values_scales_relic_fraction():
    """Relic contributor with fractional value [0, 1] on tower.hp is scaled to (1 + v)."""
    row = _make_mult_row('state::tower.hp', 'relics', 0.51)
    result = _scale_survivability_relic_vault_values([row])
    assert len(result) == 1
    assert result[0].value == pytest.approx(1.51)
    assert result[0].source_class == 'relics'
    assert result[0].composition_stage == 'multiplicative'


def test_scale_survivability_relic_vault_values_scales_vault_base_zero():
    """Vault (base class) contributor with value=0 on tower.hp is scaled to 1.0 (no-op factor)."""
    row = _make_mult_row('state::tower.hp', 'base', 0.0)
    result = _scale_survivability_relic_vault_values([row])
    assert result[0].value == pytest.approx(1.0)


def test_scale_survivability_relic_vault_values_no_scale_for_labs():
    """Labs contributor on tower.hp is NOT scaled (already in multiplier form)."""
    row = _make_mult_row('state::tower.hp', 'labs', 12.5)
    result = _scale_survivability_relic_vault_values([row])
    assert result[0].value == pytest.approx(12.5)


def test_scale_survivability_relic_vault_values_no_scale_outside_surface_set():
    """Relic contributor on a surface NOT in the survivability set is left unchanged."""
    row = _make_mult_row('state::tower.enemy_attack_level_skip_pct', 'relics', 0.51)
    result = _scale_survivability_relic_vault_values([row])
    assert result[0].value == pytest.approx(0.51)


def test_scale_wall_fortification_lab_value_converts_lab_percent_to_multiplier():
    """Labs contributor on wall_fortification_multiplier is converted: v -> 1 + v/100."""
    row = _make_mult_row('state::wall.fortification_multiplier', 'labs', 940.0)
    result = _scale_wall_fortification_lab_value([row])
    assert len(result) == 1
    assert result[0].value == pytest.approx(10.4)
    assert result[0].source_class == 'labs'


def test_scale_wall_fortification_lab_value_no_change_outside_surface():
    """Labs contributor on a different surface is NOT converted by the fortification scaler."""
    row = _make_mult_row('state::tower.hp', 'labs', 12.5)
    result = _scale_wall_fortification_lab_value([row])
    assert result[0].value == pytest.approx(12.5)


@pytest.mark.expensive
def test_progression_qe_matches_legacy_tower_hp():
    """QE value for state::tower.hp matches legacy after tranche 4 workshop-multipliers fix."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.hp',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.hp')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::tower_hp'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for tower_hp'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_wall_fortification_multiplier():
    """QE value for state::wall.fortification_multiplier matches legacy after tranche 4 lab-formula fix."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::wall.fortification_multiplier',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::wall.fortification_multiplier')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::wall_fortification_multiplier'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for wall_fortification_multiplier'
    )


# PH4-C tranche 5: remaining progression_v1 and timing_v1 surfaces
# (alias fix for primordial_collapse + parity confirmation for already-correct surfaces)


@pytest.mark.expensive
def test_progression_qe_matches_legacy_orb_count():
    """QE value for state::tower.orb_count matches legacy (simple additive sum, no formula fix needed)."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.orb_count',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.orb_count')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::tower_orb_count'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for orb_count'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_plasma_cannon_effect_pct():
    """QE value for state::cards.plasma_cannon.effect_pct matches legacy (scenario_adjustment, no fix needed)."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::cards.plasma_cannon.effect_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::cards.plasma_cannon.effect_pct')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['runtime_mechanic_param::cards.plasma_cannon.effect_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for plasma_cannon_effect_pct'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_orbital_augment_electron_count():
    """QE value for mechanic_param::module.orbital_augment.electron_count matches legacy (count surface, no fix needed)."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('mechanic_param::module.orbital_augment.electron_count',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'mechanic_param::module.orbital_augment.electron_count')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['mechanic_param::module.orbital_augment.electron_count'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for orbital_augment_electron_count'
    )


@pytest.mark.expensive
def test_progression_qe_matches_legacy_primordial_collapse_bh_damage_reduction_pct():
    """QE value for primordial_collapse.bh_damage_reduction_pct matches legacy after tranche 5 alias fix."""
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('mechanic_param::module.primordial_collapse.bh_damage_reduction_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'mechanic_param::module.primordial_collapse.bh_damage_reduction_pct')

    # Legacy uses the old destination_id name
    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['mechanic_param::module.primordial_collapse.in_bh_enemy_damage_reduction_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for primordial_collapse_bh_damage_reduction_pct'
    )


@pytest.mark.expensive
def test_timing_qe_matches_legacy_package_chance_pct():
    """QE value for state::tower.package_chance_pct matches legacy (timing_v1 surface, no fix needed)."""
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from engine.timing_engine import compile_timing_family_rows
    from engine.scenario_engine import ScenarioConfig
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('timing_tournament_no_perks')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.package_chance_pct',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.package_chance_pct')

    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150),
        perks_enabled=False,
    )
    legacy_result = fallback_resolve(list(timing_rows))
    legacy_val = legacy_result.rows['canonical_stat::package_chance_pct'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-6), (
        f'QE={qe_val} != legacy={legacy_val} for package_chance_pct'
    )


# PH4-C tranche 6: orb_speed_rpm workshop-times-multipliers fix


@pytest.mark.expensive
def test_progression_qe_matches_legacy_orb_speed_rpm():
    """QE value for state::tower.orb_speed_rpm matches legacy after tranche 6 fix.

    orb_speed_rpm uses the same unit=rpm multiplier-base formula as tower_hp:
    workshop base is additive, relic/vault/module_substat are multiplicative.
    Adding 'state::tower.orb_speed_rpm' to _SURVIVABILITY_WORKSHOP_MULTIPLIER_SURFACE_IDS
    enables the existing routing and relic/vault scaling to apply.
    """
    from compilers.stat_input_compiler import compile_stat_inputs
    from engine.stat_resolution_core import resolve_stats as fallback_resolve
    from engine.stat_query_kernel import StatQueryKernel
    from tests.helpers import build_family_baseline, build_state

    state = build_state()
    baseline = build_family_baseline('progression_start_of_run')
    qe_resp = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=('state::tower.orb_speed_rpm',),
        trace_mode='none',
    )
    qe_val = next(r.final_value for r in qe_resp.resolved_surface_rows
                  if r.surface_id == 'state::tower.orb_speed_rpm')

    legacy_result = fallback_resolve(compile_stat_inputs(state, preset_name='Farming', perks_enabled=False))
    legacy_val = legacy_result.rows['canonical_stat::tower_orb_speed_rpm'].final_value

    assert qe_val == pytest.approx(legacy_val, rel=1e-9), (
        f'QE={qe_val} != legacy={legacy_val} for orb_speed_rpm'
    )
