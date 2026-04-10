from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from qe.contracts import compat_surface_from_legacy_canonical, load_section_layout_contract, normalize_surface_id_to_contract
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
from input.lab_category_registry import load_lab_category_registry_by_raw_name


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
    derived_rows: list[dict[str, object]] = []
    for spec in surface_specs(stats_layout, 'derived_wall_economy_surfaces'):
        surface_id = spec['surface_id']
        start_row = dict(rows_start.get(surface_id) or {})
        max_row = dict(rows_max.get(surface_id) or {})
        start_display = start_row.get('display_value')
        max_display = max_row.get('display_value')
        if not isinstance(start_display, str) or not start_display.strip():
            start_display = '—'
        if not isinstance(max_display, str) or not max_display.strip():
            max_display = '—'
        row_status = str(start_row.get('status') or max_row.get('status') or 'missing')
        derived_rows.append({
            'canonical_row_id': str(spec.get('canonical_row_id') or surface_id),
            'display_label': spec['label'],
            'value_format': {
                'value_type': str(start_row.get('value_type') or max_row.get('value_type') or 'scalar'),
                'display_kind': 'scalar',
            },
            'start_of_run': start_display,
            'max_workshop': max_display,
            'decomposition': {
                'workshop': '—',
                'lab': '—',
                'module': '—',
                'card': '—',
                'enhancement': '—',
                'relic': '—',
                'perk': '—',
                'other': '—',
            },
            'row_status': row_status,
            'row_notes': str(start_row.get('notes') or max_row.get('notes') or ''),
            'name': spec['label'],
            'workshop_level': '—',
            'workshop_value': '—',
            'lab_effects': '—',
            'module_effects': '—',
            'card_effects': '—',
            'enhancement_effects': '—',
            'relics': '—',
            'start_of_run_modifier_total': '—',
            'start_of_run_value': start_display,
            'max_workshop_value': '—',
            'perk_effects': '—',
            'other': '—',
            'max_progression_modifier_total': '—',
            'max_progression_value': max_display,
        })
    if derived_rows:
        sections.append({'section_id': 'derived_wall_economy_surfaces', 'title': 'Derived', 'rows': derived_rows})
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


def _dashboard_token_row(row: list[object], width: int) -> list[str]:
    tokens = [str(value).strip() for value in list(row or [])[:width]]
    if len(tokens) < width:
        tokens.extend([''] * (width - len(tokens)))
    return tokens


def _dashboard_gap(panel_id: str, gap_id: str, detail: str) -> dict[str, str]:
    return {'panel_id': panel_id, 'gap_id': gap_id, 'detail': detail}


