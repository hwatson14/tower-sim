from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.family_baseline_materializer import BaselineContributorRow, FamilyBaselineContributorMap, FamilyBaselineMaterializer
from engine.state_identity import StateIdentity
from engine.stat_query_kernel import OverlayApplicator, StatQueryKernel
from models.stat_input import StatInput


def _progression_baseline() -> FamilyBaselineContributorMap:
    identity = StateIdentity('acct_demo_v1', 'loadout_demo_farm', 'scn_progression_no_perks', 'branch_base')
    return FamilyBaselineMaterializer().materialize_from_rows(
        identity,
        'progression_runtime_no_perks',
        (
            StatInput(
                stat_name='Enemy Attack Level Skip',
                source_family='workshop',
                source_name='Enemy Attack Level Skip',
                value=25,
                value_type='integer_pct',
                stage='account_state',
                contributor_id='workshop.enemy_attack_level_skip.base',
                provenance='workshop.track.enemy_attack_level_skip',
                destination_object_type='canonical_stat',
                destination_id='enemy_attack_level_skip_pct',
                kb_mapped=True,
            ),
            StatInput(
                stat_name='Enemy Attack Level Skip Relic',
                source_family='relic',
                source_name='Enemy Attack Level Skip',
                value=1.1,
                value_type='multiplier',
                stage='account_state',
                contributor_id='relic.enemy_attack_level_skip.multiplier',
                provenance='relics.enemy_attack_level_skip',
                destination_object_type='canonical_stat',
                destination_id='enemy_attack_level_skip_pct',
                kb_mapped=True,
            ),
        ),
    )


def _overlay(
    *,
    delta_id: str,
    runtime_branch_id: str,
    delta_type: str = 'workshop_mutation',
    target_scope: dict[str, object] | None = None,
    changed_contributors: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        'delta_id': delta_id,
        'baseline_runtime_branch_id': 'branch_base',
        'runtime_branch_id': runtime_branch_id,
        'affected_family_id': 'progression_runtime_no_perks',
        'delta_type': delta_type,
        'target_scope': target_scope or {'surface_ids': ['state::tower.enemy_attack_level_skip_pct']},
        'changed_contributors': changed_contributors or [],
        'changed_masks': [],
        'changed_assertions': [],
        'provenance_note': 'wave free-upgrade event',
    }


def test_worked_example_baseline_contributor_map_rows_match_r86_examples():
    identity = StateIdentity(
        account_snapshot_id='acct_demo_v1',
        loadout_id='loadout_demo_farm',
        scenario_id='scn_progression_no_perks',
        runtime_branch_id='branch_base',
    )
    rows = (
        StatInput(
            stat_name='Free Attack Upgrade',
            source_family='workshop',
            source_name='Free Attack Upgrade',
            value=49,
            value_type='integer_pct',
            stage='account_state',
            contributor_id='workshop.free_attack_upgrade.base',
            provenance='workshop.track.free_attack_upgrade',
            destination_object_type='canonical_stat',
            destination_id='free_attack_upgrade_chance_pct',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Free Upgrades',
            source_family='card',
            source_name='Free Upgrades',
            value=1.20,
            value_type='multiplier',
            stage='loadout_resolved',
            contributor_id='card.free_upgrades.multiplier',
            provenance='cards.free_upgrades',
            destination_object_type='canonical_stat',
            destination_id='free_upgrade_multiplier',
            kb_mapped=True,
        ),
    )

    baseline = FamilyBaselineMaterializer().materialize_from_rows(identity, 'progression_runtime_no_perks', rows)

    assert baseline.account_snapshot_id == 'acct_demo_v1'
    active_rows = [row.__dict__ for row in baseline.contributor_rows if row.active]
    assert [row.__dict__ for row in baseline.contributor_rows_by_surface['state::tower.enemy_attack_level_skip_pct']] == [
        {
            'surface_id': 'state::tower.enemy_attack_level_skip_pct',
            'surface_class': 'surface',
            'domain': 'progression',
            'source_class': 'base',
            'composition_stage': 'gate_enable_disable',
            'contributor_id': 'query_placeholder::state::tower.enemy_attack_level_skip_pct',
            'value': False,
            'value_type': 'scalar',
            'active': False,
            'gate_reason': 'surface_absent_from_bound_inputs',
            'provenance_ref': 'engine.family_baseline_materializer.placeholder',
        }
    ]
    assert active_rows == [
        {
            'surface_id': 'state::tower.free_attack_upgrade_chance_pct',
            'surface_class': 'surface',
            'domain': 'progression',
            'source_class': 'workshop',
            'composition_stage': 'additive_pre_cap',
            'contributor_id': 'workshop.free_attack_upgrade.base',
            'value': 49,
            'value_type': 'integer_pct',
            'active': True,
            'gate_reason': None,
            'provenance_ref': 'workshop.track.free_attack_upgrade',
        },
        {
            'surface_id': 'support_surface::free_upgrade_multiplier',
            'surface_class': 'surface',
            'domain': 'progression',
            'source_class': 'cards',
            'composition_stage': 'multiplicative',
            'contributor_id': 'card.free_upgrades.multiplier',
            'value': 1.20,
            'value_type': 'scalar',
            'active': True,
            'gate_reason': None,
            'provenance_ref': 'cards.free_upgrades',
        },
    ]


