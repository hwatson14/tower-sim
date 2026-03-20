# Required Updates to r27 Calculator and KB

This document lists every update the r27 `integration_r20` package needs for the
scenario-invariant engine to consume fully governed inputs, plus pre-existing
bugs discovered during the session.

---

## A. Pre-existing stat engine bugs (found in v92, still present in r27)

### A1. tower_orb_count perk silently dropped
**File:** `engine/stat_engine.py` lines 705–719
**Bug:** Resolver has branches for workshop, card, lab, module_substat, vault — but NO perk branch. Perk `Orbs +1` (PERK_ORBS_1, 2 picks, value 2.5, type flat) is in contributors but ignored.
**Result:** 6 orbs instead of 8.
**Fix:** Add `elif r.source_family == 'perk': extra += v` branch after the vault branch.

### A2. count_add SPB creates fractional integer stats
**File:** `compilers/stat_input_compiler.py` line 1163
**Bug:** `_scaled_perk_value` applies `standard_bonus_multiplier` (1.25) to ALL `count_add` operations without rounding. Produces fractional counts: Bounce Shot +2 → 7.5, Orbs +1 → 2.5.
**Result:** `tower_bounce_shot_targets` = 15.5 instead of 16.
**Fix:** After the `count_add` scaling line, add: `if operation == 'count_add': scaled = round(scaled)`
**Note:** The `explicit-spb-integrality-policy.md` KB document exists and describes this policy, but the code does not implement it. The `perk-entity-registry.csv` lacks the `spb_applies`, `spb_formula_class`, and `integrality_policy` columns that the policy document references.

### A3. tower_bounce_shot_targets resolves to fractional value
**File:** `engine/stat_engine.py`
**Bug:** Schema declares `resolver: integer_count_stat` but the engine has no special handler for this resolver type. Downstream of A2.
**Result:** 15.5 instead of 16.
**Fix:** Fixing A2 resolves this. Optionally also add integrality enforcement for `integer_count_stat` resolver type.

---

## B. Stat engine surfaces needed by scenario engine (not yet resolved)

### B1. CF damage reduction percentage — not emitted
**Current state:** `raw::Chrono Field Damage Reduction` and `raw::Chrono Field Reduction %` are both `unmapped` in the statbook.
**What's needed:** A resolved surface `mechanic_param::uw.chrono_field.damage_reduction_pct` that combines:
  - Chrono Field Damage Reduction lab (1 level, base 10%)
  - Chrono Field Reduction % lab (30 levels, `value = 10.50 + (level-1) * 0.50`)
  - Total = base + lab_value
**KB source:** `kb/formulas/tables/canonical-formula-registry.csv` rows `wiki_verified_chrono_field_reduction_pct_lab` and `wiki_verified_chrono_field_damage_reduction_unlock`.
**Workaround in scenario engine:** `compute_cf_damage_reduction_pct(unlock_level, reduction_pct_level)` helper function computes the value from lab levels. Caller must read IDS and pass the result manually until the stat engine emits it.

### B2. BC reduction lab levels — not emitted
**Current state:** No stat engine surface for any of the 4 BC reduction lab group levels.
**What's needed:** 4 resolved surfaces or input reader that provides:
  - `bc_reduction_group1_pct` (main BC reduction lab — PC/orb/thorns/DR/knockback/more_bosses)
  - `bc_reduction_group2_pct` (armored/enemy_speed/more_enemies/enemy_attack_speed)
  - `bc_reduction_group3_pct` (enemy ultimates)
  - `bc_reduction_group4_pct` (UW durations/death_defy_down/energy_shields_down/enemy_level_skip)
**KB source:** `kb/tournaments/tables/battle-condition-reduction-lab.csv` (group 1) and `battle-condition-group-{2,3,4}-reduction-lab.csv`.
**Workaround in scenario engine:** Caller must read IDS lab levels and compute pct values manually, then pass via `config_from_statbook(..., bc_reduction_group1_pct=X, ...)`.

---

## C. KB updates needed