def _dashboard_display_token(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _stats_dashboard_contract_manifest() -> dict[str, object]:
    return {
        'owner': 'qe',
        'row_contract_model': 'qe_workshop_reconciliation_rows',
        'row_status_semantics': [
            'resolved',
            'partially_resolved',
            'mapped_not_resolved',
            'missing',
            'non_recon',
            'not_applicable',
        ],
        'missingness_rule': 'Do not backfill missing canonical QE rows from line_verification or input_dashboard context payloads.',
        'no_backfill_sources': [
            'line_verification',
            'input_dashboard',
        ],
        'panel_acceptance': [
            {
                'panel_id': 'workshop',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'Counts toward current canonical visible-stat completion. Missingness and row status are QE-owned.',
            },
            {
                'panel_id': 'derived',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned canonical overview rows with explicit start/max visibility and row status semantics.',
            },
            {
                'panel_id': 'offense_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned offense stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'defense_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned defense stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'utility_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned utility and economy stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'wall_economy_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned derived wall and economy rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'cards_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned card stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'bots_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned bot stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'guardians_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned guardian stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'modules_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned module stat rows published directly from the canonical visible-surface contract.',
            },
            {
                'panel_id': 'uw_stats_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'active',
                'notes': 'QE-owned ultimate-weapon stat rows published directly from the canonical visible-surface contract.',
            },
        ],
    }


def preset_options(account_state_payload: dict) -> list[str]:
    default_preset = str(account_state_payload.get('default_preset') or 'Farming')
    canonical_order = ['Farming', 'Tourney', 'Milestone', 'Preset 4', 'Preset 5']
    source_options: list[str] = []
    seen: set[str] = set()

    def _add_option(name: object) -> None:
        value = str(name).strip()
        if value and value not in seen:
            seen.add(value)
            source_options.append(value)

    for preset_name in (account_state_payload.get('card_presets') or {}).keys():
        _add_option(preset_name)
    for preset_name in (account_state_payload.get('module_presets') or {}).keys():
        _add_option(preset_name)
    for row in (account_state_payload.get('workshop') or {}).values():
        for preset_name in dict((row or {}).get('preset_levels') or {}).keys():
            _add_option(preset_name)
        for preset_name in dict((row or {}).get('preset_values') or {}).keys():
            _add_option(preset_name)
    for row in (account_state_payload.get('workshop_enhancement_tracks') or {}).values():
        for preset_name in dict((row or {}).get('preset_levels') or {}).keys():
            _add_option(preset_name)
    _add_option(default_preset)
    if not source_options and len(seen) == 1:
        return [default_preset] if default_preset else ['Farming']
    options = [name for name in canonical_order if name in seen]
    options.extend(name for name in source_options if name not in canonical_order)
    return options or ['Farming']


def build_labs_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    raw_rows = list(((account_state_payload.get('raw_sections') or {}).get('Labs') or []))
    labs_rows = []
    for row in raw_rows:
        name, level, _target, max_level = _dashboard_token_row(row, 4)
        if name and name != 'END OF ARRAY':
            labs_rows.append({'name': name, 'level': level, 'max': max_level})
    section_layout = load_section_layout_contract()
    labs_layout = dict(section_layout.get('labs') or {})
    bucket_order = [str(name) for name in (labs_layout.get('bucket_order') or [])]
    bucket_labels = {str(k): str(v) for k, v in (labs_layout.get('bucket_labels') or {}).items()}
    lab_category_registry = load_lab_category_registry_by_raw_name()
    rows_by_bucket: dict[str, list[dict[str, str]]] = {}
    gaps: list[dict[str, str]] = []
    for row in labs_rows:
        taxonomy = lab_category_registry.get(row['name']) or {}
        bucket_id = str(taxonomy.get('category_ui') or 'misc')
        if bucket_id == 'misc':
            gaps.append(_dashboard_gap('labs', 'lab_category_registry_missing', f'Lab category mapping missing for {row["name"]}'))
        rows_by_bucket.setdefault(bucket_id, []).append(row)
    buckets = []
    for bucket_id in bucket_order:
        rows = rows_by_bucket.get(bucket_id) or []
        if rows:
            buckets.append({'bucket_id': bucket_id, 'bucket_label': bucket_labels.get(bucket_id, bucket_id.replace('_', ' ').title()), 'rows': rows})
    for bucket_id, rows in rows_by_bucket.items():
        if rows and bucket_id not in bucket_order:
            buckets.append({'bucket_id': bucket_id, 'bucket_label': bucket_labels.get(bucket_id, bucket_id.replace('_', ' ').title()), 'rows': rows})
    return (
        {
            'panel_id': 'labs',
            'panel_type': 'labs_bucket_grid',
            'title': 'Labs',
            'payload': {'column_headers': ['Name', 'Level', 'Max'], 'bucket_order': bucket_order, 'buckets': buckets},
        },
        gaps,
    )


def build_input_dashboard_qe_publications(
    *,
    account_state,
    compare_rows_by_preset: dict[str, dict],
    projected_compare_rows_by_preset: dict[str, dict],
    stat_inputs: list,
    preset_name: str,
) -> dict[str, object]:
    current_preset_rows = dict(compare_rows_by_preset.get(preset_name) or {})
    current_normalized_rows = {normalize_surface_id_to_contract(raw): dict(payload or {}) for raw, payload in current_preset_rows.items()}
    projected_preset_rows = dict(projected_compare_rows_by_preset.get(preset_name) or {})
    projected_normalized_rows = {
        normalize_surface_id_to_contract(raw): dict(payload or {}) for raw, payload in projected_preset_rows.items()
    }

    def _surface_id_candidates_from_row(row: object) -> list[str]:
        candidates: list[str] = []

        def _add_candidate(value: object) -> None:
            text = str(value or '').strip()
            if text and text not in candidates:
                candidates.append(text)

        destination_id = str(getattr(row, 'destination_id', '') or '').strip()
        if destination_id:
            _add_candidate(destination_id)
            _add_candidate(normalize_surface_id_to_contract(destination_id))
            if not destination_id.startswith('state::'):
                _add_candidate(f'state::{destination_id}')
            if '_' in destination_id and not destination_id.startswith('state::'):
                prefix, tail = destination_id.split('_', 1)
                _add_candidate(f'state::{prefix}.{tail}')
                _add_candidate(f"state::{destination_id.replace('_', '.')}")
            compat_surface = str(compat_surface_from_legacy_canonical(destination_id) or '').strip()
            if compat_surface:
                _add_candidate(compat_surface)

        contributor_id = str(getattr(row, 'contributor_id', '') or '').strip()
        parts = contributor_id.split('__')
        if len(parts) >= 3 and parts[1] and parts[2]:
            _add_candidate(f"state::{parts[1]}.{parts[2]}")
            if len(parts) >= 4 and parts[3]:
                _add_candidate(f"state::{parts[1]}.{parts[2]}.{parts[3]}")
            if parts[0] == 'uw_upgrade':
                uw_prefix = parts[1].replace('_', '.')
                _add_candidate(f"state::uw.{uw_prefix}.{parts[2]}")
                if len(parts) >= 4 and parts[3]:
                    _add_candidate(f"state::uw.{uw_prefix}.{parts[2]}_{parts[3]}")
                    _add_candidate(f"state::uw.{uw_prefix}.{parts[2]}.{parts[3]}")
        return candidates

    workshop_surface_map: dict[str, str] = {}
    for row in stat_inputs:
        if str(getattr(row, 'source_family', '')).strip() != 'workshop':
            continue
        source_name = str(getattr(row, 'source_name', '') or getattr(row, 'stat_name', '') or '').strip()
        surface_id = ''
        for candidate_surface_id in _surface_id_candidates_from_row(row):
            if candidate_surface_id in current_normalized_rows or candidate_surface_id in projected_normalized_rows:
                surface_id = candidate_surface_id
                break
        if source_name and surface_id and source_name not in workshop_surface_map:
            workshop_surface_map[source_name] = surface_id

    workshop_coin_values: dict[str, object] = {}
    workshop_max_values: dict[str, object] = {}
    for source_name, surface_id in workshop_surface_map.items():
        current_row_payload = current_normalized_rows.get(surface_id) or {}
        projected_row_payload = projected_normalized_rows.get(surface_id) or {}
        workshop_coin_values[source_name] = current_row_payload.get('display_value') or current_row_payload.get('final_value')
        workshop_max_values[source_name] = projected_row_payload.get('display_value') or projected_row_payload.get('final_value')

    uw_track_effects: dict[str, dict[str, object]] = {}
    for uw_name, tracks in (account_state.uw_tracks or {}).items():
        uw_slug = str(uw_name).strip().lower().replace(' ', '_')
        for track_row in tracks or []:
            track_name = getattr(track_row, 'track_name', None)
            if track_name is None and isinstance(track_row, dict):
                track_name = track_row.get('track_name')
            if not track_name:
                continue
            tokens = tuple(str(track_name).strip().lower().replace('%', 'pct').replace(' ', '_').split('_'))
            surface_id = None
            for candidate_surface_id in projected_normalized_rows:
                if f'state::uw.{uw_slug}.' not in candidate_surface_id:
                    continue
                if any(token in candidate_surface_id for token in tokens):
                    surface_id = candidate_surface_id
                    break
            row_payload = projected_normalized_rows.get(surface_id or '') or {}
            contributors = row_payload.get('contributors') or []
            lab_values = []
            module_values = []
            perk_values = []
            for contributor in contributors:
                source_family = str((contributor or {}).get('source_family') or '').strip().lower()
                display = (contributor or {}).get('display_value')
                value = (contributor or {}).get('value')
                if source_family == 'lab' and (display is not None or value is not None):
                    lab_values.append(str(display if display is not None else value))
                if 'module' in source_family and (display is not None or value is not None):
                    module_values.append(str(display if display is not None else value))
                if source_family == 'perk' and (display is not None or value is not None):
                    perk_values.append(str(display if display is not None else value))
            uw_track_effects[f'{uw_name}::{track_name}'] = {
                'surface_id': surface_id,
                'lab_effect': '; '.join(lab_values) if lab_values else None,
                'module_effect': '; '.join(module_values) if module_values else None,
                'perk_effect': '; '.join(perk_values) if perk_values else None,
                'final_value': row_payload.get('display_value') or row_payload.get('final_value'),
            }
    return {
        'workshop_coin_values': workshop_coin_values,
        'workshop_max_values': workshop_max_values,
        'uw_track_effects': uw_track_effects,
    }


def _build_workshop_panel(
    account_state_payload: dict,
    selected_preset: str,
    qe_dashboard_publications: dict[str, object] | None = None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, object]]] = {'offense': [], 'defense': [], 'utility': []}
    gaps: list[dict[str, str]] = []
    qe_published = qe_dashboard_publications or {}
    workshop_coin_values = dict(qe_published.get('workshop_coin_values') or {})
    workshop_max_values = dict(qe_published.get('workshop_max_values') or {})
    for name, row in (account_state_payload.get('workshop') or {}).items():
        category = str((row or {}).get('category') or '').strip().lower()
        category = category if category in groups else 'utility'
        preset_levels = dict((row or {}).get('preset_levels') or {})
        preset_values = dict((row or {}).get('preset_values') or {})
        unlock_value = (row or {}).get('unlocked')
        if unlock_value is None:
            level_value = preset_levels.get(selected_preset)
            unlock_value = bool(level_value) if level_value is not None else None
        coin_level_value = preset_levels.get(selected_preset)
        max_level_value = (row or {}).get('max_level')
        coin_value = workshop_coin_values.get(name, preset_values.get(selected_preset))
        max_value = workshop_max_values.get(name, '')
        if max_value in (None, '') and coin_value not in (None, '') and coin_level_value is not None and max_level_value is not None:
            if str(coin_level_value) == str(max_level_value):
                max_value = coin_value
        if max_value in (None, ''):
            gaps.append(_dashboard_gap('workshop', 'max_value_not_published_upstream', f'Max Value missing for {name}'))
        groups[category].append({
            'unlock': _dashboard_display_token(unlock_value),
            'name': name,
            'coin_level': '' if preset_levels.get(selected_preset) is None else str(preset_levels.get(selected_preset)),
            'coin_value': '' if coin_value is None else str(coin_value),
            'max_level': '' if (row or {}).get('max_level') is None else str((row or {}).get('max_level')),
            'max_value': '' if max_value is None else str(max_value),
        })
    payload: dict[str, object] = {
        'column_headers': ['Unlock', 'Name', 'Coin Level', 'Coin Value', 'Max Level', 'Max Value'],
        'groups': groups,
    }
    return ({'panel_id': 'workshop', 'panel_type': 'grouped_workshop_table', 'title': 'Workshop', 'payload': payload}, gaps)