def test_overlay_applicator_supports_replace_add_remove_and_multiply_without_mutating_baseline():
    baseline = _progression_baseline()
    overlay = _overlay(
        delta_id='delta_progression_wave_001',
        runtime_branch_id='branch_wave_187',
        changed_contributors=[
            {
                'contributor_id': 'workshop.enemy_attack_level_skip.base',
                'new_value': 27,
            },
            {
                'operation': 'multiply',
                'contributor_id': 'relic.enemy_attack_level_skip.multiplier',
                'factor': 2,
            },
            {
                'operation': 'add',
                'surface_id': 'state::tower.enemy_attack_level_skip_pct',
                'surface_class': 'surface',
                'domain': 'progression',
                'source_class': 'cards',
                'composition_stage': 'additive_pre_cap',
                'contributor_id': 'card.enemy_attack_level_skip.bonus',
                'new_value': 3,
                'value_type': 'integer_pct',
                'provenance_ref': 'cards.enemy_attack_level_skip',
            },
            {
                'operation': 'remove',
                'contributor_id': 'card.enemy_attack_level_skip.bonus',
            },
        ],
    )

    applied = OverlayApplicator().apply_overlay_delta(baseline, overlay)

    assert baseline.runtime_branch_id == 'branch_base'
    assert applied.runtime_branch_id == 'branch_wave_187'
    assert {
        row.contributor_id: row.value
        for row in baseline.contributor_rows
        if row.active
    } == {
        'relic.enemy_attack_level_skip.multiplier': 1.1,
        'workshop.enemy_attack_level_skip.base': 25,
    }
    assert {
        row.contributor_id: row.value
        for row in applied.contributor_rows
        if row.active
    } == {
        'relic.enemy_attack_level_skip.multiplier': 2.2,
        'workshop.enemy_attack_level_skip.base': 27,
    }


@pytest.mark.parametrize(
    ('change', 'match'),
    [
        (
            {
                'operation': 'add',
                'surface_id': 'state::tower.enemy_attack_level_skip_pct',
                'surface_class': 'context_resource',
                'domain': 'progression',
                'source_class': 'cards',
                'composition_stage': 'additive_pre_cap',
                'contributor_id': 'card.enemy_attack_level_skip.bad_surface_class',
                'new_value': 3,
                'value_type': 'integer_pct',
                'provenance_ref': 'cards.enemy_attack_level_skip',
            },
            'surface_class mismatch',
        ),
        (
            {
                'operation': 'add',
                'surface_id': 'state::tower.enemy_attack_level_skip_pct',
                'surface_class': 'surface',
                'domain': 'timing',
                'source_class': 'cards',
                'composition_stage': 'additive_pre_cap',
                'contributor_id': 'card.enemy_attack_level_skip.bad_domain',
                'new_value': 3,
                'value_type': 'integer_pct',
                'provenance_ref': 'cards.enemy_attack_level_skip',
            },
            'domain mismatch',
        ),
    ],
)
def test_overlay_applicator_rejects_metadata_drift_for_added_rows(change, match):
    baseline = _progression_baseline()
    overlay = _overlay(delta_id='delta_progression_wave_002', runtime_branch_id='branch_wave_188', changed_contributors=[change])

    with pytest.raises(ValueError, match=match):
        OverlayApplicator().apply_overlay_delta(baseline, overlay)


