from __future__ import annotations
import pytest

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from compilers import stat_input_compiler as compiler
from compilers.stat_input_compiler import compile_stat_inputs
from tests.helpers import build_state, run_stats_subprocess

# Fast-path baseline assertions read the committed max-progression artifacts.
# Tests that need custom inputs still rerun `run_stats.py` and are marked slow.
OUT = ROOT / 'out'


def _build_state(perks_filename: str):
    return build_state(perks_filename=perks_filename)


def _perk_rows(inputs, perk_name: str):
    return [r for r in inputs if r.source_family == "perk" and r.source_name == perk_name]


def test_standard_perk_bonus_scales_max_health_perk_from_lab_level():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    hp_rows = _perk_rows(rows, "x1.20 Max Health")
    assert len(hp_rows) == 1
    assert hp_rows[0].destination_id == "tower_hp"
    assert abs(float(hp_rows[0].value) - 2.5) < 1e-9


def test_standard_perk_bonus_scales_damage_perk_from_lab_level():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    dmg_rows = _perk_rows(rows, "x1.15 Damage")
    assert len(dmg_rows) == 1
    assert dmg_rows[0].destination_id == "tower_damage"
    assert abs(float(dmg_rows[0].value) - 2.1875) < 1e-9


def test_tradeoff_improvement_scales_benefit_only_for_damage_tradeoff():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    tradeoff_rows = _perk_rows(rows, "x1.50 Tower Damage, but Bosses Have 8x Health")
    assert len(tradeoff_rows) == 2
    by_target = {r.destination_id: r for r in tradeoff_rows}
    assert abs(float(by_target["tower_damage"].value) - 1.65) < 1e-9
    assert abs(float(by_target["enemy.boss.health_multiplier"].value) - 8.0) < 1e-9



def test_banned_tradeoffs_are_filtered_from_perk_config():
    state = _build_state("perks_projected_max.json")
    active_ids = {selection.perk_id for selection in state.perk_presets[state.active_perk_preset]}
    assert "PERK_ENEMIES_HAVE_50_HEALTH_BUT_TOWER_HEALTH_REGEN_AND_LIFESTEAL_90" not in active_ids
    assert "PERK_ENEMIES_SPEED_40_BUT_ENEMIES_DAMAGE_X2_5" not in active_ids


def test_active_tradeoffs_materialize_both_positive_and_negative_sides():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    tradeoff_rows = [r for r in rows if r.source_family == "perk" and "but" in r.source_name.lower()]
    by_name = {}
    for row in tradeoff_rows:
        by_name.setdefault(row.source_name, []).append(row)
    expected = {
        "x1.50 Tower Damage, but Bosses Have 8x Health",
        "x1.80 coins, but Tower Max Health -70%",
        "Enemies Damage -50%, but Tower Damage -50%",
        "Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3",
        "x12.00 Cash Per Wave, But Enemy Kill Don't Give Cash",
        "Tower Health Regen x8.00, But Tower Max Max Health -60%",
        "Boss Health -70%, But Boss Speed +50%",
        "Lifesteal x2.50, But Knockback force -70%",
    }
    assert set(by_name) == expected
    for perk_name, perk_rows in by_name.items():
        assert len(perk_rows) == 2, perk_name



def test_ranged_tradeoff_positive_side_is_preserved_but_not_bound_to_a_calculated_stat():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    tradeoff_rows = _perk_rows(rows, "Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3")
    assert len(tradeoff_rows) == 2
    assert any(r.destination_id is None and r.value == "wiki_named_effect" for r in tradeoff_rows)
    assert any(r.destination_id == "enemy.ranged.damage_multiplier" and abs(float(r.value) - 3.0) < 1e-9 for r in tradeoff_rows)


