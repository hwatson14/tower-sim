from __future__ import annotations

import csv
from pathlib import Path
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_FORMULA_REGISTRY = REPO_ROOT / 'kb/formulas/tables/canonical-formula-registry.csv'
FORMULA_AUTHORITY_POLICY = REPO_ROOT / 'kb/formulas/tables/formula-authority-classification-policy.csv'
FORMULA_COVERAGE_LEDGER = REPO_ROOT / 'kb/ledgers/tables/formula-coverage-ledger.csv'
EFFECTIVE_PATHS_REGISTRY = REPO_ROOT / 'kb/ledgers/tables/effective-paths-formula-registry.csv'
FORMULA_SURFACE_POLICY = REPO_ROOT / 'kb/ledgers/formula_surface_policy.yaml'

APPROVED_AUTHORITY_CLASSIFICATIONS = {
    'canonical_in_canonical_formula_registry',
    'canonical_in_non_formula_table_by_design',
    'intentionally_de_scoped',
}

DISALLOWED_AMBIGUOUS_STATUSES = {
    'sourced_but_unsurfaced',
    'sourced_not_active_canon',
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        rows: list[dict[str, str]] = []
        for row in csv.DictReader(handle):
            clean = {k: v for k, v in row.items() if k is not None}
            rows.append(clean)
    return rows


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def test_formula_authority_policy_classifies_every_surface() -> None:
    policy_rows = _read_csv(FORMULA_AUTHORITY_POLICY)

    policy_lookup = {
        (row['mechanic_type'], row['mechanic_id']): row
        for row in policy_rows
    }

    assert all(
        row['authority_classification'] in APPROVED_AUTHORITY_CLASSIFICATIONS
        for row in policy_rows
    )

    for row in _read_csv(CANONICAL_FORMULA_REGISTRY):
        key = ('formula_id', row['formula_id'])
        assert key in policy_lookup, f'missing authority policy row for canonical formula {row["formula_id"]!r}'
        assert policy_lookup[key]['authority_classification'] == 'canonical_in_canonical_formula_registry'

    for row in _read_csv(FORMULA_COVERAGE_LEDGER):
        key = ('formula_area', row['formula_area'])
        assert key in policy_lookup, f'missing authority policy row for formula area {row["formula_area"]!r}'
        assert policy_lookup[key]['authority_classification'] in {
            'canonical_in_non_formula_table_by_design',
            'intentionally_de_scoped',
        }

    for row in _read_csv(EFFECTIVE_PATHS_REGISTRY):
        key = ('effective_paths_formula_id', row['formula_id'])
        assert key in policy_lookup, f'missing authority policy row for EP formula {row["formula_id"]!r}'
        assert policy_lookup[key]['authority_classification'] == 'intentionally_de_scoped'


def test_formula_ledgers_do_not_use_ambiguous_source_only_states() -> None:
    coverage_statuses = {row['status'] for row in _read_csv(FORMULA_COVERAGE_LEDGER)}
    ep_statuses = {row['status'] for row in _read_csv(EFFECTIVE_PATHS_REGISTRY)}

    assert DISALLOWED_AMBIGUOUS_STATUSES.isdisjoint(coverage_statuses)
    assert DISALLOWED_AMBIGUOUS_STATUSES.isdisjoint(ep_statuses)


def test_intentional_de_scope_rows_require_reason_code() -> None:
    for row in _read_csv(FORMULA_COVERAGE_LEDGER):
        if row.get('authority_classification') == 'intentionally_de_scoped':
            assert row.get('authority_reason_code')

    for row in _read_csv(EFFECTIVE_PATHS_REGISTRY):
        if row.get('authority_classification') == 'intentionally_de_scoped':
            assert row.get('authority_reason_code')


def test_formula_surface_policy_has_no_publish_block_entries() -> None:
    policy = _read_yaml(FORMULA_SURFACE_POLICY)
    blocked = {
        surface_id: contract
        for surface_id, contract in (policy.get('surfaces') or {}).items()
        if (contract or {}).get('publish_policy') == 'block'
    }
    assert blocked == {}
