# Scenario-Invariant Derived Effects Engine — Audit Report

## Engine summary
- File: `engine/scenario_invariant_engine.py`
- Tests: `tests/test_scenario_invariant.py` — 58/58 passing
- Surfaces emitted: 46
- Provisional surfaces: 0
- Blocked surfaces: 2 (orb + electron boss hit cadence — no KB formula)
- Deferred surfaces: Group 3 enemy ultimates + mass_enforcement (not boss-v1-relevant)

## Audit results

### KB table existence: 8/8 tables verified present
| Table | Status |
|---|---|
| `kb/tournaments/tables/tier-battle-conditions.csv` | ✓ |
| `kb/tournaments/tables/battle-condition-magnitudes.csv` | ✓ |
| `kb/tournaments/tables/battle-condition-behavior-reference.csv` | ✓ |
| `kb/tournaments/tables/battle-condition-reduction-lab.csv` | ✓ |
| `kb/tournaments/tables/battle-condition-group-{2,3,4}-reduction-lab.csv` | ✓ |
| `kb/enemies/tables/boss-hit-interval.csv` | ✓ |
| `kb/enemies/tables/wiki-verified-boss-summary.csv` | ✓ |
| `kb/combat/contracts/enemy-class-interaction-matrix.csv` | ✓ |

### Doc 09 contract compliance: 11/11 surfaces
All surfaces listed in the effect surface contract doc are emitted.

### Doc 12 formula verification: 10 verified, 2 blocked
| Formula | Status | KB source |
|---|---|---|
| Boss every 10 waves | Verified | wiki-verified-boss-summary.csv |
| Boss HP x20 | Verified | wiki-verified-boss-summary.csv |
| Boss hit interval 2.0s | Verified | boss-hit-interval.csv |
| Boss heat-up +4%/hit | Verified | wiki-verified-enemy-categories + wiki-verified-baselines.md |
| Thorns boss 0.5x | Verified | enemy-class-interaction-matrix.csv, HIGH |
| Electron boss 0.25x | Verified | enemy-class-interaction-matrix.csv, HIGH |
| BC reduction formula | Verified | Architecture: penalty × (1 − lab/100) |
| CF damage reduction | Verified | canonical-formula-registry.csv + wiki |
| Enemy attack speed BC | Verified | battle-condition-behavior-reference.csv |
| UW duration BC | Verified | battle-condition-behavior-reference.csv + magnitudes.csv |
| Orb boss hit cadence | **Blocked** | No governed formula in KB |
| Electron boss hit cadence | **Blocked** | No governed formula in KB |

### Bridge key verification: 24/24 stat engine keys resolved
All keys read by `config_from_statbook()` are present and resolved in the r27 stat engine output.

### BC magnitude league uniformity: confirmed
All BC magnitudes are identical across all leagues at every wave breakpoint.
Engine correctly loads from a single league and applies uniformly.

### Edge cases: 5/5 passing
- Tournament with no league → falls back to tier BCs
- Tier < 14 → no BCs, default boss interval 10
- UW duration BC exceeds base duration → floored at 0, uptime = 0
- Milestone mode → uses tier BCs (same as farming)
- 100% BC reduction lab → removes all penalties (multiplier = 1.0)

### End-to-end with real stat engine: verified
Tested farming T14, farming T21, tournament wave 0/500/1000 — all produce correct values cross-checked against KB tables.

## Surface inventory (46 fields)

### BC Group 1 — resistance multipliers (5)
`bc_plasma_cannon_resistance`, `bc_orb_resistance`, `bc_thorns_resistance`, `bc_death_ray_resistance`, `bc_knockback_resistance`

### BC Group 2 — enemy modifiers (4)
`bc_enemy_attack_speed_increase_pct`, `bc_enemy_speed_increase_pct`, `bc_more_enemies_pct`, `bc_armored_enemies_blocked_hits`

### BC Group 4 — UW/utility/survival (4)
`bc_uw_duration_reduction_s`, `bc_enemy_level_skip_reduction_pp`, `bc_death_defy_down_pp`, `bc_energy_shields_down_fraction`

### Boss cadence (2)
`boss_wave_interval`, `boss_hit_interval_seconds`

### Boss class inherent resistances (2)
`boss_thorns_effectiveness`, `boss_electron_effectiveness`

### Environment overlays (3)
`env_enemy_damage_multiplier`, `env_boss_health_multiplier`, `env_boss_speed_multiplier`

### UW uptime (9)
BH/CF/GT: `*_effective_duration_s`, `*_effective_cooldown_s`, `*_uptime_fraction`

### CF damage reduction — KB-verified (3)
`cf_damage_reduction_pct`, `cf_avg_damage_reduction_fraction`, `cf_slow_pct`

### Bot surfaces (5)
`bot_amplify_uptime_fraction`, `bot_golden_uptime_fraction`, `bot_thunder_uptime_fraction`, `bot_flame_cooldown_s`, `bot_flame_damage_reduction_pct`

### Orb/electron pass-through (5)
`tower_orb_count`, `tower_orb_speed_rpm`, `orb_boss_hit_rate_status`, `electron_count`, `electron_boss_hit_rate_status`

### Diagnostics (4)
`mode_id`, `bc_source`, `surfaces_status`, `deferred_bc_note`