@pytest.mark.slow
def test_tourney_compare_for_offense_uses_perks_off_even_when_engine_perks_on(tmp_path):
    import subprocess, sys, json
    out = tmp_path / "compare_policy"
    result = run_stats_subprocess([
        sys.executable, str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--perk-state', 'on',
        '--perks', str(ROOT / 'input' / 'perks_projected_max.json'),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    policy = diagnostics['compare_situation_policy']
    assert policy['tournament']['preset'] == 'Tourney'
    assert policy['tournament']['perk_state'] == 'off'
    assert policy['farming']['preset'] == 'Farming'
    assert policy['farming']['perk_state'] == 'on'
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    tower_damage = compare['canonical_stat::tower_damage']
    assert tower_damage['compare_preset'] == 'Tourney'
    assert tower_damage['ep_stage_context']['ep_run_state'] == 'tournament_perks_off'
    assert tower_damage['ep_stage_context']['package_run_state'] == 'tourney_perks_off'
    assert tower_damage['ep_stage_context']['compare_perk_state'] == 'off'


def test_standard_perk_bonus_scales_raw_add_game_speed():
    perk_meta = {'category': 'standard'}
    perk_lab_state = {'standard_bonus_multiplier': 1.25, 'tradeoff_bonus_multiplier': 1.0}
    value = compiler._scaled_perk_value(
        perk_meta=perk_meta,
        perk_id='PERK_INCREASE_MAX_GAME_SPEED_BY_1_00',
        operation='raw_add',
        raw_value='1.00',
        picks=1,
        effect_index='1',
        perk_lab_state=perk_lab_state,
    )
    assert math.isclose(value, 1.25, rel_tol=1e-9)


def test_wall_hp_uses_additive_ratio_bonuses_not_ratio_times_one_plus_bonus():
    from engine.stat_engine import resolve_stats
    from models.stat_input import StatInput

    inputs = [
        StatInput(stat_name="Tower HP", source_family="workshop", source_name="Health", value=100.0, value_type="resolved_value", stage="loadout_resolved", preset_name="Farming", provenance="test", destination_object_type="canonical_stat", destination_id="tower_hp", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Wall Health", source_family="workshop", source_name="Wall Health", value=2.0, value_type="resolved_value", stage="loadout_resolved", preset_name="Farming", provenance="test", destination_object_type="canonical_stat", destination_id="wall_hp", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Wall Health", source_family="lab", source_name="Wall Health", value=100.0, value_type="resolved_value", stage="account_state", preset_name=None, provenance="test", destination_object_type="canonical_stat", destination_id="wall_hp", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Wall Health", source_family="module_substat", source_name="Sharp Fortitude", value=120.0, value_type="percent_display", stage="loadout_resolved", preset_name="Farming", provenance="test", destination_object_type="canonical_stat", destination_id="wall_hp", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Wall Health", source_family="enhancement", source_name="Wall Health", value=1.59, value_type="resolved_value", stage="account_state", preset_name=None, provenance="test", destination_object_type="canonical_stat", destination_id="wall_hp", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Sharp Fortitude::unique", source_family="module", source_name="Sharp Fortitude", value=2.5, value_type="multiplier_display", stage="loadout_resolved", preset_name="Farming", provenance="test", destination_object_type="canonical_stat", destination_id="wall_hp", resolver_id="standard_scalar_stat", kb_mapped=True),
    ]
    statbook = resolve_stats(inputs)
    row = statbook.rows["canonical_stat::wall_hp"]
    expected = 100.0 * (2.0 + 1.0 + 1.2) * 1.59 * 2.5
    assert row.final_value == pytest.approx(expected)

@pytest.mark.slow
def test_max_progression_falls_back_to_projected_perks_when_primary_config_empty(tmp_path):
    import subprocess, sys, json
    empty_perks = tmp_path / 'perks.json'
    empty_perks.write_text(json.dumps({'perk_presets': {}, 'active_perk_preset': None}))
    out = tmp_path / 'fallback_run'
    result = run_stats_subprocess([
        sys.executable, str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--perks', str(empty_perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    assert diagnostics['perk_config_resolution']['fallback_applied'] is True
    assert diagnostics['perk_config_resolution']['resolved_perks_path'].endswith('input/perks_projected_max.json')


def test_tower_regen_compare_contributors_use_farming_perks_on_context():
    import json
    compare = json.loads((OUT / 'ep_oracle_compare.json').read_text())
    row = compare['canonical_stat::tower_regen']
    contributors = row['package_contributors']
    assert row['compare_preset'] == 'Farming'
    assert row['compare_perk_state'] == 'on'
    assert any(c['source_family'] == 'perk' and c['source_name'] == 'x1.75 Health Regen' for c in contributors)
    assert any(c['source_family'] == 'module_substat' and c['source_name'] == 'Sharp Fortitude' and c['preset_name'] == 'Farming' for c in contributors)
    assert any(c['source_family'] == 'module_substat' and c['source_name'] == 'Orbital Augment' and c['preset_name'] == 'Farming' for c in contributors)
    regen_closure = json.loads((OUT / 'tower_regen_closure_report.json').read_text())
    assert regen_closure['compare_preset'] == 'Farming'
    assert regen_closure['compare_perk_state'] == 'on'


def test_tower_regen_ep_semantic_gap_report_emits_farming_context_and_hypotheses():
    import json
    report = json.loads((OUT / 'tower_regen_ep_semantic_gap_report.json').read_text())
    hypotheses = report['ep_formula_hypotheses']
    assert report['compare_state_key'] == 'Farming__perks_on'
    assert hypotheses['ep_standard_perk_factor'] == pytest.approx(report['current_factors']['standard_perk_factor'])
    assert hypotheses['ep_tradeoff_regen_factor'] == pytest.approx(8.8)
    assert 'nearest_integer_wse_level_candidate' in hypotheses
    scenarios = {row['scenario']: row for row in report['scenarios']}
    assert 'ep_perk_semantics_bundle' in scenarios
    assert report['assessment']['calculator_change_recommended'] is False


def test_tower_defense_absolute_semantic_gap_report_identifies_standard_perk_ep_semantics():
    import json
    report = json.loads((OUT / 'tower_defense_absolute_semantic_gap_report.json').read_text())
    assert report['current_factors']['standard_perk_factor'] == pytest.approx(2.1875)
    assert report['ep_formula_hypotheses']['ep_standard_perk_factor'] == pytest.approx(2.1875)
    scenarios = {row['scenario']: row for row in report['scenarios']}
    assert report['current_factors']['standard_perk_factor'] == pytest.approx(report['ep_formula_hypotheses']['ep_standard_perk_factor'])
    assert report['package_value'] == pytest.approx(report['ep_value'], rel=1e-4)
    assert report['assessment']['calculator_change_recommended'] is False


def test_multiplier_from_value_keeps_exact_one_neutral_and_preserves_raw_perk_drawbacks():
    from engine.stat_engine import _multiplier_from_value, _canonical_source_multiplier
    from models.stat_input import StatInput

    assert _multiplier_from_value(1.0) == pytest.approx(1.0)
    row = StatInput(stat_name="Tower HP", source_family="perk", source_name="x1.80 coins, but Tower Max Health -70%", value=0.3, value_type="multiplier", stage="loadout_resolved", preset_name="Tourney", provenance="test", destination_object_type="canonical_stat", destination_id="tower_hp", resolver_id="standard_scalar_stat", kb_mapped=True)
    assert _canonical_source_multiplier("tower_hp", row, 0.3) == pytest.approx(0.3)


def test_parse_ep_value_q_and_q_suffixes_have_distinct_magnitudes():
    import run_stats
    q_value, q_kind = run_stats._parse_ep_value('1.0q')
    Q_value, Q_kind = run_stats._parse_ep_value('1.0Q')
    assert q_kind == 'scaled_number'
    assert Q_kind == 'scaled_number'
    assert q_value == pytest.approx(1e15)
    assert Q_value == pytest.approx(1e18)


def test_compare_situation_policy_exposes_distinct_milestone_engine_and_compare_keys():
    import json
    diagnostics = json.loads((OUT / 'diagnostics.json').read_text())
    policy = diagnostics['compare_situation_policy']
    assert 'milestone_engine' in policy
    assert 'milestone_compare_policy' in policy
    assert policy['milestone_compare_policy']['preset'] == 'Milestone'


def test_package_compare_capability_has_single_nested_perk_state_field():
    import json
    diagnostics = json.loads((OUT / 'diagnostics.json').read_text())
    cap = diagnostics['ep_compare_stage_rules']['package_compare_capability']
    assert 'perk_state' in cap
    assert diagnostics['ep_compare_stage_rules'].get('perk_state') is None


def test_tower_damage_runtime_gap_report_uses_ep_cash_50b_assumption():
    import json
    report = json.loads((OUT / 'tower_damage_runtime_gap_report.json').read_text())
    assert report['current_assumption_parameters']['project_funding_cash_assumption'] == pytest.approx(50_000_000_000.0)
    assert report['ep_evidence']['evidence_strength'] == 'user_provided_for_current_ep_compare_basis'
    scenarios = {row['scenario']: row for row in report['scenarios']}
    fitted = scenarios['ep_cash_50b_with_berserker_x8']
    assert fitted['package_value'] == pytest.approx(report['ep_value'], rel=1e-5)
    assert abs(fitted['required_residual_multiplier_to_match_ep'] - 1.0) < 1e-5
    assert report['assessment']['compare_assumption_change_recommended'] is True
    assert report['assessment']['calculator_change_recommended'] is False


def test_farming_survivability_compare_respects_perk_bans():
    import json
    diagnostics = json.loads((OUT / 'diagnostics.json').read_text())
    audit = diagnostics.get('perk_contributor_audit', {})
    for key in [
        'canonical_stat::tower_hp',
        'canonical_stat::tower_regen',
        'canonical_stat::tower_defense_absolute',
    ]:
        farming_rows = audit.get(key, {}).get('Farming', [])
        assert farming_rows
        assert all(row.get('preset_name') == 'ProjectedMax_AllAllowedExceptBanned' for row in farming_rows)



def test_tower_hp_compare_includes_dwhp_and_ep_armor_assist_factor():
    import json
    compare = json.loads((OUT / 'ep_oracle_compare.json').read_text())
    row = compare['canonical_stat::tower_hp']
    contributors = row['package_contributors']
    by_name = {c['source_name']: c for c in contributors}
    assert by_name['Death Wave Health']['value'] == pytest.approx(12.5)
    assert by_name['Death Wave Health']['source_family'] == 'lab'
    assert by_name['Orbital Augment']['value'] == pytest.approx(1.00466)
    assert row['compare_preset'] == 'Farming'
    assert row['compare_perk_state'] == 'on'


def test_tower_hp_gap_after_dwhp_and_armor_assist_fix_reduces_to_ep_standard_perk_semantics():
    import json
    compare = json.loads((OUT / 'ep_oracle_compare.json').read_text())
    row = compare['canonical_stat::tower_hp']
    assert float(row['package_value']) == pytest.approx(float(row['ep_value']), rel=6e-4)


def test_free_upgrades_enhancement_applies_to_all_three_free_upgrade_stats():
    import json
    statbook = json.loads((OUT / 'statbook.json').read_text())['rows']
    attack = statbook['canonical_stat::free_attack_upgrade_chance_pct']['final_value']
    defense = statbook['canonical_stat::free_defense_upgrade_chance_pct']['final_value']
    utility = statbook['canonical_stat::free_utility_upgrade_chance_pct']['final_value']
    assert statbook['canonical_stat::free_upgrade_shared_add_pct']['final_value'] == pytest.approx(41.25)
    assert attack == pytest.approx((49.5 + 6.0 + 41.25) * 1.12)
    assert defense == pytest.approx((49.5 + 3.0 + 41.25) * 1.12)
    assert utility == pytest.approx((49.5 + 4.0 + 10.4 + 0.8 + 41.25) * 1.12)


def test_tradeoff_regen_positive_side_scales_full_multiplier_with_ito():
    from compilers.stat_input_compiler import _scaled_perk_value
    value = _scaled_perk_value(
        perk_meta={'category': 'trade_off'},
        perk_id='PERK_TOWER_HEALTH_REGEN_X8_00_BUT_TOWER_MAX_MAX_HEALTH_60',
        operation='multiplier',
        raw_value='8',
        picks=1,
        effect_index='1',
        perk_lab_state={'tradeoff_bonus_multiplier': 1.1},
    )
    assert value == 8.8


def test_tower_regen_compare_closes_after_module_efficiency_fix():
    import json, math
    compare = json.loads((OUT / 'ep_oracle_compare.json').read_text())
    row = compare['canonical_stat::tower_regen']
    assert row['compare_preset'] == 'Farming'
    assert row['compare_perk_state'] == 'on'
    assert math.isclose(row['package_value'], row['ep_value'], rel_tol=1e-4, abs_tol=1e8)



def test_all_standard_multiplier_perks_use_full_result_spb_rule():
    import csv
    entity_path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
    effect_path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-effect-registry.csv'
    entity = {}
    with entity_path.open(newline='') as f:
        for row in csv.DictReader(f):
            entity[row['perk_id']] = row
    perk_lab_state = {'standard_bonus_multiplier': 1.25, 'tradeoff_bonus_multiplier': 1.0}
    checked = 0
    with effect_path.open(newline='') as f:
        for row in csv.DictReader(f):
            if entity.get(row['perk_id'], {}).get('category') != 'standard':
                continue
            if row['operation'] != 'multiplier':
                continue
            base = float(row['effect_value'])
            picks = int(entity[row['perk_id']].get('max_picks') or 1)
            value = compiler._scaled_perk_value(
                perk_meta={'category': 'standard'},
                perk_id=row['perk_id'],
                operation=row['operation'],
                raw_value=row['effect_value'],
                picks=picks,
                effect_index=row['effect_index'],
                perk_lab_state=perk_lab_state,
            )
            expected = (1.0 + ((base - 1.0) * picks)) * 1.25
            assert value == pytest.approx(expected), row['perk_name']
            checked += 1
    assert checked == 8


def test_all_standard_additive_perks_use_additive_spb_rule():
    import csv
    entity_path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
    effect_path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-effect-registry.csv'
    entity = {}
    with entity_path.open(newline='') as f:
        for row in csv.DictReader(f):
            entity[row['perk_id']] = row
    perk_lab_state = {'standard_bonus_multiplier': 1.25, 'tradeoff_bonus_multiplier': 1.0}
    additive_ops = {'percentage_points_add', 'count_add', 'seconds_add', 'raw_add'}
    checked = 0
    with effect_path.open(newline='') as f:
        for row in csv.DictReader(f):
            if entity.get(row['perk_id'], {}).get('category') != 'standard':
                continue
            if row['operation'] not in additive_ops:
                continue
            base = float(row['effect_value'])
            picks = int(entity[row['perk_id']].get('max_picks') or 1)
            value = compiler._scaled_perk_value(
                perk_meta={'category': 'standard'},
                perk_id=row['perk_id'],
                operation=row['operation'],
                raw_value=row['effect_value'],
                picks=picks,
                effect_index=row['effect_index'],
                perk_lab_state=perk_lab_state,
            )
            expected = base * picks * 1.25
            assert value == pytest.approx(expected), row['perk_name']
            checked += 1
    assert checked == 5


def test_remaining_exception_set_promoted_in_formula_ledger():
    import yaml
    surfaces = yaml.safe_load((ROOT / 'config' / 'destination_formula_ledger.yaml').read_text())['surfaces']
    promoted = {
        'canonical_stat::free_attack_upgrade_chance_pct',
        'canonical_stat::free_defense_upgrade_chance_pct',
        'canonical_stat::free_utility_upgrade_chance_pct',
        'canonical_stat::package_chance_pct',
        'canonical_stat::tower_damage_per_meter_multiplier',
        'canonical_stat::tower_hp',
        'canonical_stat::tower_regen',
    }
    for key in promoted:
        assert surfaces[key]['formula_class'] == 'generic_family_promoted'


def test_promoted_family_outputs_hold_on_v85_run():
    import json
    compare = json.loads((OUT / 'ep_oracle_compare.json').read_text())
    assert compare['canonical_stat::package_chance_pct']['status'] == 'matched_exact'
    assert compare['canonical_stat::tower_damage_per_meter_multiplier']['status'] == 'matched_exact'
    assert compare['canonical_stat::tower_hp']['status'] == 'matched_close'
    assert compare['canonical_stat::tower_regen']['status'] == 'matched_close'
    statbook = json.loads((OUT / 'statbook.json').read_text())['rows']
    assert 'Promoted shared support-multiplier family' in statbook['canonical_stat::free_attack_upgrade_chance_pct']['notes']
    assert 'Promoted shared support-multiplier family' in statbook['canonical_stat::free_defense_upgrade_chance_pct']['notes']
    assert 'Promoted shared support-multiplier family' in statbook['canonical_stat::free_utility_upgrade_chance_pct']['notes']


def test_remaining_count_add_perks_keep_spb_but_round_to_integer():
    from compilers.stat_input_compiler import _scaled_perk_value

    effect = {"spb_applies": "yes", "spb_formula_class": "additive", "integrality_policy": "round_final"}
    perk_lab_state = {'standard_bonus_multiplier': 1.25, 'tradeoff_bonus_multiplier': 1.0}

    # 4 More Smart Missiles: 4 * 1 * 1.25 = 5.0
    assert _scaled_perk_value(
        perk_meta={'category': 'standard'},
        perk_effect_meta=effect,
        perk_id='PERK_MORE_SMART_MISSILES',
        operation='count_add',
        raw_value='4',
        picks=1,
        effect_index='1',
        perk_lab_state=perk_lab_state,
    ) == 5.0

    # +1 Wave on Death Wave: 1 * 1 * 1.25 = 1.25 -> integer count policy
    assert _scaled_perk_value(
        perk_meta={'category': 'standard'},
        perk_effect_meta=effect,
        perk_id='PERK_DEATH_WAVE_PLUS_1_WAVE',
        operation='count_add',
        raw_value='1',
        picks=1,
        effect_index='1',
        perk_lab_state=perk_lab_state,
    ) == 1.0

    # Extra Set of Inner Mines: same integer count policy
    assert _scaled_perk_value(
        perk_meta={'category': 'standard'},
        perk_effect_meta=effect,
        perk_id='PERK_EXTRA_SET_OF_INNER_MINES',
        operation='count_add',
        raw_value='1',
        picks=1,
        effect_index='1',
        perk_lab_state=perk_lab_state,
    ) == 1.0


def test_free_upgrades_card_is_split_into_canonical_free_upgrade_stats_and_values_match_ep_baseline():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    free_upgrade_card_rows = [r for r in rows if r.source_family == "card" and r.source_name == "Free Upgrades"]
    assert {r.destination_id for r in free_upgrade_card_rows} == {
        "free_attack_upgrade_chance_pct",
        "free_defense_upgrade_chance_pct",
        "free_utility_upgrade_chance_pct",
    }
    assert all(float(r.value) == pytest.approx(10.0) for r in free_upgrade_card_rows)

    from engine.stat_engine import resolve_stats
    statbook = resolve_stats(rows)
    assert statbook.rows['canonical_stat::free_upgrade_shared_add_pct'].final_value == pytest.approx(41.25, rel=1e-6)
    assert statbook.rows["canonical_stat::free_attack_upgrade_chance_pct"].final_value == pytest.approx(108.36, rel=1e-6)
    assert statbook.rows["canonical_stat::free_defense_upgrade_chance_pct"].final_value == pytest.approx(105.0, rel=1e-6)
    assert statbook.rows["canonical_stat::free_utility_upgrade_chance_pct"].final_value == pytest.approx(118.664, rel=1e-6)
    support = statbook.rows["canonical_stat::free_upgrade_multiplier"]
    assert all(c["source_family"] != "card" for c in support.contributors)


def test_max_rend_mult_exact_formula_uses_enhancement_base_cap_lab_and_module_substat():
    from engine.stat_engine import resolve_stats
    from models.stat_input import StatInput

    inputs = [
        StatInput(stat_name="Rend Armor Mult +", source_family="enhancement", source_name="Rend Armor Mult +", value=1.21, value_type="resolved_value", stage="account_state", preset_name=None, provenance="test", destination_object_type="canonical_stat", destination_id="max_rend_mult", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Max Rend Armor Multiplier", source_family="lab", source_name="Max Rend Armor Multiplier", value=1.0, value_type="resolved_value", stage="account_state", preset_name=None, provenance="test", destination_object_type="canonical_stat", destination_id="max_rend_mult", resolver_id="standard_scalar_stat", kb_mapped=True),
        StatInput(stat_name="Max Rend Armor Multi", source_family="module_substat", source_name="Death Penalty", value=20.0, value_type="percent_display", stage="loadout_resolved", preset_name="Farming", provenance="test", destination_object_type="canonical_stat", destination_id="max_rend_mult", resolver_id="standard_scalar_stat", kb_mapped=True),
    ]
    statbook = resolve_stats(inputs)
    row = statbook.rows["canonical_stat::max_rend_mult"]
    assert row.final_value == pytest.approx((8.0 + 1.0 + (8.0 * 0.2)) * 1.21)



def test_coin_surface_kb_split_and_transition_mirror():
    from engine.stat_engine import resolve_stats

    state = _build_state("perks_projected_max.json")
    inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    statbook = resolve_stats(inputs)

    narrow = statbook.rows["canonical_stat::coins_per_kill_bonus"]
    broad = statbook.rows["canonical_stat::coin_bonus_multiplier"]
    mirror = statbook.rows["canonical_stat::coin_kill_multiplier"]

    narrow_families = {c["source_family"] for c in narrow.contributors}
    broad_families = {c["source_family"] for c in broad.contributors}

    assert narrow_families <= {"workshop", "lab", "module_substat", "enhancement", "vault", "perk"}
    assert "card" not in narrow_families
    assert "relic" not in narrow_families
    assert broad_families <= {"enhancement", "module", "perk"}
    assert "workshop" not in broad_families
    assert "lab" not in broad_families
    assert "module_substat" not in broad_families
    assert "card" not in broad_families
    assert "relic" not in broad_families

    workshop = next(float(c["value"]) for c in narrow.contributors if c["source_family"] == "workshop")
    lab = next(float(c["value"]) for c in narrow.contributors if c["source_family"] == "lab")
    substats = sum(float(c["value"]) for c in narrow.contributors if c["source_family"] == "module_substat")
    enh = next(float(c["value"]) for c in narrow.contributors if c["source_family"] == "enhancement")
    vault_mult = 1.0
    for c in narrow.contributors:
        if c["source_family"] == "vault":
            v = float(c["value"])
            vault_mult *= (1.0 + v if 0.0 <= v <= 1.0 else v)
    expected_without_perks = ((workshop * lab) + substats) * enh * vault_mult
    perk_multiplier = 1.0
    for c in narrow.contributors:
        if c["source_family"] == "perk":
            v = float(c["value"])
            perk_multiplier *= (1.0 + v if 0.0 <= v <= 1.0 else v)
    assert narrow.final_value == pytest.approx(expected_without_perks * perk_multiplier)
    assert mirror.final_value == pytest.approx(narrow.final_value)


def test_all_coin_bonus_multiplier_uses_farming_tier_and_numeric_pack_multipliers():
    from engine.stat_engine import resolve_stats

    state = _build_state("perks_projected_max.json")
    inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    statbook = resolve_stats(inputs)

    row = statbook.rows["canonical_stat::all_coin_bonus_multiplier"]
    assert row.status == "resolved"
    assert row.final_value == pytest.approx(1314.4527406548677)
    values = {c['stat_name']: c['value'] for c in row.contributors}
    assert values['account_flag.disable_ads'] == pytest.approx(1.5)
    assert values['account_flag.starter_pack'] == pytest.approx(2.0)
    assert values['account_flag.epic_pack'] == pytest.approx(3.0)
    assert values['account_context.farming_tier_coin_multiplier'] == pytest.approx(17.6)
    assert values['cosmetic_bonus.theme_song_coin_multiplier'] == pytest.approx(1.682)


def test_coin_perks_route_to_coins_per_kill_bonus_not_coin_bonus_multiplier():
    state = _build_state("perks_projected_max.json")
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=True)
    all_coin_rows = _perk_rows(rows, "x1.15 All Coin Bonuses")
    tradeoff_rows = _perk_rows(rows, "x1.80 coins, but Tower Max Health -70%")
    assert len(all_coin_rows) == 1
    assert all_coin_rows[0].destination_id == "coins_per_kill_bonus"
    positive = [r for r in tradeoff_rows if float(r.value) > 1.0]
    assert len(positive) == 1
    assert positive[0].destination_id == "coins_per_kill_bonus"


@pytest.mark.slow
def test_coin_surfaces_match_expected_farming_start_and_max_progression(tmp_path):
    import subprocess, sys, json
    expected = {
        'start_of_run': {
            'canonical_stat::coins_per_kill_bonus': 9.818858000000002,
            'canonical_stat::all_coin_bonus_multiplier': 1314.4527406548677,
        },
        'max_progression': {
            'canonical_stat::coins_per_kill_bonus': 42.52792871250001,
            'canonical_stat::all_coin_bonus_multiplier': 1314.4527406548677,
        },
    }
    for mode, targets in expected.items():
        out = tmp_path / mode
        result = run_stats_subprocess([
            sys.executable, str(ROOT / 'run_stats.py'),
            '--preset', 'Farming',
            '--state-mode', mode,
            '--out', str(out),
        ], cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        statbook = json.loads((out / 'statbook_publishable.json').read_text())['rows']
        for key, value in targets.items():
            assert statbook[key]['status'] == 'resolved'
            assert statbook[key]['final_value'] == pytest.approx(value)
