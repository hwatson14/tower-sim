from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from engine.query_routing import to_legacy_surface_id
from models.statbook import StatBook, StatRow


@dataclass(frozen=True)
class IncrementalParityResult:
    status: str
    compared_nodes: list[str]
    mismatches: Dict[str, dict]


def _row_view(row: StatRow) -> dict:
    return {
        'final_value': row.final_value,
        'value_type': row.value_type,
        'status': row.status,
        'source_count': row.source_count,
        'notes': row.notes,
    }


class IncrementalParityHarness:
    def compare(self, candidate_rows: Dict[str, StatRow], reference_statbook: StatBook) -> IncrementalParityResult:
        mismatches: Dict[str, dict] = {}
        compared = sorted(candidate_rows.keys())
        for node in compared:
            candidate = candidate_rows[node]
            reference = reference_statbook.rows.get(node)
            if reference is None:
                legacy_node = to_legacy_surface_id(node)
                if legacy_node != node:
                    reference = reference_statbook.rows.get(legacy_node)
            if reference is None:
                mismatches[node] = {'reason': 'missing_reference_row'}
                continue
            if _row_view(candidate) != _row_view(reference):
                mismatches[node] = {
                    'candidate': _row_view(candidate),
                    'reference': _row_view(reference),
                }
        return IncrementalParityResult(
            status='pass' if not mismatches else 'fail',
            compared_nodes=compared,
            mismatches=mismatches,
        )
