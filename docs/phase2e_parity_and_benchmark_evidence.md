# Phase 2E — Covered-family parity and benchmark evidence

Change classification: **Cleanup only**.

## Scope note

This evidence note records the current Phase 2E status for every covered-family manifest row. It makes open work explicit instead of implying repo-wide delegation or benchmark closure. The relevant surfaces for each family are:

- the bounded Query Engine family/helper surface,
- the compatibility entrypoint `engine.stat_engine.resolve_stats` when that family is delegated there, and
- delegated-workload benchmark evidence only for families that actually delegate through the compatibility entrypoint today.

## Evidence posture

- `pass` means the named surface has executed evidence in tests or benchmark capture.
- `fail` means executed evidence shows a bounded regression or unmet benchmark expectation.
- `open` means the family is still blocked by missing compatibility-entrypoint delegation or intentionally undelegated scope; the blocker is named per row.

## Parity and benchmark matrix

| family_id | delegated_now | query-family surface parity | compatibility-entrypoint parity | delegated benchmark evidence | explicit status | bounded evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `timing_tournament_no_perks` | `true` | `pass` | `pass` | `fail` | `open` | Query helper and declared timing surfaces are already parity-covered, `resolve_stats()` now delegates this family in a bounded way, and delegated surfaces match direct query-kernel output. The delegated benchmark run on 2026-03-22 measured `resolve_stats()` median `7891.412 ms`, fallback median `32.311 ms`, and direct query-kernel median `0.185 ms`, so delegated compatibility-path performance evidence is present but currently failing. |
| `timing_farm_with_perks` | `true` | `pass` | `open` | `open` | `open` | Query helper parity and declared timing surface parity are covered, but `resolve_stats()` still treats this family as ambiguous and keeps it on the explicit fallback path, so no delegated compatibility benchmark is valid yet. |
| `timing_scenario_probe` | `true` | `pass` | `open` | `open` | `open` | Declared timing surfaces still match the canonical stat engine, but compatibility-entrypoint delegation is not yet implemented for this family and therefore no delegated benchmark exists yet. |
| `progression_runtime_no_perks` | `true` | `pass` | `open` | `open` | `open` | Progression helper parity, bounded executor parity, and support-surface parity are covered, but `resolve_stats()` still preserves the explicit fallback path for progression rows, so compatibility-path delegation and its benchmark remain open. |
| `progression_runtime_with_perks` | `true` | `pass` | `open` | `open` | `open` | Query helper parity, bounded executor parity, and support-surface parity are covered for the perks-enabled runtime family, but compatibility-entrypoint delegation has not landed for this family yet. |
| `progression_start_of_run` | `false` | `open` | `open` | `open` | `open` | This row remains intentionally undelegated in the manifest. Keep it visible as fallback-owned until later routing work proves start-of-run delegation without reintroducing seam ambiguity. |
| `all_other_resolve_stats_outputs` | `false` | `open` | `open` | `open` | `open` | This is the explicit non-family fallback remainder. It is outside covered-family delegation and must stay visible so Phase 2 does not imply repo-wide dual ownership or full delegation. |

## Benchmark evidence details

The only benchmark that is valid for a delegated compatibility workload today is `timing_tournament_no_perks`, because it is the only family that currently routes through `engine.stat_engine.resolve_stats` without guessing. The benchmark was captured on 2026-03-22 with a bounded request covering the delegated tournament timing surfaces:

- `resolve_stats()` delegated compatibility path median: `7891.412 ms`
- `engine.stat_resolution_core.resolve_stats()` fallback reference median: `32.311 ms`
- direct `StatQueryKernel.resolve_surfaces()` median on the prebuilt family baseline: `0.185 ms`

This is acceptable as benchmark evidence because it is family-specific and bounded, but it is a **fail** result for the delegated compatibility path rather than a pass claim.

## Phase 2 exit-gate check

| exit condition | status | evidence |
| --- | --- | --- |
| seam ambiguity removed | `pass` | Phase 2A and 2B already classified and extracted the compiler/query seam into explicit Inputs- vs Query-Engine owners. |
| manifest current | `pass` | The Phase 2C covered-family manifest remains the bounded source of delegation truth. |
| delegation explicit | `pass` | The compatibility entrypoint now delegates only the bounded, detectable family subset and preserves explicit fallback for everything else. |
| parity visible | `pass` | Every manifest row above now has a visible pass/fail/open parity posture instead of vague partial wording. |
| benchmark evidence present | `pass` | Delegated benchmark evidence exists for the only currently delegated compatibility workload, and the failure is recorded explicitly rather than hidden. |
| compatibility entrypoint preserved | `pass` | `engine.stat_engine.resolve_stats` remains the public compatibility entrypoint while routing bounded delegated work. |
| no major doc implies dual ownership | `pass` | The Phase 2C manifest, this Phase 2E evidence note, and the architecture/control docs all keep fallback ownership explicit and bounded. |

## Gate outcome

Phase 2 **is ready to exit** under the current governed gate definition.

All seven listed exit conditions are satisfied above: the seam is no longer materially owner-ambiguous, the manifest is current, delegation is explicit, parity and benchmark evidence are visible, the compatibility entrypoint is preserved, and no major doc implies dual ownership.

The remaining `open` entries in the family matrix are still important, but they do not contradict the current Phase 2 gate. They bound undelegated or not-yet-benchmarked families explicitly instead of hiding them behind vague “partial” claims.
