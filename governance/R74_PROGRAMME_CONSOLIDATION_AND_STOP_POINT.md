# R74 Programme Consolidation and Stop-Point Recommendation

## Purpose

This tranche freezes the current state of the guarded incremental stat-runtime programme so future merge work and future AI threads do not reopen already-settled decisions or overstate what has been achieved.

This is a **consolidation tranche**, not a capability tranche.

---

## Governing architecture decisions now locked

### 1. Formula truth remains in the existing stat engine
The DAG/incremental layer must **wrap** the existing calculator formulas.
It must **not** replace formula truth with a parallel mini-engine.

### 2. No stat-engine overrides allowed
Canonical bucket correctness must not depend on stat-engine postprocessing override logic.
Where necessary, canonical formulas were moved into direct resolver paths and helper/derived composition was moved outside the stat-engine core.

### 3. Dependency truth must be explicit and fail-closed
Only surfaces with explicit dependency closure are eligible for:
- guarded publication
- targeted probe execution
- cached complete-statbook publication

Everything else must fail closed to `full_safe`.

### 4. Cached complete-statbook mode is valid only with strong cache identity
Cached publication is only allowed when:
- a cached full reference statbook is supplied
- cached workshop continuity is valid outside the mutated keys
- the cached fingerprint matches the current compiled non-workshop input plane and request context

### 5. Performance claims must be benchmark-backed
Architecture completion is not enough.
Fast paths are only considered successful where benchmark evidence exists.

---

## Verified current capability set

## A. Guarded canonical publication: verified
The following workshop-mutated canonical paths are explicitly verified on the current line:

- `Health -> canonical_stat::tower_hp`
- `Health -> canonical_stat::wall_hp`
- `Orbs -> canonical_stat::tower_orb_count`
- `Defense % -> canonical_stat::tower_defense_pct`
- `Thorn Damage -> canonical_stat::tower_thorns_damage_pct`
- `Orb Speed -> canonical_stat::tower_orb_speed_rpm`
- `Free Attack Upgrade -> canonical_stat::free_attack_upgrade_chance_pct`
- `Free Defense Upgrade -> canonical_stat::free_defense_upgrade_chance_pct`
- `Free Utility Upgrade -> canonical_stat::free_utility_upgrade_chance_pct`
- `Enemy Attack Level Skip -> canonical_stat::enemy_attack_level_skip_pct`
- `Enemy Health Level Skip -> canonical_stat::enemy_health_level_skip_pct`

These are verified for the guarded line through tests and benchmark-backed execution on the promoted subset.

## B. Runtime-consumer publication: verified narrow scope only
The following runtime outputs are explicitly verified:

- `attack_wave`
- `health_wave`

These are only verified for the skip-driven runtime-consumer family and only through the guarded runtime publication path with an explicit target display wave.

No broader runtime-consumer publication should be implied.

## C. Fast paths: verified
### `incremental_targeted_probe_guarded`
Verified to skip `resolve_stats(...)` on eligible closed-subset paths and return a sparse/probe output.

### `incremental_cached_publish_guarded`
Verified to return a complete statbook from cached reference plus candidate overlay on eligible closed-subset paths, with strong cache fingerprint gating.

---

## Current benchmark-backed status

The programme now has benchmark-backed operational advantage on the current promoted subset.

### Measured headline
On the current benchmarked subset:
- targeted probe mode is strongly faster than `full_safe`
- cached publish mode is also strongly faster than `full_safe`

### Important limit
This advantage is only demonstrated for the currently promoted subset and benchmark scenarios.
It must not be generalized to all stat surfaces or all runtime consumers.

---

## What is complete

- dependency contract and mutation model
- guarded incremental planning
- parity-backed subset execution
- guarded canonical publication on the promoted subset
- removal of stat-engine override dependence for the affected line
- guarded skip-runtime publication
- targeted probe mode
- cached complete-statbook mode with strong cache fingerprint
- cost attribution benchmark
- subset executor optimisation
- overlay/publication optimisation
- explicit free-attack path verification and benchmark coverage

---

## What is not complete

- broad canonical closure across all stat surfaces
- broad runtime-consumer publication beyond skip-wave outputs
- universal incremental publication for scenario-sensitive or downstream combat surfaces
- proof that gains generalize beyond the current benchmarked subset
- final stop/go decision for further expansion

---

## Recommended stop/go decision

## Recommendation: SOFT STOP on broad expansion

The programme has now crossed the threshold of:
- architectural defensibility
- correctness gating
- real measured performance advantage

That means the main objective has been achieved **for the current promoted subset**.

Further broad expansion is now likely to produce diminishing returns unless there is a concrete downstream need for additional surfaces.

### Continue only if one of these is true
1. A downstream consumer specifically needs another canonical surface on the incremental path.
2. A downstream runtime consumer specifically needs guarded runtime publication.
3. There is evidence that another narrow family is both package-closed and high-frequency enough to matter.

### Otherwise
Prefer to consolidate, merge, and stop.

---

## Recommended next actions

### Option A: Stop after merge and use
Recommended default.

Actions:
- merge the guarded incremental line
- use the current promoted subset for repeated fast-path consumers
- only reopen expansion if a concrete missing surface becomes a real blocker

### Option B: One more narrow expansion tranche
Only if there is a known high-value missing surface with clear package closure.

### Option C: Separate production-hardening tranche
If desired, a future tranche could focus on:
- benchmark repeatability
- cache contract documentation
- CI benchmark smoke coverage
- merge cleanup and naming normalization

This is more valuable than broad surface expansion unless the product requirement says otherwise.

---

## Current completion estimate

### Honest weighted status
- Architecture/control plane: **87%**
- Verified executable incremental capability: **82%**
- Useful performance outcome: **75%**
- Overall programme: **81%**

This should be treated as the current programme completion estimate unless a future tranche materially changes either coverage breadth or measured performance.

---

## Merge guidance

This consolidation tranche should be merged after R73.
It should not be interpreted as authorization for unrestricted further DAG expansion.

The controlling rule remains:
> Expand only where package evidence closes the dependency path and benchmarked value justifies the work.

