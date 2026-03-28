from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from helpers import cached_run_stats_output

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.slow


def test_smoke(tmp_path) -> None:
    out = cached_run_stats_output('--state-mode', 'start_of_run')
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    account_state = json.loads((out / 'account_state.json').read_text())
    statbook = json.loads((out / 'statbook.json').read_text())
    state_matrix = json.loads((out / 'state_matrix.json').read_text())
    assert diagnostics['engine_status'] == 'publish_gate_enforced_resolution'
    assert diagnostics['mapped_stat_input_count'] >= 100
    assert statbook['diagnostics']['mapped_input_count'] == diagnostics['mapped_stat_input_count']
    assert account_state['card_slots_unlocked'] == 17
    assert diagnostics['card_slots_unlocked'] == 17
    assert diagnostics['card_slot_limit_exceeded'] == {}
    assert diagnostics['state_mode'] == 'start_of_run'
    assert set(state_matrix) == {'account_baseline', 'gem_respec', 'start_of_run', 'max_progression'}
    assert state_matrix['account_baseline']['input_count'] < state_matrix['gem_respec']['input_count'] < state_matrix['start_of_run']['input_count']
    assert account_state['module_presets']['Farming']['generator']['primary'] == 'Singularity Harness'
    assert account_state['module_presets']['Farming']['core']['assist'] == 'Dimension Core'
    assert len(account_state['modules_inventory']) >= 20
    assert statbook['diagnostics']['resolved_stat_count'] >= 20


def test_formula_regressions():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    statbook = json.loads((root / 'out' / 'statbook.json').read_text())
    diagnostics = json.loads((root / 'out' / 'diagnostics.json').read_text())
    assert statbook['diagnostics']['resolved_stat_count'] >= 1
    assert diagnostics['audits']['resolved_stats_with_unresolved_contributors'] == []
    assert diagnostics['audits']['capability_destinations_non_boolean'] == []
    raw = statbook['rows']
    atk = raw['canonical_stat::tower_attack_speed']
    if atk['status'] == 'resolved':
        assert abs(float(atk['final_value']) - 41.505253125) < 0.05


def test_no_raw_level_leaks_on_key_workshop_surfaces():

    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    stat_inputs = json.loads((root / 'out' / 'stat_inputs.json').read_text())
    bad = []
    key_destinations = {
        'free_attack_upgrade_chance_pct',
        'free_defense_upgrade_chance_pct',
        'free_utility_upgrade_chance_pct',
        'recovery_amount_pct',
        'max_recovery_multiplier',
        'wall_fortification_multiplier',
    }
    for row in stat_inputs:
        if row.get('source_family') == 'workshop' and row.get('destination_id') in key_destinations and row.get('value_type') == 'level':
            bad.append((row.get('source_name'), row.get('destination_id')))
    assert not bad, bad


def test_no_raw_level_leaks_broad_workshop_surface_set():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / 'out' / 'stat_inputs.json').read_text())
    bad = []
    watched = {
        'tower_multishot_chance_pct','tower_multishot_targets','tower_rapid_fire_chance_pct','tower_rapid_fire_duration_seconds',
        'tower_bounce_shot_chance_pct','tower_bounce_shot_targets','tower_bounce_shot_range_m','tower_supercrit_chance_pct',
        'tower_supercrit_multiplier','tower_rend_armor_chance_pct','tower_rend_armor_multiplier','tower_defense_absolute',
        'tower_knockback_chance_pct','tower_knockback_force','tower_orb_speed_rpm','tower_orb_count','tower_shockwave_size_m',
        'tower_shockwave_interval_seconds','tower_land_mine_chance_pct','tower_land_mine_damage','tower_land_mine_radius_m',
        'tower_death_defy_chance_pct','cash_per_wave','coins_per_wave','wall_invincibility_duration_seconds'
    }
    for r in rows:
        if r.get('kb_mapped') and r.get('source_family') in {'workshop','lab'} and r.get('destination_id') in watched and r.get('value_type') == 'level':
            bad.append((r.get('destination_id'), r.get('stat_name'), r.get('value')))
    assert not bad, bad[:10]


def test_publish_gate_audits_present():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    diagnostics = json.loads((root / 'out' / 'diagnostics.json').read_text())
    audits = diagnostics['audits']
    assert 'mapped_rows_still_level' in audits
    assert 'resolved_stats_with_unresolved_contributors' in audits
    assert 'capability_destinations_non_boolean' in audits
    assert 'compare_layer_destination_unit_inconsistencies' in audits
    assert isinstance(diagnostics['destination_type_schema'], dict)
    assert 'tower_attack_speed' in diagnostics['destination_type_schema']


