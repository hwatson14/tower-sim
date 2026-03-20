# R44 Coin Perk Rewire

## Summary

User-confirmed game behavior shows coin perks change the visible Coins / Kill Bonus surface, not the derived all-coin helper surface.

## Changes

- Rewired `PERK_X1_15_ALL_COIN_BONUSES` to target `coins_per_kill_bonus`
- Rewired the positive side of `PERK_X1_80_COINS_BUT_TOWER_MAX_HEALTH_70` to target `coins_per_kill_bonus`
- Updated `coins_per_kill_bonus` formula to multiply the narrow surface by perk multipliers
- Removed perk ownership from `coin_bonus_multiplier`
- Resolved `all_coin_bonus_multiplier` numerically as:
  - `coin_bonus_multiplier * coins_multiplier * theme_song_coin_multiplier * parsed account_context.coin_multiplier_display`
- Kept premium flags as source trace only; no guessed numeric mapping was introduced

## Result

For Farming:
- `start_of_run coins_per_kill_bonus` stays at 9.65979
- `max_progression coins_per_kill_bonus` resolves to 41.8389654375
