# Bot runtime contract

`kb/bots/tables/bot-entity-registry.csv`, `bot-track-registry.csv`, `bot-mechanic-registry.csv`, and `bot-contributor-routing.csv` are the active normalized simulator-facing bot surfaces.

## Rules
- Bot identity is per named bot and must not be flattened into a generic pooled mechanic.
- Medal-funded tracks come from `bot-upgrade-tracks-long.csv`.
- Golden Bot and Flame Bot have separate lab extension support from `bot-labs-summary.yaml`.
- Material runtime behavior may be modeled from the named mechanic channel, but entries listed in `bot-runtime-boundary-registry.csv` are out-of-scope timing boundaries and must not be silently promoted into exact same-tick behavior.
- Bot unlock order affects unlock cost and belongs to economy/event-shop handling, not per-bot runtime track lookup.

## Bot Range Ownership

### Raw range owners
- `state::bot.golden.range_m`
- `state::bot.amplify.range_m`
- `state::bot.flame.range_m`
- `state::bot.thunder.range_m`

These rows own the named bot medal/lab track output before tower-range amplification.

### Shared flat bonus owner
- `state::bot.global.range_bonus_m`

This shared row owns flat bot-range additions that apply before tower-range amplification, including:
- relic and vault Bot Range contributors routed through `bot.global.range_bonus_m`
- `Singularity Harness` flat bot-range bonus from `kb/modules/contracts/module-unique-mechanic-contracts.csv`

### Effective range family
- `state::bot.golden.effective_range_m`
- `state::bot.amplify.effective_range_m`
- `state::bot.flame.effective_range_m`
- `state::bot.thunder.effective_range_m`

These are the future QE-owned effective active-range rows. They must stay distinct from the raw medal/lab track rows above.

### Effective range formula
For Golden Bot, Amplify Bot, Flame Bot, and Thunder Bot:

`effective_bot_range_m = (raw_bot_range_m + state::bot.global.range_bonus_m) * 1.33 * (state::tower.range_m / 69.5)`

Where:
- `raw_bot_range_m` is the named bot's raw pre-amplification range row
- `state::bot.global.range_bonus_m` is the shared flat pre-amplification bot-range bonus
- `state::tower.range_m` is tower range in meters

### Provenance
- Raw named-bot range ownership is anchored in `kb/bots/tables/bot-track-registry.csv` and `kb/ledgers/tables/towersim-static-ledger.csv`
- Shared flat bonus ownership is anchored in `kb/global-rules/contracts/compiler-routing-policy.yaml` and `kb/modules/contracts/module-unique-mechanic-contracts.csv`
- Tower-range amplification semantics are anchored in `kb/ledgers/tables/towersim-static-ledger.csv` and `kb/bots/tables/golden-bot-tracks.yaml`
- Exact amplification factor is sanctioned here from verified wiki evidence on `AdvancedAnalysis`:
  `Displayed Range Golden Bot = RangeBot x 1.33 x (RangeTower / 69.5m)`

Raw EP exports may support future audits, but they are not the active owner surface for this formula.

## Boss Waves Flame Bot Hit Estimate

Boss Waves may use a static expected-hit estimate for Flame Bot damage reduction when no explicit runtime hit-chance override is supplied.

This is a simulator encounter approximation, not a new QE-owned stat surface:
- Flame Bot center positions are treated as uniformly distributed inside the tower range disk.
- Reference geometry uses tower range `69.5m` and approximate wall radius `20m`.
- Boss movement is approximated as a radial path from tower range to the wall radius; if boss lifetime ends before wall contact, exposure ends on the partial path.
- Energy Net hold time extends the pre-contact exposure window at the wall radius.
- If boss lifetime extends after wall contact, post-contact exposure continues at the wall radius until modeled boss death.
- Flame Bot effective range must come from `state::bot.flame.effective_range_m`, so raw range, shared bot-range bonus, Singularity Harness range, and tower-range amplification stay QE-owned.
- Because bot range scales with tower range, Boss Waves normalizes the effective Flame Bot range back to the `69.5m` reference geometry for this probability estimate.
- Flame Bot cooldown comes from `state::bot.flame.cooldown_seconds`; repeated activations over the exposure window are modeled as deterministic cooldown windows with random phase.
- The estimate is a chance that the boss is tagged at least once. It must not be applied as fractional Flame Bot damage reduction; a tagged boss receives the full Flame Bot hit-state semantics until death, and an untagged boss receives none.

Explicit runtime hit-chance inputs remain higher priority for scenario experiments. Exact same-tick pathing, per-frame bot movement, and micro-precedence with other timed effects remain out of scope unless a future KB contract owns them.