def _build_workshop_enhancements_panel(account_state_payload: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, object]]] = {'offense': [], 'defense': [], 'utility': []}
    for name, row in (account_state_payload.get('workshop_enhancement_tracks') or {}).items():
        category = str((row or {}).get('category') or '').strip().lower()
        category = category if category in groups else 'utility'
        preset_levels = dict((row or {}).get('preset_levels') or {})
        groups[category].append({
            'name': name,
            'level': '' if preset_levels.get(selected_preset) is None else str(preset_levels.get(selected_preset)),
            'max': '' if (row or {}).get('max_level') is None else str((row or {}).get('max_level')),
            'value': '' if (row or {}).get('current_multiplier') is None else str((row or {}).get('current_multiplier')),
        })
    return ({'panel_id': 'workshop_enhancements', 'panel_type': 'grouped_enhancement_table', 'title': 'Workshop Enhancements', 'payload': {'column_headers': ['Name', 'Level', 'Max', 'Value'], 'groups': groups}}, [])


def _build_uw_panel(account_state_payload: dict, qe_dashboard_publications: dict[str, object] | None = None) -> tuple[dict[str, object], list[dict[str, str]]]:
    uw_plus_tracks = account_state_payload.get('uw_plus_tracks') or {}
    qe_published = qe_dashboard_publications or {}
    uw_track_effects = dict(qe_published.get('uw_track_effects') or {})
    rows: list[dict[str, object]] = []
    gaps: list[dict[str, str]] = []
    for uw_name, tracks in (account_state_payload.get('uw_tracks') or {}).items():
        unlock = _dashboard_display_token((account_state_payload.get('ultimate_weapons') or {}).get(uw_name, {}).get('unlocked'))
        for track in tracks or []:
            plus_key = f"{uw_name}::{track.get('track_name') or ''}"
            published_effects = dict(uw_track_effects.get(plus_key) or {})
            lab_effect = published_effects.get('lab_effect')
            module_effect = published_effects.get('module_effect')
            perk_effect = published_effects.get('perk_effect')
            final_value = published_effects.get('final_value')
            rows.append({
                'unlock': unlock,
                'uw': uw_name,
                'track': track.get('track_name') or '',
                'stone_level': '' if track.get('level') is None else str(track.get('level')),
                'stone_value': '' if track.get('resolved_value') is None else str(track.get('resolved_value')),
                'lab': '' if lab_effect is None else str(lab_effect),
                'module': '' if module_effect is None else str(module_effect),
                'perk': '' if perk_effect is None else str(perk_effect),
                'final': '' if final_value is None else str(final_value),
                'uw_plus': ((uw_plus_tracks.get(plus_key) or {}).get('display_token') or ''),
            })
            if lab_effect is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'lab_column_not_published_upstream', f'Lab column missing for {plus_key}'))
            if module_effect is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'module_column_not_published_upstream', f'Module column missing for {plus_key}'))
            if perk_effect is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'perk_column_not_published_upstream', f'Perk column missing for {plus_key}'))
            if final_value is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'final_column_not_published_upstream', f'Final column missing for {plus_key}'))
    return ({'panel_id': 'ultimate_weapons', 'panel_type': 'uw_track_table', 'title': 'Ultimate Weapons', 'payload': {'column_headers': ['Unlock', 'UW', 'Track', 'Stone Level', 'Stone Value', 'Lab', 'Module', 'Perk', 'Final', 'UW+'], 'rows': rows}}, gaps)


