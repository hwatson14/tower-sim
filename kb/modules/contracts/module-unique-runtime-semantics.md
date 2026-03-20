# Module Unique Runtime Semantics v5

Status: materially tightened. Quantitative values are covered; this file formalises runtime contracts for the module unique effects most likely to be simulated incorrectly.

## Source ranking

1. Epic Module Unique Effect wiki page for named effect text and rarity values.

2. Modules wiki page for assist-module behavior, hard-cap note, and unique-effect eligibility.

3. Repo `tower_sim/libs/modules_library.py` as normalized transcription of wiki tables.


## Global rules

- Only modules naturally drawn as Epic have unique effects; merging rares to Epic does not create a unique effect.

- Assist modules provide weaker versions of unique effect, main effect, and substats; assist unique rarity starts at Epic and can be upgraded.

- Assist substats do not bypass hard caps such as 98% Defense, 90% Chrono Field speed reduction, 150s Wall Rebuild, 7s Shockwave Frequency, 40% Death Defy, and 37s Inner Land Mine cooldown.

- Quantity-style assist contributions use FLOOR rather than ROUND.


## High-value mechanic contracts

### Death Penalty (Cannon)

- Trigger: on_enemy_spawn_then_on_first_hit

- Runtime contract: At enemy spawn roll listed chance; if marked, first subsequent hit destroys that enemy regardless of ordinary damage pipeline.

- Rarity values: Epic 5.0, Legendary 8.0, Mythic 11.0, Ancestral 15.0

- Special rules: Marked enemy is destroyed by first hit.

- Confidence: high


### Amplifying Strike (Cannon)

- Trigger: on_boss_or_elite_kill

- Runtime contract: Killing a boss or elite grants 5x tower damage for listed seconds; a new valid kill refreshes timer rather than stacking multiplier.

- Rarity values: Epic 5.0, Legendary 11.0, Mythic 18.0, Ancestral 26.0

- Special rules: Wiki note: does Impact UW damage; new boss/elite kill refreshes duration.

- Confidence: high


### Anti-Cube Portal (Armor)

- Trigger: on_shockwave_hit

- Runtime contract: When shockwave registers a hit, apply listed damage-taken multiplier to that enemy for 7s even if the enemy is immune to the shockwave movement/effect.

- Rarity values: Epic 10.0, Legendary 15.0, Mythic 20.0, Ancestral 25.0

- Special rules: Enemies still count as hit even if immune to shockwave effects.

- Confidence: high


### Negative Mass Projector (Armor)

- Trigger: on_orb_nonkill_hit

- Runtime contract: If an orb hits and does not kill, add listed reduction to both enemy damage and speed, stacking additively until total reduction reaches 50%.

- Rarity values: Epic 1.0, Legendary 1.5, Mythic 2.0, Ancestral 2.5

- Special rules: Orb hit still counts for effect logic even if enemy is immune to orb effect; only if orb does not kill.

- Confidence: high


### Space Displacer (Armor)

- Trigger: on_landmine_spawn

- Runtime contract: Each landmine spawn rolls listed chance to become an autonomous Inner Land Mine subject to 20 max; damage/stat source depends on whether ILM UW is unlocked.

- Rarity values: Epic 15.0, Legendary 20.0, Mythic 25.0, Ancestral 30.0

- Special rules: If ILM UW unlocked, uses player ILM stats/effects; otherwise uses level-1 x30 damage multiplier. Chance applies to normal landmine spawns.

- Confidence: high


### Orbital Augment (Armor)

- Trigger: while_orbital_system_active

- Runtime contract: Spawn listed number of Electrons. On Electron hit, deal 15% of current remaining HP, multiplied by 0.25 against Bosses and Fleets.

- Rarity values: Epic 2.0, Legendary 4.0, Mythic 6.0, Ancestral 8.0

- Special rules: Each Electron deals 15% of enemy remaining health; quarter effective against Bosses and Fleets.

- Confidence: high


### Galaxy Compressor (Generator)

- Trigger: on_recovery_package_collected

