from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
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
from qe.workshop_stat_rows import (
    _format_effect_from_contributors,
    _row_display_value,
    build_workshop_reconciliation_row,
)
from input.lab_category_registry import load_lab_category_registry_by_raw_name

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BOT_TRACK_COSTS_PATH = _REPO_ROOT / 'kb' / 'bots' / 'tables' / 'bot-upgrade-tracks-long.csv'
_GUARDIAN_TRACK_COSTS_PATH = _REPO_ROOT / 'kb' / 'guardians' / 'tables' / 'guardian-upgrades.csv'
_DASH = '—'
_DISPLAY_REPLACEMENTS = {
    'Ã¢â‚¬â€': _DASH,
    'â€”': _DASH,
    'ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â': _DASH,
    'Â·': ' · ',
    'Ã‚Â·': ' · ',
}

_NUMERIC_TOKEN_RE = re.compile(
    r'^(?P<prefix>(?:x|\+|-|\+\s+|-\s+)?)'
    r'(?P<number>\d+(?:\.\d+)?)'
    r'(?P<suffix>%|x|s|m)?$',
    flags=re.IGNORECASE,
)


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _normalize_display_text(value: object) -> str:
    text = '' if value is None else str(value)
    for bad, good in _DISPLAY_REPLACEMENTS.items():
        text = text.replace(bad, good)
    text = re.sub(r'\s*·\s*', ' · ', text).strip()
    if not text:
        return _DASH
    match = _NUMERIC_TOKEN_RE.match(text.replace(' ', ''))
    if match:
        prefix = match.group('prefix') or ''
        number = float(match.group('number'))
        suffix = match.group('suffix') or ''
        number_text = str(int(number)) if number.is_integer() else f'{number:.2f}'.rstrip('0').rstrip('.')
        if prefix in {'+', '-'}:
            return f'{prefix} {number_text}{suffix}'
        return f'{prefix}{number_text}{suffix}'
    return text


def _normalize_identity(value: object) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')


@lru_cache(maxsize=1)
def _load_bot_cumulative_costs() -> dict[tuple[str, str, int], float]:
    costs: dict[tuple[str, str, int], float] = {}
    with _BOT_TRACK_COSTS_PATH.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            bot_name = _normalize_identity(row.get('bot_name'))
            track_name = _normalize_identity(row.get('track_name'))
            try:
                level = int(float(row.get('level') or 0))
                medal_cost = float(row.get('medal_cost') or 0.0)
            except ValueError:
                continue
            costs[(bot_name, track_name, level)] = medal_cost
    return costs


