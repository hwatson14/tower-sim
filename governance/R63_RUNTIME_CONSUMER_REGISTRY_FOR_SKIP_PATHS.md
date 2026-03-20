# R63 — Runtime consumer registry for skip-driven wave surfaces

## Purpose
Promote the first runtime consumers from implicit code knowledge to explicit, machine-readable dependency knowledge.

This tranche does **not** publish new runtime outputs through the guarded bridge. It closes a narrower gap:
- `canonical_stat::enemy_attack_level_skip_pct` is an explicit upstream of `runtime_consumer::wave_progression.attack_wave`
- `canonical_stat::enemy_health_level_skip_pct` is an explicit upstream of `runtime_consumer::wave_progression.health_wave`

## KB / package evidence
- `docs/10_workshop_dependency_ledger.md` marks the two skip canonicals as driving attack/health wave progression.
- `engine/wave_progression_policy.py` deterministically advances `attack_wave` and `health_wave` from `attack_skip_pct` and `health_skip_pct`.
- `engine/boss_wave_engine.py` reads the two canonical skip rows from the statbook and passes them into `WaveProgressionPolicy.advance_to_wave(...)`.

## Why this tranche matters
The guarded DAG line has already proven canonical publishability for EALS/EHLS.
The next safe step is not full runtime publication; it is making the direct runtime consumers explicit so later invalidation and publication work does not rely on code archaeology.

## Scope in
- explicit runtime-consumer registry module
- machine-readable CSV mirror
- tests that prove both registry shape and monotonic consumer semantics

## Scope out
- guarded bridge publication of runtime surfaces
- removing the full-safe reference path
- broader progression/runtime graph closure beyond attack-wave and health-wave consumers
