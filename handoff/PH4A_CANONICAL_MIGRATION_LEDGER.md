# PH4A_CANONICAL_MIGRATION_LEDGER.md

## Purpose

This file freezes the executable denominator for `PH4-A — Canonical migration ledger and denominator freeze`.

It exists to prevent Phase 4 code work from rediscovering scope ad hoc.
Until the contents are folded into the long-lived control stack, this file is the bounded working ledger for:
- family denominator
- canonical stat-group denominator
- residual bucket policy
- parity denominator
- benchmark denominator
- allowed post-Phase-4 residue

This file does **not** authorize code migration by itself.
Code migration starts only when the active tranche still points at PH4 and this denominator remains consistent with repo truth.

---

## Denominator freeze decisions

### Frozen scope categories
Only these categories are allowed in Phase 4:

1. `family_scoped_canonical_resolution`
2. `non_family_canonical_stat_resolution`
3. `compatibility_only_surface`
4. `legacy_merge_reference_residue`
5. `out_of_phase4_scope`

No later Phase 4 tranche may silently add a new category, move a row between categories, or expand the denominator without first updating the control stack.

### Frozen family denominator
The Phase 4 family denominator is frozen at **6 declared scenario families** from `kb/global-rules/contracts/stat-query-scenario-families.yaml`:

#### Timing family universe
- `timing_tournament_no_perks`
- `timing_farm_with_perks`
- `timing_scenario_probe`

#### Progression family universe
- `progression_start_of_run`
- `progression_runtime_no_perks`
- `progression_runtime_with_perks`

### Frozen family-surface denominator
The declared family-surface denominator is frozen at **26 surfaces** from `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`.

#### Timing family surfaces (8)
- `state::tower.package_chance_pct`
- `mechanic_param::uw.black_hole.cooldown_seconds`
- `mechanic_param::uw.black_hole.duration_seconds`
- `mechanic_param::uw.golden_tower.cooldown_seconds`
- `mechanic_param::uw.golden_tower.duration_seconds`
- `support_surface::timing.gcomp_cooldown_reduction_seconds`
- `state::cards.wave_accelerator.spawn_rate_acceleration`
- `support_surface::timing.wave_duration_seconds_effective`

#### Progression family surfaces (18)
- `state::tower.hp`
- `state::wall.hp`
- `state::wall.regen`
- `state::wall.fortification_multiplier`
- `state::tower.defense_pct`
- `state::tower.thorns_damage_pct`
- `state::tower.orb_count`
- `state::tower.orb_speed_rpm`
- `state::cards.plasma_cannon.effect_pct`
- `mechanic_param::module.orbital_augment.electron_count`
- `mechanic_param::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct`
- `mechanic_param::module.primordial_collapse.bh_damage_reduction_pct`
- `state::tower.free_attack_upgrade_chance_pct`
- `state::tower.free_defense_upgrade_chance_pct`
- `state::tower.free_utility_upgrade_chance_pct`
- `state::tower.enemy_attack_level_skip_pct`
- `state::tower.enemy_health_level_skip_pct`
- `support_surface::free_upgrade_multiplier`

### Frozen non-family canonical stat-group denominator
The non-family canonical stat-resolution denominator is frozen at **8 stat groups**.
These groups are named at the migration-planning level so PH4-C can execute in bounded slices instead of rediscovering owner scope inside `engine/stat_resolution_core.py`.

1. `survivability_pool_and_wall_stats`
   - Includes canonical survivability resolution not already frozen as declared progression-family surfaces.
   - Includes legacy-core ownership around tower/wall pools, regen, fortification, invulnerability, thorns-wall interactions, and recovery-linked survivability composition.

2. `combat_base_and_damage_pipeline_stats`
   - Includes attack speed, tower damage, crit/super-crit multipliers, damage-per-meter, knockback force, land-mine damage, and other legacy-core combat scalar composition not already governed as declared family surfaces.

3. `economy_coin_and_cash_stats`
   - Includes `coins_per_kill_bonus`, `coin_kill_multiplier`, `coin_bonus_multiplier`, `coins_multiplier`, `all_coin_bonus_multiplier`, `cash_per_wave`, `interest_per_wave_pct`, `cash_kill_multiplier`, `cells_kill_multiplier`, and related economy/currency scalar composition still owned by legacy resolution.

4. `free_upgrade_package_and_recovery_stats`
   - Includes free-upgrade multiplier/chance composition, package chance support, max recovery, recovery amount, and package/recovery bridge logic that still lands through legacy final-value truth.

5. `orb_module_and_runtime_helper_stats`
   - Includes orb-count helper resolution, Orbital Augment runtime helper composition, module runtime scalars not already frozen as declared family surfaces, and bounded runtime helper composition still resolved in legacy core.

