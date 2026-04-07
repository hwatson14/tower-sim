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

_WORKSHOP_MULTIPLICATIVE_SURFACE_OVERRIDES: frozenset[str] = frozenset({
    'state::economy.cash_per_wave',
    'state::economy.coins_per_wave',
    'state::tower.knockback_force',
    'state::tower.orb_speed_rpm',
})

_WORKSHOP_FRACTIONAL_MODULE_PCT_SURFACES: frozenset[str] = frozenset({
    'state::tower.thorns_damage_pct',
})


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
        return f'{sign}{av:.2f}'.rstrip('0').rstrip('.')
    if av >= 10:
        return f'{sign}{av:.2f}'.rstrip('0').rstrip('.')
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


def _modifier_total_display_kind(*, surface_id: str, value_type: str | None) -> str:
    value_type_text = str(value_type or '').strip().lower()
    if value_type_text in {'damage', 'hp', 'health', 'hp_per_second', 'attacks_per_second', 'multiplier'}:
        return 'multiplier'
    return _surface_display_kind(surface_id=surface_id, value_type=value_type)


def _neutral_effect_value(*, display_kind: str) -> str:
    if display_kind == 'multiplier':
        return 'x 1'
    if display_kind == 'pct':
        return '+ 0%'
    return '+ 0'


def _is_neutral_effect_display(value: str, *, display_kind: str) -> bool:
    return value == _neutral_effect_value(display_kind=display_kind)


def _row_family(
    *,
    surface_id: str,
    value_type: str | None,
    start_row: dict[str, object],
    max_row: dict[str, object],
) -> str:
    value_type_text = str(value_type or '').strip().lower()
    if surface_id in _WORKSHOP_MULTIPLICATIVE_SURFACE_OVERRIDES:
        return 'multiplicative'
    if value_type_text in {'damage', 'hp', 'health', 'hp_per_second', 'attacks_per_second', 'multiplier'}:
        return 'multiplicative'
    if _surface_display_kind(surface_id=surface_id, value_type=value_type) != 'pct':
        return 'additive_scalar'

    for row in (start_row, max_row):
        for contributor in (row.get('contributors') or []):
            contributor_dict = dict(contributor or {})
            source_class = str(contributor_dict.get('source_class') or '')
            if source_class not in {'labs', 'module_main', 'module_substat', 'module_unique', 'cards', 'relics', 'enhancement', 'workshop', 'perk', 'perks', 'perk_effect'}:
                continue
            contributor_id = str(contributor_dict.get('contributor_id') or '')
            if source_class == 'workshop' and not contributor_id.startswith('enhancement.'):
                continue
            if _contributor_display_kind(contributor_dict, surface_value_type=value_type_text) == 'multiplier':
                return 'additive_then_multiplicative'
    return 'additive_pct'


def _explicit_display_kind(contributor: dict[str, object]) -> str:
    value = str((contributor.get('input_value_type') or contributor.get('value_type') or '')).strip().lower()
    return value if value in {'pct', 'percent_display', 'multiplier', 'multiplier_display'} else ''


def _multiplicative_factor_for_contributor(
    contributor: dict[str, object],
    *,
    value: float,
    kind: str,
    surface_value_type: str,
) -> float:
    source_class = str(contributor.get('source_class') or '').lower()
    explicit_kind = _explicit_display_kind(contributor)

    if source_class == 'relics':
        return value if value >= 1.0 else (1.0 + value)

    if source_class == 'module_substat' and explicit_kind == 'multiplier_display':
        return 1.0 + value

    if explicit_kind == 'percent_display':
        return 1.0 + (value / 100.0)

    if source_class.startswith('module') and 0.0 < value < 1.0:
        return 1.0 + value

    if kind == 'multiplier':
        return value

    if kind == 'pct':
        if surface_value_type == 'multiplier' and not explicit_kind:
            return value if value >= 1.0 else (1.0 + value)
        return 1.0 + (value / 100.0)

    return value


def _additive_component_value_for_contributor(
    contributor: dict[str, object],
    *,
    value: float,
    kind: str,
    family: str,
    surface_id: str,
) -> float:
    source_class = str(contributor.get('source_class') or '').lower()
    if family in {'additive_pct', 'additive_then_multiplicative'} and source_class == 'relics' and kind != 'multiplier' and 0.0 <= value <= 1.0:
        return value * 100.0
    if (
        family in {'additive_pct', 'additive_then_multiplicative'}
        and surface_id in _WORKSHOP_FRACTIONAL_MODULE_PCT_SURFACES
        and source_class == 'module_substat'
        and kind != 'multiplier'
        and 0.0 <= value <= 1.0
    ):
        return value * 100.0
    return value


