# Card effect application contract

These surfaces define simulator-facing card behavior.

## Active canonical surfaces
- `kb/cards/tables/card-entity-registry.csv`
- `kb/cards/tables/card-effect-registry.csv`
- `kb/cards/tables/card-contributor-routing.csv`
- `kb/cards/tables/wiki-card-slots-and-costs.csv`
- `kb/cards/tables/card-masteries.csv`
- `kb/cards/tables/wiki-card-mastery-lab-costs.csv`
- `kb/cards/tables/card-unresolved-simulator-surfaces.csv`

## Application rules
- A card effect may apply only when the card is equipped and an active slot is available.
- Card-slot capacity is determined by the slot-cost surface plus any separately sourced slot-cap modifiers.
- Card masteries are a distinct progression layer. Mastery effects apply only when the mastery is unlocked and the card is equipped.
- Lock semantics during boss/fleet presence are active runtime rules. The bundle supports the rule itself but not frame-exact same-tick transition precedence.
- Where the bundle contains only a verified slice of card base values, a simulator must use the captured slice or require explicit external account-state values. It must not extrapolate full ladders.

## Prohibited behavior
- Do not infer missing epic-card or unsurfaced base-card ladders.
- Do not treat presence of a card mastery row as proof that the full base-card ladder is also surfaced.
- Do not override the unresolved simulator surfaces registry with advisory notes.
