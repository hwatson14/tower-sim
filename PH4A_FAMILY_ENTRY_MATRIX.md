# PH4A_FAMILY_ENTRY_MATRIX.md

## Purpose

This file freezes the practical entry boundary between `PH4-A` and `PH4-B`.

The Phase 4 denominator is already frozen in `PH4A_CANONICAL_MIGRATION_LEDGER.md`.
This file adds the missing operational matrix:
- what each declared family currently does in repo truth
- what the tests currently enforce
- what must change before `PH4-B` can legitimately move from blocked entry state into bounded implementation

This file is a Phase 4A artifact.
It does **not** authorize broad family cutover.

---

## Declared family universe

The governed family universe remains:

### Timing
- `timing_tournament_no_perks`
- `timing_farm_with_perks`
- `timing_scenario_probe`

### Progression
- `progression_start_of_run`
- `progression_runtime_no_perks`
- `progression_runtime_with_perks`

This file does not change that denominator.

---

## Current repo-truth family matrix

| family_id | declared by contract | current resolve_stats routing | current test posture | PH4-B eligible now? | blocker |
|---|---:|---|---|---:|---|
| `timing_tournament_no_perks` | yes | delegated through query kernel when the bounded timing predicate and `preset_name == Tourney` both hold | explicitly tested as delegated | partial only | still uses bounded heuristic gating rather than family-complete cutover surface |
| `timing_farm_with_perks` | yes | explicit fallback through legacy path | explicitly tested as **not** delegated when ambiguous | no | family remains blocked by ambiguity and unresolved naming/routing boundary |
| `timing_scenario_probe` | yes | explicit fallback through legacy path | no explicit start-of-PH4 delegation test proving cutover readiness | no | no current delegation path and no bounded cutover proof |
| `progression_start_of_run` | yes | explicit fallback through legacy path | progression fallback behavior covered broadly as undelegated | no | no current family routing path |
| `progression_runtime_no_perks` | yes | explicit fallback through legacy path | progression fallback behavior covered broadly as undelegated | no | no current family routing path |
| `progression_runtime_with_perks` | yes | explicit fallback through legacy path | progression fallback behavior covered broadly as undelegated | no | no current family routing path |

---

## Current code-truth constraints

### Constraint 1 — one-family-only delegation
`engine/stat_engine.py` currently hardcodes only one manifest-approved delegated family:
- `timing_tournament_no_perks`

No other declared family has a live family-routing path at the compatibility entrypoint.

### Constraint 2 — timing routing is still heuristic-gated
Delegation currently depends on both:
- `_looks_like_timing_family_rows(stat_inputs)`
- `preset_names == {'Tourney'}`

That means current delegation is still a bounded compatibility proof, not declared-family cutover.

### Constraint 3 — delegated timing surface naming is not yet denominator-clean
The current delegated timing surface IDs include:
- `runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration`

The declared timing denominator in `PH4A_CANONICAL_MIGRATION_LEDGER.md` uses:
- `state::cards.wave_accelerator.spawn_rate_acceleration`

This mismatch must be resolved or explicitly normalized before PH4-B can move beyond blocked entry state.

### Constraint 4 — fallback remains the practical owner for all other families
Outside the one delegated timing family, `resolve_stats()` still falls back to:
- `engine.stat_resolution_core.resolve_stats`

That remains the practical canonical owner path for undelegated family resolution today.

---

## Current test-truth matrix

The current tests enforce these rules:

1. `timing_tournament_no_perks`
   - delegates when unambiguous
   - preserves fallback rows that are not part of the delegated family merge

2. progression rows
   - must remain on the explicit fallback path
   - any attempt to delegate them today is treated as wrong

3. ambiguous timing families
   - must not be delegated yet
   - current tests explicitly reject implying broader timing-family cutover

Therefore the current automated truth is aligned with a **PH4-A complete / PH4-B blocked at entry** interpretation, not a PH4-B implementation-underway interpretation.

---

## PH4-B entry criteria

`PH4-B` may move from blocked entry state into bounded implementation only when all of the following are true:

1. `ACTIVE_TRANCHE.md` and `BURNDOWN.yaml` explicitly reflect that PH4-A denominator freeze is complete and PH4-B is the active tranche.
2. The active control truth no longer leaves the one-family-only delegation limit implicit.
3. The timing-family surface naming mismatch has an explicit disposition:
   - resolved to the declared denominator, or
   - explicitly normalized as an accepted alias path.
4. There is an explicit family-routing plan for all 6 declared families, even if implementation remains bounded and sequential.
5. No current test still encodes the assumption that broader family cutover would be wrong **unless** that test is intentionally rewritten as part of PH4-B entry.

If any of these are false, PH4-B remains blocked.

---

## PH4-B first-slice recommendation

When PH4-B does move into bounded implementation, the first implementation slice should be:

1. convert the current delegated timing family from heuristic compatibility proof into declared-family routing owned by the PH4 denominator
2. resolve the `wave_accelerator.spawn_rate_acceleration` naming boundary explicitly
3. only then widen timing-family coverage to the remaining declared timing families
4. only after timing-family routing is explicit should progression-family routing begin

This preserves the current test truth instead of breaking it all at once.

---

## Non-goals

This file does not:
- begin broad PH4-B implementation
- rewrite tests
- change current family routing
- change the denominator frozen in `PH4A_CANONICAL_MIGRATION_LEDGER.md`

---

## Current conclusion

The correct current reading of repo truth is:

- `PH4-A` is complete as a control-and-ledger tranche
- `PH4-B` is the active tranche but remains blocked at the entry boundary
- only one declared family has bounded live delegation today
- the test suite still enforces fallback for every other family class
- therefore PH4-B has not moved into bounded implementation yet and should not be claimed as broadly underway
