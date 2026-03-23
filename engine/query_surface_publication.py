from __future__ import annotations

from pathlib import Path
from typing import Dict

from engine.query_currency_income import publish_currency_income_surfaces
from engine.query_derived_composites import publish_derived_composites
from models.statbook import StatRow


def publish_phase3_query_surfaces(rows: Dict[str, StatRow], manual_input_path: str | Path | None = None) -> None:
    """Publish Phase 3 query-owned/public surfaces from already-resolved rows.

    This is intentionally separate from legacy derived-surface composition. The
    compatibility entrypoint may call it today, but later query entrypoints can
    call the same publication contract directly.
    """
    publish_derived_composites(rows)
    publish_currency_income_surfaces(rows, manual_input_path=manual_input_path)



def phase3_publication_contract_snapshot() -> dict:
    """Expose the intended Phase 3 publication contract for tests and audits."""
    return {
        'required_objective_surfaces': [
            'derived::ehp',
            'derived::edamage',
            'derived::eecon',
        ],
        'ep_objective_surfaces': [
            'derived::ehp_ep',
            'derived::edamage_ep',
            'derived::eecon_ep',
        ],
        'ep_helper_prefixes': [
            'derived::ehp_ep_helper.',
            'derived::edamage_ep_helper.',
            'derived::eecon_ep_helper.',
        ],
        'forbidden_legacy_prefixes': [
            'objective_state::',
        ],
    }