def _component_effect(
    row: dict[str, object],
    *,
    include_contributor,
    family: str,
    surface_value_type: str,
) -> tuple[float, float, bool]:
    additive_total = 0.0
    factor_total = 1.0
    has_value = False
    for contributor in (row.get('contributors') or []):
        contributor_dict = dict(contributor or {})
        if not include_contributor(contributor_dict):
            continue
        raw_value = contributor_dict.get('value')
        if not isinstance(raw_value, (int, float)):
            continue
        value = float(raw_value)
        kind = _contributor_display_kind(contributor_dict, surface_value_type=surface_value_type)
        source_class = str(contributor_dict.get('source_class') or '').lower()
        has_value = True

        if family == 'multiplicative':
            if abs(value) < 1e-12:
                continue
            factor_total *= _multiplicative_factor_for_contributor(
                contributor_dict,
                value=value,
                kind=kind,
                surface_value_type=surface_value_type,
            )
            continue

        if family == 'additive_then_multiplicative':
            if source_class == 'enhancement' or kind == 'multiplier':
                factor_total *= value
            else:
                additive_total += _additive_component_value_for_contributor(
                    contributor_dict,
                    value=value,
                    kind=kind,
                    family=family,
                    surface_id=str(row.get('stat_name') or ''),
                )
            continue

        additive_total += _additive_component_value_for_contributor(
            contributor_dict,
            value=value,
            kind=kind,
            family=family,
            surface_id=str(row.get('stat_name') or ''),
        )

    return additive_total, factor_total, has_value


def _combine_component_effects(
    effects: list[tuple[float, float, bool]],
    *,
    family: str,
) -> tuple[float, float, bool]:
    additive_total = 0.0
    factor_total = 1.0
    has_value = False
    for additive_value, factor_value, effect_has_value in effects:
        additive_total += additive_value
        factor_total *= factor_value
        has_value = has_value or effect_has_value
    return additive_total, factor_total, has_value


def _diff_component_effects(
    *,
    start_effect: tuple[float, float, bool],
    max_effect: tuple[float, float, bool],
    family: str,
) -> tuple[float, float, bool]:
    start_additive, start_factor, start_has = start_effect
    max_additive, max_factor, max_has = max_effect
    if family == 'multiplicative':
        baseline = start_factor if start_has and start_factor != 0 else 1.0
        return 0.0, (max_factor / baseline), (start_has or max_has)
    if family == 'additive_then_multiplicative':
        baseline = start_factor if start_has and start_factor != 0 else 1.0
        return max_additive - start_additive, (max_factor / baseline), (start_has or max_has)
    return max_additive - start_additive, 1.0, (start_has or max_has)


def _format_component_effect_display(
    effect: tuple[float, float, bool],
    *,
    family: str,
) -> str:
    additive_total, factor_total, has_value = effect
    if not has_value:
        return '—'
    if family == 'multiplicative':
        if abs(factor_total - 1.0) < 1e-9:
            return '—'
        return _format_effect_value(factor_total, display_kind='multiplier')
    if family == 'additive_pct':
        return '—' if abs(additive_total) < 1e-9 else _format_effect_value(additive_total, display_kind='pct')
    if family == 'additive_scalar':
        return '—' if abs(additive_total) < 1e-9 else _format_effect_value(additive_total, display_kind='scalar')
    additive_part = None if abs(additive_total) < 1e-9 else _format_effect_value(additive_total, display_kind='pct')
    factor_part = None if abs(factor_total - 1.0) < 1e-9 else _format_effect_value(factor_total, display_kind='multiplier')
    if additive_part and factor_part:
        return f'{additive_part} · {factor_part}'
    if additive_part:
        return additive_part
    if factor_part:
        return factor_part
    return '—'


def _format_effective_total_display(
    *,
    effect: tuple[float, float, bool],
    family: str,
    workshop_value: float | None,
    surface_id: str,
    surface_value_type: str,
) -> str:
    additive_total, factor_total, has_value = effect
    if not has_value:
        return '—'
    if family != 'additive_then_multiplicative':
        return _format_component_effect_display(effect, family=family)
    if workshop_value is None:
        return _format_component_effect_display(effect, family=family)

    final_value = (workshop_value + additive_total) * factor_total
    if _is_multiplier_surface(surface_id=surface_id, value_type=surface_value_type):
        if workshop_value == 0:
            return _format_component_effect_display(effect, family=family)
        return _format_effect_value(final_value / workshop_value, display_kind='multiplier')
    if _is_percent_surface(surface_id=surface_id, value_type=surface_value_type):
        return _format_effect_value(final_value - workshop_value, display_kind='pct')
    return _format_effect_value(final_value - workshop_value, display_kind='scalar')