- Runtime contract: When a recovery package is collected, reduce cooldown of all eligible Ultimate Weapons (UWs) except Poison Swamp by listed seconds.

- Rarity values: Epic 10.0, Legendary 13.0, Mythic 17.0, Ancestral 20.0

- Special rules: Wiki explicitly excludes Poison Swamp.

- Confidence: high


### Pulsar Harvester (Generator)

- Trigger: on_projectile_hit

- Runtime contract: Each projectile hit rolls listed proc chance; on proc, reduce both enemy Health level and Attack level by 1, with diminishing returns after 100 total reductions on that enemy.

- Rarity values: Epic 1.0, Legendary 1.5, Mythic 2.0, Ancestral 2.5

- Special rules: Each proc reduces both Health and Attack level by 1.

- Confidence: high


### Black Hole Digestor (Generator)

- Trigger: on_free_upgrade_triggered_this_wave

- Runtime contract: For each free-upgrade trigger during current wave, add listed percent to temporary coin/kill bonus for that wave, excluding Tower Range increases as valid triggers.

- Rarity values: Epic 3.0, Legendary 5.0, Mythic 7.0, Ancestral 10.0

- Special rules: Bonus applies when free upgrade triggers even if no upgrades remain in that category; free upgrades cannot increase Tower Range.

- Confidence: high


### Project Funding (Generator)

- Trigger: continuous_from_current_cash

- Runtime contract: Compute tower damage multiplier from current cash digit count / logarithmic form; clamp final multiplier to at least x1.00.

- Rarity values: Epic 12.5, Legendary 25.0, Mythic 50.0, Ancestral 100.0

- Special rules: Wiki note gives effective form (1 + Log(cash) * rarityMult); multiplier never below x1.00.

- Confidence: high


### Restorative Bonus (Generator)

- Trigger: on_recovery_package_collected

- Runtime contract: On package pickup, apply 50% attack speed boost for listed seconds and then decay over 60 seconds; new package refreshes timer.

- Rarity values: Epic 15.0, Legendary 20.0, Mythic 25.0, Ancestral 30.0

- Special rules: New package refreshes effect rather than stacking duration.

- Confidence: high


### Dimension Core (Core)

- Trigger: on_chain_lightning_resolution_and_shock_application

- Runtime contract: Allow CL to hit initial target with 60% chance, double shock chance and base shock multiplier, and when shock reapplies to same enemy additively accumulate multiplier up to listed stack count.

- Rarity values: Epic 5.0, Legendary 10.0, Mythic 15.0, Ancestral 20.0

- Special rules: CL has 60% chance to hit initial target; shock chance and multiplier doubled. Wiki note: base shock mult with max lab 1.66x becomes 2.32x after doubling; total stack form 1 + 1.32*n.

- Confidence: high


### Multiverse Nexus (Core)

- Trigger: on_uw_cooldown_schedule

- Runtime contract: Compute shared cooldown from average of DW, GT, BH base cooldowns adjusted by listed offset, then schedule all three to fire simultaneously on that unified cooldown.

- Rarity values: Epic 20.0, Legendary 10.0, Mythic 1.0, Ancestral -10.0

- Special rules: Wiki says Death Wave, Golden Tower, and Black Hole always activate at same time; cooldown is average of three plus/minus listed seconds. At Ancestral the offset is -10s.

- Confidence: high


### Primordial Collapse (Core)

- Trigger: while_black_hole_active

- Runtime contract: Spawn one extra Black Hole and, while enemies are inside any Black Hole, reduce their outgoing damage by listed percent.

- Rarity values: Epic 50.0, Legendary 55.0, Mythic 65.0, Ancestral 80.0

- Special rules: Spawns one additional Black Hole.

- Confidence: high


## Remaining caution

- Several duration semantics are not fully specified by the wiki and remain marked as not documented rather than guessed.

- Some contracts describe event ordering at a level suitable for a deterministic sim, but not every low-level engine tie-break is source-closed.

- Where the wiki gives both narrative wording and a scalar value, this KB preserves the scalar and keeps unstated tie-break rules out of canon.
