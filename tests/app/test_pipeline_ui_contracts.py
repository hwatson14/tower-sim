from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def start_of_run_pipeline_result(tmp_path_factory: pytest.TempPathFactory):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    out_dir = tmp_path_factory.mktemp("start_of_run_pipeline_out")
    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=out_dir,
            preset='Farming',
            state_mode='start_of_run',
        )
    )
    assert result.exit_code == 0
    return result


@pytest.fixture(scope="module")
def canonical_pipeline_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    from app.pipeline import PipelineRunRequest, execute_pipeline

    out_dir = tmp_path_factory.mktemp("canonical_pipeline_out")
    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=out_dir,
            preset='Farming',
            state_mode='start_of_run',
        )
    )
    assert result.exit_code == 0

    return {
        'diagnostics': json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8')),
        'statbook_publishable': json.loads((out_dir / 'statbook_publishable.json').read_text(encoding='utf-8')),
        'optimizer_scores': json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8')),
        'ep_oracle_compare': json.loads((out_dir / 'ep_oracle_compare.json').read_text(encoding='utf-8')),
        'pipeline_trace': json.loads((out_dir / 'pipeline_trace.json').read_text(encoding='utf-8')),
        'dashboards': {
            'input_dashboard': json.loads((out_dir / 'input_dashboard.json').read_text(encoding='utf-8')),
            'stats_dashboard': json.loads((out_dir / 'stats_dashboard.json').read_text(encoding='utf-8')),
        },
        'out_dir': out_dir,
    }


def test_request_adapter_and_execute_pipeline_emit_trace(start_of_run_pipeline_result):
    result = start_of_run_pipeline_result

    assert result.exit_code == 0
    assert (result.out_dir / 'pipeline_trace.json').exists()
    trace = result.pipeline_trace.to_dict()
    assert trace['execution_path']['recompute_mode'] is not None
    assert 'cache_status' in trace['execution_path']
    assert 'runtime_consumers' in trace['execution_path']
    stage_ids = [stage['stage_id'] for stage in trace['stages']]
    assert stage_ids[:4] == ['input_load', 'runtime_account_assembly', 'compare_materialization', 'stat_resolution']
    assert 'artifact_write' in stage_ids
    input_load_stage = next(stage for stage in trace['stages'] if stage['stage_id'] == 'input_load')
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == 'input/manual_inputs.yaml'


@pytest.mark.live
def test_trace_input_load_manual_inputs_path_respects_override(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    manual_inputs_override = tmp_path / 'manual_inputs.partial.yaml'
    manual_inputs_override.write_text('player:\\n  profile_name: fixture-partial\\n', encoding='utf-8')
    request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'out',
        manual_inputs=manual_inputs_override,
    )
    result = execute_pipeline(request)

    assert result.exit_code == 0
    trace = result.pipeline_trace.to_dict()
    input_load_stage = next(stage for stage in trace['stages'] if stage['stage_id'] == 'input_load')
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == manual_inputs_override.as_posix()


def test_trace_artifact_is_listed_in_generated_files(start_of_run_pipeline_result):
    result = start_of_run_pipeline_result
    generated = {path.name for path in result.generated_files}
    assert 'pipeline_trace.json' in generated


def _streamlit_widget_by_label(widgets, label: str):
    matches = [widget for widget in widgets if getattr(widget, 'label', None) == label]
    assert len(matches) == 1, f"expected one {label!r} widget, found {len(matches)}"
    return matches[0]


def _set_streamlit_text_input(app_test, label: str, value: str) -> None:
    _streamlit_widget_by_label(app_test.text_input, label).set_value(value)


def _set_streamlit_selectbox(app_test, label: str, value: str) -> None:
    _streamlit_widget_by_label(app_test.selectbox, label).set_value(value)


def _click_streamlit_button(app_test, label: str) -> None:
    _streamlit_widget_by_label(app_test.button, label).click()


def _streamlit_labels(widgets) -> list[str]:
    return [str(getattr(widget, 'label', '')) for widget in widgets]


def _streamlit_values(widgets) -> list[str]:
    return [str(getattr(widget, 'value', '')) for widget in widgets]


def test_streamlit_boss_waves_exposes_only_wired_manual_runtime_inputs():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert 'Combat assumptions' in source
    assert 'Override boss damage calibration' in source
    assert 'Advanced damage calibration' not in source
    assert "number_input('End wave', min_value=10, value=10000, step=10)" in source
    assert "selectbox(\n        'Run type'," in source
    assert 'BOSS_WAVE_DISSONANCE_RUN_LABELS' in source
    for label in (
        'Orb damage to boss (total %)',
        'Electron damage override (total %)',
        'Boss time to contact override (s)',
        'Death Wave maxed wave',
    ):
        assert label in source
    for stale_label in (
        'Orb boss hit %',
        'Effective DR %',
        'Incoming damage multiplier',
        'Death Wave health max x',
        'Boss hit interval (s)',
        'Flame Bot boss hit chance (%)',
        'Flame Bot DR %',
        'Defense Field DR %',
        'BH DR %',
        'BH duration (s)',
        'PBH uptime',
    ):
        assert stale_label not in source


def test_streamlit_perks_tab_consumes_pipeline_preview_not_local_generator():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert "'Perks'" in source
    assert 'build_perk_timeline_preview' in source
    assert 'for column, policy_preset in zip(columns, BOSS_WAVE_PERK_POLICY_PRESETS)' in source
    assert 'replace(request, perk_policy_preset=policy_preset)' in source
    assert 'Priority order' in source
    assert 'Bans' in source
    assert 'Taken by wave' in source
    assert 'Perk plan' in source
    assert 'Final wave' in source
    assert "_arrow_safe_frame(pd.DataFrame(rows), columns=('value', 'picks', 'max value'))" in source
    assert 'generate_timeline_from_policy' not in source
    assert 'PerkTimelinePolicy' not in source


