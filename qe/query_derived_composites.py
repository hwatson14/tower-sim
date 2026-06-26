
from __future__ import annotations

import math
import re
from typing import Dict, Any, Iterable

from qe.compat.legacy_surface_ids import (
    legacy_canonical_surface_id as _compat_canon,
    legacy_mechanic_surface_id as _compat_mech,
    legacy_runtime_surface_id as _compat_runtime,
    surface_id_candidates,
)
from qe.contracts import normalize_surface_id_to_contract
from qe.models import StatRow
from qe.run_plan import derive_wall_hp_from_qe_primitives, derive_wall_regen_hp_per_second
from qe.stat_input_compiler import intro_sprint_mastery_multiplier_for_level


def _surface_id_candidates(key: str) -> tuple[str, ...]:
    return surface_id_candidates(key)


def _row(rows: Dict[str, StatRow], key: str) -> StatRow | None:
    for candidate in _surface_id_candidates(key):
        row = rows.get(candidate)
        if row is not None:
            return row
    return None


def _get(rows: Dict[str, StatRow], key: str, default: float = 0.0) -> float:
    row = _row(rows, key)
    if row is None or row.final_value is None:
        return default
    try:
        return float(row.final_value)
    except Exception:
        return default


def _get_first(rows: Dict[str, StatRow], keys: Iterable[str], default: float = 0.0) -> float:
    for key in keys:
        row = _row(rows, key)
        if row is None or row.final_value is None:
            continue
        try:
            return float(row.final_value)
        except Exception:
            continue
    return default


def _raw_surface_value(rows: Dict[str, StatRow], keys: Iterable[str]) -> Any:
    for key in keys:
        row = _row(rows, key)
        if row is None:
            continue
        if row.final_value is not None:
            return row.final_value
        for contributor in row.contributors or []:
            if contributor.get('value') is not None:
                return contributor.get('value')
            if contributor.get('input_value') is not None:
                return contributor.get('input_value')
    return None


def _parse_multiplier_token(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r'[-+]?\d+(?:\.\d+)?', str(value))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _bool(rows: Dict[str, StatRow], keys: Iterable[str], default: bool = False) -> bool:
    for key in keys:
        row = _row(rows, key)
        if row is None or row.final_value is None:
            continue
        value = row.final_value
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return float(value) != 0.0
        sval = str(value).strip().lower()
        if sval in {'true', 'yes', 'on', 'active', 'enabled'}:
            return True
        if sval in {'false', 'no', 'off', 'inactive', 'disabled', 'locked'}:
            return False
    return default


def _contributors(rows: Dict[str, StatRow], keys: Iterable[str]) -> list[dict[str, Any]]:
    for key in keys:
        row = _row(rows, key)
        if row is None:
            continue
        contributors = list(row.contributors or [])
        if contributors:
            return contributors
    return []


def _contributor_value_by_token(
    rows: Dict[str, StatRow],
    *,
    row_keys: Iterable[str],
    token: str,
    default: float = 0.0,
) -> float:
    token_normalized = str(token).strip().lower()
    for contributor in _contributors(rows, row_keys):
        contributor_id = str((contributor or {}).get('contributor_id') or '').strip().lower()
        if token_normalized not in contributor_id:
            continue
        value = (contributor or {}).get('value')
        try:
            return float(value)
        except Exception:
            continue
    return default


def _contributor_product_by_token(
    rows: Dict[str, StatRow],
    *,
    row_keys: Iterable[str],
    token: str,
    default: float = 1.0,
) -> float:
    token_normalized = str(token).strip().lower()
    product = 1.0
    found = False
    for contributor in _contributors(rows, row_keys):
        contributor_id = str((contributor or {}).get('contributor_id') or '').strip().lower()
        if token_normalized not in contributor_id:
            continue
        value = (contributor or {}).get('value')
        try:
            product *= float(value)
            found = True
        except Exception:
            continue
    return product if found else default


def _has_dissonance_restriction_override(rows: Dict[str, StatRow], category: str) -> bool:
    prefix = f'dissonance_restriction_override::{category}::'
    for row in rows.values():
        for contributor in row.contributors or []:
            contributor_id = str((contributor or {}).get('contributor_id') or '')
            if contributor_id.startswith(prefix):
                return True
    return False


def _dissonance_restriction_override_categories(rows: Dict[str, StatRow]) -> set[str]:
    prefix = 'dissonance_restriction_override::'
    categories: set[str] = set()
    for row in rows.values():
        for contributor in row.contributors or []:
            contributor_id = str((contributor or {}).get('contributor_id') or '')
            if not contributor_id.startswith(prefix):
                continue
            _, _, rest = contributor_id.partition(prefix)
            category, separator, _ = rest.partition('::')
            if separator and category:
                categories.add(category)
    return categories


def _tp(rows: Dict[str, StatRow], a: str, b: str) -> float:
    return _get(rows, a) + _get(rows, b)


def _uptime(duration: float, cooldown: float) -> float:
    total = duration + cooldown
    return duration / total if total > 0 else 0.0


