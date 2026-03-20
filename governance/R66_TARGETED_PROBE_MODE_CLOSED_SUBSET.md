# R66 Targeted Probe Mode for Closed Subset

## Purpose
Introduce a guarded bridge mode that can publish a **partial statbook** for the already-verified closed subset without computing the full-safe reference statbook on eligible paths.

## New mode
- `incremental_targeted_probe_guarded`

## Scope
Eligible only when incremental planning does **not** require fallback.

Returned statbook scope:
- partial candidate subset only
- rows are emitted directly from `IncrementalSubsetExecutor`
- no overlay against full-safe reference occurs in this mode

## Why this is allowed
This mode relies on subset paths that were already parity-proven in prior tranches:
- health -> tower_hp -> wall_hp
- orb count
- defense
- thorns
- orb speed
- free-upgrade canonical paths
- EALS / EHLS canonical paths
- skip-driven runtime outputs for explicit target wave requests

The mode is therefore a **deployment of previously verified subset execution**, not a new formula source.

## Runtime outputs
When `runtime_target_display_wave` is supplied and the dirty plan impacts registered skip consumers, this mode publishes runtime outputs from the probe subset only:
- `attack_wave`
- `health_wave`

## Fail-closed behavior
If incremental planning reports fallback required:
- bridge returns ordinary full-safe statbook
- diagnostics status = `fallback_full_safe`

## Important boundary
This mode is **not** a complete incremental replacement.
It only removes full-safe reference precompute for the already-closed subset and still returns a partial statbook.
