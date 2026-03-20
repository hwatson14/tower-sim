# Battle Condition Mechanics

This file expands battle conditions into a reasoning-ready system for tournaments and difficulty modelling.

## Design intent
Battle conditions are runtime environment modifiers, not permanent account stats. They should therefore be stored as direct environment effects and then reduced into effective values after lab mitigation.

## Canonical naming pattern
- `battle_condition__<entity>__<attribute>__<measure>`
- `derived__battle_condition__<entity>__effective_<measure>`

Examples:
- `battle_condition__enemy_attack_speed__modifier__pct`
- `battle_condition__orb_resistance__orb_damage_to_enemy_hp__pct`
- `battle_condition__ultimate_weapon_durations__duration_reduction__seconds`

## Reduction lab architecture
The KB already includes these reduction references:
- `kb/tournaments/tables/battle-condition-reduction-lab.csv`
- `kb/tournaments/tables/note-derived-battle-condition-groups.csv`
- `kb/tournaments/tables/battle-condition-reduction-baselines.csv`
- `kb/tournaments/tables/battle-condition-reduction-lab.csv`
- `kb/tournaments/tables/battle-condition-group-2-reduction-lab.csv`
- `kb/tournaments/tables/battle-condition-group-3-reduction-lab.csv`
- `kb/tournaments/tables/battle-condition-group-4-reduction-lab.csv`

Use the structure:
- generic battle condition reduction
- group 1 reduction
- group 2 reduction
- group 3 reduction
- group 4 reduction

## Resistance battle conditions

### Orb Resistance
- `battle_condition__orb_resistance__orb_damage_to_enemy_hp__pct`
- weakens orb-based deletion and pushes value toward stronger direct kill conversion

### Thorns Resistance
- `battle_condition__thorns_resistance__thorns_damage_retained__pct`
- reduces passive crash-kill reliability and weakens thorn-based eHP loops

### Death Ray Resistance
- `battle_condition__death_ray_resistance__death_ray_damage_to_enemy_hp__pct`
- turns a deletion mechanic into a chip mechanic

### Plasma Cannon Resistance
- `battle_condition__plasma_cannon_resistance__damage_retained__pct`
- materially affects boss burst handling

### Knockback Resistance
- `battle_condition__knockback_resistance__knockback_force_reduction__pct`
- reduces control radius and enemy dwell-time management

## Spawn and pressure battle conditions

### More Enemies
- `battle_condition__more_enemies__spawn_count__pct`
- increases both danger and potential economy density depending on kill throughput

### Enemy Attack Speed
- `battle_condition__enemy_attack_speed__modifier__pct`
- one of the harshest survivability modifiers because effective incoming DPS rises without needing bigger per-hit damage

### Enemy Speed
- `battle_condition__enemy_speed__modifier__pct`
- compresses control windows and reduces time available for kill conversion

### Armored Enemies
- `battle_condition__armored_enemies__blocked_hits__count`
- punishes high-hit low-impact damage patterns more than chunky burst

### More Bosses
- `battle_condition__more_bosses__boss_wave_interval__waves`
- changes encounter frequency rather than only changing scalar strength

## Defensive and system penalty battle conditions

### Energy Shields Down
- `battle_condition__energy_shields_down__recharge_time_increase__pct`
- attacks emergency recovery rather than steady-state sustain

### Death Defy Down
- `battle_condition__death_defy_down__chance_reduction__pct`
- increases tail risk near death breakpoints

### Ultimate Weapon Durations
- `battle_condition__ultimate_weapon_durations__duration_reduction__seconds`
- simultaneously reduces economy and defensive uptime for Golden Tower, Black Hole, Poison Swamp and Chrono Field

## Enemy ultimate battle conditions

### Protector's Ultimate
- `battle_condition__protector_ultimate__duration__seconds`
- `battle_condition__protector_ultimate__cooldown__seconds`
- `battle_condition__protector_ultimate__immunities__enabled`

### Tank's Ultimate
- `battle_condition__tank_ultimate__duration__seconds`
- `battle_condition__tank_ultimate__cooldown__seconds`

### Basic's Ultimate
- `battle_condition__basic_ultimate__spawn_conversion_fast__pct`
- `battle_condition__basic_ultimate__spawn_conversion_tank__pct`
- `battle_condition__basic_ultimate__spawn_conversion_ranged__pct`
- `battle_condition__basic_ultimate__spawn_conversion_boss__pct`
- `battle_condition__basic_ultimate__spawn_conversion_protector__pct`

### Boss's Ultimate
- `battle_condition__boss_ultimate__overheal__pct`

### Ranged Ultimate
- `battle_condition__ranged_ultimate__tower_disable_duration__seconds`

### Fast Ultimate
- `battle_condition__fast_ultimate__buffed_nearby_enemies__count`

## Special pressure mechanics

### Mass Enforcement
- `battle_condition__mass_enforcement__mass_gain_per_wave__pct`
- punishes slow kill conversion because pressure compounds with enemy dwell time

## Strategy interpretation

### Build invalidation rule
Some battle conditions attack specific archetypes directly:
- orb resistance vs orb kill systems
- thorns resistance vs thorn crash loops
- death ray resistance vs death ray deletion
- armored enemies vs many-hit damage patterns
- protector ultimate vs specific control and damage channels

### Mode dependence rule
The same BC can be positive or negative depending on objective. For example, More Enemies increases both pressure and possible kill-based economy. GPT reasoning should test whether the player can still kill efficiently before treating it as a benefit.

### Frequency versus severity rule
Not all BCs are scalar multipliers. More Bosses changes encounter cadence, which can be more important than a simple percentage buff.

## Quant coverage currently in KB
- battle-condition behavior reference
- battle-condition group mappings
- battle-condition reduction lab tables
- tier battle-condition level table
- archived `battle_condition_values.csv` style simplifications are intentionally excluded from the active KB

## Remaining gap
Full per-level magnitude ladders are still partial. The KB currently captures mechanic shape and reduction architecture more strongly than complete numeric severity tables.