def test_overlay_applicator_rejects_metadata_drift_for_mutated_rows():
    baseline = FamilyBaselineContributorMap(
        account_snapshot_id='acct_demo_v1',
        loadout_id='loadout_demo_farm',
        scenario_id='scn_progression_no_perks',
        runtime_branch_id='branch_base',
        family_id='progression_runtime_no_perks',
        baseline_semantics={
            'deterministic': True,
            'immutable': True,
            'overlay_free': True,
            'bounded_to_declared_surface_set': True,
        },
        contributor_rows=(
            BaselineContributorRow(
                surface_id='state::tower.enemy_attack_level_skip_pct',
                surface_class='context_resource',
                domain='progression',
                source_class='workshop',
                composition_stage='additive_pre_cap',
                contributor_id='workshop.enemy_attack_level_skip.base',
                value=25,
                value_type='integer_pct',
                active=True,
                gate_reason=None,
                provenance_ref='workshop.track.enemy_attack_level_skip',
            ),
        ),
    )
    overlay = {
        'delta_id': 'delta_progression_wave_003',
        'baseline_runtime_branch_id': 'branch_base',
        'runtime_branch_id': 'branch_wave_189',
        'affected_family_id': 'progression_runtime_no_perks',
        'delta_type': 'workshop_mutation',
        'target_scope': {'surface_ids': ['state::tower.enemy_attack_level_skip_pct']},
        'changed_contributors': [
            {
                'contributor_id': 'workshop.enemy_attack_level_skip.base',
                'new_value': 27,
            },
        ],
        'changed_masks': [],
        'changed_assertions': [],
        'provenance_note': 'wave free-upgrade event',
    }

    with pytest.raises(ValueError, match='surface_class mismatch'):
        OverlayApplicator().apply_overlay_delta(baseline, overlay)


def test_overlay_applicator_rejects_family_delta_type_mismatches():
    baseline = _progression_baseline()
    overlay = _overlay(
        delta_id='delta_progression_wave_004',
        runtime_branch_id='branch_wave_190',
        delta_type='card_assertions',
        changed_contributors=[{'contributor_id': 'workshop.enemy_attack_level_skip.base', 'new_value': 27}],
    )

    with pytest.raises(ValueError, match="forbids overlay delta_type 'card_assertions'"):
        OverlayApplicator().apply_overlay_delta(baseline, overlay)


def test_overlay_applicator_rejects_surface_targets_outside_target_scope():
    identity = StateIdentity('acct_demo_v1', 'loadout_demo_farm', 'scn_progression_no_perks', 'branch_base')
    baseline = FamilyBaselineMaterializer().materialize_from_rows(
        identity,
        'progression_runtime_no_perks',
        (
            StatInput(
                stat_name='Enemy Attack Level Skip',
                source_family='workshop',
                source_name='Enemy Attack Level Skip',
                value=25,
                value_type='integer_pct',
                stage='account_state',
                contributor_id='workshop.enemy_attack_level_skip.base',
                provenance='workshop.track.enemy_attack_level_skip',
                destination_object_type='canonical_stat',
                destination_id='enemy_attack_level_skip_pct',
                kb_mapped=True,
            ),
            StatInput(
                stat_name='Free Upgrades',
                source_family='card',
                source_name='Free Upgrades',
                value=1.2,
                value_type='multiplier',
                stage='loadout_resolved',
                contributor_id='card.free_upgrades.multiplier',
                provenance='cards.free_upgrades',
                destination_object_type='canonical_stat',
                destination_id='free_upgrade_multiplier',
                kb_mapped=True,
            ),
        ),
    )
    overlay = _overlay(
        delta_id='delta_progression_wave_005',
        runtime_branch_id='branch_wave_191',
        target_scope={'surface_ids': ['support_surface::free_upgrade_multiplier']},
        changed_contributors=[
            {
                'operation': 'add',
                'surface_id': 'state::tower.enemy_attack_level_skip_pct',
                'surface_class': 'surface',
                'domain': 'progression',
                'source_class': 'cards',
                'composition_stage': 'additive_pre_cap',
                'contributor_id': 'card.enemy_attack_level_skip.outside_scope',
                'new_value': 3,
                'value_type': 'integer_pct',
                'provenance_ref': 'cards.enemy_attack_level_skip',
            }
        ],
    )

    with pytest.raises(ValueError, match='outside target_scope surface_ids'):
        OverlayApplicator().apply_overlay_delta(baseline, overlay)


