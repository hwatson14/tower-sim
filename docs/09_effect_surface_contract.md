# Surface Namespace Contract

## Decision
Do **not** introduce a new top-level `effect_surface::` namespace by default.

Prefer the package's established namespaces unless a genuine unresolved surface class forces a new family:
- `canonical_stat::`
- `runtime_mechanic_param::`
- `mechanic_param::`

## Rule
Any newly emitted fixed-for-run surface for scenario or progression use should first be evaluated against the existing namespace families.

Only introduce a new namespace if:
1. the surface is not a canonical stat
2. the surface is not a runtime/mechanic parameter
3. forcing it into the existing families would create semantic confusion

## Current recommendation
- perk-derived fixed outputs that are true stat or runtime surfaces should be emitted under existing namespaces
- scenario overlays that are not emitted by the stat engine may remain internal to the scenario engine until a governed package namespace is chosen

## Anti-fragmentation rule
Do not freeze parallel naming families in docs or code without first checking the current package ledger/registry patterns.
