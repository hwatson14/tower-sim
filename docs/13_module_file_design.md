# Module and File Design

## Purpose
This file exists only to keep future AI implementation on rails.
It is intentionally compact. It is not a final repo map.

## Design rule
Prefer **editing existing stat-engine modules** over creating new files.
Only create a new file when the responsibility is genuinely new and cannot be cleanly placed into the current calculator/stat architecture.

## Recommended top-level implementation shape

### 1. Stat engine
Owns baseline stat resolution and fixed-run perk resolution.

Recommended additions:
- `engine/perk_resolver.py`
  - input: fixed selected perk set + perk context
  - output: perk contributor/effect rows for stat aggregation
- `engine/stat_publish_contract.py` or existing equivalent contract module
  - central place for emitted canonical stats and fixed effect surfaces

Preferred if possible:
- integrate perk resolution into existing stat-engine pipeline rather than creating a standalone top-level perk engine.

### 2. Scenario-invariant derived effects engine
Owns mode, BC, heat, uptime/cooldown/sync/resistance surfaces.

Recommended files:
- `engine/scenario_invariant_engine.py`
- `engine/scenario_invariant_contract.py`

Primary outputs:
- boss hit interval surface
- BC resistance surfaces
- UW uptime/cooldown surfaces
- bot cadence surfaces
- any fixed-for-run overlap/sync surfaces

### 3. Progression engine
Owns run-evolving workshop state, wave state, and boss simulation.

Recommended files:
- `engine/progression_state.py`
- `engine/progression_recalc_bridge.py`
- `engine/boss_wave_engine.py`
- `engine/boss_ttk_solver.py`
- `engine/boss_damage_intake.py`

## File responsibility ledger
| File / module | Responsibility | New file? | Why |
|---|---|---:|---|
| `engine/perk_resolver.py` | Resolve fixed-run perk contributors inside stat engine | Yes, likely | Distinct logic, but still stat-engine-owned |
| `engine/scenario_invariant_engine.py` | Build fixed-for-run scenario-adjusted effect surfaces | Yes | New top-level owner class exists |
| `engine/scenario_invariant_contract.py` | Freeze emitted scenario-invariant surfaces | Maybe | Add only if no existing contract module fits |
| `engine/progression_state.py` | Hold workshop/wave/combat state models | Yes | Needed for explicit ownership |
| `engine/progression_recalc_bridge.py` | Call stat engine safely after workshop changes | Yes | Keeps progression from duplicating stat logic |
| `engine/boss_wave_engine.py` | Orchestrate boss-wave loop | Yes | Core new engine surface |
| `engine/boss_ttk_solver.py` | Solve percent-damage boss TTK | Maybe | Create only if logic is large enough |
| `engine/boss_damage_intake.py` | Apply boss hits, heat-up, DR, wall damage | Maybe | Create only if logic is large enough |

## What not to add yet
To avoid file bloat, do **not** add these until implementation size justifies them:
- separate top-level perk engine
- separate top-level plasma cannon adapter file
- separate top-level orb/electron cadence engines
- separate “helper” modules with vague ownership
- extra contract files if an existing contract module can hold the surfaces cleanly

## Preferred implementation sequence
1. Extend stat engine with fixed-run perk resolution
2. Add scenario-invariant engine and contract
3. Add progression state + recalc bridge
4. Add boss-wave engine
5. Split boss-wave internals into submodules only if the file becomes too large

## AI implementation guardrails
- Do not duplicate stat formulas in progression code.
- Do not put mode/BC/heat inside the stat engine.
- Do not create extra top-level engines.
- Do not create files just because a concept exists in the docs.
- Keep the initial implementation coarse-grained and verified before further decomposition.