### C1. perk-entity-registry.csv missing integrality columns
**Current state:** The CSV has columns `perk_id, perk_name, category, max_picks, stacking_type, effect_count, source_class, status`. 
**What's needed:** Add columns `spb_applies`, `spb_formula_class`, `integrality_policy` as documented in `kb/perks/sources/explicit-spb-integrality-policy.md`.
**Why:** The policy document exists but isn't reflected in the machine-readable registry. The stat engine code doesn't implement the policy because the columns don't exist.

### C2. No canonical table for BC reduction group → BC mapping
**Current state:** The group-to-BC mapping is only discoverable from the `applies_to` free-text column in each group reduction lab CSV.
**What's needed:** A machine-readable `kb/tournaments/tables/bc-group-membership.csv` with columns `bc_id, group_number` so the engine can programmatically look up which BCs belong to which reduction group.
**Why:** The current engine hardcodes the group membership knowledge. A KB table would make it auditable.

---

## D. Docs pack updates needed

### D1. Doc 12 formula verification ledger — 3 upgrades
The following should be upgraded from Provisional to Verified:
  - Boss heat-up +4%/hit → KB: `wiki-verified-enemy-categories-and-shared-rules.csv` + `wiki-verified-baselines.md`
  - Electron boss effect 0.25x → KB: `enemy-class-interaction-matrix.csv`, HIGH
  - Thorns boss effect 0.5x → KB: `enemy-class-interaction-matrix.csv`, HIGH

### D2. Doc 12 — CF damage reduction should be added as Verified
Add row: CF damage reduction, base 10% + lab 10.5→25%, applied after defense absolute, Verified, `canonical-formula-registry.csv` + wiki.

### D3. Doc 09 effect surface contract — add scenario engine surfaces
The effect surface contract should include the full 46-surface inventory from the scenario engine. Current doc 09 only lists a subset.

### D4. Doc 07 gap ledger — close Gap D (boss heat-up)
Gap D status should change from "provisional implementation rule" to "closed — KB-verified".

### D5. Doc 06 perk notes — account for retroactive PWR
The docs say "perk set is fixed for the entire run" which is correct, but don't account for the retroactive wave recalculation mechanic. The progression engine needs to own the perk timeline (when perks are awarded), not just consume a static preset.

---

## E. Scenario engine integration notes

### E1. How to integrate
Drop `scenario_invariant_engine.py` into `engine/` and `test_scenario_invariant.py` into `tests/`. No existing files are modified.

### E2. How to call from run_stats.py or progression engine
```python
from engine.scenario_invariant_engine import (
    config_from_statbook, compute_scenario_surfaces, compute_cf_damage_reduction_pct
)

# Read stat engine output
statbook_rows = json.loads(Path('out/statbook.json').read_text())['rows']

# Compute CF DR from IDS lab levels (until stat engine emits it)
cf_dr_pct = compute_cf_damage_reduction_pct(
    cf_dr_unlock_level=1,    # from IDS: Chrono Field Damage Reduction level
    cf_reduction_pct_level=20,  # from IDS: Chrono Field Reduction % level
)

# Build config from stat engine output
config = config_from_statbook(
    statbook_rows,
    mode_id='farming',
    tier=14,
    cf_damage_reduction_pct=cf_dr_pct,
    bc_reduction_group1_pct=10.0,  # from IDS lab level → lookup in BC reduction lab table
)

# Compute all scenario surfaces
surfaces = compute_scenario_surfaces(config)
```

### E3. What the progression engine consumes
The progression engine should consume `ScenarioSurfaces` directly. Key surfaces for boss-v1:
- `boss_hit_interval_seconds` (adjusted by enemy_attack_speed BC)
- `boss_wave_interval` (adjusted by more_bosses BC)
- `bc_plasma_cannon_resistance`, `bc_orb_resistance`, `bc_thorns_resistance` (for boss TTK)
- `boss_thorns_effectiveness`, `boss_electron_effectiveness` (inherent boss class resistances)
- `cf_damage_reduction_pct`, `cf_uptime_fraction`, `cf_avg_damage_reduction_fraction` (for boss intake)
- `bh_uptime_fraction` (for mitigation envelope)
- `env_enemy_damage_multiplier`, `env_boss_health_multiplier` (for boss HP and damage scaling)
- `bc_uw_duration_reduction_s` (already factored into uptime fractions)
- `bc_death_defy_down_pp`, `bc_energy_shields_down_fraction` (for survival)
