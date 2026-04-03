from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_load_artifacts_tolerates_missing_optional_reports(tmp_path):
    from app.inspector_data import load_artifacts

    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    for name, payload in {
        'pipeline_trace.json': {'stages': [], 'execution_path': {}},
        'diagnostics.json': {'default_preset': 'Farming'},
        'account_state.json': {'card_presets': {}},
        'input_dashboard.json': {'schema_version': 2, 'panels': []},
        'stats_dashboard.json': {'schema_version': 1, 'panels': []},
        'statbook.json': {'rows': {}, 'diagnostics': {}},
        'statbook_publishable.json': {'rows': {}, 'diagnostics': {}},
        'run_stats.json': {'presets': {}},
        'run_stats_query_rows_start_of_run.json': {'Farming': {'rows': {}}},
        'run_stats_query_rows_max_progression.json': {'Farming': {'rows': {}}},
        'state_matrix.json': {},
        'ep_oracle_compare.json': {},
        'line_by_line_verification.json': {},
        'audit_surface_manifest.json': {},
        'family_completeness_matrix.json': {},
    }.items():
        (out_dir / name).write_text(json.dumps(payload), encoding='utf-8')

    artifacts = load_artifacts(out_dir)
    assert artifacts.get('diagnostics.json', {})['default_preset'] == 'Farming'
    assert artifacts.get('input_dashboard.json', {})['schema_version'] == 2
    assert artifacts.get('stats_dashboard.json', {})['schema_version'] == 1
    assert artifacts.get('tower_regen_closure_report.json', {}) == {}