def _ev(chance_pct: float, multiplier: float) -> float:
    return 1.0 + (chance_pct / 100.0) * max(0.0, multiplier - 1.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _pct(v: float) -> float:
    return v / 100.0


def _pct_surface_ratio(rows: Dict[str, StatRow], keys: Iterable[str], default: float = 0.0) -> float:
    value = _get_first(rows, keys, default)
    return max(0.0, value) / 100.0


def _ep_bullet_per_second(attack_speed: float) -> float:
    return ((0.01413 * attack_speed * attack_speed) + (4.01278 * attack_speed) + 92.8885) * 1.3


def _ep_rapidfire_factor(rfc_pct: float, rfd_seconds: float, bullet_per_second: float) -> float:
    rfc = max(0.0, rfc_pct) / 100.0
    denom = 1.0 + (rfc * rfd_seconds * bullet_per_second)
    if denom <= 0.0:
        return 1.0
    return (1.0 + 4.0 * rfc * rfd_seconds * bullet_per_second) / denom


def _ep_multishot(msc_pct: float, mst: float) -> float:
    return 1.0 + _pct(msc_pct) * max(mst - 1.0, 0.0)


def _ep_bounceshot(bsc_pct: float, bst: float, astral_deliverance: float) -> float:
    chance = _pct(max(0.0, bsc_pct))
    targets = max(int(bst), 0)
    bonus = max(0.0, astral_deliverance)
    total = 1.0
    for n in range(1, targets + 1):
        total += (chance ** n) * ((1.0 + bonus) ** n)
    return total


def _ep_critical(cc_pct: float, cf: float, scc_pct: float, scm: float, being_annihilator: float) -> float:
    cc = _clamp(_pct(max(0.0, cc_pct)), 0.0, 1.0)
    scc = _clamp(_pct(max(0.0, scc_pct)), 0.0, 1.0)
    normal_crit = (1.0 - cc) + (cc * cf * (1.0 - scc) + cc * cf * scc * scm)
    streak = max(0.0, being_annihilator)
    streak_chance = cc * scc
    denom = 1.0 + streak * streak_chance
    pi_zero = 1.0 / denom if denom > 0 else 1.0
    pi_streak = (streak * streak_chance) / denom if denom > 0 else 0.0
    ba_crit_f = cf * scm
    return pi_zero * normal_crit + pi_streak * ba_crit_f


def _ep_uwcritical(cc_pct: float, cf: float, scc_pct: float, scm: float) -> float:
    cc = _pct(max(0.0, cc_pct))
    scc = _pct(max(0.0, scc_pct))
    return (1.0 + cc * cf) * (1.0 + cc * scc * scm)


def _ep_shockwave_damage(acp: float, sw_size_ws: float, sw_size_lab: float, sw_frequency_ws: float, sw_frequency_vault: float, sw_frequency_sub: float) -> float:
    if acp == 0:
        return 1.0
    sw_size_ws_term = 0.6 + 0.05 * sw_size_ws
    sw_size_lab_term = sw_size_lab / 20.0
    sw_size = sw_size_ws_term + sw_size_lab_term
    sw_freq_ws_term = 20.0 - 0.15 * sw_frequency_ws
    sw_freq = max(7.0, sw_freq_ws_term + sw_frequency_vault + sw_frequency_sub) + sw_size / 2.0
    return 1.0 + (acp - 1.0) * (7.0 / sw_freq)


def _ep_rangedpm(range_m: float, dpm: float, kill_at_range: float) -> float:
    dpm_bonus = max(0.0, dpm - 1.0) if dpm >= 1.0 else max(0.0, dpm)
    return 1.0 + range_m * dpm_bonus * kill_at_range


def _ep_sl_coverage(sl_quantity: float, sl_angle: float) -> float:
    return min(1.0, max(0.0, sl_quantity * sl_angle / 360.0))


def _ep_sl_final_bonus(sl_coverage: float, sl_bonus: float) -> float:
    return 1.0 + (sl_bonus - 1.0) * sl_coverage


def _stat_uw_sl_final_lr(sl_light_range: float, dpm_factor: float) -> float:
    return 1.0 + max(0.0, sl_light_range) * max(0.0, dpm_factor - 1.0)


def _stat_uw_sl_final_dmg(base: float, sl_light_range: float, substat: float, relic: float, vault: float, has_perk: bool) -> float:
    return (base + substat) * (1.0 + relic) * (1.0 + vault) * (1.5 if has_perk else 1.0) * sl_light_range


def _ep_super_tower_effective_bonus(has_card: bool, has_mastery: bool, st_bonus: float, st_cooldown: float, has_sl: bool, sl_quantity: float, sl_angle: float) -> float:
    if not has_card:
        return 1.0
    st_slb = 1.0 + (0.35 * (st_bonus - 1.0)) if has_mastery else 1.0
    slc = _ep_sl_coverage(sl_quantity, sl_angle) if has_sl else 0.0
    cooldown = max(st_cooldown, 1e-9)
    return 1.0 + (15.0 * (st_bonus * (1.0 + (st_slb - 1.0) * slc) - 1.0)) / cooldown


def _ep_maxrend(has_rend: bool, lab_level: float, substat: float, wsp_level: float) -> float:
    if not has_rend:
        return 1.0
    lab = lab_level * 0.25
    wsp = 1.0 + (wsp_level * 0.01)
    return (8.0 + substat + lab) * wsp


def _ep_cl_dps(cl_damage: float, cl_quant: float, cl_chance_pct: float, multi_rapid_bounce: float, bullet_per_second: float) -> float:
    return cl_damage * cl_quant * _pct(cl_chance_pct) * multi_rapid_bounce * bullet_per_second


def _ep_dw_dps(has_dw: bool, dw_damage: float, dw_quantity: float, dw_cooldown: float, dw_damage_amp: float) -> float:
    if not has_dw or dw_cooldown <= 0.0:
        return 0.0
    return dw_damage / dw_cooldown * dw_quantity * (5.0 + dw_damage_amp * 1.5)


def _ep_aoe_card_boost(has_aoe_card: bool, aoe_card_level: float) -> float:
    if not has_aoe_card:
        return 1.0
    tiers = [0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.25]
    idx = int(max(1, min(len(tiers), round(aoe_card_level)))) - 1
    return 1.0 + tiers[idx]


def _ep_sm_dps(sm_damage: float, sm_quant: float, sm_cooldown: float, sm_coverfire: float, sm_heat: float, sm_aoe: float, has_aoe_card: bool, aoe_card_level: float) -> float:
    if sm_cooldown <= 0.0:
        return 0.0
    return sm_heat * sm_aoe * (sm_damage * sm_quant / sm_cooldown + sm_coverfire) * _ep_aoe_card_boost(has_aoe_card, aoe_card_level)


def _ep_slm_dps(sm_damage: float, sl_damage: float, sm_cooldown: float, sm_heat: float, sm_aoe: float, has_aoe_card: bool, aoe_card_level: float) -> float:
    if sm_cooldown <= 0.0:
        return 0.0
    return sm_heat * sm_aoe * sm_damage * sl_damage / sm_cooldown * _ep_aoe_card_boost(has_aoe_card, aoe_card_level)


def _ep_ps_dps(has_ps: bool, ps_damage: float, ps_duration: float, ps_cooldown: float, ps_deathcreep: float, ps_rend: float, has_aoe_card: bool, aoe_card_level: float) -> float:
    if not has_ps or ps_cooldown <= 0.0:
        return 0.0
    return ps_damage * (ps_duration / ps_cooldown) * ps_deathcreep * ps_rend * _ep_aoe_card_boost(has_aoe_card, aoe_card_level)


def _ep_ilm_dps(has_ilm: bool, ilm_damage: float, detonation_per_sec: float, chrono_jump: float, ilm_charged_mines: float, ilm_aoe: float, has_aoe_card: bool, aoe_card_level: float) -> float:
    if not has_ilm:
        return 0.0
    return ilm_damage * detonation_per_sec * (1.0 + chrono_jump * ilm_charged_mines) * ilm_aoe * _ep_aoe_card_boost(has_aoe_card, aoe_card_level)


def _ep_uw_total_damage(dw: float, cl: float, sm: float, slm: float, sl: float, ps: float, ilm: float, uw_damage_boost: float, st_uw_mastery: float, uw_crit_card: float) -> float:
    return uw_damage_boost * (((dw + sm + cl + ps + ilm) * sl * st_uw_mastery) + slm) * uw_crit_card * st_uw_mastery


def _ep_module_bonus(primary_bonus: float, has_assist: bool, assist_bonus: float, stone_bac: float, lab_bac: float) -> float:
    return primary_bonus * ((((assist_bonus - 1.0) * (1.0 + stone_bac + lab_bac) * 0.01) + 1.0) if has_assist else 1.0)



def _ep_shock_factor(rows: Dict[str, StatRow]) -> float:
    direct = _get_first(
        rows,
        [
            'support_surface::edamage.shock_factor',
            'support_surface::shock.factor',
            _compat_runtime('shock.factor'),
            _compat_mech('shock.factor'),
        ],
        0.0,
    )
    if direct > 0.0:
        return direct
    cl_active = _bool(
        rows,
        [_compat_runtime('uw.chain_lightning.active'), _compat_mech('uw.chain_lightning.active')],
        default=_get_first(rows, [_compat_mech('uw.chain_lightning.damage_multiplier'), _compat_runtime('uw.chain_lightning.damage_multiplier')], 0.0) > 0.0,
    )
    shock_enabled = _bool(rows, [_compat_runtime('shock.enabled'), _compat_mech('shock.enabled')], default=cl_active)
    if not (cl_active and shock_enabled):
        return 1.0
    shock_level = _get_first(rows, ['support_surface::shock.level', _compat_runtime('shock.level'), _compat_mech('shock.level')], 0.0)
    has_dc = _get_first(rows, [_compat_mech('module.dimension_core.multiplier'), _compat_mech('module.dimension_core.damage_multiplier')], 0.0) > 0.0
    dc_mult = _get_first(rows, [_compat_mech('module.dimension_core.multiplier'), _compat_mech('module.dimension_core.damage_multiplier')], 0.0)
    return 1.0 + (0.1 + 0.04 * shock_level) * (2.0 * dc_mult if has_dc else 1.0)



def _ep_wave_boost_factor(wave_accel_bonus: float, intro_sprint_pct: float, intro_sprint_mastery_bonus: float, wave_skip_chance_pct: float, wave_skip_mastery_bonus: float) -> float:
    wam = 1.0 + max(0.0, wave_accel_bonus)
    intro = 1.0 / max(0.05, 1.0 - max(0.0, intro_sprint_pct) - max(0.0, intro_sprint_mastery_bonus))
    skip = 1.0 + _pct(max(0.0, wave_skip_chance_pct)) * (1.0 + max(0.0, wave_skip_mastery_bonus))
    return wam * intro * skip


def _ep_tradeoff_defense_factor(rows: Dict[str, StatRow]) -> float:
    return _get_first(
        rows,
        [
            'support_surface::ehp.tradeoff_defense_factor',
            'support_surface::perk.tradeoff_defense_factor',
            _compat_runtime('perk.tradeoff_defense_factor'),
            _compat_mech('perk.tradeoff_defense_factor'),
            'support_surface::perk.improve_tradeoff_defense_factor',
            _compat_runtime('perk.improve_tradeoff_defense_factor'),
            _compat_mech('perk.improve_tradeoff_defense_factor'),
        ],
        1.0,
    )


def _ep_armor_factor(rows: Dict[str, StatRow]) -> float:
    direct = _get_first(
        rows,
        [
            'support_surface::ehp.armor_factor',
            _compat_runtime('armor.multiplier'),
            _compat_mech('armor.multiplier'),
            _compat_canon('tower_armor_multiplier'),
        ],
        0.0,
    )
    if direct > 0.0:
        return direct
    primary_bonus = _get_first(rows, [
        'support_surface::ehp.armor_primary_bonus',
        _compat_mech('module.armor.primary_bonus'),
        _compat_mech('module.armor.primary_multiplier'),
        _compat_mech('module.armor.multiplier'),
    ], 1.0)
    has_assist = _bool(rows, [
        'support_surface::ehp.armor_assist_enabled',
        _compat_mech('module.armor.assist_enabled'),
        _compat_mech('module.armor.has_assist'),
    ], False)
    assist_bonus = _get_first(rows, [
        'support_surface::ehp.armor_assist_bonus',
        _compat_mech('module.armor.assist_bonus_multiplier'),
        _compat_mech('module.armor.assist_bonus'),
    ], 1.0)
    stone_bac = _get_first(rows, [
        'support_surface::ehp.armor_assist_stone_bonus_pct',
        _compat_mech('module.armor.assist_stone_bonus_pct'),
    ], 0.0)
    lab_bac = _get_first(rows, [
        'support_surface::ehp.armor_assist_lab_bonus_pct',
        _compat_mech('module.armor.assist_lab_bonus_pct'),
    ], 0.0)
    return _ep_module_bonus(primary_bonus, has_assist, assist_bonus, stone_bac, lab_bac)




def _ep_health(ws_val: float, lab_lvl: float, has_card: bool, card_val: float, has_mastery: bool, mastery_lvl: float, wse_lvl: float, has_perk: bool, spb_lvl: float, has_cto: bool, has_rto: bool, relic_pct: float, vault_pct: float, has_dwhp: bool, dwhp_lvl: float) -> float:
    lab = 1.0 + 0.03 * lab_lvl
    card = (card_val * (1.0 + 0.2 * (1.0 + mastery_lvl)) if has_mastery else card_val) if has_card else 1.0
    wse = 1.0 + 0.01 * wse_lvl
    perkhp = (1.0 + 0.2 * 5.0) * (1.0 + 0.01 * spb_lvl) if has_perk else 1.0
    cto = 0.3 if has_cto else 1.0
    rto = 0.4 if has_rto else 1.0
    relic = 1.0 + relic_pct
    vault = 1.0 + vault_pct
    dwhp = 5.0 + 0.25 * dwhp_lvl if has_dwhp else 1.0
    return ws_val * lab * card * wse * perkhp * cto * rto * relic * vault * dwhp


def _ep_dabs(ws_val: float, lab_lvl: float, has_card: bool, card_val: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, wse_lvl: float, has_perk: bool, spb_lvl: float, relic_pct: float, vault_pct: float) -> float:
    lab = 1.0 + 0.03 * lab_lvl
    card = card_val if has_card else 1.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = 1.0 + prim_sub + ass_sub * sac
    wse = 1.0 + 0.01 * wse_lvl
    perk = (1.0 + 0.15 * 5.0) * (1.0 + 0.01 * spb_lvl) if has_perk else 1.0
    relic = 1.0 + relic_pct
    vault = 1.0 + vault_pct
    return ws_val * lab * card * substat * wse * perk * relic * vault


def _ep_def_pct(ws_val: float, lab_lvl: float, has_card: bool, card_val: float, has_mastery: bool, mastery_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, has_perk: bool, spb_lvl: float, relic_pct: float, vault_pct: float) -> float:
    lab = 0.002 * lab_lvl
    card = (card_val + 0.007 * (1.0 + mastery_lvl)) if has_card else 0.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    perk = (0.04 * 5.0) * (1.0 + 0.01 * spb_lvl) if has_perk else 0.0
    return min(0.98, ws_val + lab + card + substat + perk + relic_pct + vault_pct)


def _ep_wall_health(ws_val: float, lab_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, wse_lvl: float, prim_effect: float, ass_effect: float, fort_lvl: float) -> float:
    lab = 0.02 * lab_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    wse = 1.0 + 0.01 * wse_lvl
    sf = (prim_effect + ass_effect) if (prim_effect + ass_effect) != 0.0 else 1.0
    wallhp = (ws_val + lab + substat) * wse * sf
    fort = 1.0 + 0.2 * fort_lvl
    return wallhp * fort


def _ep_max_rcvr(ws_val: float, lab_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, wse_lvl: float, vault_pct: float) -> float:
    lab = 0.01 * lab_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    wse = 1.0 + 0.01 * wse_lvl
    vault = 1.0 + vault_pct
    return (ws_val + lab + substat) * wse * vault


def _ep_cpk(ws_val: float, lab_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, wse_lvl: float, has_perk: bool, spb_lvl: float, has_cto: bool, ito_lvl: float, vault_pct: float) -> float:
    lab = 1.0 + 0.02 * lab_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    wse = (1.0 + 0.01 * wse_lvl) ** 2
    perk = (1.0 + 0.15 * 5.0) * (1.0 + 0.01 * spb_lvl) if has_perk else 1.0
    cto = 1.8 * (1.0 + 0.01 * ito_lvl) if has_cto else 1.0
    vault = 1.0 + vault_pct
    return (ws_val * lab + substat) * wse * perk * cto * vault


def _ep_card_coins(has_card: bool, card_val: float, has_mastery: bool, mastery_lvl: float) -> float:
    if not has_card:
        return 1.0
    return card_val * (1.0 + 0.03 * (1.0 + mastery_lvl) if has_mastery else 1.0)


def _ep_card_eom(has_eom: bool, mastery_lvl: float, hit_pct: float) -> float:
    return 1.0 + 0.04 * (1.0 + mastery_lvl) * min(1.0, hit_pct) if has_eom else 1.0


def _ep_fup(ws_val: float, has_card: bool, card_val: float, has_perk: bool, spb_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, wse_lvl: float, relic_pct: float, vault_pct: float) -> float:
    ws = ws_val
    card = card_val if has_card else 0.0
    perk = 0.05 * 5.0 * (1.0 + 0.01 * spb_lvl) if has_perk else 0.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    wse = 1.0 + 0.01 * wse_lvl
    relic = 1.0 + relic_pct
    vault = 1.0 + vault_pct
    return (ws + card + perk + substat) * wse * relic * vault


def _epc_card_ws(skip: int, has_ws: bool, card_val: float, has_mastery: bool, mastery_lvl: float) -> float:
    if not has_ws:
        return 0.0
    ws = card_val
    wsm = 0.1 + 0.05 * mastery_lvl if has_mastery else 0.0
    total = 0.0
    for k in range(0, 6):
        rem = skip - 2 * k
        if rem < 0:
            continue
        total += (ws * (1.0 - wsm)) ** rem * (ws * wsm) ** k * math.comb(k + rem, rem) * (1.0 - ws)
    return total


def _epc_gcomp(ws_val: float, lab_lvl: float, has_card: bool, card_val: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float, pab_lvl: float, boss_wave: float, gcomp_val: float, wave_dur: float) -> float:
    ws = ws_val
    lab = 0.002 * lab_lvl
    card = card_val if has_card else 0.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    rpc = ws + lab + card + substat
    rpcb = ((rpc * (boss_wave - 1.0) + 1.0) / boss_wave) if pab_lvl == 1 else rpc
    ptg = 0.0 if gcomp_val == 0 else -(gcomp_val * rpcb)
    return 1.0 - ptg / (wave_dur + ptg) if (wave_dur + ptg) != 0 else 1.0


def _epc_mvn(mvn: float, assmvn: float, gtcd: float, bhcd: float, dwcd: float, uwcount: float) -> float:
    pmod = math.isfinite(mvn) and mvn != 0.0
    amod = math.isfinite(assmvn) and assmvn != 0.0
    if not (pmod or amod) or uwcount == 0:
        return 0.0
    cd = (gtcd + bhcd + dwcd) / uwcount + (mvn if pmod else assmvn)
    frac = cd - math.floor(cd)
    if abs(frac - 0.5) < 1e-9:
        return float(math.floor(cd) if math.floor(cd) % 2 == 0 else math.ceil(cd))
    return float(round(cd))


def _epc_gtcd(has_gt: bool, stone_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    if not has_gt:
        return 0.0
    stone = 300.0 - 10.0 * stone_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return stone + substat


def _epc_bhcd(has_bh: bool, stone_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    if not has_bh:
        return 0.0
    stone = 200.0 - 10.0 * stone_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return stone + substat


def _epu_dwcd(has_dw: bool, stone_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    if not has_dw:
        return 0.0
    stone = 300.0 - 10.0 * stone_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return stone + substat


def _epc_gtb(stone_lvl: float, lab_lvl: float, has_perk: bool, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    stone = 5.0 + 0.8 * stone_lvl
    lab = 0.15 * lab_lvl
    perk = 1.5 if has_perk else 1.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return (stone + lab) * perk + substat


def _epc_gtd(stone_lvl: float, lab_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    stone = 15.0 + stone_lvl
    lab = lab_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return stone + lab + substat


def _epc_gtgc(has_gc: bool, stone_lvl: float, kps: float, gtd: float) -> float:
    return math.pow(1.0 + 0.0003 * (1.0 + stone_lvl), kps * gtd) if has_gc else 1.0


def _epc_bhcb(lab_lvl: float, kill_pct: float) -> float:
    return ((1.0 + 0.5 * lab_lvl) - 1.0) * kill_pct + 1.0


def _epc_bhd(stone_lvl: float, has_perk: bool, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    stone = 15.0 + stone_lvl
    perk = 12.0 if has_perk else 0.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return stone + perk + substat


def _epc_dwcb(lab_lvl: float) -> float:
    return 1.5 + 0.05 * lab_lvl


def _epu_dwq(stone_lvl: float, has_perk: bool, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    stone = 1.0 + stone_lvl
    perk = 1.0 if has_perk else 0.0
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + math.floor(ass_sub * sac)
    return stone + perk + substat


def _epc_slcb(lab_lvl: float) -> float:
    return 1.0 + 0.1 * lab_lvl


def _epc_sla(stone_lvl: float, stone_sac: float, lab_sac: float, prim_sub: float, ass_sub: float) -> float:
    stone = 30.0 + stone_lvl
    sac = (1.0 + stone_sac + lab_sac) * 0.01
    substat = prim_sub + ass_sub * sac
    return stone + substat


def _epc_slq(stone_lvl: float) -> float:
    return 1.0 + stone_lvl


def _avg_blocks(vec: list[float], width: int) -> list[float]:
    if width <= 0:
        return [float(sum(vec)) / max(len(vec), 1)]
    return [sum(vec[i:i+width]) / len(vec[i:i+width]) for i in range(0, len(vec), width)]


def _ep_sync(hasgt: bool, gtm: float, gtd: float, gtcd: float, gtgc: float, hasbh: bool, bhm: float, bhd: float, bhcd: float, hasdw: bool, dwm: float, dwd: float, dwcd: float, hasgb: bool, gbm: float, gbd: float, gbcd: float) -> float:
    nGT = int(round(gtcd)) if hasgt and gtcd > 0 else 1
    nBH = int(round(bhcd)) if hasbh and bhcd > 0 else 1
    nDW = int(round(dwcd)) if hasdw and dwcd > 0 else 1
    nGB = int(round(gbcd)) if hasgb and gbcd > 0 else 1

    GTA = [1.0 if r <= nGT - gtd else gtm * gtgc for r in range(1, nGT + 1)] if hasgt else [1.0]
    BHA = [1.0 if r <= nBH - bhd else bhm for r in range(1, nBH + 1)] if hasbh else [1.0]
    DWA = [1.0 if r <= nDW - dwd else dwm for r in range(1, nDW + 1)] if hasdw else [1.0]
    GBA = [1.0 if r <= nGB - gbd else gbm for r in range(1, nGB + 1)] if hasgb else [1.0]

    def block_width(n_self: int, others: list[int], active: bool) -> int:
        if not active:
            return 1
        widths = [math.gcd(n_self, n) for n in others if n > 0]
        return max(widths + [1])

    wGT = block_width(nGT, [nBH if hasbh else 0, nDW if hasdw else 0, nGB if hasgb else 0], hasgt)
    wBH = block_width(nBH, [nGT if hasgt else 0, nDW if hasdw else 0, nGB if hasgb else 0], hasbh)
    wDW = block_width(nDW, [nGT if hasgt else 0, nBH if hasbh else 0, nGB if hasgb else 0], hasdw)
    wGB = block_width(nGB, [nGT if hasgt else 0, nBH if hasbh else 0, nDW if hasdw else 0], hasgb)

    GTB = _avg_blocks(GTA, wGT) if hasgt else [1.0]
    BHB = _avg_blocks(BHA, wBH) if hasbh else [1.0]
    DWB = _avg_blocks(DWA, wDW) if hasdw else [1.0]
    GBB = _avg_blocks(GBA, wGB) if hasgb else [1.0]

    rGT, rBH, rDW, rGB = len(GTB), len(BHB), len(DWB), len(GBB)
    LOWCM = math.lcm(rGT, rBH, rDW, rGB)
    prod = []
    for i in range(LOWCM):
        prod.append(
            (GTB[i % rGT] if hasgt else 1.0)
            * (BHB[i % rBH] if hasbh else 1.0)
            * (DWB[i % rDW] if hasdw else 1.0)
            * (GBB[i % rGB] if hasgb else 1.0)
        )
    return sum(prod) / len(prod) if prod else 1.0

def _ep_chain_thunder_factor(rows: Dict[str, StatRow]) -> float:
    reduction_pct = _get_first(
        rows,
        [
            'support_surface::ehp.chain_thunder_reduction_pct',
            'state::uw.chain_lightning.max_enemy_damage_reduction_pct',
            _compat_runtime('uw.chain_thunder.reduction_pct'),
            _compat_mech('uw.chain_thunder.reduction_pct'),
            _compat_mech('uw.chain_lightning.max_enemy_damage_reduction_pct'),
        ],
        0.0,
    )
    if reduction_pct <= 0.0:
        return 1.0
    return 1.0 / max(1.0 - min(0.98, reduction_pct / 100.0), 0.02)

def _contributor(rows: Dict[str, StatRow], key: str, destination: str) -> Dict[str, Any]:
    resolved_key = normalize_surface_id_to_contract(key)
    row = _row(rows, key)
    defaulted_if_missing = row is None or row.final_value is None
    return {
        'stat_name': resolved_key,
        'source_family': 'published_surface',
        'source_name': resolved_key,
        'value': None if row is None else row.final_value,
        'value_type': None if row is None else getattr(row, 'value_type', None),
        'stage': 'derived_surface_publication',
        'destination_object_type': 'derived',
        'destination_id': destination,
        'resolver_id': 'query_derived_composites',
        'kb_mapped': row is not None,
        'defaulted_if_missing': defaulted_if_missing,
    }


_QUERY_DERIVED_REPLACEABLE_SURFACES = frozenset({
    'state::economy.all_coin_bonus_multiplier',
})


def _query_derived_can_replace(name: str, existing: StatRow) -> bool:
    if isinstance(existing.schema, dict) and existing.schema.get('resolver') == 'query_derived_composites':
        return True
    return name in _QUERY_DERIVED_REPLACEABLE_SURFACES


def _publish(rows: Dict[str, StatRow], name: str, value: float, value_type: str, contributors: list[Dict[str, Any]], notes: str) -> None:
    existing = rows.get(name)
    if existing is not None:
        if _query_derived_can_replace(name, existing):
            rows.pop(name, None)
        else:
            raise ValueError(f'Query publication collision for {name}')
    rows[name] = StatRow(
        stat_name=name,
        final_value=value,
        value_type=value_type,
        source_count=len(contributors),
        status='resolved',
        notes=notes,
        contributors=contributors,
        schema={'resolver': 'query_derived_composites'},
    )


def _publish_unresolved(rows: Dict[str, StatRow], name: str, value_type: str, contributors: list[Dict[str, Any]], notes: str) -> None:
    existing = rows.get(name)
    if existing is not None:
        if _query_derived_can_replace(name, existing):
            rows.pop(name, None)
        else:
            if isinstance(existing.schema, dict) and existing.schema.get('resolver') == 'query_derived_composites':
                return
            raise ValueError(f'Query publication collision for {name}')
    rows[name] = StatRow(
        stat_name=name,
        final_value=None,
        value_type=value_type,
        source_count=len(contributors),
        status='mapped_not_resolved',
        notes=notes,
        contributors=contributors,
        schema={'resolver': 'query_derived_composites'},
    )


_DISSONANT_ECHO_LEVEL_SURFACES = {
    'attack': 'state::labs.dissonant_echo.attack.level',
    'defense': 'state::labs.dissonant_echo.defense.level',
    'utility': 'state::labs.dissonant_echo.utility.level',
    'ultimate_weapons': 'state::labs.dissonant_echo.ultimate_weapons.level',
}


def _dissonance_total_multiplier(rows: Dict[str, StatRow], category: str) -> float:
    return _get_first(rows, [f'derived::dissonance.{category}.total_multiplier'], 1.0)


def _publish_dissonance_surfaces(rows: Dict[str, StatRow]) -> None:
    for category, level_surface in _DISSONANT_ECHO_LEVEL_SURFACES.items():
        echo_multiplier_surface = f'derived::dissonance.{category}.echo_multiplier'
        echo_bonus_surface = f'derived::dissonance.{category}.echo_bonus_multiplier'
        level_row = _row(rows, level_surface)
        echo_fraction = 0.0
        try:
            if level_row is not None and level_row.final_value is not None:
                echo_fraction = (1.0 + float(level_row.final_value)) * 0.005
        except (TypeError, ValueError):
            echo_fraction = 0.0
        if level_row is not None:
            _publish(
                rows,
                echo_multiplier_surface,
                echo_fraction,
                'ratio',
                [_contributor(rows, level_surface, f'dissonance.{category}.echo_multiplier')],
                'v28 Dissonant Echo formula from EP v5.06.02: (1 + level) * 0.5%; public max wording says 10.0% while EP level 20 implies 10.5%.',
            )
        active_boost_surface = f'state::dissonance.{category}.active_boost_multiplier'
        echo_source_surface = f'state::dissonance.{category}.echo_source_bonus'
        active_boost = _get_first(rows, [active_boost_surface], 1.0)
        echo_source_bonus = _get_first(rows, [echo_source_surface], 0.0)
        active_delta = max(0.0, active_boost - 1.0)
        echo_spillover_source = max(0.0, echo_source_bonus - active_delta)
        echo_bonus = echo_spillover_source * max(0.0, echo_fraction)
        total_multiplier = active_boost + echo_bonus
        _publish(
            rows,
            echo_bonus_surface,
            echo_bonus,
            'multiplier',
            [
                _contributor(rows, echo_source_surface, f'dissonance.{category}.echo_bonus_multiplier'),
                _contributor(rows, echo_multiplier_surface, f'dissonance.{category}.echo_bonus_multiplier'),
            ],
            'v28 Dissonant Echo additive bonus applied to this tier: sum(max(Dissonant Boost - 1, 0) from other _IDS tier PBs) * Echo lab fraction. The active-tier PB is excluded from Echo to avoid double-counting.',
        )
        _publish(
            rows,
            f'derived::dissonance.{category}.total_multiplier',
            total_multiplier,
            'multiplier',
            [
                _contributor(rows, active_boost_surface, f'dissonance.{category}.total_multiplier'),
                _contributor(rows, echo_bonus_surface, f'dissonance.{category}.total_multiplier'),
            ],
            'v28 total Dissonance multiplier used by stats: active-tier Dissonant Boost plus other-tier Dissonant Echo additive bonus.',
        )


def _publish_effective_bot_ranges(rows: Dict[str, StatRow]) -> None:
    tower_range_m = _get(rows, 'state::tower.range_m')
    global_range_bonus_m = _get(rows, 'state::bot.global.range_bonus_m')
    tower_amplification = 1.33 * (tower_range_m / 69.5) if tower_range_m > 0.0 else 0.0

    for bot_name in ('golden', 'amplify', 'flame', 'thunder', 'bot_bot'):
        owned_surface = f'state::bot.{bot_name}.owned'
        raw_surface = f'state::bot.{bot_name}.range_m'
        effective_surface = f'state::bot.{bot_name}.effective_range_m'
        existing = rows.get(effective_surface)
        if existing is not None and existing.status == 'resolved':
            continue
        if existing is not None:
            rows.pop(effective_surface, None)
        raw_range_m = _get(rows, raw_surface)
        bot_owned = _bool(rows, [owned_surface], default=True)
        effective_range_m = (raw_range_m + global_range_bonus_m) * tower_amplification if bot_owned and tower_amplification > 0.0 else 0.0
        _publish(
            rows,
            effective_surface,
            effective_range_m,
            'distance',
            [
                _contributor(rows, owned_surface, effective_surface),
                _contributor(rows, raw_surface, effective_surface),
                _contributor(rows, 'state::bot.global.range_bonus_m', effective_surface),
                _contributor(rows, 'state::tower.range_m', effective_surface),
            ],
            'QE-published effective bot range from bot owned flag, raw bot range + shared flat bonus, amplified by tower range per sanctioned KB formula.',
        )


_BOT_PLUS_UNLOCK_SURFACES = (
    'state::bot.plus.wildfire.unlocked',
    'state::bot.plus.titan_shock.unlocked',
    'state::bot.plus.bonus_cell.unlocked',
    'state::bot.plus.echoing_shot.unlocked',
    'state::bot.plus.maximum_power.unlocked',
)


def _publish_bot_plus_surfaces(rows: Dict[str, StatRow]) -> None:
    unlocked_count = sum(1 for surface_id in _BOT_PLUS_UNLOCK_SURFACES if _bool(rows, [surface_id], False))
    all_unlocked = unlocked_count == len(_BOT_PLUS_UNLOCK_SURFACES)
    contributors = [_contributor(rows, surface_id, 'bot.plus.all_unlocked') for surface_id in _BOT_PLUS_UNLOCK_SURFACES]
    _publish(
        rows,
        'derived::bot.plus.unlocked_count',
        float(unlocked_count),
        'count',
        contributors,
        'v28 Bot+ unlocked ability count from _IDS Bot+ flags.',
    )
    _publish(
        rows,
        'derived::bot.plus.all_unlocked',
        1.0 if all_unlocked else 0.0,
        'bool',
        contributors,
        'v28 Synchronicity unlock condition: all five Bot+ abilities unlocked.',
    )
    _publish(
        rows,
        'derived::bot.synchronicity.base_slots_unlocked',
        2.0 if all_unlocked else 0.0,
        'count',
        contributors,
        'v28 Synchronicity grants two synchronized pathing slots once all five Bot+ abilities are unlocked; extra stone slots remain input-state growth.',
    )


def publish_derived_composites(rows: Dict[str, StatRow]) -> None:
    _publish_dissonance_surfaces(rows)
    _publish_effective_bot_ranges(rows)
    _publish_bot_plus_surfaces(rows)
    dissonance_override_categories = _dissonance_restriction_override_categories(rows)
    defense_dissonance_active = _bool(
        rows,
        [
            'support_surface::dissonance.defense_run_active',
            'state::dissonance.defense.run_active',
            'context::dissonance.defense_run_active',
        ],
        False,
    ) or 'defense' in dissonance_override_categories
    utility_dissonance_active = _bool(
        rows,
        [
            'support_surface::dissonance.utility_run_active',
            'state::dissonance.utility.run_active',
            'context::dissonance.utility_run_active',
        ],
        False,
    ) or 'utility' in dissonance_override_categories
    ultimate_weapons_dissonance_active = _bool(
        rows,
        [
            'support_surface::dissonance.ultimate_weapons_run_active',
            'state::dissonance.ultimate_weapons.run_active',
            'context::dissonance.ultimate_weapons_run_active',
        ],
        False,
    ) or 'ultimate_weapons' in dissonance_override_categories
    # eHP: closer to EP CN5 structure
    health_factor = _get_first(rows, ['support_surface::ehp.health_factor', _compat_runtime('ehp.health_factor')], 0.0)
    health_ws = _get_first(rows, ['support_surface::ehp.health_ws'], 0.0)
    health_resolved = _get_first(rows, [_compat_canon('tower_hp'), 'state::tower.hp'], 0.0)
    health_lab_factor = 1.0 + 0.03 * _get_first(rows, ['support_surface::ehp.health_lab_level'], 0.0)
    health_card_active = _bool(rows, ['support_surface::ehp.health_card_active'], False)
    health_card_base = _get_first(rows, ['support_surface::ehp.health_card_multiplier'], 1.0)
    health_card_mastery_active = _bool(rows, ['support_surface::ehp.health_card_mastery_active'], False)
    health_card_mastery_level = _get_first(rows, ['support_surface::ehp.health_card_mastery_level'], 0.0)
    health_card_factor = (health_card_base * (1.0 + 0.2 * (1.0 + health_card_mastery_level)) if health_card_mastery_active else health_card_base) if health_card_active else 1.0
    health_wse_factor = 1.0 + 0.01 * _get_first(rows, ['support_surface::ehp.workshop_enhancement_level'], 0.0)
    health_perk_active = _bool(rows, ['support_surface::ehp.health_perk_active'], False)
    standard_perks_bonus_level = _get_first(rows, ['support_surface::ehp.standard_perks_bonus_level'], 0.0)
    health_perk_factor = ((1.0 + 0.2 * 5.0) * (1.0 + 0.01 * standard_perks_bonus_level)) if health_perk_active else 1.0
    health_cto_factor = 0.3 if _bool(rows, ['support_surface::ehp.cto_active'], False) else 1.0
    health_rto_factor = 0.4 if _bool(rows, ['support_surface::ehp.rto_active'], False) else 1.0
    health_relic_factor = 1.0 + _get_first(rows, ['support_surface::ehp.health_relic_pct'], 0.0)
    health_vault_factor = 1.0 + _get_first(rows, ['support_surface::ehp.health_vault_pct'], 0.0)
    health_dwhp_factor = (5.0 + 0.25 * _get_first(rows, ['support_surface::ehp.death_wave_hp_level'], 0.0)) if _bool(rows, ['support_surface::ehp.death_wave_hp_active'], False) else 1.0
    if health_dwhp_factor <= 1.0:
        health_dwhp_factor = _contributor_value_by_token(
            rows,
            row_keys=(_compat_canon('tower_hp'), 'state::tower.hp'),
            token='death_wave_health',
            default=1.0,
        )
    if ultimate_weapons_dissonance_active:
        health_dwhp_factor = 1.0
    if health_ws > 0.0:
        health_factor_fallback = health_ws * health_lab_factor * health_card_factor * health_wse_factor * health_perk_factor * health_cto_factor * health_rto_factor * health_relic_factor * health_vault_factor * health_dwhp_factor
    else:
        health_factor_fallback = health_resolved
    if health_factor <= 0.0:
        health_factor = health_factor_fallback
    defense_dissonance_factor = 1.0 if defense_dissonance_active else _dissonance_total_multiplier(rows, 'defense')
    health_factor = 1.0 if defense_dissonance_active else health_factor * defense_dissonance_factor
    armor_slot_health_factor = _contributor_product_by_token(
        rows,
        row_keys=(_compat_canon('tower_hp'), 'state::tower.hp'),
        token='module__armor__health__pct',
        default=1.0,
    )
    health_raw_factor = health_factor / armor_slot_health_factor if armor_slot_health_factor > 0.0 else health_factor

    armor_primary_factor = _get_first(rows, [
        'support_surface::ehp.armor_primary_factor',
        'support_surface::ehp.armor_primary_bonus',
        _compat_mech('module.armor.primary_factor'),
        _compat_mech('module.armor.primary_bonus'),
        _compat_mech('module.armor.primary_multiplier'),
        _compat_mech('module.armor.multiplier'),
    ], 1.0)
    armor_assist_enabled = _bool(rows, [
        'support_surface::ehp.armor_assist_enabled',
        _compat_mech('module.armor.assist_enabled'),
        _compat_mech('module.armor.has_assist'),
    ], False)
    armor_assist_bonus = _get_first(rows, [
        'support_surface::ehp.armor_assist_bonus',
        _compat_mech('module.armor.assist_bonus_multiplier'),
        _compat_mech('module.armor.assist_bonus'),
    ], 1.0)
    armor_assist_factor = (((armor_assist_bonus - 1.0) * (1.0 + _get_first(rows, ['support_surface::ehp.armor_assist_stone_bonus_pct', _compat_mech('module.armor.assist_stone_bonus_pct')], 0.0) + _get_first(rows, ['support_surface::ehp.armor_assist_lab_bonus_pct', _compat_mech('module.armor.assist_lab_bonus_pct')], 0.0)) * 0.01) + 1.0) if armor_assist_enabled else 1.0
    armor_factor = _get_first(rows, ['support_surface::ehp.armor_factor'], 0.0)
    if armor_factor <= 0.0:
        armor_factor = armor_slot_health_factor if armor_slot_health_factor > 1.0 else armor_primary_factor * armor_assist_factor
    if defense_dissonance_active:
        armor_primary_factor = 1.0
        armor_assist_factor = 1.0
        armor_factor = 1.0

    wall_health_final = _get_first(rows, ['state::wall.hp', _compat_canon('wall_hp')], 0.0)
    tower_hp_for_wall = health_factor if health_factor > 0.0 else _get_first(rows, ['state::tower.hp', _compat_canon('tower_hp')], 0.0)
    wall_hp_row = _row(rows, 'state::wall.hp')
    wall_hp_derivation = None
    if wall_hp_row is not None and tower_hp_for_wall > 0.0:
        try:
            wall_hp_derivation = derive_wall_hp_from_qe_primitives(
                tower_hp=tower_hp_for_wall,
                wall_hp_contributors=tuple(dict(contributor or {}) for contributor in (wall_hp_row.contributors or ())),
            )
        except ValueError:
            wall_hp_derivation = None
    wall_health_ws = _get_first(rows, ['support_surface::ehp.wall_hp_ws'], 0.0)
    wall_health_lab_term = 0.02 * _get_first(rows, ['support_surface::ehp.wall_hp_lab_level'], 0.0)
    ehp_sac_factor = (1.0 + _get_first(rows, ['support_surface::ehp.stone_sac_pct'], 0.0) + _get_first(rows, ['support_surface::ehp.lab_sac_pct'], 0.0)) * 0.01
    wall_health_substat_term = _get_first(rows, ['support_surface::ehp.wall_hp_prim_sub'], 0.0) + _get_first(rows, ['support_surface::ehp.wall_hp_ass_sub'], 0.0) * ehp_sac_factor
    wall_health_wse_factor = 1.0 + 0.01 * _get_first(rows, ['support_surface::ehp.workshop_enhancement_level'], 0.0)
    wall_health_module_factor = (_get_first(rows, ['support_surface::ehp.wall_module_primary_effect'], 0.0) + _get_first(rows, ['support_surface::ehp.wall_module_assist_effect'], 0.0)) or 1.0
    wall_health_pre_fort = (wall_health_ws + wall_health_lab_term + wall_health_substat_term) * wall_health_wse_factor * wall_health_module_factor
    wall_health_fort_factor = 1.0 + 0.2 * _get_first(rows, ['support_surface::ehp.wall_fortification_level'], 0.0)
    if wall_health_fort_factor <= 1.0:
        wall_health_fort_factor = _get_first(rows, ['state::wall.fortification_multiplier'], wall_health_fort_factor)
    if wall_health_pre_fort <= 0.0 and wall_health_final > 0.0 and wall_health_fort_factor > 0.0:
        wall_health_pre_fort = wall_health_final / wall_health_fort_factor
    if wall_hp_derivation is not None:
        wall_health_pre_fort = float(wall_hp_derivation['wall_hp_pre_fort'])
    wall_health_display_final = wall_health_pre_fort * wall_health_fort_factor
    wall_health_factor = _get_first(rows, ['support_surface::ehp.wall_health_factor'], 0.0)
    if wall_health_factor <= 0.0:
        if health_factor > 0.0 and wall_health_display_final > 0.0:
            wall_health_factor = wall_health_display_final / health_factor
        else:
            wall_health_factor = wall_health_final if wall_health_final > 0.0 else (wall_health_pre_fort * wall_health_fort_factor)
    if defense_dissonance_active:
        wall_health_lab_term = 0.0
        wall_health_substat_term = 0.0
        wall_health_wse_factor = 1.0
        wall_health_module_factor = 1.0
        wall_health_fort_factor = 1.0
        wall_health_pre_fort = 0.0
        wall_health_display_final = 0.0
        wall_health_factor = 0.0

    recovery_ws = _get_first(rows, [_compat_canon('max_recovery_multiplier'), 'support_surface::ehp.max_recovery_ws'], 0.0)
    recovery_lab_term = 0.01 * _get_first(rows, ['support_surface::ehp.max_recovery_lab_level'], 0.0)
    recovery_substat_term = _get_first(rows, ['support_surface::ehp.max_recovery_prim_sub'], 0.0) + _get_first(rows, ['support_surface::ehp.max_recovery_ass_sub'], 0.0) * ehp_sac_factor
    recovery_wse_factor = 1.0 + 0.01 * _get_first(rows, ['support_surface::ehp.workshop_enhancement_level'], 0.0)
    recovery_vault_factor = 1.0 + _get_first(rows, ['support_surface::ehp.max_recovery_vault_pct'], 0.0)
    max_recovery_factor = _get_first(rows, ['support_surface::ehp.max_recovery_factor'], 0.0)
    if max_recovery_factor <= 0.0:
        max_recovery_factor = (recovery_ws + recovery_lab_term + recovery_substat_term) * recovery_wse_factor * recovery_vault_factor
    if defense_dissonance_active:
        recovery_lab_term = 0.0
        recovery_substat_term = 0.0
        recovery_wse_factor = 1.0
        recovery_vault_factor = 1.0
        max_recovery_factor = 0.0

    wall_active = _bool(rows, ['support_surface::ehp.wall_active'], wall_health_factor > 0.0)
    recovery_active = _bool(rows, ['support_surface::ehp.max_recovery_active'], max_recovery_factor > 0.0)
    if defense_dissonance_active:
        wall_active = False
        recovery_active = False
    wall_or_recovery_factor = (wall_health_factor + max_recovery_factor) if (wall_active or recovery_active) else 1.0

    dabs_ws = _get_first(rows, ['support_surface::ehp.dabs_ws'], 0.0)
    dabs_resolved = _get_first(rows, [_compat_canon('tower_defense_absolute'), 'state::tower.defense_absolute'], 0.0)
    dabs_lab_factor = 1.0 + 0.03 * _get_first(rows, ['support_surface::ehp.dabs_lab_level'], 0.0)
    dabs_card_factor = _get_first(rows, ['support_surface::ehp.dabs_card_multiplier'], 1.0) if _bool(rows, ['support_surface::ehp.dabs_card_active'], False) else 1.0
    dabs_substat_factor = 1.0 + _get_first(rows, ['support_surface::ehp.dabs_prim_sub'], 0.0) + _get_first(rows, ['support_surface::ehp.dabs_ass_sub'], 0.0) * ehp_sac_factor
    dabs_wse_factor = 1.0 + 0.01 * _get_first(rows, ['support_surface::ehp.workshop_enhancement_level'], 0.0)
    dabs_perk_factor = ((1.0 + 0.15 * 5.0) * (1.0 + 0.01 * standard_perks_bonus_level)) if _bool(rows, ['support_surface::ehp.dabs_perk_active'], False) else 1.0
    dabs_relic_factor = 1.0 + _get_first(rows, ['support_surface::ehp.dabs_relic_pct'], 0.0)
    dabs_vault_factor = 1.0 + _get_first(rows, ['support_surface::ehp.dabs_vault_pct'], 0.0)
    if dabs_ws > 0.0:
        dabs_base_factor = dabs_ws * dabs_lab_factor * dabs_card_factor * dabs_substat_factor * dabs_wse_factor * dabs_perk_factor * dabs_relic_factor * dabs_vault_factor
    else:
        dabs_base_factor = dabs_resolved
    dabs = _get_first(rows, ['support_surface::ehp.dabs_factor'], 0.0)
    if dabs <= 0.0:
        dabs = dabs_base_factor
    if defense_dissonance_active:
        dabs_base_factor = 0.0
        dabs = 0.0

    def_pct_ws = _get_first(rows, [_compat_canon('tower_defense_pct'), 'support_surface::ehp.def_pct_ws'], 0.0)
    def_pct_lab_term = 0.002 * _get_first(rows, ['support_surface::ehp.def_pct_lab_level'], 0.0)
    def_pct_card_term = (_get_first(rows, ['support_surface::ehp.def_pct_card_bonus'], 0.0) + 0.007 * (1.0 + _get_first(rows, ['support_surface::ehp.def_pct_card_mastery_level'], 0.0)) if _bool(rows, ['support_surface::ehp.def_pct_card_mastery_active'], False) else _get_first(rows, ['support_surface::ehp.def_pct_card_bonus'], 0.0)) if _bool(rows, ['support_surface::ehp.def_pct_card_active'], False) else 0.0
    def_pct_substat_term = _get_first(rows, ['support_surface::ehp.def_pct_prim_sub'], 0.0) + _get_first(rows, ['support_surface::ehp.def_pct_ass_sub'], 0.0) * ehp_sac_factor
    def_pct_perk_term = ((0.04 * 5.0) * (1.0 + 0.01 * standard_perks_bonus_level)) if _bool(rows, ['support_surface::ehp.def_pct_perk_active'], False) else 0.0
    def_pct_relic_term = _get_first(rows, ['support_surface::ehp.def_pct_relic_pct'], 0.0)
    def_pct_vault_term = _get_first(rows, ['support_surface::ehp.def_pct_vault_pct'], 0.0)
    defense_pct = _get_first(rows, ['support_surface::ehp.def_pct'], -1.0)
    def_pct_raw = min(0.98, def_pct_ws + def_pct_lab_term + def_pct_card_term + def_pct_substat_term + def_pct_perk_term + def_pct_relic_term + def_pct_vault_term)
    if defense_pct < 0.0:
        defense_pct = def_pct_raw
    if defense_dissonance_active:
        defense_pct = 0.0
        def_pct_raw = 0.0
    defense_taken_factor = 1.0 / max(1.0 - defense_pct, 0.01)

    chrono_duration = _get_first(rows, ['support_surface::ehp.chrono_field_duration_seconds'], -1.0)
    if chrono_duration < 0.0:
        chrono_duration = _tp(rows, _compat_mech('uw.chrono_field.duration_seconds'), _compat_runtime('uw.chrono_field.duration_seconds'))
    chrono_cooldown = _get_first(rows, ['support_surface::ehp.chrono_field_cooldown_seconds', _compat_mech('uw.chrono_field.cooldown_seconds')], 0.0)
    chrono_reduction_pct = _get_first(rows, ['support_surface::ehp.chrono_field_damage_reduction_pct', _compat_mech('uw.chrono_field.damage_reduction_pct')], 0.0)
    cfu = _uptime(chrono_duration, chrono_cooldown)
    cf_factor = 1.0 / max(1.0 - min(0.95, cfu * chrono_reduction_pct / 100.0), 0.05)
    if ultimate_weapons_dissonance_active:
        chrono_duration = 0.0
        chrono_cooldown = 0.0
        chrono_reduction_pct = 0.0
        cfu = 0.0
        cf_factor = 1.0
    wall_invuln_reduction_pct = _get_first(rows, ['support_surface::ehp.wall_invuln_reduction_pct'], 0.0)
    wall_invuln_factor = 1.0 / max(1.0 - wall_invuln_reduction_pct, 0.05)
    chain_thunder_reduction_pct = _get_first(rows, [
        'support_surface::ehp.chain_thunder_reduction_pct',
        'state::uw.chain_lightning.max_enemy_damage_reduction_pct',
        _compat_runtime('uw.chain_thunder.reduction_pct'),
        _compat_mech('uw.chain_thunder.reduction_pct'),
        _compat_mech('uw.chain_lightning.max_enemy_damage_reduction_pct'),
    ], 0.0)
    chain_thunder_factor = _ep_chain_thunder_factor(rows)
    if ultimate_weapons_dissonance_active:
        chain_thunder_reduction_pct = 0.0
        chain_thunder_factor = 1.0
    primordial_bh_reduction_pct = _get_first(rows, [
        'state::module.primordial_collapse.bh_damage_reduction_pct',
        _compat_mech('module.primordial_collapse.bh_damage_reduction_pct'),
        _compat_mech('module.primordial_collapse.in_bh_enemy_damage_reduction_pct'),
    ], 0.0)
    primordial_bh_duration = _get_first(rows, [
        'support_surface::ehp.black_hole_duration_seconds',
        'state::uw.black_hole.base_duration_seconds',
        _compat_mech('uw.black_hole.duration_seconds'),
    ], 0.0)
    primordial_bh_cooldown = _get_first(rows, [
        'support_surface::ehp.black_hole_cooldown_seconds',
        'state::uw.black_hole.base_cooldown_seconds',
        _compat_mech('uw.black_hole.cooldown_seconds'),
    ], 0.0)
    primordial_bh_uptime = _uptime(primordial_bh_duration, primordial_bh_cooldown)
    primordial_bh_factor = 1.0 / max(1.0 - min(0.95, primordial_bh_uptime * primordial_bh_reduction_pct / 100.0), 0.05)
    if ultimate_weapons_dissonance_active:
        primordial_bh_reduction_pct = 0.0
        primordial_bh_duration = 0.0
        primordial_bh_cooldown = 0.0
        primordial_bh_uptime = 0.0
        primordial_bh_factor = 1.0
    tradeoff_defense_factor = _ep_tradeoff_defense_factor(rows)
    tradeoff_defense_reduction_pct = max(0.0, 1.0 - (1.0 / tradeoff_defense_factor)) * 100.0 if tradeoff_defense_factor > 0 else 0.0

    base_pool = health_raw_factor * armor_factor * wall_or_recovery_factor
    pre_defense_pool = base_pool * cf_factor * chain_thunder_factor * primordial_bh_factor
    dabs_effective = dabs * wall_invuln_factor
    pre_tradeoff_ehp = (pre_defense_pool + dabs_effective) * defense_taken_factor
    ehp = pre_tradeoff_ehp * tradeoff_defense_factor
    ehp_contrib = [_contributor(rows, _compat_canon('tower_hp'), 'ehp'), _contributor(rows, _compat_canon('wall_hp'), 'ehp')]
    _publish(rows, 'derived::ehp.health_lab_factor', health_lab_factor, 'multiplier', [], 'EPH_HEALTH lab factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_card_factor', health_card_factor, 'multiplier', [], 'EPH_HEALTH card factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_wse_factor', health_wse_factor, 'multiplier', [], 'EPH_HEALTH workshop enhancement factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_perk_factor', health_perk_factor, 'multiplier', [], 'EPH_HEALTH perk factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_cto_factor', health_cto_factor, 'multiplier', [], 'EPH_HEALTH CTO factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_rto_factor', health_rto_factor, 'multiplier', [], 'EPH_HEALTH RTO factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_relic_factor', health_relic_factor, 'multiplier', [], 'EPH_HEALTH relic factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_vault_factor', health_vault_factor, 'multiplier', [], 'EPH_HEALTH vault factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.health_dwhp_factor', health_dwhp_factor, 'multiplier', [], 'EPH_HEALTH death-wave HP factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.defense_dissonance_factor', defense_dissonance_factor, 'multiplier', [_contributor(rows, 'derived::dissonance.defense.total_multiplier', 'ehp.defense_dissonance_factor')], 'v28 Health Dissonance/Echo multiplier applied to the eHP health factor.')
    _publish(rows, 'derived::ehp.health_raw_factor', health_raw_factor, 'scalar', ehp_contrib, 'EPH_HEALTH raw health helper before the Armor-slot module health multiplier; EP exports this separately as Health raw.')
    _publish(rows, 'derived::ehp.health_factor', health_factor, 'scalar', ehp_contrib, 'EPH_HEALTH-like health factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.armor_primary_factor', armor_primary_factor, 'multiplier', [], 'EPH_ARMOR primary factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.armor_assist_factor', armor_assist_factor, 'multiplier', [], 'EPH_ARMOR assist factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.armor_factor', armor_factor, 'multiplier', [_contributor(rows, 'support_surface::ehp.armor_factor', 'ehp.armor_factor')], 'EPH_ARMOR-like armor factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_health_lab_term', wall_health_lab_term, 'scalar', [], 'EPH_WALL_HEALTH lab term [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_health_substat_term', wall_health_substat_term, 'scalar', [], 'EPH_WALL_HEALTH substat term [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_health_wse_factor', wall_health_wse_factor, 'multiplier', [], 'EPH_WALL_HEALTH workshop enhancement factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_health_module_factor', wall_health_module_factor, 'multiplier', [], 'EPH_WALL_HEALTH module factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_health_fort_factor', wall_health_fort_factor, 'multiplier', [], 'EPH_WALL_HEALTH fortification factor [EP helper support surface]')
    _publish(
        rows,
        'derived::wall.hp_pre_fort',
        wall_health_pre_fort,
        'hp',
        [
            _contributor(rows, 'derived::ehp.wall_health_wse_factor', 'wall.hp_pre_fort'),
            _contributor(rows, 'derived::ehp.wall_health_module_factor', 'wall.hp_pre_fort'),
            _contributor(rows, 'state::wall.hp', 'wall.hp_pre_fort'),
            _contributor(rows, 'state::wall.fortification_multiplier', 'wall.hp_pre_fort'),
        ],
        'QE-published wall HP before fortification.',
    )
    _publish(
        rows,
        'derived::wall.hp_final',
        wall_health_display_final,
        'hp',
        [
            _contributor(rows, 'derived::wall.hp_pre_fort', 'wall.hp_final'),
            _contributor(rows, 'state::wall.fortification_multiplier', 'wall.hp_final'),
        ],
        'QE-published final displayed Wall HP / Wall Pool after applying wall fortification once.',
    )
    wall_regen_pct_points = _get_first(rows, ['state::wall.regen', _compat_canon('wall_regen')], 0.0)
    tower_regen_hp_per_second = _get_first(rows, ['state::tower.regen', _compat_canon('tower_regen')], 0.0)
    wall_regen_hp_per_second = 0.0
    if tower_regen_hp_per_second > 0.0 and wall_regen_pct_points >= 0.0:
        wall_regen_hp_per_second = derive_wall_regen_hp_per_second(
            tower_regen_hp_per_second=tower_regen_hp_per_second,
            wall_regen_percent_points=wall_regen_pct_points,
        )
    if defense_dissonance_active:
        wall_regen_hp_per_second = 0.0
    _publish(
        rows,
        'derived::wall.regen_hp_per_second',
        wall_regen_hp_per_second,
        'hp_per_second',
        [
            _contributor(rows, 'state::tower.regen', 'wall.regen_hp_per_second'),
            _contributor(rows, 'state::wall.regen', 'wall.regen_hp_per_second'),
        ],
        'QE-published final displayed Wall Regen HP/sec from tower regen and wall regen percent-points.',
    )
    _publish(rows, 'derived::ehp.wall_factor', wall_health_factor, 'scalar', ehp_contrib, 'EPH_WALL_HEALTH-like factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.max_recovery_lab_term', recovery_lab_term, 'scalar', [], 'EPH_MAX_RCVR lab term [EP helper support surface]')
    _publish(rows, 'derived::ehp.max_recovery_substat_term', recovery_substat_term, 'scalar', [], 'EPH_MAX_RCVR substat term [EP helper support surface]')
    _publish(rows, 'derived::ehp.max_recovery_wse_factor', recovery_wse_factor, 'multiplier', [], 'EPH_MAX_RCVR workshop enhancement factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.max_recovery_vault_factor', recovery_vault_factor, 'multiplier', [], 'EPH_MAX_RCVR vault factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.recovery_package_factor', max_recovery_factor, 'scalar', ehp_contrib, 'EPH_MAX_RCVR-like factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_or_recovery_factor', wall_or_recovery_factor, 'scalar', ehp_contrib, 'EP CN5 IF(OR(CI,CJ),CI+CJ,1) factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_pkg_factor', wall_or_recovery_factor, 'scalar', ehp_contrib, 'EP CN5 wall/max recovery additive factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.base_pool', base_pool, 'scalar', ehp_contrib, 'health x armor x wall/max recovery base pool [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_lab_factor', dabs_lab_factor, 'multiplier', [], 'EPH_DABS lab factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_card_factor', dabs_card_factor, 'multiplier', [], 'EPH_DABS card factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_substat_factor', dabs_substat_factor, 'multiplier', [], 'EPH_DABS substat factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_wse_factor', dabs_wse_factor, 'multiplier', [], 'EPH_DABS workshop enhancement factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_perk_factor', dabs_perk_factor, 'multiplier', [], 'EPH_DABS perk factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_relic_factor', dabs_relic_factor, 'multiplier', [], 'EPH_DABS relic factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_vault_factor', dabs_vault_factor, 'multiplier', [], 'EPH_DABS vault factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_base_factor', dabs_base_factor, 'scalar', [], 'EPH_DABS base factor before wall invulnerability [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_effective_factor', dabs_effective, 'scalar', [], 'EP CG5 additive DABS factor after wall invulnerability [EP helper support surface]')
    _publish(rows, 'derived::ehp.dabs_factor', dabs, 'scalar', [_contributor(rows, _compat_canon('tower_defense_absolute'), 'ehp.dabs_factor')], 'EPH_DABS-like additive absolute defense term [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_raw', def_pct_raw, 'ratio', [], 'EPH_DEF_PCT raw defense pct before direct override [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_lab_term', def_pct_lab_term, 'ratio', [], 'EPH_DEF_PCT lab term [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_card_term', def_pct_card_term, 'ratio', [], 'EPH_DEF_PCT card term [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_substat_term', def_pct_substat_term, 'ratio', [], 'EPH_DEF_PCT substat term [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_perk_term', def_pct_perk_term, 'ratio', [], 'EPH_DEF_PCT perk term [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_relic_term', def_pct_relic_term, 'ratio', [], 'EPH_DEF_PCT relic term [EP helper support surface]')
    _publish(rows, 'derived::ehp.def_pct_vault_term', def_pct_vault_term, 'ratio', [], 'EPH_DEF_PCT vault term [EP helper support surface]')
    _publish(rows, 'derived::ehp.defense_taken_factor', defense_taken_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_defense_pct'), 'ehp.defense_taken_factor')], '1/(1-EPH_DEF_PCT) [EP helper support surface]')
    _publish(rows, 'derived::ehp.chrono_field_duration_seconds', chrono_duration, 'scalar', [], 'Chrono Field duration [EP helper support surface]')
    _publish(rows, 'derived::ehp.chrono_field_cooldown_seconds', chrono_cooldown, 'scalar', [], 'Chrono Field cooldown [EP helper support surface]')
    _publish(rows, 'derived::ehp.chrono_field_damage_reduction_pct', chrono_reduction_pct, 'ratio', [], 'Chrono Field damage reduction pct [EP helper support surface]')
    _publish(rows, 'derived::ehp.chrono_field_uptime', cfu, 'ratio', [_contributor(rows, _compat_mech('uw.chrono_field.duration_seconds'), 'ehp.chrono_field_uptime')], 'chrono field uptime [EP helper support surface]')
    _publish(rows, 'derived::ehp.chrono_field_damage_reduction_factor', cf_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.chrono_field.damage_reduction_pct'), 'ehp.chrono_field_damage_reduction_factor')], 'chrono field reduction factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_invuln_reduction_pct', wall_invuln_reduction_pct, 'ratio', [], 'Wall invulnerability reduction pct [EP helper support surface]')
    _publish(rows, 'derived::ehp.wall_invuln_factor', wall_invuln_factor, 'multiplier', [_contributor(rows, 'support_surface::ehp.wall_invuln_reduction_pct', 'ehp.wall_invuln_factor')], 'wall invulnerability factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.chain_thunder_reduction_pct', chain_thunder_reduction_pct, 'ratio', [], 'Chain Thunder reduction pct [EP helper support surface]')
    _publish(rows, 'derived::ehp.chain_thunder_factor', chain_thunder_factor, 'multiplier', [_contributor(rows, 'state::uw.chain_lightning.max_enemy_damage_reduction_pct', 'ehp.chain_thunder_factor')], 'EP CN5 chain thunder factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.primordial_black_hole_uptime', primordial_bh_uptime, 'ratio', [
        _contributor(rows, 'support_surface::ehp.black_hole_duration_seconds', 'ehp.primordial_black_hole_uptime'),
        _contributor(rows, 'support_surface::ehp.black_hole_cooldown_seconds', 'ehp.primordial_black_hole_uptime'),
    ], 'Primordial Collapse black-hole uptime [EP helper support surface]')
    _publish(rows, 'derived::ehp.primordial_black_hole_damage_reduction_factor', primordial_bh_factor, 'multiplier', [
        _contributor(rows, 'state::module.primordial_collapse.bh_damage_reduction_pct', 'ehp.primordial_black_hole_damage_reduction_factor'),
        _contributor(rows, 'support_surface::ehp.black_hole_duration_seconds', 'ehp.primordial_black_hole_damage_reduction_factor'),
        _contributor(rows, 'support_surface::ehp.black_hole_cooldown_seconds', 'ehp.primordial_black_hole_damage_reduction_factor'),
    ], 'Primordial Collapse black-hole damage reduction factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.tradeoff_defense_reduction_pct', tradeoff_defense_reduction_pct, 'ratio', [], 'Tradeoff defense reduction pct [EP helper support surface]')
    _publish(rows, 'derived::ehp.tradeoff_defense_factor', tradeoff_defense_factor, 'multiplier', [_contributor(rows, _compat_mech('perk.tradeoff_defense_factor'), 'ehp.tradeoff_defense_factor')], 'improve trade-off defense factor [EP helper support surface]')
    _publish(rows, 'derived::ehp.pre_defense_pool', pre_defense_pool, 'scalar', ehp_contrib, 'EP CN5 pre-defense multiplicative pool [EP helper support surface]')
    _publish(rows, 'derived::ehp.pre_tradeoff_ehp', pre_tradeoff_ehp, 'scalar', ehp_contrib, 'EP CN5 pre-tradeoff eHP [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.ce_pool_factor', health_factor, 'scalar', ehp_contrib, 'EP eHP CE5 pool factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.cf_armor_factor', armor_factor, 'multiplier', [_contributor(rows, 'support_surface::ehp.armor_factor', 'ehp.ep_cf_armor_factor')], 'EP eHP CF5 armor factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.ci_wall_factor', wall_health_factor, 'scalar', ehp_contrib, 'EP eHP CI5 wall factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.cj_recovery_factor', max_recovery_factor, 'scalar', ehp_contrib, 'EP eHP CJ5 max recovery factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.cg_dabs_factor', dabs_effective, 'scalar', [_contributor(rows, _compat_canon('tower_defense_absolute'), 'ehp.ep_cg_dabs_factor')], 'EP eHP CG5 DABS factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.ch_defense_taken_factor', defense_taken_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_defense_pct'), 'ehp.ep_ch_defense_taken_factor')], 'EP eHP CH5 defense taken factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.ck_tradeoff_factor', tradeoff_defense_factor, 'multiplier', [_contributor(rows, _compat_mech('perk.tradeoff_defense_factor'), 'ehp.ep_ck_tradeoff_factor')], 'EP eHP CK5 tradeoff factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.cl_cfdr_factor', cf_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.chrono_field.damage_reduction_pct'), 'ehp.ep_cl_cfdr_factor')], 'EP eHP CL5 chrono damage reduction factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp_ep_helper.cm_chain_thunder_factor', chain_thunder_factor, 'multiplier', [_contributor(rows, 'state::uw.chain_lightning.max_enemy_damage_reduction_pct', 'ehp.ep_cm_chain_thunder_factor')], 'EP eHP CM5 chain thunder factor alias [EP helper support surface]')
    _publish(rows, 'derived::ehp', ehp, 'scalar', ehp_contrib, 'Native eHP objective line; currently equal to EP line')
    _publish(rows, 'derived::ehp_ep', ehp, 'scalar', ehp_contrib, 'Exact Effective Paths eHP objective line')

    # eDamage: expanded EP-structured decomposition
    td = _get(rows, _compat_canon('tower_damage'))
    asp = _get_first(rows, [_compat_canon('tower_attack_speed'), 'derived::attack_speed'])
    dpm = _get(rows, _compat_canon('tower_damage_per_meter_multiplier'))
    rng = _get(rows, _compat_canon('tower_range_m'))
    kill_at_range = _get_first(rows, ['support_surface::timing.kill_at_range_multiplier', _compat_runtime('targeting.kill_at_range_multiplier'), _compat_mech('targeting.kill_at_range_multiplier')], 0.25)
    attack_dissonance_active = _bool(
        rows,
        [
            'support_surface::dissonance.attack_run_active',
            'state::dissonance.attack.run_active',
            'context::dissonance.attack_run_active',
        ],
        False,
    ) or 'attack' in dissonance_override_categories
    defense_dissonance_active = _bool(
        rows,
        [
            'support_surface::dissonance.defense_run_active',
            'state::dissonance.defense.run_active',
            'context::dissonance.defense_run_active',
        ],
        False,
    ) or 'defense' in dissonance_override_categories
    if attack_dissonance_active:
        asp = 1.0
        dpm = 0.0
        rng = 30.0

    perk_damage_factor = _get_first(rows, ['support_surface::perk.damage_multiplier', _compat_runtime('perk.damage_multiplier'), _compat_mech('perk.damage_multiplier')], 1.0)
    tradeoff_damage_factor = _get_first(rows, ['support_surface::perk.tradeoff_damage_multiplier', _compat_runtime('perk.tradeoff_damage_multiplier'), _compat_mech('perk.tradeoff_damage_multiplier')], 1.0)
    shock_factor = _ep_shock_factor(rows)
    card_damage_mastery_factor = _get_first(
        rows,
        [
            'state::cards.damage.mastery_effect',
            _compat_runtime('cards.damage.mastery_effect'),
            _compat_mech('cards.damage.mastery_effect'),
            _compat_runtime('cards.damage.mastery_multiplier'),
            _compat_mech('cards.damage.mastery_multiplier'),
        ],
        1.0,
    )
    berserker_bonus_multiplier = _get_first(
        rows,
        [
            'state::cards.berserker.assumed_bonus_multiplier',
            _compat_runtime('cards.berserker.assumed_bonus_multiplier'),
            _compat_mech('cards.berserker.assumed_bonus_multiplier'),
        ],
        0.0,
    )
    berserker_factor = 1.0 + max(0.0, berserker_bonus_multiplier)

    cannon_module_factor = _get_first(rows, [_compat_mech('module.cannon.primary_damage_multiplier'), _compat_mech('module.cannon.damage_multiplier'), _compat_mech('module.cannon.multiplier')], 1.0)
    cannon_assist_enabled = _bool(rows, [_compat_mech('module.cannon.assist_enabled'), _compat_mech('module.cannon.has_assist')], False)
    cannon_assist_bonus = _get_first(rows, [_compat_mech('module.cannon.assist_bonus_multiplier'), _compat_mech('module.cannon.assist_multiplier')], 1.0)
    cannon_assist_factor = _ep_module_bonus(
        cannon_module_factor,
        cannon_assist_enabled,
        cannon_assist_bonus,
        _get_first(rows, [_compat_mech('module.cannon.assist_stone_bonus_pct')], 0.0),
        _get_first(rows, [_compat_mech('module.cannon.assist_lab_bonus_pct')], 0.0),
    )

    acp_raw = _get_first(rows, ['state::module.anti_cube_portal.shockwave_damage_taken_mult_x', _compat_mech('module.anti_cube_portal.shockwave_damage_taken_mult_x'), _compat_mech('module.anti_cube_portal.damage_multiplier'), _compat_mech('module.anti_cube_portal.multiplier'), _compat_mech('module.acp.damage_multiplier'), _compat_mech('module.acp.multiplier')], 0.0)
    shockwave_size_m = _get_first(rows, ['state::tower.shockwave_size_m', _compat_canon('tower_shockwave_size_m')], 0.0)
    shockwave_interval_seconds = _get_first(rows, ['state::tower.shockwave_interval_seconds', _compat_canon('tower_shockwave_interval_seconds')], 0.0)
    if defense_dissonance_active:
        acp_factor = 1.0
    elif acp_raw > 0.0 and shockwave_size_m > 0.0 and shockwave_interval_seconds > 0.0:
        acp_factor = 1.0 + (acp_raw - 1.0) * (7.0 / max(shockwave_interval_seconds + shockwave_size_m / 2.0, 1e-9))
    else:
        acp_factor = _ep_shockwave_damage(
            acp_raw,
            _get_first(rows, [_compat_canon('shockwave_size_level'), _compat_mech('shockwave.size_ws_level')], 0.0),
            _get_first(rows, [_compat_runtime('shockwave.size_lab_level'), _compat_mech('shockwave.size_lab_level')], 0.0),
            _get_first(rows, [_compat_canon('shockwave_frequency_level'), _compat_mech('shockwave.frequency_ws_level')], 0.0),
            _get_first(rows, [_compat_runtime('shockwave.frequency_vault_bonus_seconds'), _compat_mech('shockwave.frequency_vault_bonus_seconds')], 0.0),
            _get_first(rows, [_compat_mech('shockwave.frequency_substat_seconds'), _compat_runtime('shockwave.frequency_substat_seconds')], 0.0),
        )
    amp_strike_factor = _get_first(rows, ['support_surface::amp_strike.damage_multiplier', _compat_mech('amp_strike.damage_multiplier')], 1.0)

    attack_dissonance_factor = _dissonance_total_multiplier(rows, 'attack')
    if attack_dissonance_active:
        base_damage_stack = acp_factor * amp_strike_factor
    else:
        base_damage_stack = td * perk_damage_factor * tradeoff_damage_factor * shock_factor * card_damage_mastery_factor * berserker_factor * cannon_assist_factor * acp_factor * amp_strike_factor * attack_dissonance_factor

    cc = _get(rows, _compat_canon('tower_crit_chance_pct'))
    cf = _get(rows, _compat_canon('tower_crit_multiplier'))
    scc = _get(rows, _compat_canon('tower_supercrit_chance_pct'))
    scm = _get(rows, _compat_canon('tower_supercrit_multiplier'))
    if attack_dissonance_active:
        cc = 0.0
        cf = 1.0
        scc = 0.0
        scm = 1.0
    ultimate_crit_card_chance_pct = _get_first(
        rows,
        [
            'state::cards.ultimate_crit.chance_pct',
            _compat_runtime('cards.ultimate_crit.chance_pct'),
            _compat_mech('cards.ultimate_crit.chance_pct'),
        ],
        0.0,
    )
    being_annihilator = _get_first(
        rows,
        [
            'state::module.being_annihilator.guaranteed_supercrits_after_supercrit_attacks',
            _compat_mech('module.being_annihilator.guaranteed_supercrits_after_supercrit_attacks'),
            _compat_runtime('module.being_annihilator.guaranteed_supercrits_after_supercrit_attacks'),
            _compat_mech('module.being_annihilator.streak_count'),
            _compat_runtime('module.being_annihilator.streak_count'),
        ],
        0.0,
    )
    bullet_crit_factor = _ep_critical(cc, cf, scc, scm, being_annihilator)
    uw_crit_factor = _ep_uwcritical(cc, cf, scc, scm)
    uw_crit_card_factor = _ev(ultimate_crit_card_chance_pct, cf)

    bps = _ep_bullet_per_second(asp)
    multishot_factor = _ep_multishot(_get(rows, _compat_canon('tower_multishot_chance_pct')), _get(rows, _compat_canon('tower_multishot_targets')))
    bounce_factor = _ep_bounceshot(
        _get(rows, _compat_canon('tower_bounce_shot_chance_pct')),
        _get(rows, _compat_canon('tower_bounce_shot_targets')),
        _get_first(rows, [_compat_mech('module.astral_deliverance.bounce_bonus_per_hop'), _compat_mech('module.astral_deliverance.multiplier_per_bounce'), _compat_mech('module.astral_deliverance.multiplier')], 0.0),
    )
    rapidfire_factor = _ep_rapidfire_factor(_get(rows, _compat_canon('tower_rapid_fire_chance_pct')), _get(rows, _compat_canon('tower_rapid_fire_duration_seconds')), bps)
    range_dpm_factor = _ep_rangedpm(rng, dpm, kill_at_range)
    if attack_dissonance_active:
        multishot_factor = 1.0
        bounce_factor = 1.0
        rapidfire_factor = 1.0
        range_dpm_factor = 1.0

    sl_quantity = _get_first(rows, ['state::uw.spotlight.count', _compat_mech('uw.spotlight.count'), _compat_runtime('uw.spotlight.count'), _compat_mech('uw.spotlight.quantity'), _compat_runtime('uw.spotlight.quantity')], 0.0)
    sl_angle = _get_first(rows, [_compat_mech('uw.spotlight.angle_degrees'), _compat_runtime('uw.spotlight.angle_degrees'), _compat_canon('uw.spotlight.angle_degrees')], 0.0)
    sl_light_range = _get_first(rows, [_compat_mech('uw.spotlight.light_range_bonus'), _compat_runtime('uw.spotlight.light_range_bonus')], 0.0)
    spotlight_light_range_factor = _stat_uw_sl_final_lr(sl_light_range, range_dpm_factor)
    sl_bonus = _stat_uw_sl_final_dmg(
        _get_first(rows, ['state::uw.spotlight.bonus_multiplier', _compat_mech('uw.spotlight.bonus_multiplier'), _compat_runtime('uw.spotlight.bonus_multiplier'), _compat_mech('uw.spotlight.damage_multiplier'), _compat_runtime('uw.spotlight.damage_multiplier')], 1.0),
        spotlight_light_range_factor,
        _get_first(rows, [_compat_mech('uw.spotlight.damage_substat'), _compat_runtime('uw.spotlight.damage_substat')], 0.0),
        _get_first(rows, [_compat_mech('uw.spotlight.relic_bonus')], 0.0),
        _get_first(rows, [_compat_mech('uw.spotlight.vault_bonus')], 0.0),
        _bool(rows, [_compat_runtime('perk.spotlight_damage.active')], False),
    )
    spotlight_coverage = _ep_sl_coverage(sl_quantity, sl_angle) if sl_quantity > 0 and sl_angle > 0 else 0.0
    spotlight_factor = _ep_sl_final_bonus(spotlight_coverage, sl_bonus) if spotlight_coverage > 0 else 1.0
    if ultimate_weapons_dissonance_active:
        sl_quantity = 0.0
        sl_angle = 0.0
        spotlight_light_range_factor = 1.0
        sl_bonus = 1.0
        spotlight_coverage = 0.0
        spotlight_factor = 1.0

    super_tower_factor = _ep_super_tower_effective_bonus(
        _bool(rows, [_compat_runtime('cards.super_tower.active'), _compat_mech('cards.super_tower.active')], False),
        _bool(rows, [_compat_runtime('cards.super_tower.mastery_active'), _compat_mech('cards.super_tower.mastery_active')], False),
        _get_first(rows, [_compat_runtime('cards.super_tower.bonus_multiplier'), _compat_mech('cards.super_tower.bonus_multiplier')], 1.0),
        _get_first(rows, [_compat_runtime('cards.super_tower.cooldown_seconds'), _compat_mech('cards.super_tower.cooldown_seconds')], 1.0),
        sl_quantity > 0 and sl_angle > 0,
        sl_quantity,
        sl_angle,
    )
    rend_factor = _ep_maxrend(
        _bool(rows, [_compat_runtime('rend.active'), _compat_mech('rend.active')], False),
        _get_first(rows, [_compat_runtime('rend.lab_level'), _compat_mech('rend.lab_level')], 0.0),
        _get_first(rows, [_compat_runtime('rend.substat'), _compat_mech('rend.substat')], 0.0),
        _get_first(rows, [_compat_runtime('rend.enhancement_level'), _compat_mech('rend.enhancement_level')], 0.0),
    )
    if attack_dissonance_active:
        rend_factor = 1.0
    bullet_pipeline_factor = multishot_factor * bounce_factor * bps * rapidfire_factor * range_dpm_factor * super_tower_factor * rend_factor

    multi_rapid_bounce = multishot_factor * bounce_factor * rapidfire_factor

    has_aoe_card = _bool(rows, [_compat_runtime('cards.aoe.active'), _compat_mech('cards.aoe.active')], False)
    aoe_card_level = _get_first(rows, [_compat_runtime('cards.aoe.level'), _compat_mech('cards.aoe.level')], 0.0)

    dw = _ep_dw_dps(
        _bool(rows, [_compat_runtime('uw.death_wave.active'), _compat_mech('uw.death_wave.active')], default=_get_first(rows, [_compat_mech('uw.death_wave.damage_multiplier'), _compat_runtime('uw.death_wave.damage_multiplier')], 0.0) > 0.0),
        _get_first(rows, ['support_surface::uw.death_wave.final_damage', _compat_mech('uw.death_wave.damage_multiplier'), _compat_runtime('uw.death_wave.damage_multiplier')], 0.0),
        _get_first(rows, ['support_surface::uw.death_wave.final_quantity', 'state::uw.death_wave.effect_wave_count', _compat_mech('uw.death_wave.effect_wave_count'), _compat_runtime('uw.death_wave.effect_wave_count'), _compat_mech('uw.death_wave.quantity'), _compat_runtime('uw.death_wave.quantity')], 0.0),
        _get_first(rows, ['support_surface::uw.death_wave.final_cooldown_seconds', _compat_mech('uw.death_wave.cooldown_seconds'), _compat_runtime('uw.death_wave.cooldown_seconds')], 1.0),
        _get_first(rows, ['support_surface::uw.death_wave.damage_amp', _compat_mech('uw.death_wave.damage_amp'), _compat_runtime('uw.death_wave.damage_amp')], 0.0),
    )
    cl = _ep_cl_dps(
        _get_first(rows, ['support_surface::uw.chain_lightning.final_damage', _compat_mech('uw.chain_lightning.damage_multiplier'), _compat_runtime('uw.chain_lightning.damage_multiplier')], 0.0),
        _get_first(rows, ['support_surface::uw.chain_lightning.final_quantity', _compat_mech('uw.chain_lightning.quantity'), _compat_runtime('uw.chain_lightning.quantity')], 0.0),
        _get_first(rows, ['support_surface::uw.chain_lightning.final_chance', _compat_mech('uw.chain_lightning.chance_pct'), _compat_runtime('uw.chain_lightning.chance_pct')], 0.0),
        multi_rapid_bounce,
        bps,
    )

    sm_damage = _get_first(rows, ['support_surface::uw.smart_missiles.final_damage', _compat_mech('uw.smart_missiles.damage_multiplier'), _compat_runtime('uw.smart_missiles.damage_multiplier')], 0.0)
    sm_quantity = _get_first(rows, ['support_surface::uw.smart_missiles.final_quantity', _compat_mech('uw.smart_missiles.quantity'), _compat_runtime('uw.smart_missiles.quantity')], 0.0)
    sm_cooldown = _get_first(rows, ['support_surface::uw.smart_missiles.final_cooldown_seconds', _compat_mech('uw.smart_missiles.cooldown_seconds'), _compat_runtime('uw.smart_missiles.cooldown_seconds')], 1.0)
    sm_coverfire_time = _get_first(rows, ['support_surface::uw.smart_missiles.cover_fire_time_seconds', _compat_mech('uw.smart_missiles.cover_fire_time_seconds'), _compat_runtime('uw.smart_missiles.cover_fire_time_seconds')], 0.0)
    sm_coverfire = _get_first(rows, ['support_surface::uw.smart_missiles.cover_fire_dps'], 0.0)
    if sm_coverfire <= 0.0 and sm_coverfire_time > 0.0:
        sm_coverfire = sm_damage / sm_coverfire_time
    sm_heat = _get_first(rows, ['support_surface::uw.smart_missiles.heat_multiplier', _compat_mech('uw.smart_missiles.heat_multiplier'), _compat_runtime('uw.smart_missiles.heat_multiplier')], 1.0)
    sm_aoe = _get_first(rows, ['support_surface::uw.smart_missiles.aoe_multiplier', _compat_mech('uw.smart_missiles.aoe_multiplier'), _compat_runtime('uw.smart_missiles.aoe_multiplier')], 1.0)
    sm = _ep_sm_dps(sm_damage, sm_quantity, sm_cooldown, sm_coverfire, sm_heat, sm_aoe, has_aoe_card, aoe_card_level)

    slm = _ep_slm_dps(
        sm_damage if sm_damage > 0.0 else _get_first(rows, ['support_surface::uw.smart_missiles.final_damage_fallback'], 10.0),
        sl_bonus,
        sm_cooldown if sm_cooldown > 0.0 else max(1e-9, 20.0 - _get_first(rows, ['support_surface::uw.smart_missiles.cooldown_reduction_seconds'], 0.0)),
        sm_heat,
        sm_aoe,
        has_aoe_card,
        aoe_card_level,
    ) if _bool(rows, [_compat_runtime('uw.spotlight.active'), _compat_mech('uw.spotlight.active')], default=sl_quantity > 0.0 and sl_angle > 0.0) and _bool(rows, [_compat_runtime('uw.smart_missiles.active'), _compat_mech('uw.smart_missiles.active')], default=sm_damage > 0.0) else 0.0

    ps_damage = _get_first(rows, ['support_surface::uw.poison_swamp.damage', _compat_mech('uw.poison_swamp.damage_multiplier'), _compat_runtime('uw.poison_swamp.damage_multiplier')], 0.0)
    ps_duration = _get_first(rows, ['support_surface::uw.poison_swamp.duration_seconds', _compat_mech('uw.poison_swamp.duration_seconds'), _compat_runtime('uw.poison_swamp.duration_seconds')], 0.0)
    ps_cooldown = _get_first(rows, ['support_surface::uw.poison_swamp.cooldown_seconds', _compat_mech('uw.poison_swamp.cooldown_seconds'), _compat_runtime('uw.poison_swamp.cooldown_seconds')], 1.0)
    ps_deathcreep = _get_first(rows, ['support_surface::uw.poison_swamp.death_creep_multiplier', _compat_mech('uw.poison_swamp.death_creep_multiplier'), _compat_runtime('uw.poison_swamp.death_creep_multiplier')], 1.0)
    ps_rend = _get_first(rows, ['support_surface::uw.poison_swamp.rend_multiplier'], 0.0)
    if ps_rend <= 0.0:
        ps_rend = 1.0 + max(0.0, rend_factor) * _get_first(rows, ['support_surface::uw.poison_swamp.rend_scalar', _compat_mech('uw.poison_swamp.rend_scalar')], 0.0)
    ps = _ep_ps_dps(
        _bool(rows, [_compat_runtime('uw.poison_swamp.active'), _compat_mech('uw.poison_swamp.active')], default=ps_damage > 0.0),
        ps_damage,
        ps_duration,
        ps_cooldown,
        ps_deathcreep,
        ps_rend,
        has_aoe_card,
        aoe_card_level,
    )

    ilm_quantity = _get_first(rows, ['support_surface::uw.inner_land_mines.final_quantity', _compat_mech('uw.inner_land_mines.quantity'), _compat_runtime('uw.inner_land_mines.quantity')], 0.0)
    ilm_cooldown = _get_first(rows, ['support_surface::uw.inner_land_mines.cooldown_seconds', _compat_mech('uw.inner_land_mines.cooldown_seconds'), _compat_runtime('uw.inner_land_mines.cooldown_seconds')], 1.0)
    ilm_spawn_per_second = ilm_quantity / max(ilm_cooldown, 1e-9)
    sd_chance = _get_first(rows, ['support_surface::uw.inner_land_mines.space_displacer_spawn_per_second'], 0.0)
    if sd_chance <= 0.0:
        sd_chance = _get_first(rows, [_compat_runtime('land_mine.spawn_per_second'), _compat_mech('land_mine.spawn_per_second')], 0.0) * _get_first(rows, [_compat_runtime('land_mine.chance'), _compat_mech('land_mine.chance')], 0.0) * _get_first(rows, [_compat_mech('module.space_displacer.spawn_multiplier'), _compat_mech('module.space_displacer.multiplier')], 0.0)
    chrono_jump = _get_first(rows, ['support_surface::uw.inner_land_mines.chrono_jump_multiplier', _compat_runtime('uw.chrono_jump.multiplier'), _compat_mech('uw.chrono_jump.multiplier')], 0.0) * _get_first(rows, ['support_surface::uw.inner_land_mines.chrono_jump_scalar'], 5.0)
    ilm_charged_mines = _get_first(rows, ['support_surface::uw.inner_land_mines.charged_mines', _compat_mech('uw.inner_land_mines.charged_mines'), _compat_runtime('uw.inner_land_mines.charged_mines')], 0.0)
    ilm = _ep_ilm_dps(
        _bool(rows, [_compat_runtime('uw.inner_land_mines.active'), _compat_mech('uw.inner_land_mines.active')], default=False),
        _get_first(rows, ['support_surface::uw.inner_land_mines.final_damage', _compat_mech('uw.inner_land_mines.damage_multiplier'), _compat_runtime('uw.inner_land_mines.damage_multiplier')], 0.0),
        ilm_spawn_per_second + sd_chance,
        chrono_jump,
        ilm_charged_mines,
        _get_first(rows, ['support_surface::uw.inner_land_mines.aoe_multiplier', _compat_mech('uw.inner_land_mines.aoe_multiplier'), _compat_runtime('uw.inner_land_mines.aoe_multiplier')], 1.0),
        has_aoe_card,
        aoe_card_level,
    )
    if ultimate_weapons_dissonance_active:
        dw = 0.0
        cl = 0.0
        sm = 0.0
        slm = 0.0
        ps = 0.0
        ilm = 0.0
        sm_heat = 1.0
        ps_deathcreep = 1.0
        ilm_charged_mines = 0.0
    uw_dissonance_factor = _dissonance_total_multiplier(rows, 'ultimate_weapons')
    uw_damage_boost = 1.0 if ultimate_weapons_dissonance_active else _get_first(rows, ['state::tower.ultimate_damage_multiplier', 'support_surface::uw.total_damage_boost_multiplier', _compat_canon('ultimate_damage_multiplier'), _compat_mech('uw.damage_boost_multiplier')], 1.0) * uw_dissonance_factor
    st_uw_mastery = _get_first(
        rows,
        [
            'support_surface::uw.super_tower_effective_uw_bonus',
            _compat_runtime('cards.super_tower.uw_mastery_multiplier'),
            _compat_mech('cards.super_tower.uw_mastery_multiplier'),
        ],
        1.0,
    )
    uw_total_damage = _ep_uw_total_damage(dw, cl, sm, slm, spotlight_factor, ps, ilm, uw_damage_boost, st_uw_mastery, uw_crit_card_factor)

    project_funding_pct = _get_first(
        rows,
        [
            'state::module.project_funding.cash_digit_multiplier_pct',
            _compat_mech('module.project_funding.cash_digit_multiplier_pct'),
        ],
        0.0,
    )
    project_funding_cash = _get_first(rows, ['support_surface::module.project_funding.current_cash'], 0.0)
    project_funding_factor = 1.0
    if not attack_dissonance_active and project_funding_pct > 0.0 and project_funding_cash > 0.0:
        project_funding_factor = max(1.0, 1.0 + math.log10(project_funding_cash) * _pct(project_funding_pct))

    slow_factor = _get_first(rows, ['support_surface::chrono_field.exposure_multiplier'], 0.0)
    if slow_factor <= 0.0:
        cf_slow_pct = _get_first(rows, [_compat_mech('uw.chrono_field.slow_pct'), _compat_runtime('uw.chrono_field.slow_pct')], 0.0)
        slow_factor = 1.0
        if cf_slow_pct > 0.0:
            slow_factor *= 1.0 / max(1.0 - min(0.90, _pct(cf_slow_pct)), 0.1)
    cf_plus_multiplier = _get_first(rows, ['support_surface::chrono_field.plus_exposure_multiplier', _compat_mech('uw.chrono_field.plus_exposure_multiplier')], 1.0)
    slow_factor *= cf_plus_multiplier
    if ultimate_weapons_dissonance_active:
        cf_plus_multiplier = 1.0
        slow_factor = 1.0

    shock_stack_factor = 1.0
    shock_damage_multiplier = _get_first(rows, ['state::shock.damage_multiplier', _compat_mech('shock.damage_multiplier')], 0.0)
    shock_max_stacks = _get_first(rows, ['state::module.dimension_core.max_shock_stacks', _compat_mech('module.dimension_core.max_shock_stacks')], 0.0)
    if shock_damage_multiplier > 1.0 and shock_max_stacks > 0.0:
        shock_stack_factor = 1.0 + max(0.0, shock_damage_multiplier - 1.0) * 2.0 * shock_max_stacks

    edamage = base_damage_stack * (bullet_crit_factor * bullet_pipeline_factor * spotlight_factor + uw_total_damage * uw_crit_factor) * slow_factor * shock_stack_factor * project_funding_factor

    _publish(rows, 'derived::edamage.base_damage_stack', base_damage_stack, 'scalar', [_contributor(rows, _compat_canon('tower_damage'), 'edamage.base_damage_stack')], 'EP EM5 DC5-like base damage stack [EP helper support surface]')
    _publish(rows, 'derived::edamage.berserker_bonus_multiplier', berserker_bonus_multiplier, 'multiplier', [_contributor(rows, 'state::cards.berserker.assumed_bonus_multiplier', 'edamage.berserker_bonus_multiplier')], 'Explicit Berserker full-stack bonus multiplier assumption [EP helper support surface]')
    _publish(rows, 'derived::edamage.berserker_factor', berserker_factor, 'multiplier', [_contributor(rows, 'state::cards.berserker.assumed_bonus_multiplier', 'edamage.berserker_factor')], 'Explicit Berserker full-stack factor applied to projected eDamage [EP helper support surface]')
    _publish(rows, 'derived::edamage.attack_dissonance_factor', attack_dissonance_factor, 'multiplier', [_contributor(rows, 'derived::dissonance.attack.total_multiplier', 'edamage.attack_dissonance_factor')], 'v28 Attack Dissonance/Echo multiplier; not applied during an active Attack Dissonant Run because EP restricts that branch to ACP * Amp Strike.')
    _publish(rows, 'derived::edamage.attack_dissonance_restricted', 1.0 if attack_dissonance_active else 0.0, 'bool', [_contributor(rows, 'support_surface::dissonance.attack_run_active', 'edamage.attack_dissonance_restricted')], 'v28 Attack Dissonant Run branch: damage stack is ACP * Amp Strike, crits/projectile multipliers/range/DPM/rend are forced to EP restricted values.')
    _publish(rows, 'derived::edamage.defense_dissonance_shockwave_restricted', 1.0 if defense_dissonance_active else 0.0, 'bool', [_contributor(rows, 'support_surface::dissonance.defense_run_active', 'edamage.defense_dissonance_shockwave_restricted')], 'v28 Defense Dissonant Run branch: defensive Shockwave is disabled, so the Anti-Cube Portal shockwave damage factor is neutralized.')
    _publish(rows, 'derived::edamage.acp_factor', acp_factor, 'multiplier', [_contributor(rows, 'state::module.anti_cube_portal.shockwave_damage_taken_mult_x', 'edamage.acp_factor')], 'EP EPD_SHOCKWAVE_DAMAGE-aligned ACP factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.bullet_crit_factor', bullet_crit_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_crit_chance_pct'), 'edamage.bullet_crit_factor'), _contributor(rows, _compat_canon('tower_supercrit_chance_pct'), 'edamage.bullet_crit_factor')], 'EPD_CRITICAL-aligned bullet crit factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw_crit_card_factor', uw_crit_card_factor, 'multiplier', [_contributor(rows, 'state::cards.ultimate_crit.chance_pct', 'edamage.uw_crit_card_factor'), _contributor(rows, _compat_canon('tower_crit_multiplier'), 'edamage.uw_crit_card_factor')], 'Ultimate Crit card factor applied to aggregate UW damage [EP helper support surface]')
    _publish(rows, 'derived::edamage.bullet_per_second', bps, 'rate', [_contributor(rows, _compat_canon('tower_attack_speed'), 'edamage.bullet_per_second')], 'EP BULLET_PER_SECOND from mechanics lineage [EP helper support surface]')
    _publish(rows, 'derived::edamage.multishot_factor', multishot_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_multishot_chance_pct'), 'edamage.multishot_factor'), _contributor(rows, _compat_canon('tower_multishot_targets'), 'edamage.multishot_factor')], 'EPD_MULTISHOT-aligned multishot factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.bounce_factor', bounce_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_bounce_shot_chance_pct'), 'edamage.bounce_factor'), _contributor(rows, _compat_canon('tower_bounce_shot_targets'), 'edamage.bounce_factor')], 'EPD_BOUNCESHOT-aligned bounce factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.rapidfire_factor', rapidfire_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_rapid_fire_chance_pct'), 'edamage.rapidfire_factor'), _contributor(rows, _compat_canon('tower_rapid_fire_duration_seconds'), 'edamage.rapidfire_factor')], 'EPD_RAPIDFIRE-aligned rapidfire factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.range_dpm_factor', range_dpm_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_damage_per_meter_multiplier'), 'edamage.range_dpm_factor'), _contributor(rows, _compat_canon('tower_range_m'), 'edamage.range_dpm_factor')], 'EPD_RANGEDPM-aligned range x dpm x kill-at-range factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.spotlight_light_range_factor', spotlight_light_range_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.spotlight.light_range'), 'edamage.spotlight_light_range_factor')], 'EP spotlight light-range factor before coverage/final bonus [EP helper support surface]')
    _publish(rows, 'derived::edamage.spotlight_bonus_term', sl_bonus, 'multiplier', [_contributor(rows, _compat_mech('uw.spotlight.damage_multiplier'), 'edamage.spotlight_bonus_term')], 'EP spotlight bonus term before coverage [EP helper support surface]')
    _publish(rows, 'derived::edamage.spotlight_coverage', spotlight_coverage, 'ratio', [_contributor(rows, _compat_mech('uw.spotlight.quantity'), 'edamage.spotlight_coverage'), _contributor(rows, _compat_mech('uw.spotlight.angle_degrees'), 'edamage.spotlight_coverage')], 'EP spotlight coverage from quantity and angle [EP helper support surface]')
    _publish(rows, 'derived::edamage.super_tower_factor', super_tower_factor, 'multiplier', [_contributor(rows, _compat_runtime('cards.super_tower.bonus_multiplier'), 'edamage.super_tower_factor')], 'EPD_SUPERTOWER_EFFECTIVE_BONUS-aligned factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.rend_factor', rend_factor, 'multiplier', [_contributor(rows, _compat_runtime('rend.lab_level'), 'edamage.rend_factor')], 'EPD_MAXREND-aligned rend factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.bullet_pipeline_factor', bullet_pipeline_factor, 'scalar', [_contributor(rows, _compat_canon('tower_attack_speed'), 'edamage.bullet_pipeline_factor')], 'EP EM5 DV5-like bullet pipeline factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.spotlight_factor', spotlight_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.spotlight.damage_multiplier'), 'edamage.spotlight_factor')], 'EP spotlight final bonus with quantity and angle coverage [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw.death_wave_dps', dw, 'scalar', [_contributor(rows, _compat_mech('uw.death_wave.damage_multiplier'), 'edamage.uw.death_wave_dps')], 'EP_DW_DPS-like death wave DPS [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw.chain_lightning_dps', cl, 'scalar', [_contributor(rows, _compat_mech('uw.chain_lightning.damage_multiplier'), 'edamage.uw.chain_lightning_dps')], 'EP_CL_DPS-like chain lightning DPS [EP helper support surface]')
    _publish(rows, 'derived::edamage_boss', cl, 'scalar', [_contributor(rows, 'derived::edamage.uw.chain_lightning_dps', 'edamage_boss')], 'TowerSim Boss Waves base damage surface: confirmed constant Chain Lightning boss DPS before scenario/loadout exposure factors.')
    _publish(rows, 'derived::edamage.boss_applicable_dps_cl_only', cl, 'scalar', [_contributor(rows, 'derived::edamage_boss', 'edamage.boss_applicable_dps_cl_only')], 'Compatibility alias for derived::edamage_boss during Boss Waves damage-surface migration.')
    _publish(rows, 'derived::edamage.uw.smart_missiles_heatup_factor', sm_heat, 'multiplier', [_contributor(rows, _compat_mech('uw.smart_missiles.heat_multiplier'), 'edamage.uw.smart_missiles_heatup_factor')], 'Smart Missiles heatup multiplier used by the EP Smart Missile and Spotlight Missile helper branches.')
    _publish(rows, 'derived::edamage.uw.smart_missiles_dps', sm, 'scalar', [_contributor(rows, _compat_mech('uw.smart_missiles.damage_multiplier'), 'edamage.uw.smart_missiles_dps')], 'smart missiles DPS or proxy [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw.spotlight_missiles_dps', slm, 'scalar', [_contributor(rows, _compat_mech('uw.spotlight_missiles.damage_multiplier'), 'edamage.uw.spotlight_missiles_dps')], 'spotlight missiles DPS or proxy [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw.poison_swamp_death_creep_factor', ps_deathcreep, 'multiplier', [_contributor(rows, _compat_mech('uw.poison_swamp.death_creep_multiplier'), 'edamage.uw.poison_swamp_death_creep_factor')], 'Poison Swamp Death Creep multiplier used by the EP Poison Swamp helper branch.')
    _publish(rows, 'derived::edamage.uw.poison_swamp_dps', ps, 'scalar', [_contributor(rows, _compat_mech('uw.poison_swamp.damage_multiplier'), 'edamage.uw.poison_swamp_dps')], 'poison swamp DPS or proxy [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw.ilm_charged_mines_factor', ilm_charged_mines, 'multiplier', [_contributor(rows, _compat_mech('uw.inner_land_mines.charged_mines'), 'edamage.uw.ilm_charged_mines_factor')], 'Inner Land Mines Charged Mines heat multiplier used by the EP ILM helper branch.')
    _publish(rows, 'derived::edamage.uw.ilm_dps', ilm, 'scalar', [_contributor(rows, _compat_mech('uw.inner_land_mines.damage_multiplier'), 'edamage.uw.ilm_dps')], 'EP_ILM_DPS-like inner land mine DPS including Space Displacer contribution [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw_dissonance_factor', uw_dissonance_factor, 'multiplier', [_contributor(rows, 'derived::dissonance.ultimate_weapons.total_multiplier', 'edamage.uw_dissonance_factor')], 'v28 Ultimate Weapon Dissonance/Echo multiplier applied to the UW damage boost path.')
    _publish(rows, 'derived::edamage.uw_total_damage', uw_total_damage, 'scalar', [_contributor(rows, _compat_mech('uw.chain_lightning.damage_multiplier'), 'edamage.uw_total_damage')], 'EP_UW_TOTAL_DAMAGE-like aggregate UW damage [EP helper support surface]')
    _publish(rows, 'derived::edamage.uw_crit_factor', uw_crit_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_crit_chance_pct'), 'edamage.uw_crit_factor')], 'EPD_UWCRITICAL-aligned UW crit factor [EP helper support surface]')
    _publish(rows, 'derived::edamage.chrono_field_plus_factor', cf_plus_multiplier, 'multiplier', [_contributor(rows, _compat_mech('uw.chrono_field.plus_exposure_multiplier'), 'edamage.chrono_field_plus_factor')], 'Chrono Field+ exposure multiplier applied to the EP slow factor.')
    _publish(rows, 'derived::edamage.slow_factor', slow_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.chrono_field.slow_pct'), 'edamage.slow_factor')], 'EP Chrono Field slow exposure multiplier [EP helper support surface]')
    _publish(rows, 'derived::edamage.shock_stack_factor', shock_stack_factor, 'multiplier', [_contributor(rows, 'state::shock.damage_multiplier', 'edamage.shock_stack_factor'), _contributor(rows, 'state::module.dimension_core.max_shock_stacks', 'edamage.shock_stack_factor')], 'Dimension Core additive shock-stack factor from module runtime contract.')
    _publish(rows, 'derived::edamage.project_funding_factor', project_funding_factor, 'multiplier', [_contributor(rows, 'state::module.project_funding.cash_digit_multiplier_pct', 'edamage.project_funding_factor'), _contributor(rows, 'support_surface::module.project_funding.current_cash', 'edamage.project_funding_factor')], 'Project Funding runtime multiplier from current cash; applied at objective level so EP base-stack helper surfaces remain comparable.')
    _publish(rows, 'derived::edamage_ep_helper.dx_spotlight_light_range_factor', spotlight_light_range_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.spotlight.light_range'), 'edamage.ep_dx_spotlight_light_range_factor')], 'EP eDamage DX5 spotlight light-range factor alias [EP helper support surface]')
    _publish(rows, 'derived::edamage_ep_helper.dx_spotlight_bonus_term', sl_bonus, 'multiplier', [_contributor(rows, _compat_mech('uw.spotlight.damage_multiplier'), 'edamage.ep_dx_spotlight_bonus_term')], 'EP eDamage DX5 spotlight bonus term alias [EP helper support surface]')
    _publish(rows, 'derived::edamage_ep_helper.dx_spotlight_coverage', spotlight_coverage, 'ratio', [_contributor(rows, _compat_mech('uw.spotlight.quantity'), 'edamage.ep_dx_spotlight_coverage'), _contributor(rows, _compat_mech('uw.spotlight.angle_degrees'), 'edamage.ep_dx_spotlight_coverage')], 'EP eDamage DX5 spotlight coverage alias [EP helper support surface]')
    _publish(rows, 'derived::edamage_ep_helper.dc_base_damage_stack', base_damage_stack, 'scalar', [_contributor(rows, _compat_canon('tower_damage'), 'edamage_ep_helper.dc_base_damage_stack')], 'EP eDamage DC5 base damage stack alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep_helper.di_bullet_crit_factor', bullet_crit_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_crit_chance_pct'), 'edamage_ep_helper.di_bullet_crit_factor')], 'EP eDamage DI5 bullet crit factor alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep_helper.dj_uw_crit_factor', uw_crit_factor, 'multiplier', [_contributor(rows, _compat_canon('tower_crit_chance_pct'), 'edamage_ep_helper.dj_uw_crit_factor')], 'EP eDamage DJ5 UW crit factor alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep_helper.dj1_uw_crit_card_factor', uw_crit_card_factor, 'multiplier', [_contributor(rows, 'state::cards.ultimate_crit.chance_pct', 'edamage_ep_helper.dj1_uw_crit_card_factor')], 'EP eDamage DJ1 Ultimate Crit card factor alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep_helper.dv_bullet_pipeline_factor', bullet_pipeline_factor, 'scalar', [_contributor(rows, _compat_canon('tower_attack_speed'), 'edamage_ep_helper.dv_bullet_pipeline_factor')], 'EP eDamage DV5 bullet pipeline factor alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep_helper.ei_uw_total_damage', uw_total_damage, 'scalar', [_contributor(rows, _compat_mech('uw.chain_lightning.damage_multiplier'), 'edamage_ep_helper.ei_uw_total_damage')], 'EP eDamage EI5 total UW damage alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep_helper.el_slow_factor', slow_factor, 'multiplier', [_contributor(rows, _compat_mech('uw.chrono_field.slow_pct'), 'edamage_ep_helper.el_slow_factor')], 'EP eDamage EL5 slow factor alias [EP helper surface]')
    _publish(rows, 'derived::edamage_ep', edamage, 'scalar', [_contributor(rows, _compat_canon('tower_damage'), 'edamage_ep')], 'Exact Effective Paths eDamage objective line')
    _publish(rows, 'derived::edamage', edamage, 'scalar', [_contributor(rows, 'derived::edamage_ep', 'edamage')], 'Compatibility alias for derived::edamage_ep; do not treat as an independent TowerSim-native damage model.')

    # eEcon: closer to EP DI5 structure (CL * CM * DC * DG * DH)
    adstarter_theme_relic_factor = _get_first(rows, ['support_surface::eecon.adstarter_theme_relic_factor', 'support_surface::eecon.base_meta_factor'], 1.0)
    cpk_source_keys = [
        'support_surface::eecon.cpk_factor',
        'state::economy.coins_per_kill_bonus',
        'state::economy.coin_kill_multiplier',
        _compat_canon('coins_per_kill_bonus'),
        _compat_canon('coin_kill_multiplier'),
        'support_surface::eecon.coin_kill_ws',
    ]
    cpk_source_row = next((row for key in cpk_source_keys if (row := _row(rows, key)) is not None and row.final_value is not None), None)
    cpk_contributor_key = cpk_source_row.stat_name if cpk_source_row is not None else 'state::economy.coins_per_kill_bonus'
    cpk_factor = _get_first(rows, ['support_surface::eecon.cpk_factor'], 0.0)
    if cpk_factor <= 0.0:
        cpk_factor = _ep_cpk(
            _get_first(rows, cpk_source_keys[1:], 0.0),
            _get_first(rows, ['support_surface::eecon.coin_kill_lab_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.stone_sac_pct'], 0.0),
            _get_first(rows, ['support_surface::eecon.lab_sac_pct'], 0.0),
            _get_first(rows, ['support_surface::eecon.coin_kill_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.coin_kill_ass_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.workshop_enhancement_level'], 0.0),
            _bool(rows, ['support_surface::eecon.coin_perk_active'], False),
            _get_first(rows, ['support_surface::eecon.standard_perks_bonus_level'], 0.0),
            _bool(rows, ['support_surface::eecon.cto_active'], False),
            _get_first(rows, ['support_surface::eecon.ito_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.coin_vault_pct'], 0.0),
        )
    if cpk_source_row is None:
        coin_kill_contributors = [_contributor(rows, cpk_contributor_key, 'eecon')]
        _publish(rows, 'derived::eecon.base_meta_factor', adstarter_theme_relic_factor, 'multiplier', [], 'ad starter / theme / relic factor [EP helper support surface]')
        _publish_unresolved(rows, 'derived::eecon.cpk_factor', 'multiplier', coin_kill_contributors, 'Blocked: v28 eEcon requires a resolved coin-kill source; missing/null coin-kill must not publish as zero.')
        _publish_unresolved(rows, 'derived::eecon.base_coin_income', 'scalar', coin_kill_contributors, 'Blocked: v28 eEcon base income requires resolved coin-kill input.')
        _publish_unresolved(rows, 'derived::eecon', 'scalar', coin_kill_contributors, 'Blocked: v28 eEcon requires resolved coin-kill input instead of silently publishing zero.')
        _publish_unresolved(rows, 'derived::eecon_ep', 'scalar', coin_kill_contributors, 'Blocked: v28 EP eEcon requires resolved coin-kill input instead of silently publishing zero.')
        return
    freeup_factor = _get_first(rows, ['support_surface::eecon.freeup_factor'], 0.0)
    if freeup_factor <= 0.0:
        has_freeup = _bool(rows, ['support_surface::eecon.freeup_enabled'], default=bool(_get_first(rows, ['support_surface::eecon.freeup_percent'], 0.0)))
        freeup_pct = _get_first(rows, ['support_surface::eecon.freeup_percent'], 0.0)
        if freeup_pct <= 0.0:
            freeup_pct = _pct_surface_ratio(
                rows,
                ['state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct'],
            )
            has_freeup = has_freeup or freeup_pct > 0.0
        if not has_freeup or freeup_pct == 0.0:
            freeup_factor = 1.0
        else:
            freeup_att = _pct_surface_ratio(rows, ['state::tower.free_attack_upgrade_chance_pct'])
            freeup_def = _pct_surface_ratio(rows, ['state::tower.free_defense_upgrade_chance_pct'])
            freeup_uti = _pct_surface_ratio(rows, ['state::tower.free_utility_upgrade_chance_pct'])
            if freeup_att <= 0.0 and freeup_def <= 0.0 and freeup_uti <= 0.0:
                freeup_att = _ep_fup(
                    _get_first(rows, ['support_surface::eecon.freeup_attack_ws'], 0.0),
                    _bool(rows, ['support_surface::eecon.freeup_card_active'], False),
                    _get_first(rows, ['support_surface::eecon.freeup_card_value'], 0.0),
                    _bool(rows, ['support_surface::eecon.freeup_perk_active'], False),
                    _get_first(rows, ['support_surface::eecon.standard_perks_bonus_level'], 0.0),
                    _get_first(rows, ['support_surface::eecon.stone_sac_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.lab_sac_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_attack_prim_sub'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_attack_ass_sub'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_wse_level'], _get_first(rows, ['support_surface::eecon.workshop_enhancement_level'], 0.0)),
                    _get_first(rows, ['support_surface::eecon.freeup_attack_relic_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_attack_vault_pct'], 0.0),
                )
                freeup_def = _ep_fup(
                    _get_first(rows, ['support_surface::eecon.freeup_defense_ws'], 0.0),
                    _bool(rows, ['support_surface::eecon.freeup_card_active'], False),
                    _get_first(rows, ['support_surface::eecon.freeup_card_value'], 0.0),
                    _bool(rows, ['support_surface::eecon.freeup_perk_active'], False),
                    _get_first(rows, ['support_surface::eecon.standard_perks_bonus_level'], 0.0),
                    _get_first(rows, ['support_surface::eecon.stone_sac_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.lab_sac_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_defense_prim_sub'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_defense_ass_sub'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_wse_level'], _get_first(rows, ['support_surface::eecon.workshop_enhancement_level'], 0.0)),
                    _get_first(rows, ['support_surface::eecon.freeup_defense_relic_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_defense_vault_pct'], 0.0),
                )
                freeup_uti = _ep_fup(
                    _get_first(rows, ['support_surface::eecon.freeup_utility_ws'], 0.0),
                    _bool(rows, ['support_surface::eecon.freeup_card_active'], False),
                    _get_first(rows, ['support_surface::eecon.freeup_card_value'], 0.0),
                    _bool(rows, ['support_surface::eecon.freeup_perk_active'], False),
                    _get_first(rows, ['support_surface::eecon.standard_perks_bonus_level'], 0.0),
                    _get_first(rows, ['support_surface::eecon.stone_sac_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.lab_sac_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_utility_prim_sub'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_utility_ass_sub'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_wse_level'], _get_first(rows, ['support_surface::eecon.workshop_enhancement_level'], 0.0)),
                    _get_first(rows, ['support_surface::eecon.freeup_utility_relic_pct'], 0.0),
                    _get_first(rows, ['support_surface::eecon.freeup_utility_vault_pct'], 0.0),
                )
            freeup = (freeup_att + freeup_def + freeup_uti) * freeup_pct
            has_ws = _bool(rows, ['support_surface::eecon.wave_skip_active'], _get_first(rows, ['state::cards.wave_skip.chance_pct', _compat_runtime('cards.wave_skip.chance_pct')], 0.0) > 0.0)
            ws_card = _get_first(rows, ['state::cards.wave_skip.chance_pct', _compat_runtime('cards.wave_skip.chance_pct')], 0.0)
            if ws_card > 1.0:
                ws_card /= 100.0
            ws_mastery = _bool(rows, ['support_surface::eecon.wave_skip_mastery_active'], False)
            ws_mastery_level = _get_first(rows, ['support_surface::eecon.wave_skip_mastery_level'], 0.0)
            freeup_factor = 1.0
            for skip in range(0, 11):
                freeup_factor += _epc_card_ws(skip, has_ws, ws_card, ws_mastery, ws_mastery_level) * freeup * (skip + 1)
    coin_card_factor = _get_first(rows, ['support_surface::eecon.coin_card_factor'], 0.0)
    if coin_card_factor <= 0.0:
        coin_card_factor = _ep_card_coins(
            _bool(rows, ['support_surface::eecon.coin_card_active'], _get_first(rows, ['state::economy.coins_multiplier', _compat_runtime('cards.coins.multiplier')], 0.0) != 0.0),
            _get_first(rows, ['state::economy.coins_multiplier', _compat_runtime('cards.coins.multiplier'), _compat_mech('cards.coins.multiplier')], 1.0),
            _bool(rows, ['support_surface::eecon.coin_card_mastery_active'], False),
            _get_first(rows, ['support_surface::eecon.coin_card_mastery_level'], 0.0),
        )
    module_factor = _get_first(rows, ['support_surface::eecon.module_factor'], 0.0)
    if module_factor <= 0.0:
        module_factor = _ep_module_bonus(
            _get_first(rows, [_compat_mech('module.generator.primary_coin_multiplier'), _compat_mech('module.generator.coin_multiplier')], 1.0),
            _bool(rows, [_compat_mech('module.generator.assist_enabled')], False),
            _get_first(rows, [_compat_mech('module.generator.assist_bonus_multiplier')], 1.0),
            _get_first(rows, [_compat_mech('module.generator.assist_stone_bonus_pct')], 0.0),
            _get_first(rows, [_compat_mech('module.generator.assist_lab_bonus_pct')], 0.0),
        )
    all_coin_bonus_contributors = [
        _contributor(rows, cpk_contributor_key, 'economy.all_coin_bonus_multiplier'),
        _contributor(rows, 'state::economy.coin_bonus_multiplier', 'economy.all_coin_bonus_multiplier'),
        _contributor(rows, 'state::economy.coins_multiplier', 'economy.all_coin_bonus_multiplier'),
        _contributor(rows, 'state::meta.cosmetic_bonus.theme_song_coin_multiplier', 'economy.all_coin_bonus_multiplier'),
        _contributor(rows, 'state::meta.account_context.coin_multiplier_display', 'economy.all_coin_bonus_multiplier'),
    ]
    broad_coin_bonus_factor = _get_first(rows, ['state::economy.coin_bonus_multiplier'], 0.0)
    all_coins_card_relic_factor = _get_first(rows, ['state::economy.coins_multiplier'], 0.0)
    theme_song_factor = _get_first(rows, ['state::meta.cosmetic_bonus.theme_song_coin_multiplier'], 0.0)
    account_coin_multiplier_factor = _parse_multiplier_token(_raw_surface_value(rows, ['state::meta.account_context.coin_multiplier_display']))
    all_coin_bonus_factor = 0.0
    if (
        broad_coin_bonus_factor > 0.0
        and cpk_factor > 0.0
        and all_coins_card_relic_factor > 0.0
        and theme_song_factor > 0.0
        and account_coin_multiplier_factor is not None
        and account_coin_multiplier_factor > 0.0
    ):
        all_coin_bonus_factor = (
            cpk_factor
            * broad_coin_bonus_factor
            * all_coins_card_relic_factor
            * theme_song_factor
            * account_coin_multiplier_factor
        )
        all_coin_bonus_core_factor = (
            broad_coin_bonus_factor
            * all_coins_card_relic_factor
            * theme_song_factor
            * account_coin_multiplier_factor
        )
        _publish(
            rows,
            'state::economy.all_coin_bonus_multiplier',
            all_coin_bonus_factor,
            'multiplier',
            all_coin_bonus_contributors,
            'EP-aligned all-coin display surface: Coins/Kill x Coin Bonus x Coins multiplier x theme/song coin multiplier x parsed account coin multiplier display. Premium flags are trace-only.',
        )
        _publish(
            rows,
            'derived::eecon.all_coin_bonus_core_factor',
            all_coin_bonus_core_factor,
            'multiplier',
            all_coin_bonus_contributors[1:],
            'All-coin core factor before Coins/Kill, retained to make the EP display composition auditable.',
        )
    else:
        _publish_unresolved(
            rows,
            'state::economy.all_coin_bonus_multiplier',
            'multiplier',
            all_coin_bonus_contributors,
            'Blocked: all-coin display surface requires resolved Coins/Kill, Coin Bonus, Coins multiplier, theme/song multiplier, and parsed account coin multiplier display.',
        )

    cl_factor = adstarter_theme_relic_factor * cpk_factor * freeup_factor * coin_card_factor * module_factor

    eom_factor = _get_first(rows, ['support_surface::eecon.eom_factor'], 0.0)
    if eom_factor <= 0.0:
        eom_factor = _ep_card_eom(
            _bool(rows, ['support_surface::eecon.eom_active'], False),
            _get_first(rows, ['support_surface::eecon.eom_mastery_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.eom_hit_pct'], 0.0),
        )

    sync_factor = _get_first(rows, ['support_surface::timing.combined_multiplier', 'support_surface::eecon.sync_factor'], 0.0)
    gt_gcomp_factor = _get_first(rows, ['support_surface::eecon.gcomp_factor'], 0.0)
    mvn_offset = _get_first(rows, ['support_surface::eecon.mvn_offset'], 0.0)
    gt_bonus_term = _get_first(rows, ['support_surface::eecon.gt_bonus', 'state::uw.golden_tower.bonus_multiplier'], 0.0)
    gt_duration_term = _get_first(rows, ['support_surface::eecon.gt_duration', 'state::uw.golden_tower.duration_seconds', 'state::uw.golden_tower.base_duration_seconds'], 0.0)
    gt_cd_term = _get_first(rows, ['support_surface::eecon.gt_cooldown', 'state::uw.golden_tower.cooldown_seconds', 'state::uw.golden_tower.base_cooldown_seconds'], 0.0)
    gt_gc_factor = _get_first(rows, ['support_surface::eecon.gt_gc_factor'], 0.0)
    bh_bonus_term = _get_first(rows, ['support_surface::eecon.bh_bonus', 'state::uw.black_hole.coin_bonus_multiplier'], 0.0)
    bh_duration_term = _get_first(rows, ['support_surface::eecon.bh_duration', 'state::uw.black_hole.duration_seconds', 'state::uw.black_hole.base_duration_seconds'], 0.0)
    bh_cd_term = _get_first(rows, ['support_surface::eecon.bh_cooldown', 'state::uw.black_hole.cooldown_seconds', 'state::uw.black_hole.base_cooldown_seconds'], 0.0)
    dw_bonus_term = _get_first(rows, ['support_surface::eecon.dw_bonus', 'state::uw.death_wave.coin_bonus_multiplier'], 0.0)
    dw_duration_term = _get_first(rows, ['support_surface::eecon.dw_duration', 'state::uw.death_wave.effect_wave_count'], 0.0)
    dw_cd_term = _get_first(rows, ['support_surface::eecon.dw_cooldown', 'state::uw.death_wave.cooldown_seconds'], 0.0)
    gb_bonus_term = _get_first(rows, ['support_surface::eecon.gb_bonus', 'state::bot.golden.bonus_multiplier'], 0.0)
    gb_duration_term = _get_first(rows, ['support_surface::eecon.gb_duration', 'state::bot.golden.duration_seconds'], 0.0)
    gb_cd_term = _get_first(rows, ['support_surface::eecon.gb_cooldown', 'state::bot.golden.cooldown_seconds'], 0.0)

    has_gt = _bool(rows, ['support_surface::eecon.gt_active', _compat_runtime('uw.golden_tower.active'), _compat_mech('uw.golden_tower.active')], gt_bonus_term > 0.0 or gt_duration_term > 0.0 or gt_cd_term > 0.0)
    has_bh = _bool(rows, ['support_surface::eecon.bh_active', _compat_runtime('uw.black_hole.active'), _compat_mech('uw.black_hole.active')], bh_bonus_term > 0.0 or bh_duration_term > 0.0 or bh_cd_term > 0.0)
    has_dw = _bool(rows, ['support_surface::eecon.dw_active', _compat_runtime('uw.death_wave.active'), _compat_mech('uw.death_wave.active')], dw_bonus_term > 0.0 or dw_duration_term > 0.0 or dw_cd_term > 0.0)
    has_gb = _bool(rows, ['support_surface::eecon.gb_active', _compat_runtime('uw.golden_bot.active'), _compat_mech('uw.golden_bot.active')], gb_bonus_term > 0.0 or gb_duration_term > 0.0 or gb_cd_term > 0.0)

    stone_sac = _get_first(rows, ['support_surface::eecon.stone_sac_pct'], 0.0)
    lab_sac = _get_first(rows, ['support_surface::eecon.lab_sac_pct'], 0.0)

    if gt_gcomp_factor <= 0.0:
        gt_gcomp_factor = _epc_gcomp(
            _get_first(rows, ['support_surface::eecon.recovery_package_chance_ws'], 0.0),
            _get_first(rows, ['support_surface::eecon.recovery_package_chance_lab_level'], 0.0),
            _bool(rows, ['support_surface::eecon.recovery_package_card_active'], False),
            _get_first(rows, ['support_surface::eecon.recovery_package_card_value'], 0.0),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.recovery_package_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.recovery_package_ass_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.package_after_boss_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.boss_wave'], 10.0),
            _get_first(rows, ['support_surface::eecon.gcomp_value'], 0.0),
            _get_first(rows, ['support_surface::eecon.wave_duration'], 120.0),
        )

    if gt_bonus_term <= 0.0:
        gt_bonus_term = _epc_gtb(
            _get_first(rows, ['support_surface::eecon.gt_stone_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.gt_lab_level'], 0.0),
            _bool(rows, ['support_surface::eecon.gt_perk_active'], False),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.gt_bonus_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.gt_bonus_ass_sub'], 0.0),
        )
    if gt_duration_term <= 0.0:
        gt_duration_term = _epc_gtd(
            _get_first(rows, ['support_surface::eecon.gt_duration_stone_level'], _get_first(rows, ['support_surface::eecon.gt_stone_level'], 0.0)),
            _get_first(rows, ['support_surface::eecon.gt_duration_lab_level', 'support_surface::eecon.gt_lab_level'], 0.0),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.gt_duration_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.gt_duration_ass_sub'], 0.0),
        )
    if gt_cd_term <= 0.0:
        gt_cd_term = _epc_gtcd(
            has_gt,
            _get_first(rows, ['support_surface::eecon.gt_cooldown_stone_level'], 0.0),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.gt_cooldown_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.gt_cooldown_ass_sub'], 0.0),
        ) * (gt_gcomp_factor if gt_gcomp_factor > 0.0 else 1.0)
    if gt_gc_factor <= 0.0:
        gt_gc_factor = _epc_gtgc(
            _bool(rows, ['support_surface::eecon.gt_goldenscreen_active'], False),
            _get_first(rows, ['support_surface::eecon.gt_goldenscreen_stone_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.kills_per_second'], 0.0),
            gt_duration_term,
        )

    if bh_bonus_term <= 0.0:
        bh_bonus_term = _epc_bhcb(
            _get_first(rows, ['support_surface::eecon.bh_coin_bonus_lab_level'], 0.0),
            _get_first(rows, ['support_surface::eecon.bh_kill_pct'], 1.0),
        )
    if bh_duration_term <= 0.0:
        bh_duration_term = _epc_bhd(
            _get_first(rows, ['support_surface::eecon.bh_duration_stone_level'], 0.0),
            _bool(rows, ['support_surface::eecon.bh_perk_active'], False),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.bh_duration_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.bh_duration_ass_sub'], 0.0),
        )
    if bh_cd_term <= 0.0:
        bh_cd_term = _epc_bhcd(
            has_bh,
            _get_first(rows, ['support_surface::eecon.bh_cooldown_stone_level'], 0.0),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.bh_cooldown_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.bh_cooldown_ass_sub'], 0.0),
        ) * (gt_gcomp_factor if gt_gcomp_factor > 0.0 else 1.0)

    if dw_bonus_term <= 0.0:
        dw_bonus_term = _epc_dwcb(_get_first(rows, ['support_surface::eecon.dw_coin_bonus_lab_level'], 0.0))
    if dw_duration_term <= 0.0:
        dw_duration_term = _epu_dwq(
            _get_first(rows, ['support_surface::eecon.dw_quantity_stone_level'], 0.0),
            _bool(rows, ['support_surface::eecon.dw_perk_active'], False),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.dw_quantity_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.dw_quantity_ass_sub'], 0.0),
        ) * 4.0
    if dw_cd_term <= 0.0:
        dw_cd_term = _epu_dwcd(
            has_dw,
            _get_first(rows, ['support_surface::eecon.dw_cooldown_stone_level'], 0.0),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.dw_cooldown_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.dw_cooldown_ass_sub'], 0.0),
        ) * (gt_gcomp_factor if gt_gcomp_factor > 0.0 else 1.0)

    uwcount = float(sum([1 if has_gt else 0, 1 if has_bh else 0, 1 if has_dw else 0]))
    if mvn_offset <= 0.0:
        mvn_offset = _epc_mvn(
            _get_first(rows, ['support_surface::eecon.mvn_primary_value'], 0.0),
            _get_first(rows, ['support_surface::eecon.mvn_assist_value'], 0.0),
            gt_cd_term,
            bh_cd_term,
            dw_cd_term,
            uwcount,
        )
    if mvn_offset > 0.0 and uwcount > 0.0:
        gt_cd_term = mvn_offset
        bh_cd_term = mvn_offset
        dw_cd_term = mvn_offset

    if gb_bonus_term <= 0.0:
        gb_bonus_term = _get_first(rows, ['support_surface::eecon.gb_bonus_multiplier', 'support_surface::eecon.gb_bonus'], 1.0)
    if gb_duration_term <= 0.0:
        gb_duration_term = _get_first(rows, ['support_surface::eecon.gb_duration_seconds', 'support_surface::eecon.gb_duration'], 0.0)
    if gb_cd_term <= 0.0:
        gb_cd_term = _get_first(rows, ['support_surface::eecon.gb_cooldown_seconds', 'support_surface::eecon.gb_cooldown'], 0.0)

    if sync_factor <= 0.0:
        sync_factor = _ep_sync(
            has_gt,
            gt_bonus_term if gt_bonus_term > 0.0 else 1.0,
            gt_duration_term,
            gt_cd_term,
            gt_gc_factor if gt_gc_factor > 0.0 else 1.0,
            has_bh,
            bh_bonus_term if bh_bonus_term > 0.0 else 1.0,
            bh_duration_term,
            bh_cd_term,
            has_dw,
            dw_bonus_term if dw_bonus_term > 0.0 else 1.0,
            dw_duration_term,
            dw_cd_term,
            has_gb,
            gb_bonus_term if gb_bonus_term > 0.0 else 1.0,
            gb_duration_term,
            gb_cd_term,
        )

    sl_coin_bonus = _get_first(rows, ['support_surface::eecon.spotlight_coin_bonus_multiplier', 'state::uw.spotlight.coin_bonus_multiplier', _compat_runtime('uw.spotlight.coin_bonus_multiplier'), _compat_mech('uw.spotlight.coin_bonus_multiplier')], 1.0)
    sl_quantity = _get_first(rows, ['support_surface::eecon.sl_quantity'], 0.0)
    if sl_quantity <= 0.0:
        sl_quantity = _get_first(rows, ['state::uw.spotlight.count', _compat_mech('uw.spotlight.count')], 0.0)
    if sl_quantity <= 0.0:
        sl_quantity = _epc_slq(_get_first(rows, ['support_surface::eecon.sl_quantity_stone_level', _compat_mech('uw.spotlight.quantity_stone_level')], _get_first(rows, [_compat_mech('uw.spotlight.quantity')], 0.0) - 1.0))
    sl_angle = _get_first(rows, ['support_surface::eecon.sl_angle'], 0.0)
    if sl_angle <= 0.0:
        sl_angle = _get_first(rows, ['state::uw.spotlight.angle_degrees', _compat_mech('uw.spotlight.angle_degrees')], 0.0)
    if sl_angle <= 0.0:
        sl_angle = _epc_sla(
            _get_first(rows, ['support_surface::eecon.sl_angle_stone_level', _compat_mech('uw.spotlight.angle_stone_level')], 0.0),
            stone_sac,
            lab_sac,
            _get_first(rows, ['support_surface::eecon.sl_angle_prim_sub'], 0.0),
            _get_first(rows, ['support_surface::eecon.sl_angle_ass_sub'], 0.0),
        )
    spotlight_coin_bonus = _get_first(rows, ['support_surface::eecon.spotlight_coin_bonus_term', 'support_surface::eecon.spotlight_coin_bonus'], 0.0)
    if spotlight_coin_bonus <= 0.0:
        spotlight_coin_bonus = _epc_slcb(_get_first(rows, ['support_surface::eecon.sl_coin_bonus_lab_level'], 0.0))
    spotlight_coin_coverage = _get_first(rows, ['support_surface::eecon.spotlight_coin_coverage'], 0.0)
    if spotlight_coin_coverage <= 0.0:
        spotlight_coin_coverage = _ep_sl_coverage(sl_quantity, sl_angle)
    spotlight_coin_factor = 1.0 + ((sl_coin_bonus * spotlight_coin_bonus) - 1.0) * spotlight_coin_coverage

    wave_factor = _get_first(rows, ['support_surface::eecon.wave_factor'], 0.0)
    if wave_factor <= 0.0:
        wave_accel_mastery = _bool(rows, ['support_surface::eecon.wave_accelerator_mastery_active'], False)
        wave_accel_mastery_level = _get_first(rows, ['support_surface::eecon.wave_accelerator_mastery_level'], 0.0)
        wam = 6500.0 / (1.0 + (0.10 * (1.0 + wave_accel_mastery_level) if wave_accel_mastery else 0.0))

        intro_active = _bool(rows, ['support_surface::eecon.intro_sprint_active'], False)
        intro_waves = _get_first(rows, ['support_surface::eecon.intro_sprint_waves'], 0.0)
        intro_mastery_active = _bool(rows, ['support_surface::eecon.intro_sprint_mastery_active'], False)
        intro_mastery_total_waves = _get_first(rows, ['state::cards.intro_sprint.waves', _compat_runtime('cards.intro_sprint.waves')], 0.0)
        if intro_mastery_total_waves <= 0.0:
            intro_mastery_multiplier = intro_sprint_mastery_multiplier_for_level(
                _get_first(rows, ['support_surface::eecon.intro_sprint_mastery_level'], 0.0)
            )
            intro_mastery_total_waves = (
                intro_waves * intro_mastery_multiplier
                if intro_mastery_multiplier is not None and intro_waves > 0.0
                else 0.0
            )
        is_reduction = 0.0
        isd = 0.0
        if intro_active:
            is_reduction = intro_waves - (1.0 + intro_waves / 10.0)
            isd = intro_waves
            if intro_mastery_active:
                extra = max(0.0, intro_mastery_total_waves - intro_waves)
                is_reduction += extra - (extra / 10.0)
                isd += extra

        ws_total = 0.0
        has_ws = _bool(rows, ['support_surface::eecon.wave_skip_active'], _get_first(rows, ['state::cards.wave_skip.chance_pct', _compat_runtime('cards.wave_skip.chance_pct')], 0.0) > 0.0)
        ws_card = _get_first(rows, ['state::cards.wave_skip.chance_pct', _compat_runtime('cards.wave_skip.chance_pct')], 0.0)
        if ws_card > 1.0:
            ws_card /= 100.0
        ws_mastery = _bool(rows, ['support_surface::eecon.wave_skip_mastery_active'], False)
        ws_mastery_level = _get_first(rows, ['support_surface::eecon.wave_skip_mastery_level'], 0.0)
        for skip in range(1, 11):
            ws_total += skip * _epc_card_ws(skip, has_ws, ws_card, ws_mastery, ws_mastery_level)
        if has_ws:
            ws_total *= max(wam - isd, 0.0)
        denom = max(1e-9, wam - is_reduction - ws_total)
        wave_factor = 6500.0 / denom

    utility_dissonance_factor = 0.0 if utility_dissonance_active else _dissonance_total_multiplier(rows, 'utility')
    eecon_raw_factor = cl_factor * eom_factor * sync_factor * spotlight_coin_factor * wave_factor * utility_dissonance_factor
    eecon_unit_scale_factor = _get_first(rows, ['support_surface::eecon.unit_scale_factor'], 1000.0)
    eecon = eecon_raw_factor * eecon_unit_scale_factor
    _publish(rows, 'derived::eecon.base_meta_factor', adstarter_theme_relic_factor, 'multiplier', [], 'ad starter / theme / relic factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.cpk_factor', cpk_factor, 'multiplier', [_contributor(rows, cpk_contributor_key, 'eecon.cpk_factor')], 'EPC_CPK-like coin-per-kill factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.freeup_factor', freeup_factor, 'multiplier', [], 'free-up factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.coin_card_factor', coin_card_factor, 'multiplier', [_contributor(rows, _compat_runtime('cards.coins.multiplier'), 'eecon.coin_card_factor')], 'EPC_CARD_COINS factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.module_factor', module_factor, 'multiplier', [], 'generator module factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.all_coin_bonus_factor', all_coin_bonus_factor if all_coin_bonus_factor > 0.0 else 1.0, 'multiplier', all_coin_bonus_contributors, 'Published all-coin display factor available to eEcon reconciliation; final EP eEcon chain remains separately governed.')
    _publish(rows, 'derived::eecon.cl_factor', cl_factor, 'multiplier', [], 'EP eEcon CL term [EP helper support surface]')
    _publish(rows, 'derived::eecon.eom_factor', eom_factor, 'multiplier', [], 'EP eEcon CM term [EP helper support surface]')
    _publish(rows, 'derived::eecon_ep_helper.cl_meta_stack', cl_factor, 'multiplier', [], 'EP eEcon CL workbook grouping alias [EP helper surface]')
    _publish(rows, 'derived::eecon_ep_helper.cm_eom_factor', eom_factor, 'multiplier', [], 'EP eEcon CM workbook grouping alias [EP helper surface]')
    _publish(rows, 'derived::eecon.gcomp_factor', gt_gcomp_factor, 'multiplier', [], 'EPC_GCOMP-like package timing factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.mvn_offset', mvn_offset, 'scalar', [], 'EPC_MVN-like merged cooldown offset [EP helper support surface]')
    _publish(rows, 'derived::eecon.gt_bonus_term', gt_bonus_term, 'multiplier', [], 'EPC_GTB-like GT bonus term [EP helper support surface]')
    _publish(rows, 'derived::eecon.gt_duration_term', gt_duration_term, 'scalar', [], 'EPC_GTD-like GT duration term [EP helper support surface]')
    _publish(rows, 'derived::eecon.gt_cooldown_term', gt_cd_term, 'scalar', [], 'EPC_GTCD-like GT cooldown term [EP helper support surface]')
    _publish(rows, 'derived::eecon.gt_gc_factor', gt_gc_factor, 'multiplier', [], 'EPC_GTGC-like GT gold-crit factor [EP helper support surface]')
    _publish(rows, 'derived::eecon.bh_bonus_term', bh_bonus_term, 'multiplier', [], 'EPC_BHCB-like BH bonus term [EP helper support surface]')
    _publish(rows, 'derived::eecon.bh_duration_term', bh_duration_term, 'scalar', [], 'EPC_BHD-like BH duration term [EP helper support surface]')
    _publish(rows, 'derived::eecon.bh_cooldown_term', bh_cd_term, 'scalar', [], 'EPC_BHCD-like BH cooldown term [EP helper support surface]')
    _publish(rows, 'derived::eecon.dw_bonus_term', dw_bonus_term, 'multiplier', [], 'EPC_DWCB-like DW bonus term [EP helper support surface]')
    _publish(rows, 'derived::eecon.dw_duration_term', dw_duration_term, 'scalar', [], 'EPU_DWQ*4-like DW duration term [EP helper support surface]')
    _publish(rows, 'derived::eecon.dw_cooldown_term', dw_cd_term, 'scalar', [], 'EPU_DWCD-like DW cooldown term [EP helper support surface]')
    _publish(rows, 'derived::eecon.sync_factor', sync_factor, 'multiplier', [], 'EP eEcon DC term [EP helper support surface]')
    _publish(rows, 'derived::eecon_ep_helper.dc_sync_factor', sync_factor, 'multiplier', [], 'EP eEcon DC workbook grouping alias [EP helper surface]')
    _publish(rows, 'derived::eecon.spotlight_coin_bonus_term', spotlight_coin_bonus, 'multiplier', [_contributor(rows, 'support_surface::eecon.sl_coin_bonus_lab_level', 'eecon.spotlight_coin_bonus_term')], 'EP spotlight coin bonus term before coverage [EP helper support surface]')
    _publish(rows, 'derived::eecon.spotlight_coin_coverage', spotlight_coin_coverage, 'ratio', [_contributor(rows, 'support_surface::eecon.sl_quantity', 'eecon.spotlight_coin_coverage'), _contributor(rows, 'support_surface::eecon.sl_angle', 'eecon.spotlight_coin_coverage')], 'EP spotlight coin coverage from quantity and angle [EP helper support surface]')
    _publish(rows, 'derived::eecon.spotlight_coin_factor', spotlight_coin_factor, 'multiplier', [_contributor(rows, _compat_runtime('uw.spotlight.coin_bonus_multiplier'), 'eecon.spotlight_coin_factor')], 'EP eEcon DG term [EP helper support surface]')
    _publish(rows, 'derived::eecon_ep_helper.dg_spotlight_coin_bonus_term', spotlight_coin_bonus, 'multiplier', [_contributor(rows, 'support_surface::eecon.sl_coin_bonus_lab_level', 'eecon_ep_helper.dg_spotlight_coin_bonus_term')], 'EP eEcon DG workbook bonus-term alias [EP helper surface]')
    _publish(rows, 'derived::eecon_ep_helper.dg_spotlight_coin_coverage', spotlight_coin_coverage, 'ratio', [_contributor(rows, 'support_surface::eecon.sl_quantity', 'eecon_ep_helper.dg_spotlight_coin_coverage'), _contributor(rows, 'support_surface::eecon.sl_angle', 'eecon_ep_helper.dg_spotlight_coin_coverage')], 'EP eEcon DG workbook coverage alias [EP helper surface]')
    _publish(rows, 'derived::eecon_ep_helper.dg_spotlight_coin_factor', spotlight_coin_factor, 'multiplier', [_contributor(rows, _compat_runtime('uw.spotlight.coin_bonus_multiplier'), 'eecon_ep_helper.dg_spotlight_coin_factor')], 'EP eEcon DG workbook factor alias [EP helper surface]')
    _publish(rows, 'derived::eecon.wave_factor', wave_factor, 'multiplier', [], 'EP eEcon DH term [EP helper support surface]')
    _publish(rows, 'derived::eecon.utility_dissonance_factor', utility_dissonance_factor, 'multiplier', [_contributor(rows, 'derived::dissonance.utility.total_multiplier', 'eecon.utility_dissonance_factor')], 'v28 Utility Dissonance/Echo multiplier applied to the final eEcon chain.')
    _publish(rows, 'derived::eecon.raw_factor', eecon_raw_factor, 'scalar', [_contributor(rows, cpk_contributor_key, 'eecon.raw_factor')], 'Raw multiplicative eEcon factor before EP CPK unit scaling.')
    _publish(rows, 'derived::eecon.unit_scale_factor', eecon_unit_scale_factor, 'multiplier', [], 'EP Average CpK unit scale from workbook factor units to displayed coin units.')
    _publish(rows, 'derived::eecon.base_coin_income', eecon, 'scalar', [_contributor(rows, cpk_contributor_key, 'eecon.base_coin_income')], 'Deterministic coin-income proxy surface derived from the governed eEcon line [query support surface]')
    _publish(rows, 'derived::eecon', eecon, 'scalar', [_contributor(rows, cpk_contributor_key, 'eecon')], 'Native eEcon objective line; currently equal to EP line')
    _publish(rows, 'derived::eecon_ep', eecon, 'scalar', [_contributor(rows, cpk_contributor_key, 'eecon_ep')], 'Exact Effective Paths eEcon objective line')


def compute_derived_ehp(rows):
    tmp = dict(rows)
    publish_derived_composites(tmp)
    return tmp['derived::ehp'].final_value


def compute_derived_edamage(rows):
    tmp = dict(rows)
    publish_derived_composites(tmp)
    return tmp['derived::edamage'].final_value


def compute_derived_eecon(rows):
    tmp = dict(rows)
    publish_derived_composites(tmp)
    return tmp['derived::eecon'].final_value
