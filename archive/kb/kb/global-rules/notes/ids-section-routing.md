# IDS section routing

## Purpose

This note closes the source-routing story for all uploaded `_IDS.csv` sections.

## Sections and owning routing families

- `Labs` -> `lab`
- `WS` -> `workshop`
- `Enhancements` -> `enhancements`
- `Ultimate Weapons (UWs)` -> `uw_upgrade` plus `unlock`
- `Cards` -> `card`
- `Relics` -> `relic`
- `Vault` -> `vault`
- `Bots` -> `bot_upgrade`
- `Themes & Songs` -> `theme_song`
- `Modules` -> `module`
- `Guardians` -> `guardian_upgrade` plus `unlock`
- `Player & Stuff` -> `player_stuff`

## Destination classes

The routing surface now terminates in one of:
- canonical target stats
- runtime mechanic parameters
- environment parameters
- capabilities
- account resources
- account context
- cosmetic bonuses
- account flags

## Important distinction

Not every `_IDS.csv` section is a combat contributor.

Some sections are:
- direct stat contributors (`workshop`, `lab`, `relic`, `vault`, `enhancements`)
- runtime-mechanic contributors (`uw_upgrade`, `bot_upgrade`, `guardian_upgrade`)
- account/profile context (`player_stuff`)
- cosmetic passive bonus contributors (`theme_song`)
- capability/unlock gates (`unlock` rows emitted from Ultimate Weapons (UWs), guardians, vault-style automations, and other account-side unlocks)

That is intentional. The routing contract is complete when every section terminates in an explicit destination class, not only when every row becomes a combat stat.
