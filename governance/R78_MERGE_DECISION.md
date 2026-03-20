# R78 Merge Decision

Verdict: merged as an adapted progression-completion slice on top of the current refactored baseline.

Accepted capability:
- progression-equivalent grouping instead of raw query-bound grouping
- grouped fanout to max end-wave within each equivalent group
- dirty-state progression recompute restored
- scenario-owned progression inputs consumed by progression:
  - boss_wave_interval
  - enemy_level_skip_reduction_pp
- deterministic same-wave free-upgrade generation with no warmup skip ramp preserved
- sparse enemy table interpolation preserved

Candidate concerns found during intake:
- bundled boss-wave changes regressed existing runtime-contract compatibility until adapted
- BossWaveEngineConfig lost league/tournament_wave compatibility
- governed-runtime diagnostics and boss-hit interval precedence regressed until adapted

Adaptations applied during merge:
- preserved current runtime-contract behavior while keeping progression fixes
- restored BossWaveEngineConfig league/tournament_wave compatibility
- restored governed-runtime boss-hit-interval precedence
- restored diagnostics compatibility required by current boss-wave scaffold tests
