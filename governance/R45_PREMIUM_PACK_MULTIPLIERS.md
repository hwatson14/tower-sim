# R45 Premium Pack Multipliers for All Coin Bonuses

Change summary:
- `all_coin_bonus_multiplier` now applies premium-pack multipliers numerically when the corresponding flags are true.
- KB source added: `kb/global-rules/tables/player-pack-coin-multipliers.csv`
- Multipliers:
  - Disable Ads = 1.5x
  - Starter Pack = 2.0x
  - Epic Pack = 3.0x
- Legacy `account_context.coin_multiplier_display` remains trace-only and is not used numerically.
- Farming-tier coin bonus is now looked up from KB using `account_context.farming_tier`.

Current farming account behavior:
- Farming Tier = Tier 14 -> coin bonus 17.6x
- Premium packs enabled -> combined pack multiplier 9x
