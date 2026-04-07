from __future__ import annotations

_DISPLAY_SUFFIXES: list[tuple[float, str]] = [(1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'k')]

_WORKSHOP_LABEL_ALIASES: dict[str, str] = {
    'Crit Chance': 'Critical Chance',
    'Crit Multiplier': 'Critical Factor',
    'Super Crit Chance': 'Super Critical Chance',
    'Super Crit Multiplier': 'Super Critical Mult',
    'Rend Armor Multiplier': 'Rend Armor Mult',
    'Rend Armor Chance': 'Rend Armor Chance',
    'Thorns': 'Thorn Damage',
    'Orb Count': 'Orbs',
    'Shockwave Interval': 'Shockwave Frequency',
    'Regen': 'Health Regen',
    'Coins / Kill': 'Coin / Kill Bonus',
    'Coins / Kill Bonus': 'Coin / Kill Bonus',
    'Coins / Wave': 'Coin / Wave',
    'Max Recovery': 'Max Amount',
}


def _sum_contributor_values_filtered(
    row: dict[str, object],
    *,
    source_classes: tuple[str, ...],
    contributor_prefixes: tuple[str, ...] = (),
    invert_prefix_match: bool = False,
) -> float | None:
    values: list[float] = []
    for contributor in (row.get('contributors') or []):
        if str((contributor or {}).get('source_class') or '') not in source_classes:
            continue
        contributor_id = str((contributor or {}).get('contributor_id') or '')
        prefix_match = any(contributor_id.startswith(prefix) for prefix in contributor_prefixes)
        if contributor_prefixes and ((prefix_match and invert_prefix_match) or (not prefix_match and not invert_prefix_match)):
            continue
        value = (contributor or {}).get('value')
        if isinstance(value, (int, float)):
            values.append(float(value))
    if not values:
        return None
    return float(sum(values))


def _contributor_display_kind(
    contributor: dict[str, object],
    *,
    surface_value_type: str,
) -> str:
    preferred = str((contributor.get('input_value_type') or contributor.get('value_type') or '')).strip().lower()
    if preferred in {'pct', 'percent_display'}:
        return 'pct'
    if preferred in {'multiplier', 'multiplier_display'}:
        return 'multiplier'

    source_class = str(contributor.get('source_class') or '').lower()
    contributor_id = str(contributor.get('contributor_id') or '').lower()

    if source_class.startswith('module'):
        if '__pct@@' in contributor_id:
            return 'multiplier'
        if surface_value_type in {'damage', 'health', 'multiplier'}:
            return 'multiplier'

    if source_class in {'perk', 'perks', 'perk_effect'} and surface_value_type in {'damage', 'hp', 'hp_per_second', 'attacks_per_second', 'multiplier'}:
        return 'multiplier'

    if contributor_id.startswith('enhancement.free_upgrades_+'):
        return 'multiplier'

    if '__multiplier' in contributor_id or 'multiplier' in contributor_id:
        return 'multiplier'
    if '__pct' in contributor_id or 'chance' in contributor_id or 'percent' in contributor_id:
        return 'pct'
    return 'scalar'


def _format_compact_number(value: float | int | None) -> str:
    if value is None:
        return '0'
    v = float(value)
    sign = '-' if v < 0 else ''
    av = abs(v)
    for threshold, suffix in _DISPLAY_SUFFIXES:
        if av >= threshold:
            scaled = av / threshold
            decimals = 2 if scaled < 10 else (1 if scaled < 100 else 0)
            token = f'{scaled:.{decimals}f}'.rstrip('0').rstrip('.')
            return f'{sign}{token}{suffix}'
    if av >= 100:
        return f'{sign}{av:.0f}'
    if av >= 10:
        return f'{sign}{av:.1f}'.rstrip('0').rstrip('.')
    return f'{sign}{av:.2f}'.rstrip('0').rstrip('.')


def _is_percent_surface(*, surface_id: str, value_type: str | None) -> bool:
    value_type_text = str(value_type or '').strip().lower()
    return value_type_text in {'pct', 'percent_display'} or surface_id.endswith('_pct') or 'chance' in surface_id


def _is_multiplier_surface(*, surface_id: str, value_type: str | None) -> bool:
    value_type_text = str(value_type or '').strip().lower()
    return value_type_text in {'multiplier', 'multiplier_display'} or surface_id.endswith('_multiplier')


def _surface_display_kind(*, surface_id: str, value_type: str | None) -> str:
    if _is_multiplier_surface(surface_id=surface_id, value_type=value_type):
        return 'multiplier'
    if _is_percent_surface(surface_id=surface_id, value_type=value_type):
        return 'pct'
    return 'scalar'


def _format_effect_value(
    value: float | None,
    *,
    display_kind: str,
    default_prefix: str = '+',
) -> str:
    if value is None:
        return '—'
    prefix = 'x' if display_kind == 'multiplier' else default_prefix
    number = _format_compact_number(value)
    suffix = '%' if display_kind == 'pct' else ''
    return f'{prefix} {number}{suffix}'


