# R69 Incremental Benchmark Tranche

## Purpose
Measure whether the closed-subset incremental modes are materially faster than `full_safe` on the current guarded architecture.

## Scope
Benchmark only already-verified paths:
- `Health -> tower_hp -> wall_hp`
- `Enemy Attack Level Skip -> enemy_attack_level_skip_pct -> attack_wave`

## Modes compared
- `full_safe`
- `incremental_targeted_probe_guarded`
- `incremental_cached_publish_guarded`

## Guardrails
- No new formulas.
- No widening of dependency closure.
- Results are environment-local and directional.
- Any speed claim must be tied to these exact scenarios and modes only.

## Expected interpretation
- `incremental_targeted_probe_guarded` should beat `full_safe` when consumers can accept a sparse statbook.
- `incremental_cached_publish_guarded` should beat `full_safe` when a valid cached full reference statbook is available.
- If not, the architecture may still be correct but not yet worth the extra complexity.