@lru_cache(maxsize=1)
def _load_guardian_cumulative_costs() -> dict[tuple[str, str, int], float]:
    costs: dict[tuple[str, str, int], float] = {}
    with _GUARDIAN_TRACK_COSTS_PATH.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            guardian_name = _normalize_identity(row.get('guardian_name') or row.get('guardian'))
            track_name = _normalize_identity(row.get('track_attribute') or row.get('attribute'))
            try:
                level = int(float(row.get('level') or 0))
                bit_cost = float(row.get('cost_bits') or row.get('cost') or 0.0)
            except ValueError:
                continue
            costs[(guardian_name, track_name, level)] = bit_cost
    verified_track_columns = {
        'cooldown_bits': 'cooldown',
        'duration_bits': 'duration',
        'range_bonus_bits': 'range_bonus',
        'cash_bonus_bits': 'cash_bonus',
        'find_chance_bits': 'find_chance',
        'double_find_chance_bits': 'double_find_chance',
        'recovery_amount_bits': 'recovery_amount',
        'max_recovery_bits': 'max_recovery',
        'multiplier_bits': 'multiplier',
        'targets_bits': 'targets',
        'percentage_bits': 'percentage',
    }
    for path in sorted((_REPO_ROOT / 'kb' / 'guardians' / 'tables').glob('wiki-verified-guardian-*-upgrades.csv')):
        guardian_name = _normalize_identity(path.stem.replace('wiki-verified-guardian-', '').replace('-upgrades', ''))
        with path.open(encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                try:
                    level = int(float(row.get('level') or 0))
                except ValueError:
                    continue
                for cost_key, normalized_track in verified_track_columns.items():
                    if cost_key not in row:
                        continue
                    try:
                        bit_cost = float(row.get(cost_key) or 0.0)
                    except ValueError:
                        continue
                    costs.setdefault((guardian_name, normalized_track, level), bit_cost)
    return costs


def _format_cumulative_cost(value: float | None) -> str:
    if value is None:
        return _DASH
    return str(int(value)) if float(value).is_integer() else f'{value:.2f}'.rstrip('0').rstrip('.')


def _cumulative_total_text(*values: object) -> str:
    total = 0.0
    saw_value = False
    for value in values:
        normalized = _normalize_display_text(value)
        if normalized == _DASH:
            continue
        number, _suffix = _parse_display_number(normalized)
        if number is None:
            continue
        total += number
        saw_value = True
    if not saw_value:
        return _DASH
    return _format_cumulative_cost(total)


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
        start_display = _normalize_display_text(start_row.get('display_value'))
        max_display = _normalize_display_text(max_row.get('display_value'))
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
        'product_contract': {
            'primary_surface_rule': 'Stats primary surface must stay operator-useful and workshop-led; repetitive resolved ledgers belong in secondary surfaces.',
            'secondary_surface_rule': 'Detailed QE resolved rows, compare/debug tooling, and repetitive ledger dumps must be isolated from the default operator workflow.',
        },
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
                'product_tier': 'primary',
                'notes': 'Counts toward current canonical visible-stat completion. Missingness and row status are QE-owned.',
            },
            {
                'panel_id': 'ultimate_weapons',
                'panel_role': 'operator_context',
                'authority': 'publication_payload_from_input_and_qe',
                'acceptance_state': 'active',
                'product_tier': 'primary',
                'notes': 'Operator-useful ultimate-weapon visibility belongs on the main Stats surface, but does not replace canonical QE row ownership.',
            },
            {
                'panel_id': 'bots',
                'panel_role': 'operator_context',
                'authority': 'publication_payload_from_input_and_qe',
                'acceptance_state': 'active',
                'product_tier': 'primary',
                'notes': 'Operator-useful bot visibility belongs on the main Stats surface, but does not replace canonical QE row ownership.',
            },
            {
                'panel_id': 'guardians',
                'panel_role': 'operator_context',
                'authority': 'publication_payload_from_input_and_qe',
                'acceptance_state': 'active',
                'product_tier': 'primary',
                'notes': 'Operator-useful guardian visibility belongs on the main Stats surface, but does not replace canonical QE row ownership.',
            },
            {
                'panel_id': 'modules',
                'panel_role': 'operator_context',
                'authority': 'publication_payload_from_input_and_qe',
                'acceptance_state': 'active',
                'product_tier': 'primary',
                'notes': 'Operator-useful module visibility belongs on the main Stats surface, but does not replace canonical QE row ownership.',
            },
            {
                'panel_id': 'offense_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned offense stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'defense_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned defense stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'utility_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned utility and economy stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'wall_economy_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned derived wall and economy rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'cards_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned card stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'bots_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned bot stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'guardians_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned guardian stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'modules_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned module stat rows remain available, but they are secondary detail rather than the default operator workflow.',
            },
            {
                'panel_id': 'uw_stats_resolved',
                'panel_role': 'canonical_stat_rows',
                'authority': 'qe_query_rows',
                'acceptance_state': 'secondary',
                'product_tier': 'secondary',
                'notes': 'QE-owned ultimate-weapon stat rows remain available, but they are secondary detail rather than the default operator workflow.',
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


def _uw_track_surface_map() -> dict[str, dict[str, str]]:
    return {
        'Chain Lightning': {
            'Damage': 'state::uw.chain_lightning.damage_multiplier',
            'Quantity': 'state::uw.chain_lightning.quantity',
            'Chance': 'state::uw.chain_lightning.chance_pct',
        },
        'Smart Missiles': {
            'Damage': 'state::uw.smart_missiles.damage_multiplier',
            'Quantity': 'state::uw.smart_missiles.quantity',
            'Cooldown': 'state::uw.smart_missiles.cooldown_seconds',
        },
        'Death Wave': {
            'Damage': 'state::uw.death_wave.damage_multiplier',
            'Quantity': 'state::uw.death_wave.effect_wave_count',
            'Cooldown': 'state::uw.death_wave.cooldown_seconds',
        },
        'Chrono Field': {
            'Duration': 'state::uw.chrono_field.duration_seconds',
            'Speed Reduction': 'state::uw.chrono_field.slow_pct',
            'Cooldown': 'state::uw.chrono_field.cooldown_seconds',
        },
        'Inner Land Mines': {
            'Damage': 'state::uw.inner_land_mines.damage',
            'Quantity': 'state::uw.inner_land_mines.quantity',
            'Cooldown': 'state::uw.inner_land_mines.cooldown_seconds',
        },
        'Golden Tower': {
            'Multiplier': 'state::uw.golden_tower.bonus_multiplier',
            'Duration': 'state::uw.golden_tower.duration_seconds',
            'Cooldown': 'state::uw.golden_tower.cooldown_seconds',
        },
        'Poison Swamp': {
            'Damage': 'state::uw.poison_swamp.damage_multiplier',
            'Duration': 'state::uw.poison_swamp.duration_seconds',
            'Cooldown': 'state::uw.poison_swamp.cooldown_seconds',
        },
        'Black Hole': {
            'Size': 'state::uw.black_hole.size_m',
            'Duration': 'state::uw.black_hole.duration_seconds',
            'Cooldown': 'state::uw.black_hole.cooldown_seconds',
        },
        'Spotlight': {
            'Multiplier': 'state::uw.spotlight.bonus_multiplier',
            'Angle': 'state::uw.spotlight.angle_degrees',
            'Quantity': 'state::uw.spotlight.count',
        },
    }


def _uw_other_surface_specs(stats_layout: dict[str, object]) -> dict[str, list[dict[str, str]]]:
    sections: dict[str, list[dict[str, str]]] = {}
    for entry in (stats_layout.get('uw_other_surfaces') or []):
        if not isinstance(entry, dict):
            continue
        section = str(entry.get('section') or '').strip()
        label = str(entry.get('label') or '').strip()
        surface_id = normalize_surface_id_to_contract(str(entry.get('surface_id') or '').strip())
        if section and label and surface_id:
            sections.setdefault(section, []).append({'label': label, 'surface_id': surface_id})
    return sections


def _format_named_other_entries(entries: list[tuple[str, object]]) -> str:
    tokens: list[str] = []
    for label, value in entries:
        label_text = str(label or '').strip()
        value_text = str(value or '').strip()
        if not label_text and not value_text:
            continue
        tokens.append(f'{label_text} {value_text}'.strip())
    return ' · '.join(tokens) if tokens else '—'


def _section_surface_value(row: dict[str, object], *, metadata_value: object = None) -> str:
    if row:
        final_value = row.get('final_value')
        if final_value is not None:
            return _normalize_display_text(row.get('display_value') or final_value)
        display_value = row.get('display_value')
        if display_value not in (None, ''):
            return _normalize_display_text(display_value)
    return _normalize_display_text(metadata_value or _DASH)


def _build_supplemental_rows(
    *,
    prefix: str,
    entries: list[tuple[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not entries:
        return rows
    rows.append({
        'canonical_row_id': f'{prefix}::supplemental_header',
        'display_label': 'Supplemental effects',
        'name': 'Supplemental effects',
        'workshop_level': _DASH,
        'stone_value': _DASH,
        'lab_effects': _DASH,
        'module_effects': _DASH,
        'start_of_run_value': _DASH,
        'perk_effects': _DASH,
        'max_progression_value': _DASH,
        'other': _DASH,
        'reconciliation_status': 'not_applicable',
        'reconciliation_cell_flags': {},
        'row_status': 'non_recon',
    })
    for label, value in entries:
        rows.append({
            'canonical_row_id': f'{prefix}::supplemental::{_normalize_identity(label)}',
            'display_label': f'Supplemental: {label}',
            'name': f'Supplemental: {label}',
            'workshop_level': _DASH,
            'stone_value': _DASH,
            'lab_effects': _DASH,
            'module_effects': _DASH,
            'start_of_run_value': _normalize_display_text(value),
            'perk_effects': _DASH,
            'max_progression_value': _DASH,
            'other': _DASH,
            'reconciliation_status': 'not_applicable',
            'reconciliation_cell_flags': {},
            'row_status': 'non_recon',
        })
    return rows


def _display_terms_parseable(*terms: object) -> bool:
    for term in terms:
        normalized = _normalize_display_text(term)
        if normalized == _DASH:
            continue
        value, _suffix = _parse_display_number(normalized)
        if value is None:
            return False
    return True


def _sum_display_terms(*terms: object) -> tuple[float | None, str]:
    total = 0.0
    suffix = ''
    saw = False
    for term in terms:
        normalized = _normalize_display_text(term)
        if normalized == _DASH:
            continue
        value, parsed_suffix = _parse_display_number(normalized)
        if value is None:
            return None, ''
        if not suffix and parsed_suffix:
            suffix = parsed_suffix
        saw = True
        total += value
    if not saw:
        return None, suffix
    return total, suffix


def _format_compacted_display_sum(*terms: object, fallback_surface_id: str = '') -> str:
    total, suffix = _sum_display_terms(*terms)
    if total is None:
        return _join_display_tokens(*[str(term) for term in terms if _normalize_display_text(term) != _DASH])
    if not suffix:
        suffix = _semantic_suffix_for_display(total, fallback_surface_id=fallback_surface_id)
    return _format_value_with_hint(total, suffix_hint=suffix)


def _format_uw_stat_input_value(*, destination_id: str, raw_value: object) -> str:
    if raw_value in (None, ''):
        return '—'
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return str(raw_value)
    if destination_id.endswith('_pct'):
        return f'{_dashboard_display_token(value)}%'
    if destination_id.endswith('_multiplier') or destination_id.endswith('.damage'):
        return f'x{_dashboard_display_token(value)}'
    return _dashboard_display_token(value)


def _build_uw_stat_input_maps(stat_inputs_payload: list[dict[str, object]] | None) -> tuple[dict[str, dict[str, list[str]]], dict[str, list[tuple[str, str]]]]:
    primary_surface_ids = {
        surface_id
        for track_map in _uw_track_surface_map().values()
        for surface_id in track_map.values()
    }
    surface_effects: dict[str, dict[str, list[str]]] = {}
    section_other_entries: dict[str, list[tuple[str, str]]] = {}
    explicit_other_sections = {
        'state::uw.chain_lightning.max_enemy_damage_reduction_pct': 'Chain Lightning',
        'state::uw.chrono_field.damage_reduction_pct': 'Chrono Field',
        'state::uw.spotlight.coin_bonus_multiplier': 'Spotlight',
        'state::uw.spotlight.light_range': 'Spotlight',
    }
    for row in (stat_inputs_payload or []):
        if not isinstance(row, dict):
            continue
        raw_destination_id = str(row.get('destination_id') or '').strip()
        destination_id = normalize_surface_id_to_contract(raw_destination_id)
        if destination_id.startswith('uw.'):
            destination_id = f'state::{destination_id}'
        if not destination_id.startswith('state::uw.'):
            continue
        source_family = str(row.get('source_family') or '').strip().lower()
        source_name = str(row.get('source_name') or '').strip()
        value_text = _format_uw_stat_input_value(destination_id=destination_id, raw_value=row.get('value'))
        if destination_id in primary_surface_ids:
            effects = surface_effects.setdefault(destination_id, {'lab': [], 'module': [], 'perk': []})
            if source_family == 'lab':
                effects['lab'].append(value_text)
            elif source_family.startswith('module'):
                effects['module'].append(value_text)
            elif source_family in {'perk', 'perks', 'perk_effect'}:
                effects['perk'].append(value_text)
            continue
        section_name = explicit_other_sections.get(destination_id)
        if not section_name:
            continue
        section_other_entries.setdefault(section_name, []).append(
            (source_name or destination_id.split('.')[-1].replace('_', ' ').title(), value_text)
        )
    return surface_effects, section_other_entries


def _uw_recon_status(*, start_row: dict[str, object], max_row: dict[str, object], stone_value: str) -> str:
    if _normalize_display_text(stone_value) == _DASH:
        return 'red'
    if str(start_row.get('status') or '') != 'resolved':
        return 'amber'
    if str(max_row.get('status') or '') != 'resolved':
        return 'amber'
    return 'green'


def _row_is_resolved(row: dict[str, object]) -> bool:
    return str(row.get('status') or '').strip() == 'resolved'


def _parse_display_number(text: object) -> tuple[float | None, str]:
    normalized = _normalize_display_text(text)
    if normalized == _DASH:
        return None, ''
    compact = normalized.replace(' ', '')
    match = _NUMERIC_TOKEN_RE.match(compact)
    if not match:
        return None, ''
    try:
        value = float(match.group('number'))
    except ValueError:
        return None, ''
    prefix = match.group('prefix') or ''
    if prefix.startswith('-'):
        value = -value
    return value, (match.group('suffix') or '')


def _surface_pct_scale_hint(surface_id: str) -> str:
    if surface_id in {
        'state::bot.flame.damage_reduction_pct',
        'state::bot.thunder.linger_slow_pct',
        'state::guardian.attack.missing_health_damage_pct',
        'state::guardian.ally.recovery_amount_pct',
        'state::guardian.fetch.find_chance_pct',
        'state::guardian.fetch.double_find_chance_pct',
    }:
        return 'fraction_to_percent'
    return 'direct'


def _semantic_suffix_for_display(value_text: object, *, fallback_surface_id: str = '') -> str:
    normalized = _normalize_display_text(value_text)
    compact = normalized.replace(' ', '')
    match = _NUMERIC_TOKEN_RE.match(compact)
    if match and (match.group('suffix') or ''):
        return match.group('suffix') or ''
    if 'multiplier' in fallback_surface_id or 'bonus' in fallback_surface_id:
        return 'x'
    if fallback_surface_id.endswith('_pct'):
        return '%'
    if fallback_surface_id.endswith('_seconds'):
        return 's'
    if fallback_surface_id.endswith('_m'):
        return 'm'
    return ''


def _format_value_with_hint(value: object, *, suffix_hint: str = '', scale_hint: str = 'direct') -> str:
    if value in (None, ''):
        return _DASH
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _normalize_display_text(value)
    if scale_hint == 'fraction_to_percent':
        number *= 100.0
        suffix_hint = '%'
    number_text = str(int(number)) if float(number).is_integer() else f'{number:.2f}'.rstrip('0').rstrip('.')
    if suffix_hint == 'x':
        return f'x{number_text}'
    return f'{number_text}{suffix_hint}'


def _surface_display_value(row: dict[str, object], *, surface_id: str, fallback_value: object = None) -> str:
    if _row_is_resolved(row):
        final_value = row.get('final_value')
        if final_value is not None:
            return _format_value_with_hint(
                final_value,
                suffix_hint=_semantic_suffix_for_display(row.get('display_value'), fallback_surface_id=surface_id),
                scale_hint=_surface_pct_scale_hint(surface_id),
            )
        display = row.get('display_value')
        if display not in (None, ''):
            return _normalize_display_text(display)
    return _format_value_with_hint(
        fallback_value,
        suffix_hint=_semantic_suffix_for_display(fallback_value, fallback_surface_id=surface_id),
        scale_hint=_surface_pct_scale_hint(surface_id),
    )


def _normalize_effect_text_for_surface(surface_id: str, value: object) -> str:
    normalized = _normalize_display_text(value)
    if normalized == _DASH:
        return _DASH
    number, parsed_suffix = _parse_display_number(normalized)
    if number is None:
        return normalized
    suffix_hint = parsed_suffix or _semantic_suffix_for_display(normalized, fallback_surface_id=surface_id)
    return _format_value_with_hint(number, suffix_hint=suffix_hint, scale_hint=_surface_pct_scale_hint(surface_id))


def _uw_stone_value_text(surface_id: str, metadata: dict[str, object], start_row: dict[str, object]) -> str:
    for contributor in start_row.get('contributors') or []:
        if not isinstance(contributor, dict):
            continue
        if str(contributor.get('source_class') or '').strip() != 'ultimate_weapons':
            continue
        display_value = contributor.get('display_value')
        if display_value not in (None, ''):
            return _normalize_effect_text_for_surface(surface_id, display_value)
        value = contributor.get('value')
        if value not in (None, ''):
            return _format_value_with_hint(
                value,
                suffix_hint=_semantic_suffix_for_display(value, fallback_surface_id=surface_id),
                scale_hint='direct',
            )
    return _normalize_effect_text_for_surface(surface_id, metadata.get('stone_value'))


def _derived_uw_perk_delta_text(
    *,
    surface_id: str,
    start_value: str,
    max_value: str,
    start_expected: float | None,
) -> str:
    if surface_id not in {
        'state::uw.black_hole.duration_seconds',
        'state::uw.chrono_field.duration_seconds',
    }:
        return _DASH
    if start_expected is None:
        return _DASH
    start_number, suffix = _parse_display_number(start_value)
    max_number, max_suffix = _parse_display_number(max_value)
    if start_number is None or max_number is None:
        return _DASH
    if abs(start_expected - start_number) >= 0.011:
        return _DASH
    delta = max_number - start_number
    if abs(delta) < 0.011:
        return _DASH
    suffix_hint = max_suffix or suffix or _semantic_suffix_for_display(max_value, fallback_surface_id=surface_id)
    magnitude = _format_value_with_hint(abs(delta), suffix_hint=suffix_hint, scale_hint='direct')
    return f"- {magnitude}" if delta < 0 else f"+ {magnitude}"


def _bot_recon_status_explicit(
    *,
    surface_id: str,
    start_value: str,
    metadata: dict[str, str],
    lab_effects: str,
    module_effects: str,
) -> str:
    base_text = _normalize_display_text(metadata.get('medal_value') or _DASH)
    spent_text = _normalize_display_text(metadata.get('medals_spent') or _DASH)
    if spent_text == _DASH or base_text == _DASH:
        return 'red'
    if not _display_terms_parseable(base_text, lab_effects, module_effects, start_value):
        return 'red'
    base_value, _ = _parse_display_number(base_text)
    start_number, _ = _parse_display_number(start_value)
    if base_value is None or start_number is None:
        return 'red'
    lab_value, _ = _parse_display_number(lab_effects)
    module_value, _ = _parse_display_number(module_effects)
    expected = base_value + (lab_value or 0.0) + (module_value or 0.0)
    return 'green' if abs(expected - start_number) < 0.011 else 'red'


def _guardian_recon_status_explicit(*, bit_value: str, start_value: str, bits_spent: str) -> str:
    if _normalize_display_text(bits_spent) == _DASH:
        return 'red'
    if not _display_terms_parseable(bit_value, start_value):
        return 'red'
    base_value, _ = _parse_display_number(bit_value)
    start_number, _ = _parse_display_number(start_value)
    if base_value is None or start_number is None:
        return 'red'
    return 'green' if abs(base_value - start_number) < 0.011 else 'red'


def _module_slot_recon_status_explicit(slot_payload: dict[str, object]) -> str:
    primary = dict(slot_payload.get('primary') or {})
    assist = dict(slot_payload.get('assist') or {})
    required_primary_fields = (
        primary.get('module_name'),
        primary.get('rarity_text'),
        primary.get('main_value_text'),
        primary.get('main_label_text'),
        primary.get('displayed_level_cap'),
    )
    if any(value in (None, '') for value in required_primary_fields):
        return 'amber'
    if assist:
        if not assist.get('module_name') or not assist.get('rarity_text'):
            return 'amber'
        if not str(assist.get('role_bar_detail_text') or '').strip():
            return 'amber'
        if _extract_module_assist_pct({'assist': assist}) == _DASH:
            return 'amber'
    return 'green'


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


def _extract_module_assist_pct(slot_payload: dict[str, object]) -> str:
    assist_payload = dict(slot_payload.get('assist') or {})
    detail = str(assist_payload.get('role_bar_detail_text') or '').strip()
    match = re.search(r'Main\s+([0-9.]+)x', detail)
    if not match:
        return _DASH
    try:
        return f"{float(match.group(1)) * 100:.2f}".rstrip('0').rstrip('.') + '%'
    except ValueError:
        return _DASH


def _module_slot_recon_status(slot_payload: dict[str, object]) -> str:
    return _module_slot_recon_status_explicit(slot_payload)


def _build_module_grouped_summary(slots: dict[str, object]) -> list[dict[str, object]]:
    slot_order = ['cannon', 'armor', 'generator', 'core']

    def _slot_value(slot: str, key: str, role: str = 'primary') -> str:
        slot_payload = dict((slots.get(slot) or {}))
        role_payload = dict(slot_payload.get(role) or {})
        return _normalize_display_text(role_payload.get(key))

    def _slot_module_name(slot: str, role: str) -> str:
        slot_payload = dict((slots.get(slot) or {}))
        role_payload = dict(slot_payload.get(role) or {})
        return _normalize_display_text(role_payload.get('module_name'))

    return [
        {'group': '', 'label': 'Max Level', 'values': {slot: _slot_value(slot, 'displayed_level_cap') for slot in slot_order}},
        {'group': '', 'label': 'Assist %', 'values': {slot: _extract_module_assist_pct(dict(slots.get(slot) or {})) for slot in slot_order}},
        {'group': 'Primary', 'label': 'Module', 'values': {slot: _slot_module_name(slot, 'primary') for slot in slot_order}},
        {'group': 'Primary', 'label': 'Rarity', 'values': {slot: _slot_value(slot, 'rarity_text') for slot in slot_order}},
        {'group': 'Assist', 'label': 'Module', 'values': {slot: _slot_module_name(slot, 'assist') for slot in slot_order}},
        {'group': 'Assist', 'label': 'Rarity', 'values': {slot: _slot_value(slot, 'rarity_text', 'assist') for slot in slot_order}},
        {'group': 'Current', 'label': 'Multiplier', 'values': {slot: _slot_value(slot, 'main_value_text') for slot in slot_order}},
        {'group': 'Current', 'label': 'Effect', 'values': {slot: _slot_value(slot, 'main_label_text') for slot in slot_order}},
    ]


def _normalize_module_slot_payload(slot_payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(slot_payload or {})
    for role in ('primary', 'assist'):
        role_payload = dict(normalized.get(role) or {})
        if role_payload:
            if 'main_value_text' in role_payload:
                role_payload['main_value_text'] = _normalize_display_text(role_payload.get('main_value_text'))
            normalized[role] = role_payload
    return normalized


def _build_modules_panel(module_card_payloads: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    gaps: list[dict[str, str]] = []
    presets = module_card_payloads.get('presets') or {}
    preset_payload = presets.get(selected_preset)
    if not preset_payload:
        gaps.append(_dashboard_gap('modules', 'module_card_payloads_missing', 'module_card_payloads.json missing selected preset payload'))
        return ({
            'panel_id': 'modules',
            'panel_type': 'module_slot_stack',
            'title': 'Modules',
            'payload': {'selected_preset': selected_preset, 'slots': {}, 'summary_rows': [], 'slot_order': ['cannon', 'armor', 'generator', 'core'], 'message': 'Module card payload unavailable.'},
        }, gaps)
    normalized_slots = {
        slot: _normalize_module_slot_payload(dict(slot_payload or {}))
        for slot, slot_payload in dict(preset_payload or {}).items()
    }
    return ({
        'panel_id': 'modules',
        'panel_type': 'module_slot_stack',
        'title': 'Modules',
        'payload': {
            'selected_preset': selected_preset,
            'slot_order': ['cannon', 'armor', 'generator', 'core'],
            'summary_rows': _build_module_grouped_summary(normalized_slots),
            'slots': normalized_slots,
        },
    }, gaps)


def _build_guardians_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    for guardian_name, tracks in (account_state_payload.get('guardian_tracks') or {}).items():
        for track in tracks or []:
            rows.append({'unlock': '', 'guardian': guardian_name, 'track': track.get('track_name') or '', 'level': '' if track.get('level') is None else str(track.get('level')), 'value': '' if track.get('resolved_value') is None else str(track.get('resolved_value'))})
    return ({'panel_id': 'guardians', 'panel_type': 'track_table', 'title': 'Guardians', 'payload': {'entity_key': 'guardian', 'column_headers': ['Unlock', 'Guardian', 'Track', 'Level', 'Value'], 'rows': rows}}, [])


def _stats_reconciliation_status(*, start_row: dict[str, object], max_row: dict[str, object]) -> str:
    status = str(start_row.get('status') or max_row.get('status') or 'missing')
    if status == 'resolved':
        return 'green'
    if status == 'non_recon':
        return 'red'
    return 'amber'


def _operator_workshop_row(
    *,
    name: str,
    start_row: dict[str, object],
    max_row: dict[str, object],
    canonical_row_id: str,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    meta = dict(metadata or {})
    base_value = str(meta.get('base_value') or meta.get('resolved_value') or '—')
    return {
        'canonical_row_id': canonical_row_id,
        'display_label': name,
        'name': name,
        'workshop_level': str(meta.get('level') or '—'),
        'lab_effects': str(meta.get('lab') or '—'),
        'relics': str(meta.get('relics') or '—'),
        'base_subtotal': base_value,
        'module_effects': str(meta.get('module') or '—'),
        'card_effects': str(meta.get('card') or '—'),
        'base_loadout_subtotal': str(meta.get('final') or '—'),
        'enhancement_effects': str(meta.get('enhancement') or '—'),
        'start_of_run_modifier_total': str(meta.get('modifier_total') or '—'),
        'workshop_value': base_value,
        'start_of_run_value': str(start_row.get('display_value') or meta.get('final') or '—'),
        'other': str(meta.get('other') or '—'),
        'max_workshop_modifier_total': str(meta.get('max_modifier_total') or '—'),
        'max_workshop_value': str(meta.get('max_value') or '—'),
        'max_workshop_resolved_value': str(meta.get('max_resolved_value') or '—'),
        'perk_effects': str(meta.get('perk') or '—'),
        'max_progression_value': str(max_row.get('display_value') or start_row.get('display_value') or meta.get('final') or '—'),
        'reconciliation_status': _stats_reconciliation_status(start_row=start_row, max_row=max_row),
        'reconciliation_cell_flags': {},
    }


def _operator_table_columns(*, level_label: str, include_labs: bool, include_modules: bool, include_perks: bool, include_max_progression: bool) -> list[dict[str, str]]:
    columns: list[dict[str, str]] = [
        {'key': 'name', 'label': 'Track'},
        {'key': 'workshop_level', 'label': level_label},
    ]
    if include_labs:
        columns.append({'key': 'lab_effects', 'label': 'Lab'})
    if include_modules:
        columns.append({'key': 'module_effects', 'label': 'Module'})
    if include_perks:
        columns.append({'key': 'perk_effects', 'label': 'Perk'})
    columns.append({'key': 'start_of_run_value', 'label': 'Start of Run'})
    if include_max_progression:
        columns.append({'key': 'max_progression_value', 'label': 'Max Progression'})
    columns.append({'key': 'reconciliation_status', 'label': 'Recon', 'kind': 'recon'})
    return columns


def _uw_operator_table_columns() -> list[dict[str, str]]:
    return [
        {'key': 'name', 'label': 'Track'},
        {'key': 'workshop_level', 'label': 'Stone Level'},
        {'key': 'stone_value', 'label': 'Stone Value'},
        {'key': 'lab_effects', 'label': 'Lab'},
        {'key': 'module_effects', 'label': 'Module'},
        {'key': 'start_of_run_value', 'label': 'Start of Run'},
        {'key': 'perk_effects', 'label': 'Perk'},
        {'key': 'max_progression_value', 'label': 'Max Progression'},
        {'key': 'other', 'label': 'Other'},
        {'key': 'reconciliation_status', 'label': 'Recon', 'kind': 'recon'},
    ]


def _bot_operator_table_columns() -> list[dict[str, str]]:
    return [
        {'key': 'name', 'label': 'Track'},
        {'key': 'medal_level', 'label': 'Level'},
        {'key': 'medals_spent', 'label': 'Cumulative Medals Spent'},
        {'key': 'medal_value', 'label': 'Value'},
        {'key': 'lab_effects', 'label': 'Lab'},
        {'key': 'module_effects', 'label': 'Module'},
        {'key': 'start_of_run_value', 'label': 'Start of Run'},
        {'key': 'reconciliation_status', 'label': 'Recon', 'kind': 'recon'},
    ]


def _guardian_operator_table_columns() -> list[dict[str, str]]:
    return [
        {'key': 'name', 'label': 'Track'},
        {'key': 'bit_level', 'label': 'Level'},
        {'key': 'bits_spent', 'label': 'Cumulative Bits Spent'},
        {'key': 'bit_value', 'label': 'Value'},
        {'key': 'start_of_run_value', 'label': 'Start of Run'},
        {'key': 'reconciliation_status', 'label': 'Recon', 'kind': 'recon'},
    ]


def _operator_panel_payload(
    *,
    panel_id: str,
    sections: dict[str, list[dict[str, object]]],
    level_label: str,
    include_labs: bool,
    include_modules: bool,
    include_perks: bool,
    include_max_progression: bool,
) -> dict[str, object]:
    return {
        'artifact': 'stats_operator_workshop_rows',
        'owner': 'publication',
        'columns': _operator_table_columns(
            level_label=level_label,
            include_labs=include_labs,
            include_modules=include_modules,
            include_perks=include_perks,
            include_max_progression=include_max_progression,
        ),
        'sections': [
            {'section_id': f'{panel_id}::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
            for section_name, rows in sections.items()
        ],
    }


def _reduce_prefixed_label(label: str, prefix: str) -> str:
    if label.startswith(f'{prefix} '):
        return label[len(prefix) + 1:]
    return label


def _bot_track_surface_map() -> dict[str, list[dict[str, str]]]:
    return {
        'Amplify': [
            {'track': 'Bonus', 'surface_id': 'state::bot.amplify.bonus_multiplier', 'effective_surface_id': ''},
            {'track': 'Cooldown', 'surface_id': 'state::bot.amplify.cooldown_seconds', 'effective_surface_id': ''},
            {'track': 'Duration', 'surface_id': 'state::bot.amplify.duration_seconds', 'effective_surface_id': ''},
            {'track': 'Range', 'surface_id': 'state::bot.amplify.range_m', 'effective_surface_id': 'state::bot.amplify.effective_range_m'},
        ],
        'Flame': [
            {'track': 'Cooldown', 'surface_id': 'state::bot.flame.cooldown_seconds', 'effective_surface_id': ''},
            {'track': 'Damage', 'surface_id': 'state::bot.flame.damage_multiplier', 'effective_surface_id': ''},
            {'track': 'Damage Reduction', 'surface_id': 'state::bot.flame.damage_reduction_pct', 'effective_surface_id': ''},
            {'track': 'Range', 'surface_id': 'state::bot.flame.range_m', 'effective_surface_id': 'state::bot.flame.effective_range_m'},
        ],
        'Golden': [
            {'track': 'Bonus', 'surface_id': 'state::bot.golden.bonus_multiplier', 'effective_surface_id': ''},
            {'track': 'Cooldown', 'surface_id': 'state::bot.golden.cooldown_seconds', 'effective_surface_id': ''},
            {'track': 'Duration', 'surface_id': 'state::bot.golden.duration_seconds', 'effective_surface_id': ''},
            {'track': 'Range', 'surface_id': 'state::bot.golden.range_m', 'effective_surface_id': 'state::bot.golden.effective_range_m'},
        ],
        'Thunder': [
            {'track': 'Cooldown', 'surface_id': 'state::bot.thunder.cooldown_seconds', 'effective_surface_id': ''},
            {'track': 'Duration', 'surface_id': 'state::bot.thunder.duration_seconds', 'effective_surface_id': ''},
            {'track': 'Linger', 'surface_id': 'state::bot.thunder.linger_slow_pct', 'effective_surface_id': ''},
            {'track': 'Range', 'surface_id': 'state::bot.thunder.range_m', 'effective_surface_id': 'state::bot.thunder.effective_range_m'},
        ],
    }


def _extract_bot_medal_spent(level_token: str) -> str:
    match = re.search(r'Cost\s+([0-9]+)', level_token or '')
    return match.group(1) if match else 'â€”'


def _build_bot_track_metadata_index(account_state_payload: dict[str, object]) -> dict[str, dict[str, str]]:
    rows = (account_state_payload.get('raw_sections') or {}).get('Bots') or []
    index: dict[str, dict[str, str]] = {}
    cumulative_costs = _load_guardian_cumulative_costs()
    current_bot = ''
    track_name_overrides = {
        'Damage R.': 'Damage Reduction',
    }
    for row in rows:
        if not isinstance(row, list):
            continue
        bot_name = str(row[0] if len(row) > 0 else '').strip()
        if bot_name and bot_name.lower() not in {'true', 'false'}:
            current_bot = bot_name.replace(' Bot', '')
        if not current_bot:
            continue
        track_name = str(row[2] if len(row) > 2 else '').strip()
        if not track_name:
            continue
        normalized_track_name = track_name_overrides.get(track_name, track_name)
        level_token = str(row[4] if len(row) > 4 else '').strip()
        token_parts = [part.strip() for part in level_token.split('|')] if level_token else []
        medal_level = token_parts[0] if token_parts else 'â€”'
        medal_value = token_parts[1] if len(token_parts) > 1 and token_parts[1] else (str(row[3] if len(row) > 3 else '').strip() or 'â€”')
        try:
            medal_level_value = int(medal_level)
        except ValueError:
            medal_level_value = None
        track_cost_key = {
            'Bonus': 'bonus_multiplier',
            'Cooldown': 'cooldown_seconds',
            'Duration': 'duration_seconds',
            'Range': 'range_m',
            'Damage': 'damage_multiplier',
            'Damage Reduction': 'damage_reduction_pct',
            'Linger': 'linger_slow_pct',
        }.get(normalized_track_name, _normalize_identity(normalized_track_name))
        medals_spent = _format_cumulative_cost(
            cumulative_costs.get((_normalize_identity(f'{current_bot} Bot'), track_cost_key, int(medal_level_value or -1)))
        ) if medal_level_value is not None else _DASH
        index[f'{current_bot}::{normalized_track_name}'] = {
            'medal_level': medal_level or 'â€”',
            'medals_spent': medals_spent,
            'medal_value': medal_value or 'â€”',
        }
    return index


def _guardian_track_surface_map() -> dict[str, list[dict[str, str]]]:
    return {
        'Attack': [
            {'track': 'Percentage', 'surface_id': 'state::guardian.attack.missing_health_damage_pct'},
            {'track': 'Cooldown', 'surface_id': 'state::guardian.attack.cooldown_seconds'},
            {'track': 'Targets', 'surface_id': 'state::guardian.attack.targets_count'},
        ],
        'Ally': [
            {'track': 'Recovery Amount', 'surface_id': 'state::guardian.ally.recovery_amount_pct'},
            {'track': 'Max Recovery', 'surface_id': 'state::guardian.ally.max_recovery_multiplier'},
            {'track': 'Cooldown', 'surface_id': 'state::guardian.ally.cooldown_seconds'},
        ],
        'Bounty': [
            {'track': 'Multiplier', 'surface_id': 'state::guardian.bounty.coin_multiplier'},
            {'track': 'Cooldown', 'surface_id': 'state::guardian.bounty.cooldown_seconds'},
            {'track': 'Targets', 'surface_id': 'state::guardian.bounty.targets_count'},
        ],
        'Fetch': [
            {'track': 'Cooldown', 'surface_id': 'state::guardian.fetch.cooldown_seconds'},
            {'track': 'Find Chance', 'surface_id': 'state::guardian.fetch.find_chance_pct'},
            {'track': 'Double Find Chance', 'surface_id': 'state::guardian.fetch.double_find_chance_pct'},
        ],
        'Summon': [
            {'track': 'Cooldown', 'surface_id': 'state::guardian.summon.cooldown_seconds'},
            {'track': 'Duration', 'surface_id': 'state::guardian.summon.duration_seconds'},
            {'track': 'Cash Bonus', 'surface_id': 'state::guardian.summon.cash_bonus_multiplier'},
        ],
        'Scout': [
            {'track': 'Cooldown', 'surface_id': 'state::guardian.scout.cooldown_seconds'},
            {'track': 'Range Bonus', 'surface_id': 'state::guardian.scout.range_bonus_multiplier'},
            {'track': 'Duration', 'surface_id': 'state::guardian.scout.duration_seconds'},
        ],
    }


def _extract_guardian_bits_spent(level_token: str) -> str:
    match = re.search(r'Cost\s+([0-9]+)', level_token or '')
    return match.group(1) if match else 'â€”'


def _build_guardian_track_metadata_index(account_state_payload: dict[str, object]) -> dict[str, dict[str, str]]:
    rows = (account_state_payload.get('raw_sections') or {}).get('Guardians') or []
    index: dict[str, dict[str, str]] = {}
    current_guardian = ''
    for row in rows:
        if not isinstance(row, list):
            continue
        guardian_name = str(row[0] if len(row) > 0 else '').strip()
        if guardian_name and guardian_name.lower() not in {'true', 'false'}:
            current_guardian = guardian_name
        if not current_guardian:
            continue
        track_name = str(row[2] if len(row) > 2 else '').strip()
        if not track_name:
            continue
        level_token = str(row[4] if len(row) > 4 else '').strip()
        token_parts = [part.strip() for part in level_token.split('|')] if level_token else []
        bit_level = token_parts[0] if token_parts else 'â€”'
        bit_value = token_parts[1] if len(token_parts) > 1 and token_parts[1] else (str(row[3] if len(row) > 3 else '').strip() or 'â€”')
        try:
            bit_level_value = int(bit_level)
        except ValueError:
            bit_level_value = None
        track_cost_key = _normalize_identity(track_name)
        bits_spent = _format_cumulative_cost(
            cumulative_costs.get((_normalize_identity(current_guardian), track_cost_key, bit_level_value))
        ) if bit_level_value is not None else _DASH
        index[f'{current_guardian}::{track_name}'] = {
            'bit_level': bit_level or 'â€”',
            'bits_spent': bits_spent,
            'bit_value': bit_value or 'â€”',
        }
    return index


def _guardian_start_value(metadata_value: object, start_row: dict[str, object], *, surface_id: str, value_type: str) -> str:
    return _row_display_value(start_row, surface_id=surface_id, value_type=value_type) or str(metadata_value or 'â€”')


def _guardian_recon_status(*, start_value: str) -> str:
    normalized = str(start_value or '').strip().replace('Ã¢â‚¬â€', 'â€”')
    return 'green' if normalized not in {'', 'â€”'} else 'amber'


def _join_display_tokens(*values: str) -> str:
    tokens: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        normalized = text.replace('â€”', '—')
        if normalized == '—':
            continue
        tokens.append(normalized)
    return ' Â· '.join(tokens) if tokens else 'â€”'


def _bot_recon_status(*, start_row: dict[str, object], effective_row: dict[str, object]) -> str:
    if str(start_row.get('status') or '') == 'resolved' and (
        not effective_row or str(effective_row.get('status') or '') == 'resolved'
    ):
        return 'green'
    return 'amber'


def _operator_workshop_row(
    *,
    name: str,
    start_row: dict[str, object],
    max_row: dict[str, object],
    canonical_row_id: str,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    meta = dict(metadata or {})
    base_value = _normalize_display_text(meta.get('base_value') or meta.get('resolved_value') or _DASH)
    return {
        'canonical_row_id': canonical_row_id,
        'display_label': name,
        'name': name,
        'workshop_level': _normalize_display_text(meta.get('level') or _DASH),
        'lab_effects': _normalize_display_text(meta.get('lab') or _DASH),
        'relics': _normalize_display_text(meta.get('relics') or _DASH),
        'base_subtotal': base_value,
        'module_effects': _normalize_display_text(meta.get('module') or _DASH),
        'card_effects': _normalize_display_text(meta.get('card') or _DASH),
        'base_loadout_subtotal': _normalize_display_text(meta.get('final') or _DASH),
        'enhancement_effects': _normalize_display_text(meta.get('enhancement') or _DASH),
        'start_of_run_modifier_total': _normalize_display_text(meta.get('modifier_total') or _DASH),
        'workshop_value': base_value,
        'start_of_run_value': _normalize_display_text(start_row.get('display_value') or meta.get('final') or _DASH),
        'other': _normalize_display_text(meta.get('other') or _DASH),
        'max_workshop_modifier_total': _normalize_display_text(meta.get('max_modifier_total') or _DASH),
        'max_workshop_value': _normalize_display_text(meta.get('max_value') or _DASH),
        'max_workshop_resolved_value': _normalize_display_text(meta.get('max_resolved_value') or _DASH),
        'perk_effects': _normalize_display_text(meta.get('perk') or _DASH),
        'max_progression_value': _normalize_display_text(max_row.get('display_value') or start_row.get('display_value') or meta.get('final') or _DASH),
        'reconciliation_status': _stats_reconciliation_status(start_row=start_row, max_row=max_row),
        'reconciliation_cell_flags': {},
    }


def _build_bot_track_metadata_index(account_state_payload: dict[str, object]) -> dict[str, dict[str, str]]:
    rows = (account_state_payload.get('raw_sections') or {}).get('Bots') or []
    index: dict[str, dict[str, str]] = {}
    cumulative_costs = _load_bot_cumulative_costs()
    current_bot = ''
    track_name_overrides = {'Damage R.': 'Damage Reduction'}
    track_cost_keys = {
        'Bonus': 'bonus_multiplier_x',
        'Cooldown': 'cooldown_seconds',
        'Duration': 'duration_seconds',
        'Range': 'range_meters',
        'Damage': 'damage_multiplier_x',
        'Damage Reduction': 'damage_reduction_pct',
        'Linger': 'linger_seconds',
    }
    for row in rows:
        if not isinstance(row, list):
            continue
        bot_name = str(row[0] if len(row) > 0 else '').strip()
        if bot_name and bot_name.lower() not in {'true', 'false'}:
            current_bot = bot_name.replace(' Bot', '')
        if not current_bot:
            continue
        track_name = str(row[2] if len(row) > 2 else '').strip()
        if not track_name:
            continue
        normalized_track_name = track_name_overrides.get(track_name, track_name)
        level_token = str(row[4] if len(row) > 4 else '').strip()
        token_parts = [part.strip() for part in level_token.split('|')] if level_token else []
        medal_level = token_parts[0] if token_parts else _DASH
        medal_value = token_parts[1] if len(token_parts) > 1 and token_parts[1] else (str(row[3] if len(row) > 3 else '').strip() or _DASH)
        try:
            medal_level_value = int(medal_level)
        except ValueError:
            medal_level_value = None
        medals_spent = _format_cumulative_cost(
            cumulative_costs.get((_normalize_identity(f'{current_bot} Bot'), track_cost_keys.get(normalized_track_name, _normalize_identity(normalized_track_name)), medal_level_value))
        ) if medal_level_value is not None else _DASH
        index[f'{current_bot}::{normalized_track_name}'] = {
            'medal_level': _normalize_display_text(medal_level or _DASH),
            'medals_spent': medals_spent,
            'medal_value': _normalize_display_text(medal_value or _DASH),
        }
    return index


def _build_guardian_track_metadata_index(account_state_payload: dict[str, object]) -> dict[str, dict[str, str]]:
    rows = (account_state_payload.get('raw_sections') or {}).get('Guardians') or []
    index: dict[str, dict[str, str]] = {}
    cumulative_costs = _load_guardian_cumulative_costs()
    current_guardian = ''
    track_cost_keys = {
        'Percentage': 'percentage',
        'Cooldown': 'cooldown',
        'Targets': 'targets',
        'Recovery Amount': 'recovery_amount',
        'Max Recovery': 'max_recovery',
        'Multiplier': 'multiplier',
        'Find Chance': 'find_chance',
        'Double Find Chance': 'double_find_chance',
        'Cash Bonus': 'cash_bonus',
        'Range Bonus': 'range_bonus',
        'Duration': 'duration',
    }
    for row in rows:
        if not isinstance(row, list):
            continue
        guardian_name = str(row[0] if len(row) > 0 else '').strip()
        if guardian_name and guardian_name.lower() not in {'true', 'false'}:
            current_guardian = guardian_name
        if not current_guardian:
            continue
        track_name = str(row[2] if len(row) > 2 else '').strip()
        if not track_name:
            continue
        level_token = str(row[4] if len(row) > 4 else '').strip()
        token_parts = [part.strip() for part in level_token.split('|')] if level_token else []
        bit_level = token_parts[0] if token_parts else _DASH
        bit_value = token_parts[1] if len(token_parts) > 1 and token_parts[1] else (str(row[3] if len(row) > 3 else '').strip() or _DASH)
        try:
            bit_level_value = int(bit_level)
        except ValueError:
            bit_level_value = None
        bits_spent = _format_cumulative_cost(
            cumulative_costs.get((_normalize_identity(current_guardian), track_cost_keys.get(track_name, _normalize_identity(track_name)), bit_level_value))
        ) if bit_level_value is not None else _DASH
        index[f'{current_guardian}::{track_name}'] = {
            'bit_level': _normalize_display_text(bit_level or _DASH),
            'bits_spent': bits_spent,
            'bit_value': _normalize_display_text(bit_value or _DASH),
        }
    return index


def _guardian_start_value(metadata_value: object, start_row: dict[str, object], *, surface_id: str, value_type: str) -> str:
    return _normalize_display_text(_row_display_value(start_row, surface_id=surface_id, value_type=value_type) or metadata_value or _DASH)


def _guardian_recon_status(*, start_row: dict[str, object], metadata: dict[str, str], start_value: str) -> str:
    # Guardian rows reconcile green only when current-level bit metadata resolves and the
    # sanctioned start_of_run row resolves for the same visible track.
    if str(start_row.get('status') or '') != 'resolved':
        return 'amber'
    if _normalize_display_text(metadata.get('bit_level')) == _DASH or _normalize_display_text(metadata.get('bits_spent')) == _DASH:
        return 'amber'
    return 'green' if _normalize_display_text(start_value) != _DASH else 'amber'


def _join_display_tokens(*values: str) -> str:
    tokens: list[str] = []
    for value in values:
        text = _normalize_display_text(value)
        if text == _DASH:
            continue
        tokens.append(text)
    return ' · '.join(tokens) if tokens else _DASH


def _bot_recon_status(*, start_row: dict[str, object], effective_row: dict[str, object], metadata: dict[str, str], requires_effective: bool) -> str:
    # Bot rows reconcile green only when cumulative medal metadata resolves from KB,
    # the start-state QE row resolves, and any published effective surface also resolves.
    if _normalize_display_text(metadata.get('medal_level')) == _DASH or _normalize_display_text(metadata.get('medals_spent')) == _DASH:
        return 'amber'
    if str(start_row.get('status') or '') != 'resolved':
        return 'amber'
    if requires_effective and str(effective_row.get('status') or '') != 'resolved':
        return 'amber'
    return 'green'


def _build_stats_uw_operator_panel(
    *,
    account_state_payload: dict[str, object],
    input_dashboard_payload: dict[str, object],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
    qe_dashboard_publications: dict[str, object] | None = None,
    uw_surface_effects: dict[str, dict[str, list[str]]] | None = None,
    uw_section_other_entries: dict[str, list[tuple[str, str]]] | None = None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    gaps: list[dict[str, str]] = []
    input_uw_panel = next(
        (panel for panel in (input_dashboard_payload.get('panels') or []) if str((panel or {}).get('panel_id') or '') == 'ultimate_weapons'),
        {},
    )
    input_rows = ((input_uw_panel.get('payload') or {}).get('rows') or [])
    row_index = {
        f"{str(row.get('uw') or '').strip()}::{str(row.get('track') or '').strip()}": dict(row or {})
        for row in input_rows
        if isinstance(row, dict)
    }
    track_surface_map = _uw_track_surface_map()
    other_specs_by_section = _uw_other_surface_specs(stats_layout)
    surface_effect_map = uw_surface_effects or {}
    section_other_from_inputs = uw_section_other_entries or {}
    sections: dict[str, list[dict[str, object]]] = {}
    for uw_name, track_map in track_surface_map.items():
        section_rows: list[dict[str, object]] = []
        primary_other_entries = [
            (
                spec['label'],
                (dict(rows_start.get(spec['surface_id']) or {}).get('display_value')
                 or dict(rows_max.get(spec['surface_id']) or {}).get('display_value')
                 or '—'),
            )
            for spec in other_specs_by_section.get(uw_name, [])
            if (
                dict(rows_start.get(spec['surface_id']) or {}).get('display_value') not in (None, '')
                or dict(rows_max.get(spec['surface_id']) or {}).get('display_value') not in (None, '')
            )
        ]
        primary_other_entries.extend(section_other_from_inputs.get(uw_name, []))
        first_row = True
        for track_name, surface_id in track_map.items():
            metadata = dict(row_index.get(f'{uw_name}::{track_name}') or {})
            effect_map = surface_effect_map.get(surface_id) or {}
            start_row = dict(rows_start.get(surface_id) or {})
            max_row = dict(rows_max.get(surface_id) or {})
            start_value = _normalize_display_text(start_row.get('display_value') or metadata.get('final') or _DASH)
            max_value = _normalize_display_text(max_row.get('display_value') or metadata.get('final') or _DASH)
            other_value = _format_named_other_entries(primary_other_entries) if first_row else _DASH
            perk_value = _normalize_display_text(metadata.get('perk') or (' · '.join(effect_map.get('perk') or []) if (effect_map.get('perk') or []) else _DASH))
            section_rows.append({
                'canonical_row_id': surface_id,
                'display_label': track_name,
                'name': track_name,
                'workshop_level': _normalize_display_text(metadata.get('stone_level') or _DASH),
                'stone_value': _normalize_display_text(metadata.get('stone_value') or _DASH),
                'lab_effects': _normalize_display_text(metadata.get('lab') or (' · '.join(effect_map.get('lab') or []) if (effect_map.get('lab') or []) else _DASH)),
                'module_effects': _normalize_display_text(metadata.get('module') or (' · '.join(effect_map.get('module') or []) if (effect_map.get('module') or []) else _DASH)),
                'start_of_run_value': start_value,
                'perk_effects': perk_value,
                'max_progression_value': max_value,
                'other': other_value,
                'reconciliation_status': _uw_recon_status(
                    start_row=start_row,
                    max_row=max_row,
                    stone_value=metadata.get('stone_value') or _DASH,
                ),
                'reconciliation_cell_flags': {},
            })
            first_row = False
        plus_key = f'{uw_name}::'
        for key, plus_payload in sorted((account_state_payload.get('uw_plus_tracks') or {}).items()):
            if not str(key).startswith(plus_key):
                continue
            display_token = _normalize_display_text((plus_payload or {}).get('display_token') or _DASH)
            plus_name = str((plus_payload or {}).get('plus_track_name') or str(key).split('::', 1)[-1] or 'UW+')
            section_rows.append({
                'canonical_row_id': f'uw_plus::{uw_name}::{plus_name}',
                'display_label': f'UW+ {plus_name}',
                'name': f'UW+ {plus_name}',
                'workshop_level': _DASH,
                'stone_value': display_token,
                'lab_effects': _DASH,
                'module_effects': _DASH,
                'start_of_run_value': _DASH,
                'perk_effects': _DASH,
                'max_progression_value': _DASH,
                'other': _DASH,
                'reconciliation_status': 'amber',
                'reconciliation_cell_flags': {},
            })
        sections[uw_name] = section_rows
    return ({
        'panel_id': 'ultimate_weapons',
        'panel_type': 'workshop_stat_table',
        'title': 'Ultimate Weapons',
        'payload': {
            'artifact': 'stats_operator_workshop_rows',
            'owner': 'publication',
            'columns': _uw_operator_table_columns(),
            'sections': [
                {'section_id': f'uw::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
                for section_name, rows in sections.items()
            ],
        },
    }, gaps)


def _row_module_effect_display(row: dict[str, object], *, surface_value_type: str) -> str:
    return _format_effect_from_contributors(
        row,
        source_classes=('module_main', 'module_substat', 'module_unique'),
        surface_value_type=surface_value_type,
    )


def _row_level_display(metadata: dict[str, object]) -> str:
    level = metadata.get('level')
    return '' if level in (None, '') else str(level)


def _build_stats_track_operator_panel(
    *,
    panel_id: str,
    title: str,
    specs_key: str,
    rows_start: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
    track_rows: list[dict[str, object]],
    entity_names_by_key: dict[str, str],
    include_labs: bool,
    include_modules: bool,
    include_perks: bool,
    include_max_progression: bool,
) -> dict[str, object]:
    row_index = {
        f"{str(row.get('entity') or '').strip()}::{str(row.get('track') or '').strip()}": dict(row or {})
        for row in track_rows
    }
    sections: dict[str, list[dict[str, object]]] = {}
    for spec in _stats_surface_specs(stats_layout, specs_key):
        surface_id = spec['surface_id']
        parts = surface_id.split('.')
        entity_key = parts[1] if len(parts) > 2 else ''
        entity_name = entity_names_by_key.get(entity_key, spec['label'])
        row_name = _reduce_prefixed_label(spec['label'], entity_name)
        track_key = f'{entity_name}::{row_name}'
        start_row = dict(rows_start.get(surface_id) or {})
        metadata = row_index.get(track_key) or {}
        surface_value_type = str(start_row.get('value_type') or '')
        row_payload = _operator_workshop_row(
            name=row_name,
            start_row=start_row,
            max_row={} if not include_max_progression else dict(rows_start.get(surface_id) or {}),
            canonical_row_id=str(spec.get('canonical_row_id') or surface_id),
            metadata={
                'level': _row_level_display(metadata),
                'lab': _format_effect_from_contributors(
                    start_row,
                    source_classes=('labs',),
                    surface_value_type=surface_value_type,
                ) if include_labs else '—',
                'module': _row_module_effect_display(start_row, surface_value_type=surface_value_type) if include_modules else '—',
                'perk': _format_effect_from_contributors(
                    start_row,
                    source_classes=('perk', 'perks', 'perk_effect'),
                    surface_value_type=surface_value_type,
                ) if include_perks else '—',
                'resolved_value': _row_display_value(start_row, surface_id=surface_id, value_type=surface_value_type) or metadata.get('resolved_value') or '—',
            },
        )
        if not include_max_progression:
            row_payload['max_progression_value'] = '—'
        sections.setdefault(entity_name, []).append(
            row_payload
        )
    return {
        'panel_id': panel_id,
        'panel_type': 'workshop_stat_table',
        'title': title,
        'payload': _operator_panel_payload(
            panel_id=panel_id,
            sections=sections,
            level_label='Level',
            include_labs=include_labs,
            include_modules=include_modules,
            include_perks=include_perks,
            include_max_progression=include_max_progression,
        ),
    }


def _build_stats_bots_operator_panel(
    *,
    account_state_payload: dict[str, object],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
) -> dict[str, object]:
    del rows_max, stats_layout
    metadata_index = _build_bot_track_metadata_index(account_state_payload)
    global_range_row = dict(rows_start.get('state::bot.global.range_bonus_m') or {})
    global_range_value_type = str(global_range_row.get('value_type') or '')
    sections: dict[str, list[dict[str, object]]] = {}
    for bot_name, track_specs in _bot_track_surface_map().items():
        section_rows: list[dict[str, object]] = []
        for spec in track_specs:
            track_name = spec['track']
            surface_id = spec['surface_id']
            effective_surface_id = spec['effective_surface_id']
            metadata = metadata_index.get(f'{bot_name}::{track_name}') or {}
            start_row = dict(rows_start.get(surface_id) or {})
            effective_row = dict(rows_start.get(effective_surface_id) or {}) if effective_surface_id else {}
            surface_value_type = str(start_row.get('value_type') or '')
            module_value = _row_module_effect_display(start_row, surface_value_type=surface_value_type)
            if track_name == 'Range':
                module_value = _join_display_tokens(
                    module_value,
                    _format_effect_from_contributors(
                        global_range_row,
                        source_classes=('module_main', 'module_substat', 'module_unique'),
                        surface_value_type=global_range_value_type,
                    ),
                )
            section_rows.append({
                'canonical_row_id': surface_id,
                'display_label': track_name,
                'name': track_name,
                'medal_level': str(metadata.get('medal_level') or 'â€”'),
                'medals_spent': str(metadata.get('medals_spent') or 'â€”'),
                'medal_value': str(metadata.get('medal_value') or 'â€”'),
                'lab_effects': _format_effect_from_contributors(
                    start_row,
                    source_classes=('labs',),
                    surface_value_type=surface_value_type,
                ),
                'module_effects': module_value,
                'start_of_run_value': _row_display_value(start_row, surface_id=surface_id, value_type=surface_value_type) or 'â€”',
                'effective_value': str(effective_row.get('display_value') or 'â€”'),
                'reconciliation_status': _bot_recon_status(start_row=start_row, effective_row=effective_row),
                'reconciliation_cell_flags': {},
            })
        sections[bot_name] = section_rows
    return {
        'panel_id': 'bots',
        'panel_type': 'workshop_stat_table',
        'title': 'Bots',
        'payload': {
            'artifact': 'stats_operator_workshop_rows',
            'owner': 'publication',
            'columns': _bot_operator_table_columns(),
            'sections': [
                {'section_id': f'bots::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
                for section_name, rows in sections.items()
            ],
        },
    }


def _build_stats_guardians_operator_panel(
    *,
    account_state_payload: dict[str, object],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
) -> dict[str, object]:
    del rows_max, stats_layout
    metadata_index = _build_guardian_track_metadata_index(account_state_payload)
    guardian_value_index = {
        f"{guardian_name}::{str(track.get('track_name') or '').strip()}": dict(track or {})
        for guardian_name, tracks in (account_state_payload.get('guardian_tracks') or {}).items()
        for track in (tracks or [])
    }
    sections: dict[str, list[dict[str, object]]] = {}
    for guardian_name, track_specs in _guardian_track_surface_map().items():
        section_rows: list[dict[str, object]] = []
        for spec in track_specs:
            track_name = spec['track']
            surface_id = spec['surface_id']
            start_row = dict(rows_start.get(surface_id) or {})
            metadata = metadata_index.get(f'{guardian_name}::{track_name}') or {}
            guardian_snapshot = guardian_value_index.get(f'{guardian_name}::{track_name}') or {}
            surface_value_type = str(start_row.get('value_type') or guardian_snapshot.get('resolved_unit') or '')
            start_value = _guardian_start_value(
                guardian_snapshot.get('resolved_value'),
                start_row,
                surface_id=surface_id,
                value_type=surface_value_type,
            )
            section_rows.append({
                'canonical_row_id': surface_id,
                'display_label': track_name,
                'name': track_name,
                'bit_level': str(metadata.get('bit_level') or 'â€”'),
                'bits_spent': str(metadata.get('bits_spent') or 'â€”'),
                'bit_value': str(metadata.get('bit_value') or 'â€”'),
                'start_of_run_value': start_value,
                'reconciliation_status': _guardian_recon_status(start_value=start_value),
                'reconciliation_cell_flags': {},
            })
        sections[guardian_name] = section_rows
    return {
        'panel_id': 'guardians',
        'panel_type': 'workshop_stat_table',
        'title': 'Guardians',
        'payload': {
            'artifact': 'stats_operator_workshop_rows',
            'owner': 'publication',
            'columns': _guardian_operator_table_columns(),
            'sections': [
                {'section_id': f'guardians::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
                for section_name, rows in sections.items()
            ],
        },
    }


def _build_stats_uw_operator_panel(
    *,
    account_state_payload: dict[str, object],
    input_dashboard_payload: dict[str, object],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
    qe_dashboard_publications: dict[str, object] | None = None,
    uw_surface_effects: dict[str, dict[str, list[str]]] | None = None,
    uw_section_other_entries: dict[str, list[tuple[str, str]]] | None = None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    del qe_dashboard_publications
    gaps: list[dict[str, str]] = []
    input_uw_panel = next(
        (panel for panel in (input_dashboard_payload.get('panels') or []) if str((panel or {}).get('panel_id') or '') == 'ultimate_weapons'),
        {},
    )
    input_rows = ((input_uw_panel.get('payload') or {}).get('rows') or [])
    row_index = {
        f"{str(row.get('uw') or '').strip()}::{str(row.get('track') or '').strip()}": dict(row or {})
        for row in input_rows
        if isinstance(row, dict)
    }
    track_surface_map = _uw_track_surface_map()
    other_specs_by_section = _uw_other_surface_specs(stats_layout)
    surface_effect_map = uw_surface_effects or {}
    section_other_from_inputs = uw_section_other_entries or {}
    sections: dict[str, list[dict[str, object]]] = {}
    for uw_name, track_map in track_surface_map.items():
        section_rows: list[dict[str, object]] = []
        supplemental_entries = [
            (
                spec['label'],
                _section_surface_value(
                    dict(rows_start.get(spec['surface_id']) or {}) or dict(rows_max.get(spec['surface_id']) or {})
                ),
            )
            for spec in other_specs_by_section.get(uw_name, [])
            if (
                dict(rows_start.get(spec['surface_id']) or {}).get('display_value') not in (None, '')
                or dict(rows_max.get(spec['surface_id']) or {}).get('display_value') not in (None, '')
            )
        ]
        supplemental_entries.extend(section_other_from_inputs.get(uw_name, []))
        for track_name, surface_id in track_map.items():
            metadata = dict(row_index.get(f'{uw_name}::{track_name}') or {})
            effect_map = surface_effect_map.get(surface_id) or {}
            start_row = dict(rows_start.get(surface_id) or {})
            max_row = dict(rows_max.get(surface_id) or {})
            stone_text = _uw_stone_value_text(surface_id, metadata, start_row)
            lab_value = _normalize_effect_text_for_surface(surface_id, metadata.get('lab')) if metadata.get('lab') not in (None, '') else (_format_compacted_display_sum(*(effect_map.get('lab') or []), fallback_surface_id=surface_id) if (effect_map.get('lab') or []) else None)
            if not lab_value:
                lab_value = _format_effect_from_contributors(
                    start_row,
                    source_classes=('labs',),
                    surface_value_type=str(start_row.get('value_type') or ''),
                )
            module_value = _normalize_effect_text_for_surface(surface_id, metadata.get('module')) if metadata.get('module') not in (None, '') else (_format_compacted_display_sum(*(effect_map.get('module') or []), fallback_surface_id=surface_id) if (effect_map.get('module') or []) else None)
            if not module_value:
                module_value = _format_effect_from_contributors(
                    start_row,
                    source_classes=('module_main', 'module_substat', 'module_unique'),
                    surface_value_type=str(start_row.get('value_type') or ''),
                )
            perk_value = _normalize_effect_text_for_surface(surface_id, metadata.get('perk')) if metadata.get('perk') not in (None, '') else (_format_compacted_display_sum(*(effect_map.get('perk') or []), fallback_surface_id=surface_id) if (effect_map.get('perk') or []) else None)
            if not perk_value:
                perk_value = _format_effect_from_contributors(
                    max_row or start_row,
                    source_classes=('perk', 'perks', 'perk_effect'),
                    surface_value_type=str((max_row or start_row).get('value_type') or ''),
                )
            lab_text = _normalize_display_text(lab_value or _DASH)
            module_text = _normalize_display_text(module_value or _DASH)
            other_text = _DASH
            start_expected, _suffix = _sum_display_terms(stone_text, lab_text, module_text, other_text)
            start_value = _surface_display_value(
                start_row,
                surface_id=surface_id,
                fallback_value=start_expected if start_expected is not None else metadata.get('final'),
            )
            max_value = _surface_display_value(
                max_row,
                surface_id=surface_id,
                fallback_value=metadata.get('final'),
            )
            perk_text = _normalize_display_text(perk_value or _DASH)
            if perk_text == _DASH:
                perk_text = _derived_uw_perk_delta_text(
                    surface_id=surface_id,
                    start_value=start_value,
                    max_value=max_value,
                    start_expected=start_expected,
                )
            max_expected, _suffix = _sum_display_terms(stone_text, lab_text, module_text, other_text, perk_text)
            if not _row_is_resolved(max_row) and max_expected is not None:
                max_value = _surface_display_value(
                    max_row,
                    surface_id=surface_id,
                    fallback_value=max_expected,
                )
            uw_recon_status = 'amber'
            if not _display_terms_parseable(stone_text, start_value, max_value, lab_text, module_text, perk_text):
                uw_recon_status = 'red'
            elif start_expected is not None and max_expected is not None:
                start_number, _ = _parse_display_number(start_value)
                max_number, _ = _parse_display_number(max_value)
                if start_number is None or max_number is None:
                    uw_recon_status = 'red'
                elif abs(start_expected - start_number) < 0.011 and abs(max_expected - max_number) < 0.011:
                    uw_recon_status = 'green'
                else:
                    uw_recon_status = 'red'
            section_rows.append({
                'canonical_row_id': surface_id,
                'display_label': track_name,
                'name': track_name,
                'workshop_level': _normalize_display_text(metadata.get('stone_level') or _DASH),
                'stone_value': stone_text,
                'lab_effects': lab_text,
                'module_effects': module_text,
                'start_of_run_value': start_value,
                'perk_effects': perk_text,
                'max_progression_value': max_value,
                'other': other_text,
                'reconciliation_status': uw_recon_status,
                'reconciliation_cell_flags': {},
            })
        plus_key = f'{uw_name}::'
        for key, plus_payload in sorted((account_state_payload.get('uw_plus_tracks') or {}).items()):
            if not str(key).startswith(plus_key):
                continue
            plus_name = str((plus_payload or {}).get('plus_track_name') or str(key).split('::', 1)[-1] or 'UW+')
            section_rows.append({
                'canonical_row_id': f'uw_plus::{uw_name}::{plus_name}',
                'display_label': f'UW+: {plus_name}',
                'name': f'UW+: {plus_name}',
                'workshop_level': _DASH,
                'stone_value': _normalize_display_text((plus_payload or {}).get('display_token') or _DASH),
                'lab_effects': _DASH,
                'module_effects': _DASH,
                'start_of_run_value': _DASH,
                'perk_effects': _DASH,
                'max_progression_value': _DASH,
                'other': _DASH,
                'reconciliation_status': 'not_applicable',
                'reconciliation_cell_flags': {},
                'row_status': 'non_recon',
            })
        section_rows.extend(_build_supplemental_rows(prefix=f'uw::{_normalize_identity(uw_name)}', entries=supplemental_entries))
        sections[uw_name] = section_rows
    return ({
        'panel_id': 'ultimate_weapons',
        'panel_type': 'workshop_stat_table',
        'title': 'Ultimate Weapons',
        'payload': {
            'artifact': 'stats_operator_workshop_rows',
            'owner': 'publication',
            'columns': _uw_operator_table_columns(),
            'sections': [
                {'section_id': f'uw::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
                for section_name, rows in sections.items()
            ],
        },
    }, gaps)


def _build_stats_bots_operator_panel(
    *,
    account_state_payload: dict[str, object],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
) -> dict[str, object]:
    del rows_max, stats_layout
    metadata_index = _build_bot_track_metadata_index(account_state_payload)
    global_range_row = dict(rows_start.get('state::bot.global.range_bonus_m') or {})
    global_range_value_type = str(global_range_row.get('value_type') or '')
    sections: dict[str, list[dict[str, object]]] = {}
    total_spent_values: list[str] = []
    for bot_name, track_specs in _bot_track_surface_map().items():
        section_rows: list[dict[str, object]] = []
        for spec in track_specs:
            track_name = spec['track']
            surface_id = spec['surface_id']
            metadata = metadata_index.get(f'{bot_name}::{track_name}') or {}
            start_row = dict(rows_start.get(surface_id) or {})
            surface_value_type = str(start_row.get('value_type') or '')
            module_value = _row_module_effect_display(start_row, surface_value_type=surface_value_type)
            if track_name == 'Range':
                module_value = _join_display_tokens(
                    module_value,
                    _format_effect_from_contributors(
                        global_range_row,
                        source_classes=('module_main', 'module_substat', 'module_unique'),
                        surface_value_type=global_range_value_type,
                    ),
                )
            lab_effects = _normalize_display_text(
                _format_effect_from_contributors(
                    start_row,
                    source_classes=('labs',),
                    surface_value_type=surface_value_type,
                )
            )
            start_value = _surface_display_value(
                start_row,
                surface_id=surface_id,
                fallback_value=metadata.get('medal_value'),
            )
            section_rows.append({
                'canonical_row_id': surface_id,
                'display_label': _normalize_display_text(track_name),
                'name': _normalize_display_text(track_name),
                'medal_level': _normalize_display_text(metadata.get('medal_level') or _DASH),
                'medals_spent': _normalize_display_text(metadata.get('medals_spent') or _DASH),
                'medal_value': _normalize_display_text(metadata.get('medal_value') or _DASH),
                'lab_effects': lab_effects,
                'module_effects': _normalize_display_text(module_value),
                'start_of_run_value': start_value,
                'reconciliation_status': _bot_recon_status_explicit(
                    surface_id=surface_id,
                    start_value=start_value,
                    metadata=metadata,
                    lab_effects=lab_effects,
                    module_effects=_normalize_display_text(module_value),
                ),
                'reconciliation_cell_flags': {},
            })
            total_spent_values.append(metadata.get('medals_spent') or _DASH)
        sections[bot_name] = section_rows
    sections['Totals'] = [{
        'canonical_row_id': 'bots::total_spent',
        'display_label': 'Total',
        'name': 'Total',
        'medal_level': _DASH,
        'medals_spent': _cumulative_total_text(*total_spent_values),
        'medal_value': _DASH,
        'lab_effects': _DASH,
        'module_effects': _DASH,
        'start_of_run_value': _DASH,
        'reconciliation_status': 'not_applicable',
        'reconciliation_cell_flags': {},
        'row_status': 'non_recon',
    }]
    return {
        'panel_id': 'bots',
        'panel_type': 'workshop_stat_table',
        'title': 'Bots',
        'payload': {
            'artifact': 'stats_operator_workshop_rows',
            'owner': 'publication',
            'columns': _bot_operator_table_columns(),
            'sections': [
                {'section_id': f'bots::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
                for section_name, rows in sections.items()
            ],
        },
    }


def _build_stats_guardians_operator_panel(
    *,
    account_state_payload: dict[str, object],
    rows_start: dict[str, dict[str, object]],
    rows_max: dict[str, dict[str, object]],
    stats_layout: dict[str, object],
) -> dict[str, object]:
    del rows_max, stats_layout
    metadata_index = _build_guardian_track_metadata_index(account_state_payload)
    guardian_value_index = {
        f"{guardian_name}::{str(track.get('track_name') or '').strip()}": dict(track or {})
        for guardian_name, tracks in (account_state_payload.get('guardian_tracks') or {}).items()
        for track in (tracks or [])
    }
    sections: dict[str, list[dict[str, object]]] = {}
    total_spent_values: list[str] = []
    for guardian_name, track_specs in _guardian_track_surface_map().items():
        section_rows: list[dict[str, object]] = []
        for spec in track_specs:
            track_name = spec['track']
            surface_id = spec['surface_id']
            start_row = dict(rows_start.get(surface_id) or {})
            metadata = metadata_index.get(f'{guardian_name}::{track_name}') or {}
            guardian_snapshot = guardian_value_index.get(f'{guardian_name}::{track_name}') or {}
            start_value = _surface_display_value(
                start_row,
                surface_id=surface_id,
                fallback_value=guardian_snapshot.get('resolved_value'),
            )
            bit_value = _normalize_display_text(metadata.get('bit_value') or _DASH)
            section_rows.append({
                'canonical_row_id': surface_id,
                'display_label': _normalize_display_text(track_name),
                'name': _normalize_display_text(track_name),
                'bit_level': _normalize_display_text(metadata.get('bit_level') or _DASH),
                'bits_spent': _normalize_display_text(metadata.get('bits_spent') or _DASH),
                'bit_value': bit_value,
                'start_of_run_value': start_value,
                'reconciliation_status': _guardian_recon_status_explicit(
                    bit_value=bit_value,
                    start_value=start_value,
                    bits_spent=_normalize_display_text(metadata.get('bits_spent') or _DASH),
                ),
                'reconciliation_cell_flags': {},
            })
            total_spent_values.append(metadata.get('bits_spent') or _DASH)
        sections[guardian_name] = section_rows
    sections['Totals'] = [{
        'canonical_row_id': 'guardians::total_spent',
        'display_label': 'Total',
        'name': 'Total',
        'bit_level': _DASH,
        'bits_spent': _cumulative_total_text(*total_spent_values),
        'bit_value': _DASH,
        'start_of_run_value': _DASH,
        'reconciliation_status': 'not_applicable',
        'reconciliation_cell_flags': {},
        'row_status': 'non_recon',
    }]
    return {
        'panel_id': 'guardians',
        'panel_type': 'workshop_stat_table',
        'title': 'Guardians',
        'payload': {
            'artifact': 'stats_operator_workshop_rows',
            'owner': 'publication',
            'columns': _guardian_operator_table_columns(),
            'sections': [
                {'section_id': f'guardians::{section_name.lower().replace(" ", "_")}', 'title': section_name, 'rows': rows}
                for section_name, rows in sections.items()
            ],
        },
    }


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
    qe_dashboard_publications: dict[str, object] | None = None,
    stat_inputs_payload: list[dict[str, object]] | None = None,
    annotate_display_fields: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    stats_layout = dict(load_section_layout_contract().get('stats_dashboard') or {})
    primary_panel_order = [str(name) for name in (stats_layout.get('primary_panel_order') or stats_layout.get('panel_order') or [])]
    secondary_panel_order = [str(name) for name in (stats_layout.get('secondary_panel_order') or [])]
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
    ep_compare = dict(ep_compare_publishable or {})
    uw_surface_effects, uw_section_other_entries = _build_uw_stat_input_maps(stat_inputs_payload)
    upstream_gaps: list[dict[str, str]] = []
    variants: dict[str, dict[str, list[dict[str, object]]]] = {}
    secondary_variants: dict[str, dict[str, list[dict[str, object]]]] = {}
    for preset_name in preset_opts:
        start_rows_hydrated = _rows_with_qe_derived_values(_stats_rows_by_surface(query_rows_start_of_run, preset_name), annotate_display_fields=annotate_display_fields)
        max_rows_hydrated = _rows_with_qe_derived_values(_stats_rows_by_surface(query_rows_max_progression, preset_name), annotate_display_fields=annotate_display_fields)
        variants[preset_name] = {}
        secondary_variants[preset_name] = {}
        for state_mode in state_mode_options:
            rows_start = start_rows_hydrated
            rows_max = max_rows_hydrated
            primary_panels: list[dict[str, object]] = []
            secondary_panels: list[dict[str, object]] = []
            workshop_payload = publish_workshop_reconciliation_payload(
                stats_layout=stats_layout,
                rows_start=rows_start,
                rows_max=rows_max,
                account_state_payload=account_state_payload,
                selected_preset=preset_name,
                surface_specs=_stats_surface_specs,
            )
            primary_panels.append({'panel_id': 'workshop', 'panel_type': 'workshop_stat_table', 'title': 'Workshop', 'payload': workshop_payload})
            uw_panel, uw_panel_gaps = _build_stats_uw_operator_panel(
                account_state_payload=account_state_payload,
                input_dashboard_payload=input_dashboard_payload,
                rows_start=rows_start,
                rows_max=rows_max,
                stats_layout=stats_layout,
                qe_dashboard_publications=qe_dashboard_publications,
                uw_surface_effects=uw_surface_effects,
                uw_section_other_entries=uw_section_other_entries,
            )
            if uw_panel:
                primary_panels.append(uw_panel)
                upstream_gaps.extend(uw_panel_gaps)
            else:
                upstream_gaps.append(_dashboard_gap('ultimate_weapons', 'stats_primary_surface_missing', 'ultimate weapon operator payload unavailable for Stats primary surface'))
            primary_panels.append(
                _build_stats_bots_operator_panel(
                    account_state_payload=account_state_payload,
                    rows_start=rows_start,
                    rows_max=rows_max,
                    stats_layout=stats_layout,
                )
            )
            primary_panels.append(
                _build_stats_guardians_operator_panel(
                    account_state_payload=account_state_payload,
                    rows_start=rows_start,
                    rows_max=rows_max,
                    stats_layout=stats_layout,
                )
            )
            modules_panel, module_panel_gaps = _build_modules_panel(module_card_payloads or {}, preset_name)
            if modules_panel:
                modules_panel['panel_type'] = 'context_modules'
                primary_panels.append(modules_panel)
                upstream_gaps.extend(module_panel_gaps)
            else:
                upstream_gaps.append(_dashboard_gap('modules', 'stats_primary_surface_missing', 'module_card_payloads missing selected preset payload for Stats primary surface'))
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            secondary_panels.append(
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
            variants[preset_name][state_mode] = primary_panels
            secondary_variants[preset_name][state_mode] = secondary_panels
    active_panels = (variants.get(selected_preset) or {}).get(selected_state_mode) or []
    active_secondary_panels = (secondary_variants.get(selected_preset) or {}).get(selected_state_mode) or []
    panel_map = {str(panel.get('panel_id')): panel for panel in active_panels}
    ordered_panels = [panel_map[panel_id] for panel_id in primary_panel_order if panel_id in panel_map]
    ordered_panels.extend(panel for panel in active_panels if str(panel.get('panel_id')) not in set(primary_panel_order))
    secondary_panel_map = {str(panel.get('panel_id')): panel for panel in active_secondary_panels}
    ordered_secondary_panels = [secondary_panel_map[panel_id] for panel_id in secondary_panel_order if panel_id in secondary_panel_map]
    ordered_secondary_panels.extend(panel for panel in active_secondary_panels if str(panel.get('panel_id')) not in set(secondary_panel_order))
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
        'secondary_panels': ordered_secondary_panels,
        'variants': variants,
        'secondary_variants': secondary_variants,
        'debug_manifest': {'source_artifacts': ['input_dashboard.json', 'module_card_payloads.json', 'run_stats_query_rows_start_of_run.json', 'run_stats_query_rows_max_progression.json', 'ep_oracle_compare.json'], 'generated_from': list((diagnostics.get('section_names') or []))},
    }
    if annotate_display_fields is not None:
        annotate_display_fields(payload)
    return payload
