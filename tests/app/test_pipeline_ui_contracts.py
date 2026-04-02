from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_request_adapter_and_execute_pipeline_emit_trace(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'out',
        preset='Farming',
        state_mode='max_progression',
        manual_inputs=None,
        perk_mode='max_progression_policy',
        include_slow_audits=False,
        perk_state='auto',
    )
    result = execute_pipeline(request)

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
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == str(manual_inputs_override)


def test_trace_artifact_is_listed_in_generated_files(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'out',
        )
    )
    generated = {path.name for path in result.generated_files}
    assert 'pipeline_trace.json' in generated


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


def test_inputs_dashboard_production_render_avoids_native_streamlit_tables() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("dashboard = active_artifacts.get('input_dashboard.json') or {}")
    end = text.index("with st.expander('Legacy input debug views'", start)
    production_block = text[start:end]
    assert 'st.table(' not in production_block
    assert 'st.dataframe(' not in production_block
    assert 'st.data_editor(' not in production_block


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


def test_build_verification_snapshot_set_runs_default_matrix(tmp_path):
    from app.pipeline import PipelineRunRequest, build_verification_snapshot_set

    results = build_verification_snapshot_set(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'matrix',
        )
    )
    assert len(results) == 4
    labels = {(result.request.preset, result.request.state_mode) for result in results}
    assert ('Farming', 'start_of_run') in labels
    assert ('Farming', 'max_progression') in labels
    assert ('Tourney', 'start_of_run') in labels
    assert ('Tourney', 'max_progression') in labels


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
