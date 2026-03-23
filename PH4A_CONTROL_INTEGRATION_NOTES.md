# PH4A_CONTROL_INTEGRATION_NOTES.md

## Purpose

This is a temporary Phase 4A control artifact.

It exists because the current connector path allowed safe creation of bounded artifacts but did not provide a safe in-place edit path for the existing control files during this pass.

This file must be treated as temporary and folded into:
- `ACTIVE_TRANCHE.md`
- `BURNDOWN.yaml`

before `PH4-B` begins.

It does **not** authorize PH4-B.
It exists to keep Phase 4 on rails until the live control files are updated directly.

---

## Decision

`PH4-B` remains blocked.

The correct sequence is still:
1. finish `PH4-A`
2. integrate PH4-A control truth
3. only then begin PH4-B family cutover

---

## What is now true on `main`

1. `PH4A_CANONICAL_MIGRATION_LEDGER.md` is merged and is the working denominator artifact for Phase 4A.
2. The active tranche remains `PH4-A — Canonical migration ledger and denominator freeze`.
3. The current code path in `engine/stat_engine.py` still delegates only one bounded family:
   - `timing_tournament_no_perks`
4. All other `resolve_stats()` requests still materially depend on legacy fallback through `engine/stat_resolution_core.py`.

---

## Required control-file deltas before PH4-B

These changes must be reflected in the live control files before any PH4-B code migration begins.

### `BURNDOWN.yaml`

#### PH4-A tranche status
- `delivery_status: in_progress`
- `verification_status: partial`
- `review_status: draft`

#### PH4-A evidence path addition
Add:
- `PH4A_CANONICAL_MIGRATION_LEDGER.md`

#### Phase 4 tracked metrics deltas
Set or update the following:
- `frozen_family_denominator: verified`
- `frozen_stat_group_denominator: partial`
- `legacy_owned_canonical_stat_group_count: 8`
- `legacy_merge_reference_residue_count: 3`
- `compatibility_only_surface_count: 4`
- `out_of_phase4_scope_count: 4`
- `canonical_scope_total_count: 14`
- `canonical_scope_migrated_count: 0`

#### PH4-A blockers note
Record that PH4-B is still blocked because:
- only one manifest-approved family delegates today
- the remaining declared families still resolve through legacy fallback
- delegated timing surface naming currently mixes the declared registry path with a runtime alias path

### `ACTIVE_TRANCHE.md`

Add tranche-local notes that:
- `PH4A_CANONICAL_MIGRATION_LEDGER.md` is now merged and is the authoritative working denominator artifact for PH4-A
- PH4-B remains blocked until PH4-A control-state markers reflect the denominator freeze
- current code still delegates only `timing_tournament_no_perks`
- the timing family boundary still includes a naming mismatch that must be treated as a blocker, not silently normalized into PH4-B progress

---

## Explicit PH4-B entry blockers

### Blocker 1 — Delegation breadth is still one family
Current `engine/stat_engine.py` still delegates only:
- `timing_tournament_no_perks`

This is not enough to claim PH4-B is in progress.
PH4-B requires bounded cutover planning for all 6 declared families, but implementation must not begin while control truth still lags this reality.

### Blocker 2 — Declared timing surface set vs delegated timing alias mismatch
The declared timing family denominator includes:
- `state::cards.wave_accelerator.spawn_rate_acceleration`

Current delegated timing surface IDs in `engine/stat_engine.py` include:
- `runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration`

This mismatch may be survivable through routing aliases, but it must be handled explicitly.
It must not be silently counted as PH4-B progress.

### Blocker 3 — Legacy owner reality remains dominant
Outside the single delegated family, final canonical value ownership still materially sits in:
- `engine/stat_resolution_core.py`

PH4-B should not start while the control stack could be misread as implying broader cutover than the repo actually implements.

---

## Guardrail

No PH4-B execution is allowed until the live control files make all of the following true:

1. the PH4-A denominator artifact is named in live evidence paths
2. PH4-A is marked as materially in progress rather than not started
3. the one-family-only delegation limit is visible in control truth
4. the timing alias mismatch is visible as a blocker

---

## Recommended immediate next move

Do not start PH4-B code.

First, fold this file into:
- `BURNDOWN.yaml`
- `ACTIVE_TRANCHE.md`

Then re-check whether PH4-A can be closed or whether another bounded PH4-A cleanup pass is still required.
