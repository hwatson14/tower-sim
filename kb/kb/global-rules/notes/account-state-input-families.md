# Account-state input families

These families are simulator inputs but are not universal global ladders.

They therefore use **input registries** rather than pretending the frozen KB contains a single global numeric table for every account instance.

## Families covered here
- relic
- player_stuff
- theme_song
- unlock

## Why this matters
A simulator-complete KB needs to know **what inputs exist**, where they route, what units they use, and how they affect canonical stats.
It does **not** need to invent user-specific values inside the frozen package.

## Active registry surfaces
- `kb/global-rules/tables/relic-input-registry.csv`
- `kb/global-rules/tables/player-stuff-input-registry.csv`
- `kb/global-rules/tables/theme-song-input-registry.csv`
- `kb/global-rules/tables/unlock-input-registry.csv`
