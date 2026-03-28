from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def test_module_pack14_tables_load_with_required_provenance_columns():
    cost_rows = _read_csv(ROOT / 'kb' / 'modules' / 'tables' / 'module-cost-truth.csv')
    reroll_rows = _read_csv(ROOT / 'kb' / 'modules' / 'tables' / 'module-reroll-constants.csv')
    assumption_rows = _read_csv(ROOT / 'kb' / 'modules' / 'tables' / 'module-workbook-assumption-registry.csv')

    assert cost_rows and {'surface_id', 'closure_class', 'source_ref', 'notes'}.issubset(cost_rows[0])
    assert reroll_rows and {'constant_id', 'closure_class', 'source_ref', 'notes'}.issubset(reroll_rows[0])
    assert assumption_rows and {'assumption_id', 'classification', 'canonical_owner', 'source_ref', 'use_boundary'}.issubset(assumption_rows[0])


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


def test_module_workbook_assumption_registry_classifies_canonical_vs_helper_rows():
    rows = _read_csv(ROOT / 'kb' / 'modules' / 'tables' / 'module-workbook-assumption-registry.csv')
    by_id = {row['assumption_id']: row for row in rows}

    assert by_id['module.main_effect.multiplier_ladder.effective_paths']['classification'] == 'canonical_kb_truth'
    assert by_id['module.main_effect.multiplier_ladder.effective_paths']['canonical_owner'] == 'kb/modules/sources/module-main-effect-source-closure.md'
    assert by_id['module.assist.unique_rarity_upgrade_costs.prompt_materialized']['classification'] == 'accepted_model_helper'
    assert by_id['module.assist.unique_rarity_upgrade_costs.prompt_materialized']['use_boundary'] == 'pack14_prep_notes_only'
    assert by_id['module.economics.additional_workbook_values.unclosed']['use_boundary'] == 'do_not_route_to_runtime'


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
    assert contract['assumption_registry_ref'] == 'kb/modules/tables/module-workbook-assumption-registry.csv'
    assert constants['module.reroll.currency']['value'] == 'reroll_shards'
    assert constants['module.reroll.locking_increases_cost']['value'] == 'true'
    assert constants['module.reroll.numeric_cost_ladder_closed']['value'] == 'false'


def test_module_pack14_nonruntime_draft_keeps_future_bundle_and_overlay_expectations_declarative():
    draft = yaml.safe_load((ROOT / 'kb' / 'modules' / 'contracts' / 'module-pack14-nonruntime-draft.yaml').read_text())

    assert draft['status'] == 'draft_only_pending_r86_proof_obligations'
    assert draft['scope_guardrails'] == [
        'do_not_wire_optimizer_runtime_execution',
        'do_not_add_deep_copy_mutation_paths',
        'do_not_integrate_against_still_moving_routing_ownership',
    ]
    assert draft['source_closed_economics_tables'] == [
        'kb/modules/tables/module-cost-truth.csv',
        'kb/modules/tables/module-reroll-constants.csv',
    ]
    bundle = draft['future_consumer_bundle']
    assert bundle['consumer_id'] == 'optimizer_analysis'
    assert bundle['bundle_id'] == 'optimizer_module_effects'
    assert bundle['required_surface_ids'] == ['state::module.primordial_collapse.bh_damage_reduction_pct']
    assert set(bundle['optional_surface_ids']) == {
        'state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct',
        'state::module.orbital_augment.electron_count',
    }
    assert bundle['overlay_delta_expectations']['required'] == ['module_assertions']
    assert bundle['overlay_delta_expectations']['optional'] == ['assist_slot_choice']
    assert set(bundle['overlay_delta_expectations']['forbidden']) == {
        'workshop_mutation',
        'runtime_wave_state',
        'free_upgrade_runtime_state',
    }
