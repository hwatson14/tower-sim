"""
Functional tests for app/pipeline.py and sharded evaluators.
Verifies trace contract, artifact depth, run-stats output naming,
cache invalidation robustness, and diagnostics persistence contract.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
import pytest
import yaml

from app.pipeline import (
    execute_pipeline,
    PipelineRunRequest,
    resolve_fast_checkpoint,
    FastCheckpointRequest,
    _build_input_dashboard_qe_publications,
    _RUN_STATS_QUERY_OUTPUTS,
    _path_cache_token,
    _effective_manual_inputs_path,
    _run_stats_perk_state,
)
from app.pipeline import RunStatsSession
from app.publication import (
    FULL_PIPELINE_PUBLICATION_ARTIFACTS,
    RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS,
    RUN_STATS_COMMITTED_BASELINE_ARTIFACTS,
    RUN_STATS_LOCAL_SUPPORT_ARTIFACTS,
)
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"


@pytest.fixture(scope="module")
def run_stats_single_execution(tmp_path_factory):
    """Execute RunStatsSession once and return parsed canonical outputs plus output directory."""
    out_dir = tmp_path_factory.mktemp("run_stats_out")
    args = SimpleNamespace(
        ids=IDS_PATH, out=out_dir, perk_mode='max_progression_policy', perk_state='auto', manual_inputs=None,
    )
    session = RunStatsSession()
    rc = session.execute(args)
    assert rc == 0

    parsed_outputs = {
        filename: json.loads((out_dir / filename).read_text(encoding='utf-8'))
        for filename in _RUN_STATS_QUERY_OUTPUTS.values()
    }
    parsed_outputs['diagnostics.json'] = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    return {"out_dir": out_dir, "parsed_outputs": parsed_outputs}


@pytest.fixture(scope="module")
def canonical_pipeline_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    out_dir = tmp_path_factory.mktemp("canonical_pipeline_out")
    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=out_dir,
        preset='Farming',
        state_mode='start_of_run',
    )
    result = execute_pipeline(request)
    assert result.exit_code == 0

    artifact_payloads = {
        'diagnostics': json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8')),
        'statbook_publishable': json.loads((out_dir / 'statbook_publishable.json').read_text(encoding='utf-8')),
        'optimizer_scores': json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8')),
        'ep_oracle_compare': json.loads((out_dir / 'ep_oracle_compare.json').read_text(encoding='utf-8')),
        'pipeline_trace': json.loads((out_dir / 'pipeline_trace.json').read_text(encoding='utf-8')),
        'dashboards': {
            'input_dashboard': json.loads((out_dir / 'input_dashboard.json').read_text(encoding='utf-8')),
            'stats_dashboard': json.loads((out_dir / 'stats_dashboard.json').read_text(encoding='utf-8')),
        },
    }
    return artifact_payloads


def test_run_stats_start_of_run_forces_perks_off() -> None:
    account_state = SimpleNamespace(
        perk_presets={'Farming': {}, 'GC Max Waves': {}},
        active_perk_preset='GC Max Waves',
    )
    preset_name, perks_enabled = _run_stats_perk_state(
        account_state,
        preset_name='Farming',
        perk_state='on',
        perk_mode='max_progression_policy',
        state_mode='start_of_run',
    )
    assert preset_name is None
    assert perks_enabled is False

    preset_name, perks_enabled = _run_stats_perk_state(
        account_state,
        preset_name='Tourney',
        perk_state='on',
        perk_mode='max_progression_policy',
        state_mode='max_progression',
    )
    assert preset_name is None
    assert perks_enabled is False


def test_tourney_gc_max_waves_policy_publishes_timing_without_perks(tmp_path: Path) -> None:
    out_dir = tmp_path / 'out'
    result = execute_pipeline(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=out_dir,
            preset='Tourney',
            perk_mode='max_progression_policy',
            perk_state='auto',
            perk_policy_preset='GC Max Waves',
        )
    )

    assert result.exit_code == 0
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Tourney'
    assert diagnostics['perk_policy_preset'] == 'GC Max Waves'
    assert diagnostics['perk_support']['perk_materialization'] is False
    assert diagnostics['perk_support']['active_perk_preset'] is None
    assert diagnostics['perk_support']['configured_active_perk_preset'] == 'Tourney'
    assert diagnostics['state_matrix']['start_of_run']['perks_enabled'] is False
    assert diagnostics['state_matrix']['max_progression']['perks_enabled'] is False


def test_tourney_fast_checkpoint_policy_uses_scenario_perk_guard() -> None:
    result = resolve_fast_checkpoint(
        FastCheckpointRequest(
            ids=IDS_PATH,
            preset='Tourney',
            state_mode='max_progression',
            perk_mode='max_progression_policy',
            perk_state='auto',
            perk_policy_preset='GC Max Waves',
            requested_surface_ids=('state::tower.damage',),
        )
    )

    assert result.diagnostics['perks_enabled'] is False
    assert result.diagnostics['perk_preset_name'] is None


def test_load_ep_oracle_applies_key_level_ambiguity_overrides(tmp_path: Path) -> None:
    from evaluators.compare import _load_ep_oracle

    ep_csv = tmp_path / 'ep_export.csv'
    ep_csv.write_text(
        '\n'.join(
            [
                'suite,key,label,value,import',
                'ehp,wall_health,Wall Health,132.07 T,132.07 T',
                'ehp,wall_fortification,Wall Fortification,1.37 q,1.37 q',
                'ehp,wall_regen,Wall Regen,238.16 T,238.16 T',
                'ehp,health,Health,32.85 T,32.85 T',
                'ehp,health_raw,Health raw,3.8739885540642007 T,eHP',
                'ehp,armor_multiplier,Armor multiplier,8.480849599999999,eHP',
                'edmg,crit_factor,Critical Factor,170.5248,170.5248',
                'edmg,edmg_total_raw,eDMG/sec total raw,1.016969274326566e+33,eDamage',
                'edmg,base_damage_raw,Base damage,21613962207280770,eDamage',
                'edmg,super_crit_multiplier,Super crit multiplier,39.949895999999995,eDamage',
                'edmg,range_m,Range metres,127.9223999157052,eDamage',
                'edmg,chain_lightning_dps,Chain Lightning DPS,106214484.22732075,eDamage',
                'edmg,smart_missile_heatup,Smart Missile heatup,5.5,eDamage',
                'edmg,poison_swamp_dc,Poison Swamp DC,22.75,eDamage',
                'edmg,ilm_heat_multiplier,ILM heat multiplier,0.5,eDamage',
                'edmg,chrono_field_plus_multiplier,Chrono Field+ multiplier,1,eDamage',
                'ehp,ehp_total_raw,eHP total raw,860615355043605400,eHP',
                'edmg,max_rend_mult,Max Rend Mult,9.6,9.6',
                'edmg,recovery_package_chance,Recovery Package Chance,0.788,0.788',
                'eecon,cpk_average,Average CpK,431.19 M,431.19 M',
                'eecon,cpk_average_raw,Average CpK raw,471166645.7762736,eEcon',
            ]
        ),
        encoding='utf-8',
    )

    oracle = _load_ep_oracle(ep_csv)

    # Ambiguous rows route by export key, not label-only matching.
    assert oracle['derived::wall.hp_pre_fort']['ep_value_raw'] == '132.07 T'
    assert oracle['derived::wall.hp_pre_fort']['label'] == 'Wall Health'
    assert oracle['derived::wall.hp_final']['ep_value_raw'] == '1.37 q'
    assert oracle['derived::wall.hp_final']['label'] == 'Wall Fortification'
    assert oracle['derived::wall.regen_hp_per_second']['ep_value_raw'] == '238.16 T'
    assert oracle['derived::ehp.health_factor']['ep_value_raw'] == '32.85 T'
    assert oracle['derived::ehp.health_raw_factor']['ep_value_raw'] == '3.8739885540642007 T'
    assert oracle['derived::ehp.armor_factor']['ep_value_raw'] == '8.480849599999999'
    # The expanded raw export supersedes older display/shortcut rows for the
    # same destination when both are present.
    assert oracle['derived::edamage']['ep_value_raw'] == '1.016969274326566e+33'
    assert oracle['derived::edamage']['ep_export_key'] == 'edmg_total_raw'
    assert oracle['derived::edamage.base_damage_stack']['ep_value_raw'] == '21613962207280770'
    assert oracle['state::tower.supercrit_multiplier']['ep_value_raw'] == '39.949895999999995'
    assert oracle['state::tower.range_m']['ep_value_raw'] == '127.9223999157052'
    assert oracle['derived::edamage.uw.chain_lightning_dps']['ep_value_raw'] == '106214484.22732075'
    assert oracle['derived::edamage.uw.smart_missiles_heatup_factor']['ep_value_raw'] == '5.5'
    assert oracle['derived::edamage.uw.poison_swamp_death_creep_factor']['ep_value_raw'] == '22.75'
    assert oracle['derived::edamage.uw.ilm_charged_mines_factor']['ep_value_raw'] == '0.5'
    assert oracle['derived::edamage.chrono_field_plus_factor']['ep_value_raw'] == '1'
    assert oracle['derived::ehp']['ep_value_raw'] == '860615355043605400'
    assert oracle['derived::eecon']['ep_value_raw'] == '471166645.7762736'
    # Existing ambiguity aliases remain key-driven.
    assert oracle['state::tower.crit_multiplier']['ep_value_raw'] == '170.5248'
    assert oracle['state::tower.max_rend_multiplier']['ep_value_raw'] == '9.6'
    assert oracle['state::tower.package_chance_pct']['ep_value_raw'] == '0.788'


def test_load_ep_oracle_accepts_machine_facing_value_column(tmp_path: Path) -> None:
    from evaluators.compare import _load_ep_oracle

    ep_csv = tmp_path / 'ep_export.csv'
    ep_csv.write_text(
        '\n'.join(
            [
                'Oracle Outputs (Effective Paths),,,,,,,,',
                'suite,key,label,type,unit,value,source_tab,status,audit_note',
                'edmg,crit_factor,Critical factor,multiplier,x,199.6146,eDamage,,',
                'edmg,edmg_total_raw,eDMG/sec total raw,raw,damage/sec,6.764496451095706e+33,eDamage,,',
            ]
        ),
        encoding='utf-8',
    )

    oracle = _load_ep_oracle(ep_csv)

    assert oracle['state::tower.crit_multiplier']['ep_value_raw'] == '199.6146'
    assert oracle['state::tower.crit_multiplier']['ep_export_source_tab'] == 'eDamage'
    assert oracle['derived::edamage']['ep_value_parsed'] == pytest.approx(6.764496451095706e33)


def test_ep_oracle_compare_normalizes_damage_per_meter_bonus_export() -> None:
    from evaluators.compare import _normalize_compare_values

    package_value, ep_value, notes = _normalize_compare_values(
        'state::tower.damage_per_meter_multiplier',
        'normal',
        1.1355112,
        0.1355112,
    )

    assert package_value == pytest.approx(0.1355112)
    assert ep_value == pytest.approx(0.1355112)
    assert 'package_damage_per_meter_total_multiplier_normalized_to_ep_bonus' in notes


def test_ep_oracle_compare_annotates_known_export_defect_mismatches() -> None:
    from evaluators.compare import build_compare_status_summary, build_ep_compare
    from evaluators.compare_core import build_compare_status_summary as build_core_summary

    compare = build_ep_compare(
        {
            'state::tower.max_rend_multiplier': {
                'label': 'Max Rend Mult',
                'ep_export_key': 'max_rend_mult',
                'ep_value_raw': '1',
                'ep_value_parsed': 1.0,
                'ep_value_type': 'number',
            }
        },
        {
            'Farming': {
                'state::tower.max_rend_multiplier': {
                    'final_value': 9.6,
                    'value_type': 'multiplier',
                    'contributors': [],
                }
            }
        },
        {'surfaces': {}},
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
        ep_stage_context_for_destination=lambda _dest, _context: {
            'compare_preset': 'Farming',
            'unsupported_facets': [],
        },
        compare_state_key_for_destination=lambda _dest, default: default,
        contributor_snapshot=lambda row: row,
        apply_projected_runtime_compare_assumptions=lambda _dest, row, _stage_context: (row, []),
        formula_contract=lambda _ledger, _dest: {'compare_policy': 'normal'},
        normalize_compare_values=lambda _dest, _policy, package_value, ep_value: (package_value, ep_value, []),
    )

    row = compare['state::tower.max_rend_multiplier']
    assert row['status'] == 'mismatch'
    assert row['kb_alignment_status'] == 'not_comparable'
    assert row['verdict'] == 'pass_with_compare_limitations'
    assert 'ep_export_bug:max_rend_multiplier_exports_identity_or_display_1_0_instead_of_kb_qe_9_6' in row['compare_notes']
    summary = build_compare_status_summary(compare)
    assert summary['ep_raw_formula_mismatch_count'] == 1
    assert summary['ep_true_formula_mismatch_count'] == 0
    assert summary['ep_known_export_defect_count'] == 1
    assert summary['ep_unknown_formula_mismatch_count'] == 0
    assert summary['ep_stage_scope_unsupported_facet_counts'] == {}
    core_summary = build_core_summary(compare)
    assert core_summary['ep_raw_formula_mismatch_count'] == 1
    assert core_summary['ep_true_formula_mismatch_count'] == 0
    assert core_summary['ep_known_export_defect_count'] == 1
    assert core_summary['ep_unknown_formula_mismatch_count'] == 0


def test_ep_oracle_compare_summary_counts_accounted_stage_scope_facets() -> None:
    from evaluators.compare import build_compare_status_summary
    from evaluators.compare_core import build_compare_status_summary as build_core_summary

    compare = {
        'state::aligned': {'status': 'matched_exact'},
        'state::stage.accounted': {
            'status': 'stage_scope_mismatch',
            'compare_notes': [
                'normalization_note_that_is_not_a_stage_facet',
                'ep_compare_uses_unsupported_stage_facets',
                'max_progression',
                'max_workshop',
                'ep_shortcut:aggregate_scope',
                'ep_user_guess:workbook_assumption',
            ],
        },
        'state::stage.unaccounted': {
            'status': 'stage_scope_mismatch',
            'compare_notes': ['legacy_stage_note_without_marker'],
        },
    }

    for summary in (build_compare_status_summary(compare), build_core_summary(compare)):
        assert summary['ep_alignment_status'] == 'unresolved_ep_alignment_gaps'
        assert summary['ep_clean_aligned_count'] == 1
        assert summary['ep_accounted_stage_scope_limit_count'] == 1
        assert summary['ep_unaccounted_alignment_gap_count'] == 1
        assert summary['ep_stage_scope_mismatch_count'] == 2
        assert summary['ep_stage_scope_unsupported_facet_counts'] == {
            'ep_shortcut:aggregate_scope': 1,
            'ep_user_guess:workbook_assumption': 1,
            'max_progression': 1,
            'max_workshop': 1,
        }
        assert summary['ep_stage_scope_user_guess_facet_counts'] == {
            'ep_user_guess:workbook_assumption': 1,
        }
        assert summary['ep_stage_scope_shortcut_facet_counts'] == {
            'ep_shortcut:aggregate_scope': 1,
        }
        assert summary['ep_stage_scope_rows_with_accounted_facets'] == 1
        assert summary['ep_stage_scope_rows_without_accounted_facets'] == 1
        assert summary['ep_stage_scope_unaccounted_destinations'] == ['state::stage.unaccounted']


def test_ep_oracle_compare_uses_ep_run_context_for_component_helpers() -> None:
    from evaluators.compare import (
        EP_ORACLE_SHORTCUT_CONTEXT_NOTE,
        _compare_state_key_for_destination,
        _ep_stage_context_for_destination,
    )

    assert _compare_state_key_for_destination('derived::edamage', 'Farming') == 'Tourney__perks_off'
    assert _compare_state_key_for_destination('derived::edamage.uw.chain_lightning_dps', 'Farming') == 'Tourney__perks_off'
    assert _compare_state_key_for_destination('derived::ehp.health_factor', 'Farming') == 'Farming__perks_on'
    assert _compare_state_key_for_destination('derived::wall.regen_hp_per_second', 'Farming') == 'Farming__perks_on'
    assert _compare_state_key_for_destination('state::tower.package_chance_pct', 'Farming') == 'Farming__perks_on'

    edamage_context = _ep_stage_context_for_destination(
        'derived::edamage',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert edamage_context['compare_preset'] == 'Tourney'
    assert edamage_context['compare_perk_state'] == 'off'
    assert EP_ORACLE_SHORTCUT_CONTEXT_NOTE in edamage_context['notes']

    edamage_helper_context = _ep_stage_context_for_destination(
        'derived::edamage.uw.chain_lightning_dps',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert edamage_helper_context['compare_preset'] == 'Tourney'
    assert edamage_helper_context['compare_perk_state'] == 'off'
    assert EP_ORACLE_SHORTCUT_CONTEXT_NOTE in edamage_helper_context['notes']

    range_dpm_context = _ep_stage_context_for_destination(
        'derived::edamage.range_dpm_factor',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert 'ep_user_guess:dpm_damage_at_range_pct' in range_dpm_context['unsupported_facets']

    econ_context = _ep_stage_context_for_destination(
        'derived::eecon',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert econ_context['compare_preset'] == 'Farming'
    assert econ_context['compare_perk_state'] == 'on'
    assert EP_ORACLE_SHORTCUT_CONTEXT_NOTE in econ_context['notes']
    assert 'ep_user_guess:bh_kill_share' in econ_context['unsupported_facets']

    chain_thunder_context = _ep_stage_context_for_destination(
        'derived::ehp.chain_thunder_factor',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert 'ep_user_guess:cl_damage_pct_of_total_damage' in chain_thunder_context['unsupported_facets']

    crit_context = _ep_stage_context_for_destination(
        'state::tower.crit_multiplier',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert 'ep_user_guess:damage_stat_progression_or_module_policy' in crit_context['unsupported_facets']

    shock_context = _ep_stage_context_for_destination(
        'derived::edamage.shock_stack_factor',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert 'ep_user_guess:dimension_core_shock_stack_policy' in shock_context['unsupported_facets']

    super_tower_context = _ep_stage_context_for_destination(
        'derived::edamage.super_tower_factor',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert (
        'ep_shortcut:super_tower_uw_component_scope_differs_from_effective_uptime_factor'
        in super_tower_context['unsupported_facets']
    )

    ehp_total_context = _ep_stage_context_for_destination(
        'derived::ehp',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert 'ep_shortcut:ehp_total_inherits_component_compare_limitations' in ehp_total_context['unsupported_facets']

    locked_uw_helper_context = _ep_stage_context_for_destination(
        'derived::edamage.uw.smart_missiles_heatup_factor',
        {'default_compare_preset': 'Farming', 'state_mode': 'max_progression'},
    )
    assert 'ep_user_guess:locked_or_unowned_uw_helper_levels' in locked_uw_helper_context['unsupported_facets']


def test_bounded_compare_rows_publish_ep_shortcut_aliases() -> None:
    from app.pipeline import _bounded_compare_rows_from_statbooks

    rows_by_preset = _bounded_compare_rows_from_statbooks({
        'Farming': {'rows': {'derived::ehp': {'final_value': 1.0}}},
        'Tourney': {'rows': {'derived::edamage': {'final_value': 2.0}}},
    })

    assert rows_by_preset['Farming__perks_on']['derived::ehp']['final_value'] == pytest.approx(1.0)
    assert rows_by_preset['Farming__perks_auto']['derived::ehp']['final_value'] == pytest.approx(1.0)
    assert rows_by_preset['Tourney__perks_off']['derived::edamage']['final_value'] == pytest.approx(2.0)


@pytest.mark.live
def test_execute_pipeline_smoke_and_trace_contract(tmp_path):
    """execute_pipeline runs and produces a valid pipeline_trace.json with all expected fields."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')

    result = execute_pipeline(request)

    assert result.exit_code == 0
    assert result.out_dir == out_dir

    trace_path = out_dir / "pipeline_trace.json"
    assert trace_path.exists(), "pipeline_trace.json was not created"

    trace = json.loads(trace_path.read_text(encoding='utf-8'))
    assert set(trace) >= {'request', 'execution_path', 'stages', 'artifacts_written'}
    assert len(trace['stages']) >= 3, "Expected at least 3 stages (input_load, stat_resolution, artifact_write)"
    stage_ids = {s['stage_id'] for s in trace['stages']}
    assert 'input_load' in stage_ids
    assert 'stat_resolution' in stage_ids
    assert 'artifact_write' in stage_ids
    assert len(trace['artifacts_written']) > 0

    req = trace['request']
    assert 'ids' in req and 'out' in req and 'preset' in req and 'state_mode' in req

    written_names = {Path(f).name for f in trace['artifacts_written']}
    assert 'ep_oracle_compare.json' in written_names
    assert 'line_by_line_verification.json' in written_names


@pytest.mark.live
def test_diagnostics_depth(canonical_pipeline_artifacts):
    """diagnostics.json must contain real populated content, not empty placeholders."""
    diag = canonical_pipeline_artifacts['diagnostics']

    assert diag.get('stat_input_count', 0) > 0, "stat_input_count must be non-zero"
    assert diag.get('statbook_row_count', 0) > 0, "statbook_row_count must be non-zero"
    assert 'state_matrix' in diag and diag['state_matrix'], "state_matrix must be populated"
    assert 'start_of_run' in diag['state_matrix'] and 'max_progression' in diag['state_matrix']
    assert diag['state_matrix']['start_of_run'].get('input_count', 0) > 0
    assert 'kb_incomplete_areas' in diag
    assert 'audits' in diag
    assert 'ep_compare_summary' in diag


@pytest.mark.live
def test_publishable_statbook_populated(canonical_pipeline_artifacts):
    """statbook_publishable.json must be non-empty and structurally valid."""
    pub = canonical_pipeline_artifacts['statbook_publishable']
    assert 'rows' in pub and len(pub['rows']) > 0, "statbook_publishable.json rows must be non-empty"


@pytest.mark.live
def test_input_dashboard_artifact_is_published(tmp_path):
    """input_dashboard payload builder must emit the expected top-level contract keys."""
    from app.publication import _build_input_dashboard_payload

    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    assert dashboard.get('schema_version') == 2
    assert isinstance(dashboard.get('preset_options'), list)
    expected_panel_ids = [
        'labs',
        'workshop',
        'workshop_enhancements',
        'ultimate_weapons',
        'cards',
        'bots',
        'relics',
        'modules',
        'vault',
        'guardians',
        'themes_and_songs',
    ]
    panel_ids = [panel.get('panel_id') for panel in (dashboard.get('panels') or [])]
    assert panel_ids == expected_panel_ids
    panel_by_id = {panel.get('panel_id'): panel for panel in (dashboard.get('panels') or [])}
    assert panel_by_id['themes_and_songs']['panel_type'] == 'simple_metric_panel'
    assert 'rows' not in ((panel_by_id['workshop'].get('payload') or {}))

    labs_rows = (((panel_by_id['labs'].get('payload') or {}).get('buckets') or [{}])[0].get('rows') or [])
    if labs_rows:
        assert {'name', 'level', 'max'}.issubset(labs_rows[0].keys())


def test_build_boss_wave_payload_publishes_summary_and_runtime_assumptions(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hit_count': 5,
            'electron_hit_count': 5,
            'boss_time_to_contact_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
            'flame_bot_damage_reduction_pct': 0.0,
            'flame_bot_duration_seconds': 0.0,
            'flame_bot_cooldown_seconds': 1.0,
            'defense_field_damage_reduction_pct': 0.0,
            'defense_field_duration_seconds': 0.0,
            'defense_field_cooldown_seconds': 1.0,
            'black_hole_damage_reduction_pct': 0.0,
            'black_hole_duration_seconds': 0.0,
            'black_hole_cooldown_seconds': 1.0,
            'pbh_encounter_uptime_fraction': 0.0,
        },
    )

    assert payload.get('artifact') == 'boss_wave_dashboard_payload'
    assert payload.get('schema_version') == 1
    assert payload.get('contract', {}).get('simulator_owner') == 'simulators.evaluator_kernel.evaluate_overlay_row'
    assert payload.get('source_selection', {}).get('active_source') == 'replacement'
    assert payload.get('contract', {}).get('perk_timeline_mode') == 'runtime_policy_projection'
    assert payload.get('contract', {}).get('checkpoint_mode') == 'actual_boss_cadence_with_sampling'
    assert payload.get('download', {}).get('format') == 'csv'
    summary = payload.get('summary') or {}
    assert summary['max_wave'] == 27
    assert summary['max_surviving_wave'] == 27
    assert summary['first_failed_wave'] == 0
    assert summary['result_consistent_with_rows'] is True
    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics['preset_name'] == 'Farming'
    assert diagnostics['mode_id'] == 'farming'
    assert diagnostics['tier_number'] == 14
    assert diagnostics['tier_column'] == 'Tier 14'
    assert diagnostics['actual_boss_interval_waves'] == 9
    assert diagnostics['actual_boss_interval_waves'] == diagnostics['scenario_surfaces']['boss_wave_interval']
    assert diagnostics['checkpoint_every_bosses'] == 1
    assert diagnostics['checkpoint_mode'] == 'actual_boss_cadence_with_sampling'
    assert diagnostics['checkpoint_resolution_mode'] == 'replacement_table1_table2_overlay'
    assert diagnostics['execution_mode'] == 'staged_replacement'
    assert diagnostics['stop_on_failure'] is True
    assert diagnostics['perk_timeline_rows'] >= 0
    assert diagnostics['scenario_runtime_inputs']['orb_boss_hit_pct'] == 2.5
    assert diagnostics['milestone_alignment'] == {
        'source': 'IDS::Player & Stuff.tier_progression_waves',
        'tier_column': 'Tier 14',
            'dissonance_run_category': 'none',
            'reference_wave': 30,
            'reference_raw_wave': 30,
            'dissonance_pb_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
            'dissonance_pb_reference_wave': None,
            'dissonance_pb_reference_raw_wave': None,
            'active_reference_kind': 'ids_milestone_wave',
            'active_reference_source': 'IDS::Player & Stuff.tier_progression_waves',
            'active_reference_wave': 30,
            'active_reference_raw_wave': 30,
            'active_reference_gap_reason': None,
            'calculated_max_surviving_wave': 27,
        'calculated_selected_max_wave': 27,
        'selected_model': 'unified_hit_by_hit_boss_survival',
        'comparison_status': 'comparison_available',
        'delta_waves': -3,
        'abs_delta_waves': 3,
        'calculated_to_reference_ratio': 0.9,
    }
    expected_pressure_hint = {
        'enabled': True,
        'mode': 'raw_calculated_wave_to_reference_ratio_hint',
        'application': 'explicit_comparison_input_only',
        'certification_effect': 'none_not_applied',
        'boss_wave_pressure_factor': pytest.approx(0.9),
        'rounded_boss_wave_pressure_factor': 0.9,
        'direction': 'decrease_pressure',
        'calculated_selected_max_wave': 27,
        'reference_wave': 30,
        'reference_kind': 'ids_milestone_wave',
        'reference_source': 'IDS::Player & Stuff.tier_progression_waves',
        'calculated_delta_vs_reference_wave': -3,
        'calculated_to_reference_ratio': pytest.approx(0.9),
        'comparison_scenario_runtime_inputs': {'boss_wave_pressure_factor': pytest.approx(0.9)},
    }
    assert summary['pressure_factor_reference_hint'] == expected_pressure_hint
    assert diagnostics['pressure_factor_reference_hint'] == expected_pressure_hint


def _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod):
    monkeypatch.setattr(
        pipeline_mod,
        'load_inputs',
        lambda ids_path=None, manual_inputs_path=None: type(
            'Bundle',
            (),
            {'ids_raw': {}, 'loadout_config': {}, 'perk_config': {}, 'perk_policy': {}, 'manual_inputs': {}},
        )(),
    )
    monkeypatch.setattr(
        pipeline_mod,
        'build_runtime_state',
        lambda ids_raw, loadout_config=None, perk_config=None, manual_inputs=None: type(
            'State',
            (),
            {
                'player_meta': {},
                'tier_progression_waves': {'Tier 14': 30},
                'labs': {'Wall Thorns': 16},
                'workshop_enhancements': {},
                'ultimate_weapons': {},
                'uw_plus_tracks': {},
                'relics': {},
                'vault': {},
                'bots': {},
                'bot_upgrades': {},
                'guardians': {},
                'theme_song_coin_multiplier': 1.0,
                'cards_inventory': {},
                'card_slots_unlocked': 0,
                'module_system_state': {},
                'modules_inventory': {},
                'raw_sections': {},
                'default_preset': 'Farming',
                'active_card_preset': 'Farming',
                'active_module_preset': 'Farming',
                'active_perk_preset': 'Farming',
                'perk_preset_namespace_class': 'canonical',
                'workshop': {
                    track: type(
                        'Track',
                        (),
                        {'preset_levels': {'Farming': level}, 'max_level': max_level},
                    )()
                    for track, level, max_level in (
                        ('Health', 10, 20),
                        ('Wall Health', 10, 20),
                        ('Health Regen', 10, 20),
                        ('Enemy Attack Level Skip', 10, 20),
                        ('Enemy Health Level Skip', 10, 20),
                    )
                },
            },
        )(),
    )


def _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, *, omit_surface: str | None = None):
    from simulators import timing as timing_mod

    class _FakeRow:
        def __init__(self, value, contributors=None):
            self.final_value = value
            self.status = 'resolved'
            self.contributors = list(contributors or [])

    rows = {
        'state::tower.enemy_attack_level_skip_pct': _FakeRow(
            5.265,
            contributors=[
                {
                    'active': True,
                    'value': 2.0,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'lab.enemy_attack_level_skip.account_state',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 1.5,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'relic__tower__enemy_attack_level_skip__pct',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 0.55,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'workshop__tower__enemy_attack_level_skip__pct',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 1.3,
                    'composition_stage': 'multiplicative',
                    'contributor_id': 'enhancements__tower__enemy_attack_level_skip__multiplier',
                    'input_value_type': 'resolved_value',
                },
            ],
        ),
        'state::tower.enemy_health_level_skip_pct': _FakeRow(
            3.9650000000000003,
            contributors=[
                {
                    'active': True,
                    'value': 1.5,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'lab.enemy_health_level_skip.account_state',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 1.0,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'relic__tower__enemy_health_level_skip__pct',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 0.55,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'workshop__tower__enemy_health_level_skip__pct',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 1.3,
                    'composition_stage': 'multiplicative',
                    'contributor_id': 'enhancements__tower__enemy_health_level_skip__multiplier',
                    'input_value_type': 'resolved_value',
                },
            ],
        ),
        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.hp': _FakeRow(500.0),
        'state::tower.regen': _FakeRow(100.0),
        'state::tower.range_m': _FakeRow(69.5),
        'state::wall.hp': _FakeRow(
            1000.0,
            contributors=[
                {
                    'active': True,
                    'value': 1000000000000.0,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'workshop__wall__health__flat',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 2.0,
                    'composition_stage': 'multiplicative',
                    'contributor_id': 'enhancement.wall_health_+.account_state',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 2.0,
                    'composition_stage': 'multiplicative',
                    'contributor_id': 'lab__wall__fortification__multiplier',
                    'input_value_type': 'resolved_value',
                },
            ],
        ),
        'state::wall.regen': _FakeRow(25.0),
        'state::wall.fortification_multiplier': _FakeRow(2.0),
        'state::tower.defense_pct': _FakeRow(90.0),
        'state::tower.thorns_damage_pct': _FakeRow(99.0),
        'state::wall.thorns_damage_pct': _FakeRow(15.84),
        'state::tower.death_defy_chance_pct': _FakeRow(30.0),
        'state::cards.plasma_cannon.effect_pct': _FakeRow(100.0),
        'state::capability.energy_shield.enabled': _FakeRow(True),
        'state::cards.energy_shield.recharge_cooldown_seconds': _FakeRow(480.0),
        'state::cards.energy_shield.extra_charge_count': _FakeRow(2.0),
        'state::cards.energy_net.mastery_effect': _FakeRow(
            1.0,
            contributors=[
                {
                    'active': True,
                    'value': 1.0,
                    'source_class': 'card_mastery',
                    'source_family': 'card_mastery',
                    'contributor_id': 'card_mastery__energy_net__effect__multiplier',
                    'input_value_type': 'resolved_value',
                },
            ],
        ),
        'state::module.orbital_augment.electron_count': _FakeRow(2.0),
        'state::module.primordial_collapse.bh_damage_reduction_pct': _FakeRow(80.0),
        'state::uw.black_hole.duration_seconds': _FakeRow(36.0),
        'state::uw.black_hole.cooldown_seconds': _FakeRow(46.0),
        'state::uw.chrono_field.duration_seconds': _FakeRow(50.0),
        'state::uw.chrono_field.cooldown_seconds': _FakeRow(60.0),
        'state::uw.chrono_field.damage_reduction_pct': _FakeRow(20.0),
        'state::uw.chrono_field.slow_pct': _FakeRow(30.0),
        'state::bot.flame.damage_reduction_pct': _FakeRow(0.35),
        'state::bot.flame.cooldown_seconds': _FakeRow(26.0),
        'state::bot.flame.range_m': _FakeRow(55.0),
        'state::bot.flame.effective_range_m': _FakeRow(73.15),
    }
    if omit_surface:
        rows.pop(omit_surface)
    monkeypatch.setattr(pipeline_mod, 'resolve_checkpoint_surfaces', lambda *args, **kwargs: object())
    monkeypatch.setattr(timing_mod, 'resolve_timing_consumer_bundle', lambda *args, **kwargs: object())
    monkeypatch.setattr(pipeline_mod, 'query_response_to_statbook', lambda *args, **kwargs: SimpleNamespace(rows=rows))


def _install_dissonance_pb_reference(
    monkeypatch,
    pipeline_mod,
    *,
    tier_label: str,
    category: str,
    wave: int,
):
    """Override one imported PB so reference-edge tests do not depend on live IDS churn."""
    from dataclasses import replace

    original_build_runtime_state = pipeline_mod.build_runtime_state

    def build_runtime_state_with_reference(*args, **kwargs):
        account_state = original_build_runtime_state(*args, **kwargs)
        pbs_by_tier = {
            str(tier): dict(values)
            for tier, values in dict(account_state.dissonance_pbs_by_tier or {}).items()
        }
        tier_pbs = dict(pbs_by_tier.get(tier_label) or {})
        tier_pbs[category] = int(wave)
        pbs_by_tier[tier_label] = tier_pbs
        return replace(account_state, dissonance_pbs_by_tier=pbs_by_tier)

    monkeypatch.setattr(
        pipeline_mod,
        'build_runtime_state',
        build_runtime_state_with_reference,
    )


def test_build_boss_wave_payload_replacement_inputs_drive_table_summary_export_and_diagnostics(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hit_count': 5,
            'electron_hit_count': 5,
            'boss_time_to_contact_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
        },
    )

    contract = payload.get('contract') or {}
    source_selection = payload.get('source_selection') or {}
    assert contract.get('simulator_owner') == 'simulators.evaluator_kernel.evaluate_overlay_row'
    assert contract.get('operator_table_source') == 'replacement'
    assert contract.get('summary_source') == 'replacement'
    assert contract.get('csv_export_source') == 'replacement'
    assert contract.get('diagnostics_source') == 'replacement'
    assert 'rollback_source' not in source_selection
    assert 'rollback_available' not in source_selection
    assert source_selection.get('active_source') == 'replacement'
    assert source_selection.get('csv_export_source') == 'replacement'
    assert source_selection.get('diagnostics_source') == 'replacement'
    assert not hasattr(pipeline_mod, 'build_start_of_run_state')
    assert not hasattr(pipeline_mod, 'build_boss_wave_table_payload')

    operator_rows = payload.get('operator_rows') or []
    assert payload.get('rows') == operator_rows
    assert operator_rows[0]['replacement_source'] == 'replacement'
    assert operator_rows[0]['tower_damage_per_second'] >= 0.0
    assert operator_rows[0]['summary_lane_id'] == 'avg'
    assert set(operator_rows[0]['lane_handle_ids']) == {'avg', 'min', 'max'}
    assert operator_rows[0]['boss_plasma_cannon_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_orb_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_electron_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_wall_thorns_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_expected_wall_thorns_damage_from_hits_pct'] >= operator_rows[0]['boss_wall_thorns_damage_to_boss_pct']
    assert operator_rows[0]['boss_hits_to_player'] == operator_rows[0]['boss_hits_taken']
    assert operator_rows[0]['boss_wall_thorns_hits'] >= operator_rows[0]['boss_hits_taken']
    assert operator_rows[0]['boss_hits_taken'] == max(
        0,
        operator_rows[0]['boss_wall_thorns_hits'] - int(operator_rows[0]['energy_shield_effective_charge_count']),
    )
    assert operator_rows[0]['flame_bot_hit_state_semantics'] == 'persistent_until_boss_death_after_first_flame_bot_hit'
    assert operator_rows[0]['flame_bot_lifetime_exposure_seconds'] == pytest.approx(operator_rows[0]['boss_ttk_seconds'])
    if operator_rows[0]['boss_ttk_seconds'] >= operator_rows[0]['boss_time_to_contact_seconds']:
        assert operator_rows[0]['flame_bot_lifetime_hit_chance_pct'] >= operator_rows[0]['flame_bot_contact_window_hit_chance_pct']
    else:
        assert operator_rows[0]['flame_bot_lifetime_hit_chance_pct'] <= operator_rows[0]['flame_bot_contact_window_hit_chance_pct']
    assert 'legacy_export_owner' not in contract
    assert 'legacy_shadow' not in payload
    assert payload.get('download_rows')[0]['replacement_source'] == 'replacement'
    assert payload.get('download_rows')[0]['operator_handle_id'] == operator_rows[0]['operator_handle_id']
    assert payload.get('download_rows')[0]['boss_wall_thorns_damage_to_boss_pct'] == operator_rows[0]['boss_wall_thorns_damage_to_boss_pct']
    assert payload.get('download_rows')[0]['boss_expected_wall_thorns_damage_from_hits_pct'] == operator_rows[0]['boss_expected_wall_thorns_damage_from_hits_pct']
    assert payload.get('download', {}).get('row_source') == 'replacement'
    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics.get('execution_mode') == 'staged_replacement'
    assert diagnostics.get('checkpoint_resolution_mode') == 'replacement_table1_table2_overlay'
    assert diagnostics.get('source_selection', {}).get('diagnostics_source') == 'replacement'
    assert diagnostics.get('replacement_model', {}).get('boss_ttk_contract') == 'v21_events_plus_continuous_boss_damage'
    assert diagnostics.get('replacement_model', {}).get('boss_kill_sources') == [
        'plasma_cannon',
        'orbs',
        'electrons',
        'continuous_boss_damage',
        'thorns_contact',
    ]
    assert diagnostics.get('replacement_model', {}).get('contact_resolution_sources') == ['wall_thorns_contact']
    assert diagnostics.get('replacement_model', {}).get('thorns_contact_source') == 'wall_thorns_contact_damage_pct_derived_from_tower_thorns_and_wall_thorns_lab'
    assert diagnostics.get('replacement_model', {}).get('wall_thorns_repeated_hit_multiplier') == 'Sharp Fortitude primary armor adds +1% wall-thorns damage taken per subsequent contact hit'
    assert diagnostics.get('replacement_model', {}).get('continuous_tower_dps_included') is True
    assert diagnostics.get('replacement_model', {}).get('flame_bot_hit_model') == 'static_uniform_center_overlap_recomputed_per_operator_row_over_boss_lifetime_when_ttk_is_known'
    assert diagnostics.get('replacement_model', {}).get('flame_bot_hit_state_semantics') == 'persistent_until_boss_death_after_first_flame_bot_hit'
    survival_policy = diagnostics.get('replacement_model', {}).get('stochastic_survival_policy') or {}
    assert survival_policy.get('death_defy') == 'diagnostic_only_not_applied_to_deterministic_boss_contact_ttd'
    assert survival_policy.get('death_defy_chance_pct') == pytest.approx(30.0)
    assert survival_policy.get('death_defy_effective_chance_pct') == pytest.approx(30.0)
    assert diagnostics.get('replacement_model', {}).get('contract_version') == 'boss_waves_replacement_v1'
    assert diagnostics.get('replacement_model', {}).get('table1_source_basis') == 'app_pipeline_qe_checkpoint_surfaces_to_run_plan'
    assert 'legacy_shadow_available' not in diagnostics
    assert 'legacy_shadow_materialized' not in diagnostics
    assert diagnostics.get('replacement_outputs', {}).get('download_row_count') == len(payload.get('download_rows') or [])
    family_coverage = diagnostics.get('replacement_primitive_family_coverage') or {}
    assert family_coverage.get('scope') == 'boss_waves_replacement_primitive_boundary'
    assert family_coverage.get('status') == 'covered'
    assert family_coverage.get('missing_requested_families') == []
    assert set(family_coverage.get('requested_effect_families') or []) == {
        'bot',
        'card_base',
        'card_mastery',
        'workshop',
        'enhancement',
        'module',
        'relic',
    }
    family_rows = family_coverage.get('families') or {}
    assert family_rows['workshop']['coverage_status'] == 'covered_by_qe_contributor'
    assert family_rows['enhancement']['coverage_status'] == 'covered_by_qe_contributor'
    assert family_rows['relic']['coverage_status'] == 'covered_by_qe_contributor'
    assert family_rows['card_mastery']['coverage_status'] == 'covered_by_qe_surface_and_contributor'
    assert 'replacement_primitive_family_coverage' not in diagnostics['replacement_primitive_inputs']['values']
    assert (
        diagnostics['replacement_primitive_semantics_ledger']['replacement_primitive_family_coverage']
        == family_coverage
    )
    ttk_inputs = diagnostics.get('replacement_primitive_semantics_ledger', {}).get('boss_ttk_input_contract') or {}
    assert ttk_inputs.get('orb_boss_total_damage_pct') == pytest.approx(6.0)
    assert ttk_inputs.get('orb_boss_total_damage_source') == 'default_orb_boss_total_damage_pct_6'
    assert ttk_inputs.get('electron_total_damage_pct') == pytest.approx(7.5)
    assert ttk_inputs.get('electron_total_damage_source') == 'orbital_augment_electron_count_times_boss_electron_pct'
    assert ttk_inputs.get('orbital_augment_electron_count') == pytest.approx(2.0)
    primitive_values = diagnostics.get('replacement_primitive_inputs', {}).get('values') or {}
    assert primitive_values['energy_shield_enabled'] is True
    assert primitive_values['energy_shield_recharge_cooldown_seconds'] == pytest.approx(480.0)
    assert primitive_values['energy_shield_extra_charge_count'] == pytest.approx(2.0)
    assert primitive_values['energy_shield_total_charge_count'] == pytest.approx(3.0)
    assert primitive_values['energy_shield_effective_charge_count'] == pytest.approx(3.0)
    assert primitive_values['tower_thorns_damage_pct'] == pytest.approx(99.0)
    assert primitive_values['wall_thorns_level'] == pytest.approx(16.0)
    assert primitive_values['wall_thorns_contact_damage_pct'] == pytest.approx(15.84)
    assert primitive_values['death_defy_chance_pct'] == pytest.approx(30.0)
    assert primitive_values['death_defy_down_percent_points'] == pytest.approx(0.0)
    assert primitive_values['death_defy_effective_chance_pct'] == pytest.approx(30.0)
    assert (
        primitive_values['death_defy_model_policy']
        == 'diagnostic_only_stochastic_survival_not_applied_to_deterministic_boss_contact_ttd'
    )
    assert primitive_values['primordial_collapse_bh_damage_reduction_pct'] == pytest.approx(80.0)
    assert primitive_values['black_hole_duration_seconds'] == pytest.approx(36.0)
    assert primitive_values['black_hole_cooldown_seconds'] == pytest.approx(46.0)
    primitive_ledger = diagnostics.get('replacement_primitive_semantics_ledger', {}).get('primitives') or {}
    assert primitive_ledger['state::tower.death_defy_chance_pct']['exact_value'] == pytest.approx(30.0)
    assert primitive_ledger['state::combat.death_defy_effective_chance_pct']['exact_value'] == pytest.approx(30.0)
    assert primitive_ledger['state::uw.chrono_field.slow_pct']['exact_value'] == pytest.approx(30.0)
    assert primitive_ledger['state::cards.slow_aura.enemy_speed_pct']['exact_value'] == pytest.approx(0.0)
    timed_dr = diagnostics.get('replacement_primitive_semantics_ledger', {}).get('timed_dr_semantic_contract') or {}
    timed_sources = timed_dr.get('sources') or {}
    assert timed_sources['black_hole_pbh']['damage_reduction_pct'] == pytest.approx(80.0)
    assert timed_sources['black_hole_pbh']['uptime_fraction'] == pytest.approx(36.0 / 46.0)
    assert timed_sources['black_hole_pbh']['effective_dr_fraction'] == pytest.approx(0.8 * (36.0 / 46.0))
    assert 'final_dr_override' not in timed_sources
    assert timed_sources['flame_bot']['primitive_status'] == 'static_boss_path_overlap_model'
    assert timed_sources['flame_bot']['uptime_source'] == 'static_boss_path_overlap_fraction'
    assert timed_sources['flame_bot']['static_hit_chance_model']['status'] == 'resolved'
    assert timed_sources['defense_field']['primitive_status'] == 'explicit_runtime_only_no_qe_surface_found'
    assert timed_dr['lane_policy'] == (
        'duration-style timed DR uses uptime-weighted average lanes; Flame Bot hit-chance sources are binary per boss, so min is miss, avg assumes the hit only when the modeled tag chance is near-certain, max is the full-hit lane, and hit probability is surfaced separately'
    )

    summary = payload.get('summary') or {}
    assert summary['max_surviving_wave'] == 27
    assert summary['first_failed_wave'] == 0
    assert summary['survives_through_end'] is True


def test_boss_wave_pressure_factor_flows_to_boss_health_and_incoming_damage(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', perk_mode='runtime_timeline')
    common_runtime_inputs = {
        'orb_boss_hit_pct': 2.5,
        'orb_boss_hit_count': 5,
        'electron_hit_count': 5,
        'boss_time_to_contact_seconds': 1.0,
        'effective_damage_reduction_pct': 90.0,
        'incoming_damage_multiplier': 1.0,
    }
    base_payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs=common_runtime_inputs,
    )
    pressured_payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={**common_runtime_inputs, 'boss_wave_pressure_factor': 2.0},
    )

    base_row = base_payload['operator_rows'][0]
    pressured_row = pressured_payload['operator_rows'][0]
    pressured_primitives = pressured_payload['diagnostics']['replacement_primitive_inputs']['values']
    assert pressured_row['incoming_damage_multiplier'] == pytest.approx(
        base_row['incoming_damage_multiplier'] * 2.0
    )
    assert pressured_row['boss_health'] == pytest.approx(base_row['boss_health'] * 2.0)
    assert pressured_primitives['boss_wave_pressure_factor'] == pytest.approx(2.0)
    assert pressured_primitives['boss_health_multiplier'] == pytest.approx(2.0)
    assert pressured_primitives['incoming_damage_multiplier'] == pytest.approx(2.0)
    assert pressured_payload['diagnostics']['scenario_runtime_inputs']['boss_wave_pressure_factor'] == pytest.approx(2.0)


def test_boss_wave_flame_bot_static_hit_chance_uses_path_overlap_and_energy_net():
    from simulators.timing import flame_bot_static_boss_hit_chance

    chance, components = flame_bot_static_boss_hit_chance(
        tower_range_m=69.5,
        flame_bot_effective_range_m=91.0,
        flame_bot_cooldown_seconds=5.0,
        boss_time_to_contact_seconds=6.3,
        energy_net_hold_seconds=4.3,
    )
    no_net_chance, _ = flame_bot_static_boss_hit_chance(
        tower_range_m=69.5,
        flame_bot_effective_range_m=91.0,
        flame_bot_cooldown_seconds=5.0,
        boss_time_to_contact_seconds=2.0,
        energy_net_hold_seconds=0.0,
    )
    partial_window_chance, partial_window = flame_bot_static_boss_hit_chance(
        tower_range_m=69.5,
        flame_bot_effective_range_m=200.0,
        flame_bot_cooldown_seconds=5.0,
        boss_time_to_contact_seconds=2.5,
        energy_net_hold_seconds=0.0,
    )
    lifetime_chance, lifetime_window = flame_bot_static_boss_hit_chance(
        tower_range_m=69.5,
        flame_bot_effective_range_m=91.0,
        flame_bot_cooldown_seconds=5.0,
        boss_time_to_contact_seconds=6.3,
        energy_net_hold_seconds=4.3,
        boss_lifetime_seconds=12.3,
    )
    pre_wall_chance, pre_wall_window = flame_bot_static_boss_hit_chance(
        tower_range_m=69.5,
        flame_bot_effective_range_m=91.0,
        flame_bot_cooldown_seconds=5.0,
        boss_time_to_contact_seconds=6.3,
        energy_net_hold_seconds=4.3,
        boss_lifetime_seconds=1.0,
    )

    assert components['status'] == 'resolved'
    assert components['model'] == 'static_uniform_flame_bot_center_vs_boss_path'
    assert components['tower_range_reference_m'] == pytest.approx(69.5)
    assert components['wall_radius_m'] == pytest.approx(20.0)
    assert components['energy_net_hold_seconds'] == pytest.approx(4.3)
    assert components['boss_lifetime_source'] == 'boss_time_to_contact_seconds_fallback'
    assert chance == pytest.approx(components['hit_fraction'])
    assert components['average_spatial_fraction'] > 0.75
    assert chance > no_net_chance
    assert partial_window['average_spatial_fraction'] == pytest.approx(1.0)
    assert partial_window_chance == pytest.approx(0.5)
    assert lifetime_window['boss_lifetime_source'] == 'explicit_boss_lifetime_seconds'
    assert lifetime_window['total_exposure_seconds'] == pytest.approx(12.3)
    assert lifetime_window['post_contact_seconds'] == pytest.approx(6.0)
    assert lifetime_window['hit_state_semantics'] == 'persistent_until_boss_death_after_first_flame_bot_hit'
    assert lifetime_chance > chance
    assert pre_wall_window['movement_seconds'] == pytest.approx(1.0)
    assert pre_wall_window['energy_net_hold_seconds'] == pytest.approx(0.0)
    assert pre_wall_window['post_contact_seconds'] == pytest.approx(0.0)
    assert pre_wall_chance < chance


def test_boss_wave_flame_bot_static_hit_chance_feeds_binary_hit_dr_when_not_overridden():
    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs
    from simulators.timing import flame_bot_static_boss_hit_chance

    primitives = {
        'tower_range_m': 69.5,
        'flame_bot_damage_reduction_pct': 0.95,
        'flame_bot_cooldown_seconds': 5.0,
        'flame_bot_effective_range_m': 91.0,
        'boss_time_to_contact_seconds': 6.3,
        'boss_time_to_contact_energy_net_hold_seconds': 4.3,
    }
    expected_chance, _ = flame_bot_static_boss_hit_chance(
        tower_range_m=primitives['tower_range_m'],
        flame_bot_effective_range_m=primitives['flame_bot_effective_range_m'],
        flame_bot_cooldown_seconds=primitives['flame_bot_cooldown_seconds'],
        boss_time_to_contact_seconds=primitives['boss_time_to_contact_seconds'],
        energy_net_hold_seconds=primitives['boss_time_to_contact_energy_net_hold_seconds'],
    )

    timed_dr_by_lane, sources = pipeline_mod._boss_wave_timed_dr_inputs(
        ScenarioRuntimeInputs.from_mapping({}),
        primitives=primitives,
    )

    expected_avg_dr = (
        0.95
        if expected_chance >= pipeline_mod.BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD
        else 0.0
    )
    assert timed_dr_by_lane == pytest.approx({'min': 0.0, 'avg': expected_avg_dr, 'max': 0.95})
    assert sources['flame_bot']['damage_reduction_pct'] == pytest.approx(95.0)
    assert sources['flame_bot']['uptime_fraction'] == pytest.approx(expected_chance)
    assert sources['flame_bot']['uptime_source'] == 'static_boss_path_overlap_fraction'
    assert sources['flame_bot']['primitive_status'] == 'static_boss_path_overlap_model'
    assert sources['flame_bot']['binary_outcome'] is True
    assert sources['flame_bot']['deterministic_hit_dr_fraction'] == pytest.approx(expected_avg_dr)
    assert sources['flame_bot']['binary_avg_hit_threshold'] == pytest.approx(
        pipeline_mod.BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD
    )
    assert sources['flame_bot']['lane_policy'] == (
        'binary_outcome_min_miss_avg_near_certain_hit_max_hit_probability_reported_separately'
    )
    assert sources['flame_bot']['effective_dr_fraction'] == pytest.approx(0.95 * expected_chance)
    assert sources['flame_bot']['probability_weighted_dr_fraction'] == pytest.approx(0.95 * expected_chance)
    assert sources['flame_bot']['encounter_hit_chance_fraction'] == pytest.approx(expected_chance)
    assert sources['flame_bot']['static_hit_chance_model']['hit_chance_pct'] == pytest.approx(expected_chance * 100.0)
    assert primitives['flame_bot_static_boss_hit_chance_pct'] == pytest.approx(expected_chance * 100.0)


def test_boss_wave_flame_bot_hit_chance_applies_binary_dr_with_probability_metadata():
    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs

    timed_dr_by_lane, sources = pipeline_mod._boss_wave_timed_dr_inputs(
        ScenarioRuntimeInputs.from_mapping({'flame_bot_boss_hit_chance_pct': 40.0}),
        primitives={
            'flame_bot_damage_reduction_pct': 0.35,
            'flame_bot_cooldown_seconds': 26.0,
        },
    )

    assert timed_dr_by_lane == pytest.approx({'min': 0.0, 'avg': 0.0, 'max': 0.35})
    assert sources['flame_bot']['damage_reduction_pct'] == pytest.approx(35.0)
    assert sources['flame_bot']['uptime_fraction'] == pytest.approx(0.4)
    assert sources['flame_bot']['uptime_source'] == 'manual_boss_hit_chance_fraction'
    assert sources['flame_bot']['effective_dr_fraction'] == pytest.approx(0.14)
    assert sources['flame_bot']['probability_weighted_dr_fraction'] == pytest.approx(0.14)
    assert sources['flame_bot']['encounter_hit_chance_fraction'] == pytest.approx(0.4)
    assert sources['flame_bot']['deterministic_hit_dr_fraction'] == pytest.approx(0.0)
    assert sources['flame_bot']['binary_avg_hit_threshold'] == pytest.approx(
        pipeline_mod.BOSS_WAVE_BINARY_OUTCOME_AVG_HIT_THRESHOLD
    )
    assert sources['flame_bot']['lane_policy'] == (
        'binary_outcome_min_miss_avg_near_certain_hit_max_hit_probability_reported_separately'
    )
    assert sources['flame_bot']['primitive_status'] == 'manual_boss_hit_chance_binary_model'

    override_dr_by_lane, override_sources = pipeline_mod._boss_wave_timed_dr_inputs(
        ScenarioRuntimeInputs.from_mapping(
            {
                'flame_bot_boss_hit_chance_pct': 99.0,
                'flame_bot_damage_reduction_pct': 95.0,
            }
        ),
        primitives={
            'flame_bot_damage_reduction_pct': 0.2,
            'flame_bot_cooldown_seconds': 50.0,
        },
    )

    assert override_dr_by_lane == pytest.approx({'min': 0.0, 'avg': 0.95, 'max': 0.95})
    assert override_sources['flame_bot']['damage_reduction_pct'] == pytest.approx(95.0)
    assert override_sources['flame_bot']['uptime_fraction'] == pytest.approx(0.99)
    assert override_sources['flame_bot']['effective_dr_fraction'] == pytest.approx(0.9405)
    assert override_sources['flame_bot']['probability_weighted_dr_fraction'] == pytest.approx(0.9405)
    assert override_sources['flame_bot']['deterministic_hit_dr_fraction'] == pytest.approx(0.95)


def test_boss_wave_summary_uses_sequential_not_independent_survival():
    from app import pipeline as pipeline_mod

    summary = pipeline_mod._replacement_summary_from_operator_rows([
        {'display_wave': 100, 'survives_boss': True, 'contact_envelope_survives_boss': True},
        {'display_wave': 110, 'survives_boss': False, 'contact_envelope_survives_boss': True},
        {'display_wave': 120, 'survives_boss': True, 'contact_envelope_survives_boss': False},
    ])

    assert summary['first_failed_wave'] == 110
    assert summary['last_contiguous_surviving_wave'] == 100
    assert summary['max_independent_surviving_wave'] == 120
    assert summary['max_wave'] == 100
    assert summary['max_surviving_wave'] == 100
    assert summary['selected_max_wave'] == 100
    assert summary['selected_model'] == 'unified_hit_by_hit_boss_survival'
    assert summary['hit_by_hit_max_wave'] == 100
    assert summary['contact_envelope_max_wave'] == 110
    assert summary['contact_envelope_first_failed_wave'] == 120


def test_boss_wave_summary_gc_loadout_uses_unified_hit_by_hit_lane():
    from app import pipeline as pipeline_mod

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 100,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': True,
            },
            {
                'display_wave': 110,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': False,
            },
            {
                'display_wave': 120,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': True,
            },
        ],
        perk_policy_preset='GC Max Waves',
    )

    assert summary['max_surviving_wave'] == 120
    assert summary['contact_envelope_max_wave'] == 120
    assert summary['pre_contact_boss_kill_max_wave'] == 100
    assert summary['pre_contact_boss_kill_max_independent_wave'] == 120
    assert summary['gc_pre_contact_max_wave'] == 100
    assert summary['gc_pre_contact_max_independent_wave'] == 120
    assert summary['gc_pre_contact_max_wave'] == summary['pre_contact_boss_kill_max_wave']
    assert summary['selected_max_wave'] == 120
    assert summary['selected_first_failed_wave'] == 0
    assert summary['selected_model'] == 'unified_hit_by_hit_boss_survival'


def test_boss_wave_summary_loadout_type_does_not_change_selected_max_wave_calculation():
    from app import pipeline as pipeline_mod

    rows = [
        {
            'display_wave': 100,
            'survives_boss': True,
            'contact_envelope_survives_boss': True,
            'boss_killed_before_contact': True,
        },
        {
            'display_wave': 110,
            'survives_boss': False,
            'contact_envelope_survives_boss': True,
            'boss_killed_before_contact': True,
        },
        {
            'display_wave': 120,
            'survives_boss': True,
            'contact_envelope_survives_boss': True,
            'boss_killed_before_contact': False,
        },
    ]

    summaries = {
        preset: pipeline_mod._replacement_summary_from_operator_rows(rows, perk_policy_preset=preset)
        for preset in ('eHP Max Waves', 'GC Max Waves', 'eHP Farming', 'GC Farming')
    }

    assert {summary['selected_max_wave'] for summary in summaries.values()} == {100}
    assert {summary['selected_model'] for summary in summaries.values()} == {'unified_hit_by_hit_boss_survival'}
    assert summaries['eHP Max Waves']['selected_loadout_type'] == 'ehp'
    assert summaries['GC Max Waves']['selected_loadout_type'] == 'gc'
    assert summaries['eHP Farming']['selected_loadout_type'] == 'farm'
    assert summaries['GC Farming']['selected_loadout_type'] == 'farm'


def test_boss_wave_dissonance_labels_do_not_switch_selected_lane():
    from app import pipeline as pipeline_mod

    rows = [
        {
            'display_wave': 100,
            'survives_boss': True,
            'contact_envelope_survives_boss': True,
            'boss_killed_before_contact': True,
        },
        {
            'display_wave': 110,
            'survives_boss': False,
            'contact_envelope_survives_boss': True,
            'boss_killed_before_contact': True,
        },
        {
            'display_wave': 120,
            'survives_boss': False,
            'contact_envelope_survives_boss': True,
            'boss_killed_before_contact': True,
        },
    ]

    for policy_preset in ('eHP Max Waves', 'GC Max Waves', 'eHP Farming', 'GC Farming'):
        for category in ('none', 'attack', 'defense', 'utility', 'ultimate_weapons'):
            summary = pipeline_mod._replacement_summary_from_operator_rows(
                rows,
                perk_policy_preset=policy_preset,
            )
            pipeline_mod._apply_dissonance_selected_lane_constraints(
                summary,
                dissonance_run_category=category,
            )

            expected_model = (
                'unified_hit_by_hit_boss_survival'
                if category == 'none'
                else f'unified_hit_by_hit_boss_survival_under_{category}_dissonance'
            )
            assert summary['selected_max_wave'] == 100
            assert summary['selected_max_wave'] == summary['hit_by_hit_max_wave']
            assert summary['contact_envelope_max_wave'] == 120
            assert summary['pre_contact_boss_kill_max_wave'] == 120
            assert summary['gc_pre_contact_max_wave'] == 120
            assert summary['gc_pre_contact_max_wave'] == summary['pre_contact_boss_kill_max_wave']
            assert summary['selected_model'] == expected_model


def test_boss_wave_loadout_and_card_profiles_resolve_max_wave_policies_separately():
    from app import pipeline as pipeline_mod

    ehp_loadout = pipeline_mod._boss_wave_loadout_profile_preset(
        boss_preset_name='Milestone',
        perk_policy_preset='eHP Max Waves',
    )
    gc_loadout = pipeline_mod._boss_wave_loadout_profile_preset(
        boss_preset_name='Milestone',
        perk_policy_preset='GC Max Waves',
    )

    assert ehp_loadout == 'Farming'
    assert pipeline_mod._boss_wave_card_profile_preset(
        loadout_profile_preset=ehp_loadout,
        perk_policy_preset='eHP Max Waves',
    ) == 'Farming'
    assert gc_loadout == 'Tourney'
    assert pipeline_mod._boss_wave_card_profile_preset(
        loadout_profile_preset=gc_loadout,
        perk_policy_preset='GC Max Waves',
    ) == 'Tourney'
    assert pipeline_mod._boss_wave_loadout_profile_preset(
        boss_preset_name='Milestone',
        perk_policy_preset='eHP Farming',
    ) == 'Farming'
    assert pipeline_mod._boss_wave_loadout_profile_preset(
        boss_preset_name='Milestone',
        perk_policy_preset='GC Farming',
    ) == 'Farming'


def test_boss_wave_ehp_max_waves_routes_farming_loadout_and_card_primitives():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='max_progression_policy',
            perk_policy_preset='eHP Max Waves',
        ),
        preset_name='Farming',
        tier_number=16,
        end_wave=100,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={},
    )

    diagnostics = payload['diagnostics']
    primitives = diagnostics['replacement_primitive_inputs']['values']
    contact_contract = diagnostics['contact_time_contract']

    assert diagnostics['loadout_profile_preset'] == 'Farming'
    assert diagnostics['card_profile_preset'] == 'Farming'
    assert primitives['loadout_profile_preset'] == 'Farming'
    assert primitives['card_profile_preset'] == 'Farming'
    assert primitives['energy_net_duration_seconds'] == pytest.approx(0.0)
    assert primitives['energy_net_mastery_multiplier'] == pytest.approx(1.0)
    assert primitives['energy_net_damage_multiplier_duration_seconds'] == pytest.approx(0.0)
    assert primitives['slow_aura_enemy_speed_pct'] == pytest.approx(0.0)
    assert primitives['boss_time_to_contact_energy_net_hold_seconds'] == pytest.approx(0.0)
    assert contact_contract['boss_time_to_contact_seconds']['energy_net_hold_seconds'] == pytest.approx(0.0)
    assert primitives['boss_time_to_contact_seconds'] == pytest.approx(
        primitives['boss_time_to_contact_base_seconds']
        / primitives['boss_time_to_contact_speed_remaining_fraction']
        + primitives['energy_net_duration_seconds']
    )
    assert diagnostics['replacement_primitive_semantics_ledger']['primitives'][
        'state::cards.energy_net.duration_seconds'
    ]['exact_value'] == pytest.approx(0.0)
    assert diagnostics['replacement_primitive_semantics_ledger']['primitives'][
        'state::cards.slow_aura.enemy_speed_pct'
    ]['exact_value'] == pytest.approx(0.0)
    assert diagnostics['replacement_primitive_semantics_ledger']['primitives'][
        'module::Sharp Fortitude.wall_thorns_damage_increase_per_hit'
    ]['exact_value'] == pytest.approx(0.01)


def test_boss_wave_payload_threads_tournament_enemy_speed_to_contact_time():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='none',
        ),
        preset_name='Tourney',
        tier_number=14,
        end_wave=20,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={'tournament_wave': 100},
    )

    diagnostics = payload['diagnostics']
    scenario_surfaces = diagnostics['scenario_surfaces']
    contact_time = diagnostics['contact_time_contract']['boss_time_to_contact_seconds']

    assert scenario_surfaces['bc_enemy_speed_increase_pct'] > 0.0
    assert 'enemy_speed_non_boss_pressure' in diagnostics['unsupported_terminal_pressures']
    assert contact_time['source'] == 'derived_geometry_displayed_proxy_base_cf_slow_aura_enemy_speed_energy_net'
    assert contact_time['enemy_speed_increase_fraction'] == pytest.approx(
        scenario_surfaces['bc_enemy_speed_increase_pct'] / 100.0
    )
    assert contact_time['boss_speed_multiplier'] == pytest.approx(
        scenario_surfaces['env_boss_speed_multiplier']
    )
    expected_movement_speed_multiplier = (
        (1.0 + contact_time['enemy_speed_increase_fraction']) * contact_time['boss_speed_multiplier']
    )
    assert contact_time['movement_speed_multiplier'] == pytest.approx(expected_movement_speed_multiplier)
    expected_speed_remaining = (
        (1.0 - contact_time['chrono_field_average_slow_fraction'])
        * (1.0 - contact_time['slow_aura_fraction'])
        * expected_movement_speed_multiplier
    )
    assert contact_time['speed_remaining_fraction'] == pytest.approx(expected_speed_remaining)
    assert contact_time['value'] == pytest.approx(
        (contact_time['base_seconds'] / expected_speed_remaining) + contact_time['energy_net_hold_seconds']
    )


def test_boss_wave_gc_damage_primitives_include_card_and_module_damage_support():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='max_progression_policy',
            perk_policy_preset='GC Max Waves',
        ),
        preset_name='Farming',
        tier_number=14,
        end_wave=100,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
    )

    diagnostics = payload['diagnostics']
    primitives = diagnostics['replacement_primitive_inputs']['values']
    ledger = diagnostics['replacement_primitive_semantics_ledger']['primitives']

    assert diagnostics['card_profile_preset'] == 'Tourney'
    assert primitives['card_profile_preset'] == 'Tourney'
    assert primitives['super_tower_active'] is True
    assert primitives['super_tower_bonus_multiplier'] > 1.0
    assert primitives['super_tower_cooldown_seconds'] > 0.0
    assert primitives['super_tower_mastery_active'] is True
    assert primitives['super_tower_uw_mastery_multiplier'] > 1.0
    assert primitives['edamage_super_tower_factor'] > primitives['super_tower_bonus_multiplier']
    assert primitives['energy_shield_enabled'] is True
    assert primitives['energy_shield_recharge_cooldown_seconds'] == pytest.approx(480.0)
    assert primitives['energy_shield_base_charge_count'] == pytest.approx(1.0)
    assert primitives['energy_shield_extra_charge_count'] == pytest.approx(2.0)
    assert primitives['energy_shield_total_charge_count'] == pytest.approx(3.0)
    assert primitives['energy_shields_down_fraction'] == pytest.approx(0.0)
    assert primitives['energy_shield_effective_charge_count'] == pytest.approx(3.0)
    assert primitives['death_defy_chance_pct'] >= 0.0
    assert primitives['death_defy_down_percent_points'] == pytest.approx(0.0)
    assert primitives['death_defy_effective_chance_pct'] == pytest.approx(primitives['death_defy_chance_pct'])
    assert (
        primitives['death_defy_model_policy']
        == 'diagnostic_only_stochastic_survival_not_applied_to_deterministic_boss_contact_ttd'
    )
    assert primitives['project_funding_cash_digit_multiplier_pct'] == pytest.approx(100.0)
    assert primitives['project_funding_current_cash'] == pytest.approx(50_000_000_000.0)
    assert primitives['edamage_project_funding_factor'] == pytest.approx(11.698970004336019)
    assert ledger['state::capability.energy_shield.enabled']['exact_value'] == pytest.approx(1.0)
    assert ledger['state::cards.energy_shield.recharge_cooldown_seconds']['exact_value'] == pytest.approx(480.0)
    assert ledger['state::cards.energy_shield.extra_charge_count']['exact_value'] == pytest.approx(2.0)
    assert ledger['state::combat.energy_shield_effective_charge_count']['exact_value'] == pytest.approx(3.0)
    assert ledger['state::tower.death_defy_chance_pct']['exact_value'] == pytest.approx(
        primitives['death_defy_chance_pct']
    )
    assert ledger['state::combat.death_defy_effective_chance_pct']['exact_value'] == pytest.approx(
        primitives['death_defy_effective_chance_pct']
    )
    assert ledger['derived::edamage.super_tower_factor']['exact_value'] == pytest.approx(
        primitives['edamage_super_tower_factor']
    )
    assert ledger['derived::edamage.super_tower_factor']['owner_layer'].startswith('QE publishes')
    assert ledger['support_surface::module.project_funding.current_cash']['exact_value'] == pytest.approx(
        primitives['project_funding_current_cash']
    )
    assert ledger['derived::edamage.project_funding_factor']['exact_value'] == pytest.approx(
        primitives['edamage_project_funding_factor']
    )


def test_boss_wave_primitive_request_covers_declared_hot_bundle_surfaces():
    from app import pipeline as pipeline_mod

    contract = yaml.safe_load((ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-consumer-bundles.yaml').read_text())
    bundle = next(
        bundle
        for consumer in contract['consumers']
        if consumer.get('consumer_id') == 'simulator_boss_wave'
        for bundle in consumer['bundles']
        if bundle.get('bundle_id') == 'boss_wave_hot_surfaces'
    )
    declared_surfaces = set(bundle.get('required_surface_ids') or ()) | set(bundle.get('optional_surface_ids') or ())
    requested_surfaces = set(pipeline_mod.BOSS_WAVE_REPLACEMENT_PRIMITIVE_SURFACE_IDS)
    requested_surfaces.update(pipeline_mod.BOSS_WAVE_OPTIONAL_PRIMITIVE_SURFACE_IDS)
    requested_surfaces.update(pipeline_mod.BOSS_WAVE_SLOW_AURA_OPTIONAL_PRIMITIVE_SURFACE_IDS)
    scenario_support_surfaces = {
        'support_surface::dissonance.attack_run_active',
        'support_surface::dissonance.defense_run_active',
        'support_surface::dissonance.utility_run_active',
        'support_surface::dissonance.ultimate_weapons_run_active',
    }

    assert declared_surfaces - requested_surfaces == set()
    assert requested_surfaces - declared_surfaces == scenario_support_surfaces
    assert 'state::tower.death_defy_chance_pct' in declared_surfaces


def test_boss_wave_summary_can_be_limited_by_explicit_non_boss_terminal_pressure():
    from app import pipeline as pipeline_mod

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 100,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': True,
            },
            {
                'display_wave': 110,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': True,
            },
        ],
        terminal_pressure_limits={
            'fleet_non_boss_pressure': 105,
            'elite_non_boss_pressure': 108,
        },
    )

    assert summary['selected_max_wave'] == 105
    assert summary['selected_first_failed_wave'] == 106
    assert summary['terminal_pressure_limiter'] == 'fleet_non_boss_pressure'
    assert summary['terminal_pressure_limited'] is True
    assert summary['selected_model'] == 'unified_hit_by_hit_boss_survival_limited_by_fleet_non_boss_pressure'


def test_boss_wave_unsupported_terminal_pressure_reference_cap_limits_selected_wave():
    from types import SimpleNamespace

    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 1400,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': False,
            },
        ],
    )
    account_state = SimpleNamespace(
        tier_progression_waves={},
        dissonance_pbs_by_tier={'Tier 16': {'ultimate_weapons': 780}},
    )

    pipeline_mod._apply_unsupported_terminal_pressure_reference_limit(
        summary,
        account_state=account_state,
        tier_number=16,
        dissonance_run_category='ultimate_weapons',
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
    )

    limit = summary['unsupported_pressure_reference_limit']
    assert summary['selected_max_wave'] == 780
    assert summary['selected_first_failed_wave'] == 781
    assert summary['terminal_pressure_limiter'] == 'unsupported_pressure_empirical_reference'
    assert summary['terminal_pressure_limited'] is True
    assert summary['unsupported_pressure_reference_limited'] is True
    assert limit['applicable'] is True
    assert limit['limited'] is True
    assert limit['reference_wave'] == 780
    assert limit['reference_kind'] == 'ids_dissonant_pb_wave'
    assert limit['uncapped_selected_max_wave'] == 1400
    assert summary['pressure_factor_reference_hint'] == {
        'enabled': True,
        'mode': 'raw_calculated_wave_to_reference_ratio_hint',
        'application': 'explicit_comparison_input_only',
        'certification_effect': 'none_not_applied',
        'boss_wave_pressure_factor': pytest.approx(1400 / 780),
        'rounded_boss_wave_pressure_factor': round(1400 / 780, 3),
        'direction': 'increase_pressure',
        'calculated_selected_max_wave': 1400,
        'reference_wave': 780,
        'reference_kind': 'ids_dissonant_pb_wave',
        'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'calculated_delta_vs_reference_wave': 620,
        'calculated_to_reference_ratio': pytest.approx(1400 / 780),
        'comparison_scenario_runtime_inputs': {'boss_wave_pressure_factor': pytest.approx(1400 / 780)},
    }
    assert limit['pressure_factor_reference_hint'] == summary['pressure_factor_reference_hint']
    assert (
        summary['selected_model']
        == 'unified_hit_by_hit_boss_survival_limited_by_unsupported_pressure_empirical_reference'
    )


def test_boss_wave_unsupported_terminal_pressure_reference_alignment_raises_underestimate():
    from types import SimpleNamespace

    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 700,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': False,
            },
        ],
    )
    account_state = SimpleNamespace(
        tier_progression_waves={},
        dissonance_pbs_by_tier={'Tier 16': {'ultimate_weapons': 780}},
    )

    pipeline_mod._apply_unsupported_terminal_pressure_reference_limit(
        summary,
        account_state=account_state,
        tier_number=16,
        dissonance_run_category='ultimate_weapons',
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
    )

    limit = summary['unsupported_pressure_reference_limit']
    assert summary['selected_max_wave'] == 780
    assert summary['selected_first_failed_wave'] == 781
    assert summary['selected_max_independent_wave'] == 780
    assert summary['terminal_pressure_limited'] is False
    assert summary['unsupported_pressure_reference_limited'] is False
    assert summary['unsupported_pressure_reference_aligned'] is True
    assert summary['unsupported_pressure_reference_alignment_direction'] == 'raised_to_empirical_reference'
    assert limit['applicable'] is True
    assert limit['limited'] is False
    assert limit['aligned'] is True
    assert limit['alignment_direction'] == 'raised_to_empirical_reference'
    assert limit['reference_wave'] == 780
    assert limit['uncapped_selected_max_wave'] == 700
    assert summary['pressure_factor_reference_hint']['enabled'] is True
    assert summary['pressure_factor_reference_hint']['boss_wave_pressure_factor'] == pytest.approx(700 / 780)
    assert summary['pressure_factor_reference_hint']['direction'] == 'decrease_pressure'
    assert summary['pressure_factor_reference_hint']['comparison_scenario_runtime_inputs'] == {
        'boss_wave_pressure_factor': pytest.approx(700 / 780)
    }
    assert (
        summary['selected_model']
        == 'unified_hit_by_hit_boss_survival_aligned_to_unsupported_pressure_empirical_reference'
    )


def test_boss_wave_unsupported_terminal_pressure_reference_cap_skips_when_explicitly_closed():
    from types import SimpleNamespace

    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 1400,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': False,
            },
        ],
    )
    pipeline_mod._apply_unsupported_terminal_pressure_reference_limit(
        summary,
        account_state=SimpleNamespace(
            tier_progression_waves={},
            dissonance_pbs_by_tier={'Tier 16': {'ultimate_weapons': 780}},
        ),
        tier_number=16,
        dissonance_run_category='ultimate_weapons',
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        runtime_inputs=ScenarioRuntimeInputs.from_mapping(
            {
                'fleet_terminal_max_wave': 900,
                'elite_terminal_max_wave': 900,
                'protector_terminal_max_wave': 900,
                'armored_terminal_max_wave': 900,
            }
        ),
    )

    assert summary['selected_max_wave'] == 1400
    assert summary['terminal_pressure_limited'] is False
    assert summary['unsupported_pressure_reference_limit']['applicable'] is False


def test_boss_wave_unsupported_terminal_pressure_reference_cap_skips_when_relevant_pressure_is_closed():
    from types import SimpleNamespace

    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 1400,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': False,
            },
        ],
    )
    pipeline_mod._apply_unsupported_terminal_pressure_reference_limit(
        summary,
        account_state=SimpleNamespace(
            tier_progression_waves={},
            dissonance_pbs_by_tier={'Tier 16': {'ultimate_weapons': 780}},
        ),
        tier_number=16,
        dissonance_run_category='ultimate_weapons',
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        runtime_inputs=ScenarioRuntimeInputs.from_mapping(
            {
                'armored_terminal_max_wave': 900,
            }
        ),
    )

    assert summary['selected_max_wave'] == 1400
    assert summary['terminal_pressure_limited'] is False
    assert summary['unsupported_pressure_reference_limit']['applicable'] is False


def test_boss_wave_unsupported_terminal_pressure_without_reference_blocks_selected_wave():
    from types import SimpleNamespace

    from app import pipeline as pipeline_mod
    from input.state_types import ScenarioRuntimeInputs

    summary = pipeline_mod._replacement_summary_from_operator_rows(
        [
            {
                'display_wave': 1400,
                'survives_boss': True,
                'contact_envelope_survives_boss': True,
                'boss_killed_before_contact': False,
            },
        ],
    )

    pipeline_mod._apply_unsupported_terminal_pressure_reference_limit(
        summary,
        account_state=SimpleNamespace(tier_progression_waves={}, dissonance_pbs_by_tier={}),
        tier_number=16,
        dissonance_run_category='ultimate_weapons',
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
    )

    limit = summary['unsupported_pressure_reference_limit']
    assert summary['selected_max_wave'] == 0
    assert summary['selected_first_failed_wave'] == 0
    assert summary['selected_max_independent_wave'] == 0
    assert summary['status'] == 'incomplete'
    assert summary['failure_kind'] == 'unsupported_terminal_pressure_without_reference_limit'
    assert summary['terminal_pressure_limiter'] == 'unsupported_pressure_missing_empirical_reference'
    assert summary['terminal_pressure_limited'] is True
    assert summary['unsupported_pressure_reference_limited'] is False
    assert summary['unsupported_pressure_missing_reference_blocked'] is True
    assert limit['applicable'] is True
    assert limit['missing_reference'] is True
    assert limit['blocked'] is True
    assert limit['uncapped_selected_max_wave'] == 1400
    assert summary['pressure_factor_reference_hint']['enabled'] is False
    assert summary['pressure_factor_reference_hint']['mode'] == 'no_positive_reference_wave'
    assert limit['pressure_factor_reference_hint'] == summary['pressure_factor_reference_hint']
    assert (
        summary['selected_model']
        == 'unified_hit_by_hit_boss_survival_blocked_by_unsupported_pressure_missing_empirical_reference'
    )


def test_build_boss_wave_payload_rejects_legacy_source_after_excision():
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match='replacement-only'):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={},
            boss_wave_source='legacy',
        )


def test_build_boss_wave_payload_fails_closed_on_unmapped_required_input_primitive(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, omit_surface='state::wall.regen')

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match="requires QE surface 'state::wall.regen'"):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hit_count': 5,
                'electron_hit_count': 5,
                'boss_time_to_contact_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


def test_build_boss_wave_payload_fails_closed_on_missing_wall_regen_base_primitive(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, omit_surface='state::tower.regen')

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match="requires QE surface 'state::tower.regen'"):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hit_count': 5,
                'electron_hit_count': 5,
                'boss_time_to_contact_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


def test_build_boss_wave_payload_fails_closed_on_missing_export_mapping(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)
    monkeypatch.setattr(
        pipeline_mod,
        'BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS',
        (*pipeline_mod.BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS, 'unmapped_export_field'),
    )

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match='missing required replacement fields'):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hit_count': 5,
                'electron_hit_count': 5,
                'boss_time_to_contact_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


@pytest.mark.live
def test_build_boss_wave_payload_live_path_avoids_delta_fallback():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload, build_runtime_state, load_inputs
    from input.state_types import ScenarioProjectionState, ScenarioRuntimeInputs
    from qe.publication import publish_query_surfaces
    from qe.routing import query_response_to_statbook, resolve_checkpoint_surfaces

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        perk_mode='runtime_timeline',
        runtime_state_overlay='disco_respec_2026_06_10',
    )
    runtime_inputs = {
            'orb_boss_hit_pct': 100.0,
            'orb_boss_hit_count': 1,
            'boss_time_to_contact_seconds': 1.0,
        'effective_damage_reduction_pct': 90.0,
        'incoming_damage_multiplier': 1.0,
    }
    bundle = load_inputs(ids_path=request.ids, manual_inputs_path=request.manual_inputs)
    account_state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
        manual_inputs=bundle.manual_inputs,
        runtime_state_overlay=request.runtime_state_overlay,
    )
    canonical_response = resolve_checkpoint_surfaces(
        account_state,
        requested_surface_ids=(
            'state::tower.enemy_attack_level_skip_pct',
            'state::tower.enemy_health_level_skip_pct',
            'state::wall.hp',
            'state::tower.hp',
            'state::wall.regen',
            'state::tower.regen',
            'state::wall.fortification_multiplier',
            'state::tower.defense_pct',
            'state::tower.defense_absolute',
            'state::tower.death_defy_chance_pct',
            'state::tower.thorns_damage_pct',
            'state::tower.range_m',
            'state::wall.thorns_damage_pct',
            'state::tower.orb_count',
            'state::tower.orb_speed_rpm',
            'state::cards.plasma_cannon.effect_pct',
            'state::capability.energy_shield.enabled',
            'state::cards.energy_shield.recharge_cooldown_seconds',
            'state::cards.energy_shield.extra_charge_count',
            'state::module.orbital_augment.electron_count',
            'state::module.primordial_collapse.bh_damage_reduction_pct',
            'support_surface::ehp.black_hole_duration_seconds',
            'support_surface::ehp.black_hole_cooldown_seconds',
            'state::uw.black_hole.base_duration_seconds',
            'state::uw.black_hole.base_cooldown_seconds',
            'state::uw.golden_tower.base_duration_seconds',
            'state::uw.golden_tower.base_cooldown_seconds',
            'state::uw.chrono_field.duration_seconds',
            'state::uw.chrono_field.cooldown_seconds',
            'state::uw.chrono_field.damage_reduction_pct',
            'state::bot.flame.owned',
            'state::bot.flame.damage_reduction_pct',
            'state::bot.flame.cooldown_seconds',
            'state::bot.flame.range_m',
            'state::bot.global.range_bonus_m',
            'state::bot.flame.effective_range_m',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
        scenario_projection_state=ScenarioProjectionState(second_wind_mastery_regen=True),
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(runtime_inputs),
    )
    canonical_statbook = query_response_to_statbook(canonical_response, notes='Boss Waves primitive authority reconciliation test.')
    publish_query_surfaces(canonical_statbook.rows, account_state_labs=getattr(account_state, 'labs', {}) or {})
    canonical = {
        surface_id: float(canonical_statbook.rows[surface_id].final_value)
        for surface_id in canonical_statbook.rows
        if canonical_statbook.rows[surface_id].final_value is not None
    }
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=50,
        boss_wave_step=1,
        stop_on_failure=False,
            scenario_runtime_inputs=runtime_inputs,
        )

    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics['actual_boss_interval_waves'] == 9
    assert diagnostics['actual_boss_interval_waves'] == diagnostics['scenario_surfaces']['boss_wave_interval']
    assert diagnostics['checkpoint_every_bosses'] == 1
    assert diagnostics['checkpoint_resolution_mode'] == 'replacement_table1_table2_overlay'
    assert diagnostics['execution_mode'] == 'staged_replacement'
    assert diagnostics['source_selection']['operator_table_source'] == 'replacement'
    assert diagnostics['source_selection']['summary_source'] == 'replacement'
    assert diagnostics['source_selection']['csv_export_source'] == 'replacement'
    assert diagnostics['source_selection']['diagnostics_source'] == 'replacement'
    assert payload['source_selection']['active_source'] == 'replacement'
    assert diagnostics['replacement_model']['boss_ttk_contract'] == 'v21_events_plus_continuous_boss_damage'
    assert diagnostics['replacement_model']['contract_version'] == 'boss_waves_replacement_v1'
    assert diagnostics['model_scope'] == 'boss_contact_survivability'
    assert diagnostics['not_full_max_wave_model'] is True
    assert diagnostics['model_certification']['certified_full_max_wave_model'] is False
    assert diagnostics['model_certification']['model_certification_status'] == 'partial_boss_contact_model'
    assert diagnostics['model_certification']['model_requirement_applicability']['boss_applicable_damage_semantics'] is False
    assert diagnostics['model_certification']['model_requirement_applicability']['gc_boss_applicable_damage_semantics'] is False
    assert 'source_owned_full_boss_applicable_damage_semantics' not in diagnostics['model_certification']['model_completion_blockers']
    assert diagnostics['model_certification']['model_requirement_applicability']['non_boss_terminal_pressure'] is False
    assert diagnostics['unsupported_terminal_pressures'] == []
    assert 'full_dissonance_family_masks' not in diagnostics['unsupported_terminal_pressures']
    assert diagnostics['dissonance_run_category'] == 'none'
    assert diagnostics['pbh_explicit_uptime_supported'] is True
    assert diagnostics['replacement_model']['lane_order'] == ['avg', 'min', 'max']
    assert diagnostics['replacement_model']['summary_lane_id'] == 'avg'
    assert diagnostics['perk_application_mode'] == 'runtime_timeline'
    assert diagnostics['perk_timeline_rows'] > 0
    assert canonical['state::tower.defense_absolute'] == pytest.approx(
        payload['diagnostics']['replacement_primitive_inputs']['values']['tower_defense_absolute']
    )
    assert diagnostics['perk_static_count'] == 0
    assert diagnostics['perk_static_pick_count'] == 0
    assert diagnostics['perk_mode'] == 'runtime_timeline'
    assert diagnostics['perk_state'] == 'on'
    assert diagnostics['perk_contract_owner'] == 'request_policy_with_scenario_guard'
    assert diagnostics['perk_mode_source'] == 'request_perk_mode'
    assert diagnostics['perk_state_source'] == 'request_perk_state_auto_or_on'
    assert diagnostics['perk_request_resolution'] == 'matched_request'
    assert payload['contract']['perk_timeline_mode'] == 'runtime_policy_projection'
    assert 'legacy_shadow_available' not in diagnostics
    assert 'legacy_shadow_materialized' not in diagnostics
    assert diagnostics['delta_fallback_count'] == 0
    primitive_inputs = diagnostics['replacement_primitive_inputs']
    assert primitive_inputs['layer'] == 'start_of_run_static_primitives_plus_second_wind_mastery_regen_projection_plus_row_evolved_workshop_skip_inputs_not_final_displayed_rows'
    primitives = primitive_inputs['values']
    assert primitives['survivability_projection_state']['second_wind_mastery_regen'] is True
    assert primitives['enemy_level_skip_reduction_fraction'] == pytest.approx(0.025)
    assert primitives['enemy_level_skip_chance_delta'] == pytest.approx(-0.025)
    expected_wall_regen = canonical['state::tower.regen'] * (canonical['state::wall.regen'] / 100.0)
    expected_wall_hp_pre_fort = (
        primitives['tower_hp']
        * primitives['wall_hp_ratio']
        * primitives['wall_hp_multiplier']
    )
    assert primitives['tower_hp_qe_surface'] == pytest.approx(canonical['state::tower.hp'])
    assert primitives['tower_hp'] >= canonical['state::tower.hp']
    assert primitives['attack_skip_chance'] == pytest.approx(canonical['state::tower.enemy_attack_level_skip_pct'] / 100.0)
    assert primitives['health_skip_chance'] == pytest.approx(canonical['state::tower.enemy_health_level_skip_pct'] / 100.0)
    assert primitives['wall_hp_qe_surface'] == pytest.approx(canonical['state::wall.hp'])
    assert primitives['wall_hp'] == pytest.approx(expected_wall_hp_pre_fort)
    assert primitives['tower_regen'] == pytest.approx(canonical['state::tower.regen'])
    assert primitives['wall_regen_percent_points'] == pytest.approx(canonical['state::wall.regen'])
    assert primitives['wall_regen'] == pytest.approx(expected_wall_regen)
    assert primitives['wall_fortification_multiplier'] == pytest.approx(canonical['state::wall.fortification_multiplier'])
    assert primitives['tower_defense_pct'] == pytest.approx(canonical['state::tower.defense_pct'])
    assert primitives['death_defy_chance_pct'] == pytest.approx(canonical['state::tower.death_defy_chance_pct'])
    assert primitives['death_defy_down_percent_points'] == pytest.approx(0.0)
    assert primitives['death_defy_effective_chance_pct'] == pytest.approx(canonical['state::tower.death_defy_chance_pct'])
    assert primitives['tower_thorns_damage_pct'] == pytest.approx(canonical['state::tower.thorns_damage_pct'])
    assert primitives['wall_thorns_contact_damage_pct'] == pytest.approx(canonical['state::wall.thorns_damage_pct'])
    assert primitives['wall_thorns_level'] == pytest.approx(float(account_state.labs['Wall Thorns']))
    assert primitives['tower_orb_count'] == pytest.approx(canonical['state::tower.orb_count'])
    assert primitives['tower_orb_speed_rpm'] == pytest.approx(canonical['state::tower.orb_speed_rpm'])
    assert primitives['plasma_cannon_effect_pct'] == pytest.approx(canonical['state::cards.plasma_cannon.effect_pct'])
    assert primitives['energy_shield_enabled'] == bool(canonical['state::capability.energy_shield.enabled'])
    assert primitives['energy_shield_recharge_cooldown_seconds'] == pytest.approx(
        canonical['state::cards.energy_shield.recharge_cooldown_seconds']
    )
    assert primitives['energy_shield_extra_charge_count'] == pytest.approx(
        canonical['state::cards.energy_shield.extra_charge_count']
    )
    assert primitives['energy_shield_total_charge_count'] == pytest.approx(3.0)
    assert primitives['energy_shield_effective_charge_count'] == pytest.approx(3.0)
    assert primitives['orbital_augment_electron_count'] == pytest.approx(canonical['state::module.orbital_augment.electron_count'])
    assert primitives['primordial_collapse_bh_damage_reduction_pct'] == pytest.approx(canonical['state::module.primordial_collapse.bh_damage_reduction_pct'])
    assert primitives['black_hole_duration_seconds'] == pytest.approx(canonical['state::uw.black_hole.base_duration_seconds'])
    assert primitives['black_hole_cooldown_seconds'] == pytest.approx(canonical['state::uw.black_hole.base_cooldown_seconds'])
    assert primitives['black_hole_base_duration_seconds'] == pytest.approx(canonical['state::uw.black_hole.base_duration_seconds'])
    assert primitives['black_hole_base_cooldown_seconds'] == pytest.approx(canonical['state::uw.black_hole.base_cooldown_seconds'])
    assert primitives['golden_tower_base_duration_seconds'] == pytest.approx(canonical['state::uw.golden_tower.base_duration_seconds'])
    assert primitives['golden_tower_base_cooldown_seconds'] == pytest.approx(canonical['state::uw.golden_tower.base_cooldown_seconds'])
    assert primitives['chrono_field_duration_seconds'] == pytest.approx(canonical['state::uw.chrono_field.duration_seconds'])
    assert primitives['chrono_field_cooldown_seconds'] == pytest.approx(canonical['state::uw.chrono_field.cooldown_seconds'])
    assert primitives['chrono_field_damage_reduction_pct'] == pytest.approx(canonical['state::uw.chrono_field.damage_reduction_pct'])
    assert primitives['tower_range_m'] == pytest.approx(canonical['state::tower.range_m'])
    assert primitives['flame_bot_owned'] == bool(canonical['state::bot.flame.owned'])
    assert primitives['flame_bot_damage_reduction_pct'] == pytest.approx(canonical['state::bot.flame.damage_reduction_pct'])
    assert primitives['flame_bot_cooldown_seconds'] == pytest.approx(canonical['state::bot.flame.cooldown_seconds'])
    assert primitives['flame_bot_effective_range_m'] > 0.0
    ledger = diagnostics['replacement_primitive_semantics_ledger']
    family_coverage = diagnostics['replacement_primitive_family_coverage']
    assert family_coverage['status'] == 'covered'
    assert family_coverage['missing_requested_families'] == []
    assert set(family_coverage['requested_effect_families']) == {
        'bot',
        'card_base',
        'card_mastery',
        'workshop',
        'enhancement',
        'module',
        'relic',
    }
    assert family_coverage['families']['bot']['coverage_status'] == 'covered_by_qe_surface_and_contributor'
    assert family_coverage['families']['card_base']['coverage_status'] == 'covered_by_qe_surface_and_contributor'
    assert family_coverage['families']['card_mastery']['coverage_status'] == 'covered_by_qe_surface'
    assert family_coverage['families']['workshop']['coverage_status'] == 'covered_by_qe_contributor'
    assert family_coverage['families']['enhancement']['coverage_status'] == 'covered_by_qe_contributor'
    assert family_coverage['families']['module']['coverage_status'] == 'covered_by_qe_surface_and_contributor'
    assert family_coverage['families']['relic']['coverage_status'] == 'covered_by_qe_contributor'
    assert family_coverage['families']['card_mastery']['surface_ids']
    assert 'workshop__tower__enemy_attack_level_skip__pct' in family_coverage['families']['workshop']['contributor_ids']
    assert 'relic__tower__enemy_attack_level_skip__pct' in family_coverage['families']['relic']['contributor_ids']
    assert ledger['replacement_primitive_family_coverage'] == family_coverage
    assert 'replacement_primitive_family_coverage' not in diagnostics['replacement_primitive_inputs']['values']
    assert ledger['primitives']['state::tower.enemy_attack_level_skip_pct']['state_phase'] == 'start_of_run'
    assert ledger['primitives']['state::tower.enemy_health_level_skip_pct']['state_phase'] == 'start_of_run'
    assert ledger['primitives']['state::tower.enemy_attack_level_skip_pct']['workshop_track'] == 'Enemy Attack Level Skip'
    assert ledger['primitives']['state::tower.enemy_health_level_skip_pct']['workshop_track'] == 'Enemy Health Level Skip'
    assert ledger['primitives']['state::tower.enemy_attack_level_skip_pct']['classification'] == 'transformed'
    assert ledger['primitives']['state::tower.enemy_health_level_skip_pct']['classification'] == 'transformed'
    assert ledger['primitives']['state::tower.hp']['state_phase'] == 'start_of_run'
    assert ledger['primitives']['state::tower.hp']['exact_value'] == pytest.approx(primitives['tower_hp'])
    assert ledger['primitives']['state::wall.hp']['semantic_meaning'].startswith('QE wall HP surface currently carries wall-health ratio contributors')
    assert ledger['primitives']['state::wall.hp']['fortification_transform'] == 'not_used_as_final_wall_hp'
    assert ledger['primitives']['state::wall.hp']['classification'] == 'transformed'
    assert ledger['primitives']['state::wall.hp']['boss_waves_semantic_decision'] == 'transformed_primitive_not_final_display_value'
    assert ledger['primitives']['state::wall.hp']['tower_hp'] == pytest.approx(primitives['tower_hp'])
    assert ledger['primitives']['state::wall.regen']['classification'] == 'transformed'
    assert ledger['primitives']['state::wall.regen']['boss_waves_semantic_decision'] == 'transformed_percent_points_primitive_not_final_hp_per_second'
    assert ledger['primitives']['state::wall.regen']['exact_value'] == pytest.approx(canonical['state::wall.regen'])
    assert ledger['primitives']['state::wall.regen']['row_input_value'] == pytest.approx(expected_wall_regen)
    assert ledger['primitives']['state::tower.regen']['exact_value'] == pytest.approx(canonical['state::tower.regen'])
    assert ledger['primitives']['state::tower.death_defy_chance_pct']['exact_value'] == pytest.approx(
        canonical['state::tower.death_defy_chance_pct']
    )
    assert ledger['primitives']['state::combat.death_defy_effective_chance_pct']['exact_value'] == pytest.approx(
        canonical['state::tower.death_defy_chance_pct']
    )
    assert ledger['primitives']['state::tower.regen']['state_phase'] == 'start_of_run_with_second_wind_mastery_regen_projection'
    assert ledger['primitives']['state::tower.thorns_damage_pct']['semantic_meaning'].endswith(
        'upstream base for Wall Thorns contact damage'
    )
    assert ledger['primitives']['state::wall.thorns_contact_damage_pct']['exact_value'] == pytest.approx(
        primitives['wall_thorns_contact_damage_pct']
    )
    assert 'contact-resolution source' in ledger['primitives']['state::wall.thorns_contact_damage_pct']['semantic_meaning']
    assert ledger['primitives']['state::module.primordial_collapse.bh_damage_reduction_pct']['exact_value'] == pytest.approx(
        canonical['state::module.primordial_collapse.bh_damage_reduction_pct']
    )
    timed_sources = ledger['timed_dr_semantic_contract']['sources']
    assert timed_sources['black_hole_pbh']['damage_reduction_pct'] == pytest.approx(
        canonical['state::module.primordial_collapse.bh_damage_reduction_pct']
    )
    assert timed_sources['black_hole_pbh']['uptime_fraction'] == pytest.approx(
        primitives['black_hole_duration_seconds'] / primitives['black_hole_cooldown_seconds']
    )
    assert timed_sources['black_hole_pbh']['effective_dr_fraction'] == pytest.approx(
        (canonical['state::module.primordial_collapse.bh_damage_reduction_pct'] / 100.0)
        * (primitives['black_hole_duration_seconds'] / primitives['black_hole_cooldown_seconds'])
    )
    assert timed_sources['flame_bot']['primitive_status'] == 'static_boss_path_overlap_model'
    assert timed_sources['flame_bot']['uptime_source'] == 'static_boss_path_overlap_fraction'
    expected_flame_dr_pct = primitives['flame_bot_damage_reduction_pct']
    if expected_flame_dr_pct <= 1.0:
        expected_flame_dr_pct *= 100.0
    assert timed_sources['flame_bot']['damage_reduction_pct'] == pytest.approx(expected_flame_dr_pct)
    assert timed_sources['flame_bot']['static_hit_chance_model']['status'] == 'resolved'
    assert timed_sources['flame_bot']['binary_outcome'] is True
    assert timed_sources['flame_bot']['effective_dr_fraction'] == pytest.approx(
        timed_sources['flame_bot']['probability_weighted_dr_fraction']
    )
    assert timed_sources['flame_bot']['probability_weighted_dr_fraction'] <= (
        timed_sources['flame_bot']['damage_reduction_pct'] / 100.0
    )
    assert timed_sources['defense_field']['primitive_status'] == 'explicit_runtime_only_no_qe_surface_found'
    assert ledger['primitives']['module::Sharp Fortitude.wall_thorns_damage_increase_per_hit']['exact_value'] == pytest.approx(0.01)
    assert ledger['workshop_levels']['Wall Health']['exact_value'] == account_state.workshop['Wall Health'].preset_levels['Farming']
    assert ledger['workshop_levels']['Health Regen']['exact_value'] == account_state.workshop['Health Regen'].preset_levels['Farming']
    assert ledger['workshop_levels']['Wall Fortification']['exact_value'] == account_state.labs['Wall Fortification']
    assert ledger['workshop_levels']['Wall Fortification']['fortification_transform'] == 'lab level is converted by QE into state::wall.fortification_multiplier'
    fort_check = ledger['fortification_double_application_check']
    assert fort_check['state_wall_hp_includes_fortification'] is True
    assert fort_check['reconstructed_wall_hp'] == pytest.approx(primitives['wall_hp'] * primitives['wall_fortification_multiplier'])
    assert fort_check['qe_state_wall_hp_surface'] == pytest.approx(canonical['state::wall.hp'])
    assert fort_check['policy'].startswith('derive pre-fort wall HP from tower_hp')
    hp_check = ledger['wall_hp_formula_check']
    assert hp_check['tower_hp'] == pytest.approx(primitives['tower_hp'])
    assert hp_check['reconstructed_displayed_wall_hp_pre_fort'] == pytest.approx(expected_wall_hp_pre_fort)
    regen_check = ledger['wall_regen_formula_check']
    assert regen_check['tower_regen'] == pytest.approx(canonical['state::tower.regen'])
    assert regen_check['wall_regen_percent_points'] == pytest.approx(canonical['state::wall.regen'])
    assert regen_check['reconstructed_displayed_wall_regen'] == pytest.approx(expected_wall_regen)
    semantic_contract = ledger['boss_waves_wall_surface_semantic_contract']
    assert semantic_contract['state::wall.hp']['decision'] == 'transformed_primitive_not_final_display_value'
    assert semantic_contract['state::wall.regen']['decision'] == 'transformed_percent_points_primitive_not_final_hp_per_second'
    assert diagnostics['replacement_display_derivation']['wall_hp'].startswith('operator_rows.wall_hp')
    assert diagnostics['replacement_model']['death_wave_health_multiplier_applies_to'] == 'table1_row_evolved_tower_hp_then_wall_hp_not_wall_regen_or_enemy_health'
    assert diagnostics['replacement_model']['boss_survival_model'] == 'max_waves_compares_v21_plus_continuous_boss_ttk_against_hit_by_hit_wall_ttd_with_between_hit_regen_only'
    ttk_inputs = ledger['boss_ttk_input_contract']
    assert ttk_inputs['orb_boss_total_damage_pct'] == pytest.approx(6.0)
    assert ttk_inputs['orb_boss_total_damage_source'] == 'default_orb_boss_total_damage_pct_6'
    assert ttk_inputs['electron_total_damage_pct'] == pytest.approx(canonical['state::module.orbital_augment.electron_count'] * 3.75)
    assert ttk_inputs['electron_total_damage_source'] == 'orbital_augment_electron_count_times_boss_electron_pct'
    rows = payload.get('rows') or []
    assert diagnostics['boss_wave_debug_ledger']['sample_rows']
    assert rows
    assert payload['summary']['status'] == 'complete'
    assert payload['summary']['failure_kind'] is None
    assert payload['summary']['first_unresolved_wave'] is None
    assert payload['summary']['max_surviving_wave'] == 45


@pytest.mark.live
def test_boss_wave_current_farming_mvn_primary_pc_assist_bh_dr_is_not_permanent():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload, build_runtime_state, load_inputs

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        preset='Farming',
        perk_mode='max_progression_policy',
        perk_state='auto',
        perk_policy_preset='eHP Farming',
    )
    bundle = load_inputs(ids_path=request.ids, manual_inputs_path=request.manual_inputs)
    account_state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
        manual_inputs=bundle.manual_inputs,
    )
    core_selection = account_state.module_presets['Farming']['core']
    assert core_selection.primary == 'Multiverse Nexus'
    assert core_selection.assist == 'Primordial Collapse'

    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=20,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={},
    )
    diagnostics = payload['diagnostics']
    primitives = diagnostics['replacement_primitive_inputs']['values']
    assert primitives['primordial_collapse_bh_damage_reduction_pct'] == pytest.approx(10.0)
    assert primitives['black_hole_duration_seconds'] < primitives['black_hole_cooldown_seconds']
    assert primitives['black_hole_duration_seconds'] > 0.0
    assert primitives['black_hole_cooldown_seconds'] > 0.0

    timed_sources = diagnostics['replacement_primitive_semantics_ledger'][
        'timed_dr_semantic_contract'
    ]['sources']
    black_hole = timed_sources['black_hole_pbh']
    raw_uptime = primitives['black_hole_duration_seconds'] / primitives['black_hole_cooldown_seconds']
    assert black_hole['damage_reduction_pct'] == pytest.approx(10.0)
    assert black_hole['duration_seconds'] == pytest.approx(primitives['black_hole_duration_seconds'])
    assert black_hole['cooldown_seconds'] == pytest.approx(primitives['black_hole_cooldown_seconds'])
    assert black_hole['uptime_source'] == 'duration_over_cooldown'
    assert black_hole['uptime_fraction'] == pytest.approx(raw_uptime)
    assert black_hole['uptime_fraction'] < 1.0
    assert black_hole['effective_dr_fraction'] == pytest.approx(0.10 * raw_uptime)


def test_boss_wave_payload_flows_explicit_overheat_decay_inputs_into_table_rows():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=36,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 1.0,
            'orb_boss_total_damage_pct': 6.0,
            'enemy_level_skip_decay_pct': 10.0,
            'enemy_level_skip_decay_interval_waves': 9.0,
            'enemy_level_skip_decay_start_wave': 18.0,
            'tower_damage_decay_pct': 10.0,
            'tower_damage_decay_start_wave': 16.0,
            'tower_health_decay_pct': 10.0,
            'tower_health_decay_start_wave': 16.0,
        },
    )

    primitive_values = payload['diagnostics']['replacement_primitive_inputs']['values']
    assert primitive_values['enemy_level_skip_decay_fraction_per_step'] == pytest.approx(0.1)
    assert primitive_values['enemy_level_skip_decay_interval_waves'] == 9
    assert primitive_values['enemy_level_skip_decay_start_wave'] == 18
    rows = payload['operator_rows']
    by_wave = {int(row['display_wave']): row for row in rows}
    assert by_wave[18]['overheat_effects']['tower_damage_decay_steps'] == pytest.approx(0.0)
    assert by_wave[27]['overheat_effects']['tower_damage_decay_steps'] == pytest.approx(1.0)
    assert by_wave[36]['overheat_effects']['tower_damage_decay_steps'] == pytest.approx(2.0)
    assert by_wave[36]['overheat_effects']['tower_health_decay_multiplier'] == pytest.approx(0.8)
    assert by_wave[36]['attack_wave'] > by_wave[27]['attack_wave']


def test_boss_wave_payload_defaults_skip_decay_to_kb_curve_when_overheat_start_is_known():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline'),
        preset_name='Farming',
        tier_number=14,
        end_wave=36,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 1.0,
            'orb_boss_total_damage_pct': 6.0,
            'enemy_level_skip_decay_start_wave': 18.0,
        },
    )

    primitive_values = payload['diagnostics']['replacement_primitive_inputs']['values']
    assert primitive_values['enemy_level_skip_decay_source'] == 'kb.tournaments.tables.battle-condition-magnitudes.csv:enemy_level_skip'
    assert primitive_values['enemy_level_skip_decay_start_wave'] == 18
    assert primitive_values['enemy_level_skip_decay_schedule'][0] == pytest.approx(0.01)
    assert primitive_values['enemy_level_skip_decay_schedule'][20] == pytest.approx(0.02)


def test_boss_wave_payload_can_report_explicit_non_boss_terminal_limiter():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=200,
        boss_wave_step=5,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
            'fleet_terminal_max_wave': 90.0,
            'elite_terminal_max_wave': 120.0,
        },
    )

    summary = payload['summary']
    diagnostics = payload['diagnostics']
    assert summary['terminal_pressure_limits']['fleet_non_boss_pressure'] == 90
    assert summary['terminal_pressure_limiter'] == 'fleet_non_boss_pressure'
    assert summary['terminal_pressure_limited'] is True
    assert summary['selected_max_wave'] == 90
    assert diagnostics['terminal_pressure_limiter'] == 'fleet_non_boss_pressure'


def test_boss_wave_model_certification_marks_explicit_runtime_override_closure():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=200,
        boss_wave_step=5,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
            'boss_applicable_damage_per_second': 1.0,
            'tower_damage_decay_pct': 1.0,
            'tower_health_decay_pct': 1.0,
            'fleet_terminal_max_wave': 90.0,
            'elite_terminal_max_wave': 120.0,
            'protector_terminal_max_wave': 130.0,
            'armored_terminal_max_wave': 140.0,
            'boss_terminal_max_wave': 150.0,
        },
    )

    certification = payload['diagnostics']['model_certification']
    assert certification['certified_full_max_wave_model'] is False
    assert certification['runtime_override_closure'] == {
        'non_boss_terminal_pressure': True,
        'v28_damage_health_decay_magnitudes': True,
        'boss_applicable_damage_semantics': True,
        'gc_boss_applicable_damage_semantics': True,
    }
    assert certification['model_requirement_applicability']['non_boss_terminal_pressure'] is False
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in certification['model_completion_blockers']
    assert 'source_owned_v28_damage_health_decay_magnitudes' not in certification['model_completion_blockers']
    assert 'source_owned_full_boss_applicable_damage_semantics' not in certification['model_completion_blockers']


def test_boss_wave_high_tier_dissonance_flags_unsupported_terminal_pressure():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        perk_mode='runtime_timeline',
        perk_state='on',
        perk_policy_preset='eHP Max Waves',
    )
    payload = build_boss_wave_payload(
        request,
        preset_name='Milestone',
        tier_number=17,
        end_wave=120,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='ultimate_weapons',
    )

    diagnostics = payload['diagnostics']
    certification = diagnostics['model_certification']
    assert {
        'armored_enemies_blocked_hits',
        'knockback_resistance_non_boss_pressure',
        'protector_ultimate_deferred',
        'boss_ultimate_deferred',
        'mass_enforcement_deferred',
    } <= set(diagnostics['unsupported_terminal_pressures'])
    assert certification['model_requirement_applicability']['non_boss_terminal_pressure'] is True
    assert 'source_owned_non_boss_terminal_pressure_formulas' in certification['model_completion_blockers']
    assert certification['unsupported_terminal_pressures'] == diagnostics['unsupported_terminal_pressures']
    assert diagnostics['replacement_model']['unsupported_terminal_pressures'] == diagnostics['unsupported_terminal_pressures']
    assert payload['summary']['pressure_factor_reference_hint'] == diagnostics['pressure_factor_reference_hint']
    assert diagnostics['pressure_factor_reference_hint']['enabled'] in {False, True}
    assert diagnostics['pressure_factor_reference_hint'].get('application') in {
        None,
        'explicit_comparison_input_only',
    }


@pytest.mark.live
def test_boss_wave_selected_payload_pressure_factor_closes_unsupported_pressure_as_approximation():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            runtime_state_overlay='disco_respec_2026_06_10',
        ),
        preset_name='Milestone',
        tier_number=16,
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_total_damage_pct': 6.0,
            'boss_wave_pressure_factor': 1.25,
        },
        dissonance_run_category='ultimate_weapons',
    )

    diagnostics = payload['diagnostics']
    certification = diagnostics['model_certification']
    closure = certification['non_boss_terminal_pressure_closure']

    assert diagnostics['context_status'] == 'complete'
    assert payload['summary']['selected_max_wave'] > 0
    assert diagnostics['scenario_runtime_inputs']['boss_wave_pressure_factor'] == pytest.approx(1.25)
    assert diagnostics['unsupported_terminal_pressures']
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in diagnostics['model_completion_blockers']
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in certification['model_completion_blockers']
    assert diagnostics['model_certification_status'] == certification['model_certification_status']
    assert diagnostics['certified_full_max_wave_model'] == certification['certified_full_max_wave_model']
    assert diagnostics['runtime_override_closure'] == certification['runtime_override_closure']
    assert diagnostics['effective_model_closure'] == certification['effective_model_closure']
    assert diagnostics['non_boss_terminal_pressure_closure'] == closure
    assert certification['runtime_override_closure']['non_boss_terminal_pressure'] is True
    assert certification['effective_model_closure']['non_boss_terminal_pressure'] is True
    assert closure == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': True,
        'boss_wave_pressure_factor': 1.25,
    }
    assert certification['terminal_pressure_runtime_override_status']['closed'] is False
    assert certification['terminal_pressure_runtime_override_status']['missing_fields']


@pytest.mark.live
def test_boss_wave_milestone_matrix_caps_unsupported_high_tier_to_manual_dissonance_reference():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('ultimate_weapons',),
    )

    row = matrix['rows'][0]
    candidate = row['candidate_results'][0]
    assert row['reference_kind'] == 'ids_dissonant_pb_wave'
    assert row['reference_wave'] == 780
    assert row['dissonance_pb_reference_wave'] == 780
    assert row['best_selected_max_wave'] == 780
    assert row['delta_vs_reference_wave'] == 0
    assert row['terminal_pressure_limiter'] == 'unsupported_pressure_empirical_reference'
    assert row['terminal_pressure_reference_status'] == 'empirical_reference_limited'
    assert row['unsupported_pressure_reference_limited'] is True
    assert row['unsupported_pressure_uncapped_selected_max_wave'] > 780
    assert candidate['selected_max_wave'] == 780
    assert candidate['terminal_pressure_reference_status'] == 'empirical_reference_limited'
    assert candidate['unsupported_pressure_reference_limited'] is True
    assert candidate['unsupported_pressure_reference_limit']['uncapped_selected_max_wave'] > 780
    assert 'source_owned_non_boss_terminal_pressure_formulas' in row['model_completion_blockers']


@pytest.mark.live
def test_boss_wave_milestone_matrix_aligns_unsupported_result_to_manual_dissonance_reference():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(15,),
        end_wave=3200,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('ultimate_weapons',),
    )

    row = matrix['rows'][0]
    candidate = row['candidate_results'][0]
    reference_wave = row['reference_wave']
    uncapped_wave = row['unsupported_pressure_uncapped_selected_max_wave']
    assert isinstance(reference_wave, int) and reference_wave > 0
    assert isinstance(uncapped_wave, int) and uncapped_wave > 0
    expected_direction = (
        'capped_to_empirical_reference'
        if uncapped_wave > reference_wave
        else 'raised_to_empirical_reference'
        if uncapped_wave < reference_wave
        else 'already_at_empirical_reference'
    )
    assert row['reference_kind'] == 'ids_dissonant_pb_wave'
    assert row['dissonance_pb_reference_wave'] == reference_wave
    assert row['best_selected_max_wave'] == reference_wave
    assert row['delta_vs_reference_wave'] == 0
    assert row['unsupported_pressure_reference_limited'] is (uncapped_wave > reference_wave)
    assert row['unsupported_pressure_reference_aligned'] is True
    assert row['terminal_pressure_limiter'] == (
        'unsupported_pressure_empirical_reference' if uncapped_wave > reference_wave else None
    )
    assert row['terminal_pressure_reference_status'] == (
        'empirical_reference_limited' if uncapped_wave > reference_wave else 'empirical_reference_aligned'
    )
    assert row['unsupported_pressure_reference_alignment_direction'] == expected_direction
    assert candidate['selected_max_wave'] == reference_wave
    assert candidate['terminal_pressure_reference_status'] == row['terminal_pressure_reference_status']
    assert candidate['unsupported_pressure_reference_limit']['reference_wave'] == reference_wave
    assert candidate['unsupported_pressure_reference_limit']['uncapped_selected_max_wave'] == uncapped_wave
    assert candidate['unsupported_pressure_reference_alignment_direction'] == expected_direction
    assert 'source_owned_non_boss_terminal_pressure_formulas' in row['model_completion_blockers']


@pytest.mark.live
def test_boss_wave_milestone_matrix_defaults_to_clean_ids_reference_alignment_with_comparison_opt_out():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    comparison_matrix = build_boss_wave_milestone_matrix(
        request,
        tiers=(14,),
        end_wave=5000,
        boss_wave_step=10,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        dissonance_run_categories=('utility',),
        align_clean_reference_rows=False,
    )
    comparison_row = comparison_matrix['rows'][0]

    default_matrix = build_boss_wave_milestone_matrix(
        request,
        tiers=(14,),
        end_wave=5000,
        boss_wave_step=10,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        dissonance_run_categories=('utility',),
    )
    row = default_matrix['rows'][0]
    candidate = next(
        candidate
        for candidate in row['candidate_results']
        if candidate['selected_max_wave'] == row['best_calculated_selected_max_wave']
    )
    reference_wave = comparison_row['reference_wave']
    assert isinstance(reference_wave, int) and reference_wave > 0
    nearest_lane = row['reference_nearest_lane']
    nearest_lane_label = row['reference_nearest_lane_label']
    nearest_lane_wave = row['reference_nearest_lane_wave']
    lane_wave_by_name = {
        'hit_by_hit': row['best_hit_by_hit_max_wave'],
        'contact_envelope': row['best_contact_envelope_max_wave'],
        'pre_contact_boss_kill': row['best_pre_contact_boss_kill_max_wave'],
        'gc_pre_contact': row['best_gc_pre_contact_max_wave'],
    }
    assert nearest_lane in lane_wave_by_name
    assert nearest_lane_label
    assert nearest_lane_wave == lane_wave_by_name[nearest_lane]
    lane_delta = nearest_lane_wave - reference_wave
    calculated_delta = comparison_row['best_calculated_selected_max_wave'] - reference_wave
    calculated_ratio = comparison_row['best_calculated_selected_max_wave'] / reference_wave

    assert comparison_matrix['ids_reference_alignment_enabled'] is False
    assert comparison_row['reference_wave'] == reference_wave
    assert comparison_row['best_selected_max_wave'] == comparison_row['best_calculated_selected_max_wave']
    assert comparison_row['delta_vs_reference_wave'] != 0

    assert default_matrix['ids_reference_alignment_enabled'] is True
    assert row['reference_wave'] == reference_wave
    assert row['best_calculated_selected_max_wave'] == comparison_row['best_calculated_selected_max_wave']
    assert row['best_hit_by_hit_max_wave'] == candidate['hit_by_hit_max_wave']
    assert row['best_contact_envelope_max_wave'] == candidate['contact_envelope_max_wave']
    assert row['best_pre_contact_boss_kill_max_wave'] == candidate['pre_contact_boss_kill_max_wave']
    assert row['best_gc_pre_contact_max_wave'] == candidate['gc_pre_contact_max_wave']
    assert row['best_contact_envelope_max_wave'] == row['best_calculated_selected_max_wave']
    assert row['reference_nearest_lane'] == nearest_lane
    assert row['reference_nearest_lane_label'] == nearest_lane_label
    assert row['reference_nearest_lane_wave'] == nearest_lane_wave
    assert row['reference_nearest_lane_delta_vs_reference_wave'] == lane_delta
    assert row['reference_nearest_lane_abs_delta_wave'] == abs(lane_delta)
    assert row['reference_lane_alignment'] == {
        'reference_wave': reference_wave,
        'nearest_lane': nearest_lane,
        'nearest_lane_label': nearest_lane_label,
        'nearest_lane_wave': nearest_lane_wave,
        'nearest_lane_delta_vs_reference_wave': lane_delta,
        'nearest_lane_abs_delta_wave': abs(lane_delta),
    }
    assert row['reference_quality'] == {
        'reference_wave': reference_wave,
        'reference_kind': 'ids_dissonant_pb_wave',
        'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'low_wave_threshold': 3000,
        'below_low_wave_threshold': False,
        'pb_age_status': 'age_unknown_no_source_timestamp',
        'dissonance_pb_bonus_cap_wave': 5000,
        'dissonance_pb_bonus_cap_reached': False,
        'reference_interpretation': 'exact_wave_reference',
        'exact_reference': True,
        'calibration_candidate': True,
        'caveats': ['pb_age_unknown_no_source_timestamp'],
    }
    assert row['best_selected_max_wave'] == reference_wave
    assert row['delta_vs_reference_wave'] == 0
    assert row['calculated_delta_vs_reference_wave'] == calculated_delta
    assert row['calculated_to_reference_ratio'] == pytest.approx(calculated_ratio)
    assert row['pressure_factor_reference_hint']['enabled'] is True
    assert row['pressure_factor_reference_hint']['mode'] == 'raw_calculated_wave_to_reference_ratio_hint'
    assert row['pressure_factor_reference_hint']['application'] == 'explicit_comparison_input_only'
    assert row['pressure_factor_reference_hint']['certification_effect'] == 'none_not_applied'
    assert row['pressure_factor_reference_hint']['boss_wave_pressure_factor'] == pytest.approx(
        calculated_ratio
    )
    assert row['pressure_factor_reference_hint']['rounded_boss_wave_pressure_factor'] == round(
        calculated_ratio,
        3,
    )
    assert row['pressure_factor_reference_hint']['direction'] == 'increase_pressure'
    assert row['pressure_factor_reference_hint']['comparison_scenario_runtime_inputs'] == {
        'boss_wave_pressure_factor': pytest.approx(calculated_ratio)
    }
    assert row['ids_reference_alignment'] == {
        'enabled': True,
        'applied': True,
        'mode': 'clean_ids_reference_empirical_alignment',
        'calculated_selected_max_wave': comparison_row['best_calculated_selected_max_wave'],
        'aligned_selected_max_wave': reference_wave,
        'reference_wave': reference_wave,
        'reference_kind': 'ids_dissonant_pb_wave',
        'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'calculated_delta_vs_reference_wave': calculated_delta,
        'calculated_to_reference_ratio': pytest.approx(calculated_ratio),
        'alignment_direction': 'lowered_to_ids_reference',
        'reason': 'clean_row_aligned_to_active_ids_reference',
    }
    comparison_candidate = next(
        candidate
        for candidate in comparison_row['candidate_results']
        if candidate['selected_max_wave'] == comparison_row['best_calculated_selected_max_wave']
    )
    assert candidate['selected_max_wave'] == comparison_candidate['selected_max_wave']
    assert default_matrix['wide_rows'][0]['utility_wave'] == reference_wave
    assert (
        default_matrix['wide_rows'][0]['utility_calculated_wave']
        == comparison_row['best_calculated_selected_max_wave']
    )
    assert default_matrix['wide_rows'][0]['utility_hit_by_hit_wave'] == row['best_hit_by_hit_max_wave']
    assert default_matrix['wide_rows'][0]['utility_contact_envelope_wave'] == row['best_contact_envelope_max_wave']
    assert (
        default_matrix['wide_rows'][0]['utility_pre_contact_boss_kill_wave']
        == row['best_pre_contact_boss_kill_max_wave']
    )
    assert default_matrix['wide_rows'][0]['utility_gc_pre_contact_wave'] == row['best_gc_pre_contact_max_wave']
    assert default_matrix['wide_rows'][0]['utility_reference_nearest_lane'] == nearest_lane
    assert default_matrix['wide_rows'][0]['utility_reference_nearest_lane_label'] == nearest_lane_label
    assert (
        default_matrix['wide_rows'][0]['utility_reference_nearest_lane_wave']
        == nearest_lane_wave
    )
    assert default_matrix['wide_rows'][0]['utility_reference_nearest_lane_delta_vs_reference_wave'] == lane_delta
    assert default_matrix['wide_rows'][0]['utility_reference_nearest_lane_abs_delta_wave'] == abs(lane_delta)
    assert (
        default_matrix['wide_rows'][0]['utility_calculated_delta_vs_reference_wave']
        == calculated_delta
    )
    assert default_matrix['wide_rows'][0]['utility_calculated_to_reference_ratio'] == pytest.approx(
        calculated_ratio
    )
    assert default_matrix['wide_rows'][0]['utility_pressure_factor_hint'] == pytest.approx(
        calculated_ratio
    )
    assert default_matrix['wide_rows'][0]['utility_pressure_factor_hint_direction'] == 'increase_pressure'
    assert default_matrix['wide_rows'][0]['utility_primitive_family_coverage_status'] == 'covered'
    assert row['replacement_primitive_family_coverage']['status'] == 'covered'
    assert row['replacement_primitive_family_coverage']['missing_requested_families'] == []
    family_summary = default_matrix['replacement_primitive_family_coverage_summary']
    assert family_summary['status'] == 'covered'
    assert family_summary['selected_row_count'] == 1
    assert family_summary['rows_with_coverage'] == 1
    assert family_summary['missing_requested_families'] == []
    assert family_summary['family_status_counts']['card_mastery'] == {'covered_by_qe_surface': 1}
    assert family_summary['family_status_counts']['workshop'] == {'covered_by_qe_contributor': 1}
    assert default_matrix['wide_rows'][0]['utility_reference_calibration_candidate'] is True
    assert (
        default_matrix['wide_rows'][0]['utility_reference_quality_caveats']
        == 'pb_age_unknown_no_source_timestamp'
    )
    summary = default_matrix['reference_alignment_summary']
    assert summary['row_count'] == 1
    assert summary['rows_with_calculated_delta'] == 1
    assert summary['ids_reference_alignment_applied_count'] == 1
    assert summary['raw_delta_over_reference_count'] == 1
    assert summary['raw_delta_under_reference_count'] == 0
    assert summary['reference_nearest_lane_counts'] == {nearest_lane: 1}
    assert summary['max_abs_calculated_delta_row']['label'] == 'Utility Dissonant Run'
    assert summary['max_abs_calculated_delta_row']['calculated_delta_vs_reference_wave'] == (
        calculated_delta
    )
    assert summary['max_abs_calculated_delta_row']['reference_nearest_lane'] == nearest_lane
    assert summary['max_abs_calculated_delta_row']['reference_nearest_lane_wave'] == nearest_lane_wave
    assert summary['by_run_type'] == [
        {
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'row_count': 1,
            'rows_with_reference': 1,
            'rows_with_calculated_delta': 1,
            'ids_reference_alignment_applied_count': 1,
            'raw_delta_over_reference_count': 1,
            'raw_delta_under_reference_count': 0,
            'raw_delta_match_count': 0,
            'max_abs_calculated_delta_wave': abs(calculated_delta),
            'reference_nearest_lane_counts': {nearest_lane: 1},
        }
    ]
    calibration_alignment = summary['calibration_reference_alignment']
    assert calibration_alignment['definition'] == 'calibration_candidate_with_no_reference_caveats'
    assert calibration_alignment['row_count'] == 0
    assert calibration_alignment['rows_with_reference'] == 0
    assert calibration_alignment['rows_with_calculated_delta'] == 0
    assert calibration_alignment['raw_delta_over_reference_count'] == 0
    assert calibration_alignment['raw_delta_under_reference_count'] == 0
    assert calibration_alignment['raw_delta_match_count'] == 0
    assert calibration_alignment['max_abs_calculated_delta_wave'] == 0
    assert calibration_alignment['max_abs_calculated_delta_row'] is None
    assert calibration_alignment['excluded_from_calibration_reference_count'] == 1
    assert calibration_alignment['excluded_caveated_reference_count'] == 1
    assert calibration_alignment['excluded_non_candidate_reference_count'] == 0
    assert calibration_alignment['excluded_by_run_type'] == [
        {
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'excluded_from_calibration_reference_count': 1,
            'excluded_caveated_reference_count': 1,
            'excluded_non_candidate_reference_count': 0,
        }
    ]
    quality_summary = default_matrix['reference_quality_summary']
    assert quality_summary == {
        'row_count': 1,
        'rows_with_reference': 1,
        'calibration_candidate_count': 1,
        'low_wave_threshold': 3000,
        'low_wave_reference_count': 0,
        'pb_age_unknown_count': 1,
        'dissonance_pb_bonus_cap_count': 0,
        'rows_with_caveats': 1,
        'by_run_type': [
            {
                'dissonance_run_category': 'utility',
                'label': 'Utility Dissonant Run',
                'row_count': 1,
                'rows_with_reference': 1,
                'calibration_candidate_count': 1,
                'low_wave_reference_count': 0,
                'pb_age_unknown_count': 1,
                'dissonance_pb_bonus_cap_count': 0,
                'rows_with_caveats': 1,
            }
        ],
    }
    pressure_summary = default_matrix['pressure_factor_hint_summary']
    assert pressure_summary['row_count'] == 1
    assert pressure_summary['rows_with_pressure_factor_hint'] == 1
    assert pressure_summary['direction_counts'] == {'increase_pressure': 1}
    assert pressure_summary['max_factor_distance_row']['tier'] == 14
    assert pressure_summary['max_factor_distance_row']['tier_column'] == 'Tier 14'
    assert pressure_summary['max_factor_distance_row']['dissonance_run_category'] == 'utility'
    assert pressure_summary['max_factor_distance_row']['label'] == 'Utility Dissonant Run'
    assert pressure_summary['max_factor_distance_row']['selected_max_wave'] == reference_wave
    assert pressure_summary['max_factor_distance_row']['calculated_selected_max_wave'] == (
        comparison_row['best_calculated_selected_max_wave']
    )
    assert pressure_summary['max_factor_distance_row']['reference_wave'] == reference_wave
    assert pressure_summary['calibration_quality'] == {
        'definition': 'calibration_candidate_with_no_reference_caveats',
        'rows_with_pressure_factor_hint': 0,
        'excluded_caveated_hint_count': 1,
        'excluded_caveated_hint_reason_counts': {
            'pb_age_unknown_no_source_timestamp': 1,
        },
        'direction_counts': {},
        'factor_distribution': {
            'count': 0,
            'min_factor': None,
            'median_factor': None,
            'mean_factor': None,
            'max_factor': None,
            'rounded_median_factor': None,
            'rounded_mean_factor': None,
            'comparison_scenario_runtime_inputs': {},
        },
        'max_factor_distance_from_one': 0.0,
        'max_factor_distance_row': {},
    }
    utility_factor = calculated_ratio
    empty_factor_distribution = {
        'count': 0,
        'min_factor': None,
        'median_factor': None,
        'mean_factor': None,
        'max_factor': None,
        'rounded_median_factor': None,
        'rounded_mean_factor': None,
        'comparison_scenario_runtime_inputs': {},
    }
    assert pressure_summary['by_run_type'] == [
        {
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'row_count': 1,
            'rows_with_pressure_factor_hint': 1,
            'direction_counts': {'increase_pressure': 1},
            'max_factor_distance_from_one': pytest.approx(
                abs(utility_factor - 1.0)
            ),
            'max_factor_distance_row': pressure_summary['max_factor_distance_row'],
            'calibration_quality_hint_count': 0,
            'calibration_quality_direction_counts': {},
            'calibration_quality_max_factor_distance_from_one': 0.0,
            'calibration_quality_max_factor_distance_row': {},
            'excluded_caveated_hint_count': 1,
            'excluded_caveated_hint_reason_counts': {
                'pb_age_unknown_no_source_timestamp': 1,
            },
            'disabled_hint_mode_counts': {},
            'pressure_factor_evidence_quality': 'caveated_reference_hints_only',
            'pressure_factor_distribution': {
                'count': 1,
                'min_factor': pytest.approx(utility_factor),
                'median_factor': pytest.approx(utility_factor),
                'mean_factor': pytest.approx(utility_factor),
                'max_factor': pytest.approx(utility_factor),
                'rounded_median_factor': round(utility_factor, 3),
                'rounded_mean_factor': round(utility_factor, 3),
                'comparison_scenario_runtime_inputs': {
                    'boss_wave_pressure_factor': pytest.approx(utility_factor),
                },
                'explicit_comparison_input_available': True,
                'application': 'explicit_comparison_input_only',
                'certification_effect': 'none_not_applied',
                'mode': 'median_calibration_quality_pressure_factor_hint',
            },
            'explicit_comparison_input_hint': {
                'boss_wave_pressure_factor': pytest.approx(utility_factor),
            },
            'calibration_quality_factor_distribution': empty_factor_distribution,
        }
    ]


def test_boss_wave_pressure_factor_hint_summary_publishes_calibration_distribution() -> None:
    from app.pipeline import _boss_wave_pressure_factor_hint_summary

    rows = [
        {
            'tier': 1,
            'tier_column': 'Tier 1',
            'dissonance_run_category': 'none',
            'label': 'Regular',
            'best_selected_max_wave': 100,
            'best_display': '100',
            'best_calculated_selected_max_wave': 100,
            'best_loadout_policy_preset': 'eHP Max Waves',
            'pressure_factor_reference_hint': {
                'enabled': True,
                'boss_wave_pressure_factor': 1.0,
                'direction': 'no_adjustment',
            },
            'reference_quality': {'calibration_candidate': True, 'caveats': []},
        },
        {
            'tier': 2,
            'tier_column': 'Tier 2',
            'dissonance_run_category': 'none',
            'label': 'Regular',
            'best_selected_max_wave': 100,
            'best_display': '100',
            'best_calculated_selected_max_wave': 200,
            'best_loadout_policy_preset': 'eHP Max Waves',
            'pressure_factor_reference_hint': {
                'enabled': True,
                'boss_wave_pressure_factor': 2.0,
                'direction': 'increase_pressure',
            },
            'reference_quality': {'calibration_candidate': True, 'caveats': []},
        },
        {
            'tier': 3,
            'tier_column': 'Tier 3',
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'best_selected_max_wave': 100,
            'best_display': '100',
            'best_calculated_selected_max_wave': 400,
            'best_loadout_policy_preset': 'GC Max Waves',
            'pressure_factor_reference_hint': {
                'enabled': True,
                'boss_wave_pressure_factor': 4.0,
                'direction': 'increase_pressure',
            },
            'reference_quality': {
                'calibration_candidate': True,
                'caveats': ['pb_age_unknown_no_source_timestamp'],
            },
        },
        {
            'tier': 4,
            'tier_column': 'Tier 4',
            'dissonance_run_category': 'attack',
            'label': 'Attack Dissonant Run',
            'best_selected_max_wave': 5000,
            'best_display': '5000',
            'best_calculated_selected_max_wave': 12000,
            'best_loadout_policy_preset': 'eHP Max Waves',
            'pressure_factor_reference_hint': {
                'enabled': False,
                'mode': 'dissonance_pb_bonus_cap_not_exact_reference',
                'boss_wave_pressure_factor': None,
                'direction': None,
            },
            'reference_quality': {
                'calibration_candidate': False,
                'caveats': [
                    'pb_age_unknown_no_source_timestamp',
                    'dissonance_pb_5000_bonus_cap_floor',
                ],
            },
        },
    ]

    summary = _boss_wave_pressure_factor_hint_summary(rows)
    distribution = summary['calibration_quality']['factor_distribution']

    assert summary['rows_with_pressure_factor_hint'] == 3
    assert summary['disabled_hint_mode_counts'] == {
        'dissonance_pb_bonus_cap_not_exact_reference': 1,
    }
    assert summary['calibration_quality']['rows_with_pressure_factor_hint'] == 2
    assert summary['calibration_quality']['excluded_caveated_hint_count'] == 1
    assert summary['calibration_quality']['excluded_caveated_hint_reason_counts'] == {
        'pb_age_unknown_no_source_timestamp': 1,
    }
    assert distribution['count'] == 2
    assert distribution['min_factor'] == pytest.approx(1.0)
    assert distribution['median_factor'] == pytest.approx(1.5)
    assert distribution['mean_factor'] == pytest.approx(1.5)
    assert distribution['max_factor'] == pytest.approx(2.0)
    assert distribution['comparison_scenario_runtime_inputs'] == {
        'boss_wave_pressure_factor': pytest.approx(1.5)
    }
    assert distribution['explicit_comparison_input_available'] is True
    assert distribution['application'] == 'explicit_comparison_input_only'
    assert distribution['certification_effect'] == 'none_not_applied'
    by_run_type = {
        row['dissonance_run_category']: row
        for row in summary['by_run_type']
    }
    assert by_run_type['none']['pressure_factor_evidence_quality'] == 'clean_calibration_available'
    assert by_run_type['none']['pressure_factor_distribution']['count'] == 2
    assert by_run_type['none']['pressure_factor_distribution']['median_factor'] == pytest.approx(1.5)
    assert by_run_type['none']['explicit_comparison_input_hint'] == {
        'boss_wave_pressure_factor': pytest.approx(1.5),
    }
    assert by_run_type['none']['calibration_quality_factor_distribution']['median_factor'] == pytest.approx(1.5)
    assert by_run_type['utility']['pressure_factor_evidence_quality'] == 'caveated_reference_hints_only'
    assert by_run_type['utility']['pressure_factor_distribution']['median_factor'] == pytest.approx(4.0)
    assert by_run_type['utility']['explicit_comparison_input_hint'] == {
        'boss_wave_pressure_factor': pytest.approx(4.0),
    }
    assert by_run_type['utility']['calibration_quality_factor_distribution']['count'] == 0
    assert by_run_type['attack']['pressure_factor_evidence_quality'] == 'disabled_by_reference_quality'
    assert by_run_type['attack']['disabled_hint_mode_counts'] == {
        'dissonance_pb_bonus_cap_not_exact_reference': 1,
    }


def test_boss_wave_matrix_model_accuracy_summary_publishes_default_and_approximation_posture() -> None:
    from app.pipeline import _boss_wave_matrix_model_accuracy_summary

    common = {
        'model_blocker_summary': {
            'rows_with_model_completion_blockers': 35,
        },
        'reference_quality_summary': {
            'rows_with_reference': 76,
            'calibration_candidate_count': 23,
            'low_wave_reference_count': 11,
            'pb_age_unknown_count': 56,
            'dissonance_pb_bonus_cap_count': 42,
            'rows_with_caveats': 60,
        },
        'pressure_factor_hint_summary': {
            'by_run_type': [
                {
                    'dissonance_run_category': 'none',
                    'label': 'Regular',
                    'row_count': 21,
                    'rows_with_pressure_factor_hint': 16,
                    'calibration_quality_hint_count': 16,
                    'pressure_factor_evidence_quality': 'clean_calibration_available',
                    'pressure_factor_distribution': {
                        'count': 16,
                        'min_factor': 1.0,
                        'median_factor': 2.606384292771721,
                        'max_factor': 5.101279317697228,
                        'rounded_median_factor': 2.606,
                    },
                    'explicit_comparison_input_hint': {
                        'boss_wave_pressure_factor': 2.606384292771721,
                    },
                    'calibration_quality_factor_distribution': {
                        'count': 16,
                        'median_factor': 2.606384292771721,
                        'rounded_median_factor': 2.606,
                    },
                    'excluded_caveated_hint_count': 0,
                    'excluded_caveated_hint_reason_counts': {},
                    'disabled_hint_mode_counts': {},
                },
                {
                    'dissonance_run_category': 'utility',
                    'label': 'Utility Dissonant Run',
                    'row_count': 21,
                    'rows_with_pressure_factor_hint': 3,
                    'calibration_quality_hint_count': 0,
                    'pressure_factor_evidence_quality': 'caveated_reference_hints_only',
                    'pressure_factor_distribution': {
                        'count': 3,
                        'min_factor': 1.0,
                        'median_factor': 1.2266500622665006,
                        'max_factor': 1.2266500622665006,
                        'rounded_median_factor': 1.227,
                    },
                    'explicit_comparison_input_hint': {
                        'boss_wave_pressure_factor': 1.2266500622665006,
                    },
                    'calibration_quality_factor_distribution': {
                        'count': 0,
                        'median_factor': None,
                        'rounded_median_factor': None,
                    },
                    'excluded_caveated_hint_count': 3,
                    'excluded_caveated_hint_reason_counts': {
                        'pb_age_unknown_no_source_timestamp': 3,
                    },
                    'disabled_hint_mode_counts': {
                        'dissonance_pb_bonus_cap_not_exact_reference': 12,
                    },
                },
            ],
            'calibration_quality': {
                'factor_distribution': {
                    'count': 16,
                    'median_factor': 2.606384292771721,
                        'comparison_scenario_runtime_inputs': {
                            'boss_wave_pressure_factor': 2.606384292771721,
                        },
                        'explicit_comparison_input_available': True,
                    },
                },
            },
        'reference_gap_summary': {
            'missing_reference_blocked_count': 19,
        },
    }
    default = _boss_wave_matrix_model_accuracy_summary(
        certification={
            'model_certification_status': 'partial_boss_contact_model',
            'model_closure_status': 'partial_missing_required_model_inputs',
            'certified_full_max_wave_model': False,
            'model_completion_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
            'accepted_approximation_closure': {'closed': False, 'mode': 'none'},
        },
        **common,
    )
    approximated = _boss_wave_matrix_model_accuracy_summary(
        certification={
            'model_certification_status': 'partial_boss_contact_model',
            'model_closure_status': 'closed_with_pressure_factor_approximation',
            'certified_full_max_wave_model': False,
            'model_completion_blockers': [],
            'accepted_approximation_closure': {
                'closed': True,
                'mode': 'boss_wave_pressure_factor_approximation',
                'boss_wave_pressure_factor': 1.25,
            },
        },
        **common,
    )

    assert default['status'] == 'default_partial_comparison_calibration_available'
    assert default['operator_next_step'] == 'apply_comparison_only_pressure_factor_input_to_review_approximation'
    assert default['comparison_only_pressure_factor_inputs'] == {
        'boss_wave_pressure_factor': pytest.approx(2.606384292771721),
    }
    assert default['reference_caveat_counts'] == {
        'below_3000_wave_perk_volatility': 11,
        'pb_age_unknown_no_source_timestamp': 56,
        'dissonance_pb_5000_bonus_cap_floor': 42,
    }
    assert default['missing_reference_blocked_count'] == 19
    assert default['certified_full_max_wave_model'] is False
    assert default['pressure_factor_by_run_type'][0]['pressure_factor_evidence_quality'] == (
        'clean_calibration_available'
    )
    assert default['pressure_factor_by_run_type'][1]['pressure_factor_evidence_quality'] == (
        'caveated_reference_hints_only'
    )
    assert default['pressure_factor_by_run_type'][1]['pressure_factor_rounded_median'] == pytest.approx(1.227)
    assert default['pressure_factor_by_run_type'][1]['calibration_quality_pressure_factor_median'] is None
    assert default['dissonance_pressure_factor_evidence'] == {
        'status': 'caveated_dissonance_hints_only',
        'run_type_count': 1,
        'rows_with_pressure_factor_hint': 3,
        'calibration_quality_hint_count': 0,
        'excluded_caveated_hint_count': 3,
        'excluded_caveated_hint_reason_counts': {
            'pb_age_unknown_no_source_timestamp': 3,
        },
        'disabled_hint_mode_counts': {
            'dissonance_pb_bonus_cap_not_exact_reference': 12,
        },
        'categories_with_pressure_factor_hints': ['Utility Dissonant Run'],
        'categories_with_explicit_review_inputs': ['Utility Dissonant Run'],
        'categories_with_clean_calibration': [],
        'categories_without_clean_calibration': ['Utility Dissonant Run'],
        'explicit_review_inputs_by_run_type': [
                {
                    'dissonance_run_category': 'utility',
                    'label': 'Utility Dissonant Run',
                    'boss_wave_pressure_factor': 1.2266500622665006,
                    'rounded_boss_wave_pressure_factor': 1.227,
                'evidence_quality': 'caveated_reference_hints_only',
                'calibration_quality_hint_count': 0,
                'excluded_caveated_hint_count': 3,
                'excluded_caveated_hint_reason_counts': {
                    'pb_age_unknown_no_source_timestamp': 3,
                    },
                'explicit_comparison_input_hint': {
                    'boss_wave_pressure_factor': 1.2266500622665006,
                },
                'comparison_review_request': {
                    'mode': 'comparison_only',
                    'dissonance_run_category': 'utility',
                    'include_boss_wave_milestone_matrix': True,
                    'comparison_scenario_runtime_inputs': {
                        'boss_wave_pressure_factor': 1.2266500622665006,
                    },
                    'default_account_truth_unchanged': True,
                    'certification_effect': 'none_not_applied',
                },
                'application': 'manual_or_comparison_only',
                'certification_effect': 'none_not_applied',
            }
        ],
        'explicit_review_request_count': 1,
        'application': 'explicit_manual_or_comparison_input_only',
        'certification_effect': 'none_not_applied',
    }

    assert approximated['status'] == 'explicit_pressure_factor_approximation_active'
    assert approximated['operator_next_step'] == 'review_approximation_against_reference_quality_caveats'
    assert approximated['accepted_approximation_closure']['boss_wave_pressure_factor'] == pytest.approx(1.25)
    assert approximated['certified_full_max_wave_model'] is False


def test_boss_wave_reference_alignment_summary_publishes_calibration_subset() -> None:
    from app.pipeline import _boss_wave_reference_alignment_summary

    rows = [
        {
            'tier': 1,
            'tier_column': 'Tier 1',
            'dissonance_run_category': 'none',
            'label': 'Regular',
            'reference_wave': 4000,
            'best_selected_max_wave': 4000,
            'best_calculated_selected_max_wave': 4025,
            'calculated_delta_vs_reference_wave': 25,
            'calculated_to_reference_ratio': 1.00625,
            'reference_nearest_lane': 'contact_envelope',
            'reference_nearest_lane_label': 'Contact envelope',
            'reference_nearest_lane_wave': 4025,
            'reference_nearest_lane_delta_vs_reference_wave': 25,
            'ids_reference_alignment': {
                'applied': True,
                'alignment_direction': 'raise_to_reference',
            },
            'reference_quality': {'calibration_candidate': True, 'caveats': []},
        },
        {
            'tier': 2,
            'tier_column': 'Tier 2',
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'reference_wave': 4402,
            'best_selected_max_wave': 4402,
            'best_calculated_selected_max_wave': 4502,
            'calculated_delta_vs_reference_wave': 100,
            'calculated_to_reference_ratio': 1.0227,
            'reference_nearest_lane': 'hit_by_hit',
            'reference_nearest_lane_label': 'Hit by hit',
            'reference_nearest_lane_wave': 4502,
            'reference_nearest_lane_delta_vs_reference_wave': 100,
            'reference_quality': {
                'calibration_candidate': True,
                'caveats': ['pb_age_unknown_no_source_timestamp'],
            },
        },
        {
            'tier': 3,
            'tier_column': 'Tier 3',
            'dissonance_run_category': 'attack',
            'label': 'Attack Dissonant Run',
            'reference_wave': 5000,
            'best_selected_max_wave': 5000,
            'best_calculated_selected_max_wave': 6000,
            'calculated_delta_vs_reference_wave': 1000,
            'calculated_to_reference_ratio': 1.2,
            'reference_nearest_lane': 'contact_envelope',
            'reference_nearest_lane_label': 'Contact envelope',
            'reference_nearest_lane_wave': 6000,
            'reference_nearest_lane_delta_vs_reference_wave': 1000,
            'reference_quality': {
                'calibration_candidate': False,
                'caveats': ['dissonance_pb_5000_bonus_cap_floor'],
            },
        },
        {
            'tier': 4,
            'tier_column': 'Tier 4',
            'dissonance_run_category': 'defense',
            'label': 'Defense Dissonant Run',
            'reference_wave': None,
            'calculated_delta_vs_reference_wave': None,
            'reference_quality': {'calibration_candidate': False, 'caveats': []},
        },
    ]

    summary = _boss_wave_reference_alignment_summary(rows)
    calibration = summary['calibration_reference_alignment']

    assert summary['row_count'] == 4
    assert summary['rows_with_reference'] == 3
    assert summary['rows_with_calculated_delta'] == 3
    assert summary['raw_delta_over_reference_count'] == 3
    assert summary['max_abs_calculated_delta_row']['label'] == 'Attack Dissonant Run'
    assert calibration['definition'] == 'calibration_candidate_with_no_reference_caveats'
    assert calibration['row_count'] == 1
    assert calibration['rows_with_reference'] == 1
    assert calibration['rows_with_calculated_delta'] == 1
    assert calibration['raw_delta_over_reference_count'] == 1
    assert calibration['raw_delta_under_reference_count'] == 0
    assert calibration['raw_delta_match_count'] == 0
    assert calibration['max_abs_calculated_delta_wave'] == 25
    assert calibration['max_abs_calculated_delta_row']['label'] == 'Regular'
    assert calibration['excluded_from_calibration_reference_count'] == 2
    assert calibration['excluded_caveated_reference_count'] == 2
    assert calibration['excluded_non_candidate_reference_count'] == 1
    assert calibration['excluded_by_run_type'] == [
        {
            'dissonance_run_category': 'attack',
            'label': 'Attack Dissonant Run',
            'excluded_from_calibration_reference_count': 1,
            'excluded_caveated_reference_count': 1,
            'excluded_non_candidate_reference_count': 1,
        },
        {
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'excluded_from_calibration_reference_count': 1,
            'excluded_caveated_reference_count': 1,
            'excluded_non_candidate_reference_count': 0,
        },
    ]


def test_boss_wave_reference_quality_flags_low_wave_and_pb_age() -> None:
    from app.pipeline import _boss_wave_reference_quality

    quality = _boss_wave_reference_quality(
        reference_wave=829,
        reference_kind='ids_dissonant_pb_wave',
        reference_source='IDS::Player & Stuff.dissonance_pbs_by_tier',
    )

    assert quality == {
        'reference_wave': 829,
        'reference_kind': 'ids_dissonant_pb_wave',
        'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'low_wave_threshold': 3000,
        'below_low_wave_threshold': True,
        'pb_age_status': 'age_unknown_no_source_timestamp',
        'dissonance_pb_bonus_cap_wave': 5000,
        'dissonance_pb_bonus_cap_reached': False,
        'reference_interpretation': 'exact_wave_reference',
        'exact_reference': True,
        'calibration_candidate': False,
        'caveats': [
            'below_3000_wave_perk_volatility',
            'pb_age_unknown_no_source_timestamp',
        ],
    }


def test_boss_wave_reference_quality_marks_capped_dissonance_pb_as_non_exact() -> None:
    from app.pipeline import _boss_wave_pressure_factor_reference_hint, _boss_wave_reference_quality

    quality = _boss_wave_reference_quality(
        reference_wave=5000,
        reference_kind='ids_dissonant_pb_wave',
        reference_source='IDS::Player & Stuff.dissonance_pbs_by_tier',
    )
    hint = _boss_wave_pressure_factor_reference_hint(
        calculated_wave=6200,
        reference_wave=5000,
        reference_kind='ids_dissonant_pb_wave',
        reference_source='IDS::Player & Stuff.dissonance_pbs_by_tier',
        calculated_delta_vs_reference_wave=1200,
        calculated_to_reference_ratio=1.24,
    )

    assert quality == {
        'reference_wave': 5000,
        'reference_kind': 'ids_dissonant_pb_wave',
        'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'low_wave_threshold': 3000,
        'below_low_wave_threshold': False,
        'pb_age_status': 'age_unknown_no_source_timestamp',
        'dissonance_pb_bonus_cap_wave': 5000,
        'dissonance_pb_bonus_cap_reached': True,
        'reference_interpretation': 'lower_bound_at_dissonance_bonus_cap',
        'exact_reference': False,
        'calibration_candidate': False,
        'caveats': [
            'pb_age_unknown_no_source_timestamp',
            'dissonance_pb_5000_bonus_cap_floor',
        ],
    }
    assert hint == {
        'enabled': False,
        'mode': 'dissonance_pb_bonus_cap_not_exact_reference',
        'boss_wave_pressure_factor': None,
        'direction': None,
        'calculated_selected_max_wave': 6200,
        'reference_wave': 5000,
        'reference_kind': 'ids_dissonant_pb_wave',
        'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
        'reference_interpretation': 'lower_bound_at_dissonance_bonus_cap',
        'exact_reference': False,
        'dissonance_pb_bonus_cap_wave': 5000,
        'caveats': ['dissonance_pb_5000_bonus_cap_floor'],
    }


def test_boss_wave_reference_gap_summary_splits_cap_omitted_dissonance_pb_zeros() -> None:
    from app.pipeline import (
        _annotate_boss_wave_dissonance_pb_cap_omissions,
        _boss_wave_matrix_reference_gap_summary,
    )

    rows = [
        {
            'tier': 16,
            'tier_column': 'Tier 16',
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'reference_kind': 'ids_dissonant_pb_wave',
            'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
            'reference_wave': None,
            'reference_raw_wave': 0,
            'reference_gap_reason': 'zero_reference_wave',
            'terminal_pressure_reference_status': 'missing_empirical_reference_blocked',
            'best_calculated_selected_max_wave': 0,
            'unsupported_pressure_uncapped_selected_max_wave': 1827,
            'unsupported_terminal_pressures': ['protector_ultimate_deferred'],
            'terminal_pressure_runtime_override_status': {
                'required_fields': ['protector_terminal_max_wave'],
                'missing_fields': ['protector_terminal_max_wave'],
            },
        },
        {
            'tier': 21,
            'tier_column': 'Tier 21',
            'dissonance_run_category': 'none',
            'label': 'Regular',
            'reference_kind': 'ids_milestone_wave',
            'reference_source': 'IDS::Player & Stuff.tier_progression_waves',
            'reference_wave': None,
            'reference_raw_wave': 0,
            'reference_gap_reason': 'zero_reference_wave',
            'terminal_pressure_reference_status': 'missing_empirical_reference_blocked',
            'best_calculated_selected_max_wave': 0,
            'unsupported_pressure_uncapped_selected_max_wave': 5,
            'unsupported_terminal_pressures': ['boss_ultimate_deferred'],
            'terminal_pressure_runtime_override_status': {
                'required_fields': ['boss_terminal_max_wave'],
                'missing_fields': ['boss_terminal_max_wave'],
            },
        },
    ]

    _annotate_boss_wave_dissonance_pb_cap_omissions(
        rows,
        account_state=SimpleNamespace(dissonance_pbs_by_tier={'Tier 12': {'utility': 5000}}),
    )
    summary = _boss_wave_matrix_reference_gap_summary(rows)

    assert rows[0]['dissonance_pb_cap_omitted_reference'] is True
    assert rows[0]['dissonance_pb_cap_omission_context'] == {
        'applies': True,
        'mode': 'zero_ids_dissonant_pb_after_bonus_cap_reached',
        'reference_interpretation': 'intentionally_unfilled_after_dissonance_bonus_cap_reached',
        'dissonance_pb_bonus_cap_wave': 5000,
        'cap_reached_tiers': [12],
        'nearest_cap_tier': 12,
        'evidence_source': 'account_state.dissonance_pbs_by_tier',
    }
    assert rows[1]['dissonance_pb_cap_omitted_reference'] is False
    assert summary['missing_reference_blocked_count'] == 2
    assert summary['dissonance_pb_cap_omitted_reference_count'] == 1
    assert summary['ordinary_missing_reference_blocked_count'] == 1
    assert summary['by_run_type'] == [
        {
            'dissonance_run_category': 'none',
            'label': 'Regular',
            'missing_reference_blocked_count': 1,
            'dissonance_pb_cap_omitted_reference_count': 0,
            'ordinary_missing_reference_blocked_count': 1,
            'tiers': [21],
        },
        {
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'missing_reference_blocked_count': 1,
            'dissonance_pb_cap_omitted_reference_count': 1,
            'ordinary_missing_reference_blocked_count': 0,
            'tiers': [16],
        },
    ]
    assert summary['missing_references'][0]['dissonance_pb_cap_omitted_reference'] is True
    assert summary['missing_references'][1]['dissonance_pb_cap_omitted_reference'] is False


@pytest.mark.live
def test_boss_wave_direct_dissonance_matrix_carries_terminal_pressure_cap_metadata(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_dissonance_pb_reference(
        monkeypatch,
        pipeline_mod,
        tier_label='Tier 16',
        category='utility',
        wave=0,
    )

    payload = pipeline_mod.build_boss_wave_payload(
            PipelineRunRequest(
                ids=IDS_PATH,
                out=ROOT / 'out',
                perk_mode='max_progression_policy',
                perk_policy_preset='eHP Max Waves',
                runtime_state_overlay='disco_respec_2026_06_10',
            ),
        preset_name='Milestone',
        tier_number=16,
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        include_dissonance_run_matrix=True,
    )

    uw_row = next(row for row in payload['dissonance_run_matrix'] if row['dissonance_run_category'] == 'ultimate_weapons')
    assert uw_row['selected_max_wave'] == 780
    assert uw_row['terminal_pressure_limiter'] == 'unsupported_pressure_empirical_reference'
    assert uw_row['terminal_pressure_limited'] is True
    assert uw_row['unsupported_pressure_reference_limited'] is True
    assert uw_row['unsupported_pressure_uncapped_selected_max_wave'] > uw_row['selected_max_wave']
    assert uw_row['unsupported_pressure_reference_limit']['reference_wave'] == 780
    assert {
        'armored_enemies_blocked_hits',
        'knockback_resistance_non_boss_pressure',
        'protector_ultimate_deferred',
    } <= set(uw_row['unsupported_terminal_pressures'])
    assert 'source_owned_non_boss_terminal_pressure_formulas' in uw_row['model_completion_blockers']

    utility_row = next(row for row in payload['dissonance_run_matrix'] if row['dissonance_run_category'] == 'utility')
    assert utility_row['selected_max_wave'] == 0
    assert utility_row['status'] == 'incomplete'
    assert utility_row['terminal_pressure_limiter'] == 'unsupported_pressure_missing_empirical_reference'
    assert utility_row['terminal_pressure_limited'] is True
    assert utility_row['unsupported_pressure_missing_reference_blocked'] is True
    assert utility_row['unsupported_pressure_reference_limit']['missing_reference'] is True
    assert utility_row['unsupported_pressure_uncapped_selected_max_wave'] > 0


@pytest.mark.live
def test_boss_wave_milestone_matrix_blocks_unsupported_pressure_without_reference(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_dissonance_pb_reference(
        monkeypatch,
        pipeline_mod,
        tier_label='Tier 16',
        category='utility',
        wave=0,
    )

    matrix = pipeline_mod.build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=2000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('utility',),
    )

    row = matrix['rows'][0]
    candidate = row['candidate_results'][0]
    expected_terminal_status = {
        'closed': False,
        'mode': 'active_unsupported_pressure_inputs',
        'required_fields': [
            'armored_terminal_max_wave',
            'fleet_terminal_max_wave',
            'protector_terminal_max_wave',
        ],
        'missing_fields': [
            'armored_terminal_max_wave',
            'fleet_terminal_max_wave',
            'protector_terminal_max_wave',
        ],
        'required_fields_by_pressure': {
            'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
            'knockback_resistance_non_boss_pressure': ['fleet_terminal_max_wave'],
            'protector_ultimate_deferred': ['protector_terminal_max_wave'],
        },
        'missing_fields_by_pressure': {
            'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
            'knockback_resistance_non_boss_pressure': ['fleet_terminal_max_wave'],
            'protector_ultimate_deferred': ['protector_terminal_max_wave'],
        },
        'unmapped_pressures': [],
    }
    assert row['reference_kind'] == 'ids_dissonant_pb_wave'
    assert row['reference_wave'] is None
    assert row['reference_raw_wave'] == 0
    assert row['reference_gap_reason'] == 'zero_reference_wave'
    assert row['best_status'] == 'incomplete'
    assert row['best_selected_max_wave'] == 0
    assert row['terminal_pressure_limiter'] == 'unsupported_pressure_missing_empirical_reference'
    assert row['terminal_pressure_limited'] is True
    assert row['unsupported_pressure_reference_limited'] is False
    assert row['unsupported_pressure_missing_reference_blocked'] is True
    assert row['unsupported_pressure_uncapped_selected_max_wave'] > 0
    assert row['unsupported_pressure_reference_limit']['missing_reference'] is True
    assert row['unsupported_pressure_reference_limit']['blocked'] is True
    assert row['unsupported_pressure_reference_limit']['reference_raw_wave'] == 0
    assert row['unsupported_pressure_reference_limit']['reference_gap_reason'] == 'zero_reference_wave'
    assert row['terminal_pressure_runtime_override_status'] == expected_terminal_status
    assert row['model_certification']['terminal_pressure_runtime_override_status'] == expected_terminal_status
    assert matrix['model_certification']['terminal_pressure_runtime_override_status'] == expected_terminal_status
    assert matrix['model_certification']['non_boss_terminal_pressure_closure'] == {
        'closed': False,
        'mode': 'missing',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': False,
        'boss_wave_pressure_factor': None,
    }
    assert matrix['model_certification']['effective_model_closure'] == {
        'non_boss_terminal_pressure': False,
        'v28_damage_health_decay_magnitudes': True,
        'boss_applicable_damage_semantics': True,
        'gc_boss_applicable_damage_semantics': True,
    }
    assert matrix['model_closure_status'] == 'partial_missing_required_model_inputs'
    assert matrix['model_certification']['model_closure_status'] == 'partial_missing_required_model_inputs'
    assert matrix['accepted_approximation_closure'] == {
        'closed': False,
        'mode': 'none',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': None,
        'replaced_blockers': [],
        'certification_effect': 'none',
        'certified_full_max_wave_model': False,
    }
    assert matrix['model_completion_blockers'] == matrix['model_certification']['model_completion_blockers']
    assert matrix['runtime_override_closure'] == matrix['model_certification']['runtime_override_closure']
    assert matrix['effective_model_closure'] == matrix['model_certification']['effective_model_closure']
    assert matrix['terminal_pressure_runtime_override_status'] == matrix['model_certification'][
        'terminal_pressure_runtime_override_status'
    ]
    assert matrix['non_boss_terminal_pressure_closure'] == matrix['model_certification'][
        'non_boss_terminal_pressure_closure'
    ]
    assert row['model_certification']['effective_model_closure'] == matrix['model_certification'][
        'effective_model_closure'
    ]
    assert matrix['reference_gap_summary'] == {
        'row_count': 1,
        'missing_reference_blocked_count': 1,
        'ordinary_missing_reference_blocked_count': 0,
        'dissonance_pb_cap_omitted_reference_count': 1,
        'by_reference_kind': {'ids_dissonant_pb_wave': 1},
        'by_run_type': [
            {
                'dissonance_run_category': 'utility',
                'label': 'Utility Dissonant Run',
                'missing_reference_blocked_count': 1,
                'dissonance_pb_cap_omitted_reference_count': 1,
                'ordinary_missing_reference_blocked_count': 0,
                'tiers': [16],
            }
        ],
        'missing_references': [
            {
                'tier': 16,
                'tier_column': 'Tier 16',
                'dissonance_run_category': 'utility',
                'label': 'Utility Dissonant Run',
                'reference_kind': 'ids_dissonant_pb_wave',
                'reference_source': 'IDS::Player & Stuff.dissonance_pbs_by_tier',
                'reference_wave': None,
                'reference_raw_wave': 0,
                'reference_gap_reason': 'zero_reference_wave',
                'dissonance_pb_cap_omitted_reference': True,
                'dissonance_pb_cap_omission_context': {
                    'applies': True,
                    'mode': 'zero_ids_dissonant_pb_after_bonus_cap_reached',
                    'reference_interpretation': (
                        'intentionally_unfilled_after_dissonance_bonus_cap_reached'
                    ),
                    'dissonance_pb_bonus_cap_wave': 5000,
                    'cap_reached_tiers': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    'nearest_cap_tier': 12,
                    'evidence_source': 'account_state.dissonance_pbs_by_tier',
                },
                'best_calculated_selected_max_wave': 0,
                'unsupported_pressure_uncapped_selected_max_wave': row[
                    'unsupported_pressure_uncapped_selected_max_wave'
                ],
                'unsupported_terminal_pressures': row['unsupported_terminal_pressures'],
                'terminal_pressure_required_fields': expected_terminal_status['required_fields'],
                'terminal_pressure_missing_fields': expected_terminal_status['missing_fields'],
                'terminal_pressure_required_fields_by_pressure': expected_terminal_status[
                    'required_fields_by_pressure'
                ],
                'terminal_pressure_missing_fields_by_pressure': expected_terminal_status[
                    'missing_fields_by_pressure'
                ],
                'terminal_pressure_unmapped_pressures': [],
            }
        ],
    }
    assert candidate['selected_max_wave'] == 0
    assert candidate['terminal_pressure_runtime_override_status'] == expected_terminal_status
    assert candidate['unsupported_pressure_missing_reference_blocked'] is True
    assert candidate['unsupported_pressure_reference_limit']['uncapped_selected_max_wave'] > 0
    assert 'source_owned_non_boss_terminal_pressure_formulas' in row['model_completion_blockers']


@pytest.mark.live
def test_boss_wave_milestone_matrix_pressure_factor_closes_missing_reference_blocker():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=2000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_total_damage_pct': 6.0,
            'boss_wave_pressure_factor': 1.25,
        },
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('utility',),
    )

    row = matrix['rows'][0]
    candidate = row['candidate_results'][0]
    assert matrix['model_completion_blockers'] == []
    assert matrix['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert matrix['model_certification']['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert matrix['accepted_approximation_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': 1.25,
        'replaced_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
        'certification_effect': 'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation',
        'certified_full_max_wave_model': False,
    }
    assert matrix['model_accuracy_summary']['status'] == 'explicit_pressure_factor_approximation_active'
    assert matrix['model_accuracy_summary']['operator_next_step'] == (
        'review_approximation_against_reference_quality_caveats'
    )
    assert matrix['model_accuracy_summary']['accepted_approximation_closure'] == (
        matrix['accepted_approximation_closure']
    )
    assert matrix['model_accuracy_summary']['certified_full_max_wave_model'] is False
    assert matrix['effective_model_closure']['non_boss_terminal_pressure'] is True
    assert matrix['non_boss_terminal_pressure_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': True,
        'boss_wave_pressure_factor': 1.25,
    }
    assert row['best_status'] == 'complete'
    assert row['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert row['best_model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert row['model_certification']['accepted_approximation_closure'] == matrix['accepted_approximation_closure']
    assert row['best_selected_max_wave'] > 0
    assert row['terminal_pressure_limiter'] is None
    assert row['terminal_pressure_limited'] is False
    assert row['unsupported_pressure_missing_reference_blocked'] is False
    assert row['terminal_pressure_reference_status'] is None
    assert matrix['reference_gap_summary']['missing_reference_blocked_count'] == 0
    assert matrix['reference_gap_summary']['missing_references'] == []
    assert candidate['status'] == 'complete'
    assert candidate['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert candidate['accepted_approximation_closure'] == matrix['accepted_approximation_closure']
    assert candidate['selected_max_wave'] == row['best_calculated_selected_max_wave']
    assert candidate['terminal_pressure_limiter'] is None
    assert candidate['unsupported_pressure_missing_reference_blocked'] is False
    assert candidate['non_boss_terminal_pressure_closure'] == matrix['non_boss_terminal_pressure_closure']


@pytest.mark.live
def test_boss_wave_milestone_matrix_comparison_pressure_factor_publishes_closure_diagnostics(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_dissonance_pb_reference(
        monkeypatch,
        pipeline_mod,
        tier_label='Tier 16',
        category='utility',
        wave=0,
    )

    matrix = pipeline_mod.build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=2000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        comparison_scenario_runtime_inputs={'boss_wave_pressure_factor': 1.25},
        comparison_label='pressure_factor_assumptions',
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('utility',),
    )

    comparison_matrix = matrix['comparison']['matrix']
    diagnostics = pipeline_mod._boss_wave_milestone_matrix_diagnostics_payload(matrix)

    assert matrix['comparison']['runtime_input_overrides'] == {'boss_wave_pressure_factor': 1.25}
    assert matrix['comparison']['base_scenario_runtime_inputs'] == {'orb_boss_total_damage_pct': 6.0}
    assert matrix['comparison']['scenario_runtime_inputs'] == {
        'orb_boss_total_damage_pct': 6.0,
        'boss_wave_pressure_factor': 1.25,
    }
    assert matrix['model_completion_blockers'] == ['source_owned_non_boss_terminal_pressure_formulas']
    assert matrix['model_accuracy_summary']['status'] == 'default_partial_missing_required_model_inputs'
    assert matrix['model_accuracy_summary']['operator_next_step'] == (
        'supply_terminal_max_wave_inputs_or_explicit_pressure_factor'
    )
    assert matrix['reference_gap_summary']['missing_reference_blocked_count'] == 1
    assert matrix['rows'][0]['best_selected_max_wave'] == 0
    assert comparison_matrix['model_completion_blockers'] == []
    assert comparison_matrix['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert comparison_matrix['accepted_approximation_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': 1.25,
        'replaced_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
        'certification_effect': 'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation',
        'certified_full_max_wave_model': False,
    }
    assert comparison_matrix['model_accuracy_summary']['status'] == (
        'explicit_pressure_factor_approximation_active'
    )
    assert comparison_matrix['model_accuracy_summary']['accepted_approximation_closure'] == (
        comparison_matrix['accepted_approximation_closure']
    )
    assert comparison_matrix['effective_model_closure']['non_boss_terminal_pressure'] is True
    assert comparison_matrix['non_boss_terminal_pressure_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': True,
        'boss_wave_pressure_factor': 1.25,
    }
    assert comparison_matrix['reference_gap_summary']['missing_reference_blocked_count'] == 0
    assert comparison_matrix['reference_gap_summary']['missing_references'] == []
    assert comparison_matrix['rows'][0]['best_status'] == 'complete'
    assert comparison_matrix['rows'][0]['best_selected_max_wave'] > 0
    assert diagnostics['comparison_model_completion_blockers'] == []
    assert diagnostics['model_closure_status'] == 'partial_missing_required_model_inputs'
    assert diagnostics['model_accuracy_summary'] == matrix['model_accuracy_summary']
    assert diagnostics['comparison_model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert diagnostics['comparison_accepted_approximation_closure'] == (
        comparison_matrix['accepted_approximation_closure']
    )
    assert diagnostics['comparison_model_accuracy_summary'] == (
        comparison_matrix['model_accuracy_summary']
    )
    assert diagnostics['comparison_runtime_input_overrides'] == {'boss_wave_pressure_factor': 1.25}
    assert diagnostics['comparison_base_scenario_runtime_inputs'] == {'orb_boss_total_damage_pct': 6.0}
    assert diagnostics['comparison_effective_model_closure']['non_boss_terminal_pressure'] is True
    assert diagnostics['comparison_non_boss_terminal_pressure_closure'] == (
        comparison_matrix['non_boss_terminal_pressure_closure']
    )
    assert diagnostics['comparison_model_certification']['non_boss_terminal_pressure_closure'] == (
        comparison_matrix['non_boss_terminal_pressure_closure']
    )
    assert diagnostics['comparison_model_blocker_summary']['rows_with_model_completion_blockers'] == 0
    assert diagnostics['comparison_reference_gap_summary']['missing_reference_blocked_count'] == 0
    assert diagnostics['comparison_reference_gap_summary']['missing_references'] == []


@pytest.mark.live
def test_boss_wave_milestone_matrix_comparison_terminal_overrides_close_disco_gap(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_dissonance_pb_reference(
        monkeypatch,
        pipeline_mod,
        tier_label='Tier 16',
        category='utility',
        wave=0,
    )

    matrix = pipeline_mod.build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=2000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        comparison_scenario_runtime_inputs={
            'fleet_terminal_max_wave': 1700.0,
            'protector_terminal_max_wave': 1700.0,
            'armored_terminal_max_wave': 1700.0,
        },
        comparison_label='terminal_pressure_assumptions',
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('utility',),
    )

    comparison_matrix = matrix['comparison']['matrix']
    comparison_row = comparison_matrix['rows'][0]
    comparison_candidate = comparison_row['candidate_results'][0]
    assert matrix['comparison']['runtime_input_overrides'] == {
        'fleet_terminal_max_wave': 1700.0,
        'protector_terminal_max_wave': 1700.0,
        'armored_terminal_max_wave': 1700.0,
    }
    assert matrix['comparison']['base_scenario_runtime_inputs'] == {'orb_boss_total_damage_pct': 6.0}
    assert matrix['comparison']['scenario_runtime_inputs'] == {
        'orb_boss_total_damage_pct': 6.0,
        'fleet_terminal_max_wave': 1700.0,
        'protector_terminal_max_wave': 1700.0,
        'armored_terminal_max_wave': 1700.0,
    }
    assert matrix['rows'][0]['unsupported_pressure_missing_reference_blocked'] is True
    assert matrix['reference_gap_summary']['missing_reference_blocked_count'] == 1
    assert comparison_matrix['model_completion_blockers'] == []
    assert comparison_matrix['non_boss_terminal_pressure_closure'] == {
        'closed': True,
        'mode': 'explicit_terminal_max_wave_inputs',
        'exact_terminal_override_closed': True,
        'pressure_factor_approximation_closed': False,
        'boss_wave_pressure_factor': None,
    }
    assert comparison_matrix['terminal_pressure_runtime_override_status'] == {
        'closed': True,
        'mode': 'active_unsupported_pressure_inputs',
        'required_fields': [
            'armored_terminal_max_wave',
            'fleet_terminal_max_wave',
            'protector_terminal_max_wave',
        ],
        'missing_fields': [],
        'required_fields_by_pressure': {
            'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
            'knockback_resistance_non_boss_pressure': ['fleet_terminal_max_wave'],
            'protector_ultimate_deferred': ['protector_terminal_max_wave'],
        },
        'missing_fields_by_pressure': {},
        'unmapped_pressures': [],
    }
    assert comparison_matrix['reference_gap_summary']['missing_reference_blocked_count'] == 0
    assert comparison_row['best_status'] == 'complete'
    assert 0 < comparison_row['best_selected_max_wave'] <= 1700
    assert comparison_candidate['non_boss_terminal_pressure_closure'] == (
        comparison_matrix['non_boss_terminal_pressure_closure']
    )
    wide = matrix['comparison']['wide_rows'][0]
    assert wide['utility_default_wave'] == 0
    assert wide['utility_comparison_wave'] == comparison_row['best_selected_max_wave']
    assert wide['utility_comparison_terminal_pressure_limiter'] == comparison_row['terminal_pressure_limiter']


def test_boss_wave_model_certification_only_requires_damage_health_decay_for_tournament_modes():
    from app.pipeline import _boss_wave_model_certification_payload
    from input.state_types import ScenarioRuntimeInputs

    normal = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
        damage_health_decay_required=False,
    )
    normal_ehp = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
        damage_health_decay_required=False,
        gc_boss_applicable_damage_required=False,
    )
    tournament = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
        damage_health_decay_required=True,
    )

    assert normal['model_requirement_applicability']['v28_damage_health_decay_magnitudes'] is False
    assert (
        'source_owned_v28_damage_health_decay_magnitudes'
        not in normal['model_completion_blockers']
    )
    assert tournament['model_requirement_applicability']['v28_damage_health_decay_magnitudes'] is True
    assert (
        'source_owned_v28_damage_health_decay_magnitudes'
        in tournament['model_completion_blockers']
    )
    assert normal['model_requirement_applicability']['boss_applicable_damage_semantics'] is True
    assert normal['model_requirement_applicability']['gc_boss_applicable_damage_semantics'] is True
    assert 'source_owned_full_boss_applicable_damage_semantics' in normal['model_completion_blockers']
    assert normal_ehp['model_requirement_applicability']['boss_applicable_damage_semantics'] is False
    assert normal_ehp['model_requirement_applicability']['gc_boss_applicable_damage_semantics'] is False
    assert 'source_owned_full_boss_applicable_damage_semantics' not in normal_ehp['model_completion_blockers']
    assert normal['effective_model_closure'] == {
        'non_boss_terminal_pressure': True,
        'v28_damage_health_decay_magnitudes': True,
        'boss_applicable_damage_semantics': False,
        'gc_boss_applicable_damage_semantics': False,
    }
    assert normal_ehp['effective_model_closure'] == {
        'non_boss_terminal_pressure': True,
        'v28_damage_health_decay_magnitudes': True,
        'boss_applicable_damage_semantics': True,
        'gc_boss_applicable_damage_semantics': True,
    }
    assert tournament['effective_model_closure'] == {
        'non_boss_terminal_pressure': True,
        'v28_damage_health_decay_magnitudes': False,
        'boss_applicable_damage_semantics': False,
        'gc_boss_applicable_damage_semantics': False,
    }
    runtime_fields = set(ScenarioRuntimeInputs.__dataclass_fields__)
    supported = set(tournament['explicit_runtime_overrides_supported'])
    assert supported <= runtime_fields
    assert {
        'boss_time_to_contact_seconds',
        'boss_hit_interval_seconds',
        'effective_damage_reduction_pct',
        'incoming_damage_multiplier',
        'boss_wave_pressure_factor',
        'orb_boss_hit_pct',
        'orb_boss_hit_count',
        'orb_boss_total_damage_pct',
        'electron_hit_count',
        'electron_total_damage_pct',
        'flame_bot_damage_reduction_pct',
        'flame_bot_boss_hit_chance_pct',
        'flame_bot_duration_seconds',
        'flame_bot_cooldown_seconds',
        'defense_field_damage_reduction_pct',
        'defense_field_duration_seconds',
        'defense_field_cooldown_seconds',
        'black_hole_damage_reduction_pct',
        'black_hole_duration_seconds',
        'black_hole_cooldown_seconds',
        'pbh_encounter_uptime_fraction',
        'boss_applicable_damage_per_second',
        'boss_applicable_damage_factor',
        'boss_edamage_target_share',
        'boss_edamage_cadence_uptime_factor',
        'boss_edamage_reliability_factor',
        'boss_edamage_semantic_normalizer',
        'death_wave_health_max_multiplier',
        'death_wave_health_max_wave',
        'enemy_level_skip_reduction_pp',
        'enemy_level_skip_decay_start_wave',
        'enemy_level_skip_decay_pct',
        'enemy_level_skip_decay_interval_waves',
        'tower_damage_decay_start_wave',
        'tower_damage_decay_pct',
        'tower_health_decay_start_wave',
        'tower_health_decay_pct',
        'fleet_terminal_max_wave',
        'elite_terminal_max_wave',
        'protector_terminal_max_wave',
        'armored_terminal_max_wave',
        'boss_terminal_max_wave',
    } <= supported
    assert 'boss_wave_interval' not in supported
    assert 'orb_boss_hits_per_second' not in supported
    assert 'electron_hits_per_second' not in supported
    assert 'enemy_skip_decay_pct_per_step' not in supported
    assert 'tower_damage_decay_pct_per_step' not in supported
    assert 'tower_health_decay_pct_per_step' not in supported


def test_boss_wave_model_certification_reports_v28_damage_health_decay_closure_details():
    from app.pipeline import _boss_wave_model_certification_payload
    from input.state_types import ScenarioRuntimeInputs

    missing = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({'tower_damage_decay_pct': 1.0}),
        damage_health_decay_required=True,
        gc_boss_applicable_damage_required=False,
    )
    closed = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping(
            {
                'tower_damage_decay_pct': 1.0,
                'tower_health_decay_pct': 2.0,
                'tower_damage_decay_start_wave': 4500.0,
            }
        ),
        damage_health_decay_required=True,
        gc_boss_applicable_damage_required=False,
    )
    not_required = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({}),
        damage_health_decay_required=False,
        gc_boss_applicable_damage_required=False,
    )

    missing_status = missing['v28_damage_health_decay_closure']
    assert missing_status['closed'] is False
    assert missing_status['mode'] == 'missing_source_owned_magnitudes'
    assert missing_status['required_fields'] == ['tower_damage_decay_pct', 'tower_health_decay_pct']
    assert missing_status['missing_fields'] == ['tower_health_decay_pct']
    assert missing_status['source_owned_default_available'] is False
    assert 'source_owned_v28_damage_health_decay_magnitudes' in missing['model_completion_blockers']

    closed_status = closed['v28_damage_health_decay_closure']
    assert closed_status['closed'] is True
    assert closed_status['mode'] == 'explicit_runtime_inputs'
    assert closed_status['missing_fields'] == []
    assert closed_status['supplied_start_wave_fields'] == ['tower_damage_decay_start_wave']
    assert closed['runtime_override_closure']['v28_damage_health_decay_magnitudes'] is True
    assert 'source_owned_v28_damage_health_decay_magnitudes' not in closed['model_completion_blockers']

    not_required_status = not_required['v28_damage_health_decay_closure']
    assert not_required_status['closed'] is False
    assert not_required_status['mode'] == 'not_required'
    assert not_required_status['required'] is False
    assert 'source_owned_v28_damage_health_decay_magnitudes' not in not_required['model_completion_blockers']


def test_boss_wave_model_certification_closes_only_relevant_terminal_pressure_overrides():
    from app.pipeline import _boss_wave_model_certification_payload
    from input.state_types import ScenarioRuntimeInputs

    certification = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({'armored_terminal_max_wave': 900}),
        non_boss_terminal_pressure_required=True,
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        damage_health_decay_required=False,
        gc_boss_applicable_damage_required=False,
    )

    assert certification['runtime_override_closure']['non_boss_terminal_pressure'] is True
    assert certification['model_closure_status'] == 'closed_with_explicit_terminal_pressure_inputs'
    assert certification['accepted_approximation_closure'] == {
        'closed': False,
        'mode': 'none',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': None,
        'replaced_blockers': [],
        'certification_effect': 'none',
        'certified_full_max_wave_model': False,
    }
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in certification['model_completion_blockers']
    terminal_status = certification['terminal_pressure_runtime_override_status']
    assert terminal_status['mode'] == 'active_unsupported_pressure_inputs'
    assert terminal_status['required_fields'] == ['armored_terminal_max_wave']
    assert terminal_status['missing_fields'] == []
    assert terminal_status['unmapped_pressures'] == []
    assert terminal_status['required_fields_by_pressure'] == {
        'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
    }


def test_boss_wave_model_certification_maps_boss_ultimate_to_boss_terminal_override():
    from app.pipeline import _boss_wave_model_certification_payload
    from input.state_types import ScenarioRuntimeInputs

    missing = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({'armored_terminal_max_wave': 900}),
        non_boss_terminal_pressure_required=True,
        unsupported_terminal_pressures=['boss_ultimate_deferred'],
        damage_health_decay_required=False,
        gc_boss_applicable_damage_required=False,
    )
    closed = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({'boss_terminal_max_wave': 901}),
        non_boss_terminal_pressure_required=True,
        unsupported_terminal_pressures=['boss_ultimate_deferred'],
        damage_health_decay_required=False,
        gc_boss_applicable_damage_required=False,
    )

    assert missing['terminal_pressure_runtime_override_status']['required_fields'] == [
        'boss_terminal_max_wave'
    ]
    assert missing['terminal_pressure_runtime_override_status']['missing_fields'] == [
        'boss_terminal_max_wave'
    ]
    assert missing['terminal_pressure_runtime_override_status']['unmapped_pressures'] == []
    assert 'source_owned_non_boss_terminal_pressure_formulas' in missing['model_completion_blockers']
    assert closed['terminal_pressure_runtime_override_status']['closed'] is True
    assert closed['terminal_pressure_runtime_override_status']['missing_fields'] == []
    assert closed['runtime_override_closure']['non_boss_terminal_pressure'] is True
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in closed['model_completion_blockers']


def test_boss_wave_model_certification_closes_terminal_pressure_by_explicit_pressure_factor():
    from app.pipeline import _boss_wave_model_certification_payload
    from input.state_types import ScenarioRuntimeInputs

    certification = _boss_wave_model_certification_payload(
        runtime_inputs=ScenarioRuntimeInputs.from_mapping({'boss_wave_pressure_factor': 1.25}),
        non_boss_terminal_pressure_required=True,
        unsupported_terminal_pressures=['armored_enemies_blocked_hits'],
        damage_health_decay_required=False,
        gc_boss_applicable_damage_required=False,
    )

    assert certification['runtime_override_closure']['non_boss_terminal_pressure'] is True
    assert certification['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert certification['accepted_approximation_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': 1.25,
        'replaced_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
        'certification_effect': 'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation',
        'certified_full_max_wave_model': False,
    }
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in certification['model_completion_blockers']
    assert certification['terminal_pressure_runtime_override_status']['closed'] is False
    assert certification['terminal_pressure_runtime_override_status']['missing_fields'] == ['armored_terminal_max_wave']
    closure = certification['non_boss_terminal_pressure_closure']
    assert closure == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': True,
        'boss_wave_pressure_factor': 1.25,
    }


def test_boss_wave_hit_interval_applies_slow_aura_mastery_when_not_explicit() -> None:
    from simulators.timing import boss_hit_interval_seconds

    interval, source, components = boss_hit_interval_seconds(
        scenario_base_seconds=2.0,
        slow_aura_mastery_attack_interval_multiplier=1.5,
    )

    assert interval == pytest.approx(3.0)
    assert source == 'scenario_boss_hit_interval_plus_slow_aura_mastery'
    assert components['slow_aura_mastery_attack_interval_multiplier'] == pytest.approx(1.5)

    explicit_interval, explicit_source, explicit_components = boss_hit_interval_seconds(
        explicit_hit_interval_seconds=2.25,
        scenario_base_seconds=2.0,
        slow_aura_mastery_attack_interval_multiplier=1.5,
    )

    assert explicit_interval == pytest.approx(2.25)
    assert explicit_source == 'runtime_input_boss_hit_interval_seconds'
    assert explicit_components['slow_aura_mastery_attack_interval_multiplier'] == pytest.approx(1.0)


@pytest.mark.live
def test_boss_wave_dissonance_run_masks_are_visible_and_feed_max_wave_matrix():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload
    from qe.kb_surfaces import load_dissonant_run_restrictions

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        perk_mode='max_progression_policy',
        perk_policy_preset='eHP Farming',
    )
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        include_dissonance_run_matrix=True,
    )

    matrix = payload['dissonance_run_matrix']
    assert [row['dissonance_run_category'] for row in matrix] == [
        'none',
        'attack',
        'defense',
        'utility',
        'ultimate_weapons',
    ]
    assert all('selected_max_wave' in row for row in matrix)
    restrictions = load_dissonant_run_restrictions()
    rows_by_category = {row['dissonance_run_category']: row for row in matrix}
    for category, spec in restrictions.items():
        mask_summary = rows_by_category[category]['mask_summary']
        assert mask_summary['category'] == category
        for primitive_key, expected_value in dict(spec.get('primitive_restrictions') or {}).items():
            actual_value = mask_summary['restricted_primitives'][primitive_key]
            if isinstance(expected_value, str):
                assert actual_value == expected_value
            else:
                assert actual_value == pytest.approx(float(expected_value))
        assert set(mask_summary['zeroed_workshop_tracks']) == set(spec.get('zero_workshop_tracks') or ())
        assert set(spec.get('disabled_runtime_systems') or ()).issubset(set(mask_summary['disabled_runtime_systems']))
    uw_mask_summary = rows_by_category['ultimate_weapons']['mask_summary']
    for primitive_key, conditional in dict(restrictions['ultimate_weapons'].get('conditional_primitive_restrictions') or {}).items():
        assert uw_mask_summary['restricted_primitives'][primitive_key] == pytest.approx(float(conditional['value']))
        assert uw_mask_summary['conditional_primitive_restrictions'][primitive_key]['masked_source'] == conditional['masked_source']
    assert matrix[1]['mask_summary']['category'] == 'attack'
    assert matrix[1]['mask_summary']['restricted_primitives']['tower_attack_speed'] == pytest.approx(1.0)
    assert matrix[1]['mask_summary']['restricted_primitives']['tower_bounce_shot_range_m'] == pytest.approx(0.0)
    assert 'Bounce Shot Range' in matrix[1]['mask_summary']['zeroed_workshop_tracks']
    assert matrix[2]['mask_summary']['restricted_primitives']['tower_hp'] == pytest.approx(1.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['tower_shockwave_size_m'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['wall_thorns_contact_damage_pct'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['wall_thorns_damage_increase_per_hit'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['orb_boss_total_damage_pct'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['death_defy_chance_pct'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['death_defy_effective_chance_pct'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['energy_shield_enabled'] == pytest.approx(0.0)
    assert matrix[2]['mask_summary']['restricted_primitives']['energy_shield_effective_charge_count'] == pytest.approx(0.0)
    assert 'Wall Health' in matrix[2]['mask_summary']['zeroed_workshop_tracks']
    assert 'Orbs' in matrix[2]['mask_summary']['zeroed_workshop_tracks']
    assert 'death_defy_stochastic_survival_disabled' in matrix[2]['mask_summary']['disabled_runtime_systems']
    assert 'energy_shield_contact_absorption_disabled' in matrix[2]['mask_summary']['disabled_runtime_systems']
    assert matrix[3]['mask_summary']['restricted_primitives']['free_attack_upgrade_chance'] == pytest.approx(0.0)
    assert matrix[3]['mask_summary']['restricted_primitives']['attack_skip_chance'] == pytest.approx(0.0)
    assert matrix[3]['mask_summary']['restricted_primitives']['attack_skip_workshop_track'] == ''
    assert 'Enemy Attack Level Skip' in matrix[3]['mask_summary']['zeroed_workshop_tracks']
    assert matrix[4]['mask_summary']['restricted_primitives']['chain_lightning_boss_damage_per_second'] == pytest.approx(0.0)
    assert matrix[4]['mask_summary']['restricted_primitives']['qe_boss_applicable_cl_only_damage_per_second'] == pytest.approx(0.0)
    assert matrix[4]['mask_summary']['restricted_primitives']['chrono_field_slow_pct'] == pytest.approx(0.0)
    assert matrix[4]['mask_summary']['restricted_primitives']['spotlight_bonus_multiplier'] == pytest.approx(1.0)
    assert matrix[4]['mask_summary']['restricted_primitives']['spotlight_angle_degrees'] == pytest.approx(0.0)
    assert matrix[4]['mask_summary']['restricted_primitives']['spotlight_count'] == pytest.approx(0.0)
    assert 'energy_net_mastery_multiplier' not in matrix[4]['mask_summary']['restricted_primitives']
    assert 'death_wave_health_multiplier_disabled' in matrix[4]['mask_summary']['disabled_runtime_systems']

    attack_run = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='attack',
    )
    attack_primitives = attack_run['diagnostics']['replacement_primitive_inputs']['values']
    assert attack_primitives['dissonance_run_category'] == 'attack'
    assert attack_primitives['dissonance_attack_run_active'] is True
    assert attack_primitives['dissonance_utility_run_active'] is False
    assert attack_primitives['edamage_attack_dissonance_restricted'] == pytest.approx(1.0)
    assert attack_primitives['tower_range_m'] == pytest.approx(30.0)
    assert attack_primitives['tower_attack_speed'] == pytest.approx(1.0)
    assert attack_run['summary']['selected_model'] == 'unified_hit_by_hit_boss_survival_under_attack_dissonance'
    assert attack_run['summary']['selected_max_wave'] > 0
    assert attack_run['summary']['pre_contact_boss_kill_max_wave'] == 0
    assert attack_run['summary']['gc_pre_contact_max_wave'] == 0
    assert attack_run['summary']['gc_pre_contact_max_wave'] == attack_run['summary']['pre_contact_boss_kill_max_wave']

    request_level_attack_run = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='max_progression_policy',
            perk_policy_preset='GC Max Waves',
            dissonance_run_category='attack',
        ),
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
    )
    request_attack_summary = request_level_attack_run['summary']
    request_attack_primitives = request_level_attack_run['diagnostics']['replacement_primitive_inputs']['values']
    assert request_attack_primitives['dissonance_attack_run_active'] is True
    assert request_attack_summary['selected_model'] == 'unified_hit_by_hit_boss_survival_under_attack_dissonance'
    assert request_attack_summary['selected_loadout_type'] == 'gc'
    assert request_attack_summary['pre_contact_boss_kill_max_wave'] == 0
    assert request_attack_summary['gc_pre_contact_max_wave'] == 0
    assert request_attack_summary['gc_pre_contact_max_wave'] == request_attack_summary['pre_contact_boss_kill_max_wave']

    defense_run = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='defense',
    )
    defense_primitives = defense_run['diagnostics']['replacement_primitive_inputs']['values']
    assert defense_primitives['dissonance_defense_run_active'] is True
    assert defense_primitives['edamage_defense_dissonance_shockwave_restricted'] == pytest.approx(1.0)
    assert defense_primitives['tower_shockwave_size_m'] == pytest.approx(0.0)
    assert defense_primitives['tower_shockwave_interval_seconds'] == pytest.approx(0.0)
    assert defense_primitives['death_defy_chance_pct'] == pytest.approx(0.0)
    assert defense_primitives['death_defy_effective_chance_pct'] == pytest.approx(0.0)
    assert defense_primitives['energy_shield_enabled'] == pytest.approx(0.0)
    assert defense_primitives['energy_shield_effective_charge_count'] == pytest.approx(0.0)

    defense_gc_run = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='max_progression_policy',
            perk_policy_preset='GC Max Waves',
        ),
        preset_name='Farming',
        tier_number=1,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='defense',
    )
    assert defense_gc_run['diagnostics']['replacement_primitive_inputs']['values']['wall_hp'] == pytest.approx(0.0)
    assert (
        defense_gc_run['diagnostics']['replacement_primitive_inputs']['values']['boss_damage_source']
        == 'qe_derived_edamage_ep_boss_exposure_model'
    )
    assert (
        defense_gc_run['diagnostics']['replacement_primitive_inputs']['values']['gc_boss_damage_source']
        == defense_gc_run['diagnostics']['replacement_primitive_inputs']['values']['boss_damage_source']
    )
    assert defense_gc_run['summary']['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert defense_gc_run['summary']['selected_loadout_type'] == 'gc'
    assert defense_gc_run['summary']['selected_max_wave'] > 0
    assert (
        'source_owned_full_boss_applicable_damage_semantics'
        not in defense_gc_run['diagnostics']['model_certification']['model_completion_blockers']
    )

    utility_run = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='utility',
    )
    utility_primitives = utility_run['diagnostics']['replacement_primitive_inputs']['values']
    assert utility_primitives['dissonance_utility_run_active'] is True
    assert utility_primitives['dissonance_attack_run_active'] is False
    assert utility_primitives['attack_skip_workshop_track'] == ''

    uw_run = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='uw',
    )
    uw_primitives = uw_run['diagnostics']['replacement_primitive_inputs']['values']
    assert uw_primitives['dissonance_ultimate_weapons_run_active'] is True
    assert uw_primitives['dissonance_defense_run_active'] is False
    assert uw_primitives['chain_lightning_boss_damage_per_second'] == pytest.approx(0.0)
    assert uw_primitives['qe_boss_applicable_cl_only_damage_per_second'] == pytest.approx(0.0)
    assert uw_primitives['chrono_field_slow_pct'] == pytest.approx(0.0)
    assert uw_primitives['spotlight_bonus_multiplier'] == pytest.approx(1.0)
    assert uw_primitives['spotlight_angle_degrees'] == pytest.approx(0.0)
    assert uw_primitives['spotlight_count'] == pytest.approx(0.0)
    assert uw_run['diagnostics']['replacement_primitive_semantics_ledger']['wall_hp_formula_check']['death_wave_health_max_multiplier'] == pytest.approx(1.0)

    uw_energy_net_run = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='max_progression_policy',
            perk_policy_preset='GC Max Waves',
        ),
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='uw',
    )
    uw_energy_net_primitives = uw_energy_net_run['diagnostics']['replacement_primitive_inputs']['values']
    assert uw_energy_net_primitives['card_profile_preset'] == 'Tourney'
    assert uw_energy_net_primitives['energy_net_duration_seconds'] > 0.0
    assert uw_energy_net_primitives['energy_net_mastery_multiplier'] > 1.0
    assert (
        uw_energy_net_primitives['energy_net_damage_multiplier_duration_seconds']
        >= uw_energy_net_primitives['energy_net_duration_seconds']
    )


def test_boss_wave_ultimate_weapons_dissonance_masks_chrono_field_before_contact_derivation():
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        perk_mode='max_progression_policy',
        perk_policy_preset='eHP Farming',
    )
    common_kwargs = {
        'preset_name': 'Farming',
        'tier_number': 14,
        'end_wave': 20,
        'boss_wave_step': 10,
        'stop_on_failure': False,
        'scenario_runtime_inputs': {'orb_boss_total_damage_pct': 6.0},
    }

    regular_run = build_boss_wave_payload(request, **common_kwargs)
    uw_run = build_boss_wave_payload(
        request,
        **common_kwargs,
        dissonance_run_category='ultimate_weapons',
    )

    regular_primitives = regular_run['diagnostics']['replacement_primitive_inputs']['values']
    uw_primitives = uw_run['diagnostics']['replacement_primitive_inputs']['values']
    uw_mask = uw_run['diagnostics']['dissonance_run_mask']
    uw_contact_contract = uw_run['diagnostics']['contact_time_contract']['boss_time_to_contact_seconds']

    assert 'boss_time_to_contact_seconds' not in regular_run['diagnostics']['scenario_runtime_inputs']
    assert 'boss_time_to_contact_seconds' not in uw_run['diagnostics']['scenario_runtime_inputs']
    assert regular_primitives['chrono_field_slow_pct'] > 0.0
    assert regular_primitives['boss_time_to_contact_chrono_field_average_slow_fraction'] > 0.0

    for primitive_key in (
        'chrono_field_duration_seconds',
        'chrono_field_cooldown_seconds',
        'chrono_field_damage_reduction_pct',
        'chrono_field_slow_pct',
    ):
        assert uw_primitives[primitive_key] == pytest.approx(0.0)
        assert uw_mask['restricted_primitives'][primitive_key] == pytest.approx(0.0)

    assert uw_primitives['boss_time_to_contact_chrono_field_average_slow_fraction'] == pytest.approx(0.0)
    assert uw_contact_contract['chrono_field_average_slow_fraction'] == pytest.approx(0.0)
    assert uw_contact_contract['source'] == 'derived_geometry_displayed_proxy_base_cf_slow_aura_energy_net'
    assert uw_contact_contract['base_seconds_source'] == 'geometry_displayed_proxy_candidate'
    assert (
        uw_contact_contract['geometry_proxy_truth_status']
        == 'displayed_proxy_candidate_not_wall_contact_truth'
    )
    assert 'chrono_field_slow_contact_time_and_dr_disabled' in uw_mask['disabled_runtime_systems']

    slow_aura_fraction = float(uw_primitives['boss_time_to_contact_slow_aura_fraction'])
    expected_speed_remaining = max(0.01, 1.0 - slow_aura_fraction)
    expected_contact_time = (
        float(uw_primitives['boss_time_to_contact_base_seconds']) / expected_speed_remaining
    ) + float(uw_primitives['boss_time_to_contact_energy_net_hold_seconds'])
    assert uw_primitives['boss_time_to_contact_speed_remaining_fraction'] == pytest.approx(expected_speed_remaining)
    assert uw_primitives['boss_time_to_contact_seconds'] == pytest.approx(expected_contact_time)
    assert uw_contact_contract['value'] == pytest.approx(expected_contact_time)
    assert regular_primitives['boss_time_to_contact_seconds'] > uw_primitives['boss_time_to_contact_seconds']


@pytest.mark.live
def test_boss_wave_payload_threads_all_dissonance_boost_factors_into_gc_damage():
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        runtime_state_overlay='disco_respec_2026_06_10',
        perk_mode='max_progression_policy',
        perk_policy_preset='GC Max Waves',
    )
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
    )

    primitives = payload['diagnostics']['replacement_primitive_inputs']['values']
    assert primitives['dissonance_attack_active_boost_multiplier'] > 1.0
    assert primitives['dissonance_defense_active_boost_multiplier'] > 1.0
    assert primitives['dissonance_utility_active_boost_multiplier'] > 1.0
    assert primitives['dissonance_ultimate_weapons_active_boost_multiplier'] > 1.0
    assert primitives['edamage_attack_dissonance_factor'] == pytest.approx(
        primitives['dissonance_attack_total_multiplier']
    )
    assert primitives['ehp_defense_dissonance_factor'] == pytest.approx(
        primitives['dissonance_defense_total_multiplier']
    )
    assert primitives['dissonance_utility_total_multiplier'] > 1.0
    assert primitives['edamage_uw_dissonance_factor'] == pytest.approx(
        primitives['dissonance_ultimate_weapons_total_multiplier']
    )
    assert primitives['edamage_attack_dissonance_factor'] > 1.0
    assert primitives['edamage_uw_dissonance_factor'] > 1.0
    assert primitives['boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
    assert primitives['boss_damage_per_second'] == pytest.approx(
        primitives['edamage_ep'] * primitives['edamage_boss_runtime_factor']
    )


@pytest.mark.live
def test_boss_wave_milestone_matrix_selects_best_loadout_by_tier_and_dissonance_category():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(14,),
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        loadout_policy_presets=('eHP Farming', 'GC Max Waves'),
    )

    assert matrix['artifact'] == 'boss_wave_milestone_matrix'
    assert matrix['model_scope'] == 'boss_contact_survivability'
    assert matrix['not_full_max_wave_model'] is True
    assert matrix['model_certification_status'] == 'partial_boss_contact_model'
    assert matrix['certified_full_max_wave_model'] is False
    assert matrix['model_certification']['certified_full_max_wave_model'] is False
    assert matrix['model_certification']['model_certification_status'] == 'partial_boss_contact_model'
    assert matrix['model_certification']['model_requirement_applicability']['non_boss_terminal_pressure'] is False
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in matrix['model_certification']['model_completion_blockers']
    assert (
        'source_owned_v28_damage_health_decay_magnitudes'
        not in matrix['model_certification']['model_completion_blockers']
    )
    assert (
        matrix['model_certification']['model_requirement_applicability']['v28_damage_health_decay_magnitudes']
        is False
    )
    assert matrix['preset_name'] == 'Milestone'
    assert matrix['tiers'] == [14]
    assert matrix['scenario_runtime_input_sources']['boss_time_to_contact_seconds'] == 'caller_supplied_runtime_input'
    assert matrix['contact_time_contract']['boss_time_to_contact_seconds']['matrix_default_is_uncertified_assumption'] is False
    assert [row['dissonance_run_category'] for row in matrix['rows']] == [
        'none',
        'attack',
        'defense',
        'utility',
        'ultimate_weapons',
    ]
    assert matrix['model_blocker_summary'] == {
        'row_count': 5,
        'rows_with_model_completion_blockers': 0,
        'model_completion_blocker_counts': {},
        'rows_with_unsupported_terminal_pressures': 0,
        'unsupported_terminal_pressure_counts': {},
    }
    assert len(matrix['wide_rows']) == 1
    wide = matrix['wide_rows'][0]
    assert wide['tier_column'] == 'Tier 14'
    assert wide['milestone_reference_wave'] == 5761
    assert wide['regular_reference_kind'] == 'ids_milestone_wave'
    assert wide['regular_reference_wave'] == 5761
    assert wide['attack_reference_kind'] == 'ids_dissonant_pb_wave'
    assert wide['attack_reference_wave'] == 5000
    assert wide['defense_reference_wave'] == 5000
    utility_row = next(row for row in matrix['rows'] if row['dissonance_run_category'] == 'utility')
    assert wide['utility_reference_wave'] == utility_row['reference_wave']
    assert wide['utility_reference_wave'] > 0
    assert wide['ultimate_weapons_reference_wave'] == 4727
    assert wide['regular_best_loadout'] in {'eHP Farming', 'GC Max Waves'}
    assert wide['attack_best_loadout'] in {'eHP Farming', 'GC Max Waves'}
    if not str(wide['regular_best_loadout']).startswith('GC'):
        assert wide['regular_best_gc_boss_damage_source'] is None
    assert 'regular_status' in wide
    assert wide['regular_model_certification_status'] == 'partial_boss_contact_model'
    assert wide['regular_certified_full_max_wave_model'] is False
    assert 'attack_status' in wide
    attack_row = next(row for row in matrix['rows'] if row['dissonance_run_category'] == 'attack')
    ehp_attack_candidate = next(row for row in attack_row['candidate_results'] if row['loadout_policy_preset'] == 'eHP Farming')
    assert ehp_attack_candidate['selected_model'] == 'unified_hit_by_hit_boss_survival_under_attack_dissonance'
    assert ehp_attack_candidate['selected_max_wave'] > 0
    assert ehp_attack_candidate['alignment']['calculated_selected_max_wave'] == ehp_attack_candidate['selected_max_wave']
    assert 'source_owned_full_boss_applicable_damage_semantics' not in ehp_attack_candidate['model_completion_blockers']
    gc_attack_candidate = next(row for row in attack_row['candidate_results'] if row['loadout_policy_preset'] == 'GC Max Waves')
    assert gc_attack_candidate['selected_model'] == 'unified_hit_by_hit_boss_survival_under_attack_dissonance'
    assert gc_attack_candidate['selected_loadout_type'] == 'gc'
    assert gc_attack_candidate['pre_contact_boss_kill_max_wave'] == 0
    assert gc_attack_candidate['gc_pre_contact_max_wave'] == gc_attack_candidate['pre_contact_boss_kill_max_wave']
    assert gc_attack_candidate['boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
    assert gc_attack_candidate['gc_boss_damage_source'] == gc_attack_candidate['boss_damage_source']
    assert 'source_owned_full_boss_applicable_damage_semantics' not in gc_attack_candidate['model_completion_blockers']
    assert attack_row['best_selected_max_wave'] == max(
        ehp_attack_candidate['selected_max_wave'],
        gc_attack_candidate['selected_max_wave'],
    )
    assert attack_row['ids_reference_alignment']['enabled'] is True
    assert attack_row['ids_reference_alignment']['applied'] is False
    assert (
        attack_row['ids_reference_alignment']['reason']
        == 'dissonance_pb_at_bonus_cap_not_exact_reference'
    )
    assert attack_row['ids_reference_alignment']['reference_interpretation'] == (
        'lower_bound_at_dissonance_bonus_cap'
    )
    assert attack_row['ids_reference_alignment']['dissonance_pb_bonus_cap_wave'] == 5000
    assert attack_row['reference_quality']['dissonance_pb_bonus_cap_reached'] is True
    assert attack_row['reference_quality']['exact_reference'] is False
    assert attack_row['pressure_factor_reference_hint']['enabled'] is False
    assert attack_row['pressure_factor_reference_hint']['mode'] == (
        'dissonance_pb_bonus_cap_not_exact_reference'
    )
    assert attack_row['reference_kind'] == 'ids_dissonant_pb_wave'
    assert attack_row['reference_wave'] == 5000
    assert attack_row['dissonance_pb_reference_wave'] == 5000
    assert attack_row['delta_vs_reference_wave'] == attack_row['best_selected_max_wave'] - 5000
    defense_row = next(row for row in matrix['rows'] if row['dissonance_run_category'] == 'defense')
    if str(defense_row['best_selected_loadout_type']) == 'gc':
        assert defense_row['best_boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
        assert defense_row['best_gc_boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
    else:
        assert defense_row['best_gc_boss_damage_source'] is None
    ehp_defense_candidate = next(row for row in defense_row['candidate_results'] if row['loadout_policy_preset'] == 'eHP Farming')
    assert ehp_defense_candidate['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert ehp_defense_candidate['selected_max_wave'] >= 0
    gc_defense_candidate = next(row for row in defense_row['candidate_results'] if row['loadout_policy_preset'] == 'GC Max Waves')
    assert gc_defense_candidate['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert gc_defense_candidate['boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
    assert gc_defense_candidate['gc_boss_damage_source'] == gc_defense_candidate['boss_damage_source']
    assert gc_defense_candidate['selected_max_wave'] >= 0
    assert 'source_owned_full_boss_applicable_damage_semantics' not in gc_defense_candidate['model_completion_blockers']
    regular_row = next(row for row in matrix['rows'] if row['dissonance_run_category'] == 'none')
    assert regular_row['reference_kind'] == 'ids_milestone_wave'
    assert regular_row['reference_wave'] == 5761
    for row in matrix['rows']:
        category = row['dissonance_run_category']
        expected_model = (
            'unified_hit_by_hit_boss_survival'
            if category == 'none'
            else f'unified_hit_by_hit_boss_survival_under_{category}_dissonance'
        )
        assert row['best_selected_max_wave'] >= 0
        assert row['best_selected_model'] == expected_model
        assert row['best_model_certification_status'] == 'partial_boss_contact_model'
        assert row['model_certification_status'] == 'partial_boss_contact_model'
        assert row['model_certification']['model_certification_status'] == 'partial_boss_contact_model'
        assert row['model_certification']['certified_full_max_wave_model'] is False
        assert row['certified_full_max_wave_model'] is False
        assert 'source_owned_v28_damage_health_decay_magnitudes' not in row['model_completion_blockers']
        assert row['best_loadout_policy_preset'] in {'eHP Farming', 'GC Max Waves'}
        assert len(row['candidate_results']) == 2
        for candidate in row['candidate_results']:
            assert candidate['selected_model'] == expected_model
            assert candidate['selected_max_wave'] == candidate['hit_by_hit_max_wave']
            assert candidate['alignment']['calculated_selected_max_wave'] == candidate['selected_max_wave']
        assert row['best_display'].endswith(f"({row['best_loadout_policy_preset']})")
        assert row['reference_wave'] is not None
        assert row['delta_vs_reference_wave'] == row['best_selected_max_wave'] - row['reference_wave']


def test_boss_wave_milestone_matrix_labels_default_contact_time_as_uncertified_assumption():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out'),
        tiers=(14,),
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=True,
        loadout_policy_presets=('eHP Farming',),
        dissonance_run_categories=('none',),
    )

    contact_contract = matrix['contact_time_contract']['boss_time_to_contact_seconds']
    assert 'boss_time_to_contact_seconds' not in matrix['scenario_runtime_inputs']
    assert 'boss_time_to_contact_seconds' not in matrix['scenario_runtime_input_sources']
    assert contact_contract['source'] == 'per_candidate_derived_geometry_displayed_proxy_base_cf_slow_aura_energy_net'
    assert contact_contract['ownership'] == 'runtime_input_override_or_per_candidate_geometry_proxy_simulator_derivation'
    assert contact_contract['derived_by_simulator'] is True
    assert contact_contract['geometry_proxy_status'] == 'per_candidate_displayed_proxy_base'
    assert contact_contract['matrix_default_is_uncertified_assumption'] is False
    assert (
        'matrix_default_boss_contact_time_is_uncertified_assumption'
        not in matrix['model_certification']['model_completion_blockers']
    )

    caller_supplied = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out'),
        tiers=(14,),
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
        },
        loadout_policy_presets=('eHP Farming',),
        dissonance_run_categories=('none',),
    )
    assert caller_supplied['scenario_runtime_input_sources']['boss_time_to_contact_seconds'] == 'caller_supplied_runtime_input'
    assert caller_supplied['model_certification']['model_completion_blockers'] == []


def test_boss_wave_milestone_matrix_selection_prefers_owned_complete_candidate():
    from app.pipeline import _boss_wave_milestone_matrix_selection_rank

    policy_presets = ('eHP Max Waves', 'GC Max Waves')
    incomplete_high = {
        'loadout_policy_preset': 'GC Max Waves',
        'selected_max_wave': 9000,
        'status': 'incomplete',
    }
    complete_low = {
        'loadout_policy_preset': 'eHP Max Waves',
        'selected_max_wave': 100,
        'status': 'complete',
    }

    best = max(
        (incomplete_high, complete_low),
        key=lambda row: _boss_wave_milestone_matrix_selection_rank(row, policy_presets),
    )
    assert best is complete_low


def test_boss_wave_replacement_primitive_cache_is_bounded_and_returns_copies(monkeypatch):
    from types import SimpleNamespace

    from app import pipeline as pipeline_mod

    calls = {'count': 0}

    def fake_resolver(**_kwargs):
        calls['count'] += 1
        return {'value': float(calls['count']), 'nested': {'safe': True}}

    monkeypatch.setattr(pipeline_mod, '_resolve_boss_wave_replacement_primitives', fake_resolver)
    monkeypatch.setattr(pipeline_mod, '_BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE_MAX_SIZE', 2)
    pipeline_mod._BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE.clear()

    account_state = SimpleNamespace()
    base_config = {
        'mode_id': 'milestone',
        'tier_number': 14,
        'tier_column': 'Tier 14',
        'league': '',
        'tournament_wave': 0,
        'dissonance_run_category': 'none',
    }

    first = pipeline_mod._resolve_boss_wave_replacement_primitives_cached(
        account_state=account_state,
        preset_name='Farming',
        config=base_config,
        perks_enabled=True,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0},
        workshop_levels={'Damage': 1},
    )
    first['value'] = 999.0
    second = pipeline_mod._resolve_boss_wave_replacement_primitives_cached(
        account_state=account_state,
        preset_name='Farming',
        config=base_config,
        perks_enabled=True,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0},
        workshop_levels={'Damage': 1},
    )
    assert second['value'] == pytest.approx(1.0)
    assert calls['count'] == 1

    for tier in (15, 16):
        config = dict(base_config)
        config['tier_number'] = tier
        config['tier_column'] = f'Tier {tier}'
        pipeline_mod._resolve_boss_wave_replacement_primitives_cached(
            account_state=account_state,
            preset_name='Farming',
            config=config,
            perks_enabled=True,
            scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0},
            workshop_levels={'Damage': 1},
        )

    assert len(pipeline_mod._BOSS_WAVE_REPLACEMENT_PRIMITIVES_CACHE) <= 2


@pytest.mark.live
def test_boss_wave_milestone_matrix_progressive_horizon_matches_full_horizon(monkeypatch):
    from app.models import PipelineRunRequest
    from app import pipeline as pipeline_mod

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    kwargs = {
        'tiers': (14, 19),
        'end_wave': 8000,
        'boss_wave_step': 10,
        'stop_on_failure': True,
        'scenario_runtime_inputs': {'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        'loadout_policy_presets': ('eHP Max Waves', 'GC Max Waves'),
        'dissonance_run_categories': ('none', 'defense', 'utility'),
    }

    progressive = pipeline_mod.build_boss_wave_milestone_matrix(request, **kwargs)
    original = pipeline_mod._boss_wave_matrix_candidate_end_waves
    monkeypatch.setattr(
        pipeline_mod,
        '_boss_wave_matrix_candidate_end_waves',
        lambda **payload: (int(payload['final_end_wave']),),
    )
    full_horizon = pipeline_mod.build_boss_wave_milestone_matrix(request, **kwargs)
    monkeypatch.setattr(pipeline_mod, '_boss_wave_matrix_candidate_end_waves', original)

    assert progressive['wide_rows'] == full_horizon['wide_rows']
    for progressive_row, full_row in zip(progressive['rows'], full_horizon['rows']):
        for key in (
            'tier',
            'dissonance_run_category',
            'best_selected_max_wave',
            'best_loadout_policy_preset',
            'best_selected_model',
            'best_status',
        ):
            assert progressive_row[key] == full_row[key]


@pytest.mark.live
def test_boss_wave_milestone_matrix_can_compare_default_to_bridge_assumptions():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out'),
        tiers=(14,),
        end_wave=5200,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        comparison_scenario_runtime_inputs={
            'boss_edamage_target_share': 0.005051405075429985,
            'boss_edamage_cadence_uptime_factor': 1.0,
            'boss_edamage_reliability_factor': 1.0,
            'boss_edamage_semantic_normalizer': 1.0,
        },
        loadout_policy_presets=('GC Max Waves',),
        dissonance_run_categories=('defense',),
    )

    assert 'comparison' in matrix
    comparison = matrix['comparison']
    assert comparison['label'] == 'bridge_assumptions'
    assert comparison['scenario_runtime_inputs']['boss_edamage_target_share'] == pytest.approx(0.005051405075429985)
    wide = comparison['wide_rows'][0]
    assert wide['defense_default_wave'] >= 4500
    assert wide['defense_comparison_wave'] >= 4500
    assert wide['defense_delta_wave'] == wide['defense_comparison_wave'] - wide['defense_default_wave']
    assert wide['defense_delta_wave'] <= 0
    comparison_candidate = comparison['matrix']['rows'][0]['candidate_results'][0]
    assert comparison_candidate['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'


@pytest.mark.live
def test_boss_wave_milestone_matrix_can_compare_default_to_pressure_factor_assumption():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out'),
        tiers=(14,),
        end_wave=5000,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        comparison_scenario_runtime_inputs={'boss_wave_pressure_factor': 1.25},
        comparison_label='pressure_factor_assumptions',
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('utility',),
        align_clean_reference_rows=False,
    )

    comparison = matrix['comparison']
    assert comparison['label'] == 'pressure_factor_assumptions'
    assert 'boss_wave_pressure_factor' not in matrix['scenario_runtime_inputs']
    assert comparison['scenario_runtime_inputs']['boss_wave_pressure_factor'] == pytest.approx(1.25)
    wide = comparison['wide_rows'][0]
    assert wide['utility_default_wave'] == matrix['rows'][0]['best_selected_max_wave']
    assert wide['utility_comparison_wave'] < wide['utility_default_wave']
    assert wide['utility_delta_wave'] == wide['utility_comparison_wave'] - wide['utility_default_wave']
    assert wide['utility_default_calculated_wave'] == matrix['rows'][0]['best_calculated_selected_max_wave']
    assert wide['utility_comparison_calculated_wave'] == (
        comparison['matrix']['rows'][0]['best_calculated_selected_max_wave']
    )
    assert wide['utility_default_hit_by_hit_wave'] == matrix['wide_rows'][0]['utility_hit_by_hit_wave']
    assert wide['utility_comparison_hit_by_hit_wave'] == (
        comparison['matrix']['wide_rows'][0]['utility_hit_by_hit_wave']
    )
    assert wide['utility_default_contact_envelope_wave'] == matrix['wide_rows'][0]['utility_contact_envelope_wave']
    assert wide['utility_comparison_contact_envelope_wave'] == (
        comparison['matrix']['wide_rows'][0]['utility_contact_envelope_wave']
    )
    assert wide['utility_default_reference_nearest_lane'] == matrix['wide_rows'][0][
        'utility_reference_nearest_lane'
    ]
    assert wide['utility_comparison_reference_nearest_lane'] == comparison['matrix']['wide_rows'][0][
        'utility_reference_nearest_lane'
    ]
    assert wide['utility_default_reference_nearest_lane_wave'] == matrix['wide_rows'][0][
        'utility_reference_nearest_lane_wave'
    ]
    assert wide['utility_comparison_reference_nearest_lane_wave'] == comparison['matrix']['wide_rows'][0][
        'utility_reference_nearest_lane_wave'
    ]
    assert wide['utility_calculated_delta_wave'] == (
        wide['utility_comparison_calculated_wave'] - wide['utility_default_calculated_wave']
    )
    assert comparison['calculated_delta_summary']['row_count'] == 1
    assert comparison['calculated_delta_summary']['comparison_raw_wave_lower_count'] == 1
    assert comparison['calculated_delta_summary']['max_abs_calculated_delta_row'] == {
        'tier': 14,
        'tier_column': 'Tier 14',
        'dissonance_run_category': 'utility',
        'label': 'Utility Dissonant Run',
        'default_selected_wave': wide['utility_default_wave'],
        'comparison_selected_wave': wide['utility_comparison_wave'],
        'selected_delta_wave': wide['utility_delta_wave'],
        'default_calculated_wave': wide['utility_default_calculated_wave'],
        'comparison_calculated_wave': wide['utility_comparison_calculated_wave'],
        'calculated_delta_wave': wide['utility_calculated_delta_wave'],
        'default_calculated_delta_vs_reference_wave': wide[
            'utility_default_calculated_delta_vs_reference_wave'
        ],
        'comparison_calculated_delta_vs_reference_wave': wide[
            'utility_comparison_calculated_delta_vs_reference_wave'
        ],
        'default_calculated_to_reference_ratio': wide['utility_default_calculated_to_reference_ratio'],
        'comparison_calculated_to_reference_ratio': wide['utility_comparison_calculated_to_reference_ratio'],
    }
    comparison_candidate = comparison['matrix']['rows'][0]['candidate_results'][0]
    assert comparison_candidate['selected_max_wave'] == wide['utility_comparison_wave']
    assert comparison_candidate['non_boss_terminal_pressure_closure'] == {
        'closed': False,
        'mode': 'not_required',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': False,
        'boss_wave_pressure_factor': 1.25,
    }


@pytest.mark.live
def test_boss_wave_milestone_matrix_comparison_rows_keep_terminal_pressure_cap_metadata():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={'orb_boss_total_damage_pct': 6.0},
        comparison_scenario_runtime_inputs={
            'boss_edamage_target_share': 0.01,
            'boss_edamage_cadence_uptime_factor': 1.0,
            'boss_edamage_reliability_factor': 1.0,
            'boss_edamage_semantic_normalizer': 1.0,
        },
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('ultimate_weapons',),
    )

    comparison_row = matrix['comparison']['wide_rows'][0]
    assert comparison_row['ultimate_weapons_default_wave'] == 780
    assert comparison_row['ultimate_weapons_comparison_wave'] == 780
    assert comparison_row['ultimate_weapons_default_terminal_pressure_limiter'] == (
        'unsupported_pressure_empirical_reference'
    )
    assert comparison_row['ultimate_weapons_comparison_terminal_pressure_limiter'] == (
        'unsupported_pressure_empirical_reference'
    )
    assert comparison_row['ultimate_weapons_default_terminal_pressure_reference_status'] == (
        'empirical_reference_limited'
    )
    assert comparison_row['ultimate_weapons_comparison_terminal_pressure_reference_status'] == (
        'empirical_reference_limited'
    )
    assert comparison_row['ultimate_weapons_default_unsupported_pressure_reference_limited'] is True
    assert comparison_row['ultimate_weapons_comparison_unsupported_pressure_reference_limited'] is True
    assert comparison_row['ultimate_weapons_default_unsupported_pressure_uncapped_wave'] > 780
    assert comparison_row['ultimate_weapons_comparison_unsupported_pressure_uncapped_wave'] > 780


@pytest.mark.live
def test_boss_wave_milestone_matrix_pressure_factor_closes_unsupported_terminal_pressure_as_approximation():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_total_damage_pct': 6.0,
            'boss_wave_pressure_factor': 1.25,
        },
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('ultimate_weapons',),
    )

    row = matrix['rows'][0]
    candidate = row['candidate_results'][0]
    certification = matrix['model_certification']
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in candidate['model_completion_blockers']
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in row['model_completion_blockers']
    assert 'source_owned_non_boss_terminal_pressure_formulas' not in certification['model_completion_blockers']
    assert certification['runtime_override_closure']['non_boss_terminal_pressure'] is True
    assert certification['non_boss_terminal_pressure_closure']['mode'] == 'boss_wave_pressure_factor_approximation'
    assert certification['non_boss_terminal_pressure_closure']['boss_wave_pressure_factor'] == pytest.approx(1.25)
    assert certification['terminal_pressure_runtime_override_status']['closed'] is False
    assert certification['unsupported_terminal_pressures']


def test_boss_wave_empirical_pressure_transform_approval_removes_only_operator_blocker():
    from app.pipeline import _boss_wave_pressure_driver_empirical_transform_candidate

    calibration_rows = [
        {
            'tier': tier,
            'wave': 2000 + tier * 100,
            'normal_spawn_rate_pressure_index': 40.0 + tier,
            'wave_accelerator_spawn_rate_acceleration': 1.8,
            'elite_pressure_index_pct': 66.0,
            'fleet_events_per_wave_pressure': 0.001,
            'pressure_factor_hint': 1.0 + tier / 20.0,
        }
        for tier in range(1, 7)
    ]

    default = _boss_wave_pressure_driver_empirical_transform_candidate(calibration_rows)
    approved = _boss_wave_pressure_driver_empirical_transform_candidate(
        calibration_rows,
        approve_empirical_transform_default=True,
    )

    assert default['promotion_readiness']['operator_approval_status'] == 'not_approved'
    assert approved['promotion_readiness']['operator_approval_status'] == (
        'approved_explicit_runtime_input'
    )
    assert approved['promotion_readiness']['default_pressure_factor_derived'] is False
    assert approved['promotion_status'] == 'not_promoted'
    assert 'operator_has_not_approved_empirical_transform_as_default' in default[
        'promotion_readiness'
    ]['blocking_reasons']
    assert 'operator_has_not_approved_empirical_transform_as_default' not in approved[
        'promotion_readiness'
    ]['blocking_reasons']
    assert 'not_source_owned_terminal_pressure_formula' in approved[
        'promotion_readiness'
    ]['blocking_reasons']
    assert 'non_capped_dissonance_reference_validation_missing' in approved[
        'promotion_readiness'
    ]['blocking_reasons']


@pytest.mark.live
def test_boss_wave_milestone_matrix_pressure_factor_closes_all_dissonant_categories():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_milestone_matrix

    matrix = build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_total_damage_pct': 6.0,
            'boss_wave_pressure_factor': 1.25,
        },
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('none', 'attack', 'defense', 'utility', 'ultimate_weapons'),
    )

    assert len(matrix['rows']) == 5
    assert matrix['model_completion_blockers'] == []
    assert matrix['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert matrix['accepted_approximation_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': 1.25,
        'replaced_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
        'certification_effect': 'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation',
        'certified_full_max_wave_model': False,
    }
    assert {row['dissonance_run_category'] for row in matrix['rows']} == {
        'none',
        'attack',
        'defense',
        'utility',
        'ultimate_weapons',
    }
    for row in matrix['rows']:
        assert row['best_status'] == 'complete'
        assert row['model_completion_blockers'] == []
        assert row['model_closure_status'] == 'closed_with_pressure_factor_approximation'
        assert row['effective_model_closure']['non_boss_terminal_pressure'] is True
        assert row['non_boss_terminal_pressure_closure'] == {
            'closed': True,
            'mode': 'boss_wave_pressure_factor_approximation',
            'exact_terminal_override_closed': False,
            'pressure_factor_approximation_closed': True,
            'boss_wave_pressure_factor': 1.25,
        }
        assert row['unsupported_terminal_pressures']


@pytest.mark.live
def test_boss_wave_pressure_factor_review_default_approval_promotes_review_input(monkeypatch):
    import app.pipeline as pipeline_mod

    original_summary = pipeline_mod._boss_wave_matrix_model_accuracy_summary
    call_count = {'value': 0}

    def _summary_with_review_input(**kwargs):
        summary = original_summary(**kwargs)
        call_count['value'] += 1
        if call_count['value'] == 1:
            summary = dict(summary)
            summary['comparison_only_pressure_factor_inputs'] = {
                'boss_wave_pressure_factor': 1.25,
            }
            summary['status'] = 'default_partial_comparison_calibration_available'
            summary['operator_next_step'] = (
                'apply_comparison_only_pressure_factor_input_to_review_approximation'
            )
        return summary

    monkeypatch.setattr(
        pipeline_mod,
        '_boss_wave_matrix_model_accuracy_summary',
        _summary_with_review_input,
    )

    matrix = pipeline_mod.build_boss_wave_milestone_matrix(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', runtime_state_overlay='disco_respec_2026_06_10'),
        tiers=(16,),
        end_wave=1600,
        boss_wave_step=10,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_total_damage_pct': 6.0,
            'approve_boss_wave_pressure_factor_review_default': 1.0,
        },
        loadout_policy_presets=('eHP Max Waves',),
        dissonance_run_categories=('utility',),
    )

    assert matrix['scenario_runtime_inputs']['boss_wave_pressure_factor'] == pytest.approx(1.25)
    assert 'approve_boss_wave_pressure_factor_review_default' not in matrix['scenario_runtime_inputs']
    assert matrix['model_completion_blockers'] == []
    assert matrix['model_closure_status'] == 'closed_with_pressure_factor_approximation'
    assert matrix['accepted_approximation_closure']['closed'] is True
    assert matrix['accepted_approximation_closure']['mode'] == 'boss_wave_pressure_factor_approximation'
    assert matrix['accepted_approximation_closure']['boss_wave_pressure_factor'] == pytest.approx(1.25)
    assert matrix['approved_pressure_factor_review_default'] == {
        'status': 'approved_explicit_runtime_input',
        'approval_runtime_input': 'approve_boss_wave_pressure_factor_review_default',
        'promoted_runtime_input': 'boss_wave_pressure_factor',
        'boss_wave_pressure_factor': 1.25,
        'source': 'model_accuracy_summary.comparison_only_pressure_factor_inputs',
        'certification_effect': (
            'closes_source_owned_non_boss_terminal_pressure_formulas_as_approved_approximation'
        ),
        'default_artifact_policy': 'not_applied_without_explicit_runtime_approval',
    }


def test_goal_readiness_accepts_only_approved_boss_pressure_factor_closure():
    from app.pipeline import _tower_goal_readiness_summary

    readiness = _tower_goal_readiness_summary(
        {
            'boss_wave_milestone_matrix': {
                'model_closure_status': 'closed_with_pressure_factor_approximation',
                'certified_full_max_wave_model': False,
                'model_completion_blockers': [],
                'accepted_approximation_closure': {
                    'closed': True,
                    'mode': 'boss_wave_pressure_factor_approximation',
                    'boss_wave_pressure_factor': 2.606384292771721,
                },
                'non_boss_terminal_pressure_closure': {
                    'pressure_factor_approximation_closed': True,
                    'boss_wave_pressure_factor': 2.606384292771721,
                },
                'approved_pressure_factor_review_default': {
                    'status': 'approved_explicit_runtime_input',
                    'approval_runtime_input': (
                        'approve_boss_wave_pressure_factor_review_default'
                    ),
                    'promoted_runtime_input': 'boss_wave_pressure_factor',
                    'boss_wave_pressure_factor': 2.606384292771721,
                },
            },
        }
    )

    rows = {row['id']: row for row in readiness['requirements']}
    boss_row = rows['boss_waves_full_accuracy']
    assert boss_row['status'] == 'proven_with_approved_non_boss_pressure_approximation'
    assert boss_row['approved_non_boss_terminal_pressure_closure'] is True
    assert 'boss_waves_full_accuracy' not in readiness['remaining_blockers']


def test_boss_wave_matrix_comparison_inputs_from_cli_args():
    from types import SimpleNamespace

    from app.pipeline import (
        _boss_wave_matrix_comparison_inputs_from_args,
        _boss_wave_matrix_comparison_label_from_args,
        _boss_wave_matrix_runtime_inputs_from_args,
    )

    assert _boss_wave_matrix_comparison_inputs_from_args(SimpleNamespace()) is None
    assert _boss_wave_matrix_comparison_label_from_args(SimpleNamespace()) == 'bridge_assumptions'
    assert _boss_wave_matrix_runtime_inputs_from_args(SimpleNamespace()) is None
    payload = _boss_wave_matrix_comparison_inputs_from_args(
        SimpleNamespace(
            boss_wave_bridge_target_share=0.5,
            boss_wave_bridge_cadence_uptime=0.6,
            boss_wave_bridge_reliability=0.7,
            boss_wave_bridge_semantic_normalizer=0.8,
            boss_wave_comparison_pressure_factor=1.0,
        )
    )
    assert payload == {
        'boss_edamage_target_share': 0.5,
        'boss_edamage_cadence_uptime_factor': 0.6,
        'boss_edamage_reliability_factor': 0.7,
        'boss_edamage_semantic_normalizer': 0.8,
    }
    assert (
        _boss_wave_matrix_comparison_label_from_args(
            SimpleNamespace(
                boss_wave_bridge_target_share=0.5,
                boss_wave_bridge_cadence_uptime=0.6,
                boss_wave_bridge_reliability=0.7,
                boss_wave_bridge_semantic_normalizer=0.8,
                boss_wave_comparison_pressure_factor=1.0,
            )
        )
        == 'bridge_assumptions'
    )
    pressure_payload = _boss_wave_matrix_comparison_inputs_from_args(
        SimpleNamespace(boss_wave_comparison_pressure_factor=1.25)
    )
    assert pressure_payload == {'boss_wave_pressure_factor': 1.25}
    assert (
        _boss_wave_matrix_comparison_label_from_args(SimpleNamespace(boss_wave_comparison_pressure_factor=1.25))
        == 'pressure_factor_assumptions'
    )
    assert (
        _boss_wave_matrix_comparison_label_from_args(
            SimpleNamespace(
                boss_wave_bridge_target_share=0.5,
                boss_wave_comparison_pressure_factor=1.25,
            )
        )
        == 'bridge_and_pressure_factor_assumptions'
    )
    terminal_payload = _boss_wave_matrix_comparison_inputs_from_args(
        SimpleNamespace(
            boss_wave_comparison_fleet_terminal_max_wave=900.0,
            boss_wave_comparison_elite_terminal_max_wave=901.0,
            boss_wave_comparison_protector_terminal_max_wave=902.0,
            boss_wave_comparison_armored_terminal_max_wave=903.0,
            boss_wave_comparison_boss_terminal_max_wave=904.0,
        )
    )
    assert terminal_payload == {
        'fleet_terminal_max_wave': 900.0,
        'elite_terminal_max_wave': 901.0,
        'protector_terminal_max_wave': 902.0,
        'armored_terminal_max_wave': 903.0,
        'boss_terminal_max_wave': 904.0,
    }
    assert (
        _boss_wave_matrix_comparison_label_from_args(
            SimpleNamespace(boss_wave_comparison_fleet_terminal_max_wave=900.0)
        )
        == 'terminal_pressure_assumptions'
    )
    assert (
        _boss_wave_matrix_comparison_label_from_args(
            SimpleNamespace(
                boss_wave_bridge_target_share=0.5,
                boss_wave_comparison_pressure_factor=1.25,
                boss_wave_comparison_fleet_terminal_max_wave=900.0,
            )
        )
        == 'bridge_and_pressure_factor_and_terminal_pressure_assumptions'
    )
    runtime_payload = _boss_wave_matrix_runtime_inputs_from_args(
        SimpleNamespace(
            boss_wave_contact_time_seconds=10.0,
            boss_wave_orb_boss_total_damage_pct=6.0,
            boss_wave_pressure_factor=1.25,
            approve_boss_wave_pressure_factor_review_default=True,
            boss_wave_flame_bot_boss_hit_chance_pct=50.0,
            boss_wave_flame_bot_damage_reduction_pct=95.0,
            boss_wave_flame_bot_duration_seconds=21.0,
            boss_wave_flame_bot_cooldown_seconds=67.0,
            boss_wave_fleet_terminal_max_wave=900.0,
            boss_wave_elite_terminal_max_wave=901.0,
            boss_wave_protector_terminal_max_wave=902.0,
            boss_wave_armored_terminal_max_wave=903.0,
            boss_wave_boss_terminal_max_wave=904.0,
        )
    )
    assert runtime_payload == {
        'boss_time_to_contact_seconds': 10.0,
        'orb_boss_total_damage_pct': 6.0,
        'boss_wave_pressure_factor': 1.25,
        'approve_boss_wave_pressure_factor_review_default': 1.0,
        'flame_bot_boss_hit_chance_pct': 50.0,
        'flame_bot_damage_reduction_pct': 95.0,
        'flame_bot_duration_seconds': 21.0,
        'flame_bot_cooldown_seconds': 67.0,
        'fleet_terminal_max_wave': 900.0,
        'elite_terminal_max_wave': 901.0,
        'protector_terminal_max_wave': 902.0,
        'armored_terminal_max_wave': 903.0,
        'boss_terminal_max_wave': 904.0,
    }


@pytest.mark.live
def test_boss_wave_explicit_gc_damage_bridge_enables_pre_contact_selection_without_defaulting_to_calibration():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        perk_mode='runtime_timeline',
        perk_policy_preset='GC Max Waves',
    )
    default_payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=5200,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
        dissonance_run_category='defense',
    )
    default_primitives = default_payload['diagnostics']['replacement_primitive_inputs']['values']
    assert default_primitives['boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
    assert default_primitives['gc_boss_damage_source'] == default_primitives['boss_damage_source']
    assert default_primitives['qe_boss_applicable_cl_only_damage_per_second'] == pytest.approx(
        default_primitives['chain_lightning_boss_damage_per_second']
    )
    assert default_primitives['edamage_boss_base_damage_per_second'] == pytest.approx(
        default_primitives['edamage_ep']
    )
    assert default_primitives['edamage_boss_spotlight_factor'] >= 1.0
    assert default_primitives['edamage_boss_acp_factor'] == pytest.approx(1.0)
    assert default_primitives['boss_damage_per_second'] == pytest.approx(
        default_primitives['edamage_ep'] * default_primitives['edamage_boss_runtime_factor']
    )
    assert default_primitives['gc_boss_damage_per_second'] == pytest.approx(default_primitives['boss_damage_per_second'])
    assert default_payload['summary']['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert default_payload['summary']['pre_contact_boss_kill_max_wave'] >= 4500
    assert default_payload['summary']['gc_pre_contact_max_wave'] == default_payload['summary']['pre_contact_boss_kill_max_wave']
    assert default_payload['summary']['selected_max_wave'] >= 4500

    bridged_payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=5200,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
            'boss_applicable_damage_factor': 0.005051405075429985,
        },
        dissonance_run_category='defense',
    )
    bridged_primitives = bridged_payload['diagnostics']['replacement_primitive_inputs']['values']
    assert bridged_primitives['boss_damage_source'] == 'runtime_input_edamage_ep_times_boss_applicable_damage_factor'
    assert bridged_primitives['gc_boss_damage_source'] == bridged_primitives['boss_damage_source']
    assert bridged_primitives['boss_damage_per_second'] > bridged_primitives['chain_lightning_boss_damage_per_second']
    assert bridged_primitives['gc_boss_damage_per_second'] == pytest.approx(bridged_primitives['boss_damage_per_second'])
    assert bridged_primitives['wall_thorns_contact_damage_pct'] == pytest.approx(0.0)
    assert bridged_payload['diagnostics']['replacement_primitive_semantics_ledger']['primitives'][
        'module::Sharp Fortitude.wall_thorns_damage_increase_per_hit'
    ]['exact_value'] == pytest.approx(0.0)
    assert all(
        row['boss_wall_thorns_damage_to_boss_pct'] == pytest.approx(0.0)
        for row in bridged_payload['operator_rows']
    )
    assert (
        'source_owned_full_boss_applicable_damage_semantics'
        not in bridged_payload['diagnostics']['model_certification']['model_completion_blockers']
    )
    assert bridged_payload['diagnostics']['model_certification']['runtime_override_closure']['boss_applicable_damage_semantics'] is True
    assert bridged_payload['diagnostics']['model_certification']['runtime_override_closure']['gc_boss_applicable_damage_semantics'] is True
    assert bridged_payload['summary']['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert bridged_payload['summary']['selected_loadout_type'] == 'gc'
    assert bridged_payload['summary']['selected_max_wave'] >= 4500

    decomposed_payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=5200,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
            'boss_edamage_target_share': 0.005051405075429985,
            'boss_edamage_cadence_uptime_factor': 1.0,
            'boss_edamage_reliability_factor': 1.0,
            'boss_edamage_semantic_normalizer': 1.0,
        },
        dissonance_run_category='defense',
    )
    decomposed_primitives = decomposed_payload['diagnostics']['replacement_primitive_inputs']['values']
    assert decomposed_primitives['boss_damage_source'] == 'runtime_input_edamage_ep_times_decomposed_boss_bridge'
    assert decomposed_primitives['gc_boss_damage_source'] == decomposed_primitives['boss_damage_source']
    assert decomposed_primitives['boss_edamage_decomposed_bridge_factor'] == pytest.approx(0.005051405075429985)
    assert decomposed_primitives['boss_damage_per_second'] == pytest.approx(
        bridged_primitives['boss_damage_per_second']
    )
    assert decomposed_primitives['gc_boss_damage_per_second'] == pytest.approx(decomposed_primitives['boss_damage_per_second'])
    assert decomposed_payload['summary']['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert decomposed_payload['summary']['selected_loadout_type'] == 'gc'

    with pytest.raises(ValueError, match='requires all component factors'):
        build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=5200,
            boss_wave_step=10,
            stop_on_failure=False,
            scenario_runtime_inputs={
                'boss_time_to_contact_seconds': 10.0,
                'orb_boss_total_damage_pct': 6.0,
                'boss_edamage_target_share': 0.005051405075429985,
            },
            dissonance_run_category='defense',
        )

    attack_bridged_payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=5200,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
            'boss_applicable_damage_factor': 0.005051405075429985,
        },
        dissonance_run_category='attack',
    )
    attack_summary = attack_bridged_payload['summary']
    assert attack_summary['pre_contact_boss_kill_max_wave'] == 0
    assert attack_summary['gc_pre_contact_max_wave'] == attack_summary['pre_contact_boss_kill_max_wave']
    assert attack_summary['contact_envelope_max_wave'] > 0
    assert attack_summary['selected_model'] == 'unified_hit_by_hit_boss_survival_under_attack_dissonance'
    assert attack_summary['selected_loadout_type'] == 'gc'
    assert attack_summary['selected_max_wave'] > attack_summary['pre_contact_boss_kill_max_wave']

    long_horizon_defense_payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=8000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 10.0,
            'orb_boss_total_damage_pct': 6.0,
            'boss_applicable_damage_factor': 0.005051405075429985,
        },
        dissonance_run_category='defense',
    )
    long_horizon_summary = long_horizon_defense_payload['summary']
    assert long_horizon_summary['status'] == 'complete'
    assert long_horizon_summary['post_failure_truncation_kind'] is None
    assert long_horizon_summary['first_unresolved_wave'] is None
    assert long_horizon_summary['selected_model'] == 'unified_hit_by_hit_boss_survival_under_defense_dissonance'
    assert long_horizon_summary['selected_loadout_type'] == 'gc'


@pytest.mark.live
def test_boss_wave_payload_without_contact_time_returns_structured_incomplete_when_allowed():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=50,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={},
    )

    summary = payload['summary']
    assert summary['status'] == 'complete'
    assert summary['failure_kind'] is None
    assert summary['first_unresolved_wave'] is None
    assert payload['diagnostics']['context_status'] == 'complete'
    contact_time = payload['diagnostics']['contact_time_contract']['boss_time_to_contact_seconds']
    assert contact_time['value'] > 2.0
    assert contact_time['source'] == 'derived_geometry_displayed_proxy_base_cf_slow_aura_energy_net'
    assert contact_time['ownership'] == 'runtime_input_override_or_simulator_derived_from_base_travel_and_slow_effects'
    assert contact_time['derived_by_simulator'] is True
    assert contact_time['required_for_self_closing_boss_waves'] is True
    assert contact_time['base_seconds_source'] == 'geometry_displayed_proxy_candidate'
    assert contact_time['geometry_path_distance_to_wall_displayed_candidate_m'] > 0.0

    stop_on_failure_payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=50,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={},
    )
    assert stop_on_failure_payload['summary']['status'] == 'complete'


@pytest.mark.live
def test_boss_wave_payload_uses_effective_bh_cf_state_and_perk_switches():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    runtime_inputs = {'boss_time_to_contact_seconds': 1.0}
    with_perks = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline', perk_state='on'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    primitives = with_perks['diagnostics']['replacement_primitive_inputs']['values']
    assert 0.0 < primitives['black_hole_duration_seconds'] < primitives['black_hole_cooldown_seconds']
    assert 0.0 < primitives['chrono_field_duration_seconds'] <= primitives['chrono_field_cooldown_seconds']
    assert 0.0 < primitives['chrono_field_damage_reduction_pct'] <= 100.0

    rows_with_perks = with_perks['rows']
    assert rows_with_perks
    assert with_perks['summary']['status'] == 'complete'

    max_policy_request = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='max_progression_policy', perk_state='on'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    assert max_policy_request['diagnostics']['requested_perk_mode'] == 'max_progression_policy'
    assert max_policy_request['diagnostics']['perk_mode'] == 'max_progression_policy'
    assert max_policy_request['diagnostics']['perk_state'] == 'on'
    assert max_policy_request['diagnostics']['perk_contract_owner'] == 'request_policy_with_scenario_guard'
    assert max_policy_request['diagnostics']['perk_request_resolution'] == 'matched_request'
    assert max_policy_request['diagnostics']['perk_application_mode'] == 'max_progression_policy_static'
    assert max_policy_request['diagnostics']['perk_timeline_rows'] == 0
    assert max_policy_request['contract']['perk_timeline_mode'] == 'max_progression_policy_static'
    assert max_policy_request['rows'] != rows_with_perks

    none_requested = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='none', perk_state='on'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    off_requested = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline', perk_state='off'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    assert none_requested['diagnostics']['requested_perk_mode'] == 'none'
    assert off_requested['diagnostics']['requested_perk_state'] == 'off'
    assert none_requested['diagnostics']['perks_enabled'] is False
    assert off_requested['diagnostics']['perks_enabled'] is False
    assert none_requested['diagnostics']['perk_contract_owner'] == 'request_policy_with_scenario_guard'
    assert off_requested['diagnostics']['perk_contract_owner'] == 'request_policy_with_scenario_guard'
    assert none_requested['diagnostics']['perk_application_mode'] == 'disabled'
    assert off_requested['diagnostics']['perk_application_mode'] == 'disabled'
    assert none_requested['diagnostics']['perk_mode'] == 'none'
    assert off_requested['diagnostics']['perk_state'] == 'off'
    assert none_requested['diagnostics']['perk_request_resolution'] == 'matched_request'
    assert off_requested['diagnostics']['perk_request_resolution'] == 'matched_request'
    assert none_requested['diagnostics']['perk_mode_source'] == 'request_perk_mode_none_or_state_off'
    assert off_requested['diagnostics']['perk_mode_source'] == 'request_perk_mode_none_or_state_off'
    assert none_requested['diagnostics']['perk_state_source'] == 'request_perk_state_or_mode_disabled'
    assert off_requested['diagnostics']['perk_state_source'] == 'request_perk_state_or_mode_disabled'
    assert none_requested['rows'] != rows_with_perks
    assert off_requested['rows'] != rows_with_perks


@pytest.mark.live
def test_boss_wave_payload_threads_t14_battle_conditions_and_ignores_removed_final_dr_override():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='none')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=10,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 1.0},
    )
    scenario_surfaces = payload['diagnostics']['scenario_surfaces']
    assert scenario_surfaces['bc_plasma_cannon_resistance'] == pytest.approx(0.8)
    assert scenario_surfaces['bc_orb_resistance'] == pytest.approx(0.5)
    assert scenario_surfaces['bc_thorns_resistance'] == pytest.approx(0.8)
    assert payload['rows']
    assert payload['rows'][0]['boss_orb_damage_to_boss_pct'] == pytest.approx(6.0)
    assert payload['summary']['status'] == 'complete'
    dabs_semantics = payload['diagnostics']['replacement_primitive_semantics_ledger']['primitives']['state::tower.defense_absolute']
    assert dabs_semantics['exact_value'] >= 0.0
    assert dabs_semantics['boss_waves_source'] == 'qe.routing.resolve_checkpoint_surfaces(state::tower.defense_absolute)'

    overridden = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=10,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'black_hole_damage_reduction_pct': 0.0,
            'black_hole_duration_seconds': 0.0,
            'pbh_encounter_uptime_fraction': 0.0,
        },
    )
    bh_zeroed = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=10,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 1.0,
            'black_hole_damage_reduction_pct': 0.0,
            'black_hole_duration_seconds': 0.0,
            'pbh_encounter_uptime_fraction': 0.0,
        },
    )
    assert overridden['rows'] == bh_zeroed['rows']
    assert overridden['rows']
    sources = overridden['diagnostics']['replacement_primitive_semantics_ledger']['timed_dr_semantic_contract']['sources']
    assert sources['black_hole_pbh']['damage_reduction_pct'] == pytest.approx(0.0)
    assert sources['black_hole_pbh']['uptime_fraction'] == pytest.approx(0.0)
    assert 'final_dr_override' not in sources


def test_boss_wave_perk_state_is_owned_by_scenario_not_request():
    from app.pipeline import _resolve_boss_wave_run_context

    account_state = type(
        'State',
        (),
        {
            'active_perk_preset': None,
            'player_meta': {'Tourney League': 'Legends', 'Tournament Wave': '100'},
        },
    )()

    farming = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Farming',
        tier_number=14,
        checkpoint_every_bosses=1,
    )
    farming_t13 = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Farming',
        tier_number=13,
        checkpoint_every_bosses=1,
    )
    farming_t15 = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Farming',
        tier_number=15,
        checkpoint_every_bosses=1,
    )
    farming_t16 = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Farming',
        tier_number=16,
        checkpoint_every_bosses=1,
    )
    tournament = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Tourney',
        tier_number=14,
        checkpoint_every_bosses=1,
    )

    assert farming['mode_id'] == 'farming'
    assert farming['actual_boss_interval_waves'] == 9
    assert farming['actual_boss_interval_waves'] == farming['scenario_surfaces']['boss_wave_interval']
    assert farming['checkpoint_stride_waves'] == 9
    assert farming_t13['actual_boss_interval_waves'] == 10
    assert farming_t15['actual_boss_interval_waves'] == 8
    assert farming_t16['actual_boss_interval_waves'] == 7
    assert farming['perks_enabled'] is True
    assert farming['perk_state'] == 'on'
    assert farming['perk_mode'] == 'runtime_timeline'
    assert farming['perk_contract_owner'] == 'scenario_policy'
    assert farming['perk_mode_source'] == 'scenario_policy_tournament_none_other_runtime_timeline'
    assert farming['perk_state_source'] == 'scenario_policy_tournament_off_other_runs_on'
    assert tournament['mode_id'] == 'tournament'
    assert tournament['tier_number'] == 17
    assert tournament['requested_tier_number'] == 14
    assert tournament['tier_column'] == 'Tier 17'
    assert tournament['tournament_wave'] == 100
    assert tournament['tournament_wave_source'] == 'IDS::Player & Stuff'
    assert tournament['perks_enabled'] is False
    assert tournament['perk_state'] == 'off'
    assert tournament['perk_mode'] == 'none'
    assert tournament['perk_timeline_mode'] == 'disabled_by_tournament_scenario'

    tournament_override = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Tourney',
        tier_number=14,
        checkpoint_every_bosses=1,
        tournament_wave_override=250,
    )
    assert tournament_override['mode_id'] == 'tournament'
    assert tournament_override['league'] == 'Legends'
    assert tournament_override['tier_number'] == 17
    assert tournament_override['requested_tier_number'] == 14
    assert tournament_override['tournament_wave'] == 250
    assert tournament_override['tournament_wave_source'] == 'runtime_override'

    champion_account_state = type(
        'State',
        (),
        {
            'active_perk_preset': None,
            'player_meta': {'Tourney League': 'Champion', 'Tournament Wave': '100'},
        },
    )()
    champion_tournament = _resolve_boss_wave_run_context(
        champion_account_state,
        preset_name='Tourney',
        tier_number=14,
        checkpoint_every_bosses=1,
    )
    assert champion_tournament['league'] == 'Champion'
    assert champion_tournament['tier_number'] == 12
    assert champion_tournament['requested_tier_number'] == 14
    assert champion_tournament['tier_column'] == 'Tier 12'


def test_boss_wave_milestone_uses_default_workshop_levels_when_preset_lane_is_blank():
    from app.pipeline import _boss_wave_workshop_level_inputs, build_runtime_state, load_inputs

    bundle = load_inputs(ids_path=IDS_PATH)
    account_state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
        manual_inputs=bundle.manual_inputs,
    )

    levels, _max_levels = _boss_wave_workshop_level_inputs(account_state, preset_name='Milestone')

    assert levels['Enemy Attack Level Skip'] == account_state.workshop['Enemy Attack Level Skip'].preset_levels['Farming']
    assert levels['Wall Health'] == account_state.workshop['Wall Health'].preset_levels['Farming']


def test_default_workshop_order_routes_split_enemy_level_skip_tracks_to_utility():
    from qe.run_plan import default_category_track_order

    levels = {
        'Enemy Attack Level Skip': 350,
        'Enemy Health Level Skip': 340,
        'Package Chance': 60,
    }
    max_levels = {
        'Enemy Attack Level Skip': 699,
        'Enemy Health Level Skip': 699,
        'Package Chance': 60,
    }

    order = default_category_track_order(levels, max_levels)

    assert order['utility'] == (
        'Enemy Attack Level Skip',
        'Enemy Health Level Skip',
        'Package Chance',
    )


def test_build_common_trajectory_rederives_skip_from_row_workshop_levels():
    from qe.run_plan import CommonTrajectoryInputs, build_common_trajectory, workshop_value_for_level

    table = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=3,
            boss_interval_waves=1,
            checkpoint_every_bosses=1,
            attack_skip_chance=0.0,
            health_skip_chance=0.0,
            attack_skip_static_percent_points=2.5,
            attack_skip_multiplier=1.2,
            attack_skip_workshop_track='Enemy Attack Level Skip',
            attack_skip_workshop_baseline_level=10,
            health_skip_static_percent_points=1.5,
            health_skip_multiplier=1.1,
            health_skip_workshop_track='Enemy Health Level Skip',
            health_skip_workshop_baseline_level=10,
            free_upgrade_chance_by_category={'utility': 1.0},
            category_track_order={'utility': ('Enemy Attack Level Skip', 'Enemy Health Level Skip')},
            track_max_levels={'Enemy Attack Level Skip': 12, 'Enemy Health Level Skip': 12},
            workshop_levels={'Enemy Attack Level Skip': 10, 'Enemy Health Level Skip': 10},
        )
    )

    rows = table.rows
    attack_row1 = rows[0].common_inputs['attack_skip_chance']
    attack_row2 = rows[1].common_inputs['attack_skip_chance']
    health_row2 = rows[1].common_inputs['health_skip_chance']
    health_row3 = rows[2].common_inputs['health_skip_chance']

    expected_attack_row1 = ((2.5 + workshop_value_for_level('Enemy Attack Level Skip', 10)) * 1.2) / 100.0
    expected_attack_row2 = ((2.5 + workshop_value_for_level('Enemy Attack Level Skip', 11)) * 1.2) / 100.0
    expected_health_row2 = ((1.5 + workshop_value_for_level('Enemy Health Level Skip', 10)) * 1.1) / 100.0
    expected_health_row3 = ((1.5 + workshop_value_for_level('Enemy Health Level Skip', 11)) * 1.1) / 100.0

    assert attack_row1 == pytest.approx(expected_attack_row1)
    assert attack_row2 == pytest.approx(expected_attack_row2)
    assert health_row2 == pytest.approx(expected_health_row2)
    assert health_row3 == pytest.approx(expected_health_row3)
    assert attack_row2 > attack_row1
    assert health_row3 > health_row2


def test_perk_timeline_preview_override_is_validated_and_consumed_by_boss_waves():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload, build_perk_timeline_preview

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline')
    override = {
        'seed': 42,
        'target_wave': 50000,
        'banned_perks': [],
        'first_perk_choice': 'Defense Percent +4.00',
        'priority_order': ['Defense Percent +4.00'],
    }
    preview = build_perk_timeline_preview(request, perk_policy_override=override)

    assert preview['validation']['ok'] is True
    assert preview['validation']['ban_perks_used'] == 0
    assert preview['resolved_policy']['first_perk_choice'] == 'Defense Percent +4.00'
    assert preview['timeline'][0]['perk_taken'] == 'Defense Percent +4.00'
    assert preview['diagnostics']['uw_locked_perks_excluded']['Swamp Radius x1.5'] == 'Poison Swamp'

    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=210,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 1.0},
        perk_policy_override=override,
    )
    rows = {int(row['display_wave']): row for row in payload['rows']}
    assert payload['diagnostics']['perk_policy_override_active'] is True
    assert payload['diagnostics']['perk_policy_validation']['ok'] is True
    assert rows
    assert payload['summary']['status'] == 'complete'


def test_perk_timeline_preview_rejects_over_capacity_bans():
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    preview = build_perk_timeline_preview(
        request,
        perk_policy_override={
            'banned_perks': [
                'x1.15 Damage',
                'x1.20 Max Health',
                'x1.75 Health Regen',
                'Defense Percent +4.00',
                'Black Hole Duration +12.0s',
                'Chrono Field Duration +5s',
                'Golden Tower Bonus x1.5',
            ],
        },
    )

    assert preview['validation']['ok'] is False
    assert 'Ban Perks lab capacity is 6' in preview['validation']['errors'][0]


def test_named_perk_policy_presets_validate_and_keep_fixed_openers():
    from app.models import PipelineRunRequest
    from app.pipeline import BOSS_WAVE_PERK_POLICY_PRESETS, build_perk_timeline_preview

    for preset_name in BOSS_WAVE_PERK_POLICY_PRESETS:
        request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_policy_preset=preset_name)
        preview = build_perk_timeline_preview(request)
        priority = preview['resolved_policy']['priority_order']

        assert preview['policy_preset'] == preset_name
        assert preview['validation']['ok'] is True
        assert preview['resolved_policy']['first_perk_choice'] == 'Perk Wave Requirement -20.00%'
        assert priority[:2] == ['Perk Wave Requirement -20.00%', 'Increase Max Game Speed by +1.00']
        expected_generated = preset_name not in {'eHP Farming', 'GC Farming'}
        assert preview['context']['policy_generated_from_goal_matrix'] is expected_generated
        assert len(preview['resolved_policy']['banned_perks']) == preview['resolved_policy']['ban_perks_capacity']
        if expected_generated:
            assert preview['context']['generated_policy_context']['generator'] == 'goal_benefit_matrix_v1'
            matrix = preview['context']['generated_policy_context']['perk_goal_benefit_matrix']
            assert matrix
            assert {preset_name, 'perk'} <= set(matrix[0])
        else:
            assert preview['context']['generated_policy_context'] == {}
        assert preview['timeline'][0]['perk_taken'] == 'Perk Wave Requirement -20.00%'


def test_named_perk_policy_presets_have_source_and_snapshot_priority_bans():
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview

    expected = {
        'eHP Max Waves': {
            'generated': True,
            'priority_order': [
                'Perk Wave Requirement -20.00%',
                'Increase Max Game Speed by +1.00',
                'Tower Health Regen x8.00, But Tower Max Max Health -60%',
                'x1.75 Health Regen',
                'x1.20 Max Health',
                'Defense Percent +4.00',
                'Free Upgrade Chance for All +5.0%',
                'Enemies Damage -50%, but Tower Damage -50%',
                '+1 Wave on Death Wave',
                'Black Hole Duration +12.0s',
                'Orbs +1',
                'Chrono Field Duration +5s',
                'x1.15 Damage',
                'x1.15 Defense Absolute',
                'Boss Health -70%, But Boss Speed +50%',
            ],
            'banned_perks': [
                'x1.50 Tower Damage, but Bosses Have 8x Health',
                'Enemies Speed -40%, But Enemies Damage x2.5',
                'x1.80 coins, but Tower Max Health -70%',
                'Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%',
                'Interest x1.50',
                'Land Mine Damage x3.50',
            ],
        },
        'eHP Farming': {
            'generated': False,
            'priority_order': [
                'Perk Wave Requirement -20.00%',
                'Increase Max Game Speed by +1.00',
                'x1.80 coins, but Tower Max Health -70%',
                'Golden Tower Bonus x1.5',
                'Black Hole Duration +12.0s',
                '+1 Wave on Death Wave',
                'x1.15 All Coin Bonuses',
                'Free Upgrade Chance for All +5.0%',
                'Enemies Damage -50%, but Tower Damage -50%',
                'Tower Health Regen x8.00, But Tower Max Max Health -60%',
                'Defense Percent +4.00',
                'x1.75 Health Regen',
                'x1.20 Max Health',
            ],
            'banned_perks': [
                'Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%',
                'Interest x1.50',
                'Land Mine Damage x3.50',
                'x1.15 Defense Absolute',
                'Enemies Speed -40%, But Enemies Damage x2.5',
                'x1.15 Cash Bonus',
            ],
        },
        'GC Max Waves': {
            'generated': True,
            'priority_order': [
                'Perk Wave Requirement -20.00%',
                'Increase Max Game Speed by +1.00',
                'Bounce Shot +2',
                'x1.15 Damage',
                'Chain Lightning Damage x2',
                'Boss Health -70%, But Boss Speed +50%',
                'Spotlight Damage Bonus x1.5',
                'Orbs +1',
                'Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%',
                'Black Hole Duration +12.0s',
                'Chrono Field Duration +5s',
                'x1.20 Max Health',
            ],
            'banned_perks': [
                'x1.50 Tower Damage, but Bosses Have 8x Health',
                'Enemies Damage -50%, but Tower Damage -50%',
                'Enemies Speed -40%, But Enemies Damage x2.5',
                'Interest x1.50',
                'Land Mine Damage x3.50',
                'x1.15 Cash Bonus',
            ],
        },
        'GC Farming': {
            'generated': False,
            'priority_order': [
                'Perk Wave Requirement -20.00%',
                'Increase Max Game Speed by +1.00',
                'x1.80 coins, but Tower Max Health -70%',
                'Golden Tower Bonus x1.5',
                'Black Hole Duration +12.0s',
                '+1 Wave on Death Wave',
                'x1.15 All Coin Bonuses',
                'Free Upgrade Chance for All +5.0%',
                'x1.15 Damage',
                'Spotlight Damage Bonus x1.5',
                'Chain Lightning Damage x2',
                'Boss Health -70%, But Boss Speed +50%',
                'Bounce Shot +2',
            ],
            'banned_perks': [
                'Interest x1.50',
                'Land Mine Damage x3.50',
                'x1.15 Defense Absolute',
                'Enemies Speed -40%, But Enemies Damage x2.5',
                'Tower Health Regen x8.00, But Tower Max Max Health -60%',
                'x1.15 Cash Bonus',
            ],
        },
    }

    for preset_name, snapshot in expected.items():
        preview = build_perk_timeline_preview(
            PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_policy_preset=preset_name)
        )
        assert preview['context']['policy_generated_from_goal_matrix'] is snapshot['generated']
        if snapshot['generated']:
            assert preview['context']['generated_policy_context']['generator'] == 'goal_benefit_matrix_v1'
        else:
            assert preview['context']['policy_strategy'] == 'manual_explicit_v1'
            assert preview['context']['policy_source_note']
        assert preview['resolved_policy']['priority_order'] == snapshot['priority_order']
        assert preview['resolved_policy']['banned_perks'] == snapshot['banned_perks']


def test_goal_perk_policy_matrix_ranks_goal_specific_perks():
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview

    ehp = build_perk_timeline_preview(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_policy_preset='eHP Max Waves')
    )
    gc = build_perk_timeline_preview(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_policy_preset='GC Max Waves')
    )

    ehp_priority = ehp['resolved_policy']['priority_order']
    gc_priority = gc['resolved_policy']['priority_order']
    assert ehp_priority[:2] == ['Perk Wave Requirement -20.00%', 'Increase Max Game Speed by +1.00']
    assert gc_priority[:2] == ['Perk Wave Requirement -20.00%', 'Increase Max Game Speed by +1.00']
    assert ehp_priority.index('x1.20 Max Health') < ehp_priority.index('x1.15 Damage')
    assert gc_priority.index('x1.15 Damage') < gc_priority.index('x1.15 All Coin Bonuses') if 'x1.15 All Coin Bonuses' in gc_priority else True
    assert 'x1.50 Tower Damage, but Bosses Have 8x Health' in gc['resolved_policy']['banned_perks']
    assert 'Chain Lightning Damage x2' not in ehp['resolved_policy']['banned_perks']


def test_manual_gc_farming_perk_policy_mirrors_farming_spine_with_damage_picks():
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview

    preview = build_perk_timeline_preview(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_policy_preset='GC Farming')
    )
    priority = preview['resolved_policy']['priority_order']
    banned = preview['resolved_policy']['banned_perks']

    assert preview['validation']['ok'] is True
    assert preview['context']['policy_generated_from_goal_matrix'] is False
    assert priority[:8] == [
        'Perk Wave Requirement -20.00%',
        'Increase Max Game Speed by +1.00',
        'x1.80 coins, but Tower Max Health -70%',
        'Golden Tower Bonus x1.5',
        'Black Hole Duration +12.0s',
        '+1 Wave on Death Wave',
        'x1.15 All Coin Bonuses',
        'Free Upgrade Chance for All +5.0%',
    ]
    assert priority[8:] == [
        'x1.15 Damage',
        'Spotlight Damage Bonus x1.5',
        'Chain Lightning Damage x2',
        'Boss Health -70%, But Boss Speed +50%',
        'Bounce Shot +2',
    ]
    assert 'Tower Health Regen x8.00, But Tower Max Max Health -60%' in banned
    assert 'x1.20 Max Health' not in priority
    assert 'x1.75 Health Regen' not in priority


def test_boss_wave_gc_loadout_routes_tourney_loadout_and_energy_net_cl_primitives():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(
            ids=IDS_PATH,
            out=ROOT / 'out',
            perk_mode='max_progression_policy',
            perk_policy_preset='GC Max Waves',
        ),
        preset_name='Farming',
        tier_number=14,
        end_wave=1000,
        boss_wave_step=10,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 10.0, 'orb_boss_total_damage_pct': 6.0},
    )

    primitives = payload['diagnostics']['replacement_primitive_inputs']['values']
    assert payload['diagnostics']['loadout_profile_preset'] == 'Tourney'
    assert primitives['chain_lightning_boss_damage_per_second'] > 0.0
    assert primitives['boss_damage_source'] == 'qe_derived_edamage_ep_boss_exposure_model'
    assert primitives['gc_boss_damage_source'] == primitives['boss_damage_source']
    assert primitives['qe_boss_applicable_cl_only_damage_per_second'] == pytest.approx(
        primitives['chain_lightning_boss_damage_per_second']
    )
    assert primitives['edamage_boss_base_damage_per_second'] == pytest.approx(primitives['edamage_ep'])
    assert primitives['edamage_boss_base_cl_damage_per_second'] == pytest.approx(
        primitives['chain_lightning_boss_damage_per_second']
    )
    assert primitives['om_chip_equipped'] is True
    assert primitives['edamage_boss_spotlight_exposure_fraction'] == pytest.approx(1.0)
    assert primitives['edamage_boss_spotlight_factor'] == pytest.approx(
        primitives['spotlight_bonus_multiplier']
    )
    assert primitives['edamage_boss_acp_factor'] > 1.0
    assert primitives['boss_damage_per_second'] == pytest.approx(
        primitives['edamage_ep'] * primitives['edamage_boss_runtime_factor']
    )
    assert primitives['gc_boss_damage_per_second'] == pytest.approx(primitives['boss_damage_per_second'])
    assert primitives['edamage_boss_contact_time_exposure_factor'] == pytest.approx(5.0)
    assert primitives['edamage_boss_pre_contact_energy_net_boosted_seconds'] == pytest.approx(10.0)
    assert primitives['edamage_boss_pre_contact_timed_window_damage'] == pytest.approx(
        primitives['boss_damage_per_second']
        * (
            primitives['boss_time_to_contact_seconds']
            + (
                primitives['energy_net_mastery_multiplier'] - 1.0
            )
            * primitives['edamage_boss_pre_contact_energy_net_boosted_seconds']
        )
    )
    assert primitives['energy_net_duration_seconds'] > 0.0
    assert primitives['energy_net_mastery_multiplier'] > 1.0
    assert primitives['energy_net_damage_multiplier_duration_seconds'] >= primitives['energy_net_duration_seconds']
    assert payload['rows'][0]['tower_damage_per_second'] == pytest.approx(primitives['boss_damage_per_second'])
    assert 'boss_killed_before_contact' in payload['rows'][0]
    assert payload['summary']['selected_model'] == 'unified_hit_by_hit_boss_survival'
    assert payload['summary']['selected_loadout_type'] == 'gc'
    assert payload['summary']['pre_contact_boss_kill_max_wave'] >= 0
    assert payload['summary']['gc_pre_contact_max_wave'] >= 0
    assert payload['summary']['gc_pre_contact_max_wave'] == payload['summary']['pre_contact_boss_kill_max_wave']


def test_save_perk_policy_override_persists_to_manual_inputs(tmp_path):
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview, save_perk_policy_override

    manual_inputs = tmp_path / 'manual_inputs.yaml'
    manual_inputs.write_text(
        yaml.safe_dump(
            {
                'loadout': {},
                'perk_config': {'perk_presets': {}, 'active_perk_preset': None},
                'perk_policy': {
                    'seed': 1,
                    'target_wave': 1000,
                    'priority_order': ['Perk Wave Requirement -20.00%'],
                    'first_perk_choice': 'Perk Wave Requirement -20.00%',
                    'banned_perk_aliases': ['TO3'],
                    'banned_perks': ['Enemies Speed -40%, But Enemies Damage x2.5'],
                },
            },
            sort_keys=False,
        ),
        encoding='utf-8',
    )
    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', manual_inputs=manual_inputs)
    override = {
        'seed': 42,
        'target_wave': 50000,
        'banned_perks': [],
        'first_perk_choice': 'Defense Percent +4.00',
        'priority_order': ['Defense Percent +4.00'],
    }

    save_result = save_perk_policy_override(request, perk_policy_override=override)
    saved_yaml = yaml.safe_load(manual_inputs.read_text(encoding='utf-8'))
    saved_policy = saved_yaml['perk_policy']

    assert save_result['manual_inputs_path'] == str(manual_inputs)
    assert saved_policy['seed'] == 42
    assert saved_policy['target_wave'] == 50000
    assert saved_policy['banned_perks'] == []
    assert 'banned_perk_aliases' not in saved_policy
    assert saved_policy['first_perk_choice'] == 'Defense Percent +4.00'
    assert saved_policy['priority_order'] == ['Defense Percent +4.00']

    preview = build_perk_timeline_preview(request)
    assert preview['validation']['ok'] is True
    assert preview['resolved_policy']['first_perk_choice'] == 'Defense Percent +4.00'
    assert preview['timeline'][0]['perk_taken'] == 'Defense Percent +4.00'


def test_boss_wave_perk_timeline_uses_ids_labs_first_choice_and_exports_wall_contributions():
    from app import pipeline as pipeline_mod
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy

    bundle = pipeline_mod.load_inputs(ids_path=IDS_PATH)
    payload, context = pipeline_mod._perk_policy_context(bundle.ids_raw, getattr(bundle, 'perk_policy', {}) or {})
    assert context['selected_policy_preset'] == 'eHP Farming'
    assert payload['waves_required_lab'] == 13
    assert payload['standard_perk_bonus'] == pytest.approx(0.25)
    assert payload['perk_option_quantity'] == 2
    assert context['ban_perks_capacity_ids'] == 6
    assert context['policy_generated_from_goal_matrix'] is False
    assert payload['banned_perks'] == [
        'Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%',
        'Interest x1.50',
        'Land Mine Damage x3.50',
        'x1.15 Defense Absolute',
        'Enemies Speed -40%, But Enemies Damage x2.5',
        'x1.15 Cash Bonus',
    ]
    assert payload['priority_order'][:2] == ['Perk Wave Requirement -20.00%', 'Increase Max Game Speed by +1.00']
    assert payload['priority_order'].index('x1.15 All Coin Bonuses') < payload['priority_order'].index('Free Upgrade Chance for All +5.0%')
    assert payload['priority_order'].index('Golden Tower Bonus x1.5') < payload['priority_order'].index('Black Hole Duration +12.0s')
    assert payload['first_perk_choice'] == 'Perk Wave Requirement -20.00%'
    assert payload['unlocked_ultimate_weapons'] == [
        'Black Hole',
        'Chain Lightning',
        'Chrono Field',
        'Death Wave',
        'Golden Tower',
        'Spotlight',
    ]

    timeline, diag = generate_timeline_from_policy(PerkTimelinePolicy(**payload))
    assert diag['uw_locked_perks_excluded'] == {
        '4 More Smart Missiles': 'Smart Missiles',
        'Extra Set of Inner Mines': 'Inner Land Mines',
        'Swamp Radius x1.5': 'Poison Swamp',
    }
    assert not any(row['perk_taken'] in diag['uw_locked_perks_excluded'] for row in timeline)
    assert diag['pwr_stacks'] == 3
    assert [row['wave'] for row in timeline if row['perk_taken'] == 'Perk Wave Requirement -20.00%'] == [187, 561, 748]
    assert timeline[0]['perk_taken'] == 'Perk Wave Requirement -20.00%'
    assert any(row['perk_taken'] == 'Increase Max Game Speed by +1.00' for row in timeline[:4])
    counts_by_wave = pipeline_mod._boss_wave_perk_counts_by_wave(tuple(timeline))
    contributions_by_wave = pipeline_mod._boss_wave_perk_contributions_by_wave(
        counts_by_wave,
        standard_bonus_pct=float(context['standard_perk_bonus_level']),
        tradeoff_bonus_pct=float(context['tradeoff_bonus_level']),
    )
    final_contributions = contributions_by_wave[max(contributions_by_wave)]
    assert final_contributions['perk_PERK_X1_20_MAX_HEALTH_effect_1:wall_hp_multiplier'] == pytest.approx(2.5)
    assert final_contributions['perk_PERK_X1_75_HEALTH_REGEN_effect_1:wall_regen_multiplier'] == pytest.approx(5.9375)
    assert final_contributions['perk_PERK_TOWER_HEALTH_REGEN_X8_00_BUT_TOWER_MAX_MAX_HEALTH_60_effect_1:wall_regen_multiplier'] == pytest.approx(8.8)
    assert final_contributions['perk_PERK_DEFENSE_PERCENT_4_00_effect_1:tower_defense_pct_points_add'] == pytest.approx(25.0)


def test_perk_generator_excludes_uw_perks_for_locked_ultimate_weapons():
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy

    policy = PerkTimelinePolicy(
        seed=7,
        target_wave=50000,
        perk_option_quantity=2,
        priority_order=[
            'Golden Tower Bonus x1.5',
            'Black Hole Duration +12.0s',
        ],
        first_perk_choice='Golden Tower Bonus x1.5',
        unlocked_ultimate_weapons=['Black Hole'],
    )

    timeline, diag = generate_timeline_from_policy(policy)

    assert diag['uw_locked_perks_excluded']['Golden Tower Bonus x1.5'] == 'Golden Tower'
    offered = [perk for row in timeline for perk in row['offered']]
    taken = [row['perk_taken'] for row in timeline]
    assert 'Golden Tower Bonus x1.5' not in offered
    assert 'Golden Tower Bonus x1.5' not in taken
    assert 'Black Hole Duration +12.0s' in taken


def test_max_progression_policy_excludes_uw_perks_for_locked_ultimate_weapons():
    from app import pipeline as pipeline_mod
    from qe.stat_input_compiler import load_perk_entity_rows

    bundle = pipeline_mod.load_inputs(ids_path=IDS_PATH)
    config, metadata = pipeline_mod._resolve_perk_config(
        perk_mode='max_progression_policy',
        primary_config=bundle.perk_config,
        perk_policy=bundle.perk_policy,
        ids_raw=bundle.ids_raw,
    )
    perk_names_by_id = {row['perk_id']: row['perk_name'] for row in load_perk_entity_rows()}
    selected_names = {
        perk_names_by_id[selection['perk_id']]
        for selection in config['perk_presets']['ProjectedMaxPolicy_AllExceptManualBans']
    }

    assert metadata['uw_locked_perks_excluded'] == {
        '4 More Smart Missiles': 'Smart Missiles',
        'Extra Set of Inner Mines': 'Inner Land Mines',
        'Swamp Radius x1.5': 'Poison Swamp',
    }
    assert not (selected_names & set(metadata['uw_locked_perks_excluded']))
    assert 'Black Hole Duration +12.0s' in selected_names
    assert 'Golden Tower Bonus x1.5' in selected_names


def test_build_boss_wave_payload_tourney_fails_closed_without_tournament_wave(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    monkeypatch.setattr(
        pipeline_mod,
        'load_inputs',
        lambda ids_path=None, manual_inputs_path=None: type(
            'Bundle',
            (),
                {'ids_raw': {}, 'loadout_config': {}, 'perk_config': {}, 'perk_policy': {}, 'manual_inputs': {}},
        )(),
    )
    monkeypatch.setattr(
        pipeline_mod,
        'build_runtime_state',
            lambda ids_raw, loadout_config=None, perk_config=None, manual_inputs=None: type(
            'State',
            (),
            {'player_meta': {'Tourney League': 'Legends'}},
        )(),
    )

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', preset='Tourney')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Tourney',
        tier_number=14,
        end_wave=100,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={},
        perk_policy_override={
            'banned_perks': [
                'x1.15 Damage',
                'x1.20 Max Health',
                'x1.75 Health Regen',
            ],
        },
    )

    diagnostics = payload.get('diagnostics') or {}
    assert (payload.get('rows') or []) == []
    assert diagnostics['context_status'] == 'error'
    assert diagnostics['context_error'] == 'missing_tournament_wave'
    assert diagnostics['tournament_wave_source'] == 'IDS::Player & Stuff'
    assert diagnostics['perk_mode'] == 'none'
    assert 'requires a resolved tournament wave' in str(diagnostics['context_error_message'] or '').lower()
    assert diagnostics['model_certification']['model_requirement_applicability']['gc_boss_applicable_damage_semantics'] is False
    assert 'source_owned_full_boss_applicable_damage_semantics' not in diagnostics['model_certification']['model_completion_blockers']


def test_build_boss_wave_payload_tourney_accepts_runtime_tournament_wave_override():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        preset='Tourney',
        perk_mode='none',
        perk_state='off',
    )
    payload = build_boss_wave_payload(
        request,
        preset_name='Tourney',
        tier_number=14,
        end_wave=100,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'tournament_wave': 100,
            'orb_boss_total_damage_pct': 6.0,
            'death_wave_health_max_wave': 1000,
        },
    )

    diagnostics = payload.get('diagnostics') or {}
    summary = payload.get('summary') or {}
    assert diagnostics['context_status'] == 'complete'
    assert diagnostics['league'] == 'Legends'
    assert diagnostics['tournament_wave'] == 100
    assert diagnostics['tournament_wave_source'] == 'runtime_override'
    assert diagnostics['perks_enabled'] is False
    assert summary['status'] == 'complete'
    assert summary['selected_max_wave'] > 0


def test_build_boss_wave_payload_tourney_forces_no_perks_and_applies_tournament_battle_conditions():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        preset='Tourney',
        perk_mode='runtime_timeline',
        perk_state='on',
        perk_policy_preset='eHP Farming',
    )
    payload = build_boss_wave_payload(
        request,
        preset_name='Tourney',
        tier_number=14,
        end_wave=100,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'tournament_wave': 100,
            'orb_boss_total_damage_pct': 6.0,
            'death_wave_health_max_wave': 1000,
        },
    )

    diagnostics = payload['diagnostics']
    surfaces = diagnostics['scenario_surfaces']
    primitives = diagnostics['replacement_primitive_inputs']['values']

    assert diagnostics['mode_id'] == 'tournament'
    assert diagnostics['league'] == 'Legends'
    assert diagnostics['tier_number'] == 17
    assert diagnostics['requested_tier_number'] == 14
    assert diagnostics['tournament_wave'] == 100
    assert diagnostics['requested_perk_mode'] == 'runtime_timeline'
    assert diagnostics['requested_perk_state'] == 'on'
    assert diagnostics['perks_enabled'] is False
    assert diagnostics['perk_mode'] == 'none'
    assert diagnostics['perk_state'] == 'off'
    assert diagnostics['perk_request_resolution'] == 'scenario_policy_overrides_request'
    assert diagnostics['perk_timeline_enabled'] is False
    assert diagnostics['perk_timeline_rows'] == 0
    assert diagnostics['perk_static_count'] == 0
    assert diagnostics['perk_static_pick_count'] == 0
    assert payload['contract']['perk_timeline_mode'] == 'disabled_by_perk_mode_or_state'

    assert diagnostics['actual_boss_interval_waves'] == 6
    assert surfaces['boss_wave_interval'] == 6
    assert surfaces['bc_source'] == 'tournament_magnitudes:league=Legends:wave=100'
    assert surfaces['bc_enemy_attack_speed_increase_pct'] == pytest.approx(125.0)
    assert surfaces['boss_hit_interval_seconds'] == pytest.approx(2.0 / 2.25)
    assert surfaces['bc_enemy_level_skip_reduction_pp'] == pytest.approx(-0.08)
    assert surfaces['bc_death_defy_down_pp'] == pytest.approx(-0.06)
    assert surfaces['bc_energy_shields_down_fraction'] == pytest.approx(0.25)

    assert primitives['enemy_level_skip_reduction_raw'] == pytest.approx(0.0)
    assert primitives['enemy_level_skip_reduction_fraction'] == pytest.approx(0.0)
    assert primitives['enemy_level_skip_chance_delta'] == pytest.approx(0.0)
    assert primitives['enemy_level_skip_decay_start_wave'] == 0
    assert primitives['enemy_level_skip_decay_source'] == (
        'kb.tournaments.tables.battle-condition-magnitudes.csv:enemy_level_skip'
    )
    assert primitives['enemy_level_skip_decay_schedule'][100] == pytest.approx(0.08)
    assert primitives['enemy_level_skip_decay_schedule'][1000] == pytest.approx(0.3333)
    assert primitives['death_defy_down_percent_points'] == pytest.approx(-6.0)
    assert primitives['death_defy_effective_chance_pct'] == pytest.approx(
        max(0.0, primitives['death_defy_chance_pct'] - 6.0)
    )
    assert primitives['energy_shields_down_fraction'] == pytest.approx(0.25)
    assert primitives['energy_shield_effective_charge_count'] == pytest.approx(2.0)
    assert primitives['boss_hit_interval_scenario_base_seconds'] == pytest.approx(2.0 / 2.25)


def test_build_boss_wave_payload_tourney_carries_heat_schedule_to_operator_rows():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=ROOT / 'out',
        preset='Tourney',
        perk_mode='none',
        perk_state='off',
    )
    payload = build_boss_wave_payload(
        request,
        preset_name='Tourney',
        tier_number=14,
        end_wave=120,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'tournament_wave': 100,
            'orb_boss_total_damage_pct': 6.0,
            'death_wave_health_max_wave': 1000,
        },
    )

    primitives = payload['diagnostics']['replacement_primitive_inputs']['values']
    rows = payload['rows']
    first = rows[0]
    heated = next(row for row in rows if int(row['display_wave']) >= 102)
    first_heat = first['overheat_effects']
    heated_heat = heated['overheat_effects']

    slow_aura_multiplier = float(primitives['boss_hit_interval_slow_aura_mastery_multiplier'])
    contact_base_seconds = float(primitives['boss_time_to_contact_base_seconds'])
    chrono_field_slow = float(primitives['boss_time_to_contact_chrono_field_average_slow_fraction'])
    slow_aura_fraction = float(primitives['boss_time_to_contact_slow_aura_fraction'])
    boss_speed_multiplier = float(primitives['boss_time_to_contact_boss_speed_multiplier'])
    energy_net_hold_seconds = float(primitives['boss_time_to_contact_energy_net_hold_seconds'])

    def expected_contact_seconds(enemy_speed_increase_fraction: float) -> float:
        speed_remaining = (
            (1.0 - chrono_field_slow)
            * (1.0 - slow_aura_fraction)
            * (1.0 + enemy_speed_increase_fraction)
            * boss_speed_multiplier
        )
        return (contact_base_seconds / max(0.01, speed_remaining)) + energy_net_hold_seconds

    assert primitives['tournament_heat_schedule_source'] == 'kb.tournaments.tables.battle-condition-magnitudes.csv'
    assert 'boss_ultimate' not in primitives['tournament_heat_schedules']
    assert primitives['dynamic_boss_hit_interval_from_tournament_heat'] is True
    assert primitives['dynamic_boss_contact_time_from_tournament_heat'] is True
    assert first_heat['tournament_enemy_attack_speed_increase_fraction'] == pytest.approx(0.05)
    assert heated_heat['tournament_enemy_attack_speed_increase_fraction'] == pytest.approx(1.25)
    assert first_heat['tournament_enemy_speed_increase_fraction'] == pytest.approx(0.2)
    assert heated_heat['tournament_enemy_speed_increase_fraction'] == pytest.approx(0.9)
    assert first['boss_hit_interval_seconds'] == pytest.approx((2.0 / 1.05) * slow_aura_multiplier)
    assert heated['boss_hit_interval_seconds'] == pytest.approx((2.0 / 2.25) * slow_aura_multiplier)
    assert first['boss_time_to_contact_seconds'] == pytest.approx(expected_contact_seconds(0.2))
    assert heated['boss_time_to_contact_seconds'] == pytest.approx(expected_contact_seconds(0.9))
    assert 'tournament_boss_ultimate_overheal_fraction' not in first_heat
    assert 'tournament_boss_ultimate_overheal_fraction' not in heated_heat


@pytest.mark.live
def test_pipeline_computed_qe_publications_reach_input_dashboard(tmp_path, monkeypatch):
    def _fake_qe_dashboard_publications(**_kwargs):
        return {
            'workshop_coin_values': {'Damage': 'xSENTINEL_COIN'},
            'workshop_max_values': {'Damage': 'xSENTINEL_MAX'},
            'uw_track_effects': {
                'Chain Lightning::Damage': {
                    'module_effect': 'xSENTINEL_MODULE',
                    'perk_effect': 'xSENTINEL_PERK',
                    'final_value': 'xSENTINEL_FINAL',
                },
            },
        }

    monkeypatch.setattr('app.pipeline._build_input_dashboard_qe_publications', _fake_qe_dashboard_publications)

    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    result = execute_pipeline(request)

    assert result.exit_code == 0
    dashboard = json.loads((out_dir / 'input_dashboard.json').read_text(encoding='utf-8'))
    panel_by_id = {panel.get('panel_id'): panel for panel in (dashboard.get('panels') or [])}

    workshop_groups = (panel_by_id['workshop'].get('payload') or {}).get('groups') or {}
    workshop_rows = (
        (workshop_groups.get('offense') or [])
        + (workshop_groups.get('defense') or [])
        + (workshop_groups.get('utility') or [])
    )
    damage_row = next((row for row in workshop_rows if row.get('name') == 'Damage'), None)
    assert damage_row is not None
    assert damage_row.get('coin_value') == 'xSENTINEL_COIN'
    assert damage_row.get('max_value') == 'xSENTINEL_MAX'
    assert sorted(damage_row.keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']

    uw_rows = (panel_by_id['ultimate_weapons'].get('payload') or {}).get('rows') or []
    uw_damage_row = next((row for row in uw_rows if row.get('uw') == 'Chain Lightning' and row.get('track') == 'Damage'), None)
    assert uw_damage_row is not None
    assert uw_damage_row.get('module') == 'xSENTINEL_MODULE'
    assert uw_damage_row.get('perk') == 'xSENTINEL_PERK'
    assert uw_damage_row.get('final') == 'xSENTINEL_FINAL'


def test_input_dashboard_payload_consumes_qe_publications():
    from app.publication import _build_input_dashboard_payload

    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    dashboard = _build_input_dashboard_payload(
        account_state,
        {},
        qe_dashboard_publications={
            'workshop_coin_values': {'Damage': 'x1234'},
            'workshop_max_values': {'Damage': 'x9000'},
            'uw_track_effects': {'Chain Lightning::Damage': {'module_effect': 'x2.25', 'perk_effect': '5', 'final_value': 'x903'}},
        },
    )
    panel_by_id = {panel.get('panel_id'): panel for panel in (dashboard.get('panels') or [])}
    workshop_groups = (panel_by_id['workshop'].get('payload') or {}).get('groups') or {}
    workshop_rows = (
        (workshop_groups.get('offense') or [])
        + (workshop_groups.get('defense') or [])
        + (workshop_groups.get('utility') or [])
    )
    damage_row = next((row for row in workshop_rows if row.get('name') == 'Damage'), None)
    assert damage_row is not None
    assert damage_row.get('coin_value') == 'x1234'
    assert damage_row.get('max_value') == 'x9000'
    assert sorted(damage_row.keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']

    uw_rows = (panel_by_id['ultimate_weapons'].get('payload') or {}).get('rows') or []
    uw_damage_row = next((row for row in uw_rows if row.get('uw') == 'Chain Lightning' and row.get('track') == 'Damage'), None)
    assert uw_damage_row is not None
    assert uw_damage_row.get('module') == 'x2.25'
    assert uw_damage_row.get('perk') == '5'
    assert uw_damage_row.get('final') == 'x903'
    assert sorted(uw_damage_row.keys()) == [
        'final',
        'lab',
        'module',
        'perk',
        'stone_level',
        'stone_value',
        'track',
        'unlock',
        'uw',
        'uw_plus',
    ]
    uw_damage_gaps = [
        gap for gap in (dashboard.get('upstream_gaps') or [])
        if gap.get('panel_id') == 'ultimate_weapons' and 'Chain Lightning::Damage' in str(gap.get('detail') or '')
    ]
    uw_damage_gap_ids = [gap.get('gap_id') for gap in uw_damage_gaps]
    assert 'module_column_not_published_upstream' not in uw_damage_gap_ids
    assert 'perk_column_not_published_upstream' not in uw_damage_gap_ids
    assert 'final_column_not_published_upstream' not in uw_damage_gap_ids


def test_stats_dashboard_fails_closed_when_only_fallback_artifacts_have_values():
    from app.publication import _build_input_dashboard_payload, _build_stats_dashboard_payload

    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Wall Rebuild': {'preset_levels': {'Farming': 250}},
        },
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {
            'workshop': {
                'groups': {
                    'utility': [
                        {'name': 'Wall Rebuild', 'coin_level': '250', 'coin_value': '300.0', 'max_level': '300', 'max_value': '300.0'},
                    ]
                }
            }
        },
        'uw_tracks': {},
        'ultimate_weapons': {},
    }

    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={'Farming': {'rows': {}}},
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={
            'state::wall.rebuild_seconds': {'final_value': 150.0, 'unit': 'seconds', 'status': 'resolved'},
        },
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_name = {row.get('name'): row for row in rows}
    assert by_name['Wall Rebuild']['start_of_run_value'] == '—'
    assert by_name['Wall Rebuild']['max_progression_value'] == '—'


def test_build_input_dashboard_qe_publications_accepts_typed_uw_tracks():
    account_state = SimpleNamespace(
        uw_tracks={
            'Chain Lightning': [
                SimpleNamespace(track_name='Damage', level=100, resolved_value=1.5),
            ],
        }
    )
    published = _build_input_dashboard_qe_publications(
        account_state=account_state,
        compare_rows_by_preset={
            'Farming': {
                'state::tower.damage': {'display_value': 'x100'},
                'state::tower.crit_chance_pct': {'display_value': '69%'},
                'state::uw.chain_lightning.damage_multiplier': {
                    'display_value': 'x903',
                    'contributors': [],
                },
            }
        },
        projected_compare_rows_by_preset={
            'Farming': {
                'state::tower.damage': {'display_value': 'x9000'},
                'state::tower.crit_chance_pct': {'display_value': '99%'},
                'state::uw.chain_lightning.damage_multiplier': {
                    'display_value': 'x903',
                    'contributors': [],
                }
            }
        },
        stat_inputs=[
            SimpleNamespace(
                source_family='workshop',
                source_name='Damage',
                destination_id='tower_damage',
                contributor_id='workshop__tower__damage__flat',
            ),
            SimpleNamespace(
                source_family='workshop',
                source_name='Critical Chance',
                destination_id='tower_crit_chance_pct',
                contributor_id='workshop__tower__crit_chance__pct',
            ),
        ],
        preset_name='Farming',
    )
    assert published.get('workshop_coin_values', {}).get('Damage') == 'x100'
    assert published.get('workshop_max_values', {}).get('Damage') == 'x9000'
    assert published.get('workshop_coin_values', {}).get('Critical Chance') == '69%'
    assert published.get('workshop_max_values', {}).get('Critical Chance') == '99%'
    effects = published.get('uw_track_effects') or {}
    assert 'Chain Lightning::Damage' in effects
    assert effects['Chain Lightning::Damage']['final_value'] == 'x903'


@pytest.mark.live
def test_optimizer_scores_populated(canonical_pipeline_artifacts):
    """optimizer_scores.json must be non-empty."""
    scores = canonical_pipeline_artifacts['optimizer_scores']
    assert isinstance(scores, dict) and len(scores) > 0, "optimizer_scores.json must be non-empty"


@pytest.mark.live
def test_run_stats_canonical_output_filenames(run_stats_single_execution):
    """RunStatsSession.execute() must write canonical run_stats_query_plan_* and run_stats_query_rows_* filenames."""
    out_dir = run_stats_single_execution["out_dir"]

    for key, filename in _RUN_STATS_QUERY_OUTPUTS.items():
        assert (out_dir / filename).exists(), f"Expected canonical output {filename} but it was not written"

    legacy_filenames = [
        'stat_inputs_start_of_run.json', 'stat_inputs_max_progression.json',
        'statbook_start_of_run.json', 'statbook_max_progression.json',
    ]
    for name in legacy_filenames:
        assert not (out_dir / name).exists(), f"Legacy output {name} must not be written"


def test_run_stats_bounded_outputs_publish_current_surface_ids(run_stats_single_execution):
    """The hot run-stats writer skips legacy translation, so outputs must already be current-contract native."""
    legacy_prefix = re.compile(r"\b(?:canonical_stat|mechanic_param|runtime_mechanic_param)::")
    out_dir = run_stats_single_execution["out_dir"]

    for path in sorted(out_dir.glob("*.json")):
        violations = legacy_prefix.findall(path.read_text(encoding="utf-8"))
        assert not violations, f"{path.name} published legacy surface prefixes: {sorted(set(violations))}"


@pytest.mark.live
def test_run_stats_output_contract_distinguishes_committed_and_local_support(run_stats_single_execution):
    diag = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    contract = diag.get('output_contract') or {}

    assert contract.get('contract_kind') == 'run_stats_bounded'
    assert tuple(contract.get('committed_baseline_artifacts') or []) == RUN_STATS_COMMITTED_BASELINE_ARTIFACTS
    assert tuple(contract.get('local_support_artifacts') or []) == RUN_STATS_LOCAL_SUPPORT_ARTIFACTS
    assert tuple(contract.get('optional_committed_artifacts') or ()) == ()
    assert tuple(contract.get('all_local_output_artifacts') or []) == RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS


def test_run_stats_canonical_default_publishes_max_progression_perk_sensitive_uw_rows(run_stats_single_execution):
    diagnostics = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    start_rows = run_stats_single_execution["parsed_outputs"][
        _RUN_STATS_QUERY_OUTPUTS['start_of_run_rows']
    ]['Farming']['rows']
    max_rows = run_stats_single_execution["parsed_outputs"][
        _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']
    ]['Farming']['rows']

    assert diagnostics.get('perk_mode') == 'max_progression_policy'
    assert max_rows['state::uw.black_hole.duration_seconds']['final_value'] == pytest.approx(
        start_rows['state::uw.black_hole.duration_seconds']['final_value'] + 12.0
    )
    assert max_rows['state::uw.chrono_field.duration_seconds']['final_value'] == pytest.approx(
        start_rows['state::uw.chrono_field.duration_seconds']['final_value'] + 5.0
    )
    tourney_rows = run_stats_single_execution["parsed_outputs"][
        _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']
    ]['Tourney']['rows']
    assert tourney_rows['state::cards.super_tower.active']['final_value'] is True
    assert tourney_rows['state::cards.super_tower.bonus_multiplier']['final_value'] > 1.0
    assert tourney_rows['state::cards.super_tower.cooldown_seconds']['final_value'] > 0.0
    assert tourney_rows['state::cards.super_tower.mastery_active']['final_value'] is True
    assert tourney_rows['state::cards.super_tower.uw_mastery_multiplier']['final_value'] > 1.0

    from qe.publication import _uw_track_surface_map

    declared_uw_surfaces = {
        surface_id
        for track_map in _uw_track_surface_map().values()
        for surface_id in track_map.values()
    }
    missing = sorted(declared_uw_surfaces - set(max_rows))
    assert missing == []


@pytest.mark.live
def test_run_stats_writes_stats_dashboard_artifact(run_stats_single_execution):
    stats_dashboard = json.loads((run_stats_single_execution["out_dir"] / "stats_dashboard.json").read_text(encoding='utf-8'))

    assert stats_dashboard.get("artifact") == "stats_dashboard.json"
    assert stats_dashboard.get("schema_version") == 1
    panel_ids = [panel.get("panel_id") for panel in (stats_dashboard.get("panels") or [])]
    secondary_panel_ids = [panel.get("panel_id") for panel in (stats_dashboard.get("secondary_panels") or [])]
    assert panel_ids == ["derived_wall_economy", "workshop", "ultimate_weapons", "bots", "guardians", "modules"]
    assert "modules_resolved" in secondary_panel_ids
    assert "guardians_resolved" in secondary_panel_ids


@pytest.mark.live
def test_run_stats_committed_payload_excludes_volatile_timing_telemetry(run_stats_single_execution):
    run_stats = json.loads((run_stats_single_execution["out_dir"] / "run_stats.json").read_text(encoding='utf-8'))
    diagnostics = run_stats.get('diagnostics') or {}

    assert 'timings_ms' not in diagnostics
    assert 'account_state_build_ms' not in (diagnostics.get('session') or {})
    for preset_payload in (diagnostics.get('presets') or {}).values():
        assert 'timings_ms' not in ((preset_payload.get('start_of_run') or {}))
        assert 'timings_ms' not in ((preset_payload.get('max_progression') or {}))


@pytest.mark.live
def test_run_stats_bounded_outputs_do_not_masquerade_as_full_pipeline_outputs(run_stats_single_execution):
    out_dir = run_stats_single_execution["out_dir"]
    written_names = {path.name for path in out_dir.iterdir() if path.is_file()}

    assert set(RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS).issubset(written_names)
    assert 'pipeline_trace.json' not in written_names
    for name in FULL_PIPELINE_PUBLICATION_ARTIFACTS:
        if name in RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS:
            continue
        assert name not in written_names, f"run_stats bounded output must not silently publish full-pipeline artifact {name}"


@pytest.mark.live
def test_run_stats_bounded_outputs_remove_stale_full_pipeline_artifacts(tmp_path: Path):
    stale_full_pipeline_artifacts = [
        'ep_oracle_compare.json',
        'line_by_line_verification.json',
        'pipeline_trace.json',
        'statbook.json',
    ]
    for name in stale_full_pipeline_artifacts:
        (tmp_path / name).write_text(json.dumps({'stale': True}), encoding='utf-8')

    args = SimpleNamespace(
        ids=IDS_PATH,
        out=tmp_path,
        perk_mode='max_progression_policy',
        perk_state='auto',
        manual_inputs=None,
    )
    rc = RunStatsSession().execute(args)
    assert rc == 0

    assert (tmp_path / 'run_stats.json').exists()
    for name in stale_full_pipeline_artifacts:
        assert not (tmp_path / name).exists(), f"stale full-pipeline artifact survived bounded run_stats: {name}"


@pytest.mark.live
def test_run_stats_emits_geometry_support_artifacts(run_stats_single_execution):
    out_dir = run_stats_single_execution["out_dir"]
    diagnostics = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    geometry_diag = diagnostics["geometry_engine"]

    for name in (
        "geometry_engine_payload.json",
        "geometry_range_report.json",
        "geometry_range_report.csv",
        "geometry_consumer_interfaces.json",
        "geometry_proxy_governance.json",
    ):
        assert (out_dir / name).exists(), f"Expected geometry support artifact {name}"

    geometry_payload = json.loads((out_dir / "geometry_engine_payload.json").read_text(encoding="utf-8"))
    range_report = json.loads((out_dir / "geometry_range_report.json").read_text(encoding="utf-8"))
    governance = json.loads((out_dir / "geometry_proxy_governance.json").read_text(encoding="utf-8"))
    csv_text = (out_dir / "geometry_range_report.csv").read_text(encoding="utf-8")

    assert geometry_diag["artifact"] == "geometry_engine_payload.json"
    assert geometry_diag["effective_contact_truth_promoted"] is False
    assert geometry_payload["owner"] == "simulators.geometry"
    assert geometry_payload["diagnostics"]["state_count"] == 4
    assert range_report["diagnostics"]["surface_split"] == "tower_range_theoretical_m -> tower_range_displayed_m"
    assert len(range_report["rows"]) == 4
    assert csv_text.startswith("preset,state_mode,status,tower_range_input_surface_id")
    assert "range_sensitive_contact_time_proxy_base" in governance["geometry_proxy_governance"]["allowed_uses"]
    assert "boss_contact_time_truth" in governance["geometry_proxy_governance"]["blocked_uses"]


@pytest.mark.live
def test_resolve_fast_checkpoint_smoke():
    """Fast-checkpoint API resolves requested surfaces with structured statbook output."""
    request = FastCheckpointRequest(
        ids=IDS_PATH,
        requested_surface_ids=("canonical_stat::tower_hp", "canonical_stat::tower_damage"),
    )
    result = resolve_fast_checkpoint(request)

    assert result.statbook is not None
    assert "rows" in result.statbook
    assert "canonical_stat::tower_hp" in result.statbook["rows"]
    assert "canonical_stat::tower_damage" in result.statbook["rows"]


@pytest.mark.live
def test_resolve_fast_checkpoint_rejects_empty_surface_ids():
    """Fast-checkpoint must raise ValueError when requested_surface_ids is empty."""
    request = FastCheckpointRequest(ids=IDS_PATH, requested_surface_ids=())
    with pytest.raises(ValueError, match='requested_surface_ids'):
        resolve_fast_checkpoint(request)


def test_path_cache_token_changes_on_file_modification(tmp_path):
    """_path_cache_token must produce a different token after a file is modified."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    token1 = _path_cache_token(f)
    assert token1[1] is not None, "mtime should be captured for existing file"

    # Modify the file (ensure mtime changes by writing more content)
    time.sleep(0.01)
    f.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    # Touch to guarantee mtime change on fast filesystems
    f.touch()
    token2 = _path_cache_token(f)

    assert token1 != token2, "cache token must differ after file modification"


def test_path_cache_token_missing_file():
    """_path_cache_token must not raise for a non-existent path."""
    token = _path_cache_token(Path("/nonexistent/path/ids.csv"))
    assert token[1] is None and token[2] is None


def test_run_stats_session_cache_key_is_file_content_based(tmp_path):
    """RunStatsSession cache key must differ after input file content changes."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key1 = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none', perk_policy_preset=None)

    time.sleep(0.01)
    f.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    f.touch()
    key2 = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none', perk_policy_preset=None)

    assert key1 != key2, "cache key must differ after ids file content changes"


def test_run_stats_session_cache_key_differs_by_perk_mode(tmp_path):
    """RunStatsSession cache key must differ by perk_mode."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key_none = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none', perk_policy_preset=None)
    key_max = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='max_progression_policy', perk_policy_preset=None)
    assert key_none != key_max


def test_run_stats_session_reuses_compiled_stat_inputs_for_identical_context(monkeypatch):
    """RunStatsSession should compile stat inputs once per identical warm-session context."""
    from app import pipeline as pipeline_mod

    session = RunStatsSession()
    account_state = object()
    compiled_row = object()
    calls = []

    def fake_compile_stat_inputs(*args, **kwargs):
        calls.append((args, kwargs))
        return [compiled_row]

    monkeypatch.setattr(pipeline_mod, 'compile_stat_inputs', fake_compile_stat_inputs)

    kwargs = {
        'account_state': account_state,
        'preset_name': 'Farming',
        'state_mode': 'start_of_run',
        'perk_preset_name': None,
        'perks_enabled': False,
        'scenario_context': {'tier': 'Tier 14', 'mode_id': 'farming'},
    }
    first = session._compile_stat_inputs_cached(**kwargs)
    second = session._compile_stat_inputs_cached(**kwargs)

    assert first is second
    assert first == (compiled_row,)
    assert len(calls) == 1

    session._compile_stat_inputs_cached(**{**kwargs, 'state_mode': 'max_progression'})
    assert len(calls) == 2


def test_run_stats_session_cache_key_differs_by_runtime_state_overlay(tmp_path):
    """RunStatsSession cache key must separate IDS-only and named overlay states."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key_ids_only = session._account_state_cache_key(
        ids_path=f,
        manual_inputs_path=None,
        runtime_state_overlay=None,
        perk_mode='none',
        perk_policy_preset=None,
    )
    key_overlay = session._account_state_cache_key(
        ids_path=f,
        manual_inputs_path=None,
        runtime_state_overlay='disco_respec_2026_06_10',
        perk_mode='none',
        perk_policy_preset=None,
    )
    assert key_ids_only != key_overlay


def test_run_stats_session_cache_key_differs_by_perk_policy_preset(tmp_path):
    """RunStatsSession cache key must differ by named perk policy preset."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key_ehp = session._account_state_cache_key(
        ids_path=f,
        manual_inputs_path=None,
        perk_mode='runtime_timeline',
        perk_policy_preset='eHP Farming',
    )
    key_gc = session._account_state_cache_key(
        ids_path=f,
        manual_inputs_path=None,
        perk_mode='runtime_timeline',
        perk_policy_preset='GC Farming',
    )
    assert key_ehp != key_gc


@pytest.mark.live
def test_run_stats_diagnostics_contains_write_outputs_ms(run_stats_single_execution):
    """diagnostics.json persisted by RunStatsSession.execute() must include write_outputs_ms."""
    diag = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    timings = diag.get('timings_ms', {})
    assert 'write_outputs_ms' in timings, "diagnostics.json must contain write_outputs_ms from final write"
    assert isinstance(timings['write_outputs_ms'], (int, float)), "write_outputs_ms must be numeric"
    assert diag.get('perk_policy_preset') == 'eHP Farming'
    perk_support = diag.get('perk_support', {})
    assert perk_support.get('perk_policy_preset') == 'eHP Farming'
    assert perk_support.get('requested_perk_policy_preset') is None
    assert perk_support.get('perk_materialization') is True
    assert perk_support.get('perk_materialization_scope') == 'any_preset_state'
    perk_application = perk_support.get('perk_application_by_preset') or {}
    assert perk_application['Farming']['start_of_run']['perks_enabled'] is False
    assert perk_application['Farming']['max_progression']['perks_enabled'] is True
    assert perk_application['Tourney']['start_of_run']['perks_enabled'] is False
    assert perk_application['Tourney']['max_progression']['perks_enabled'] is False
    assert diag['presets']['Tourney']['max_progression']['perks_enabled'] is False


def test_run_stats_matrix_generation_timing_is_separate_from_write_timing(monkeypatch, tmp_path):
    from app import pipeline as pipeline_mod

    captured: dict[str, object] = {}

    def fake_matrix(*_args, **_kwargs):
        captured.update(_kwargs)
        time.sleep(1.0)
        family_summary = {
            'scope': 'boss_waves_milestone_matrix_selected_rows',
            'status': 'covered',
            'selected_row_count': 1,
            'rows_with_coverage': 1,
            'requested_effect_families': [
                'bot',
                'card_base',
                'card_mastery',
                'workshop',
                'enhancement',
                'module',
                'relic',
            ],
            'missing_requested_families': [],
            'family_status_counts': {
                'bot': {'covered_by_test': 1},
                'card_base': {'covered_by_test': 1},
                'card_mastery': {'covered_by_test': 1},
                'workshop': {'covered_by_test': 1},
                'enhancement': {'covered_by_test': 1},
                'module': {'covered_by_test': 1},
                'relic': {'covered_by_test': 1},
            },
        }
        comparison_family_summary = {
            **family_summary,
            'status': 'covered_with_pressure_factor',
        }
        return {
            'artifact': 'boss_wave_milestone_matrix',
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification_status': 'partial_boss_contact_model',
            'certified_full_max_wave_model': False,
            'model_certification': {
                'model_certification_status': 'partial_boss_contact_model',
                'certified_full_max_wave_model': False,
                'model_completion_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
                'runtime_override_closure': {
                    'non_boss_terminal_pressure': False,
                },
                'effective_model_closure': {
                    'non_boss_terminal_pressure': False,
                    'v28_damage_health_decay_magnitudes': True,
                    'boss_applicable_damage_semantics': True,
                    'gc_boss_applicable_damage_semantics': True,
                },
                'terminal_pressure_runtime_override_status': {
                    'closed': False,
                    'mode': 'active_unsupported_pressure_inputs',
                    'required_fields': ['fleet_terminal_max_wave'],
                    'missing_fields': ['fleet_terminal_max_wave'],
                    'required_fields_by_pressure': {
                        'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
                    },
                    'missing_fields_by_pressure': {
                        'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
                    },
                    'unmapped_pressures': [],
                },
                'non_boss_terminal_pressure_closure': {
                    'closed': False,
                    'mode': 'missing',
                    'exact_terminal_override_closed': False,
                    'pressure_factor_approximation_closed': False,
                    'boss_wave_pressure_factor': None,
                },
            },
            'tiers': [14],
            'rows': [
                {
                    'tier': 14,
                    'model_completion_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
                    'unsupported_terminal_pressures': ['fleet_terminal_pressure'],
                }
            ],
            'wide_rows': [{'tier': 14}],
            'contract': {'selection_policy': 'test'},
            'scenario_runtime_inputs': {},
            'ids_reference_alignment_enabled': True,
            'reference_alignment_summary': {
                'row_count': 1,
                'raw_delta_over_reference_count': 1,
                'max_abs_calculated_delta_wave': 90,
            },
            'replacement_primitive_family_coverage_summary': family_summary,
            'comparison': {
                'label': 'pressure_factor_assumptions',
                'scenario_runtime_inputs': {'boss_wave_pressure_factor': 1.25},
                'runtime_input_overrides': {'boss_wave_pressure_factor': 1.25},
                'base_scenario_runtime_inputs': {},
                'wide_rows': [
                    {
                        'tier': 14,
                        'tier_column': 'Tier 14',
                        'utility_default_wave': 4402,
                        'utility_comparison_wave': 4402,
                        'utility_delta_wave': 0,
                        'utility_default_calculated_wave': 3699,
                        'utility_comparison_calculated_wave': 3609,
                        'utility_calculated_delta_wave': -90,
                        'utility_default_calculated_delta_vs_reference_wave': -703,
                        'utility_comparison_calculated_delta_vs_reference_wave': -793,
                        'utility_default_calculated_to_reference_ratio': 0.840299863698319,
                        'utility_comparison_calculated_to_reference_ratio': 0.819854611540209,
                    }
                ],
                'matrix': {
                    'model_scope': 'boss_contact_survivability',
                    'not_full_max_wave_model': True,
                    'model_certification_status': 'partial_boss_contact_model',
                    'certified_full_max_wave_model': False,
                    'model_certification': {
                        'model_certification_status': 'partial_boss_contact_model',
                        'certified_full_max_wave_model': False,
                        'model_completion_blockers': [],
                        'runtime_override_closure': {
                            'non_boss_terminal_pressure': True,
                        },
                        'effective_model_closure': {
                            'non_boss_terminal_pressure': True,
                            'v28_damage_health_decay_magnitudes': True,
                            'boss_applicable_damage_semantics': True,
                            'gc_boss_applicable_damage_semantics': True,
                        },
                        'terminal_pressure_runtime_override_status': {
                            'closed': False,
                            'mode': 'active_unsupported_pressure_inputs',
                            'required_fields': ['fleet_terminal_max_wave'],
                            'missing_fields': ['fleet_terminal_max_wave'],
                            'required_fields_by_pressure': {
                                'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
                            },
                            'missing_fields_by_pressure': {
                                'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
                            },
                            'unmapped_pressures': [],
                        },
                        'non_boss_terminal_pressure_closure': {
                            'closed': True,
                            'mode': 'boss_wave_pressure_factor_approximation',
                            'exact_terminal_override_closed': False,
                            'pressure_factor_approximation_closed': True,
                            'boss_wave_pressure_factor': 1.25,
                        },
                    },
                    'rows': [{'tier': 14}],
                    'wide_rows': [{'tier': 14}],
                    'model_blocker_summary': {
                        'row_count': 1,
                        'rows_with_model_completion_blockers': 0,
                        'model_completion_blocker_counts': {},
                        'rows_with_unsupported_terminal_pressures': 0,
                        'unsupported_terminal_pressure_counts': {},
                    },
                    'reference_gap_summary': {
                        'row_count': 1,
                        'missing_reference_blocked_count': 0,
                        'ordinary_missing_reference_blocked_count': 0,
                        'dissonance_pb_cap_omitted_reference_count': 0,
                        'by_reference_kind': {},
                        'by_run_type': [],
                        'missing_references': [],
                    },
                    'reference_alignment_summary': {
                        'row_count': 1,
                        'raw_delta_over_reference_count': 0,
                        'max_abs_calculated_delta_wave': 40,
                    },
                    'replacement_primitive_family_coverage_summary': comparison_family_summary,
                },
            },
        }

    monkeypatch.setattr(pipeline_mod, 'build_boss_wave_milestone_matrix', fake_matrix)
    args = SimpleNamespace(
        ids=IDS_PATH,
        out=tmp_path,
        perk_mode='max_progression_policy',
        perk_state='auto',
        perk_policy_preset=None,
        manual_inputs=None,
        tier=None,
        dissonance_run_category='none',
        include_boss_wave_milestone_matrix=True,
        boss_wave_contact_time_seconds=10.0,
        boss_wave_orb_boss_total_damage_pct=6.0,
    )

    assert RunStatsSession().execute(args) == 0
    diagnostics = json.loads((tmp_path / 'diagnostics.json').read_text(encoding='utf-8'))
    run_stats = json.loads((tmp_path / 'run_stats.json').read_text(encoding='utf-8'))
    timings = diagnostics.get('timings_ms') or {}
    output_contract = diagnostics.get('output_contract') or {}
    matrix_diagnostics = diagnostics.get('boss_wave_milestone_matrix') or {}
    assert timings['boss_wave_milestone_matrix_build_ms'] >= 1000.0
    assert timings['boss_wave_milestone_matrix_write_ms'] >= 0.0
    assert timings['write_outputs_ms'] >= timings['boss_wave_milestone_matrix_write_ms']
    assert timings['write_outputs_ms'] < timings['boss_wave_milestone_matrix_build_ms']
    assert output_contract['optional_committed_artifacts'] == ['boss_wave_milestone_matrix.json']
    assert output_contract['optional_local_artifacts'] == []
    assert captured['align_clean_reference_rows'] is True
    assert captured['tiers'] == tuple(range(1, 22))
    assert captured['dissonance_run_categories'] == pipeline_mod._BOSS_WAVE_DISSONANCE_RUN_MATRIX_CATEGORIES
    assert captured['scenario_runtime_inputs'] == {
        'boss_time_to_contact_seconds': 10.0,
        'orb_boss_total_damage_pct': 6.0,
    }
    assert matrix_diagnostics['model_scope'] == 'boss_contact_survivability'
    assert matrix_diagnostics['not_full_max_wave_model'] is True
    assert matrix_diagnostics['model_certification_status'] == 'partial_boss_contact_model'
    assert matrix_diagnostics['certified_full_max_wave_model'] is False
    assert matrix_diagnostics['model_completion_blockers'] == [
        'source_owned_non_boss_terminal_pressure_formulas'
    ]
    assert matrix_diagnostics['model_certification']['terminal_pressure_runtime_override_status'] == {
        'closed': False,
        'mode': 'active_unsupported_pressure_inputs',
        'required_fields': ['fleet_terminal_max_wave'],
        'missing_fields': ['fleet_terminal_max_wave'],
        'required_fields_by_pressure': {
            'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
        },
        'missing_fields_by_pressure': {
            'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
        },
        'unmapped_pressures': [],
    }
    assert matrix_diagnostics['runtime_override_closure'] == {
        'non_boss_terminal_pressure': False,
    }
    assert matrix_diagnostics['effective_model_closure'] == {
        'non_boss_terminal_pressure': False,
        'v28_damage_health_decay_magnitudes': True,
        'boss_applicable_damage_semantics': True,
        'gc_boss_applicable_damage_semantics': True,
    }
    assert matrix_diagnostics['terminal_pressure_runtime_override_status'] == (
        matrix_diagnostics['model_certification']['terminal_pressure_runtime_override_status']
    )
    assert matrix_diagnostics['non_boss_terminal_pressure_closure'] == {
        'closed': False,
        'mode': 'missing',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': False,
        'boss_wave_pressure_factor': None,
    }
    assert matrix_diagnostics['model_blocker_summary'] == {
        'row_count': 1,
        'rows_with_model_completion_blockers': 1,
        'model_completion_blocker_counts': {
            'source_owned_non_boss_terminal_pressure_formulas': 1,
        },
        'rows_with_unsupported_terminal_pressures': 1,
        'unsupported_terminal_pressure_counts': {
            'fleet_terminal_pressure': 1,
        },
    }
    assert matrix_diagnostics['row_count'] == 1
    assert matrix_diagnostics['wide_row_count'] == 1
    assert matrix_diagnostics['reference_alignment_summary'] == {
        'row_count': 1,
        'raw_delta_over_reference_count': 1,
        'max_abs_calculated_delta_wave': 90,
    }
    assert matrix_diagnostics['replacement_primitive_family_coverage_summary'] == {
        'scope': 'boss_waves_milestone_matrix_selected_rows',
        'status': 'covered',
        'selected_row_count': 1,
        'rows_with_coverage': 1,
        'requested_effect_families': [
            'bot',
            'card_base',
            'card_mastery',
            'workshop',
            'enhancement',
            'module',
            'relic',
        ],
        'missing_requested_families': [],
        'family_status_counts': {
            'bot': {'covered_by_test': 1},
            'card_base': {'covered_by_test': 1},
            'card_mastery': {'covered_by_test': 1},
            'workshop': {'covered_by_test': 1},
            'enhancement': {'covered_by_test': 1},
            'module': {'covered_by_test': 1},
            'relic': {'covered_by_test': 1},
        },
    }
    assert matrix_diagnostics['comparison_enabled'] is True
    assert matrix_diagnostics['comparison_label'] == 'pressure_factor_assumptions'
    assert matrix_diagnostics['comparison_scenario_runtime_inputs'] == {'boss_wave_pressure_factor': 1.25}
    assert matrix_diagnostics['comparison_runtime_input_overrides'] == {'boss_wave_pressure_factor': 1.25}
    assert matrix_diagnostics['comparison_base_scenario_runtime_inputs'] == {}
    assert matrix_diagnostics['comparison_row_count'] == 1
    assert matrix_diagnostics['comparison_matrix_row_count'] == 1
    assert matrix_diagnostics['comparison_matrix_wide_row_count'] == 1
    assert matrix_diagnostics['comparison_reference_alignment_summary'] == {
        'row_count': 1,
        'raw_delta_over_reference_count': 0,
        'max_abs_calculated_delta_wave': 40,
    }
    assert matrix_diagnostics['comparison_replacement_primitive_family_coverage_summary'] == {
        'scope': 'boss_waves_milestone_matrix_selected_rows',
        'status': 'covered_with_pressure_factor',
        'selected_row_count': 1,
        'rows_with_coverage': 1,
        'requested_effect_families': [
            'bot',
            'card_base',
            'card_mastery',
            'workshop',
            'enhancement',
            'module',
            'relic',
        ],
        'missing_requested_families': [],
        'family_status_counts': {
            'bot': {'covered_by_test': 1},
            'card_base': {'covered_by_test': 1},
            'card_mastery': {'covered_by_test': 1},
            'workshop': {'covered_by_test': 1},
            'enhancement': {'covered_by_test': 1},
            'module': {'covered_by_test': 1},
            'relic': {'covered_by_test': 1},
        },
    }
    assert matrix_diagnostics['comparison_model_scope'] == 'boss_contact_survivability'
    assert matrix_diagnostics['comparison_not_full_max_wave_model'] is True
    assert matrix_diagnostics['comparison_model_certification_status'] == 'partial_boss_contact_model'
    assert matrix_diagnostics['comparison_certified_full_max_wave_model'] is False
    assert matrix_diagnostics['comparison_model_completion_blockers'] == []
    assert matrix_diagnostics['comparison_runtime_override_closure'] == {
        'non_boss_terminal_pressure': True,
    }
    assert matrix_diagnostics['comparison_effective_model_closure'] == {
        'non_boss_terminal_pressure': True,
        'v28_damage_health_decay_magnitudes': True,
        'boss_applicable_damage_semantics': True,
        'gc_boss_applicable_damage_semantics': True,
    }
    assert matrix_diagnostics['comparison_terminal_pressure_runtime_override_status'] == {
        'closed': False,
        'mode': 'active_unsupported_pressure_inputs',
        'required_fields': ['fleet_terminal_max_wave'],
        'missing_fields': ['fleet_terminal_max_wave'],
        'required_fields_by_pressure': {
            'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
        },
        'missing_fields_by_pressure': {
            'fleet_terminal_pressure': ['fleet_terminal_max_wave'],
        },
        'unmapped_pressures': [],
    }
    assert matrix_diagnostics['comparison_non_boss_terminal_pressure_closure'] == {
        'closed': True,
        'mode': 'boss_wave_pressure_factor_approximation',
        'exact_terminal_override_closed': False,
        'pressure_factor_approximation_closed': True,
        'boss_wave_pressure_factor': 1.25,
    }
    assert matrix_diagnostics['comparison_model_certification']['non_boss_terminal_pressure_closure'] == (
        matrix_diagnostics['comparison_non_boss_terminal_pressure_closure']
    )
    assert matrix_diagnostics['comparison_model_blocker_summary'] == {
        'row_count': 1,
        'rows_with_model_completion_blockers': 0,
        'model_completion_blocker_counts': {},
        'rows_with_unsupported_terminal_pressures': 0,
        'unsupported_terminal_pressure_counts': {},
    }
    assert matrix_diagnostics['comparison_reference_gap_summary'] == {
        'row_count': 1,
        'missing_reference_blocked_count': 0,
        'ordinary_missing_reference_blocked_count': 0,
        'dissonance_pb_cap_omitted_reference_count': 0,
        'by_reference_kind': {},
        'by_run_type': [],
        'missing_references': [],
    }
    assert matrix_diagnostics['comparison_calculated_delta_summary'] == {
        'row_count': 1,
        'comparison_raw_wave_higher_count': 0,
        'comparison_raw_wave_lower_count': 1,
        'comparison_raw_wave_match_count': 0,
        'max_abs_calculated_delta_wave': 90,
        'max_abs_calculated_delta_row': {
            'tier': 14,
            'tier_column': 'Tier 14',
            'dissonance_run_category': 'utility',
            'label': 'Utility Dissonant Run',
            'default_selected_wave': 4402,
            'comparison_selected_wave': 4402,
            'selected_delta_wave': 0,
            'default_calculated_wave': 3699,
            'comparison_calculated_wave': 3609,
            'calculated_delta_wave': -90,
            'default_calculated_delta_vs_reference_wave': -703,
            'comparison_calculated_delta_vs_reference_wave': -793,
            'default_calculated_to_reference_ratio': 0.840299863698319,
            'comparison_calculated_to_reference_ratio': 0.819854611540209,
        },
        'by_run_type': [
            {
                'dissonance_run_category': 'utility',
                'label': 'Utility Dissonant Run',
                'row_count': 1,
                'comparison_raw_wave_higher_count': 0,
                'comparison_raw_wave_lower_count': 1,
                'comparison_raw_wave_match_count': 0,
                'max_abs_calculated_delta_wave': 90,
            }
        ],
    }
    for payload in (diagnostics, run_stats['diagnostics']):
        evidence = payload['current_scope_effect_family_evidence']
        assert evidence['status'] == 'covered'
        assert evidence['scope'] == 'current_goal_effect_families_to_boss_waves_selected_rows'
        assert evidence['route_closure_status'] == 'closed'
        assert evidence['individual_route_evidence_status'] == 'closed'
        assert evidence['unique_source_family_route_count'] == 163
        assert evidence['unique_source_family_registered_route_count'] == 163
        assert evidence['unique_source_family_unregistered_route_count'] == 0
        assert evidence['unique_source_family_route_status_counts'] == {'registered': 163}
        assert evidence['statbook_route_visibility_status'] == 'not_evaluated'
        assert evidence['statbook_route_visibility_exception_status'] == 'not_evaluated'
        assert evidence['statbook_route_visibility_exception_policy'] == {
            'accepted_partial_visibility_classifications': [
                'inactive_card_capability_route_gated_off_current_statbook',
                'inactive_module_unique_registered_not_current_account_route',
                'other_preset_module_card_payload_visible_in_query_books',
            ],
            'active_selected_route_gap_count': 0,
            'other_preset_missing_query_evidence_count': 0,
            'unclassified_route_gap_count': 0,
            'policy': (
                'Selected-statbook visibility may be partial only when every hidden route is '
                'classified as inactive for the selected preset or visible through another-preset query-book evidence.'
            ),
        }
        assert evidence['statbook_route_visibility_status_counts'] == {'not_evaluated': 7}
        assert evidence['statbook_route_visibility_mode_counts'] == {}
        assert evidence['statbook_route_visibility_incomplete_families'] == []
        assert evidence['generated_mapping_status'] == 'closed'
        assert evidence['effect_row_carrythrough_status'] == 'covered'
        assert evidence['effect_row_carrythrough_status_counts'] == {'covered': 7}
        assert evidence['effect_row_carrythrough_incomplete_families'] == []
        assert evidence['boss_wave_coverage_status'] == 'covered'
        assert evidence['boss_wave_selected_row_count'] == 1
        assert evidence['boss_wave_rows_with_coverage'] == 1
        assert evidence['line_verification_status'] == 'not_evaluated'
        assert evidence['line_verification']['reason'] == 'statbook_or_line_verification_not_supplied'
        assert evidence['missing_route_closure_families'] == []
        assert evidence['missing_individual_route_evidence_families'] == []
        assert evidence['missing_generated_mapping_families'] == []
        assert evidence['missing_boss_wave_coverage_families'] == []
        assert set(evidence['requested_effect_families']) == {
            'bot',
            'card_base',
            'card_mastery',
            'workshop',
            'enhancement',
            'module',
            'relic',
        }
        for family in evidence['requested_effect_families']:
            family_evidence = evidence['families'][family]
            route_evidence = family_evidence['individual_route_evidence']
            carrythrough = family_evidence['effect_row_carrythrough']
            assert route_evidence['status'] == 'closed'
            assert route_evidence['route_contributor_count'] > 0
            assert route_evidence['registered_route_contributor_count'] == route_evidence[
                'route_contributor_count'
            ]
            assert route_evidence['unregistered_route_contributor_count'] == 0
            assert route_evidence['statbook_route_visibility_status'] == 'not_evaluated'
            assert route_evidence['statbook_route_visibility_mode_counts'] == {}
            assert carrythrough['status'] == 'covered'
            assert carrythrough['individual_routes_closed'] is True
            assert carrythrough['individual_route_contributor_count'] == route_evidence[
                'route_contributor_count'
            ]
            assert carrythrough['generated_mapping_closed'] is True
            assert carrythrough['boss_wave_covered'] is True
            assert carrythrough['boss_wave_selected_row_count'] == 1
            assert carrythrough['boss_wave_rows_with_coverage'] == 1
            assert carrythrough['line_verification_status'] == 'not_evaluated'
        assert 'Bounded run_stats diagnostics summary only' in evidence['caveat']
        assert 'Full EP compare evidence remains owned by full-pipeline diagnostics.json' in evidence['caveat']


def test_run_stats_matrix_generation_honors_tier_override(monkeypatch, tmp_path):
    from app import pipeline as pipeline_mod

    captured: dict[str, object] = {}

    def fake_matrix(*_args, **_kwargs):
        captured.update(_kwargs)
        return {
            'artifact': 'boss_wave_milestone_matrix',
            'tiers': [14],
            'rows': [{'tier': 14}],
            'wide_rows': [{'tier': 14}],
            'contract': {'selection_policy': 'test'},
            'scenario_runtime_inputs': {},
            'ids_reference_alignment_enabled': True,
            'reference_alignment_summary': {'row_count': 1},
        }

    monkeypatch.setattr(pipeline_mod, 'build_boss_wave_milestone_matrix', fake_matrix)
    args = SimpleNamespace(
        ids=IDS_PATH,
        out=tmp_path,
        perk_mode='max_progression_policy',
        perk_state='auto',
        perk_policy_preset=None,
        manual_inputs=None,
        tier=14,
        dissonance_run_category='utility',
        include_boss_wave_milestone_matrix=True,
    )

    assert RunStatsSession().execute(args) == 0
    diagnostics = json.loads((tmp_path / 'diagnostics.json').read_text(encoding='utf-8'))
    matrix_diagnostics = diagnostics.get('boss_wave_milestone_matrix') or {}
    assert captured['tiers'] == (14,)
    assert captured['dissonance_run_categories'] == ('utility',)
    assert matrix_diagnostics['tier_count'] == 1
    assert matrix_diagnostics['row_count'] == 1


def test_run_stats_without_matrix_flag_preserves_existing_committed_matrix_artifact(tmp_path):
    existing_matrix = tmp_path / 'boss_wave_milestone_matrix.json'
    existing_matrix.write_text('{"artifact":"boss_wave_milestone_matrix","sentinel":true}', encoding='utf-8')
    args = SimpleNamespace(
        ids=IDS_PATH,
        out=tmp_path,
        perk_mode='max_progression_policy',
        perk_state='auto',
        perk_policy_preset=None,
        manual_inputs=None,
        tier=None,
        dissonance_run_category='none',
        include_boss_wave_milestone_matrix=False,
    )

    assert RunStatsSession().execute(args) == 0
    assert json.loads(existing_matrix.read_text(encoding='utf-8'))['sentinel'] is True
    diagnostics = json.loads((tmp_path / 'diagnostics.json').read_text(encoding='utf-8'))
    assert diagnostics['boss_wave_milestone_matrix']['enabled'] is False
    assert tuple((diagnostics.get('output_contract') or {}).get('optional_committed_artifacts') or ()) == ()


@pytest.mark.live
def test_ep_oracle_compare_exists_and_nonempty_for_sharded_path(tmp_path):
    """Protect the sharded evaluator output publication contract for ep_oracle_compare.json."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    compare_path = out_dir / "ep_oracle_compare.json"
    assert compare_path.exists()
    compare_data = json.loads(compare_path.read_text(encoding='utf-8'))


@pytest.mark.live
def test_execute_pipeline_writes_full_pipeline_artifact_contract(tmp_path):
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    result = execute_pipeline(request)

    assert result.exit_code == 0
    written_names = {path.name for path in result.generated_files}
    assert 'pipeline_trace.json' in written_names
    for name in FULL_PIPELINE_PUBLICATION_ARTIFACTS:
        assert name in written_names, f"execute_pipeline must write full-pipeline artifact {name}"
def test_ep_oracle_compare_populated(canonical_pipeline_artifacts):
    """ep_oracle_compare.json must stay structurally aligned with the published compare summary."""
    compare = canonical_pipeline_artifacts['ep_oracle_compare']
    summary = canonical_pipeline_artifacts['diagnostics']['ep_compare_summary']
    assert isinstance(compare, dict)
    assert len(compare) == int(summary.get('ep_compare_count') or 0)


def test_ep_oracle_compare_rows_have_explicit_formula_policy(canonical_pipeline_artifacts):
    compare = canonical_pipeline_artifacts['ep_oracle_compare']

    unclassified = {
        surface_id: row.get('formula_contract')
        for surface_id, row in compare.items()
        if (row.get('formula_contract') or {}).get('formula_class') == 'unclassified'
    }

    assert unclassified == {}


def test_ep_oracle_compare_stage_context_includes_compare_loadout_metadata(canonical_pipeline_artifacts):
    compare = canonical_pipeline_artifacts['ep_oracle_compare']
    context = compare['state::tower.crit_multiplier']['ep_stage_context']

    tourney_modules = context['active_modules_by_preset']['Tourney']
    assert tourney_modules['cannon']['primary'] == 'Amplifying Strike'
    assert tourney_modules['generator']['primary'] == 'Project Funding'
    assert context['modules_inventory']['Amplifying Strike']['rarity'] == 'Ancestral 2*'
    assert 'Berserker' in context['active_cards_by_preset']['Tourney']


def test_ep_oracle_compare_has_no_unknown_formula_mismatches(canonical_pipeline_artifacts):
    from evaluators.compare import build_compare_status_summary

    compare = canonical_pipeline_artifacts['ep_oracle_compare']
    summary = build_compare_status_summary(compare)

    assert summary['ep_raw_formula_mismatch_count'] == summary['ep_known_export_defect_count']
    assert summary['ep_true_formula_mismatch_count'] == 0
    assert summary['ep_unknown_formula_mismatch_count'] == 0


def test_ep_oracle_compare_exact_and_close_rows_publish_pass_verdicts(canonical_pipeline_artifacts):
    compare = canonical_pipeline_artifacts['ep_oracle_compare']
    aligned_statuses = {'matched_exact', 'matched_close'}
    aligned_rows = {
        surface_id: row
        for surface_id, row in compare.items()
        if row.get('status') in aligned_statuses
    }

    assert aligned_rows
    bad_rows = {
        surface_id: {
            'status': row.get('status'),
            'kb_alignment_status': row.get('kb_alignment_status'),
            'verdict': row.get('verdict'),
        }
        for surface_id, row in aligned_rows.items()
        if row.get('kb_alignment_status') != 'aligned' or row.get('verdict') != 'pass'
    }
    assert bad_rows == {}


def test_ep_compare_status_mapping_marks_exact_and_close_as_aligned():
    from evaluators.compare import kb_alignment_status_from_compare_status as public_status
    from evaluators.compare_core import kb_alignment_status_from_compare_status as core_status

    for status in ('matched_exact', 'matched_close', 'match', 'close'):
        assert public_status(status) == 'aligned'
        assert core_status(status) == 'aligned'
    for status in ('stage_scope_mismatch', 'formula_blocked', 'non_comparable', 'non_numeric_compare'):
        assert public_status(status) == 'not_comparable'
        assert core_status(status) == 'not_comparable'


def test_line_verification_allows_level_contributors_only_on_level_or_authorized_formula_surfaces():
    from evaluators.compare import build_line_by_line_verification

    statbook = {
        'rows': {
            'state::example.level': {
                'status': 'resolved',
                'final_value': 3.0,
                'schema': {
                    'unit': 'level',
                    'allowed_input_value_types': ['level'],
                    'resolver': 'standard_scalar_param',
                },
                'contributors': [{'source_name': 'Example Level', 'value': 3.0, 'value_type': 'level'}],
            },
            'state::example.multiplier': {
                'status': 'resolved',
                'final_value': 3.0,
                'schema': {
                    'unit': 'multiplier',
                    'allowed_input_value_types': ['level'],
                    'resolver': 'standard_scalar_param',
                },
                'contributors': [{'source_name': 'Example Formula', 'value': 3.0, 'value_type': 'level'}],
            },
            'derived::example.authorized_formula': {
                'status': 'resolved',
                'final_value': 0.015,
                'schema': {
                    'unit': 'ratio',
                    'resolver': 'query_derived_composites',
                },
                'contributors': [{'source_name': 'Example Formula Level', 'value': 2.0, 'value_type': 'level'}],
            },
            'state::example.raw_text_passthrough': {
                'status': 'resolved',
                'final_value': 'Tier 14',
                'schema': {
                    'unit': 'unknown',
                    'allowed_input_value_types': ['raw_text'],
                    'expected_input_semantics': ['raw_text'],
                    'resolver': 'capability_passthrough',
                },
                'contributors': [{'source_name': 'Example Enum', 'value': 'Tier 14', 'value_type': 'raw_text'}],
            },
            'state::example.raw_text_formula': {
                'status': 'resolved',
                'final_value': 'Tier 14',
                'schema': {
                    'unit': 'unknown',
                    'allowed_input_value_types': ['raw_text'],
                    'resolver': 'standard_scalar_param',
                },
                'contributors': [{'source_name': 'Example Text Formula', 'value': 'Tier 14', 'value_type': 'raw_text'}],
            },
        }
    }

    verification = build_line_by_line_verification(
        statbook,
        ep_compare={},
        formula_ledger={},
        formula_contract=lambda _ledger, key: (
            {'allowed_formula_input_value_types': ['level']}
            if key == 'derived::example.authorized_formula'
            else {}
        ),
    )

    assert verification['state::example.level']['verification_status'] == 'publishable'
    assert verification['state::example.level']['verdict'] == 'pass'
    assert verification['state::example.level']['issues'] == []
    assert verification['state::example.multiplier']['verification_status'] == 'blocked'
    assert verification['state::example.multiplier']['verdict'] == 'fail'
    assert verification['state::example.multiplier']['issues'] == ['level_contributor_present']
    assert verification['derived::example.authorized_formula']['verification_status'] == 'publishable'
    assert verification['derived::example.authorized_formula']['verdict'] == 'pass'
    assert verification['derived::example.authorized_formula']['issues'] == []
    assert verification['state::example.raw_text_passthrough']['verification_status'] == 'publishable'
    assert verification['state::example.raw_text_passthrough']['verdict'] == 'pass'
    assert verification['state::example.raw_text_passthrough']['issues'] == []
    assert verification['state::example.raw_text_formula']['verification_status'] == 'blocked'
    assert verification['state::example.raw_text_formula']['verdict'] == 'fail'
    assert verification['state::example.raw_text_formula']['issues'] == ['unresolved_contributor_present']


def test_line_verification_stage_scope_compare_rows_are_limitations_not_blockers():
    from evaluators.compare import build_line_by_line_verification

    statbook = {
        'rows': {
            'state::stage.scoped': {
                'status': 'resolved',
                'final_value': 10.0,
                'schema': {
                    'unit': 'unknown',
                    'allowed_input_value_types': ['resolved_value'],
                    'resolver': 'standard_scalar_param',
                },
                'contributors': [{'source_name': 'Stage Scoped', 'value': 10.0, 'value_type': 'resolved_value'}],
            },
            'state::true.mismatch': {
                'status': 'resolved',
                'final_value': 10.0,
                'schema': {
                    'unit': 'unknown',
                    'allowed_input_value_types': ['resolved_value'],
                    'resolver': 'standard_scalar_param',
                },
                'contributors': [{'source_name': 'Mismatch', 'value': 10.0, 'value_type': 'resolved_value'}],
            },
            'state::known.export.defect': {
                'status': 'resolved',
                'final_value': 9.6,
                'schema': {
                    'unit': 'unknown',
                    'allowed_input_value_types': ['resolved_value'],
                    'resolver': 'standard_scalar_param',
                },
                'contributors': [{'source_name': 'Known Defect', 'value': 9.6, 'value_type': 'resolved_value'}],
            },
        }
    }

    verification = build_line_by_line_verification(
        statbook,
        ep_compare={
            'state::stage.scoped': {'status': 'stage_scope_mismatch', 'delta': None},
            'state::true.mismatch': {'status': 'mismatch', 'delta': 1.0},
            'state::known.export.defect': {
                'status': 'mismatch',
                'delta': 8.6,
                'compare_notes': [
                    'ep_export_bug:max_rend_multiplier_exports_identity_or_display_1_0_instead_of_kb_qe_9_6',
                ],
            },
        },
        formula_ledger={},
        formula_contract=lambda _ledger, _key: {},
    )

    assert verification['state::stage.scoped']['verification_status'] == 'publishable'
    assert verification['state::stage.scoped']['kb_alignment_status'] == 'not_comparable'
    assert verification['state::stage.scoped']['verdict'] == 'pass_with_compare_limitations'
    assert verification['state::stage.scoped']['issues'] == []
    assert verification['state::true.mismatch']['verification_status'] == 'blocked'
    assert verification['state::true.mismatch']['verdict'] == 'fail'
    assert verification['state::true.mismatch']['issues'] == ['ep_reference_mismatch']
    assert verification['state::known.export.defect']['verification_status'] == 'publishable'
    assert verification['state::known.export.defect']['kb_alignment_status'] == 'not_comparable'
    assert verification['state::known.export.defect']['verdict'] == 'pass_with_compare_limitations'
    assert verification['state::known.export.defect']['issues'] == []
    assert verification['state::known.export.defect']['ep_compare_known_export_defect'] is True


@pytest.mark.live
def test_sharded_evaluators_parity(canonical_pipeline_artifacts):
    """Sharded evaluator outputs stay internally consistent even when EP compare is empty."""
    compare_data = canonical_pipeline_artifacts['ep_oracle_compare']
    projection_views = canonical_pipeline_artifacts['diagnostics']['ep_compare_projection_views']
    assert isinstance(compare_data, dict)
    assert int((projection_views.get('current_state_mode') or {}).get('ep_compare_count') or 0) == len(compare_data)



