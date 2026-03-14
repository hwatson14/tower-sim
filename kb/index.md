# Tower KB Index (v56 slice)

This repository now hosts a staged v56 KB import under `kb/`, including contracts/indexes/registries plus authoritative simulator-support tables, formula surfaces, and completeness/coverage ledgers.

## Entrypoints
- `kb/global-rules/notes/index.md`
- `kb/ledgers/notes/index.md`
- Domain indexes in `kb/*/notes/index.md` and `kb/*/tables/index.md`

## Canonical routing and naming core
- `kb/global-rules/contracts/naming-contract.yaml`
- `kb/global-rules/contracts/name-aliases.yaml`
- `kb/global-rules/contracts/aliases.yaml`
- `kb/global-rules/contracts/ids-section-routing.yaml`
- `kb/global-rules/contracts/contributors.yaml`
- `kb/global-rules/contracts/contributor-mappings-full.yaml`
- `kb/global-rules/contracts/resolvers.yaml`

## Registry surfaces in-scope for this pass
- Account-state input registries:
  - `kb/global-rules/tables/player-stuff-input-registry.csv`
  - `kb/global-rules/tables/relic-input-registry.csv`
  - `kb/global-rules/tables/theme-song-input-registry.csv`
  - `kb/global-rules/tables/unlock-input-registry.csv`
- Domain registries/routing:
  - Bots, Cards, Economy/Vault, Guardians, Labs, Perks, Ultimate Weapons
- Cross-domain ledgers:
  - `kb/ledgers/tables/canonical-id-registry.csv`
  - `kb/ledgers/tables/canonicality-registry.csv`
  - `kb/ledgers/tables/surface-status-registry.csv`
  - `kb/ledgers/tables/contributor-routing-closure.csv`

## Scope boundary for current import state
Imported: authoritative tables, formula surfaces, and completeness/coverage/subsystem ledgers used for simulator support.

Still intentionally excluded: full validation harness bundles, advisory/community strategy corpora, and release/handoff packaging debris.
