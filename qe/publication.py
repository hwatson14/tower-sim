from __future__ import annotations

import re
from typing import Any, Dict, Optional

from qe.contracts import normalize_surface_id_to_contract
from qe.query_currency_income import publish_currency_income_surfaces
from qe.query_derived_composites import publish_derived_composites
from qe.query_module_policy import (
    publish_module_draw_policy_surfaces,
    publish_module_drop_economy_surfaces,
    publish_module_lab_policy_surfaces,
    publish_module_mission_economy_surfaces,
    publish_module_runtime_policy_surfaces,
)
from qe.models import StatRow
from qe.workshop_stat_rows import build_workshop_reconciliation_row


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _publish_module_account_tier_surfaces(rows: Dict[str, StatRow]) -> None:
    """Derive module tier surfaces from the already-resolved account_context farming tier.

    Reads the raw-text farming tier contributor value (e.g. 'Tier 14') using the
    same regex extraction pattern as stat_resolution_core, then publishes:
      - derived::module.runtime_profile.farming_tier
      - derived::module.runtime_profile.highest_tier_unlocked
    Both are published as the same numeric tier; guards against collision with
    surfaces already pre-populated from manual advisory inputs.
    """
    tier_row = rows.get('state::meta.account_context.farming_tier')
    if tier_row is None:
        return
    raw = (tier_row.contributors[0].get('value') if tier_row.contributors else None)
    if not isinstance(raw, str):
        return
    m = re.search(r'(\d+)', raw)
    if not m:
        return
    tier = int(m.group(1))
    for surface_id in (
        'derived::module.runtime_profile.farming_tier',
        'derived::module.runtime_profile.highest_tier_unlocked',
    ):
        if surface_id in rows:
            continue
        rows[surface_id] = StatRow(
            stat_name=surface_id,
            final_value=float(tier),
            value_type='scalar',
            source_count=1,
            status='resolved',
            notes='Derived from account_context farming tier (IDS Player & Stuff) for module economy publishers.',
            contributors=[{
                'source_class': 'account_context',
                'value': tier,
                'unit': 'tier',
                'source_raw': raw,
                'source_surface': 'state::meta.account_context.farming_tier',
            }],
            schema={
                'source_alignment': 'AccountContext',
                'publisher': 'query_surface_publication',
                'unit': 'tier',
            },
        )


def publish_query_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Optional[Dict[str, Dict[str, Any]]] = None,
    account_state_labs: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish query-owned/public surfaces from already-resolved rows.

    This is intentionally separate from legacy derived-surface composition. The
    compatibility entrypoint may call it today, but later query entrypoints can
    call the same publication contract directly.

    account_state_labs: if provided (dict of lab_name → level), wires the module
    lab policy publisher which feeds into drop economy.
    """
    publish_derived_composites(rows)
    publish_module_runtime_policy_surfaces(rows, manual_advisory_inputs=manual_advisory_inputs)
    publish_module_draw_policy_surfaces(rows)
    _publish_module_account_tier_surfaces(rows)
    if account_state_labs is not None:
        publish_module_lab_policy_surfaces(rows, account_state_labs)
    if 'derived::module.runtime_profile.farming_tier' in rows:
        publish_module_drop_economy_surfaces(rows, manual_advisory_inputs)
    if 'derived::module.runtime_profile.highest_tier_unlocked' in rows:
        publish_module_mission_economy_surfaces(rows)
    publish_currency_income_surfaces(rows, manual_advisory_inputs=manual_advisory_inputs)


def publish_workshop_reconciliation_payload(
    *,
    stats_layout: dict[str, Any],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    account_state_payload: dict[str, object],
    selected_preset: str,
    surface_specs: callable,
) -> dict[str, object]:
    section_titles = {
        'offense_surfaces': 'Offense',
        'defense_surfaces': 'Defense',
        'utility_economy_surfaces': 'Utility',
    }
    sections: list[dict[str, object]] = []
    for section_key in ('offense_surfaces', 'defense_surfaces', 'utility_economy_surfaces'):
        rows: list[dict[str, object]] = []
        for spec in surface_specs(stats_layout, section_key):
            surface_id = spec['surface_id']
            rows.append(
                build_workshop_reconciliation_row(
                    spec=spec,
                    start_row=dict(rows_start.get(surface_id) or {}),
                    max_row=dict(rows_max.get(surface_id) or {}),
                    account_state_payload=account_state_payload,
                    selected_preset=selected_preset,
                )
            )
        if rows:
            sections.append({'section_id': section_key, 'title': section_titles[section_key], 'rows': rows})
    return {
        'artifact': 'qe_workshop_reconciliation_rows',
        'owner': 'qe',
        'sections': sections,
    }


def publication_contract_snapshot() -> dict:
    """Expose the intended publication contract for tests and audits."""
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
