from __future__ import annotations

from engine.query_routing import (
    NAMING_CONTRACT_PACK_V2_REMAP_PATH,
    pack_v2_naming_remap_rows,
    to_legacy_surface_id,
    to_v2_surface_id,
)
from engine.stat_query_kernel import StatQueryKernel
from engine.family_baseline_materializer import FamilyBaselineContributorMap, BaselineContributorRow
from engine.state_identity import StateIdentity


def _baseline_with_rows(*rows: BaselineContributorRow) -> FamilyBaselineContributorMap:
    identity = StateIdentity(
        account_snapshot_id='acct',
        loadout_id='loadout',
        scenario_id='scenario',
        runtime_branch_id='branch',
    )
    return FamilyBaselineContributorMap(
        account_snapshot_id=identity.account_snapshot_id,
        loadout_id=identity.loadout_id,
        scenario_id=identity.scenario_id,
        runtime_branch_id=identity.runtime_branch_id,
        family_id='economy',
        baseline_semantics={'phase_1_queryable': True},
        contributor_rows=rows,
    )


def test_pack_v2_remap_table_is_committed_and_supports_exact_and_pattern_rows() -> None:
    assert NAMING_CONTRACT_PACK_V2_REMAP_PATH.exists()
    assert len(pack_v2_naming_remap_rows()) >= 160

    assert to_v2_surface_id('canonical_stat::tower_damage') == 'state::tower.damage'
    assert to_v2_surface_id('runtime_mechanic_param::cards.plasma_cannon.effect_pct') == 'state::cards.plasma_cannon.effect_pct'
    assert to_v2_surface_id('mechanic_param::uw.black_hole.duration_seconds') == 'state::uw.black_hole.duration_seconds'
    assert to_v2_surface_id('environment_param::enemy.boss.health_multiplier') == 'context::enemy.boss.health_multiplier'

    assert to_legacy_surface_id('state::tower.damage') == 'canonical_stat::tower_damage'
    assert to_legacy_surface_id('state::uw.black_hole.duration_seconds') == 'mechanic_param::uw.black_hole.duration_seconds'
    assert to_legacy_surface_id('context::enemy.boss.health_multiplier') == 'environment_param::enemy.boss.health_multiplier'


def test_stat_query_kernel_accepts_v2_requested_surface_ids() -> None:
    kernel = StatQueryKernel()
    baseline = _baseline_with_rows(
        BaselineContributorRow(
            surface_id='runtime_mechanic_param::cards.plasma_cannon.effect_pct',
            surface_class='surface',
            domain='tower',
            source_class='cards',
            composition_stage='scenario_adjustment',
            contributor_id='card.plasma_cannon.effect',
            value=54.0,
            value_type='scalar',
            active=True,
            gate_reason=None,
            provenance_ref='test',
        ),
    )

    response = kernel.resolve_surfaces(baseline, ('state::cards.plasma_cannon.effect_pct',), trace_mode='contributors')

    assert response.resolved_surface_rows[0].surface_id == 'state::cards.plasma_cannon.effect_pct'
    assert response.resolved_surface_rows[0].final_value == 54
    assert response.contributor_rows[0].surface_id == 'state::cards.plasma_cannon.effect_pct'
    assert response.dependency_trace['requested_surface_ids'] == ('state::cards.plasma_cannon.effect_pct',)
