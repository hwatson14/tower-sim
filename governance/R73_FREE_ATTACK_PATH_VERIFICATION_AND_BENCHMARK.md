# R73 — Free Attack Upgrade Path Verification and Benchmark Extension

## Purpose
Promote `Free Attack Upgrade -> canonical_stat::free_attack_upgrade_chance_pct` from implicitly covered to explicitly verified on the guarded bridge line.

## Why this tranche
This path is already in the progression-hot dependency contract, but needed explicit end-to-end guarded publication checks on the no-override baseline.

## What changed
- Added guarded bridge verification for `incremental_publish_guarded` on `Free Attack Upgrade`.
- Added cached guarded publication verification proving the closed path can avoid `resolve_stats(...)` with a valid cache bundle.
- Extended the benchmark harness with `free_attack_canonical` so this path is measured alongside `health_canonical` and `eals_runtime`.

## KB/package basis
- `config/progression_hot_dependency_edges.csv` already records:
  - `source_input::workshop:Free Attack Upgrade -> canonical_stat::free_attack_upgrade_chance_pct`
  - `canonical_stat::free_upgrade_multiplier -> canonical_stat::free_attack_upgrade_chance_pct`
- `engine/stat_engine.py` contains the direct canonical formula path for `free_attack_upgrade_chance_pct` on the no-override line.

## Acceptance
- Guarded publication passes on the `Free Attack Upgrade` path.
- Cached guarded publication passes without calling `resolve_stats(...)`.
- Benchmark harness emits rows for `free_attack_canonical`.
