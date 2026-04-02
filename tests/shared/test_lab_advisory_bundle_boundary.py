from __future__ import annotations

from advisors.upgrade_advisor import (
    get_lab_advisory_row,
    load_lab_advisory_rows,
    load_lab_advisory_rows_by_canonical_id,
    load_lab_advisory_source_registry,
)
from evaluators.ranker import load_lab_advisory_bundle


def test_lab_advisory_bundle_producer_and_advisor_consumer_contract():
    bundle = load_lab_advisory_bundle()

    rows = load_lab_advisory_rows(bundle)
    rows_by_id = load_lab_advisory_rows_by_canonical_id(bundle)
    source_registry = load_lab_advisory_source_registry(bundle)

    assert rows
    assert rows_by_id
    assert source_registry
    assert len(rows_by_id) == len(rows)


def test_get_lab_advisory_row_reads_from_evaluator_bundle():
    bundle = load_lab_advisory_bundle()
    first = bundle.advisory_rows[0]

    resolved = get_lab_advisory_row(bundle, first.lab_canonical_id)
    assert resolved.lab_canonical_id == first.lab_canonical_id
