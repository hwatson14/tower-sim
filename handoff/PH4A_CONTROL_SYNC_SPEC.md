# PH4A_CONTROL_SYNC_SPEC.md

## Role

This file is the final PH4-A control-sync specification.

It exists because the available GitHub connector path can safely create new bounded artifacts, but it cannot safely update existing files such as `ACTIVE_TRANCHE.md` and `BURNDOWN.yaml` through the exposed high-level interface.

This file is therefore the exact repo-truth sync specification for the remaining PH4-A closeout step.

---

## Current repo truth

The following PH4-A artifacts are already merged on `main`:
- `PH4A_CANONICAL_MIGRATION_LEDGER.md`
- `PH4A_FAMILY_ENTRY_MATRIX.md`

The following repo-truth facts are also already true:
- active tranche remains `PH4-A`
- only `timing_tournament_no_perks` has bounded live delegation today
- all other declared families remain on explicit fallback
- current tests still enforce one-family-only delegation plus fallback for other family classes

The remaining inconsistency is in the live control files.

---

## Required control sync

### ACTIVE_TRANCHE.md must visibly state

1. `PH4A_CANONICAL_MIGRATION_LEDGER.md` is merged and is the bounded working denominator artifact for PH4-A.
2. `PH4A_FAMILY_ENTRY_MATRIX.md` is merged and freezes the practical PH4-B entry boundary.
3. PH4-B remains blocked until live control-state markers reflect the denominator freeze and the one-family-only delegation limit is visible in control truth.
4. Current code still delegates only `timing_tournament_no_perks`; all other declared families remain on explicit fallback through legacy resolution.
5. The timing-family naming mismatch between the declared denominator surface `state::cards.wave_accelerator.spawn_rate_acceleration` and the current delegated runtime alias path must be treated as a blocker, not as PH4-B progress.

### BURNDOWN.yaml must be updated to reflect

#### PH4-A tranche status
- `delivery_status: in_progress`
- `verification_status: partial`
- `review_status: ready_for_review`

#### PH4-A evidence paths must include
- `PH4A_CANONICAL_MIGRATION_LEDGER.md`
- `PH4A_FAMILY_ENTRY_MATRIX.md`

#### Phase 4 tracked metrics must read
- `frozen_family_denominator: verified`
- `frozen_stat_group_denominator: partial`
- `migrated_family_count: 0`
- `migrated_stat_group_count: 0`
- `parity_covered_family_count: 0`
- `parity_covered_stat_group_count: 0`
- `benchmarked_migrated_workload_count: 0`
- `explicit_residual_bucket_count: 7`
- `legacy_owned_canonical_stat_group_count: 8`
- `legacy_merge_reference_residue_count: 3`
- `compatibility_only_surface_count: 4`
- `out_of_phase4_scope_count: 4`
- `canonical_scope_total_count: 14`
- `canonical_scope_migrated_count: 0`

#### PH4-A stop conditions must additionally make visible
- stop if PH4-B starts while only one declared family has live delegation at the compatibility entrypoint
- stop if the timing-family surface naming mismatch remains implicit rather than explicitly resolved or normalized

---

## Intended interpretation after sync

After the live control files are updated to match this specification, the correct reading of repo truth becomes:

- PH4-A is materially in progress
- denominator freeze is evidenced in both artifact truth and control truth
- PH4-B remains blocked by explicit entry criteria rather than by unstated repo knowledge
- no control file implies that PH4-B has already started

---

## Non-goals

This file does not:
- begin PH4-B
- authorize code migration
- rewrite tests
- change current family routing
- change the frozen denominator already on `main`

---

## Recommendation

Use this file only as a short-lived sync artifact.

Once `ACTIVE_TRANCHE.md` and `BURNDOWN.yaml` are directly updated, this file can be deleted or archived because its purpose will have been absorbed into live control truth.
