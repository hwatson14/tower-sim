from __future__ import annotations

from qe.query_routing import compiler_routing_policy


def test_compiler_routing_policy_uses_split_classes() -> None:
    policy = compiler_routing_policy()

    assert 'parser_drop_rows' in policy
    assert 'account_metadata_rows' in policy
    assert 'capability_policy_rows' in policy
    assert 'governed_numeric_rows' in policy
    assert 'non_calculator_scope_labs' not in policy
