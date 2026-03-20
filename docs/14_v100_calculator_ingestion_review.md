# r25 Calculator Ingestion Review

## Purpose
Record what the completed `tower_stat_calc_r25__self_contained_ai_handover.zip` changes for the wave-engine architecture and which previously-open assumptions are now closed.

## Ingestion summary
The r25 calculator package was unpacked and reviewed at the control-plane, compiler, engine, output, and final-ledger levels.

Reviewed directly:
- `START_HERE_FOR_AI.md`
- `FINAL_AUDIT_SUMMARY.md`
- `VERIFICATION_COMPLETENESS_STATUS.md`
- `FINAL_PRE_HANDOVER_AUDIT.md`
- `MASTER_SURFACE_TRUST_LEDGER.csv`
- `compilers/stat_input_compiler.py`
- `engine/stat_engine.py`
- `config/destination_formula_ledger.yaml`
- `FINAL_ALL_CALCULATED_STATS.csv`
- `output/statbook_publishable.json`

## Calculator-level verdict
The package presents itself as a curated AI-facing KB suitable for practical deterministic modelling within declared simulator scope boundaries, not exact tick/frame replay. This package includes stronger governance ledgers, perk timeline integration, and emitted surfaces needed for future wave-engine work. It should be treated as the current working baseline, subject to the user's note that final bug fixes are still landing.

## Engine-relevant findings

### 1. Plasma Cannon surface is now emitted
Previously-open fallback planning can be retired for the current calculator. The package now emits:
- `runtime_mechanic_param::cards.plasma_cannon.effect_pct`

This appears in:
- `FINAL_ALL_CALCULATED_STATS.csv`
- `output/statbook_publishable.json`
- `config/destination_formula_ledger.yaml`

This materially improves the boss TTK design because Plasma Cannon no longer needs an external card-level adapter in the intended implementation path.

### 2. Perks are already integrated into the calculator path
The current calculator/compiler path already treats perks as a contributor family. Evidence:
- `compilers/stat_input_compiler.py` stage support includes `perk`
- perk entities/effects are loaded from `kb/perks/tables/*`
- active perk selections are read and scaled using perk lab context
- perk effects are bound into canonical or runtime destinations
- outputs include runtime perk parameters such as:
  - `runtime_mechanic_param::perk.free_upgrade_chance_all_pct`
  - `runtime_mechanic_param::perk.wave_requirement_multiplier`
  - `runtime_mechanic_param::perk.max_game_speed`
  - `runtime_mechanic_param::perk.enemy_kill_cash_multiplier`

Architectural consequence: do not build a separate top-level perk engine. Treat perk resolution as part of the stat-engine/compiler system.

### 3. Wall Fortification remains separate from wall HP
The calculator emits:
- `canonical_stat::wall_fortification_multiplier`

This confirms the earlier architectural decision that wall fortification should remain a distinct consumed surface unless the calculator itself is later changed to publish a pre-folded effective wall pool.

### 4. The calculator already emits several boss-engine-critical surfaces
Confirmed emitted publishable surfaces include:
- `canonical_stat::enemy_attack_level_skip_pct`
- `canonical_stat::enemy_health_level_skip_pct`
- `canonical_stat::tower_orb_count`
- `canonical_stat::tower_orb_speed_rpm`
- `canonical_stat::free_attack_upgrade_chance_pct`
- `canonical_stat::free_defense_upgrade_chance_pct`
- `canonical_stat::free_utility_upgrade_chance_pct`
- `mechanic_param::module.orbital_augment.electron_count`

Architectural consequence: these should be consumed directly by future engines rather than re-derived externally.

### 5. The calculator already has the right recalc spine
The package structure supports the recommended recompute path:
- `account_state_compiler.py`
- `stat_input_compiler.py`
- `stat_engine.py`

Architectural consequence: the progression engine should call this path, or a safely-factored equivalent, whenever workshop-driven run state changes require refreshed current stats.

## What remains open after r25 ingestion

### Still open
- exact boss heat-up closure for final implementation wording/ownership
- orb and electron boss contact cadence surfaces if you want them governed rather than scenario-configured
- full formula lineage for every workshop dependency used by the future progression engine
- precise integration design for mode / BC / heat overlays outside the stat engine

### Closed or materially reduced
- Plasma Cannon fallback requirement
- uncertainty about whether perks should be resolved inside the stat engine
- uncertainty about whether wall fortification is separate from wall HP

## Integration decisions triggered by r25
1. Remove any planned external Plasma Cannon fallback from the primary design path.
2. Keep perks folded into the stat engine/compiler path.
3. Keep mode, BC, and heat outside the stat engine.
4. Keep progression responsible for dynamic workshop state plus stat-engine recompute triggers.
5. Keep wall fortification as a separate consumed canonical stat.

## Revised confidence

### High confidence
- 3 top-level engine split remains correct
- perk resolution belongs in stat engine/compiler path
- progression needs recompute through calculator path
- Plasma Cannon emitted surface exists now

### Medium confidence
- current docs pack is now materially closer to implementation reality
- r25 reduces previous architecture uncertainty enough to start code scaffolding

### Remaining caution
Do not over-read package completeness claims as proof that all future wave-engine mechanics are closed. The calculator is strong on stat emission, but some boss-engine runtime behaviours remain outside the current closed set.