def _build_cards_panel(account_state_payload: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    inventory_rows = []
    for card_name, card_payload in (account_state_payload.get('cards_inventory') or {}).items():
        inventory_rows.append({'name': card_name, 'level': card_payload.get('level') or '', 'mastery': card_payload.get('mastery_lab_level') or ''})
    card_names = sorted((account_state_payload.get('cards_inventory') or {}).keys())
    preset_rows_by_preset: dict[str, list[dict[str, str]]] = {}
    card_presets = dict(account_state_payload.get('card_presets') or {})
    for preset_name in preset_options(account_state_payload):
        preset_cards = card_presets.get(preset_name) or []
        selected_cards = set(preset_cards or [])
        preset_rows_by_preset[str(preset_name)] = [{'name': card_name, 'selected': 'Yes' if card_name in selected_cards else ''} for card_name in card_names]
    selected_rows = preset_rows_by_preset.get(selected_preset, [{'name': card_name, 'selected': ''} for card_name in card_names])
    return ({'panel_id': 'cards', 'panel_type': 'cards_inventory_and_preset', 'title': 'Cards', 'payload': {'inventory_rows': inventory_rows, 'preset_rows': selected_rows, 'preset_rows_by_preset': preset_rows_by_preset, 'slot_count': account_state_payload.get('card_slots_unlocked') or ''}}, [])


def _build_bots_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    for bot_name, tracks in (account_state_payload.get('bot_upgrade_tracks') or {}).items():
        for track in tracks or []:
            rows.append({'unlock': '', 'bot': bot_name, 'track': track.get('track_name') or '', 'level': '' if track.get('level') is None else str(track.get('level')), 'value': '' if track.get('resolved_value') is None else str(track.get('resolved_value'))})
    return ({'panel_id': 'bots', 'panel_type': 'track_table', 'title': 'Bots', 'payload': {'entity_key': 'bot', 'column_headers': ['Unlock', 'Bot', 'Track', 'Level', 'Value'], 'rows': rows}}, [])


def _build_simple_bonus_panel(panel_id: str, title: str, section_rows: list[list[object]]) -> dict[str, object]:
    rows = []
    for row in section_rows:
        name, bonus, _ = _dashboard_token_row(row, 3)
        if name or bonus:
            rows.append({'name': name, 'bonus': bonus})
    return {'panel_id': panel_id, 'panel_type': 'simple_bonus_table', 'title': title, 'payload': {'column_headers': ['Name', 'Bonus'], 'rows': rows}}


def _build_modules_panel(module_card_payloads: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    gaps: list[dict[str, str]] = []
    presets = module_card_payloads.get('presets') or {}
    preset_payload = presets.get(selected_preset)
    if not preset_payload:
        gaps.append(_dashboard_gap('modules', 'module_card_payloads_missing', 'module_card_payloads.json missing selected preset payload'))
        return ({'panel_id': 'modules', 'panel_type': 'module_slot_stack', 'title': 'Modules', 'payload': {'selected_preset': selected_preset, 'slots': {}, 'message': 'Module card payload unavailable.'}}, gaps)
    return ({'panel_id': 'modules', 'panel_type': 'module_slot_stack', 'title': 'Modules', 'payload': {'selected_preset': selected_preset, 'slots': preset_payload}}, gaps)


def _build_guardians_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    for guardian_name, tracks in (account_state_payload.get('guardian_tracks') or {}).items():
        for track in tracks or []:
            rows.append({'unlock': '', 'guardian': guardian_name, 'track': track.get('track_name') or '', 'level': '' if track.get('level') is None else str(track.get('level')), 'value': '' if track.get('resolved_value') is None else str(track.get('resolved_value'))})
    return ({'panel_id': 'guardians', 'panel_type': 'track_table', 'title': 'Guardians', 'payload': {'entity_key': 'guardian', 'column_headers': ['Unlock', 'Guardian', 'Track', 'Level', 'Value'], 'rows': rows}}, [])


def _build_themes_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    value = account_state_payload.get('theme_song_coin_multiplier')
    return ({'panel_id': 'themes_and_songs', 'panel_type': 'simple_metric_panel', 'title': 'Themes and Songs', 'payload': {'metric_label': 'Coin Multiplier', 'metric_value': '' if value is None else str(value)}}, [])


def build_input_dashboard_payload(
    account_state_payload: dict,
    diagnostics: dict,
    *,
    qe_dashboard_publications: dict[str, object] | None = None,
    module_card_payloads: dict[str, object] | None = None,
) -> dict[str, object]:
    selected_preset = str(account_state_payload.get('default_preset') or 'Farming')
    options = preset_options(account_state_payload)
    if selected_preset not in options:
        selected_preset = options[0]
    panels = []
    gaps: list[dict[str, str]] = []
    for builder in [
        lambda: build_labs_panel(account_state_payload),
        lambda: _build_workshop_panel(account_state_payload, selected_preset, qe_dashboard_publications=qe_dashboard_publications),
        lambda: _build_workshop_enhancements_panel(account_state_payload, selected_preset),
        lambda: _build_uw_panel(account_state_payload, qe_dashboard_publications=qe_dashboard_publications),
        lambda: _build_cards_panel(account_state_payload, selected_preset),
        lambda: _build_bots_panel(account_state_payload),
        lambda: (_build_simple_bonus_panel('relics', 'Relics', (account_state_payload.get('raw_sections') or {}).get('Relics', [])), []),
        lambda: _build_modules_panel(module_card_payloads or {}, selected_preset),
        lambda: (_build_simple_bonus_panel('vault', 'Vault', (account_state_payload.get('raw_sections') or {}).get('Vault', [])), []),
        lambda: _build_guardians_panel(account_state_payload),
        lambda: _build_themes_panel(account_state_payload),
    ]:
        panel, panel_gaps = builder()
        panels.append(panel)
        gaps.extend(panel_gaps)
    return {
        'schema_version': 2,
        'selected_preset': selected_preset,
        'preset_options': options,
        'upstream_gaps': gaps,
        'panels': panels,
        'debug_manifest': {'source_artifacts': ['account_state.json', 'module_card_payloads.json', 'diagnostics.json'], 'generated_from': list((diagnostics.get('section_names') or []))},
    }


def _stats_rows_by_surface(rows_payload: dict[str, object] | None, preset: str) -> dict[str, dict[str, object]]:
    preset_payload = dict((rows_payload or {}).get(preset) or {})
    raw_rows = preset_payload.get('rows')
    rows = dict(raw_rows) if isinstance(raw_rows, dict) else dict(preset_payload)
    return {normalize_surface_id_to_contract(str(raw_surface_id)): dict(payload or {}) for raw_surface_id, payload in rows.items()}


def _stats_surface_specs(layout: dict[str, object], key: str) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for entry in (layout.get(key) or []):
        if not isinstance(entry, dict):
            continue
        surface_id = normalize_surface_id_to_contract(str(entry.get('surface_id') or '').strip())
        label = str(entry.get('label') or '').strip()
        canonical_row_id = str(entry.get('canonical_row_id') or surface_id).strip()
        if surface_id and label:
            specs.append({'surface_id': surface_id, 'label': label, 'canonical_row_id': canonical_row_id})
    return specs


def _stats_row_payload(
    *,
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    selected_state_mode: str,
    ep_compare: dict[str, object],
    surface_id: str,
    label: str,
    canonical_row_id: str,
) -> dict[str, object]:
    start_row = dict(rows_start.get(surface_id) or {})
    max_row = dict(rows_max.get(surface_id) or {})
    row = start_row if selected_state_mode == 'start_of_run' else max_row
    ep = dict(ep_compare.get(surface_id) or {})
    return {
        'canonical_row_id': canonical_row_id,
        'display_label': label,
        'label': label,
        'surface_id': surface_id,
        'display_value': row.get('display_value') if row.get('display_value') not in (None, '') else '—',
        'start_of_run_value': start_row.get('display_value') if start_row.get('display_value') not in (None, '') else '—',
        'max_progression_value': max_row.get('display_value') if max_row.get('display_value') not in (None, '') else '—',
        'value': row.get('final_value'),
        'status': row.get('status') or start_row.get('status') or max_row.get('status') or 'missing',
        'ep_display': ep.get('ep_value_display') or ep.get('ep_value_raw'),
        'ep_delta': ep.get('delta_display'),
        'contributors_available': bool(row.get('contributors') or start_row.get('contributors') or max_row.get('contributors')),
    }


def _resolved_stat_section_panel(
    *,
    panel_id: str,
    title: str,
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    selected_state_mode: str,
    ep_compare: dict[str, object],
    surface_specs: list[dict[str, str]],
) -> dict[str, object]:
    return {
        'panel_id': panel_id,
        'panel_type': 'resolved_stat_section',
        'title': title,
        'payload': {
            'artifact': 'qe_resolved_stat_rows',
            'owner': 'qe',
            'rows': [
                _stats_row_payload(
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=selected_state_mode,
                    ep_compare=ep_compare,
                    surface_id=spec['surface_id'],
                    label=spec['label'],
                    canonical_row_id=spec['canonical_row_id'],
                )
                for spec in surface_specs
            ],
        },
    }


def _rows_with_qe_derived_values(
    rows: dict[str, dict[str, object]],
    *,
    annotate_display_fields: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, dict[str, object]]:
    preserved_derived_rows: dict[str, dict[str, object]] = {}
    for surface_id, row in (rows or {}).items():
        if str(surface_id).startswith('derived::'):
            preserved_derived_rows[str(surface_id)] = dict(row or {})
    stat_rows: dict[str, StatRow] = {}
    for surface_id, row in (rows or {}).items():
        if str(surface_id).startswith('derived::'):
            continue
        payload = dict(row or {})
        stat_rows[str(surface_id)] = StatRow(
            stat_name=str(surface_id),
            final_value=payload.get('final_value'),
            value_type=str(payload.get('value_type') or 'scalar'),
            source_count=len(payload.get('contributors') or []),
            status=str(payload.get('status') or 'resolved'),
            notes=str(payload.get('notes') or ''),
            contributors=[dict(contributor or {}) for contributor in (payload.get('contributors') or [])],
            schema={},
        )
    publish_query_surfaces(stat_rows)
    hydrated = {
        surface_id: {
            'stat_name': row.stat_name,
            'final_value': row.final_value,
            'value_type': row.value_type,
            'status': row.status,
            'contributors': [dict(contributor or {}) for contributor in (row.contributors or [])],
        }
        for surface_id, row in stat_rows.items()
    }
    hydrated.update(preserved_derived_rows)
    if annotate_display_fields is not None:
        annotate_display_fields({'rows': hydrated})
    return hydrated


def build_stats_dashboard_payload(
    *,
    account_state_payload: dict[str, object],
    diagnostics: dict[str, object],
    input_dashboard_payload: dict[str, object],
    module_card_payloads: dict[str, object] | None,
    query_rows_start_of_run: dict[str, object] | None,
    query_rows_max_progression: dict[str, object] | None,
    ep_compare_publishable: dict[str, object] | None,
    line_verification: dict[str, object] | None,
    selected_preset: str,
    selected_state_mode: str,
    annotate_display_fields: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    stats_layout = dict(load_section_layout_contract().get('stats_dashboard') or {})
    panel_order = [str(name) for name in (stats_layout.get('panel_order') or [])]
    state_mode_options = [str(name) for name in (stats_layout.get('state_mode_options') or ['start_of_run', 'max_progression'])]
    if selected_state_mode not in state_mode_options:
        selected_state_mode = state_mode_options[0]
    configured_preset_options = preset_options(account_state_payload)
    available_query_presets = sorted(set((query_rows_start_of_run or {}).keys()) | set((query_rows_max_progression or {}).keys()))
    preset_opts = [name for name in configured_preset_options if name in available_query_presets]
    preset_opts.extend(name for name in available_query_presets if name not in preset_opts)
    if not preset_opts:
        preset_opts = configured_preset_options
    if selected_preset not in preset_opts:
        selected_preset = preset_opts[0]
    input_panels_by_id = {str(panel.get('panel_id')): dict(panel or {}) for panel in (input_dashboard_payload.get('panels') or []) if isinstance(panel, dict)}
    ep_compare = dict(ep_compare_publishable or {})
    upstream_gaps: list[dict[str, str]] = []
    variants: dict[str, dict[str, list[dict[str, object]]]] = {}
    for preset_name in preset_opts:
        start_rows_hydrated = _rows_with_qe_derived_values(_stats_rows_by_surface(query_rows_start_of_run, preset_name), annotate_display_fields=annotate_display_fields)
        max_rows_hydrated = _rows_with_qe_derived_values(_stats_rows_by_surface(query_rows_max_progression, preset_name), annotate_display_fields=annotate_display_fields)
        variants[preset_name] = {}
        for state_mode in state_mode_options:
            rows_start = start_rows_hydrated
            rows_max = max_rows_hydrated
            rows = rows_start if state_mode == 'start_of_run' else rows_max
            panels: list[dict[str, object]] = []
            workshop_payload = publish_workshop_reconciliation_payload(
                stats_layout=stats_layout,
                rows_start=rows_start,
                rows_max=rows_max,
                account_state_payload=account_state_payload,
                selected_preset=preset_name,
                surface_specs=_stats_surface_specs,
            )
            panels.append({'panel_id': 'workshop', 'panel_type': 'workshop_stat_table', 'title': 'Workshop', 'payload': workshop_payload})
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='derived',
                    title='Canonical Overview',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'overview_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='offense_resolved',
                    title='Offense',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'offense_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='defense_resolved',
                    title='Defense',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'defense_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='utility_resolved',
                    title='Utility and Economy',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'utility_economy_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='wall_economy_resolved',
                    title='Derived Wall and Economy',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'derived_wall_economy_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='cards_resolved',
                    title='Cards',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'cards_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='bots_resolved',
                    title='Bots',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'bot_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='guardians_resolved',
                    title='Guardians',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'guardian_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='modules_resolved',
                    title='Modules',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'module_surfaces'),
                )
            )
            panels.append(
                _resolved_stat_section_panel(
                    panel_id='uw_stats_resolved',
                    title='Ultimate Weapons',
                    rows_start=rows_start,
                    rows_max=rows_max,
                    selected_state_mode=state_mode,
                    ep_compare=ep_compare,
                    surface_specs=_stats_surface_specs(stats_layout, 'uw_surfaces'),
                )
            )
            variants[preset_name][state_mode] = panels
    active_panels = (variants.get(selected_preset) or {}).get(selected_state_mode) or []
    panel_map = {str(panel.get('panel_id')): panel for panel in active_panels}
    ordered_panels = [panel_map[panel_id] for panel_id in panel_order if panel_id in panel_map]
    ordered_panels.extend(panel for panel in active_panels if str(panel.get('panel_id')) not in set(panel_order))
    payload = {
        'artifact': 'stats_dashboard.json',
        'schema_version': 1,
        'dashboard_version': 1,
        'contract': _stats_dashboard_contract_manifest(),
        'selected_preset': selected_preset,
        'preset_options': preset_opts,
        'selected_state_mode': selected_state_mode,
        'state_mode_options': state_mode_options,
        'upstream_gaps': upstream_gaps,
        'panels': ordered_panels,
        'variants': variants,
        'debug_manifest': {'source_artifacts': ['input_dashboard.json', 'module_card_payloads.json', 'run_stats_query_rows_start_of_run.json', 'run_stats_query_rows_max_progression.json', 'ep_oracle_compare.json'], 'generated_from': list((diagnostics.get('section_names') or []))},
    }
    if annotate_display_fields is not None:
        annotate_display_fields(payload)
    return payload
