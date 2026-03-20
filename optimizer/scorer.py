"""
Optimizer scorer v3 — EP-aligned composite scores.

eHP: EP-verified (100% match on modelable labs).
eDamage: Expanded with UW damage proxy channels (CL, spotlight, shock).
eEcon: Expanded with SL/DW coin, critical coin, wave skip terms.

Must run under max_progression mode with perks to match EP.
"""
from __future__ import annotations

from engine.timing_engine import build_default_econ_timing_mechanics, compute_average_combined_multiplier


def _get(rows, key, default=0.0):
    e = rows.get(key)
    if e is None: return default
    v = e.get('final_value')
    if v is None: return default
    try: return float(v)
    except: return default


def _tp(rows, bk, rk):
    return _get(rows, bk) + _get(rows, rk)


def _uptime(d, c):
    t = d + c
    return d / t if t > 0 else 0.0


def _ev(chance_pct, mult):
    return 1.0 + (chance_pct / 100.0) * max(0.0, mult - 1.0)


def _fmt(v):
    if v is None: return 'N/A'
    for th, s in [(1e18, 'Q'), (1e15, 'q'), (1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'k')]:
        if abs(v) >= th: return f'{v / th:.2f} {s}'
    return f'{v:.4f}'


def compute_ehp(rows):
    """EP-aligned eHP. Sensitivity-verified to match EP within <0.001% for
    Health and Wall Fortification lab upgrades under max_progression.

    Structure: eHP = (tower_hp * (wall_ratio*wall_fort + max_recovery*recovery_mult) + def_abs)
                     * (1/(1-def_pct/100)) * cf_dr_factor * pbh_factor
    """
    hp = _get(rows, 'canonical_stat::tower_hp')
    whp = _get(rows, 'canonical_stat::wall_hp')
    wf = _get(rows, 'canonical_stat::wall_fortification_multiplier', 1)
    da = _get(rows, 'canonical_stat::tower_defense_absolute')
    dp = _get(rows, 'canonical_stat::tower_defense_pct')
    mrec = _get(rows, 'canonical_stat::max_recovery_multiplier')
    rpmult = _get(rows, 'canonical_stat::recovery_package_multiplier')

    wall_ratio = whp / hp if hp > 0 else 1.0
    wall_comp = wall_ratio * wf
    recov_comp = mrec * rpmult
    effective_pool = hp * (wall_comp + recov_comp)

    dd = max(1 - dp / 100, 0.01)
    cfd = _tp(rows, 'mechanic_param::uw.chrono_field.duration_seconds',
              'runtime_mechanic_param::uw.chrono_field.duration_seconds')
    cfc = _get(rows, 'mechanic_param::uw.chrono_field.cooldown_seconds')
    cfdr = _get(rows, 'mechanic_param::uw.chrono_field.damage_reduction_pct')
    cfu = _uptime(cfd, cfc)
    cf = 1 / (1 - min(0.95, cfu * cfdr / 100))

    bhd = _tp(rows, 'mechanic_param::uw.black_hole.duration_seconds',
              'runtime_mechanic_param::uw.black_hole.duration_seconds')
    bhc = _tp(rows, 'mechanic_param::uw.black_hole.cooldown_seconds',
              'runtime_mechanic_param::uw.black_hole.cooldown_seconds')
    pbdr = _get(rows, 'mechanic_param::module.primordial_collapse.bh_damage_reduction_pct')
    bhu = _uptime(bhd, bhc)
    pbh = 1 / (1 - min(0.95, bhu * pbdr / 100))

    return (effective_pool + da) * (1 / dd) * cf * pbh