def test_overlay_applicator_rejects_contributor_targets_outside_target_scope():
    baseline = _progression_baseline()
    overlay = _overlay(
        delta_id='delta_progression_wave_006',
        runtime_branch_id='branch_wave_192',
        target_scope={'contributor_ids': ['relic.enemy_attack_level_skip.multiplier']},
        changed_contributors=[{'contributor_id': 'workshop.enemy_attack_level_skip.base', 'new_value': 27}],
    )

    with pytest.raises(ValueError, match='outside target_scope contributor_ids'):
        OverlayApplicator().apply_overlay_delta(baseline, overlay)


@pytest.mark.parametrize(
    ('change', 'match'),
    [
        (
            {'contributor_id': 'workshop.enemy_attack_level_skip.base', 'new_value': 27, 'source_class': 'cards'},
            'cannot mutate contributor metadata fields',
        ),
        (
            {'operation': 'multiply', 'contributor_id': 'relic.enemy_attack_level_skip.multiplier', 'factor': 2, 'active': False},
            'cannot mutate contributor metadata fields',
        ),
        (
            {'operation': 'remove', 'contributor_id': 'workshop.enemy_attack_level_skip.base', 'new_value': 0},
            'cannot carry value or metadata mutation fields',
        ),
    ],
)
def test_overlay_applicator_rejects_illegal_contributor_mutation(change, match):
    baseline = _progression_baseline()
    overlay = _overlay(
        delta_id='delta_progression_wave_007',
        runtime_branch_id='branch_wave_193',
        changed_contributors=[change],
    )

    with pytest.raises(ValueError, match=match):
        OverlayApplicator().apply_overlay_delta(baseline, overlay)


def test_overlay_applicator_enforces_immutable_branch_lineage():
    baseline = _progression_baseline()

    with pytest.raises(ValueError, match='baseline_runtime_branch_id does not match'):
        OverlayApplicator().apply_overlay_delta(
            baseline,
            {
                **_overlay(
                    delta_id='delta_progression_wave_008',
                    runtime_branch_id='branch_wave_194',
                    changed_contributors=[{'contributor_id': 'workshop.enemy_attack_level_skip.base', 'new_value': 27}],
                ),
                'baseline_runtime_branch_id': 'branch_other',
            },
        )

    with pytest.raises(ValueError, match='must identify a new immutable branch'):
        OverlayApplicator().apply_overlay_delta(
            baseline,
            _overlay(
                delta_id='delta_progression_wave_009',
                runtime_branch_id='branch_base',
                changed_contributors=[{'contributor_id': 'workshop.enemy_attack_level_skip.base', 'new_value': 27}],
            ),
        )


