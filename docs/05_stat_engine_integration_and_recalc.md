# Stat Engine Integration and Recalculation

## Why recalc is required
If workshop levels can change during the run, then a single frozen stat snapshot is not sufficient.

The progression engine must therefore:
1. track all current workshop levels
2. apply buys/free upgrades
3. call a KB-aligned stat recalculation path
4. consume refreshed outputs

## Correct baseline stage
Use `start_of_run` as the baseline stage.

Do **not** use `max_progression` as the default baseline for this engine if in-run workshop progression matters.

---

## Recommended v1 approach
Use a **full safe recompute** path rather than dependency-pruned recompute.

### Pros
- safest
- easiest to verify
- most KB aligned

### Cons
- slower

This is acceptable for v1 and should be preferred over premature optimisation.

---

## Recalculation trigger concept
At minimum, recalc when any in-run workshop state change affects boss-relevant outputs.

### Boss-relevant outputs include
- `wall_hp`
- `wall_regen`
- `tower_defense_pct`
- `enemy_attack_level_skip_pct`
- `enemy_health_level_skip_pct`
- `tower_thorns_damage_pct`
- `tower_orb_count`
- `tower_orb_speed_rpm`
- any free-upgrade-related surfaces that alter expected progression state

---

## Recommended interface
Conceptually:

`recompute_stats(account_baseline, fixed_perk_set, current_workshop_run_state) -> refreshed_stat_outputs`

Additional scenario overlays like mode/BC/heat remain outside this path and should be applied in the scenario-invariant engine.

---

## Workshop tracking rule
Even if v1 boss logic only directly consumes a subset of recalculated outputs, the progression engine should still track **all workshop levels**.

Reason:
- workshop can be respec'd
- any track may be non-maxed
- full state completeness matters for future expansions and correctness

---

## Optimisation rule
Do not switch to dependency-pruned or memoized recompute until:
1. the workshop dependency ledger is explicit
2. boss-relevant consumers are explicit
3. regression tests exist for recompute parity against full safe recompute


## Wall dependency note
`wall_hp` is an emitted canonical stat, but it is **not** an independent leaf in the calc. It depends on `tower_hp` plus wall ratio/additive/multiplier inputs in the stat engine.

Architectural consequence: the progression engine must never try to update wall-only downstream values in isolation; it should always rely on full stat-engine recompute from the current workshop/perk state snapshot.

## Perk timeline interaction
The perk timeline itself is static once generated and already handles retrospective PWR. For wave-accurate progression, the progression engine should read the generated timeline artifact and derive the active perk state at the current wave rather than re-implement perk timing logic.
