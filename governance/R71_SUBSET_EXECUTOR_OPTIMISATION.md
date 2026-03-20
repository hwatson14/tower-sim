# R71 Subset Executor Optimisation

Objective: reduce `execute_candidate_subset` overhead identified in R70 as the dominant remaining cost in the guarded incremental path.

## Changes

1. Cache canonical stat metadata at class level instead of loading on each execution.
2. Replace one-hop dependency expansion with explicit transitive upstream closure.
3. Build routed buckets only for selected executable nodes rather than all routed rows.
4. Remove contributor serialization from the guarded subset path. Candidate rows keep `contributors=[]` because current parity/publication checks compare only `final_value`, `value_type`, `status`, `source_count`, and `notes`.

## Expected effect

- Lower `execute_candidate_subset` cost in both targeted probe and cached publish modes.
- No change to formula truth because execution still reuses existing stat engine helpers.

## Verification

- Targeted tests for subset executor, bridge, and no-override rule.
- Benchmark rerun using the existing incremental benchmark harness.

## Boundary

This tranche does not broaden surface coverage. It optimizes the existing parity-proven closed subset only.
