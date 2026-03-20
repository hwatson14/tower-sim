# R62 Publishable Subset Expansion: Free Upgrades and Skip Surfaces

## Scope
This tranche promotes four already-configured canonical paths from implicit coverage to explicit verified publishable coverage on the R54 routed-repairs baseline after the no-override stat-engine refactor:

- `Free Defense Upgrade -> canonical_stat::free_defense_upgrade_chance_pct`
- `Free Utility Upgrade -> canonical_stat::free_utility_upgrade_chance_pct`
- `Enemy Attack Level Skip -> canonical_stat::enemy_attack_level_skip_pct`
- `Enemy Health Level Skip -> canonical_stat::enemy_health_level_skip_pct`

## Why this tranche is valid
These paths were already present in the dependency contract and mutation ledger. This tranche does not invent new edges; it adds the missing execution verification so these paths are explicitly locked as guarded-publishable on the current baseline.

## KB / package verification basis
Verified from package routing and current calculator behavior:

- `kb/ledgers/tables/contributor-routing-closure.csv` registers workshop routing for all four canonical targets.
- `config/destination_formula_ledger.yaml` and current stat-engine resolution already support the target canonical surfaces on the no-override baseline.
- The free-upgrade surfaces explicitly depend on `canonical_stat::free_upgrade_multiplier`, which remains in the closed subset as a support node.
- The skip surfaces are direct canonical outputs and are also runtime consumers for progression (`attack_wave`, `health_wave`), but this tranche promotes only the canonical publish path, not the runtime consumer publication.

## What changed
Only targeted verification files changed:
- `tests/test_incremental_subset_executor.py`
- `tests/test_progression_recalc_bridge.py`

## Acceptance criteria
- Subset executor exact-match parity on all four promoted canonical paths.
- Bridge `incremental_publish_guarded` returns `published_candidate_overlay_over_full_reference` with parity `pass` for workshop-triggered recomputes on all four paths.
- No stat-engine override logic is reintroduced.

## Out of scope
- No new dependency edges.
- No derived/runtime publication expansion beyond the canonical targets.
- No speed claim or removal of the full-safe reference path.