def _format_effect_from_contributors(
    row: dict[str, object],
    *,
    source_classes: tuple[str, ...],
    surface_value_type: str,
    contributor_prefixes: tuple[str, ...] = (),
    invert_prefix_match: bool = False,
) -> str:
    values: list[float] = []
    display_kinds: list[str] = []
    for contributor in (row.get('contributors') or []):
        if str((contributor or {}).get('source_class') or '') not in source_classes:
            continue
        contributor_id = str((contributor or {}).get('contributor_id') or '')
        prefix_match = any(contributor_id.startswith(prefix) for prefix in contributor_prefixes)
        if contributor_prefixes and ((prefix_match and invert_prefix_match) or (not prefix_match and not invert_prefix_match)):
            continue
        value = (contributor or {}).get('value')
        if not isinstance(value, (int, float)):
            continue
        values.append(float(value))
        display_kinds.append(
            _contributor_display_kind(dict(contributor or {}), surface_value_type=surface_value_type)
        )
    if not values:
        return '—'

    multiplier_surface_types = {'damage', 'hp', 'hp_per_second', 'attacks_per_second', 'multiplier'}
    if source_classes == ('relics',) and surface_value_type in multiplier_surface_types:
        relic_total = sum(values)
        if relic_total >= 0:
            return _format_effect_value(1.0 + relic_total, display_kind='multiplier')

    display_kind = 'scalar'
    if any(kind == 'multiplier' for kind in display_kinds):
        display_kind = 'multiplier'
    elif any(kind == 'pct' for kind in display_kinds):
        display_kind = 'pct'
    if display_kind == 'multiplier':
        product = 1.0
        for value in values:
            product *= float(value)
        return _format_effect_value(product, display_kind=display_kind)
    return _format_effect_value(sum(values), display_kind=display_kind)


def _lab_effects_delta_display(
    *,
    start_row: dict[str, object],
    max_row: dict[str, object],
    surface_value_type: str,
) -> str:
    def _lab_values_and_kinds(row: dict[str, object]) -> tuple[list[float], list[str]]:
        values: list[float] = []
        kinds: list[str] = []
        for contributor in (row.get('contributors') or []):
            if str((contributor or {}).get('source_class') or '') != 'labs':
                continue
            value = (contributor or {}).get('value')
            if not isinstance(value, (int, float)):
                continue
            values.append(float(value))
            kinds.append(_contributor_display_kind(dict(contributor or {}), surface_value_type=surface_value_type))
        return values, kinds

    start_values, start_kinds = _lab_values_and_kinds(start_row)
    max_values, max_kinds = _lab_values_and_kinds(max_row)
    if not start_values and not max_values:
        return '—'
    if not max_values:
        return _format_effect_from_contributors(start_row, source_classes=('labs',), surface_value_type=surface_value_type)

    multiplier_surface_types = {'damage', 'hp', 'hp_per_second', 'attacks_per_second', 'multiplier'}
    is_multiplier = any(kind == 'multiplier' for kind in (start_kinds + max_kinds)) or surface_value_type in multiplier_surface_types
    if is_multiplier:
        start_product = 1.0
        for value in start_values:
            start_product *= value if value >= 1.0 else (1.0 + value)
        max_product = 1.0
        for value in max_values:
            max_product *= value if value >= 1.0 else (1.0 + value)
        if start_product == 0:
            return _format_effect_value(max_product, display_kind='multiplier')
        ratio = max_product / start_product
        if abs(ratio - 1.0) > 1e-9:
            return _format_effect_value(ratio, display_kind='multiplier')
    else:
        delta = sum(max_values) - sum(start_values)
        if abs(delta) > 1e-9:
            display_kind = 'pct' if any(kind == 'pct' for kind in max_kinds) else 'scalar'
            return _format_effect_value(delta, display_kind=display_kind)

    return _format_effect_from_contributors(start_row, source_classes=('labs',), surface_value_type=surface_value_type)


def _has_death_wave_health_contributor(*rows: dict[str, object]) -> bool:
    for row in rows:
        for contributor in (row.get('contributors') or []):
            if str((contributor or {}).get('source_class') or '') != 'labs':
                continue
            contributor_id = str((contributor or {}).get('contributor_id') or '').lower()
            if 'death_wave_health' in contributor_id:
                return True
    return False


def _row_display_value(
    row: dict[str, object],
    *,
    surface_id: str,
    value_type: str | None,
) -> str | None:
    display = row.get('display_value')
    if isinstance(display, str) and display.strip():
        return display
    final_value = row.get('final_value')
    if isinstance(final_value, (int, float)):
        return _format_surface_value(final_value, surface_id=surface_id, value_type=value_type)
    return None


