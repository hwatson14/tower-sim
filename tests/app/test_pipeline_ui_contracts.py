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


def test_streamlit_boss_waves_exposes_only_wired_manual_runtime_inputs():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert 'Manual combat assumptions' in source
    assert "number_input('End wave', min_value=10, value=10000, step=10)" in source
    assert "number_input('Flame Bot boss hit chance (%)', min_value=0.0, max_value=100.0, value=50.0, step=1.0)" in source
    for label in (
        'Orb damage to boss (total %)',
        'Electron damage override (total %)',
        'Flame Bot boss hit chance (%)',
        'Boss time to contact (s)',
        'Death Wave maxed wave',
    ):
        assert label in source
    for stale_label in (
        'Orb boss hit %',
        'Effective DR %',
        'Incoming damage multiplier',
        'Death Wave health max x',
        'Boss hit interval (s)',
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
    assert 'save_perk_policy_override' in source
    assert 'Save perk policy' in source
    assert 'Banned perks' in source
    assert 'First perk choice' in source
    assert 'Priority order' in source
    assert 'Generated perks' in source
    assert 'generate_timeline_from_policy' not in source
    assert 'PerkTimelinePolicy' not in source


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

    assert start_farming['state::tower.free_attack_upgrade_chance_pct']['final_value'] == pytest.approx(75.9)
    assert max_farming['state::tower.free_attack_upgrade_chance_pct']['final_value'] == pytest.approx(111.8375)
    assert 'derived::wall.hp_pre_fort' in start_farming
    assert start_farming['derived::wall.hp_pre_fort']['final_value'] > 0
    assert max_farming['derived::wall.hp_pre_fort']['final_value'] > start_farming['derived::wall.hp_pre_fort']['final_value']
    assert start_farming['support_surface::ehp.black_hole_duration_seconds']['final_value'] == pytest.approx(32.0)
    assert start_farming['support_surface::ehp.black_hole_cooldown_seconds']['final_value'] == pytest.approx(50.0)
    assert start_farming['support_surface::ehp.health_relic_pct']['final_value'] == pytest.approx(0.51)
    assert start_farming['support_surface::ehp.dabs_relic_pct']['final_value'] == pytest.approx(0.28)
    assert start_farming['support_surface::ehp.def_pct_relic_pct']['final_value'] == pytest.approx(0.04)
    assert start_farming['support_surface::eecon.adstarter_theme_relic_factor']['final_value'] == pytest.approx(1.48)
    assert start_farming['support_surface::eecon.freeup_attack_relic_pct']['final_value'] == pytest.approx(0.06)
    assert start_farming['support_surface::eecon.freeup_defense_relic_pct']['final_value'] == pytest.approx(0.03)
    assert start_farming['support_surface::eecon.freeup_utility_relic_pct']['final_value'] == pytest.approx(0.05)
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
    assert start_farming['derived::ehp.health_relic_factor']['final_value'] == pytest.approx(1.51)
    assert start_farming['derived::ehp.dabs_relic_factor']['final_value'] == pytest.approx(1.28)
    assert start_farming['derived::ehp.def_pct_relic_term']['final_value'] == pytest.approx(0.04)
    assert start_farming['derived::eecon.base_meta_factor']['final_value'] == pytest.approx(1.48)


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
    assert "Checkpoint every N bosses" in boss_block
    assert "st.toggle('Stop on first failed boss', value=True)" in boss_block
    assert "display_frame = _build_boss_wave_operator_frame(frame)" in boss_block
    assert "_require_boss_wave_payload_rows(boss_payload, 'operator_rows')" in boss_block
    assert "_require_boss_wave_payload_rows(boss_payload, 'download_rows')" in boss_block
    assert "boss_payload.get('rows') or []" not in boss_block
    assert "st.error(str(exc))" in boss_block
    assert "payload_summary = dict(boss_payload.get('summary') or {})" in boss_block
    assert "visible wall regen contribution" in boss_block

    helper_start = text.index("def _build_boss_wave_operator_frame(frame: pd.DataFrame) -> pd.DataFrame:")
    helper_end = text.index("\ndef _render_boss_waves(request: PipelineRunRequest", helper_start)
    helper_block = text[helper_start:helper_end]
    assert "'Wall Regen'" in helper_block
    assert "'Regen Gain'" in helper_block
    assert "'TTK (s)'" in helper_block
    assert "payload_diagnostics = dict(boss_payload.get('diagnostics') or {})" in boss_block
    assert "payload_download = dict(boss_payload.get('download') or {})" in boss_block
    assert "boss_payload.get('contract') or {}" in boss_block
    assert "actual_boss_interval_waves" in boss_block
    assert "checkpoint_every_bosses" in boss_block
    assert "Boss Waves is a bounded runtime estimate" in boss_block
    assert "Boss-wave raw rows (debug)" in boss_block
    assert "st.download_button(" in boss_block


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
    end = text.index("with st.expander('Legacy input debug views'", start)
    production_block = text[start:end]
    assert 'st.table(' not in production_block
    assert 'st.dataframe(' not in production_block
    assert 'st.data_editor(' not in production_block


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
    end = text.index("with st.expander('Stats debug and verification'", start)
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
    assert "Stats debug tools unavailable for this snapshot" in text


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