6. `uw_mechanic_param_long_tail`
   - Includes non-family ultimate-weapon mechanic parameters still resolved through legacy destination-specific or generic mechanic composition in `engine/stat_resolution_core.py`.
   - Excludes the already-frozen timing-family surfaces above.

7. `bot_mechanic_param_long_tail`
   - Includes bot global range bonus and per-bot range, duration, cooldown, linger, multiplier, and reduction mechanic surfaces still resolved in legacy core.

8. `generic_canonical_and_mechanic_fallback_resolution`
   - Includes legacy generic bucket resolution paths that still produce canonical final values for mapped canonical/mechanic destinations not explicitly covered by the seven narrower groups above.
   - This group exists to stop silent denominator escape through "generic" logic.

### Frozen compatibility-only surface denominator
The compatibility-only denominator is frozen at **4 surface groups**.
These surfaces may remain available after Phase 4 without counting as canonical stat ownership.

1. `capability_flags_and_owned_switches`
   - `capability::*` surfaces such as owned/enabled/count style unlock flags.

2. `account_flags`
   - `account_flag::*` surfaces used as compatibility/context switches rather than canonical stat truth.

3. `account_context_and_display_surfaces`
   - `account_context::*` and similar display/context helper surfaces preserved for compatibility, reporting, or composition support.

4. `raw_unmapped_trace_rows`
   - `raw::*` preserved rows used for traceability when inputs are not yet canonically routed.

### Frozen legacy merge/reference residue denominator
The allowed legacy residue denominator is frozen at **3 residue groups**.
These may remain after PH4 cutover only if they are explicitly marked non-canonical.

1. `deprecated_transition_mirrors`
   - Example: mirror behavior such as `canonical_stat::coin_kill_multiplier` when it exists only as transition glue from `coins_per_kill_bonus`.

2. `runtime_mirror_rows_for_legacy_consumers`
   - Runtime mirror rows created only to preserve existing consumer/output compatibility while canonical ownership moves elsewhere.

3. `postprocessing_bridge_helpers`
   - Narrow postprocessing helper rows that exist only to bridge older consumer/output expectations and are not canonical truth owners.

### Frozen out-of-Phase-4 denominator
The explicit out-of-Phase-4 denominator is frozen at **4 groups**.

1. `derived_v1_query_owned_objective_surfaces`
   - `derived::ehp`, `derived::edamage`, `derived::eecon`, resource-income surfaces, and their published helper surfaces.
   - These were promoted in Phase 3 and are not Phase 4 migration targets.

2. `optimizer_simulator_advisor_product_logic`
   - Product-layer feature logic remains out of scope for PH4-A/B/C/D except where bounded consumer compatibility is necessary.

3. `run_stats_decomposition_work`
   - Broad `run_stats.py` cleanup remains Phase 6 work.

4. `inputs_ingestion_parser_compiler_cleanup`
   - CSV/IDS/parser/compiler correctness work is upstream support work and must not be relabeled as Phase 4 migration.

---

## Current-owner vs target-owner map

| frozen row | category | current owner | target owner after PH4 | allowed post-PH4 residue | notes |
|---|---|---|---|---|---|
| timing family universe (3 families / 8 surfaces) | family_scoped_canonical_resolution | `engine/stat_engine.py` compatibility entrypoint + `engine/stat_resolution_core.py` fallback for most requests; one bounded family already delegates | Query Engine family routing via `engine/stat_query_kernel.py` and governed family contracts | no canonical residue | PH4-B migration target |
| progression family universe (3 families / 18 surfaces) | family_scoped_canonical_resolution | `engine/stat_resolution_core.py` practical owner via compatibility entrypoint | Query Engine family routing via `engine/stat_query_kernel.py` and governed family contracts | no canonical residue | PH4-B migration target |
| survivability_pool_and_wall_stats | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| combat_base_and_damage_pipeline_stats | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| economy_coin_and_cash_stats | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| free_upgrade_package_and_recovery_stats | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| orb_module_and_runtime_helper_stats | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| uw_mechanic_param_long_tail | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| bot_mechanic_param_long_tail | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned stat group path | bounded temporary residue allowed only while parity is open | PH4-C migration target |
| generic_canonical_and_mechanic_fallback_resolution | non_family_canonical_stat_resolution | `engine/stat_resolution_core.py` | Query Engine-owned replacement or explicit residual classification | no silent residue | Must shrink as other groups migrate |
| capability_flags_and_owned_switches | compatibility_only_surface | compatibility path / legacy-support resolution | may remain compatibility-owned if not promoted elsewhere | yes | does not count as canonical stat truth |
| account_flags | compatibility_only_surface | compatibility path / legacy-support resolution | may remain compatibility-owned if not promoted elsewhere | yes | does not count as canonical stat truth |
| account_context_and_display_surfaces | compatibility_only_surface | compatibility path / legacy-support resolution | may remain compatibility-owned if not promoted elsewhere | yes | does not count as canonical stat truth |
| raw_unmapped_trace_rows | compatibility_only_surface | compatibility trace preservation | may remain compatibility-only | yes | not a canonical stat-resolution migration target |
| deprecated_transition_mirrors | legacy_merge_reference_residue | `engine/stat_resolution_core.py` postprocessing | non-canonical residue only if still needed | yes, temporary only | must not be called canonical owner logic |
| runtime_mirror_rows_for_legacy_consumers | legacy_merge_reference_residue | `engine/stat_resolution_core.py` postprocessing | non-canonical residue only if still needed | yes, temporary only | must be explicitly named |
| postprocessing_bridge_helpers | legacy_merge_reference_residue | `engine/stat_resolution_core.py` postprocessing | non-canonical residue only if still needed | yes, temporary only | must be explicitly named |
| derived_v1_query_owned_objective_surfaces | out_of_phase4_scope | Query Engine / Phase 3 outputs | unchanged in Phase 4 | n/a | already promoted |
| optimizer_simulator_advisor_product_logic | out_of_phase4_scope | product owners | unchanged in Phase 4 | n/a | not a PH4 migration unit |
| run_stats_decomposition_work | out_of_phase4_scope | current runtime orchestration path | Phase 6 | n/a | not a PH4 migration unit |
| inputs_ingestion_parser_compiler_cleanup | out_of_phase4_scope | Inputs / compiler owners | separate support stream | n/a | do not relabel as PH4 |

