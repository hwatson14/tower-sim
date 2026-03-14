# Bot runtime contract

`kb/bots/tables/bot-entity-registry.csv`, `bot-track-registry.csv`, `bot-mechanic-registry.csv`, and `bot-contributor-routing.csv` are the active normalized simulator-facing bot surfaces.

## Rules
- Bot identity is per named bot and must not be flattened into a generic pooled mechanic.
- Medal-funded tracks come from `bot-upgrade-tracks-long.csv`.
- Golden Bot and Flame Bot have separate lab extension support from `bot-labs-summary.yaml`.
- Material runtime behavior may be modeled from the named mechanic channel, but entries listed in `bot-unresolved-runtime-surfaces.csv` must fail closed and must not be silently interpolated.
- Bot unlock order affects unlock cost and belongs to economy/event-shop handling, not per-bot runtime track lookup.
