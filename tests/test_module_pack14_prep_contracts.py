from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def test_module_cost_truth_closes_pack14_canonical_rows_without_promoting_helper_rows():
    rows = _read_csv(ROOT / 'kb' / 'modules' / 'tables' / 'module-cost-truth.csv')
    by_id = {row['surface_id']: row for row in rows}

    assert by_id['module.draw.single.gems']['value'] == '20'
    assert by_id['module.draw.single.gems']['closure_class'] == 'canonical_kb_truth'
    assert by_id['module.draw.ten.gems']['value'] == '200'
    assert by_id['module.shatter.common.shards']['value'] == '5'
    assert by_id['module.shatter.rare.shards']['value'] == '10'
    assert by_id['module.assist.slot_unlock.epic.stones']['closure_class'] == 'canonical_kb_truth'

    helper_rows = [row for row in rows if row['closure_class'] == 'accepted_model_helper']
    assert {row['surface_id'] for row in helper_rows} == {
        'module.assist.unique_rarity.locked_to_epic.stones',
        'module.assist.unique_rarity.epic_to_legendary.stones',
        'module.assist.unique_rarity.legendary_to_mythic.stones',
        'module.assist.unique_rarity.mythic_to_ancestral.stones',
    }


def test_module_reroll_contract_fails_closed_on_numeric_ladder_invention():
    contract = yaml.safe_load((ROOT / 'kb' / 'modules' / 'contracts' / 'module-reroll-contract.yaml').read_text())
    constants = {
        row['constant_id']: row
        for row in _read_csv(ROOT / 'kb' / 'modules' / 'tables' / 'module-reroll-constants.csv')
    }

    assert contract['currency']['resource_id'] == 'reroll_shards'
    assert contract['lock_policy']['locking_increases_cost'] is True
    assert contract['numeric_cost_ladder']['source_closed'] is False
    assert contract['numeric_cost_ladder']['fail_closed'] is True
    assert contract['numeric_cost_ladder']['accepted_model_helper_allowed'] is False
    assert constants['module.reroll.currency']['value'] == 'reroll_shards'
    assert constants['module.reroll.locking_increases_cost']['value'] == 'true'
    assert constants['module.reroll.numeric_cost_ladder_closed']['value'] == 'false'


def test_optimizer_module_effects_bundle_stays_bounded_to_progression_family_surfaces():
    surface_contract = yaml.safe_load((ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-initial-surface-set.yaml').read_text())
    bundle_contract = yaml.safe_load((ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-consumer-bundles.yaml').read_text())
    overlay_requirements = yaml.safe_load((ROOT / 'kb' / 'modules' / 'contracts' / 'module-optimizer-overlay-requirements.yaml').read_text())

    progression = surface_contract['families']['progression_v1']
    progression_surfaces = {row['surface_id'] for row in progression['surfaces']}
    optimizer_bundle = next(
        bundle
        for consumer in bundle_contract['consumers']
        if consumer['consumer_id'] == 'optimizer_analysis'
        for bundle in consumer['bundles']
        if bundle['bundle_id'] == 'optimizer_module_effects'
    )
    family_bundle = next(bundle for bundle in progression['query_bundles'] if bundle['bundle_id'] == 'optimizer_module_effects')

    assert optimizer_bundle['family_bundle_id'] == 'optimizer_module_effects'
    assert optimizer_bundle['required_surface_ids'] == ['mechanic_param::module.primordial_collapse.bh_damage_reduction_pct']
    assert set(optimizer_bundle['optional_surface_ids']) == {
        'mechanic_param::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct',
        'mechanic_param::module.orbital_augment.electron_count',
    }
    assert set(family_bundle['surface_ids']) == set(optimizer_bundle['required_surface_ids']) | set(optimizer_bundle['optional_surface_ids'])
    assert set(family_bundle['surface_ids']).issubset(progression_surfaces)
    assert overlay_requirements['bundle_id'] == 'optimizer_module_effects'
    assert overlay_requirements['required_overlay_delta_types'] == ['module_assertions']
    assert overlay_requirements['optional_overlay_delta_types'] == ['assist_slot_choice']