def test_streamlit_boss_waves_operator_surface_renders_cleanly():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error

    assert _streamlit_values(app_test.title) == ['TowerSim Operations Console']
    assert 'Canonical stats, perk plans, and max-wave runs from sanctioned pipeline artifacts.' in _streamlit_values(app_test.caption)

    metric_labels = _streamlit_labels(app_test.metric)
    assert metric_labels.count('Max Boss Wave') == 1
    for stale_label in ('Rows', 'Selected wave', 'First failed wave', 'Perk plan', 'Tier', 'Loadout'):
        assert stale_label not in metric_labels

    selectbox_labels = _streamlit_labels(app_test.selectbox)
    assert 'Boss loadout' in selectbox_labels
    assert 'Perk plan' in selectbox_labels
    assert 'Run type' in selectbox_labels
    run_type_widget = _streamlit_widget_by_label(app_test.selectbox, 'Run type')
    assert list(run_type_widget.options) == [
        'Regular',
        'Attack Dissonant Run',
        'Defense Dissonant Run',
        'Utility Dissonant Run',
        'Ultimate Weapon Dissonant Run',
    ]

    number_input_labels = _streamlit_labels(app_test.number_input)
    assert 'End wave' in number_input_labels
    assert 'Checkpoint cadence (bosses)' in number_input_labels
    assert 'Matrix end wave' in number_input_labels
    assert 'Matrix checkpoint cadence (bosses)' in number_input_labels

    toggle_labels = _streamlit_labels(app_test.toggle)
    assert 'Override boss damage calibration' in toggle_labels
    assert 'Show all checkpoints' in toggle_labels
    assert 'Stop on first failed boss' not in toggle_labels

    expander_labels = _streamlit_labels(app_test.expander)
    for label in (
        'Combat assumptions',
        'All-tier preset matrix',
        'Model assumptions',
        'Advanced boss-wave evidence',
    ):
        assert label in expander_labels
    assert 'Advanced run settings' not in expander_labels
    assert 'Advanced damage calibration' not in expander_labels
    for stale_label in (
        'Dissonance comparison',
        'Full boss-wave table',
        'Boss-wave diagnostics',
        'Boss-wave raw rows (debug)',
        'Boss-wave execution details',
    ):
        assert stale_label not in expander_labels

    caption_values = _streamlit_values(app_test.caption)
    assert 'Boss checkpoints' in caption_values
    assert 'Runtime inputs' in caption_values
    assert any('Result uses' in value for value in caption_values)
    assert 'Build all-tier 4-preset matrix' in _streamlit_labels(app_test.button)


def test_streamlit_boss_waves_run_type_selector_feeds_dissonance_path():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _streamlit_widget_by_label(app_test.selectbox, 'Run type').set_value('Ultimate Weapon Dissonant Run')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    caption_values = _streamlit_values(app_test.caption)
    assert any('Ultimate Weapon Dissonant Run' in value for value in caption_values)
    assert any('IDS Dissonant PB reference' in value for value in caption_values)


def test_streamlit_boss_waves_manual_damage_calibration_is_intentional():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    assert 'Boss eDamage applicability factor' not in _streamlit_labels(app_test.number_input)

    _streamlit_widget_by_label(app_test.toggle, 'Override boss damage calibration').set_value(True)
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    number_input_labels = _streamlit_labels(app_test.number_input)
    for label in (
        'Boss eDamage applicability factor',
        'Boss target share',
        'Boss cadence uptime',
        'Boss reliability',
        'Boss semantic normalizer',
    ):
        assert label in number_input_labels


def test_streamlit_boss_waves_tourney_exposes_legends_wave_override():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert 'Legends tournament wave' not in _streamlit_labels(app_test.number_input)
    _streamlit_widget_by_label(app_test.selectbox, 'Boss loadout').set_value('Tourney')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    assert 'Legends tournament wave' in _streamlit_labels(app_test.number_input)


def test_streamlit_run_controls_are_tab_scoped_not_sidebar_global():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert "TowerSim Operations Console" in source
    assert "Canonical stats, perk plans, and max-wave runs from sanctioned pipeline artifacts." in source
    assert "TowerSim Incremental Inspector" not in source
    assert "st.sidebar.header('Run Controls')" not in source
    assert "boss_wave_perk_policy_override" not in source
    assert "perk_policy_override" not in source
    assert "st.sidebar.header('Snapshots')" in source
    assert "def _render_pipeline_run_controls" in source
    assert "def _render_verification_snapshot_controls" in source
    pipeline_start = source.index("def _render_pipeline(trace_payload")
    pipeline_end = source.index("\ndef _render_cards_matrix", pipeline_start)
    main_start = source.index("def main() -> None:")
    pipeline_block = source[pipeline_start:pipeline_end]
    assert "with st.expander('Pipeline evidence', expanded=False)" in pipeline_block
    assert "['Execution', 'Stages', 'Cache', 'Runtime', 'Advanced']" in pipeline_block
    assert "Active snapshot request defaults" in source[pipeline_start:pipeline_end]
    assert "Active snapshot request defaults" not in source[main_start:]
    assert "with st.expander('Execution Path'" not in pipeline_block
    assert "st.subheader('Cache')" not in pipeline_block
    assert "st.subheader('Incremental Plan')" not in pipeline_block
    assert "st.subheader('Runtime Consumers')" not in pipeline_block
    assert "with st.expander('Advanced raw details')" not in pipeline_block
    assert "'Run loadout'" in source
    assert "'Run perk plan'" in source
    assert "'Verification perk plan'" in source
    assert "'Boss loadout'" in source
    assert "'Perk plan'" in source
    assert "'Run type'" in source


def test_streamlit_perks_tab_renders_four_policy_columns():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    markdown_text = '\n'.join(str(item.value) for item in app_test.markdown)
    caption_text = '\n'.join(str(item.value) for item in app_test.caption)
    for policy_preset in ('eHP Max Waves', 'eHP Farming', 'GC Max Waves', 'GC Farming'):
        assert policy_preset in markdown_text
    assert caption_text.count('Priority order') == 4
    assert caption_text.count('Bans') == 4
    assert caption_text.count('Taken by wave') == 4