def _apply_effect_to_workshop_value(
    *,
    effect: tuple[float, float, bool],
    family: str,
    workshop_value: float | None,
) -> float | None:
    if workshop_value is None:
        return None
    additive_total, factor_total, has_value = effect
    if not has_value:
        return workshop_value
    if family == 'multiplicative':
        return workshop_value * factor_total
    if family in {'additive_pct', 'additive_scalar'}:
        return workshop_value + additive_total
    return (workshop_value + additive_total) * factor_total


def _aggregate_effect_total(
    row: dict[str, object],
    *,
    include_contributor,
    surface_id: str,
    surface_value_type: str,
) -> tuple[str, float, bool]:
    display_kind = _modifier_total_display_kind(surface_id=surface_id, value_type=surface_value_type)
    scalar_total = 0.0
    multiplier_total = 1.0
    has_value = False
    for contributor in (row.get('contributors') or []):
        contributor_dict = dict(contributor or {})
        if not include_contributor(contributor_dict):
            continue
        value = contributor_dict.get('value')
        if not isinstance(value, (int, float)):
            continue
        contributor_value = float(value)
        contributor_kind = _contributor_display_kind(contributor_dict, surface_value_type=surface_value_type)
        source_class = str(contributor_dict.get('source_class') or '').lower()
        has_value = True

        if display_kind == 'multiplier':
            if contributor_value == 0:
                continue
            if source_class == 'relics':
                multiplier_total *= 1.0 + contributor_value
            elif contributor_kind == 'pct':
                multiplier_total *= 1.0 + (contributor_value / 100.0)
            else:
                multiplier_total *= contributor_value
            continue

        scalar_total += contributor_value

    return display_kind, (multiplier_total if display_kind == 'multiplier' else scalar_total), has_value


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
        relic_pct_values: list[float] = []
        relic_non_pct_values: list[float] = []
        for contributor in (row.get('contributors') or []):
            if str((contributor or {}).get('source_class') or '') != 'relics':
                continue
            contributor_value = (contributor or {}).get('value')
            if not isinstance(contributor_value, (int, float)):
                continue
            contributor_id = str((contributor or {}).get('contributor_id') or '').lower()
            if '__pct' in contributor_id or 'percent' in contributor_id:
                relic_pct_values.append(float(contributor_value))
            else:
                relic_non_pct_values.append(float(contributor_value))
        if relic_pct_values and not relic_non_pct_values:
            relic_total = sum(relic_pct_values)
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


def _format_total_effect_from_row(
    row: dict[str, object],
    *,
    include_contributor,
    surface_id: str,
    surface_value_type: str,
) -> str:
    display_kind, total_value, has_value = _aggregate_effect_total(
        row,
        include_contributor=include_contributor,
        surface_id=surface_id,
        surface_value_type=surface_value_type,
    )
    if not has_value:
        return _neutral_effect_value(display_kind=display_kind)
    return _format_effect_value(total_value, display_kind=display_kind)


def _format_effect_delta_between_rows(
    *,
    start_row: dict[str, object],
    max_row: dict[str, object],
    include_contributor,
    surface_id: str,
    surface_value_type: str,
) -> str:
    display_kind, start_total, start_has_value = _aggregate_effect_total(
        start_row,
        include_contributor=include_contributor,
        surface_id=surface_id,
        surface_value_type=surface_value_type,
    )
    _display_kind_max, max_total, max_has_value = _aggregate_effect_total(
        max_row,
        include_contributor=include_contributor,
        surface_id=surface_id,
        surface_value_type=surface_value_type,
    )
    if display_kind == 'multiplier':
        if not start_has_value and not max_has_value:
            return _neutral_effect_value(display_kind=display_kind)
        baseline = start_total if start_has_value and start_total != 0 else 1.0
        return _format_effect_value(max_total / baseline, display_kind=display_kind)
    if not start_has_value and not max_has_value:
        return _neutral_effect_value(display_kind=display_kind)
    return _format_effect_value(max_total - start_total, display_kind=display_kind)


