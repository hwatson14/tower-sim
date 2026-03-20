# R53 Stat compilation audit: wall HP and free upgrades after override removal

## Scope
Audit the four formerly overridden canonicals after removing bespoke stat-engine correction helpers:
- `canonical_stat::wall_hp`
- `canonical_stat::free_attack_upgrade_chance_pct`
- `canonical_stat::free_defense_upgrade_chance_pct`
- `canonical_stat::free_utility_upgrade_chance_pct`

## Verdict
These four surfaces are **not yet accurate** through pure routed compilation.

### Free upgrades
Current rebuilt values:
- attack = 96.75
- defense = 93.75
- utility = 105.55

Known expected farming values from prior validation:
- attack = 107.7384
- defense = 104.6892
- utility = 118.28544

Interpretation:
- the shared `canonical_stat::free_upgrade_multiplier` enhancement support row still exists and resolves to `1.12`
- after removing the exact post-resolution helper, that support multiplier is no longer promoted into the three published free-upgrade canonicals
- therefore current compiled values are under by exactly the missing enhancement factor

### Wall HP
Current rebuilt value:
- wall_hp = 1958.88 in package rebuild

Independent unit test still fails:
- obtained = 1749.0
- expected = 1669.5

Interpretation:
- wall HP remains semantically unstable after override removal
- a pure routed + generic resolver path is still not producing the validated expected wall formula shape
- the package rebuild value also remains EP-mismatched

## Immediate implication
Override removal was correct, but it exposed two real remaining stat-compilation gaps:
1. free-upgrade support multiplier promotion
2. wall-HP semantic formula ownership