def _format_surface_value(value: float | int | None, *, surface_id: str, value_type: str | None) -> str:
    if value is None:
        return '—'
    number = _format_compact_number(value)
    if _is_multiplier_surface(surface_id=surface_id, value_type=value_type):
        return f'x{number}'
    if _is_percent_surface(surface_id=surface_id, value_type=value_type):
        return f'{number}%'
    return number


def _workshop_level_for_label(*, account_state_payload: dict[str, object], label: str, selected_preset: str) -> int | None:
    workshop_entries = dict(account_state_payload.get('workshop') or {})
    workshop_name = _WORKSHOP_LABEL_ALIASES.get(label, label)
    entry = dict(workshop_entries.get(workshop_name) or {})
    preset_levels = dict(entry.get('preset_levels') or {})
    level = preset_levels.get(selected_preset)
    return int(level) if isinstance(level, int) else None


def build_workshop_reconciliation_row(
    *,
    spec: dict[str, str],
    start_row: dict[str, object],
    max_row: dict[str, object],
    account_state_payload: dict[str, object],
    selected_preset: str,
) -> dict[str, object]:
    surface_id = spec['surface_id']
    canonical_row_id = str(spec.get('canonical_row_id') or surface_id)
    value_type = str(start_row.get('value_type') or max_row.get('value_type') or '')
    workshop_value = _sum_contributor_values_filtered(
        start_row,
        source_classes=('workshop',),
        contributor_prefixes=('enhancement.',),
        invert_prefix_match=True,
    )
    max_workshop_contribution = _sum_contributor_values_filtered(
        max_row,
        source_classes=('workshop',),
        contributor_prefixes=('enhancement.',),
        invert_prefix_match=True,
    )
    start_display_value = _row_display_value(start_row, surface_id=surface_id, value_type=value_type)
    max_display_value = _row_display_value(max_row, surface_id=surface_id, value_type=value_type)
    start_of_run_value = (
        start_display_value
        if isinstance(start_display_value, str)
        else _format_surface_value(None, surface_id=surface_id, value_type=value_type)
    )
    max_workshop_value = (
        max_display_value
        if isinstance(max_display_value, str)
        else _format_surface_value(None, surface_id=surface_id, value_type=value_type)
    )
    decomposition = {
        'workshop': _format_surface_value(workshop_value, surface_id=surface_id, value_type=value_type),
        'lab': _lab_effects_delta_display(
            start_row=start_row,
            max_row=max_row,
            surface_value_type=value_type,
        ),
        'module': _format_effect_from_contributors(
            start_row,
            source_classes=('module_main', 'module_substat', 'module_unique'),
            surface_value_type=value_type,
        ),
        'card': _format_effect_from_contributors(start_row, source_classes=('cards',), surface_value_type=value_type),
        'enhancement': _format_effect_from_contributors(
            start_row,
            source_classes=('workshop', 'enhancement'),
            contributor_prefixes=('enhancement.',),
            surface_value_type=value_type,
        ),
        'relic': _format_effect_from_contributors(start_row, source_classes=('relics',), surface_value_type=value_type),
        'perk': _format_effect_from_contributors(
            max_row,
            source_classes=('perk', 'perks', 'perk_effect'),
            surface_value_type=value_type,
        ),
        'other': _format_effect_from_contributors(
            start_row,
            source_classes=('base', 'scenario_rules'),
            surface_value_type=value_type,
        ),
    }
    row_status = str(start_row.get('status') or max_row.get('status') or 'missing')
    row_notes = str(start_row.get('notes') or max_row.get('notes') or '')
    if _has_death_wave_health_contributor(start_row, max_row):
        row_notes = '; '.join(part for part in [row_notes, 'Includes Death Wave Health lab contribution.'] if part)
    if row_status == 'missing' and not row_notes:
        row_notes = 'Missing QE query row.'
    return {
        'canonical_row_id': canonical_row_id,
        'display_label': spec['label'],
        'value_format': {
            'value_type': value_type or 'scalar',
            'display_kind': _surface_display_kind(surface_id=surface_id, value_type=value_type),
        },
        'start_of_run': start_of_run_value,
        'max_workshop': max_workshop_value,
        'decomposition': decomposition,
        'row_status': row_status,
        'row_notes': row_notes,
        'name': spec['label'],
        'workshop_level': _workshop_level_for_label(
            account_state_payload=account_state_payload,
            label=spec['label'],
            selected_preset=selected_preset,
        ),
        'workshop_value': decomposition['workshop'],
        'lab_effects': decomposition['lab'],
        'module_effects': decomposition['module'],
        'card_effects': decomposition['card'],
        'enhancement_effects': decomposition['enhancement'],
        'relics': decomposition['relic'],
        'start_of_run_value': start_of_run_value,
        'max_workshop_value': _format_surface_value(max_workshop_contribution, surface_id=surface_id, value_type=value_type),
        'perk_effects': decomposition['perk'],
        'other': decomposition['other'],
        'max_progression_value': max_workshop_value,
    }