def _combine_effect_values(
    *,
    left_row: dict[str, object],
    right_row: dict[str, object],
    left_include_contributor,
    right_include_contributor,
    surface_id: str,
    surface_value_type: str,
) -> str:
    display_kind, left_total, left_has_value = _aggregate_effect_total(
        left_row,
        include_contributor=left_include_contributor,
        surface_id=surface_id,
        surface_value_type=surface_value_type,
    )
    _display_kind_right, right_total, right_has_value = _aggregate_effect_total(
        right_row,
        include_contributor=right_include_contributor,
        surface_id=surface_id,
        surface_value_type=surface_value_type,
    )
    if not left_has_value and not right_has_value:
        return _neutral_effect_value(display_kind=display_kind)
    if display_kind == 'multiplier':
        return _format_effect_value(left_total * right_total, display_kind=display_kind)
    return _format_effect_value(left_total + right_total, display_kind=display_kind)


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
    final_value = row.get('final_value')
    if isinstance(final_value, (int, float)):
        return _format_surface_value(final_value, surface_id=surface_id, value_type=value_type)
    display = row.get('display_value')
    if isinstance(display, str) and display.strip():
        return display
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


def _workshop_entry_for_label(*, account_state_payload: dict[str, object], label: str) -> dict[str, object]:
    workshop_entries = dict(account_state_payload.get('workshop') or {})
    workshop_name = _WORKSHOP_LABEL_ALIASES.get(label, label)
    return dict(workshop_entries.get(workshop_name) or {})


def _format_percent_value(value: float | int | None) -> str:
    if value is None:
        return '—'
    return f'{_format_compact_number(value)}%'


def _build_wall_health_workshop_percent_row(
    *,
    spec: dict[str, str],
    account_state_payload: dict[str, object],
    selected_preset: str,
) -> dict[str, object]:
    entry = _workshop_entry_for_label(account_state_payload=account_state_payload, label=spec['label'])
    preset_values = dict(entry.get('preset_values') or {})
    current_value = preset_values.get(selected_preset)
    max_value = entry.get('max_level')
    value_text = _format_percent_value(current_value if isinstance(current_value, (int, float)) else None)
    max_text = _format_percent_value(max_value if isinstance(max_value, (int, float)) else None)
    row_note = 'Workshop wall-health percentage. Actual Wall HP is shown in the Derived section.'
    return {
        'canonical_row_id': str(spec.get('canonical_row_id') or spec['surface_id']),
        'display_label': spec['label'],
        'value_format': {
            'value_type': 'pct',
            'display_kind': 'pct',
        },
        'start_of_run': value_text,
        'max_workshop': max_text,
        'decomposition': {
            'workshop': value_text,
            'lab': '—',
            'base_subtotal': '—',
            'module': '—',
            'card': '—',
            'enhancement': '—',
            'relic': '—',
            'base_loadout_subtotal': '—',
            'perk': '—',
            'other': '—',
        },
        'row_status': 'resolved',
        'row_notes': row_note,
        'name': spec['label'],
        'workshop_level': _workshop_level_for_label(
            account_state_payload=account_state_payload,
            label=spec['label'],
            selected_preset=selected_preset,
        ),
        'workshop_value': value_text,
        'lab_effects': '—',
        'base_subtotal': '—',
        'module_effects': '—',
        'card_effects': '—',
        'relics': '—',
        'base_loadout_subtotal': '—',
        'enhancement_effects': '—',
        'start_of_run_modifier_total': '—',
        'start_of_run_value': value_text,
        'max_workshop_value': max_text,
        'max_workshop_resolved_value': max_text,
        'perk_effects': '—',
        'other': '—',
        'max_progression_modifier_total': '—',
        'max_progression_value': max_text,
    }


