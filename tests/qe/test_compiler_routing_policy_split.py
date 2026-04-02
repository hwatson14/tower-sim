from __future__ import annotations

from pathlib import Path

from qe.query_routing import compiler_routing_policy
from qe.models import StatBook, StatInput, StatRow
import qe.routing as routing_mod


def test_compiler_routing_policy_uses_split_classes() -> None:
    policy = compiler_routing_policy()

    assert 'parser_drop_rows' in policy
    assert 'account_metadata_rows' in policy
    assert 'capability_policy_rows' in policy
    assert 'governed_numeric_rows' in policy
    assert 'non_calculator_scope_labs' not in policy


def test_kernel_no_longer_uses_module_level_qe_stat_resolution_import() -> None:
    src = Path('qe/kernel.py').read_text(encoding='utf-8')
    assert '\nfrom qe.stat_resolution import resolve_bucket_value\n' not in src
    assert 'def _resolve_bucket_value_via_bridge(' not in src
    assert 'from qe.routing import load_bounded_resolution_metadata, resolve_bounded_bucket' in src


def test_resolve_stats_delta_uses_native_path_for_manifest_family(monkeypatch) -> None:
    base_inputs = [
        StatInput(
            stat_name='canonical_stat::tower_hp',
            source_family='workshop',
            source_name='Health',
            value=100.0,
            value_type='flat',
            stage='account_state',
            active=True,
            destination_object_type='canonical_stat',
            destination_id='tower_hp',
            preset_name='Farming',
        )
    ]
    target_inputs = [
        StatInput(
            stat_name='canonical_stat::tower_hp',
            source_family='workshop',
            source_name='Health',
            value=120.0,
            value_type='flat',
            stage='account_state',
            active=True,
            destination_object_type='canonical_stat',
            destination_id='tower_hp',
            preset_name='Farming',
        )
    ]
    base_statbook = StatBook(
        rows={
            'state::tower.hp': StatRow(
                stat_name='state::tower.hp',
                final_value=100.0,
                value_type='flat',
                source_count=1,
                status='resolved',
                notes='seed',
                contributors=[],
                schema=None,
            )
        },
        diagnostics={},
    )

    def _fail_fallback(*_args, **_kwargs):
        raise AssertionError('fallback delta should not be used for manifest-approved native family')

    monkeypatch.setattr(routing_mod, '_fallback_resolve_stats_delta', _fail_fallback)
    result = routing_mod.resolve_stats_delta(
        base_statbook=base_statbook,
        base_stat_inputs=base_inputs,
        target_stat_inputs=target_inputs,
    )

    delta = result.diagnostics.get('delta_resolution') or {}
    assert delta.get('path') == 'native_family_query_delta_no_compat_fallback'
