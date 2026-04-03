"""
Functional tests for app/pipeline.py and sharded evaluators.
Verifies trace contract, artifact depth, run-stats output naming,
cache invalidation robustness, and diagnostics persistence contract.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import pytest

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
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"


@pytest.fixture(scope="module")
def run_stats_single_execution(tmp_path_factory):
    """Execute RunStatsSession once and return parsed canonical outputs plus output directory."""
    out_dir = tmp_path_factory.mktemp("run_stats_out")
    args = SimpleNamespace(
        ids=IDS_PATH, out=out_dir, perk_mode='none', perk_state='auto', manual_inputs=None,
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
        perk_presets={'Farming': {}},
        active_perk_preset='Farming',
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
    workshop_rows = ((((panel_by_id['workshop'].get('payload') or {}).get('groups') or {}).get('offense') or [])
                     + (((panel_by_id['workshop'].get('payload') or {}).get('groups') or {}).get('defense') or [])
                     + (((panel_by_id['workshop'].get('payload') or {}).get('groups') or {}).get('utility') or []))
    if workshop_rows:
        assert {'unlock', 'name', 'coin_level', 'coin_value', 'max_level', 'max_value'}.issubset(workshop_rows[0].keys())
    uw_rows = ((panel_by_id['ultimate_weapons'].get('payload') or {}).get('rows') or [])
    if uw_rows:
        assert {'unlock', 'uw', 'track', 'stone_level', 'stone_value', 'lab', 'module', 'perk', 'final', 'uw_plus'}.issubset(uw_rows[0].keys())
    assert isinstance(dashboard.get('upstream_gaps'), list)


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
    key1 = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none')

    time.sleep(0.01)
    f.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    f.touch()
    key2 = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none')

    assert key1 != key2, "cache key must differ after ids file content changes"


def test_run_stats_session_cache_key_differs_by_perk_mode(tmp_path):
    """RunStatsSession cache key must differ by perk_mode."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key_none = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none')
    key_max = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='max_progression_policy')
    assert key_none != key_max


@pytest.mark.live
def test_run_stats_diagnostics_contains_write_outputs_ms(run_stats_single_execution):
    """diagnostics.json persisted by RunStatsSession.execute() must include write_outputs_ms."""
    diag = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    timings = diag.get('timings_ms', {})
    assert 'write_outputs_ms' in timings, "diagnostics.json must contain write_outputs_ms from final write"
    assert isinstance(timings['write_outputs_ms'], (int, float)), "write_outputs_ms must be numeric"


@pytest.mark.live
def test_ep_oracle_compare_exists_and_nonempty_for_sharded_path(tmp_path):
    """Protect the sharded evaluator output publication contract for ep_oracle_compare.json."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    compare_path = out_dir / "ep_oracle_compare.json"
    assert compare_path.exists()
    compare_data = json.loads(compare_path.read_text(encoding='utf-8'))
def test_ep_oracle_compare_populated(canonical_pipeline_artifacts):
    """ep_oracle_compare.json must be a non-empty dict."""
    compare = canonical_pipeline_artifacts['ep_oracle_compare']
    assert isinstance(compare, dict) and len(compare) > 0


@pytest.mark.live
def test_sharded_evaluators_parity(canonical_pipeline_artifacts):
    """Sharded evaluators produce non-empty comparison artifacts (from main's T12 contract)."""
    compare_data = canonical_pipeline_artifacts['ep_oracle_compare']
    assert isinstance(compare_data, dict) and len(compare_data) > 0
