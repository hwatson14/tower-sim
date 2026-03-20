# R68 Strong Cache Fingerprint Guard

## Purpose
Strengthen `incremental_cached_publish_guarded` so cache reuse is bound to package-verifiable upstream identity, not only workshop continuity.

## Decision
Cache validity now requires both:
1. Workshop continuity outside mutated keys.
2. Exact fingerprint match for the current non-workshop compiled stat-input plane and request execution context.

## Fingerprint scope
The fingerprint is built from:
- all compiled `StatInput` rows where `source_family != workshop`
- `state_mode`
- `preset_name`
- `card_preset_name`
- `module_preset_name`
- `perk_preset_name`
- `perks_enabled`
- `perk_counts_override`

## Why this is package-grounded
This package already compiles all upstream contributors into `StatInput` rows before stat resolution. Using the non-workshop compiled input plane as the cache identity source is therefore grounded in the existing calculator pipeline rather than an invented external manifest.

## Safety effect
Cached complete-statbook publication now fails closed when:
- the caller does not provide a cached fingerprint
- the cached fingerprint is malformed
- any non-workshop compiled input or execution context differs from the current request
- workshop levels differ outside the mutated keys

## Deliberate limitation
This is stronger than the previous workshop-only check, but it is still not a full global state hash of every raw source artifact. It is a calculator-pipeline fingerprint anchored to compiled non-workshop inputs plus request context.