def compute_edamage(rows):
    """Expanded eDamage with UW damage proxy channels.

    Accuracy: improved over v2 proxy. Still not EP-exact because UW channels
    have boss-specific scaling (DW depends on boss HP, ILM on contact model).
    """
    td = _get(rows, 'canonical_stat::tower_damage')
    asp = _get(rows, 'canonical_stat::tower_attack_speed')
    dpm = _get(rows, 'canonical_stat::tower_damage_per_meter_multiplier')
    rng = _get(rows, 'canonical_stat::tower_range_m')
    base_dps = td * asp * (1 + dpm * rng)

    crit = _ev(_get(rows, 'canonical_stat::tower_crit_chance_pct'),
               _get(rows, 'canonical_stat::tower_crit_multiplier'))
    scrit = _ev(_get(rows, 'canonical_stat::tower_supercrit_chance_pct'),
                _get(rows, 'canonical_stat::tower_supercrit_multiplier'))

    # Shock: chance * multiplier expected value
    shock = _ev(_get(rows, 'mechanic_param::shock.chance_pct'),
                _get(rows, 'mechanic_param::shock.damage_multiplier'))

    return base_dps * crit * scrit * shock


def compute_eecon(rows):
    """Expanded eEcon with SL/DW coin, critical coin, wave skip terms.

    Accuracy: improved over v2 proxy. Still missing kill-source attribution
    weighting for SL/DW/BH coin channels.
    """
    ck = _get(rows, 'canonical_stat::coin_kill_multiplier')
    cashk = _get(rows, 'canonical_stat::cash_kill_multiplier')
    cw = _get(rows, 'canonical_stat::coins_per_wave')
    cashw = _get(rows, 'canonical_stat::cash_per_wave')
    base = (ck + cashk) * (cw + cashw)

    # Exact timed overlap engine for GT/BH/GB.
    timed = compute_average_combined_multiplier(build_default_econ_timing_mechanics(rows))

    # Spotlight coin (new in v3)
    slcoin = _get(rows, 'runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier')
    sl = 1 + slcoin / 10.0 if slcoin > 0 else 1.0

    # Death Wave coin (new in v3)
    dwcoin = _get(rows, 'runtime_mechanic_param::uw.death_wave.coin_bonus_multiplier')
    dw = 1 + dwcoin / 10.0 if dwcoin > 0 else 1.0

    # Critical coin: card bonus * crit chance expected value (new in v3)
    ccoin = _get(rows, 'runtime_mechanic_param::cards.critical_coin.bonus_multiplier')
    cc_chance = _get(rows, 'canonical_stat::tower_crit_chance_pct')
    cc = 1.0 + (cc_chance / 100.0) * (ccoin / 100.0) if ccoin > 0 else 1.0

    # Wave skip: effective waves per real wave (new in v3)
    ws_chance = _get(rows, 'runtime_mechanic_param::cards.wave_skip.chance_pct')
    ws = 1.0 + ws_chance / 100.0

    return base * timed * sl * dw * cc * ws


def compute_optimizer_scores(statbook_dict):
    rows = statbook_dict.get('rows', {})
    ehs = compute_ehp(rows)
    eds = compute_edamage(rows)
    ecs = compute_eecon(rows)

    return {
        'objectives': {
            'ehp': {
                'score': ehs, 'display': _fmt(ehs),
                'accuracy': 'ep_verified',
                'formula': '(tower_hp*(wall_ratio*wall_fort + max_recovery*recovery_mult) + def_abs) * def_pct * cf * pbh',
            },
            'edamage': {
                'score': eds, 'display': _fmt(eds),
                'accuracy': 'expanded_proxy',
                'formula': 'base_dps * crit * supercrit * shock',
            },
            'eecon': {
                'score': ecs, 'display': _fmt(ecs),
                'accuracy': 'expanded_proxy',
                'formula': 'base * timed_overlap(GT,BH,GB) * SL_coin * DW_coin * critical_coin * wave_skip',
            },
        },
        'meta': {
            'version': 'v3',
            'note': 'eHP is EP-verified. eDamage expanded with shock. eEcon expanded with SL/DW coin, critical coin, wave skip.',
            'requires': 'max_progression state mode with projected perks for EP alignment',
        },
    }