def test_query_kernel_returns_worked_example_resolved_rows_contributor_rows_and_trace():
    identity = StateIdentity('acct_demo_v1', 'loadout_demo_tourney', 'scn_timing_demo', 'branch_base')
    baseline = FamilyBaselineMaterializer().materialize_from_rows(
        identity,
        'timing_tournament_no_perks',
        (
            StatInput(
                stat_name='Recovery Package Chance Workshop',
                source_family='workshop',
                source_name='Recovery Package Chance',
                value=18,
                value_type='integer_pct',
                stage='account_state',
                contributor_id='workshop.recovery_package_chance.base',
                provenance='workshop.track.recovery_package_chance',
                destination_object_type='canonical_stat',
                destination_id='package_chance_pct',
                kb_mapped=True,
            ),
            StatInput(
                stat_name='Recovery Package Chance Card',
                source_family='card',
                source_name='Recovery Package Chance',
                value=15,
                value_type='integer_pct',
                stage='loadout_resolved',
                contributor_id='card.recovery_package_chance',
                provenance='cards.recovery_package_chance',
                destination_object_type='canonical_stat',
                destination_id='package_chance_pct',
                kb_mapped=True,
            ),
            StatInput(
                stat_name='Galaxy Compressor Cooldown Reduction',
                source_family='module',
                source_name='Galaxy Compressor',
                value=13,
                value_type='seconds',
                stage='loadout_resolved',
                contributor_id='module.gcomp.cooldown_reduction',
                provenance='modules.galaxy_compressor.cooldown_reduction',
                destination_object_type='support_surface',
                destination_id='timing.gcomp_cooldown_reduction_seconds',
                kb_mapped=True,
            ),
        ),
    )

    response = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=(
            'canonical_stat::package_chance_pct',
            'support_surface::timing.gcomp_cooldown_reduction_seconds',
        ),
        trace_mode='full_trace',
    )

    assert response.family_id == 'timing_tournament_no_perks'
    assert [row.__dict__ for row in response.resolved_surface_rows] == [
        {
            'surface_id': 'canonical_stat::package_chance_pct',
            'final_value': 33,
            'value_type': 'integer_pct',
            'status': 'resolved',
        },
        {
            'surface_id': 'support_surface::timing.gcomp_cooldown_reduction_seconds',
            'final_value': 13,
            'value_type': 'seconds',
            'status': 'resolved',
        },
    ]
    contributor = next(row for row in response.contributor_rows if row.contributor_id == 'card.recovery_package_chance')
    assert contributor.surface_id == 'canonical_stat::package_chance_pct'
    assert contributor.source_class == 'cards'
    assert contributor.composition_stage == 'additive_pre_cap'
    assert contributor.active is True
    assert contributor.gate_reason is None
    assert contributor.provenance_ref == 'cards.recovery_package_chance'
    assert response.dependency_trace['requested_surface_ids'] == (
        'canonical_stat::package_chance_pct',
        'support_surface::timing.gcomp_cooldown_reduction_seconds',
    )
    assert 'canonical_stat::package_chance_pct' in response.dependency_trace['dependency_closure']
    assert 'support_surface::timing.gcomp_cooldown_reduction_seconds' in response.dependency_trace['dependency_closure']


@pytest.mark.parametrize('trace_mode', ['none', 'contributors', 'full_trace'])
def test_query_kernel_accepts_contract_trace_modes(trace_mode: str):
    identity = StateIdentity('acct_demo_v1', 'loadout_demo_tourney', 'scn_timing_demo', 'branch_base')
    baseline = FamilyBaselineMaterializer().materialize_from_rows(
        identity,
        'timing_tournament_no_perks',
        (
            StatInput(
                stat_name='Recovery Package Chance Workshop',
                source_family='workshop',
                source_name='Recovery Package Chance',
                value=18,
                value_type='integer_pct',
                stage='account_state',
                contributor_id='workshop.recovery_package_chance.base',
                provenance='workshop.track.recovery_package_chance',
                destination_object_type='canonical_stat',
                destination_id='package_chance_pct',
                kb_mapped=True,
            ),
        ),
    )

    response = StatQueryKernel().resolve_surfaces(baseline, ('canonical_stat::package_chance_pct',), trace_mode=trace_mode)

    assert response.resolved_surface_rows[0].final_value == 18
    if trace_mode == 'none':
        assert response.contributor_rows == ()
    else:
        assert len(response.contributor_rows) == 1