def test_line_by_line_verification_artifacts():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    diagnostics = json.loads((root / 'out' / 'diagnostics.json').read_text())
    verification = json.loads((root / 'out' / 'line_by_line_verification.json').read_text())
    assert isinstance(diagnostics['line_verification_summary'], dict)
    assert 'canonical_stat::tower_attack_speed' in verification
    row = verification['canonical_stat::tower_attack_speed']
    assert 'verification_status' in row
    assert 'kb_alignment_status' in row
    assert 'verdict' in row
    assert 'issues' in row
    assert row['verdict'] is not None




def test_ep_compare_artifacts_emit_authoritative_verdict_fields():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    compare = json.loads((root / 'out' / 'ep_oracle_compare.json').read_text())
    row = compare['canonical_stat::tower_attack_speed']
    assert 'kb_alignment_status' in row
    assert 'verdict' in row
    assert row['verdict'] is not None


def test_account_state_and_stat_input_are_frozen():
    import pytest
    from dataclasses import FrozenInstanceError
    from input.runtime_state import compile_account_state
    from input.ids_parser import parse_ids
    from models.stat_input import StatInput

    ids_raw = parse_ids(Path(__file__).resolve().parents[1] / 'input' / 'imports' / 'ids.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    with pytest.raises(FrozenInstanceError):
        state.active_perk_preset = 'mutated'

    row = StatInput(stat_name='x', source_family='lab', source_name='x', value=1, value_type='level', stage='account_state')
    with pytest.raises(FrozenInstanceError):
        row.value = 2


def test_boolean_and_runtime_survivors_resolve():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    statbook = json.loads((root / 'out' / 'statbook.json').read_text())['rows']
    assert statbook['account_flag::account_flag.demon_mode_automation']['status'] == 'resolved'
    assert statbook['capability::capability.additional_card_slot.count']['status'] == 'resolved'
    assert statbook['mechanic_param::uw.golden_tower.duration_seconds']['status'] == 'resolved'
    assert statbook['runtime_mechanic_param::uw.chain_lightning.chance_pct']['status'] == 'resolved'
    assert statbook['runtime_mechanic_param::uw.spotlight.bonus_multiplier']['status'] == 'resolved'
    assert statbook['runtime_mechanic_param::uw.chain_lightning.damage_multiplier']['status'] == 'resolved'
    assert statbook['canonical_stat::wall_thorns_damage_pct']['status'] == 'resolved'


def test_numeric_account_flags_resolve():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / 'out' / 'statbook.json').read_text())['rows']
    assert rows['account_flag::account_flag.discount_enhancements_pct']['status'] == 'resolved'
    assert rows['account_flag::account_flag.discount_rerolls_pct']['status'] == 'resolved'


def test_card_inventory_includes_damage_and_excludes_locked_aoe():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    account_state = json.loads((root / 'out' / 'account_state.json').read_text())
    cards = account_state['cards_inventory']
    assert cards['Damage']['level'] == 7
    assert 'Area of Effect' not in cards
    assert len(cards) == 30
    assert 'Damage' in account_state['card_presets']['Tourney']


