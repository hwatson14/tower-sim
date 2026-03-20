# R59 DAG rebase to latest R54 routed-repairs baseline

This tranche rebases the incremental dependency-runtime programme onto the user-supplied `tower_stat_calc_r54_routed_repairs` package and treats that package as the sole source baseline.

## Verified package-grounded decisions
- Formula truth remains in `engine/stat_engine.py`.
- `engine/progression_recalc_bridge.py` still uses full safe recompute by default.
- Contributor routing closure confirms direct routes for:
  - `tower_orb_count`
  - `enemy_attack_level_skip_pct`
  - `enemy_health_level_skip_pct`
  - `free_upgrade_multiplier`
- Compiled workshop-state mutability supports workshop-source invalidation for:
  - `Health`
  - `Orbs`
  - `Free Attack Upgrade`
  - `Free Defense Upgrade`
  - `Free Utility Upgrade`
  - `Enemy Attack Level Skip`
  - `Enemy Health Level Skip`
- Wall regen and wall fortification are not treated as workshop-source mutation triggers in this programme.

## What this tranche adds
- Dependency registry and machine-readable progression-hot config.
- Guarded incremental planning.
- Candidate closed-subset executor using existing stat-engine helpers.
- Exact parity harness against full-safe statbook.
- Guarded publish overlay path for parity-passed candidate rows.

## Guardrails
- Full-safe recompute remains the truth path.
- Incremental publication is only an overlay onto a complete reference statbook.
- Unsupported mutation keys fail closed to full-safe recompute.
- No runtime speed claim is made in this tranche.