def test_load_artifacts_missing_input_dashboard_returns_empty_dict(tmp_path):
    from app.inspector_data import load_artifacts

    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    (out_dir / 'pipeline_trace.json').write_text(json.dumps({'stages': [], 'execution_path': {}}), encoding='utf-8')
    (out_dir / 'diagnostics.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'account_state.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'statbook.json').write_text(json.dumps({'rows': {}, 'diagnostics': {}}), encoding='utf-8')
    (out_dir / 'statbook_publishable.json').write_text(json.dumps({'rows': {}, 'diagnostics': {}}), encoding='utf-8')
    (out_dir / 'run_stats.json').write_text(json.dumps({'presets': {}}), encoding='utf-8')
    (out_dir / 'run_stats_query_rows_start_of_run.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'run_stats_query_rows_max_progression.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'run_stats_query_plan_start_of_run.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'run_stats_query_plan_max_progression.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'state_matrix.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'ep_oracle_compare.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'line_by_line_verification.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'audit_surface_manifest.json').write_text(json.dumps({}), encoding='utf-8')
    (out_dir / 'family_completeness_matrix.json').write_text(json.dumps({}), encoding='utf-8')

    artifacts = load_artifacts(out_dir)
    assert artifacts.get('input_dashboard.json') == {}


def test_query_rows_dual_state_frame_and_surface_detail_share_normalized_path():
    from app.inspector_data import query_rows_dual_state_frame, query_rows_surface_detail

    start_rows = {
        'Farming': {
            'rows': {
                'canonical_stat::tower_damage': {'final_value': 10, 'display_value': '10', 'value_type': 'scalar', 'status': 'resolved'},
            }
        }
    }
    max_rows = {
        'Farming': {
            'rows': {
                'state::tower.damage': {'final_value': 20, 'display_value': '20', 'value_type': 'scalar', 'status': 'resolved'},
            }
        }
    }

    frame = query_rows_dual_state_frame(start_rows, max_rows, preset='Farming')
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row['surface_id'] == 'state::tower.damage'
    assert row['start_of_run_value'] == 10
    assert row['max_progression_value'] == 20
    assert row['raw_surface_id'] == 'canonical_stat::tower_damage'
    assert row['start_raw_surface_id'] == 'canonical_stat::tower_damage'
    assert row['max_raw_surface_id'] == 'state::tower.damage'
    assert bool(row['raw_surface_id_mismatch']) is True

    detail = query_rows_surface_detail(max_rows, preset='Farming', surface_id='state::tower.damage')
    assert detail['display_value'] == '20'


def test_statbook_rows_frame_groups_mixed_surface_ids():
    from app.inspector_data import statbook_rows_frame

    frame = statbook_rows_frame(
        {
            'rows': {
                'state::tower.hp': {'final_value': 100, 'display_value': '100', 'value_type': 'scalar', 'status': 'resolved', 'contributors': []},
                'mechanic_param::uw.black_hole.cooldown_seconds': {'final_value': 50, 'display_value': '50', 'value_type': 'seconds', 'status': 'resolved', 'contributors': []},
                'environment_param::enemy.boss.damage_multiplier': {'final_value': 2, 'display_value': 'x2', 'value_type': 'multiplier', 'status': 'resolved', 'contributors': []},
            }
        }
    )
    groups = set(frame['group'].tolist())
    assert 'Tower' in groups
    assert 'Ultimate Weapons' in groups
    assert 'Context' in groups
    assert 'raw_surface_id' in frame.columns
    uw_row = frame.loc[frame['raw_surface_id'] == 'mechanic_param::uw.black_hole.cooldown_seconds'].iloc[0]
    assert uw_row['surface_id'] == 'state::uw.black_hole.cooldown_seconds'


def test_run_stats_rows_frame_preserves_all_stats_and_normalizes_ids():
    from app.inspector_data import run_stats_rows_frame

    frame = run_stats_rows_frame(
        {
            'presets': {
                'Farming': {
                    'stats': {
                        'rows': {
                            'canonical_stat::tower_damage': {
                                'changed_in_max_progression': True,
                                'start_of_run': {'final_value': 10, 'display_value': '10', 'value_type': 'scalar', 'status': 'resolved'},
                                'max_progression': {'final_value': 20, 'display_value': '20', 'value_type': 'scalar', 'status': 'resolved'},
                            }
                        }
                    }
                }
            }
        },
        preset='Farming',
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row['raw_surface_id'] == 'canonical_stat::tower_damage'
    assert row['surface_id'] == 'state::tower.damage'
    assert row['start_of_run_value'] == 10
    assert row['max_progression_value'] == 20


def test_dual_state_statbook_rows_frame_preserves_raw_surface_provenance():
    from app.inspector_data import dual_state_statbook_rows_frame

    frame = dual_state_statbook_rows_frame(
        {
            'Farming': {
                'rows': {
                    'canonical_stat::tower_damage': {'final_value': 10, 'display_value': '10', 'value_type': 'scalar', 'status': 'resolved'},
                }
            }
        },
        {
            'Farming': {
                'rows': {
                    'state::tower.damage': {'final_value': 12, 'display_value': '12', 'value_type': 'scalar', 'status': 'resolved'},
                }
            }
        },
        preset='Farming',
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row['surface_id'] == 'state::tower.damage'
    assert row['raw_surface_id'] == 'canonical_stat::tower_damage'
    assert row['start_raw_surface_id'] == 'canonical_stat::tower_damage'
    assert row['max_raw_surface_id'] == 'state::tower.damage'
    assert bool(row['raw_surface_id_mismatch']) is True


def test_input_lineage_rows_frame_projects_source_and_resolved_columns():
    from app.inspector_data import input_lineage_rows_frame

    frame = input_lineage_rows_frame(
        [
            {
                'stage': 'account_state',
                'source_family': 'lab',
                'source_name': 'Game Speed',
                'value': 5.0,
                'destination_object_type': 'runtime_mechanic_param',
                'destination_id': 'game_runtime.speed_multiplier',
                'kb_mapped': True,
            },
            {
                'stage': 'account_state',
                'source_family': 'lab',
                'stat_name': 'Workshop Defense Discount',
                'value': 28,
                'kb_mapped': False,
            },
        ]
    )

    assert list(frame.columns) == [
        'source_group',
        'source_key',
        'source_value',
        'resolved_surface_id',
        'resolved_value',
        'mapping_status',
    ]
    mapped_row = frame.loc[frame['source_key'] == 'Game Speed'].iloc[0]
    assert mapped_row['source_group'] == 'account_state:lab'
    assert mapped_row['resolved_surface_id'] == 'state::meta.game_speed_multiplier'
    assert mapped_row['resolved_value'] == 5.0
    assert mapped_row['mapping_status'] == 'mapped'

    unmapped_row = frame.loc[frame['source_key'] == 'Workshop Defense Discount'].iloc[0]
    assert unmapped_row['resolved_surface_id'] is None
    assert unmapped_row['mapping_status'] == 'unmapped'


def test_input_lineage_rows_frame_prefers_account_state_source_values_when_available():
    from app.inspector_data import input_lineage_rows_frame

    frame = input_lineage_rows_frame(
        [
            {
                'stage': 'account_state',
                'source_family': 'lab',
                'source_name': 'Game Speed',
                'value': 5.0,
                'destination_object_type': 'runtime_mechanic_param',
                'destination_id': 'game_runtime.speed_multiplier',
                'kb_mapped': True,
            }
        ],
        account_state_payload={
            'labs': {
                'Game Speed': 7,
            }
        },
    )

    row = frame.iloc[0]
    assert row['source_value'] == 7
    assert row['resolved_value'] == 5.0


def test_qe_query_helpers_build_expected_contract_frames():
    from app.inspector_data import (
        qe_contributor_rows_frame,
        qe_dependency_nodes_frame,
        qe_plan_coverage_frame,
        qe_query_rows_frame,
        qe_surface_payload,
        qe_trace_steps_frame,
        qe_trace_summary_frame,
    )

    query_rows_payload = {
        'Farming': {
            'rows': {
                'state::tower.damage': {
                    'status': 'resolved',
                    'display_value': '42',
                    'final_value': 42.0,
                    'value_type': 'scalar',
                    'bundle_id': 'bundle-A',
                    'family_id': 'family-A',
                    'resolution_order_index': 0,
                    'contributors': [{'contributor_id': 'c1', 'display_value': '2.0', 'value': 2.0}],
                    'dependency_trace': {
                        'trace_contract_id': 'trace-1',
                        'trace_mode': 'full',
                        'resolution_order_index': 0,
                        'has_runtime_trace_steps': True,
                        'trace_steps': [{'step_index': 1, 'node_id': 'node-1'}],
                        'input_nodes': ['i-1'],
                        'calculation_nodes': ['c-1'],
                        'output_nodes': ['o-1'],
                    },
                }
            }
        }
    }
    query_plan_payload = {
        'presets': {
            'Farming': {
                'progression': {
                    'bundle_id': 'bundle-A',
                    'family_id': 'family-A',
                    'resolved_surface_ids': ['state::tower.damage'],
                }
            }
        }
    }

    query_frame = qe_query_rows_frame(query_rows_payload, preset='Farming')
    assert len(query_frame) == 1
    assert query_frame.iloc[0]['surface_id'] == 'state::tower.damage'

    row_payload = qe_surface_payload(query_rows_payload, preset='Farming', surface_id='state::tower.damage')
    assert row_payload['status'] == 'resolved'
    assert row_payload['family_id'] == 'family-A'

    summary_frame = qe_trace_summary_frame(row_payload.get('dependency_trace') or {})
    assert set(summary_frame.columns) == {'field', 'value'}

    contributors = qe_contributor_rows_frame(row_payload)
    assert len(contributors) == 1
    assert contributors.iloc[0]['contributor_id'] == 'c1'

    trace_steps = qe_trace_steps_frame(row_payload.get('dependency_trace') or {})
    assert len(trace_steps) == 1
    assert trace_steps.iloc[0]['node_id'] == 'node-1'

    input_nodes = qe_dependency_nodes_frame(row_payload.get('dependency_trace') or {}, field_name='input_nodes')
    assert len(input_nodes) == 1
    assert input_nodes.iloc[0]['node_id'] == 'i-1'

    coverage = qe_plan_coverage_frame(query_plan_payload, preset='Farming', surface_id='state::tower.damage')
    assert len(coverage) == 1
    assert coverage.iloc[0]['bundle_kind'] == 'progression'


def test_run_stats_section_name_groups_expected_surfaces():
    from app.inspector_data import RUN_STATS_SECTION_ORDER, run_stats_section_name

    assert run_stats_section_name('state::tower.damage') == 'Workshop Offense'
    assert run_stats_section_name('state::tower.hp') == 'Workshop Defense'
    assert run_stats_section_name('state::tower.enemy_health_level_skip_pct') == 'Workshop Utility'
    assert run_stats_section_name('state::uw.black_hole.damage_multiplier') == 'Ultimate Weapons'
    assert run_stats_section_name('derived::ehp_total') == 'Workshop Defense'
    assert RUN_STATS_SECTION_ORDER[0] == 'Workshop Offense'
    assert RUN_STATS_SECTION_ORDER[-1] == 'Other'
