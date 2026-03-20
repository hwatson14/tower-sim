# Iteration Plan

## Objective
Use this documentation pack as the stable starting point for iterative build-out of the engine.

## Recommended build sequence

### Phase 1: freeze contracts
- confirm canonical/fixed-effect-surface naming policy
- confirm stat-engine output contract for boss-relevant surfaces
- confirm scenario-invariant output contract
- confirm boss-wave row schema

### Phase 2: stat-engine alignment
- ensure stat engine can emit all required boss-relevant baseline and perk-adjusted surfaces
- add explicit temporary Plasma Cannon fallback note until replaced
- verify wall-related surfaces and fortification handling

### Phase 3: scenario-invariant engine
- implement mode/BC/heat overlays
- emit scenario-adjusted resistances and intervals
- emit UW/bot uptime/cooldown/sync surfaces

### Phase 4: progression engine skeleton
- track all workshop levels
- define buy/free-upgrade state structures
- define attack-wave and health-wave progression state
- wire stat recalculation calls

### Phase 5: boss-wave v1
- implement boss TTK solver for PC/orbs/electrons/thorns
- implement boss outgoing damage with heat-up
- implement wall survival ledger
- emit first-failing-boss-wave result

### Phase 6: verification pass
- verify every formula against KB sources using `12_formula_verification_ledger.md`
- verify temporary fallback use is explicit
- verify no engine duplicated stat logic outside its owner boundary
- verify naming contract compliance
- use `13_module_file_design.md` to avoid unnecessary file creation

---

## Recommended documents to add next during iteration
- `11_boss_wave_test_plan.md`
- `12_formula_verification_ledger.md`
- `13_module_file_design.md`

---

## Guidance for future iteration
- Prefer correctness and verifiability over optimisation.
- Keep top-level engine count low.
- Keep state ownership explicit.
- Push reusable fixed-for-run logic upward out of progression where possible.
- Never let temporary fallbacks become invisible permanent behavior.


## v100 integration update
- remove Plasma Cannon fallback work from the main path
- consume `runtime_mechanic_param::cards.plasma_cannon.effect_pct` directly
- treat perk resolution as already owned by calculator/compiler
- focus new closure work on boss heat-up, orb/electron cadence, and workshop dependency lineage