---

## Frozen parity denominator

### Family parity denominator
All **6 declared families** are in the parity denominator.
No family may be marked outside the parity denominator after PH4-A.

### Stat-group parity denominator
All **8 non-family canonical stat groups** are in the parity denominator.
Compatibility-only groups are not parity targets unless they block a canonical migration path.
Legacy residue groups require explicit bounded notes, not canonical parity claims.

---

## Frozen benchmark denominator

The benchmark denominator is frozen at **6 workloads**:

1. `timing_tournament_no_perks`
2. `timing_farm_with_perks`
3. `timing_scenario_probe`
4. `progression_start_of_run`
5. `progression_runtime_no_perks`
6. `progression_runtime_with_perks`

Benchmark intent:
- The six workloads above are the only workload families that count toward PH4 benchmark closure.
- Non-family stat-group work may attach to these workloads where relevant.
- No benchmark result counts for PH4 unless it exercises a migrated QE-owned path within one of the six frozen workloads.

---

## Migration order after PH4-A

### PH4-B
1. Cut over all 6 declared families to live QE routing.
2. Preserve explicit fallback only for rows outside the frozen family denominator.
3. Do not expand family surface scope during implementation.

### PH4-C recommended dependency order
1. `free_upgrade_package_and_recovery_stats`
2. `survivability_pool_and_wall_stats`
3. `combat_base_and_damage_pipeline_stats`
4. `economy_coin_and_cash_stats`
5. `orb_module_and_runtime_helper_stats`
6. `uw_mechanic_param_long_tail`
7. `bot_mechanic_param_long_tail`
8. `generic_canonical_and_mechanic_fallback_resolution`
9. Demote `deprecated_transition_mirrors`, `runtime_mirror_rows_for_legacy_consumers`, and `postprocessing_bridge_helpers`

Reasoning:
- shared support and package/free-upgrade composition should move before downstream consumers that rely on them
- survivability and combat groups are core canonical stat owners used by multiple later computations
- economy grouping includes bridge/helper composition that should move only after its foundational stat paths are clear
- long-tail mechanic groups should migrate after the higher-value shared stat groups are no longer forcing legacy fallback
- generic fallback must be shrunk last, not first, to avoid denominator escape

---

## Explicit stop conditions discovered during PH4-A

1. Stop if any PH4-B or PH4-C implementation attempts to migrate undeclared family surfaces.
2. Stop if any PH4-B or PH4-C implementation uses `engine/stat_resolution_core.py` as the final canonical owner for a row claimed as migrated.
3. Stop if any benchmark artifact is claimed for a workload outside the six frozen workloads.
4. Stop if parser/compiler/CSV cleanup is relabeled as Phase 4 migration work.
5. Stop if a residue row is retained after cutover without an explicit non-canonical note.

---

## Completion claim allowed after this file lands

This file supports the following bounded claim only:

> PH4-A denominator discovery is materially frozen enough for bounded PH4-B family cutover planning and Codex slicing.

This file does **not** support these claims yet:
- PH4-A is fully control-stack integrated
- PH4-B has started
- canonical stat ownership has cut over
- parity is complete
- benchmark closure is complete

---

## Recommended next action

Use this file as the execution denominator for the next bounded step:

- Codex prompt target: `PH4-B — Declared family cutover to Query Engine`
- Constraint: do not modify the frozen denominator in this file
- Constraint: do not expand beyond the 26 declared family surfaces
- Constraint: update fallback logic only for surfaces outside the frozen family denominator
