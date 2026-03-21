# Optimizer Accuracy Report

## EP Comparison Methodology

EP (Effective Paths v5.03.02) is the reference spreadsheet. Comparison was done by:
1. Extracting EP's composite score formulas from cell-level analysis
2. Matching composite score sensitivities to lab upgrades (delta% per +1 level)
3. Running greedy path rankers and comparing upgrade sequences step-by-step

All comparisons use **max_progression** state mode with **perks_projected_max.json** to match EP's operating assumptions.

## eHP — EP-verified ✓

### Composite Formula
```
eHP = (tower_hp * (wall_ratio * wall_fort + max_recovery * recovery_mult) + def_abs) * def_pct_factor * cf_dr * pbh
```

Where:
- `wall_ratio = wall_hp / tower_hp` (constant across Health lab, both co-scale)
- `max_recovery * recovery_mult` = EP's CJ term (verified exact: 16.5 × 1.42 = 23.43)
- `def_pct_factor = 1 / (1 - defense_pct/100)`
- `cf_dr = 1 / (1 - min(0.95, cf_uptime * cf_dr_pct/100))`
- `pbh = 1 / (1 - min(0.95, bh_uptime * pbh_dr_pct/100))`

### Sensitivity Match
| Lab Upgrade | My Delta | EP Delta | Error |
|---|---|---|---|
| Health 68→69 | +0.9868% | +0.9868% | 0.000% |
| Wall Fort 47→48 | +1.7000% | +1.7000% | 0.000% |

### Lab Path Match (15 steps)
- Steps 1–6: **6/6 exact match** (alternating Wall Fort and Health)
- Step 7: EP picks Assist Module Bonus - Armor (not modeled in calculator) → divergence
- Steps 8–15: **8/8 sequence match** (same upgrades as EP, offset by one due to step 7 gap)
- **Effective match rate: 100% on modelable labs**

### Known Gap
Module labs (Assist Module Bonus/Substats - Armor) don't change any calculator stats when upgraded. This is a calculator limitation, not an optimizer formula error.

## eDamage — Simplified Proxy ✗

### Composite Formula
```
eDamage = tower_damage * attack_speed * (1 + dpm * range) * crit_ev * supercrit_ev
```

### Why It Doesn't Match EP
EP's eDamage includes **additive UW damage channels** (Death Wave, Chain Lightning, Smart Missiles, Spotlight, Inner Land Mine) that are independent of base tower DPS. These channels dilute the relative contribution of base stats. Without them, Damage/Meter is over-weighted ~10x vs EP.

EP's first 7 picks are all module labs (Assist Module Bonus/Substats - Core), which also aren't modeled.

### Path to Fix
Implement UW damage channels as additive terms: `total_dmg = base_dps + DW + CL + SM + SL + ILM`, then apply shared multipliers (crit, supercrit, module bonus) to the composite.

## eEcon — Simplified Proxy ✗

### Composite Formula
```
eEcon = (coin_kill + cash_kill) * (coins_wave + cash_wave) * GT_factor * BH_factor * GB_factor
```

### Why It Doesn't Match EP
Missing multiplicative terms: Spotlight coin bonus, Death Wave coin bonus, critical coin card bonus, wave skip, recovery package economy contribution, free upgrade discounts, and module cost discounts. This causes Golden Tower Bonus to dominate incorrectly.

EP's first pick is also a module lab (Assist Module Bonus - Generator), not modeled.

### Path to Fix
Add economy terms per the R19 consumption manifest: SL coin, DW coin, critical coin, wave skip, package/wave, free upgrade average, and module discount factors.
