from __future__ import annotations

from typing import Dict, Optional

from models.account_state import AccountState

TRADE_OFF_BENEFIT_EFFECT_INDEXES = {
    'PERK_X1_50_TOWER_DAMAGE_BUT_BOSSES_HAVE_8X_HEALTH': {'1'},
    'PERK_X1_80_COINS_BUT_TOWER_MAX_HEALTH_70': {'1'},
    'PERK_ENEMIES_HAVE_50_HEALTH_BUT_TOWER_HEALTH_REGEN_AND_LIFESTEAL_90': {'1'},
    'PERK_ENEMIES_DAMAGE_50_BUT_TOWER_DAMAGE_50': {'1'},
    'PERK_RANGED_ENEMIES_ATTACK_DISTANCE_REDUCED_BUT_TOWER_RANGED_ENEMIES_DAMAGE_X3': {'1'},
    'PERK_ENEMIES_SPEED_40_BUT_ENEMIES_DAMAGE_X2_5': {'1'},
    'PERK_X12_00_CASH_PER_WAVE_BUT_ENEMY_KILL_DON_T_GIVE_CASH': {'1'},
    'PERK_TOWER_HEALTH_REGEN_X8_00_BUT_TOWER_MAX_MAX_HEALTH_60': {'1'},
    'PERK_BOSS_HEALTH_70_BUT_BOSS_SPEED_50': {'1'},
    'PERK_LIFESTEAL_X2_50_BUT_KNOCKBACK_FORCE_70': {'1'},
}

TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES = {
    perk_id: indexes.copy()
    for perk_id, indexes in TRADE_OFF_BENEFIT_EFFECT_INDEXES.items()
}
TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES['PERK_RANGED_ENEMIES_ATTACK_DISTANCE_REDUCED_BUT_TOWER_RANGED_ENEMIES_DAMAGE_X3'] = set()


def active_perk_selections(account_state: AccountState, preset: str | None) -> list[tuple[str, int]]:
    resolved_preset = preset or account_state.active_perk_preset
    if not resolved_preset:
        return []
    out: list[tuple[str, int]] = []
    for selection in account_state.perk_presets.get(resolved_preset, []):
        if selection.perk_id and selection.picks > 0:
            out.append((selection.perk_id, selection.picks))
    return out


def perk_lab_state(account_state: AccountState) -> Dict[str, float]:
    standard_bonus_level = int(account_state.labs.get('Standard Perks Bonus') or 0)
    tradeoff_bonus_level = int(account_state.labs.get('Improve Trade-off Perks') or 0)
    return {
        'standard_bonus_multiplier': 1.0 + (standard_bonus_level / 100.0),
        'tradeoff_bonus_multiplier': 1.0 + (tradeoff_bonus_level / 100.0),
    }


def scaled_perk_value(*, perk_meta: Dict[str, object], perk_id: str, operation: str, raw_value: str, picks: int, effect_index: str, perk_lab_state: Dict[str, float], perk_effect_meta: Optional[Dict[str, object]] = None):
    base_value = perk_value_from_effect(operation, raw_value)
    if not isinstance(base_value, (int, float)):
        return base_value
    effect_meta = perk_effect_meta or {}
    category = str(perk_meta.get('category') or '').strip().lower()
    picks = max(1, int(picks))
    spb_applies = str(effect_meta.get('spb_applies') or '').strip().lower()
    spb_formula_class = str(effect_meta.get('spb_formula_class') or '').strip().lower()
    integrality_policy = str(effect_meta.get('integrality_policy') or '').strip().lower()
    if category == 'standard':
        standard_mult = float(perk_lab_state.get('standard_bonus_multiplier', 1.0) or 1.0)
        spb_enabled = spb_applies != 'no'
        if operation == 'multiplier' and float(base_value) > 1.0:
            if spb_formula_class == 'multiplicative' or not spb_formula_class:
                return (1.0 + ((float(base_value) - 1.0) * picks)) * (standard_mult if spb_enabled else 1.0)
            return 1.0 + ((float(base_value) - 1.0) * picks)
        if operation == 'remaining_fraction':
            delta = float(base_value) - 1.0
            return 1.0 + (delta * picks * (standard_mult if spb_enabled else 1.0))
        if operation in {'percentage_points_add', 'count_add', 'seconds_add', 'raw_add'}:
            scaled = float(base_value) * picks * (standard_mult if spb_enabled else 1.0)
            if integrality_policy == 'round_final':
                return float(round(scaled))
            return scaled
    if category == 'trade_off' and effect_index in TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES.get(perk_id, set()):
        improve_mult = float(perk_lab_state.get('tradeoff_bonus_multiplier', 1.0) or 1.0)
        if operation == 'multiplier' and float(base_value) > 1.0:
            return float(base_value) * improve_mult
        if operation == 'remaining_fraction' and 0.0 <= float(base_value) <= 1.0:
            reduction = 1.0 - float(base_value)
            improved = min(0.999999, reduction * improve_mult)
            return 1.0 - improved
        if operation == 'percentage_points_add':
            return float(base_value) * improve_mult
    return base_value


def perk_value_type_for_operation(operation: str) -> str:
    return {
        'multiplier': 'multiplier',
        'remaining_fraction': 'multiplier',
        'percentage_points_add': 'pct',
        'count_add': 'flat',
        'seconds_add': 'flat',
        'raw_add': 'flat',
        'set_to': 'resolved_value',
        'special_unlock': 'bool',
        'special_reduction': 'raw_text',
    }.get(operation, 'resolved_value')


def perk_value_from_effect(operation: str, raw_value: str):
    if operation == 'special_unlock':
        return True
    if operation == 'special_reduction':
        return raw_value
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return raw_value


def normalized_multiplier(value: float) -> float:
    return value if value > 1.0 else 1.0 + value
