from __future__ import annotations

from typing import Dict, Any
from models.statbook import StatRow


def _as_float(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compose_derived_surfaces(rows: Dict[str, StatRow]) -> None:
    """Compose derived/helper surfaces outside the stat engine core resolver.

    This keeps canonical bucket resolution free of post-resolution override logic.
    Only derived/mirror surfaces that depend on already-resolved rows are composed here.
    """
    coins_per_kill_row = rows.get('canonical_stat::coins_per_kill_bonus')
    if coins_per_kill_row is not None:
        rows['canonical_stat::coin_kill_multiplier'] = StatRow(
            stat_name='canonical_stat::coin_kill_multiplier',
            final_value=coins_per_kill_row.final_value,
            value_type=coins_per_kill_row.value_type,
            source_count=coins_per_kill_row.source_count,
            status=coins_per_kill_row.status,
            notes='Deprecated transition mirror of canonical_stat::coins_per_kill_bonus.',
            contributors=list(coins_per_kill_row.contributors),
            schema=coins_per_kill_row.schema,
        )

    disable_ads_row = rows.get('account_flag::account_flag.disable_ads')
    starter_pack_row = rows.get('account_flag::account_flag.starter_pack')
    epic_pack_row = rows.get('account_flag::account_flag.epic_pack')
    farming_tier_row = rows.get('account_context::account_context.farming_tier')
    legacy_coin_display_row = rows.get('account_context::account_context.coin_multiplier_display')
    helper_contributors = []

    def _helper_value(row_key, label):
        row = rows.get(row_key)
        if not row:
            return None
        helper_contributors.append({
            'stat_name': label,
            'source_family': 'helper_surface',
            'source_name': label,
            'value': row.final_value,
            'value_type': row.value_type,
            'stage': 'derived_surface_composition',
            'destination_object_type': 'canonical_stat',
            'destination_id': 'all_coin_bonus_multiplier',
            'resolver_id': 'standard_scalar_stat',
            'kb_mapped': True,
        })
        return _as_float(row.final_value)

    coin_bonus_val = _helper_value('canonical_stat::coin_bonus_multiplier', 'canonical_stat::coin_bonus_multiplier')
    coins_mult_val = _helper_value('canonical_stat::coins_multiplier', 'canonical_stat::coins_multiplier')
    theme_val = _helper_value('cosmetic_bonus::cosmetic_bonus.theme_song_coin_multiplier', 'cosmetic_bonus.theme_song_coin_multiplier')

    def _load_pack_multiplier_map():
        import csv
        from pathlib import Path
        table = Path(__file__).resolve().parents[1] / 'kb' / 'global-rules' / 'tables' / 'player-pack-coin-multipliers.csv'
        out = {}
        try:
            with table.open(newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for rec in reader:
                    out[rec['flag_destination']] = float(rec['multiplier'])
        except Exception:
            out = {
                'account_flag.disable_ads': 1.5,
                'account_flag.starter_pack': 2.0,
                'account_flag.epic_pack': 3.0,
            }
        return out

    pack_multiplier_map = _load_pack_multiplier_map()

    def _flag_pack_multiplier(row, label):
        multiplier = float(pack_multiplier_map.get(label, 1.0))
        enabled = bool(getattr(row, 'final_value', False)) if row is not None else False
        helper_contributors.append({
            'stat_name': label,
            'source_family': 'helper_surface',
            'source_name': label,
            'value': multiplier if enabled else 1.0,
            'value_type': 'multiplier',
            'stage': 'derived_surface_composition',
            'destination_object_type': 'canonical_stat',
            'destination_id': 'all_coin_bonus_multiplier',
            'resolver_id': 'standard_scalar_stat',
            'kb_mapped': True,
            'notes': 'kb_pack_flag_multiplier_if_true' if enabled else 'kb_pack_flag_multiplier_if_false',
        })
        return multiplier if enabled else 1.0

    disable_ads_mult = _flag_pack_multiplier(disable_ads_row, 'account_flag.disable_ads')
    starter_pack_mult = _flag_pack_multiplier(starter_pack_row, 'account_flag.starter_pack')
    epic_pack_mult = _flag_pack_multiplier(epic_pack_row, 'account_flag.epic_pack')

    tier_display_raw = None if farming_tier_row is None else (farming_tier_row.contributors[0].get('value') if farming_tier_row.contributors else farming_tier_row.final_value)
    helper_contributors.append({'stat_name': 'account_context.farming_tier', 'source_family': 'helper_surface', 'source_name': 'account_context.farming_tier', 'value': tier_display_raw, 'value_type': 'raw_text', 'stage': 'derived_surface_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True})
    helper_contributors.append({'stat_name': 'account_context.coin_multiplier_display', 'source_family': 'helper_surface', 'source_name': 'account_context.coin_multiplier_display', 'value': None if legacy_coin_display_row is None else (legacy_coin_display_row.contributors[0].get('value') if legacy_coin_display_row.contributors else legacy_coin_display_row.final_value), 'value_type': 'raw_text', 'stage': 'derived_surface_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True, 'notes': 'legacy_trace_only_not_used_numerically'})

    tier_multiplier_val = None
    if isinstance(tier_display_raw, str):
        import re, csv
        from pathlib import Path
        m = re.search(r'(\d+)', tier_display_raw)
        if m:
            tier_num = int(m.group(1))
            try:
                tier_table = Path(__file__).resolve().parents[1] / 'kb' / 'tournaments' / 'tables' / 'tier-battle-condition-levels.csv'
                with tier_table.open(newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for rec in reader:
                        if int(rec['tier']) == tier_num:
                            tier_multiplier_val = float(rec['coin_bonus'])
                            break
            except Exception:
                tier_multiplier_val = None
    if tier_multiplier_val is not None:
        helper_contributors.append({'stat_name': 'account_context.farming_tier_coin_multiplier', 'source_family': 'helper_surface', 'source_name': 'account_context.farming_tier_coin_multiplier', 'value': tier_multiplier_val, 'value_type': 'multiplier', 'stage': 'derived_surface_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True, 'notes': 'kb_tier_coin_bonus_lookup'})

    all_coin_value = None
    all_coin_status = 'mapped_not_resolved'
    all_coin_notes = 'Derived all-coin display surface: coin_bonus_multiplier x coins_multiplier x theme song coin multiplier x farming-tier coin bonus x numeric premium-pack multipliers (Disable Ads 1.5x, Starter Pack 2x, Epic Pack 3x when unlocked). Legacy account coin multiplier display remains trace-only.'
    required = [coin_bonus_val, coins_mult_val, theme_val, tier_multiplier_val]
    if all(v is not None for v in required):
        all_coin_value = coin_bonus_val * coins_mult_val * theme_val * tier_multiplier_val * disable_ads_mult * starter_pack_mult * epic_pack_mult
        all_coin_status = 'resolved'
    else:
        all_coin_notes += ' One or more required numeric helper surfaces were unavailable.'
    rows['canonical_stat::all_coin_bonus_multiplier'] = StatRow(
        stat_name='canonical_stat::all_coin_bonus_multiplier',
        final_value=all_coin_value,
        value_type='multiplier',
        source_count=len(helper_contributors),
        status=all_coin_status,
        notes=all_coin_notes,
        contributors=helper_contributors,
        schema={
            'unit': 'multiplier',
            'resolver': 'derived_surface_composer',
            'allowed_input_value_types': ['multiplier', 'raw_text'],
            'disallowed_input_value_types': ['level', 'display_token', 'missing_inventory'],
            'publish_gate_rules': ['composed_from_resolved_rows_only'],
            'expected_input_semantics': ['multiplier_display', 'multiplier_factor', 'resolved_numeric'],
            'explicit_caps': {},
        },
    )
