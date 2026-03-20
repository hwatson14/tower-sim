# R15 optimiser interface expansion

This iteration expands the optimiser contract from the initial 9-row seed into a controlled 32-row interface.

## Contract principle

The optimiser may consume only rows explicitly whitelisted in `OPTIMISER_INTERFACE_LEDGER_R15.csv`.

## Trust tiers

- **tier1**: already audited core canonical rows or emitted helper rows with explicit promotion history.
- **tier2**: resolved runtime/helper rows with clear optimiser value and low semantic ambiguity.

## Expanded interface composition

- Canonical rows: 5
- Runtime mechanic rows: 10
- Helper/optimiser rows: 17

## Why these rows were added

The expansion targets rows that are already emitted, resolved, and materially useful for optimiser decisions in one of three domains:

- survivability
- damage
- economy

The largest additions are economy-facing cadence and multiplier rows for Golden Tower, Black Hole, Spotlight, Death Wave, Golden Bot, and card helpers, plus a small set of defensive module mechanics.

## Safety boundary

This is still **not** permission for the optimiser to read the whole statbook. Rows outside the whitelist remain non-contractual until explicitly promoted.
