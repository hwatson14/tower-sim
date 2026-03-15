# Tower KB index

This package is organized for **ChatGPT-first simulator use, strategy support, and theorycraft support** for the intended sim scope.

## High-value domains
- `workshop/`
- `labs/`
- `cards/`
- `modules/`
- `ultimate-weapons/`
- `combat/`
- `enemies/`
- `economy/`
- `community/`
- `advisory/`
- `ledgers/`

## Core package boundaries
- Module main-effect totals are accepted from bundled Effective Paths structured exports as package canon.
- Vault numeric bonuses may be supplied only through explicit externalized account-input surfaces.
- Same-tick precedence is intentionally out of scope except for thorns resolving immediately after incoming damage.
- Tournament BC exact rows marked unknown to community are accepted boundaries, not blockers.
- Wall Fortification unlock is resolved in-package as **Tier 14 / Wave 60**.

## First boundary and package-canon surfaces
- `kb/ledgers/tables/simulator-scope-boundary-ledger.csv`
- `kb/ledgers/tables/scope-boundary-registry.csv`
- `kb/modules/tables/module-main-effect-total-multipliers-package-canon.csv`
- `kb/economy/tables/vault-externalized-simulator-inputs.csv`

## Knowledge layers
- `tables/` → canonical mechanics
- `contracts/` → canonical semantics
- `community/` → community signal and meta observations
- `advisory/` → strategy guidance and theorycraft frameworks
- `notes/` and `sources/` → explanation and provenance only

## Canonical content rule
Use `tables/` first and `contracts/` second inside each domain for mechanics.
Use `advisory/` and `community/` for strategy, diagnosis, and theorycraft only after grounding them against canonical mechanics and boundary policy.