def test_all_state_modes_runnable(tmp_path):
    import json
    import subprocess
    import sys
    states = ['account_baseline', 'gem_respec', 'start_of_run', 'max_progression']
    for state in states:
        out = tmp_path / state
        result = subprocess.run([sys.executable, str(ROOT / 'run_stats.py'), '--state-mode', state, '--out', str(out)], cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        diagnostics = json.loads((out / 'diagnostics.json').read_text())
        assert diagnostics['state_mode'] == state
        assert diagnostics['state_mode_support']['state_mode'] == state
        if state == 'max_progression':
            assert diagnostics['state_mode_support']['supported'] is True
        assert (out / 'state_matrix.json').exists()




def test_loadout_config_overrides_card_and_module_presets(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    loadout.write_text(json.dumps({
        'card_presets': {
            'Farming': ['Damage']
        },
        'module_presets': {
            'Farming': {
                'cannon': {'primary': 'Death Penalty', 'assist': 'Amplifying Strike'}
            }
        }
    }))
    perks.write_text(json.dumps({}))
    out = tmp_path / 'loadout_run'
    result = subprocess.run([sys.executable, str(ROOT / 'run_stats.py'), '--loadout', str(loadout), '--perks', str(perks), '--out', str(out)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    account_state = json.loads((out / 'account_state.json').read_text())
    assert account_state['card_presets']['Farming'] == ['Damage']
    assert account_state['module_presets']['Farming']['cannon']['primary'] == 'Death Penalty'
    assert account_state['module_presets']['Farming']['cannon']['assist'] == 'Amplifying Strike'


def test_perk_infrastructure_from_perks_config(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({
        'perk_presets': {
            'Farming': [
                {'perk_id': 'PERK_X1_20_MAX_HEALTH', 'picks': 2},
                {'perk_id': 'PERK_DEFENSE_PERCENT_4_00', 'picks': 1},
                {'perk_id': 'PERK_X1_15_DAMAGE', 'picks': 1},
            ]
        },
        'active_perk_preset': 'Farming',
    }))
    out = tmp_path / 'perk_run'
    result = subprocess.run([sys.executable, str(ROOT / 'run_stats.py'), '--loadout', str(loadout), '--perks', str(perks), '--out', str(out)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    account_state = json.loads((out / 'account_state.json').read_text())
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    stat_inputs = json.loads((out / 'stat_inputs.json').read_text())
    rows = json.loads((out / 'statbook.json').read_text())['rows']
    assert account_state['active_perk_preset'] == 'Farming'
    assert account_state['perk_presets']['Farming'][0]['perk_id'] == 'PERK_X1_20_MAX_HEALTH'
    perk_rows = [r for r in stat_inputs if r.get('source_family') == 'perk']
    assert perk_rows
    assert any(r.get('destination_id') == 'tower_hp' for r in perk_rows)
    assert any(r.get('destination_id') == 'tower_defense_pct' for r in perk_rows)
    assert diagnostics['perk_support']['perk_stat_input_support'] is True
    assert diagnostics['perk_input_file'] == str(perks)
    assert rows['canonical_stat::tower_hp']['status'] == 'resolved'


def test_max_progression_with_perks_reduces_stage_scope_mismatches(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'max_prog_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({
        'perk_presets': {
            'Farming': [
                {'perk_id': 'PERK_X1_20_MAX_HEALTH', 'picks': 2},
                {'perk_id': 'PERK_DEFENSE_PERCENT_4_00', 'picks': 1},
                {'perk_id': 'PERK_X1_15_DAMAGE', 'picks': 1},
            ]
        },
        'active_perk_preset': 'Farming',
    }))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    assert diagnostics['perk_support']['state_mode'] == 'max_progression'
    assert diagnostics['perk_support']['perk_materialization'] is True
    assert diagnostics['perk_coverage_audit']['input_file'] == str(perks)
    assert compare['canonical_stat::tower_hp']['status'] != 'stage_scope_mismatch'
    assert compare['canonical_stat::package_chance_pct']['status'] != 'stage_scope_mismatch'
    assert compare['canonical_stat::tower_damage']['status'] in {'mismatch', 'matched_close'}
    assert 'assumed_maxed_berserker_x8_under_max_progression' in (compare['canonical_stat::tower_damage'].get('compare_notes') or [])



def test_loadout_can_override_active_card_and_module_presets(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'active_preset_run'
    loadout.write_text(json.dumps({
        'active_card_preset': 'Tourney',
        'active_module_preset': 'Tourney',
    }))
    perks.write_text(json.dumps({}))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    account_state = json.loads((out / 'account_state.json').read_text())
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    assert account_state['active_card_preset'] == 'Tourney'
    assert account_state['active_module_preset'] == 'Tourney'
    assert diagnostics['active_card_preset'] == 'Tourney'
    assert diagnostics['active_module_preset'] == 'Tourney'


def test_diagnostics_surface_kb_incomplete_areas(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'kb_gap_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({}))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    gaps = diagnostics['kb_incomplete_areas']
    assert gaps['summary']['blocked_formula_contract_count'] == 0
    assert not any(item['destination_id'] == 'canonical_stat::tower_damage_per_meter_multiplier' for item in gaps['blocked_formula_contracts'])
    assert not any(item['stat_name'] == 'Dimension Core::main' for item in gaps['active_unmapped_inputs'])


def test_dimension_core_main_and_damage_per_meter_gap_are_closed(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / 'closure_run'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    statbook = json.loads((out / 'statbook.json').read_text())['rows']
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    assert statbook['canonical_stat::ultimate_damage_multiplier']['status'] == 'resolved'
    assert any(c.get('source_name') == 'Dimension Core' for c in statbook['canonical_stat::ultimate_damage_multiplier']['contributors'])
    assert compare['canonical_stat::tower_damage_per_meter_multiplier']['formula_contract']['publish_policy'] == 'allow'



def test_compare_display_honors_percent_and_large_number_formatting(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'compare_display_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({}))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    assert compare['canonical_stat::tower_crit_chance_pct']['package_value_display'].endswith('%')
    assert compare['canonical_stat::tower_crit_chance_pct']['ep_value_display'].endswith('%')
    assert compare['canonical_stat::wall_hp']['package_value_display'].endswith('T')
    assert compare['canonical_stat::wall_hp']['package_value_display'] == '114T'


def test_workshop_formula_values_align_with_kb_verified_rows():
    from compilers.stat_input_compiler import WORKSHOP_FORMULA_VALUES

    assert WORKSHOP_FORMULA_VALUES["Bounce Shot Targets"](5) == 6.0
    assert WORKSHOP_FORMULA_VALUES["Bounce Shot Targets"](7) == 8.0
    assert WORKSHOP_FORMULA_VALUES["Super Critical Chance"](100) == 20.0
    assert WORKSHOP_FORMULA_VALUES["Super Critical Mult"](100) == 11.2
    assert WORKSHOP_FORMULA_VALUES["Super Critical Mult"](120) == 13.2


def test_critical_chance_card_is_kb_routed_into_tower_crit_chance():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("run_stats_mod", Path(__file__).resolve().parents[1] / "run_stats.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    raw = mod.parse_ids(Path(__file__).resolve().parents[1] / "input" / "imports" / "ids.csv")
    import yaml as _yaml
    _manual = _yaml.safe_load((Path(__file__).resolve().parents[1] / "input" / "manual_inputs.yaml").read_text()) or {}
    acc = mod.compile_account_state(raw, loadout_config=_manual.get("loadout") or {}, perk_config=_manual.get("perk_config") or {})
    statbook = mod.resolve_stats(mod.compile_stat_inputs(acc, preset_name="Tourney", card_preset_name="Tourney", state_mode="start_of_run"))
    row = statbook.rows["canonical_stat::tower_crit_chance_pct"]

    assert any(c["source_family"] == "card" and c["source_name"] == "Critical Chance" for c in row.contributors)


def test_active_loadout_presets_affect_stat_inputs(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'active_loadout_effect_run'
    loadout.write_text(json.dumps({
        'active_card_preset': 'Tourney',
        'active_module_preset': 'Tourney',
    }))
    perks.write_text(json.dumps({}))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    statbook = json.loads((out / 'statbook.json').read_text())['rows']
    damage = statbook['canonical_stat::tower_damage']
    assert any(c['source_family'] == 'card' and c['source_name'] == 'Damage' and c.get('preset_name') == 'Tourney' for c in damage['contributors'])
    assert any(c['source_family'] == 'module' and c['source_name'] == 'Amplifying Strike' and c.get('preset_name') == 'Tourney' for c in damage['contributors'])


def test_kb_gap_register_is_present_and_bucketed(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / 'kb_gap_register_run'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'output' / 'diagnostics.json').read_text()) if (out / 'output' / 'diagnostics.json').exists() else json.loads((out / 'diagnostics.json').read_text())
    reg = diagnostics['kb_gap_register']
    assert 'summary' in reg
    assert 'entries' in reg
    assert isinstance(reg['entries'], list)
    assert reg['entries']
    assert all('bucket' in e and 'surface' in e and 'what_would_close_it' in e for e in reg['entries'])
    assert diagnostics['active_unmapped_input_count'] == diagnostics['kb_incomplete_areas']['summary']['active_unmapped_input_count']
    assert diagnostics['resolved_unknown_schema_unit_count'] == diagnostics['kb_incomplete_areas']['summary']['resolved_unknown_schema_unit_count']
    assert diagnostics['ambiguous_relic_semantic_hint_count'] == diagnostics['kb_incomplete_areas']['summary']['ambiguous_relic_semantic_hint_count']
    assert diagnostics['blocked_formula_contract_count'] == diagnostics['kb_incomplete_areas']['summary']['blocked_formula_contract_count']
    assert 'Intentional non-goal / runtime-only surface' in reg['summary']
    assert 'KB missing executable contract' in reg['summary']
    assert 'KB contract ambiguous' in reg['summary']


def test_diagnostics_include_projected_compare_view(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / "projection_view_run"
    result = subprocess.run([
        sys.executable,
        str(ROOT / "run_stats.py"),
        "--out", str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / "diagnostics.json").read_text())
    views = diagnostics["ep_compare_projection_views"]
    assert views["current_state_mode"]["state_mode"] == "max_progression"
    assert views["projected_max_progression"]["state_mode"] == "max_progression"
    assert views["projected_max_progression"]["ep_stage_scope_mismatch_count"] <= views["current_state_mode"]["ep_stage_scope_mismatch_count"]


def test_projected_compare_view_honors_explicit_perks(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / "loadout.json"
    perks = tmp_path / "perks.json"
    out = tmp_path / "projection_with_perks_run"
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({
        "perk_presets": {
            "Farming": [
                {"perk_id": "PERK_X1_20_MAX_HEALTH", "picks": 2},
                {"perk_id": "PERK_DEFENSE_PERCENT_4_00", "picks": 1},
            ]
        },
        "active_perk_preset": "Farming",
    }))
    result = subprocess.run([
        sys.executable,
        str(ROOT / "run_stats.py"),
        "--loadout", str(loadout),
        "--perks", str(perks),
        "--out", str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / "diagnostics.json").read_text())
    projected = diagnostics["ep_compare_projection_views"]["projected_max_progression"]
    assert projected["active_perk_preset"] == "Farming"


def test_projected_tower_damage_uses_berserker_max_assumption_under_max_progression(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / "projection_runtime_card_run"
    result = subprocess.run([
        sys.executable,
        str(ROOT / "run_stats.py"),
        "--state-mode", "max_progression",
        "--preset", "Farming",
        "--out", str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    compare = json.loads((out / "ep_oracle_compare.json").read_text())
    damage = compare["canonical_stat::tower_damage"]
    assert damage["status"] == "matched_close"
    notes = damage.get("compare_notes") or []
    assert "assumed_maxed_berserker_x8_under_max_progression" in notes
    assert any(note.startswith("assumed_project_funding_at_cash_50b_under_max_progression") for note in notes)
    assert "conditional_runtime_card__berserker_damage" not in notes
    assert abs(float(damage["relative_delta_pct"])) < 1.0


def test_top_level_ep_compare_summary_matches_current_view(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / "compare_summary_run"
    result = subprocess.run([
        sys.executable,
        str(ROOT / "run_stats.py"),
        "--out", str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / "diagnostics.json").read_text())
    current = diagnostics["ep_compare_projection_views"]["current_state_mode"]
    assert diagnostics["ep_compare_summary"] == {k: current[k] for k in diagnostics["ep_compare_summary"].keys()}


def test_projected_tower_damage_residue_analysis(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / 'max_proj_damage'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    residue = diagnostics['tower_damage_residue_analysis']
    row = compare['canonical_stat::tower_damage']
    assert row['runtime_compare_assumptions']
    assert row['package_value_before_runtime_assumptions'] is not None
    assert residue['package_value_before_runtime_assumptions'] == row['package_value_before_runtime_assumptions']
    assert residue['package_value_after_runtime_assumptions'] == row['package_value']
    assert residue['ep_value'] == row['ep_value']
    assert residue['applied_runtime_multiplier'] > 1.0
    assert residue['required_total_runtime_multiplier_to_match_ep'] > 1.0
    assert residue['required_project_funding_multiplier_at_berserker_x8_to_match_ep'] > 1.0
    assert residue['required_project_funding_coefficient_at_cash_50b_if_berserker_x8_to_match_ep'] > 0.0


def test_lineage_backed_run_perk_destinations_are_emitted_and_include_expected_surfaces(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / 'lineage_backed_perk_scope_run'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    destinations = set(diagnostics['lineage_backed_run_perk_destinations'])
    assert 'canonical_stat::tower_hp' in destinations
    assert 'canonical_stat::tower_regen' in destinations
    assert 'canonical_stat::tower_damage' in destinations
    assert 'canonical_stat::coins_per_kill_bonus' in destinations
    assert 'canonical_stat::coin_kill_multiplier' not in destinations
    assert 'canonical_stat::package_chance_pct' not in destinations


def test_projected_package_chance_is_not_marked_run_perk_stage_scope_under_lineage_backed_classification(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / 'package_scope_projection_run'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    projected = diagnostics['ep_compare_projection_views']['projected_max_progression']
    row = compare['canonical_stat::package_chance_pct']
    assert row['status'] != 'stage_scope_mismatch'
    assert 'run_perks' not in (row.get('compare_notes') or [])
    assert projected['ep_stage_scope_mismatch_count'] == 0


def test_defense_absolute_perk_affects_resolved_stat(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'defabs_perk_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({
        'perk_presets': {
            'Farming': [
                {'perk_id': 'PERK_X1_15_DEFENSE_ABSOLUTE', 'picks': 1},
            ]
        },
        'active_perk_preset': 'Farming',
    }))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rows = json.loads((out / 'statbook.json').read_text())['rows']
    base_rows = json.loads((ROOT / 'out' / 'statbook.json').read_text())['rows']
    with_perk = rows['canonical_stat::tower_defense_absolute']['final_value']
    base = base_rows['canonical_stat::tower_defense_absolute']['final_value']
    assert with_perk < base
    ratio = with_perk / base
    assert ratio == pytest.approx(23.0 / 35.0)


def test_run_perk_residue_analysis_surfaces_stage_scope_rows(tmp_path):
    import json
    import subprocess
    import sys
    out = tmp_path / 'perk_residue_run'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    residue = diagnostics['run_perk_residue_analysis']
    assert residue['stage_scope_row_count'] == 0
    assert residue['stage_scope_rows'] == []


def test_perk_state_off_disables_perk_rows_even_with_active_preset(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'perk_off_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({
        'perk_presets': {
            'Milestone': [
                {'perk_id': 'PERK_X1_20_MAX_HEALTH', 'picks': 2},
                {'perk_id': 'PERK_DEFENSE_PERCENT_4_00', 'picks': 1},
            ]
        },
        'active_perk_preset': 'Milestone',
    }))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--perk-state', 'off',
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    stat_inputs = json.loads((out / 'stat_inputs.json').read_text())
    assert diagnostics['perk_support']['perk_state'] == 'off'
    assert diagnostics['perk_support']['perk_materialization'] is False
    assert diagnostics['perk_support']['active_perk_preset'] == 'Milestone'
    assert not [r for r in stat_inputs if r.get('source_family') == 'perk']


def test_perk_state_on_materializes_active_preset_for_any_run_type(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'perk_on_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({
        'perk_presets': {
            'Milestone': [
                {'perk_id': 'PERK_X1_20_MAX_HEALTH', 'picks': 2},
                {'perk_id': 'PERK_DEFENSE_PERCENT_4_00', 'picks': 1},
            ]
        },
        'active_perk_preset': 'Milestone',
    }))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--perk-state', 'on',
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    stat_inputs = json.loads((out / 'stat_inputs.json').read_text())
    perk_rows = [r for r in stat_inputs if r.get('source_family') == 'perk']
    assert diagnostics['perk_support']['perk_state'] == 'on'
    assert diagnostics['perk_support']['perk_materialization'] is True
    assert diagnostics['perk_support']['active_perk_preset'] == 'Milestone'
    assert perk_rows
    assert any(r.get('destination_id') == 'tower_hp' for r in perk_rows)


def test_sharp_fortitude_unique_uses_kb_rarity_value(tmp_path):
    import json
    import subprocess
    import sys
    loadout = tmp_path / 'loadout.json'
    perks = tmp_path / 'perks.json'
    out = tmp_path / 'sf_unique_run'
    loadout.write_text(json.dumps({}))
    perks.write_text(json.dumps({}))
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--loadout', str(loadout),
        '--perks', str(perks),
        '--out', str(out),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    statbook = json.loads((out / 'statbook.json').read_text())['rows']
    wall_hp = statbook['canonical_stat::wall_hp']
    sf_values = [c['value'] for c in wall_hp['contributors'] if c['source_family'] == 'module' and c['source_name'] == 'Sharp Fortitude']
    assert sf_values == [2.5]


def test_package_chance_compare_uses_tourney_preset_and_matches_ep(tmp_path):
    output_dir = tmp_path / "out"
    result = subprocess.run([
        sys.executable,
        str(ROOT / "run_stats.py"),
        "--ids",
        "input/imports/ids.csv",
        "--loadout",
        "input/loadout.json",
        "--perks",
        "input/derived/perks_projected_max.json",
        "--state-mode",
        "max_progression",
        "--perk-state",
        "on",
        "--out",
        str(output_dir),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    compare = json.loads((output_dir / "ep_oracle_compare.json").read_text())
    row = compare["canonical_stat::package_chance_pct"]
    assert row["compare_preset"] == "Tourney"
    assert row["ep_stage_context"]["compare_perk_state"] == "off"
    assert row["status"] == "matched_exact"
    assert abs(row["package_value"] - 78.8) < 1e-9


def test_compare_situation_fit_matrix_emitted(tmp_path):
    output_dir = tmp_path / 'out'
    result = subprocess.run([
        sys.executable,
        str(ROOT / 'run_stats.py'),
        '--state-mode', 'max_progression',
        '--perk-state', 'on',
        '--perks', 'input/derived/perks_projected_max.json',
        '--out', str(output_dir),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diagnostics = json.loads((output_dir / 'diagnostics.json').read_text())
    matrix = diagnostics['compare_situation_fit_matrix']
    assert matrix['destination_count'] == 26
    assert set(matrix['states'].keys()) == {'farming__perks_off', 'farming__perks_on', 'tourney__perks_off', 'tourney__perks_on'}
    tower_damage = matrix['best_fit_by_destination']['canonical_stat::tower_damage']
    assert tower_damage['perk_state'] == 'off'
    assert tower_damage['state_key'].endswith('__perks_off')


def test_survivability_compare_policy_by_destination(tmp_path):
    out_dir = tmp_path / "out_surv"
    subprocess.run([
        sys.executable,
        "run_stats.py",
        "--state-mode",
        "max_progression",
        "--perk-state",
        "on",
        "--perks",
        "input/derived/perks_projected_max.json",
        "--out",
        str(out_dir),
    ], check=True)
    with open(out_dir / "ep_oracle_compare.json", "r", encoding="utf-8") as f:
        compare = json.load(f)

    tower_hp = compare["canonical_stat::tower_hp"]
    assert tower_hp["compare_preset"] == "Farming"
    assert tower_hp["compare_perk_state"] == "on"
    assert tower_hp["ep_stage_context"]["ep_run_state"] == "farming_perks_on"

    for key in [
        "canonical_stat::tower_regen",
        "canonical_stat::tower_defense_absolute",
        "canonical_stat::wall_hp",
        "canonical_stat::wall_regen",
    ]:
        row = compare[key]
        assert row["compare_preset"] == "Farming"
        assert row["compare_perk_state"] == "on"
        assert row["ep_stage_context"]["ep_run_state"] == "farming_perks_on"


def test_promoted_shared_family_for_tower_damage_and_defense_absolute(tmp_path):
    import subprocess, sys, json
    out = tmp_path / 'out'
    subprocess.run([sys.executable, 'run_stats.py', '--state-mode', 'max_progression', '--out', str(out)], check=True)
    statbook = json.loads((out / 'statbook.json').read_text())
    rows = statbook['rows']
    for key in ['canonical_stat::tower_damage', 'canonical_stat::tower_defense_absolute']:
        row = rows[key]
        assert row['status'] == 'resolved'
        assert 'Promoted shared base-times-post-multipliers family' in (row.get('notes') or '')
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    assert abs(compare['canonical_stat::tower_damage']['relative_delta_pct']) < 0.01
    assert abs(compare['canonical_stat::tower_defense_absolute']['relative_delta_pct']) < 0.01


def test_free_upgrade_stats_are_not_hard_capped_at_100():
    from engine.stat_engine import resolve_stats
    from models.stat_input import StatInput

    rows = [
        StatInput(stat_name='Free Attack Upgrade', source_family='workshop', source_name='Free Attack Upgrade', value=99.0, value_type='resolved_value', stage='account_state', kb_mapped=True, destination_object_type='canonical_stat', destination_id='free_attack_upgrade_chance_pct', resolver_id='standard_scalar_stat'),
        StatInput(stat_name='Free Attack Upgrade', source_family='relic', source_name='Free Attack Upgrade', value=5.0, value_type='resolved_value', stage='account_state', kb_mapped=True, destination_object_type='canonical_stat', destination_id='free_attack_upgrade_chance_pct', resolver_id='standard_scalar_stat'),
    ]
    statbook = resolve_stats(rows)
    row = statbook.rows['canonical_stat::free_attack_upgrade_chance_pct']
    assert row.status == 'resolved'
    assert row.final_value == 104.0


def test_thorns_damage_is_not_hard_capped_at_100():
    from engine.stat_engine import resolve_stats
    from models.stat_input import StatInput

    rows = [
        StatInput(stat_name='Thorn Damage', source_family='workshop', source_name='Thorn Damage', value=99.0, value_type='resolved_value', stage='account_state', kb_mapped=True, destination_object_type='canonical_stat', destination_id='tower_thorns_damage_pct', resolver_id='standard_scalar_stat'),
        StatInput(stat_name='Thorns', source_family='relic', source_name='Thorns', value=0.2, value_type='resolved_value', stage='account_state', kb_mapped=True, destination_object_type='canonical_stat', destination_id='tower_thorns_damage_pct', resolver_id='standard_scalar_stat'),
        StatInput(stat_name='Sharp Fortitude', source_family='module_substat', source_name='Sharp Fortitude', value=10.0, value_type='percent_display', stage='loadout_resolved', kb_mapped=True, destination_object_type='canonical_stat', destination_id='tower_thorns_damage_pct', resolver_id='standard_scalar_stat'),
    ]
    statbook = resolve_stats(rows)
    row = statbook.rows['canonical_stat::tower_thorns_damage_pct']
    assert row.status == 'resolved'
    assert row.final_value == 129.0


def test_attack_defects_cash_per_wave_knockback_and_land_mine_scope(tmp_path):
    import json
    out = cached_run_stats_output('--state-mode', 'max_progression')
    rows = json.loads((out / 'statbook.json').read_text())['rows']

    cash = rows['canonical_stat::cash_per_wave']
    assert cash['status'] == 'resolved'
    assert abs(cash['final_value'] - 9125.952) < 1e-6

    kb = rows['canonical_stat::tower_knockback_force']
    assert kb['status'] == 'resolved'
    assert abs(kb['final_value'] - 2.166) < 1e-6

    lm = rows['canonical_stat::tower_land_mine_damage']
    assert lm['status'] == 'resolved'
    assert lm['final_value'] > 0
    assert 'Promoted runtime-damage family' in (lm.get('notes') or '')


def test_package_chance_is_not_hard_capped_at_100():
    from engine.stat_engine import resolve_stats
    from models.stat_input import StatInput

    rows = [
        StatInput(stat_name='Recovery Package Chance', source_family='workshop', source_name='Recovery Package Chance', value=95.0, value_type='resolved_value', stage='account_state', kb_mapped=True, destination_object_type='canonical_stat', destination_id='package_chance_pct', resolver_id='standard_scalar_stat'),
        StatInput(stat_name='Recovery Package Chance', source_family='perk', source_name='x11.00 Recovery Package Chance', value=22.0, value_type='resolved_value', stage='loadout_resolved', kb_mapped=True, destination_object_type='canonical_stat', destination_id='package_chance_pct', resolver_id='standard_scalar_stat'),
    ]
    statbook = resolve_stats(rows)
    row = statbook.rows['canonical_stat::package_chance_pct']
    assert row.status == 'resolved'
    assert row.final_value == 117.0


def test_coin_kill_compare_uses_farming_perks_off_and_matches_close(tmp_path):
    import json
    out = cached_run_stats_output('--state-mode', 'max_progression')
    compare = json.loads((out / 'ep_oracle_compare.json').read_text())
    row = compare['canonical_stat::coins_per_kill_bonus']
    assert row['compare_preset'] == 'Farming'
    assert row['compare_perk_state'] == 'on'
    assert row['status'] == 'matched_exact'


def test_land_mine_damage_resolves_from_runtime_family(tmp_path):
    import json
    out = cached_run_stats_output('--state-mode', 'max_progression')
    statbook = json.loads((out / 'statbook.json').read_text())['rows']
    row = statbook['canonical_stat::tower_land_mine_damage']
    assert row['status'] == 'resolved'
    assert row['final_value'] is not None
    assert row['final_value'] < 1e18


def test_orbital_augment_electron_count_resolves_as_count(tmp_path):
    import json
    out = cached_run_stats_output('--state-mode', 'max_progression')
    statbook = json.loads((out / 'statbook.json').read_text())['rows']
    row = statbook['mechanic_param::module.orbital_augment.electron_count']
    assert row['status'] == 'resolved'
    assert row['schema']['unit'] == 'count'
    assert row['final_value'] == 2


def test_tower_orb_count_consumes_perk_and_rounds_to_integer(tmp_path):
    import json
    out = cached_run_stats_output('--state-mode', 'max_progression')
    rows = json.loads((out / 'statbook.json').read_text())['rows']
    orb = rows['canonical_stat::tower_orb_count']
    assert orb['final_value'] == 8
    assert 'Consumed 5/5 contributors' in (orb.get('notes') or '')


def test_orb_and_bounce_count_perks_do_not_receive_standard_perk_bonus_scaling():
    import sys
    sys.path.insert(0, str(ROOT))
    from compilers.stat_input_compiler import _scaled_perk_value
    perk_lab_state = {'standard_bonus_multiplier': 1.25, 'tradeoff_bonus_multiplier': 1.0}
    orb_meta = {'category': 'standard'}
    orb_effect = {'spb_applies': 'no', 'spb_formula_class': 'additive', 'integrality_policy': 'round_final'}
    bounce_meta = {'category': 'standard'}
    bounce_effect = {'spb_applies': 'no', 'spb_formula_class': 'additive', 'integrality_policy': 'round_final'}
    orb_value = _scaled_perk_value(perk_meta=orb_meta, perk_effect_meta=orb_effect, perk_id='PERK_ORBS_1', operation='count_add', raw_value='1', picks=2, effect_index='1', perk_lab_state=perk_lab_state)
    bounce_value = _scaled_perk_value(perk_meta=bounce_meta, perk_effect_meta=bounce_effect, perk_id='PERK_BOUNCE_SHOT_2', operation='count_add', raw_value='2', picks=3, effect_index='1', perk_lab_state=perk_lab_state)
    assert orb_value == 2.0
    assert bounce_value == 6.0


def test_contributor_consumption_issue_surfaces_for_unconsumed_rows(tmp_path):
    import json, subprocess, sys
    perks = tmp_path / 'perks.json'
    perks.write_text(json.dumps({
        'perk_presets': {'Farming': [{'perk_id': 'PERK_ORBS_1', 'picks': 2}]},
        'active_perk_preset': 'Farming',
    }))
    out = tmp_path / 'consumption_audit_run'
    result = subprocess.run([
        sys.executable, str(ROOT / 'run_stats.py'), '--perks', str(perks), '--out', str(out)
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    verification = json.loads((out / 'line_by_line_verification.json').read_text())
    orb = verification['canonical_stat::tower_orb_count']
    assert orb['contributor_consumption'] == {'consumed': 5, 'listed': 5}
    assert 'unconsumed_contributor_present' not in orb['issues']
