# Bot track normalization contract

`kb/bots/tables/bot-upgrade-tracks-long.csv` is the normalized all-bots active surface.

## Scope
It consolidates the four event bots into one long-form canonical table.

## Interpretation
- `level = 0` represents the base/unlocked track state from the bundled source table.
- `medal_cost` is the medal spend required for that specific next row in the bundled source extract.
- `track_value` preserves source values verbatim, including `Max` where the bundled source uses it.

## Source policy
The long table is sourced from the bundled Effective Paths export already included inside the package.
This surface exists to remove the prior unevenness where only some bots had dedicated canonical tables.
