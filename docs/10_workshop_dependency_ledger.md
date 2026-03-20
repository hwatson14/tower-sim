# Workshop Dependency Ledger

## Purpose
Track workshop **track-level** run-state ownership and the high-priority downstream stat dependencies relevant to the future progression engine.

This is a starter implementation ledger, not a complete proven formula-lineage table.

## Track-level starter ledger
| Workshop track | Progression-owned current level? | Recompute required? | Primary downstream emitted surfaces impacted | Notes |
|---|---:|---:|---|---|
| Health | Yes | Yes | `canonical_stat::tower_hp`, downstream `canonical_stat::wall_hp` | `wall_hp` depends on `tower_hp`; do not treat independently |
| Health Regen | Yes | Yes | `canonical_stat::tower_regen`, `canonical_stat::wall_regen` where applicable through wall path | Boss survival relevant |
| Defense % | Yes | Yes | `canonical_stat::tower_defense_pct` | Boss intake relevant |
| Thorns | Yes | Yes | `canonical_stat::tower_thorns_damage_pct` | Boss contact damage relevant |
| Orb Count | Yes | Yes | `canonical_stat::tower_orb_count` | Boss TTK relevant |
| Orb Speed | Yes | Yes | `canonical_stat::tower_orb_speed_rpm` | Boss TTK cadence input |
| Enemy Attack Level Skip | Yes | Yes | `canonical_stat::enemy_attack_level_skip_pct` | Drives `attack_wave` progression |
| Enemy Health Level Skip | Yes | Yes | `canonical_stat::enemy_health_level_skip_pct` | Drives `health_wave` progression |
| Wall Health | Yes | Yes | `canonical_stat::wall_hp` | Separate track from fortification |
| Wall Regen | Yes | Yes | `canonical_stat::wall_regen` | Separate track from health |
| Wall Fortification | Yes | Yes | `canonical_stat::wall_fortification_multiplier` | Separate multiplier, not folded into `wall_hp` |
| Free Attack Upgrade | Yes | Yes | `canonical_stat::free_attack_upgrade_chance_pct` | Progression control surface |
| Free Defense Upgrade | Yes | Yes | `canonical_stat::free_defense_upgrade_chance_pct` | Progression control surface |
| Free Utility Upgrade | Yes | Yes | `canonical_stat::free_utility_upgrade_chance_pct` | Progression control surface |

## Rule
Even if a workshop track is not yet directly consumed by v1 boss logic, progression should still track the current level if it is mutable in-run.

## Verification status
This ledger is stronger than the prior family-level view, but it is still a design/control ledger rather than a complete formula-proof ledger.
