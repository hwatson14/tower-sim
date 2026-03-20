# V1 Boss-Wave Engine Spec

## Purpose
Build a deterministic boss-wave survivability engine that:
1. tracks attack wave and health wave separately
2. computes boss TTK first
3. computes boss outgoing damage over the TTK window
4. applies heat-up and mitigation
5. determines wall survival / first failing boss wave

## V1 scope

### In scope
- boss waves only
- separate `attack_wave` and `health_wave`
- boss HP from `health_wave`
- boss outgoing damage from `attack_wave`
- v1 boss kill sources:
  - Plasma Cannon
  - Thorns
  - Orbs
  - Electrons
- battle conditions where relevant
- boss heat-up
- BH/CF mitigation contribution
- wall-based survival

### Out of scope
- non-boss waves
- wave skip
- bullet/projectile direct DPS model
- exact tick/frame replay
- tower HP as primary survival state
- helper-sheet parity for its own sake

---

## Core causality
1. determine boss wave index
2. derive `attack_wave`
3. derive `health_wave`
4. read boss HP from common enemy HP at `health_wave` times boss multiplier
5. read boss outgoing damage baseline
6. apply scenario overlays
7. compute boss TTK from allowed v1 kill sources
8. compute boss outgoing damage over that TTK window
9. apply wall regen and wall survival logic
10. emit per-wave ledger row

---

## Boss TTK

### Rule
Boss TTK must be computed before boss outgoing damage is finalized.

### V1 source set
- Plasma Cannon
- Orbs
- Electrons
- Thorns (if boss reaches contact)

### Important note
All v1 kill sources are percent-based, but `health_wave` must still be tracked for v2 readiness.

### Recommended solver shape
Use a deterministic event progression approach rather than a naive linear DPS approximation. Recommended event classes:
- Plasma Cannon opening event using `runtime_mechanic_param::cards.plasma_cannon.effect_pct`
- orb hit events
- electron hit events
- boss contact event
- boss attack events

This remains deterministic while respecting remaining-HP-based percent effects.

---

## Boss heat-up
V1 must include boss damage heat-up.

### Working model from chat
Use the KB-backed shared enemy rule: +4% damage per completed prior hit while the boss remains alive.

For hit number `n`:
- hit 1: `1.00 x D`
- hit 2: `1.04 x D`
- hit 3: `1.08 x D`
- etc.

This is treated as verified at the mechanic-rule level in the current package; provenance should still note that boss hit interval remains an accepted model constant rather than a wiki row.

---

## Survival model
Use wall survival as the primary practical death condition.

### Inputs required from stat engine / invariant engine
- `wall_hp`
- `wall_regen`
- `tower_defense_pct`
- `wall_fortification_multiplier`
- CF mitigation surfaces
- BH mitigation-relevant surfaces
- scenario-adjusted boss hit interval and damage modifiers

### Important note on fortification
`wall_fortification_multiplier` should remain separate from `wall_hp` unless the stat engine is later changed to emit an already-fortified wall-effective-HP surface.

---

## Per-wave output rows
Recommended fields:
- `boss_wave`
- `attack_wave`
- `health_wave`
- `boss_effective_hp`
- `boss_base_damage`
- `boss_ttk_seconds`
- `boss_contact_time_seconds`
- `boss_hits_taken`
- `boss_total_damage_taken`
- `wall_hp_start`
- `wall_regen_gained`
- `wall_hp_end`
- `survival_margin_hp`
- `death_flag`

---

## V1 design constraint
Any formula adopted into implementation must be represented as one of:
- verified KB-backed rule
- published runtime surface preferred; Plasma Cannon fallback retired in r25-integrated plan
- explicit provisional implementation rule pending KB verification
