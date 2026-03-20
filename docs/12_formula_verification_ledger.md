# Formula Verification Ledger

## Status meanings
- **Verified**: closed enough in the current package/KB to implement without treating as open
- **Accepted model constant**: package-accepted modeled value; usable, but provenance is weaker than wiki-verified
- **Blocked**: not yet emitted or not yet governed tightly enough for direct implementation

| Item | Status | Owner | Evidence basis | Implementation note |
|---|---|---|---|---|
| Boss heat-up | Verified | Progression engine | `kb/enemies/tables/wiki-verified-enemy-categories-and-shared-rules.csv`; `kb/global-rules/sources/wiki-verified-baselines.md` | Use +4% per completed prior hit while alive |
| Electron boss effect | Verified | Progression engine | `kb/modules/contracts/module-unique-runtime-semantics.md`; `kb/combat/contracts/enemy-class-interaction-matrix.csv` | 15% remaining HP; quarter effective vs bosses |
| Thorns boss effect | Verified | Progression/scenario composition | `kb/combat/contracts/enemy-class-interaction-matrix.csv`; `kb/combat/contracts/runtime-effect-catalog.csv` | Half effective on bosses before other scenario resistances |
| Boss HP multiplier | Verified | Progression engine | `kb/enemies/tables/wiki-verified-boss-summary.csv` | x20 vs common enemy HP |
| Boss HP source enemy type | Verified | Progression engine | enemy taxonomy / tables in package | Use **common enemy HP**, not vague “basic enemy” wording |
| Boss hit interval | Accepted model constant | Scenario engine | `kb/enemies/tables/boss-hit-interval.csv`; formula coverage ledgers | Use 2.0s with provenance note |
| Plasma Cannon effect surface | Verified | Stat engine output | emitted `runtime_mechanic_param::cards.plasma_cannon.effect_pct` | No external fallback |
| Wall fortification multiplier surface | Verified | Stat engine output | canonical stat emission + compiler/stat engine mappings | Keep separate from `wall_hp` |
| Wall fortification formula family | Verified | Stat engine | current package calc path | Add explicit dependency note in recalc docs |
| Wall HP depends on tower HP | Verified | Stat engine / recalc bridge | current package calc path | Progression must always use full recompute |
| Orb boss cadence surface | Blocked | Scenario engine target | no governed emitted cadence surface yet | use explicit scenario override if needed |
| Electron cadence surface | Blocked | Scenario engine target | no governed emitted cadence surface yet | use explicit scenario override if needed |

## Rules
1. Do not downgrade provenance: `Accepted model constant` is usable but not the same class as wiki-verified.
2. Do not leave stale fallback language in docs once the package emits a governed surface.
3. Any blocked cadence item must be either promoted to a governed surface or kept as an explicit scenario override.