def test_streamlit_perks_table_does_not_fallback_to_active_preset_for_tourney():
    from app.streamlit_inspector import _perk_display_preset

    account_state = {
        'active_perk_preset': 'ProjectedMaxPolicy_AllExceptManualBans',
        'perk_presets': {
            'ProjectedMaxPolicy_AllExceptManualBans': [{'perk_id': 'PERK_X1_15_DAMAGE', 'picks': 1}],
            'Farming': [{'perk_id': 'PERK_X1_15_DAMAGE', 'picks': 1}],
        },
    }

    assert _perk_display_preset(account_state, selected_preset='Tourney') is None
    assert _perk_display_preset(account_state, selected_preset='Farming') == 'Farming'
    assert (
        _perk_display_preset(account_state, selected_preset='Milestone')
        == 'ProjectedMaxPolicy_AllExceptManualBans'
    )


def test_streamlit_pipeline_tourney_gc_max_waves_run_click_is_perk_guarded(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    out_dir = tmp_path / 'streamlit_tourney_run'
    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run output dir', str(out_dir))
    _set_streamlit_selectbox(app_test, 'Run loadout', 'Tourney')
    _set_streamlit_selectbox(app_test, 'Run perk plan', 'GC Max Waves')
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Tourney'
    assert diagnostics['perk_support']['perk_policy_preset'] == 'GC Max Waves'
    assert diagnostics['perk_support']['perk_materialization'] is False
    assert diagnostics['perk_support']['active_perk_preset'] is None
    assert diagnostics['state_matrix']['start_of_run']['perks_enabled'] is False
    assert diagnostics['state_matrix']['max_progression']['perks_enabled'] is False


def test_streamlit_pipeline_milestone_run_publishes_optimizer_unavailable(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    out_dir = tmp_path / 'streamlit_milestone_run'
    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run output dir', str(out_dir))
    _set_streamlit_selectbox(app_test, 'Run loadout', 'Milestone')
    _set_streamlit_selectbox(app_test, 'Run perk plan', 'eHP Max Waves')
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    optimizer_scores = json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Milestone'
    assert diagnostics['optimizer_scores']['status'] == 'unavailable'
    assert diagnostics['optimizer_scores']['reason'] == 'missing_governed_surface'
    assert optimizer_scores['meta']['status'] == 'unavailable'
    assert optimizer_scores['meta']['local_canonical_formula_fallback'] is False


def test_streamlit_pipeline_gc_farming_plan_runs_without_errors(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    out_dir = tmp_path / 'streamlit_gc_farming_run'
    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run output dir', str(out_dir))
    _set_streamlit_selectbox(app_test, 'Run loadout', 'Farming')
    _set_streamlit_selectbox(app_test, 'Run perk plan', 'GC Farming')
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Farming'
    assert diagnostics['perk_support']['perk_policy_preset'] == 'GC Farming'


def test_streamlit_register_snapshot_replaces_stale_label_for_reused_output_dir(monkeypatch, tmp_path):
    from app import streamlit_inspector as inspector

    out_dir = tmp_path / 'streamlit_reused_out'
    stale_label = inspector.snapshot_label(
        preset='Farming',
        state_mode='start_of_run',
        perk_state='auto',
        out_dir=out_dir,
    )
    session_state = {
        'snapshot_dirs': {stale_label: str(out_dir)},
        'active_out_dir': str(out_dir),
    }
    monkeypatch.setattr(inspector.st, 'session_state', session_state)

    inspector._register_snapshot(out_dir, preset='Tourney', state_mode='start_of_run', perk_state='auto')

    labels = list(session_state['snapshot_dirs'])
    assert stale_label not in labels
    assert len(labels) == 1
    assert labels[0].startswith('Tourney | start_of_run | perks auto |')
    assert session_state['snapshot_dirs'][labels[0]] == str(out_dir)


def test_streamlit_fast_checkpoint_button_is_scoped_to_stats_evidence_expander():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    tools_start = source.index('def _render_stats_debug_tools(')
    tools_end = source.index('\ndef _render_stats(', tools_start)
    tools_block = source[tools_start:tools_end]
    stats_start = source.index('def _render_stats(')
    stats_end = source.index('\ndef _require_boss_wave_payload_rows', stats_start)
    stats_block = source[stats_start:stats_end]

    assert "st.button('Resolve selected stats via fast checkpoint'" in tools_block
    assert 'runtime_state_overlay=request.runtime_state_overlay' in tools_block
    assert "with st.expander('Stats evidence and verification', expanded=False):" in stats_block
    assert '_render_stats_debug_tools(active_artifacts, comparison_artifacts, request)' in stats_block


def test_streamlit_pipeline_run_failures_are_contained(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run IDS path', str(tmp_path / 'missing_ids.csv'))
    _set_streamlit_text_input(app_test, 'Run output dir', str(tmp_path / 'bad_run_out'))
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert any('Run snapshot failed:' in str(error.value) for error in app_test.error)


def test_streamlit_checks_verification_failures_are_contained(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Verification IDS path', str(tmp_path / 'missing_ids.csv'))
    _set_streamlit_text_input(app_test, 'Verification output dir', str(tmp_path / 'bad_verification_out'))
    _click_streamlit_button(app_test, 'Build default verification set')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert any('Build default verification set failed:' in str(error.value) for error in app_test.error)


def test_streamlit_default_verification_snapshots_can_be_selected(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Verification output dir', str(tmp_path / 'verification_base'))
    _click_streamlit_button(app_test, 'Build default verification set')
    app_test.run(timeout=360)

    assert not app_test.exception
    assert not app_test.error
    snapshot_options = list(_streamlit_widget_by_label(app_test.sidebar.selectbox, 'Active snapshot').options)
    assert {
        'Farming | start_of_run | perks auto | farming_start_of_run',
        'Farming | max_progression | perks auto | farming_max_progression',
        'Tourney | start_of_run | perks off | tourney_start_of_run',
        'Tourney | max_progression | perks off | tourney_max_progression',
    }.issubset(set(snapshot_options))
    for option in snapshot_options:
        _streamlit_widget_by_label(app_test.sidebar.selectbox, 'Active snapshot').set_value(option)
        app_test.run(timeout=240)
        assert not app_test.exception
        assert not app_test.error


def test_pipeline_writes_input_dashboard_contract(tmp_path, monkeypatch):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    monkeypatch.setattr(
        'app.pipeline._build_input_dashboard_qe_publications',
        lambda **_kwargs: {
            'workshop_coin_values': {'Damage': 'xUI_SENTINEL_COIN'},
            'workshop_max_values': {'Damage': 'xUI_SENTINEL_MAX'},
        },
    )

    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'out',
        )
    )
    assert result.exit_code == 0
    dashboard_path = result.out_dir / 'input_dashboard.json'
    assert dashboard_path.exists()
    payload = json.loads(dashboard_path.read_text(encoding='utf-8'))
    assert sorted(payload.keys()) == [
        'debug_manifest',
        'panels',
        'preset_options',
        'schema_version',
        'selected_preset',
        'upstream_gaps',
    ]
    assert payload.get('schema_version') == 2
    assert payload['selected_preset']
    assert {'Farming', 'Tourney', 'Milestone', 'Preset 4', 'Preset 5'}.issubset(set(payload.get('preset_options') or []))
    panel_ids = [panel.get('panel_id') for panel in (payload.get('panels') or [])]
    panel_types = [panel.get('panel_type') for panel in (payload.get('panels') or [])]
    assert panel_ids == [
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
    assert panel_types == [
        'labs_bucket_grid',
        'grouped_workshop_table',
        'grouped_enhancement_table',
        'uw_track_table',
        'cards_inventory_and_preset',
        'track_table',
        'simple_bonus_table',
        'module_slot_stack',
        'simple_bonus_table',
        'track_table',
        'simple_metric_panel',
    ]
    panel_by_id = {panel.get('panel_id'): panel for panel in (payload.get('panels') or [])}
    workshop_groups = (panel_by_id['workshop'].get('payload') or {}).get('groups') or {}
    workshop_rows = (
        (workshop_groups.get('offense') or [])
        + (workshop_groups.get('defense') or [])
        + (workshop_groups.get('utility') or [])
    )
    damage_row = next((row for row in workshop_rows if row.get('name') == 'Damage'), None)
    assert damage_row is not None
    assert damage_row.get('coin_value') == 'xUI_SENTINEL_COIN'
    assert damage_row.get('max_value') == 'xUI_SENTINEL_MAX'
    assert sorted(damage_row.keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']


def test_pipeline_writes_stats_dashboard_contract(canonical_pipeline_artifacts):
    out_dir = canonical_pipeline_artifacts['out_dir']
    payload = canonical_pipeline_artifacts['dashboards']['stats_dashboard']

    assert (out_dir / 'stats_dashboard.json').exists()
    assert (out_dir / 'run_stats_query_rows_start_of_run.json').exists()
    assert (out_dir / 'run_stats_query_rows_max_progression.json').exists()
    assert sorted(payload.keys()) == [
        'artifact',
        'contract',
        'dashboard_version',
        'debug_manifest',
        'panels',
        'preset_options',
        'schema_version',
        'secondary_panels',
        'secondary_variants',
        'selected_preset',
        'selected_state_mode',
        'state_mode_options',
        'upstream_gaps',
        'variants',
    ]
    assert payload.get('artifact') == 'stats_dashboard.json'
    assert payload.get('contract', {}).get('owner') == 'qe'
    assert payload.get('schema_version') == 1
    assert payload.get('selected_preset') == 'Farming'
    assert payload.get('selected_state_mode') == 'start_of_run'
    panel_ids = [panel.get('panel_id') for panel in (payload.get('panels') or [])]
    assert panel_ids == [
        'derived_wall_economy',
        'workshop',
        'ultimate_weapons',
        'bots',
        'guardians',
        'modules',
    ]
    secondary_panel_ids = [panel.get('panel_id') for panel in (payload.get('secondary_panels') or [])]
    assert secondary_panel_ids == [
        'offense_resolved',
        'defense_resolved',
        'utility_resolved',
        'wall_economy_resolved',
        'cards_resolved',
        'bots_resolved',
        'guardians_resolved',
        'modules_resolved',
        'uw_stats_resolved',
    ]
    variants = payload.get('variants') or {}
    secondary_variants = payload.get('secondary_variants') or {}
    farming_variants = variants.get('Farming') or {}
    farming_secondary_variants = secondary_variants.get('Farming') or {}
    assert {'start_of_run', 'max_progression'}.issubset(set(farming_variants.keys()))
    assert {'start_of_run', 'max_progression'}.issubset(set(farming_secondary_variants.keys()))
    start_panels = farming_variants['start_of_run']
    max_panels = farming_variants['max_progression']
    start_secondary_panels = farming_secondary_variants['start_of_run']
    start_workshop = next(panel for panel in start_panels if panel.get('panel_id') == 'workshop')
    max_workshop = next(panel for panel in max_panels if panel.get('panel_id') == 'workshop')
    start_uw = next(panel for panel in start_panels if panel.get('panel_id') == 'ultimate_weapons')
    start_derived = next(panel for panel in start_panels if panel.get('panel_id') == 'derived_wall_economy')
    max_derived = next(panel for panel in max_panels if panel.get('panel_id') == 'derived_wall_economy')
    start_bots = next(panel for panel in start_panels if panel.get('panel_id') == 'bots')
    start_guardians = next(panel for panel in start_panels if panel.get('panel_id') == 'guardians')
    start_modules = next(panel for panel in start_panels if panel.get('panel_id') == 'modules')
    assert start_workshop.get('payload', {}).get('sections')
    assert max_workshop.get('payload', {}).get('sections')
    assert any(section.get('title') == 'Derived' for section in (start_derived.get('payload', {}).get('sections') or []))
    assert [table.get('title') for table in (start_derived.get('payload', {}).get('objective_tables') or [])] == ['eHP', 'eDamage', 'eEcon']
    assert [table.get('title') for table in (max_derived.get('payload', {}).get('objective_tables') or [])] == ['eHP', 'eDamage', 'eEcon']
    assert start_uw.get('payload', {}).get('sections')
    assert start_bots.get('payload', {}).get('sections')
    assert start_guardians.get('payload', {}).get('sections')
    assert 'slots' in (start_modules.get('payload') or {})
    assert (start_modules.get('payload') or {}).get('summary_rows')
    assert any(panel.get('panel_id') == 'offense_resolved' for panel in start_secondary_panels)


def test_pipeline_run_stats_query_rows_publish_qe_derived_wall_semantics(canonical_pipeline_artifacts):
    out_dir = canonical_pipeline_artifacts['out_dir']
    start_rows = json.loads((out_dir / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    max_rows = json.loads((out_dir / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))

    start_farming = (start_rows.get('Farming') or {}).get('rows') or {}
    max_farming = (max_rows.get('Farming') or {}).get('rows') or {}

    assert start_farming['state::tower.free_attack_upgrade_chance_pct']['final_value'] == pytest.approx(84.24)
    assert max_farming['state::tower.free_attack_upgrade_chance_pct']['final_value'] == pytest.approx(120.8025)
    assert 'derived::wall.hp_pre_fort' in start_farming
    assert start_farming['derived::wall.hp_pre_fort']['final_value'] > 0
    assert max_farming['derived::wall.hp_pre_fort']['final_value'] > start_farming['derived::wall.hp_pre_fort']['final_value']
    assert start_farming['support_surface::ehp.black_hole_duration_seconds']['final_value'] == pytest.approx(32.0)
    assert start_farming['support_surface::ehp.black_hole_cooldown_seconds']['final_value'] == pytest.approx(50.0)
    assert start_farming['support_surface::ehp.health_relic_pct']['final_value'] == pytest.approx(0.57)
    assert start_farming['support_surface::ehp.dabs_relic_pct']['final_value'] == pytest.approx(0.30)
    assert start_farming['support_surface::ehp.def_pct_relic_pct']['final_value'] == pytest.approx(0.05)
    assert start_farming['support_surface::eecon.adstarter_theme_relic_factor']['final_value'] == pytest.approx(1.59)
    assert start_farming['support_surface::eecon.freeup_attack_relic_pct']['final_value'] == pytest.approx(0.06)
    assert start_farming['support_surface::eecon.freeup_defense_relic_pct']['final_value'] == pytest.approx(0.07)
    assert start_farming['support_surface::eecon.freeup_utility_relic_pct']['final_value'] == pytest.approx(0.09)
    assert start_farming['state::uw.black_hole.base_duration_seconds']['final_value'] == pytest.approx(36.0)
    assert start_farming['state::uw.black_hole.base_cooldown_seconds']['final_value'] == pytest.approx(46.0)
    assert start_farming['state::uw.black_hole.duration_seconds']['final_value'] == pytest.approx(36.0)
    assert start_farming['state::uw.black_hole.cooldown_seconds']['final_value'] == pytest.approx(46.0)
    assert start_farming['state::uw.golden_tower.base_duration_seconds']['final_value'] == pytest.approx(42.0)
    assert start_farming['state::uw.golden_tower.base_cooldown_seconds']['final_value'] == pytest.approx(180.0)
    assert start_farming['state::uw.golden_tower.duration_seconds']['final_value'] == pytest.approx(42.0)
    assert start_farming['state::uw.golden_tower.cooldown_seconds']['final_value'] == pytest.approx(180.0)
    assert start_farming['derived::ehp.primordial_black_hole_uptime']['final_value'] == pytest.approx(32.0 / 82.0)
    assert start_farming['derived::ehp.primordial_black_hole_damage_reduction_factor']['final_value'] == pytest.approx(1.4539007092198584)
    assert start_farming['derived::ehp.health_relic_factor']['final_value'] == pytest.approx(1.57)
    assert start_farming['derived::ehp.dabs_relic_factor']['final_value'] == pytest.approx(1.30)
    assert start_farming['derived::ehp.def_pct_relic_term']['final_value'] == pytest.approx(0.05)
    assert start_farming['derived::eecon.base_meta_factor']['final_value'] == pytest.approx(1.59)


def test_pipeline_tier_scoped_dissonance_reconciles_t14_ep_panels(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    out_dir = tmp_path / "tier14_pipeline_out"
    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=out_dir,
            preset='Farming',
            state_mode='max_progression',
            tier=14,
            runtime_state_overlay='disco_respec_2026_06_10',
        )
    )
    assert result.exit_code == 0
    rows = json.loads((out_dir / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))['Farming']['rows']

    assert rows['derived::dissonance.defense.total_multiplier']['final_value'] == pytest.approx(5.108782215759483)
    assert rows['derived::ehp.health_factor']['final_value'] == pytest.approx(37.55645848408285e12)
    assert rows['state::uw.chain_lightning.max_enemy_damage_reduction_pct']['final_value'] == pytest.approx(36.0)
    assert rows['derived::ehp.chain_thunder_factor']['final_value'] == pytest.approx(1.5625)
    assert rows['derived::ehp']['final_value'] == pytest.approx(9.895934708746359e17)
    assert rows['state::tower.regen']['final_value'] == pytest.approx(239.1178682173424e12)
    assert rows['state::wall.fortification_multiplier']['final_value'] == pytest.approx(10.6)
    assert rows['derived::wall.hp_pre_fort']['final_value'] == pytest.approx(657.0877976375138e12)
    assert rows['derived::wall.hp_final']['final_value'] == pytest.approx(6.965130654957646e15)
    assert rows['derived::wall.regen_hp_per_second']['final_value'] == pytest.approx(1315.1482751953832e12)
    assert rows['state::tower.defense_absolute']['status'] == 'resolved'
    assert rows['derived::ehp.dabs_perk_factor']['final_value'] == pytest.approx(1.0)
    assert rows['state::tower.defense_absolute']['final_value'] == pytest.approx(148.07576034428293e6)
    assert rows['state::economy.coins_per_kill_bonus']['final_value'] == pytest.approx(48.176822924999996)
    assert rows['state::economy.all_coin_bonus_multiplier']['final_value'] == pytest.approx(4819.747713669525)
    assert rows['state::cards.wave_skip.chance_pct']['final_value'] == pytest.approx(19.0)
    assert rows['derived::eecon.freeup_factor']['final_value'] == pytest.approx(1.0135264984384758)
    assert rows['derived::eecon.wave_factor']['final_value'] == pytest.approx(1.3064513895292529)
    assert rows['derived::eecon.utility_dissonance_factor']['final_value'] > 1.0
    assert rows['derived::eecon.unit_scale_factor']['final_value'] == pytest.approx(1000.0)
    assert rows['derived::eecon']['final_value'] == pytest.approx(453088857.6792872)


def test_pipeline_cards_payload_publishes_selected_rows_by_preset(canonical_pipeline_artifacts):
    out_dir = canonical_pipeline_artifacts['out_dir']
    dashboard = canonical_pipeline_artifacts['dashboards']['input_dashboard']
    account_state = json.loads((out_dir / 'account_state.json').read_text(encoding='utf-8'))
    cards_panel = next(panel for panel in (dashboard.get('panels') or []) if panel.get('panel_id') == 'cards')
    payload = cards_panel.get('payload') or {}

    selected_preset = str(dashboard.get('selected_preset'))
    preset_options = [str(name) for name in (dashboard.get('preset_options') or [])]
    preset_rows_by_preset = payload.get('preset_rows_by_preset') or {}
    assert isinstance(preset_rows_by_preset, dict)
    assert selected_preset in preset_rows_by_preset
    assert set(preset_options).issubset(set(preset_rows_by_preset))
    selected_names_from_dashboard = {
        str(row.get('name'))
        for row in (preset_rows_by_preset.get(selected_preset) or [])
        if str(row.get('selected') or '').strip() == 'Yes'
    }
    selected_names_from_state = set((account_state.get('card_presets') or {}).get(selected_preset) or [])
    assert selected_names_from_dashboard == selected_names_from_state


def test_streamlit_app_contract_is_frozen_in_repo() -> None:
    contract_path = ROOT / 'app' / 'streamlit_inspector.py'
    text = contract_path.read_text(encoding='utf-8')
    assert '`streamlit` is optional' in text.lower()
    assert 'boss waves is interactive' in text.lower()
    assert 'permanently removed' in text.lower()
    assert 'from input.loader import load_inputs' not in text
    assert 'from input.runtime_state import build_runtime_state' not in text
    assert 'from simulators.run_executor import' not in text
    assert 'from qe.stat_input_compiler import' not in text
    assert 'manual_inputs.yaml' not in text
    assert 'kb/' not in text


def test_streamlit_stats_and_boss_waves_use_sanctioned_facades() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert 'query_rows_dual_state_frame(' in text
    assert 'query_rows_surface_detail(' in text
    assert 'build_boss_wave_payload(' in text
    assert '_module_unique_effect_map(' not in text


def test_boss_waves_render_uses_published_summary_and_execution_contract() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("def _render_boss_waves(request: PipelineRunRequest")
    end = text.index("\ndef main() -> None:", start)
    boss_block = text[start:end]
    assert "stop_on_failure = True" in boss_block
    assert "stop_on_failure=stop_on_failure" in boss_block
    assert "dissonance_run_category=dissonance_run_category" in boss_block
    assert "dissonance_run_categories=(dissonance_run_category,)" in boss_block
    assert "BOSS_WAVE_DISSONANCE_RUN_LABELS" in boss_block
    assert "Stop on first failed boss" not in boss_block
    assert "rows after the first failure" not in boss_block
    assert "'flame_bot_boss_hit_chance_pct':" not in boss_block
    assert "'flame_bot_damage_reduction_pct': flame_bot_damage_reduction_pct" in boss_block
    assert "'boss_applicable_damage_factor': boss_applicable_damage_factor" in boss_block
    assert "'boss_edamage_target_share': boss_edamage_target_share" in boss_block
    assert "'boss_edamage_cadence_uptime_factor': boss_edamage_cadence_uptime_factor" in boss_block
    assert "'boss_edamage_reliability_factor': boss_edamage_reliability_factor" in boss_block
    assert "'boss_edamage_semantic_normalizer': boss_edamage_semantic_normalizer" in boss_block
    assert "'fleet_terminal_max_wave': fleet_terminal_max_wave" in boss_block
    assert "'elite_terminal_max_wave': elite_terminal_max_wave" in boss_block
    assert "'protector_terminal_max_wave': protector_terminal_max_wave" in boss_block
    assert "'armored_terminal_max_wave': armored_terminal_max_wave" in boss_block
    assert "decomposed_bridge_inputs" in boss_block
    assert "build_boss_wave_milestone_matrix(" in boss_block
    assert "Build all-tier 4-preset matrix" in boss_block
    assert "All-tier preset matrix" in boss_block
    assert "Matrix end wave" in boss_block
    assert "Matrix checkpoint cadence (bosses)" in boss_block
    assert "value=max(30000, int(end_wave))" in boss_block
    assert "value=max(10, int(boss_wave_step))" in boss_block
    assert "Build all-tier milestone matrix" not in boss_block
    assert "All-tier milestone matrix" not in boss_block
    assert "_boss_wave_preset_matrix_frame(matrix_payload)" in boss_block
    assert "candidate_count = sum(len(row.get('candidate_results') or []) for row in matrix_rows)" in boss_block
    assert "include_dissonance_run_matrix" not in boss_block
    assert "Dissonance comparison" not in boss_block
    assert "dissonance_run_matrix" not in boss_block
    assert "'tournament_wave': int(tournament_wave_override)" in boss_block
    assert "Legends tournament wave" in boss_block
    assert "boss_calc_elapsed" in boss_block
    assert "display_frame = _build_boss_wave_operator_frame(frame)" in boss_block
    assert "_require_boss_wave_payload_rows(boss_payload, 'operator_rows')" in boss_block
    assert "_require_boss_wave_payload_rows(boss_payload, 'download_rows')" in boss_block
    assert "boss_payload.get('rows') or []" not in boss_block
    assert "st.error(str(exc))" in boss_block
    assert "payload_summary = dict(boss_payload.get('summary') or {})" in boss_block
    assert "primitive_inputs = dict(payload_diagnostics.get('replacement_primitive_inputs') or {})" in boss_block
    assert "'terminal_pressure_limiter': payload_summary.get('terminal_pressure_limiter')" in boss_block
    assert "if diagnostics['terminal_pressure_limited']:" in boss_block
    assert "Blocked by `{diagnostics['terminal_pressure_limiter']}`" in boss_block
    assert "uncapped boss-only wave" in boss_block
    assert "_focus_boss_wave_display_frame(" in boss_block
    assert "_boss_wave_assumption_frame(" in boss_block
    assert "_boss_wave_runtime_inputs_frame(" in boss_block
    assert "metric('Rows'" not in boss_block
    assert "metric('Selected wave'" not in boss_block
    assert "metric('First failed wave'" not in boss_block
    assert "metric('Perk plan'" not in boss_block
    assert "metric('Tier'" not in boss_block
    assert "metric('Loadout'" not in boss_block
    assert "payload_diagnostics.get('model_certification') or {}" in boss_block
    assert "payload_diagnostics.get('contact_time_contract') or {}" in boss_block
    assert "payload_diagnostics.get('replacement_model') or {}" in boss_block
    assert "'replacement_primitive_inputs': primitive_inputs" in boss_block
    assert "payload_diagnostics.get('replacement_primitive_semantics_ledger') or {}" in boss_block
    assert "visible wall regen contribution" in boss_block

    helper_start = text.index("def _build_boss_wave_operator_frame(frame: pd.DataFrame) -> pd.DataFrame:")
    helper_end = text.index("\ndef _render_boss_waves(request: PipelineRunRequest", helper_start)
    helper_block = text[helper_start:helper_end]
    assert "'Wall Regen'" in helper_block
    assert "'Regen Gain'" in helper_block
    assert "'Boss Kill Time'" in helper_block
    assert "'Cont Dmg %'" in helper_block
    assert "'Hit Interval (s)'" in helper_block
    assert "'Damage Reduction'" in helper_block
    assert "'Killed Before Contact'" in helper_block
    assert "'Survival Margin'" in helper_block
    assert "def _boss_wave_assumption_frame(" in helper_block
    assert "'Boss damage source'" in helper_block
    assert "'Chain Lightning DPS'" in helper_block
    assert "'EP eDamage base'" in helper_block
    assert "'Spotlight exposure'" in helper_block
    assert "'ACP factor'" in helper_block
    assert "'EN mastery multiplier'" in helper_block
    assert "'Boss time to contact'" in helper_block
    assert "'Chrono Field slow'" in helper_block
    assert "'Slow Aura slow'" in helper_block
    assert "payload_diagnostics = dict(boss_payload.get('diagnostics') or {})" in boss_block
    assert "payload_download = dict(boss_payload.get('download') or {})" in boss_block
    assert "diagnostics['context_status'] not in {'resolved', 'complete'}" in boss_block
    assert "boss_payload.get('contract') or {}" in boss_block
    assert "actual_boss_interval_waves" in boss_block
    assert "checkpoint_every_bosses" in boss_block
    assert "Boss Waves is a bounded runtime estimate" in boss_block
    assert "Advanced boss-wave evidence" in boss_block
    assert "Full boss-wave table" not in boss_block
    assert "Boss-wave diagnostics" not in boss_block
    assert "Boss-wave raw rows (debug)" not in boss_block
    assert "Boss-wave execution details" not in boss_block
    assert "st.download_button(" in boss_block


def test_boss_wave_matrix_frame_exposes_model_honesty_columns() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("def _boss_wave_preset_matrix_frame(matrix_payload: dict[str, object])")
    end = text.index("\ndef _slug_text", start)
    matrix_block = text[start:end]
    assert "'Status': matrix_row.get('best_model_certification_status')" in matrix_block
    assert "'Limiter': matrix_row.get('terminal_pressure_limiter')" in matrix_block
    assert "'Unsupported': ', '.join" in matrix_block
    assert "'Status'" in matrix_block
    assert "'Limiter'" in matrix_block
    assert "'Unsupported'" in matrix_block


def test_boss_waves_renderer_payload_contract_fails_closed_without_selected_rows() -> None:
    from app.streamlit_inspector import _require_boss_wave_payload_rows

    assert _require_boss_wave_payload_rows({'operator_rows': []}, 'operator_rows') == []
    with pytest.raises(ValueError, match="operator_rows"):
        _require_boss_wave_payload_rows({'rows': [{'display_wave': 9}]}, 'operator_rows')
    with pytest.raises(ValueError, match="download_rows"):
        _require_boss_wave_payload_rows({'download_rows': {'display_wave': 9}}, 'download_rows')
    with pytest.raises(ValueError, match="download_rows"):
        _require_boss_wave_payload_rows({'download_rows': [object()]}, 'download_rows')


def test_inputs_dashboard_production_render_avoids_native_streamlit_tables() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("dashboard = active_artifacts.get('input_dashboard.json') or {}")
    end = text.index("with st.expander('Input lineage and artifact evidence'", start)
    production_block = text[start:end]
    assert 'st.table(' not in production_block
    assert 'st.dataframe(' not in production_block
    assert 'st.data_editor(' not in production_block


def test_input_lineage_debug_table_uses_arrow_safe_display_frame() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("st.subheader('Input lineage')")
    end = text.index("\ndef _require_boss_wave_payload_rows", start)
    lineage_block = text[start:end]

    assert "input_lineage_rows_frame(" in lineage_block
    assert "_arrow_safe_frame(lineage_frame, columns=('source_value', 'resolved_value'))" in lineage_block


def test_inputs_dashboard_cards_panel_uses_published_rows_without_account_state_mutation() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("elif panel_type == 'cards_inventory_and_preset':")
    end = text.index("elif panel_type == 'track_table':", start)
    cards_block = text[start:end]
    assert "payload.get('preset_rows_by_preset')" in cards_block
    assert "preset_rows_by_preset.get(selected_preset)" in cards_block
    assert "active_artifacts.get('account_state.json'" not in cards_block
    assert "st.error(" in cards_block


def test_stats_dashboard_production_render_avoids_native_streamlit_tables() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("dashboard = active_artifacts.get('stats_dashboard.json') or {}")
    end = text.index("with st.expander('Stats evidence and verification'", start)
    production_block = text[start:end]
    assert 'st.table(' not in production_block
    assert 'st.dataframe(' not in production_block
    assert 'st.data_editor(' not in production_block


def test_stats_dashboard_production_render_demotes_secondary_panels_and_guards_debug_failures() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert "Detailed QE rows and secondary context" in text
    assert "dashboard.get('secondary_panels')" in text
    assert "secondary_variants" in text
    assert "requested_preset = str(request.preset or '').strip()" in text
    assert "render_grouped_modules_html(payload)" in text
    assert "compare_df[['surface_id', 'ep_value', 'ep_value_raw', 'compare_preset', 'compare_perk_state', 'status', 'label']]" not in text
    assert "_render_stats_debug_tools(active_artifacts, comparison_artifacts, request)" in text
    assert "Stats evidence tools unavailable for this snapshot" in text
    for stale_label in (
        'Dashboard artifact debug (stats_dashboard.json)',
        'Dashboard artifact debug (input_dashboard.json)',
        'Stats debug and verification',
        'Legacy input debug views',
        'Raw artifacts',
    ):
        assert stale_label not in text


def test_load_streamlit_reference_data_uses_request_ids_path(monkeypatch, tmp_path):
    from app import pipeline as pipeline_mod

    captured: dict[str, object] = {}

    class _Bundle:
        perk_policy = {}

    def _fake_load_inputs(*, ids_path, manual_inputs_path):
        captured['ids_path'] = ids_path
        captured['manual_inputs_path'] = manual_inputs_path
        return _Bundle()

    monkeypatch.setattr(pipeline_mod, 'load_inputs', _fake_load_inputs)
    monkeypatch.setattr(pipeline_mod, 'load_perk_entities', lambda: {})

    ids_path = tmp_path / 'custom_ids.csv'
    ids_path.write_text('h1,h2\n', encoding='utf-8')
    manual_path = tmp_path / 'manual.yaml'
    manual_path.write_text('perk_policy: {}\n', encoding='utf-8')

    payload = pipeline_mod.load_streamlit_reference_data(ids_path=ids_path, manual_inputs_path=manual_path)

    assert captured['ids_path'] == ids_path
    assert captured['manual_inputs_path'] == manual_path
    assert isinstance(payload, dict)


def test_load_streamlit_reference_data_exposes_module_lookup_contract():
    from app.pipeline import load_streamlit_reference_data

    payload = load_streamlit_reference_data(
        ids_path=ROOT / 'input' / 'imports' / 'ids.csv',
        manual_inputs_path=None,
    )

    module_lookup = payload.get('module_substat_lookup')
    assert isinstance(module_lookup, dict)
    assert ('armor', 'Knockback Force') in module_lookup
    rows = module_lookup[('armor', 'Knockback Force')]
    assert isinstance(rows, list)
    assert rows
    assert {'rarity', 'unit', 'value'}.issubset(rows[0].keys())


def test_default_verification_matrix_requests_returns_expected_pairs(tmp_path):
    from app.pipeline import PipelineRunRequest, _default_verification_matrix_requests

    requests = _default_verification_matrix_requests(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'matrix',
        )
    )

    assert len(requests) == 4
    assert [(request.preset, request.state_mode) for request in requests] == [
        ('Farming', 'start_of_run'),
        ('Farming', 'max_progression'),
        ('Tourney', 'start_of_run'),
        ('Tourney', 'max_progression'),
    ]
    assert [request.perk_state for request in requests] == ['auto', 'auto', 'off', 'off']


def test_build_verification_snapshot_set_orchestrates_execution(monkeypatch, tmp_path):
    from app.models import PipelineRunResult, PipelineTrace
    from app.pipeline import PipelineRunRequest, build_verification_snapshot_set, _default_verification_matrix_requests

    captured_requests = []

    def _fake_execute_pipeline(request):
        captured_requests.append(request)
        return PipelineRunResult(
            exit_code=0,
            request=request,
            out_dir=request.out,
            diagnostics={},
            generated_files=(),
            pipeline_trace=PipelineTrace(request={}, execution_path={}, stages=[], artifacts_written=[]),
        )

    import app.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, 'execute_pipeline', _fake_execute_pipeline)
    base_request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'matrix',
    )
    expected_requests = _default_verification_matrix_requests(base_request)

    results = build_verification_snapshot_set(base_request)

    assert len(results) == len(expected_requests)
    assert captured_requests == list(expected_requests)
    assert [result.request for result in results] == list(expected_requests)


def test_resolve_fast_checkpoint_returns_requested_surfaces():
    from app.pipeline import FastCheckpointRequest, resolve_fast_checkpoint

    result = resolve_fast_checkpoint(
        FastCheckpointRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            preset='Farming',
            state_mode='start_of_run',
            requested_surface_ids=('state::tower.hp', 'state::wall.hp'),
        )
    )

    rows = result.statbook.get('rows') or {}
    assert result.diagnostics['resolver_kind'] == 'simulator_checkpoint_qe_light'
    assert set(rows) == {'state::tower.hp', 'state::wall.hp'}

