# Card System

## Core structure
Cards are gem-funded equipable run modifiers. Their effects apply when equipped, subject to slot limits and lock behavior during boss or fleet presence.

## Active simulator-facing surfaces
- `kb/cards/tables/card-entity-registry.csv`
- `kb/cards/tables/card-effect-registry.csv`
- `kb/cards/tables/card-contributor-routing.csv`
- `kb/cards/tables/card-simulator-boundary-registry.csv`
- `kb/cards/tables/wiki-card-slots-and-costs.csv`
- `kb/cards/tables/card-masteries.csv`
- `kb/cards/tables/wiki-card-mastery-lab-costs.csv`
- `kb/cards/contracts/card-effect-application-contract.md`

## Interpretation rules
- Card ownership and level are persistent account-state inputs.
- Equipping is constrained by slot count.
- Lock behavior during boss/fleet presence is a runtime semantic, not a table property.
- Card masteries are separate from baseline card levels and belong to the same domain but a distinct progression layer.
- The current bundle surfaces full mastery ladders and a verified slice of base-card ladders. Missing base ladders must not be invented.
