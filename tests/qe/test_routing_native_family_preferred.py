from __future__ import annotations

from qe.kernel import QueryResponse, ResolvedSurfaceRow
from qe.models import BoundStatInputs, StateIdentity, StateIdentityBinding, StatBook, StatInput, StatRow
from qe.routing import QEFamilyQueryResult
import qe.routing as routing_mod
import qe.stat_resolution as compat_mod


def _manifest_capable_input() -> StatInput:
    return StatInput(
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


def _native_response(*, family_id: str) -> QueryResponse:
    return QueryResponse(
        family_id=family_id,
        resolved_surface_rows=(
            ResolvedSurfaceRow(
                surface_id='state::tower.hp',
                final_value=123.0,
                value_type='flat',
                status='resolved',
            ),
        ),
        contributor_rows=tuple(),
        dependency_trace={},
    )


def test_resolve_hybrid_rows_uses_native_without_compat_first(monkeypatch) -> None:
    stat_inputs = [_manifest_capable_input()]

    def _fail_fallback(*_args, **_kwargs):
        raise AssertionError('compat fallback must not run before native-family resolution succeeds')

    def _fake_native_result(**kwargs):
        family_id = kwargs['family_id']
        return QEFamilyQueryResult(
            binding=None,
            stat_inputs=tuple(stat_inputs),
            family_id=family_id,
            requested_surface_ids=('state::tower.hp',),
            response=_native_response(family_id=family_id),
            resolution_path='native_family_query',
        )

    monkeypatch.setattr(routing_mod, '_fallback_resolve_stats', _fail_fallback)
    monkeypatch.setattr(routing_mod, '_build_rows_family_query_result', _fake_native_result)

    statbook = routing_mod.resolve_stats(stat_inputs)

    assert statbook.rows['state::tower.hp'].final_value == 123.0
    assert statbook.diagnostics['qe_resolution_backend'] == 'native_family_query'
    assert statbook.diagnostics['qe_native_family_available'] is True
    assert statbook.diagnostics['qe_native_family_id'] == 'progression_start_of_run'


def test_resolve_hybrid_bound_inputs_uses_native_without_compat_first(monkeypatch) -> None:
    stat_input = _manifest_capable_input()
    bound_inputs = BoundStatInputs(
        binding=StateIdentityBinding(
            identity=StateIdentity(
                account_snapshot_id='acct_test',
                loadout_id='loadout_test',
                scenario_id='scenario_test',
                runtime_branch_id='branch_base',
            ),
            account_state=None,
            scenario_runtime_inputs=None,
        ),
        stat_inputs=(stat_input,),
    )

    def _fail_fallback(*_args, **_kwargs):
        raise AssertionError('compat fallback must not run before native-family resolution succeeds')

    def _fake_native_result(*_args, **kwargs):
        family_id = kwargs['family_id']
        return QEFamilyQueryResult(
            binding=bound_inputs.binding,
            stat_inputs=bound_inputs.stat_inputs,
            family_id=family_id,
            requested_surface_ids=('state::tower.hp',),
            response=_native_response(family_id=family_id),
            resolution_path='native_family_query',
        )

    monkeypatch.setattr(routing_mod, '_fallback_resolve_stats', _fail_fallback)
    monkeypatch.setattr(routing_mod, '_build_family_query_result', _fake_native_result)

    statbook = routing_mod._resolve_hybrid_statbook_from_bound_inputs(bound_inputs)

    assert statbook.rows['state::tower.hp'].final_value == 123.0
    assert statbook.diagnostics['qe_resolution_backend'] == 'native_family_query'
    assert statbook.diagnostics['qe_native_family_available'] is True
    assert statbook.diagnostics['qe_native_family_id'] == 'progression_start_of_run'


def test_resolve_hybrid_rows_fallback_includes_explicit_reason(monkeypatch) -> None:
    stat_inputs = [_manifest_capable_input()]
    fallback_statbook = StatBook(
        rows={
            'state::tower.hp': StatRow(
                stat_name='state::tower.hp',
                final_value=99.0,
                value_type='flat',
                source_count=1,
                status='resolved',
                notes='fallback',
                contributors=[],
                schema=None,
            )
        },
        diagnostics={'seed': 'fallback'},
    )

    def _native_contract_failure(**_kwargs):
        raise ValueError('materializer contract check failed for test')

    monkeypatch.setattr(routing_mod, '_build_rows_family_query_result', _native_contract_failure)
    monkeypatch.setattr(routing_mod, '_fallback_resolve_stats', lambda *_args, **_kwargs: fallback_statbook)

    statbook = routing_mod.resolve_stats(stat_inputs)

    assert statbook.rows['state::tower.hp'].final_value == 99.0
    assert statbook.diagnostics['qe_native_family_fallback']['reason'] == 'native_contract_check_failed'
    assert statbook.diagnostics['qe_native_family_fallback']['native_family_id'] == 'progression_start_of_run'
    assert 'materializer contract check failed' in statbook.diagnostics['qe_native_family_fallback']['error']


def test_stat_resolution_bucket_value_delegates_to_routing_owner(monkeypatch) -> None:
    contributors = [_manifest_capable_input()]

    def _fake_resolver(destination_object_type, destination_id, _contributors, _meta):
        assert destination_object_type == 'canonical_stat'
        assert destination_id == 'tower_hp'
        return 777.0, 'resolved', 'delegated', {'unit': 'hp'}

    monkeypatch.setattr(routing_mod, 'resolve_bounded_bucket', _fake_resolver)

    value, status, notes, _schema, meta = compat_mod.resolve_bucket_value(
        'canonical_stat',
        'tower_hp',
        contributors,
        resolved_rows={},
    )

    assert value == 777.0
    assert status == 'resolved'
    assert notes == 'delegated'
    assert meta['unit'] == 'hp'
