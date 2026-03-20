# R37 UW Lab Routing + Non-Calculator Scope Tagging

## Summary
- Routed 71 new lab rows via direct destination maps and wiki-verified value tables
- Scope-tagged 83 non-calculator labs (masteries, module meta, perk control, admin/UI, discounts)
- Lab mapping: 27.4% → 60.8% (58/212 → 129/212)
- Resolved stats: 207 → 213
- Remaining unmapped: 162 → 83 (all tagged non_calculator_scope)
- EP compare: unchanged, 0 true mismatches

## New routes by category

### UW mechanic param labs (11 with wiki tables + value resolution)
Lightning Amplifier-Scatter, Swamp Radius, Swamp Stun Chance/Time,
Missile Barrage Quantity, Missile Radius, Inner Mine Blast Radius/Rotation Speed,
Recharge Missile Barrage, Inner Land Mine-Chrono Jump, Swamp Rend-Additional Enemies

### UW capability labs (6 boolean unlock)
Inner Mine Stun, Missile Barrage, Swamp Rend, Light Speed Shots,
Double Death Ray, Garlic Thorns (R34 already had: Extra BH, BH Disable Ranged, CL Shock, Swamp Stun, Missiles Explosion)

### Environment/BC labs (23)
All tier battle condition labs: Plasma Cannon/Orb/Thorns/Death Ray/Knockback Resistance,
Enemy Attack Speed, Enemy Speed, More Enemies, Armored Enemies,
Death Defy Down, Energy Shields Down, Enemy Level Skip Reduction, UW Durations,
Boss Attack/Health, all enemy-type attack/health/speed labs (Common, Fast, Ranged, Scatter, Ray, Tank, Vampire)

### Bot labs (8)
Amp/Flame/Gold/Thunder Bot Cooldown/Duration/Burn Stack/Linger Time

### Other mechanic params (7)
Land Mine Damage, Land Mine Decay, Orb Boss Hit, Shockwave Size,
Orbs Speed, Super Tower Bonus, Max Rend Armor Multiplier,
Protector Damage Reduction/Health/Radius, Second Wind Blast,
Recharge Second Wind/Demon Mode/Nuke

## Non-calculator scope tags (83 labs)
All 83 remaining unmapped labs are explicitly tagged:
- Masteries: 31 (e.g., Attack Speed Mastery, Health Mastery, etc.)
- Module meta: 15 (Assist bonuses, substats, effect bans, costs)
- Perk control: 8 (Ban Perks, Auto Pick, Standard Perks Bonus, etc.)
- Admin/meta/discount: 18 (Buy Multiplier, Workshop discounts, Card Presets, etc.)
- Economy deferred: 2 (Starting Cash, Max Interest)
- Drop rates: 2 (Common/Rare Drop Chance)
- Accepted unknown boundary: 6 (enemy ultimate labs)
- Sentinel: 1 (END OF ARRAY)

## Architecture
- UW lab wiki tables loaded via `_load_uw_lab_wiki_values()` with lru_cache
- Direct destination routing via `_UW_LAB_DIRECT_DESTINATION` map
- Capability labs resolve to bool via level > 0 check
- Non-calculator scope labs tagged in `_NON_CALCULATOR_SCOPE_LABS` set
- No changes to stat_engine.py or run_stats.py
