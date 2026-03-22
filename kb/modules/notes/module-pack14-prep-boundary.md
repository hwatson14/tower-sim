# Pack14 module prep boundary

Change classification: **KB correction** plus **routing/contract prep** with no live runtime execution.

## Source-closed cost truth now owned under `kb/modules/`

Canonical KB truth in this tranche:

- Module gem draw prices (`20` for single, `200` for ten-pull).
- Module shatter yields (`5` shards for Common, `10` shards for Rare).
- Assist-slot unlock cost (`1000` stones per slot unlock).
- Rerolls consume reroll shards and lock state increases reroll cost.

These are now restated in concise Pack14-prep tables so downstream work can fail closed on a module-owned source instead of reaching back into prose summaries.

## Workbook-derived assumptions classified

### Canonical KB truth

- None of the workbook-derived module helper ladders are promoted to canonical cost truth in this tranche.
- Workbook-backed module main-effect tables remain canonical for the **main-effect multiplier ladder only**, as already documented in `kb/modules/sources/module-main-effect-source-closure.md`.

### Accepted-model helper logic

- `assist-unique-rarity-upgrade-costs.csv` remains accepted-model helper material because the current provenance is prompt-materialized rather than row-closed from the live wiki or a first-party export.
- Effective Paths workbook material may continue to support helper planning notes and package-canon main-effect closure, but it must not be silently promoted into new module economy or reroll canon.
- `kb/modules/tables/module-workbook-assumption-registry.csv` now records which workbook-derived assumptions are canonical owners versus accepted-model helper logic so downstream loaders can fail closed on provenance rather than ad hoc interpretation.

## Future optimizer consumer bundle boundary

The future Pack14 optimizer-facing module bundle is drafted in `kb/modules/contracts/module-pack14-nonruntime-draft.yaml` as:

- `consumer_id: optimizer_analysis`
- `bundle_id: optimizer_module_effects`
- Family scope: progression families only
- Required surface: `mechanic_param::module.primordial_collapse.bh_damage_reduction_pct`
- Optional surfaces:
  - `mechanic_param::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct`
  - `mechanic_param::module.orbital_augment.electron_count`

This keeps the draft bounded to already-governed progression-family module surfaces and explicitly avoids crossing into the timing-family `support_surface::timing.gcomp_cooldown_reduction_seconds` seam during Pack14 prep.

## Overlay delta requirements

For future optimizer experimentation, the only drafted overlay classes in the non-runtime draft are:

- required: `module_assertions`
- optional: `assist_slot_choice`

Everything else stays out of scope for this prep tranche, especially live scoring execution, account-state deep-copy mutation flows, and any new routing through the current compiler-owned seam.
