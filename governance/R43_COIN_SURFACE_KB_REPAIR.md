# R43 Coin Surface KB Repair

## Summary

This patch repairs the repo's coin stat contract in KB-first order.

The prior defect was semantic conflation: `canonical_stat::coin_kill_multiplier` had become the mixed owner for narrow Coins / Kill, broad coin-bonus contributors, and helper/display-like surfaces.

The repaired split is:
- `canonical_stat::coins_per_kill_bonus` for the narrow workshop/lab/substat/vault/spillover surface
- `canonical_stat::coin_bonus_multiplier` for the broad KB-owned direct coin-bonus surface
- `canonical_stat::coins_multiplier` as the helper broad-coins surface for card/relic ownership
- `canonical_stat::all_coin_bonus_multiplier` as a derived display surface only, fail-closed until tier normalization is trustworthy
- `canonical_stat::coin_kill_multiplier` kept only as a deprecated transition mirror of `coins_per_kill_bonus`

## Include / exclude

### coins_per_kill_bonus
Includes only workshop Coins / Kill, lab Coins / Kill, generator substat Coins / Kill, enhancement spillover, and vault Coins / Kill.

Excludes card/relic/theme/premium/tier/all-coin perks and situational UW coin mechanics.

### coin_bonus_multiplier
Includes only direct Coin Bonus enhancement, generator main Coin Bonus, and all-coin perk multipliers.

Excludes workshop/lab/substat/vault Coins / Kill, card/relic/theme/premium/tier, and situational UW coin mechanics.

### all_coin_bonus_multiplier
Composed only from helper surfaces. Currently fail-closed because tier normalization is not yet trusted enough for a publishable scalar.

## Compatibility policy

`coin_kill_multiplier` remains in the repo as a deprecated transition mirror of `coins_per_kill_bonus` so downstream consumers do not break immediately.

## Verification checklist

- narrow Coins / Kill surface is numerically correct
- broad coin-bonus surface is separated from Coins / Kill contributors
- card/relic/theme/premium/tier remain on helper surfaces
- all-coin display surface stays fail-closed without trusted tier normalization
- transition mirror equals `coins_per_kill_bonus`
