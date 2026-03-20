# R42 Direct Routing Restore

This iteration removes the prior publish-layer EP override for Free Upgrades.

Decision:
- No publish-layer overrides are permitted for canonical stats.
- Canonical outputs must be produced from full contributor routing and exact stat-engine resolution only.

Restored approach:
- Free Upgrades card is explicitly split into the three published canonical free-upgrade stats.
- Free Upgrade Chance for All perk is explicitly promoted into those same three canonicals.
- Exact free-upgrade resolver remains in the stat engine.
- Max Rend uses the corrected semantic owner formula:
  (8 + lab_bonus + 8 * module_substat_pct_bonus) * Rend Armor enhancement multiplier
- Workshop Rend Armor Mult is not used as the owner of final max_rend_mult.

Verified outputs after rebuild:
- free_attack_upgrade_chance_pct = 107.7384
- free_defense_upgrade_chance_pct = 104.6892
- free_utility_upgrade_chance_pct = 118.28544
- max_rend_mult = 9.68

Contributor trace after rebuild:
- Free upgrades rows now include workshop + card + perk, plus utility module substats where applicable.
- max_rend_mult now shows lab resolved contribution and enhancement resolved contribution directly on the canonical row.
