# Canonical Mechanics Contract

## Purpose
`mechanics/manifest.yaml` is the single authoritative mechanics entrypoint.

It selects exactly one active pack and runtime must resolve mechanics/formulas through that pack only.

## Authoritative Inputs (Current)
- `mechanics/manifest.yaml` (authoritative selector)
- Active pack files referenced by the manifest (currently under `tables/registry/ep_formulas/`)

## Contract Rules
1. Exactly one pack has `status: active`, and `active_pack` must match it.
2. Runtime mechanics/formulas are loaded only via `load_active_mechanics_pack()`.
3. `load_active_mechanics_pack()` fail-closes when manifest structure is invalid or referenced files are missing.
4. Runtime code must not directly load mechanics/formula YAMLs from hardcoded registry paths.
5. Do not introduce runtime path override hooks that bypass manifest-selected mechanics packs.
6. CI includes bypass guard tests to block direct-loading regressions.

## Scope boundary
This contract routes existing authoritative mechanics/formula tables only. It does not introduce new mechanics content.
