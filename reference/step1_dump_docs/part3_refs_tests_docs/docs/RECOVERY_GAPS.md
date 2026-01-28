# Recovery Gaps (Fail-Closed)

This bundle is *structurally complete* and importable, but not fully executable because some runtime engines were not present in the recovered artifacts.

## Missing (hard blockers)
- `sim/engines/combat_engine.py` implementation
- `sim/engines/nonboss_combat_engine.py` implementation

These are represented as fail-closed stubs that raise `CombatEngineMissing`.

## Present
- Mechanics spec surfaces (tables, registries)
- Tournament BC magnitude ingestion from Player & Stuff
- Tier BC definitions (partial, from Notion excerpt)
- Scenario runner + optimizer scaffolding (evaluation wrappers)
- Validation / invariants (fail-closed)

## Next Recovery Options
1) Recover missing combat engine modules from older "full_sim" bundles (if they exist in the old chat).
2) Rebuild combat engine deterministically from Effective Paths + wiki (high work, but possible).
