from __future__ import annotations

from typing import Dict

from qe.models import StatBook, StatRow


class IncrementalOverlayPublisher:
    """Publish candidate rows over a cached reference statbook.

    Performance rule for the guarded cached path: preserve unchanged rows by
    structural sharing and only replace the candidate rows plus diagnostics.
    The cached reference statbook must therefore be treated as immutable by the
    caller.
    """

    def publish(self, reference_statbook: StatBook, candidate_rows: Dict[str, StatRow]) -> StatBook:
        merged_rows = dict(reference_statbook.rows)
        merged_rows.update(candidate_rows)
        merged_diagnostics = dict(reference_statbook.diagnostics)
        merged_diagnostics['incremental_overlay'] = {
            'published_nodes': sorted(candidate_rows.keys()),
            'status': 'published_candidate_overlay_over_full_reference',
            'sharing_mode': 'structural_share_unchanged_rows',
        }
        return StatBook(rows=merged_rows, diagnostics=merged_diagnostics)