def build_workshop_reconciliation_row(
    *,
    spec: dict[str, str],
    start_row: dict[str, object],
    max_row: dict[str, object],
    account_state_payload: dict[str, object],
    selected_preset: str,
) -> dict[str, object]:
    canonical_row_id = str(spec.get('canonical_row_id') or spec['surface_id'])
    if canonical_row_id == 'workshop::wall.health':
        return _build_wall_health_workshop_percent_row(
            spec=spec,
            account_state_payload=account_state_payload,
            selected_preset=selected_preset,
        )

    surface_id = spec['surface_id']
    value_type = str(start_row.get('value_type') or max_row.get('value_type') or '')
    family = _row_family(
        surface_id=surface_id,
        value_type=value_type,
        start_row=start_row,
        max_row=max_row,
    )

    lab_include = lambda contributor: str(contributor.get('source_class') or '') == 'labs'
    module_include = lambda contributor: str(contributor.get('source_class') or '') in {'module_main', 'module_substat', 'module_unique'}
    card_include = lambda contributor: str(contributor.get('source_class') or '') == 'cards'
    enhancement_include = lambda contributor: (
        str(contributor.get('source_class') or '') == 'enhancement'
        or (
            str(contributor.get('source_class') or '') == 'workshop'
            and str(contributor.get('contributor_id') or '').startswith('enhancement.')
        )
    )
    relic_include = lambda contributor: str(contributor.get('source_class') or '') == 'relics'
    perk_include = lambda contributor: str(contributor.get('source_class') or '') in {'perk', 'perks', 'perk_effect'}
    start_modifier_include = lambda contributor: (
        lab_include(contributor)
        or module_include(contributor)
        or card_include(contributor)
        or enhancement_include(contributor)
        or relic_include(contributor)
    )

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
    max_progression_value = (
        max_display_value
        if isinstance(max_display_value, str)
        else _format_surface_value(None, surface_id=surface_id, value_type=value_type)
    )

    start_component_effects = {
        'lab': _component_effect(start_row, include_contributor=lab_include, family=family, surface_value_type=value_type),
        'relic': _component_effect(start_row, include_contributor=relic_include, family=family, surface_value_type=value_type),
        'module': _component_effect(start_row, include_contributor=module_include, family=family, surface_value_type=value_type),
        'card': _component_effect(start_row, include_contributor=card_include, family=family, surface_value_type=value_type),
        'enhancement': _component_effect(start_row, include_contributor=enhancement_include, family=family, surface_value_type=value_type),
    }
    base_subtotal_effect = _combine_component_effects(
        [start_component_effects['lab'], start_component_effects['relic']],
        family=family,
    )
    base_loadout_subtotal_effect = _combine_component_effects(
        [base_subtotal_effect, start_component_effects['module'], start_component_effects['card']],
        family=family,
    )
    # The start total must be composed from the exact visible modifier columns.
    start_total_effect = _combine_component_effects(
        [base_loadout_subtotal_effect, start_component_effects['enhancement']],
        family=family,
    )
    max_nonperk_total_effect = _component_effect(
        max_row,
        include_contributor=start_modifier_include,
        family=family,
        surface_value_type=value_type,
    )
    other_effect = _diff_component_effects(
        start_effect=start_total_effect,
        max_effect=max_nonperk_total_effect,
        family=family,
    )
    perk_effect = _component_effect(max_row, include_contributor=perk_include, family=family, surface_value_type=value_type)
    max_component_effects = {
        'perk': perk_effect,
        'other': other_effect,
    }
    # The max total must likewise be composed from the exact visible modifier columns.
    max_total_effect = _combine_component_effects(list(max_component_effects.values()), family=family)

    decomposition = {
        'workshop': _format_surface_value(workshop_value, surface_id=surface_id, value_type=value_type),
        'lab': _format_component_effect_display(start_component_effects['lab'], family=family),
        'relic': _format_component_effect_display(start_component_effects['relic'], family=family),
        'base_subtotal': _format_component_effect_display(base_subtotal_effect, family=family),
        'module': _format_component_effect_display(start_component_effects['module'], family=family),
        'card': _format_component_effect_display(start_component_effects['card'], family=family),
        'base_loadout_subtotal': _format_component_effect_display(base_loadout_subtotal_effect, family=family),
        'enhancement': _format_component_effect_display(start_component_effects['enhancement'], family=family),
        'perk': _format_component_effect_display(max_component_effects['perk'], family=family),
        'other': _format_component_effect_display(max_component_effects['other'], family=family),
    }
    start_of_run_modifier_total = _format_effective_total_display(
        effect=start_total_effect,
        family=family,
        workshop_value=workshop_value,
        surface_id=surface_id,
        surface_value_type=value_type,
    )
    max_workshop_resolved_value = _format_surface_value(
        _apply_effect_to_workshop_value(
            effect=start_total_effect,
            family=family,
            workshop_value=max_workshop_contribution,
        ),
        surface_id=surface_id,
        value_type=value_type,
    )
    max_progression_modifier_total = _format_component_effect_display(max_total_effect, family=family)

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
        'max_workshop': max_progression_value,
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
        'relics': decomposition['relic'],
        'base_subtotal': decomposition['base_subtotal'],
        'module_effects': decomposition['module'],
        'card_effects': decomposition['card'],
        'base_loadout_subtotal': decomposition['base_loadout_subtotal'],
        'enhancement_effects': decomposition['enhancement'],
        'start_of_run_modifier_total': start_of_run_modifier_total,
        'start_of_run_value': start_of_run_value,
        'max_workshop_value': _format_surface_value(max_workshop_contribution, surface_id=surface_id, value_type=value_type),
        'max_workshop_resolved_value': max_workshop_resolved_value,
        'perk_effects': decomposition['perk'],
        'other': decomposition['other'],
        'max_progression_modifier_total': max_progression_modifier_total,
        'max_progression_value': max_progression_value,
    }
