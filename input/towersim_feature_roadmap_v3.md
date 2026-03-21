# TowerSim Product Roadmap

## Purpose

TowerSim should become a practical decision tool for The Tower.

At a high level, it should answer four core questions:

1. What happens if I run this setup?
2. What is the best setup for a chosen goal?
3. What should I upgrade or spend over time?
4. When is it realistic to change build archetype, such as switching to glass cannon?

This roadmap is product-focused. It is about what TowerSim should help decide and explain, not the implementation details behind it.

---

## Product vision

TowerSim should feel like **one coherent account planner**, not a bag of separate calculators. It should combine estimation, optimisation, and advice into a single practical decision surface. This matches the stronger direction from the other planning draft. fileciteturn3file0turn3file2

The product shape is:

1. **Estimator**
2. **Loadout Optimiser**
3. **Progression Optimiser**
4. **Build Transition Advisor**

These are not random feature buckets. They are the main user questions the product should answer.

---

## Core product principles

### 1. One optimiser, many queries
Do not create fake separate features if they are really just different optimiser queries.

Examples:
- best farming setup
- best tournament setup
- best max-wave setup
- best econ setup

These are all still part of the same core optimisation surface.

### 2. Keep user questions central
A feature is only valuable if it answers a repeated real question.

### 3. Explanation is part of the product
Recommendations without explanation will feel like a black box.

### 4. Time matters
Good progression advice depends on both value and how fast the required resource can be earned.

### 5. Reversibility matters
Good advice depends on whether spend is:
- permanent
- frictional to undo
- freely reallocatable

### 6. Not every resource deserves equal modelling effort
Only model resources deeply if they materially change decisions.

### 7. The product should feel unified
Internally there may be many calculators and optimisers, but user-facing behaviour should feel like one planner. fileciteturn3file0turn3file2

---

## Layer model

This is useful for roadmap thinking even though this document is product-led.

### Calculators
Answer:
- what is true given these inputs?

### Estimators
Answer:
- what is likely to happen?

### Optimisers
Answer:
- what is best under this goal and these constraints?

### Advisors
Answer:
- what should I do next?

This separation is worth preserving because otherwise recommendation logic, expected-value logic, and raw mechanics blur together. fileciteturn3file0turn3file2

---

# 1. Estimator

## Purpose
The estimator answers:

- what happens if I run this setup?
- how far will it get?
- how much econ will it produce?
- what is limiting the run?
- how much better is one setup than another?

## Main user promise
Given a setup and scenario, the estimator should provide a credible view of likely outcome and the main reasons for that outcome.

## Main outputs

### Max-wave estimate
- predict expected maximum wave for a given setup and scenario
- include both survivability and damage, not survivability only
- distinguish whether the run is:
  - survivability-limited
  - damage-limited
  - boss-limited
  - mixed-limited

### Econ estimate
- predict income outcomes for a given setup
- compare resource output by goal, such as:
  - coins
  - cells
  - shards
  - other meaningful resources later

### Outcome explanation
- explain what likely stops the run
- identify main bottlenecks
- show biggest contributors to the result
- surface what would most likely improve the result

### Setup comparison
- compare one setup against another
- compare:
  - current vs projected
  - current vs optimised
  - hybrid vs GC
  - one loadout vs another

## Strong future expansions
Useful future estimator families from the other plan include:
- income estimators
- outcome estimators
- compound-return estimators
- expected-cost estimators fileciteturn3file2

## Why this matters
The estimator is the foundation for everything else. The optimiser and advisor layers are much more useful once TowerSim can first estimate outcomes credibly.

---

# 2. Loadout Optimiser

## Purpose
The loadout optimiser answers one core question:

- what is the best setup for my chosen goal?

This is the main optimisation feature family and likely the highest-value product surface.

## Main user promise
Given the account state, scenario, and chosen objective, TowerSim should recommend the best setup and explain why it wins.

## Goals it should support
Initial goal families should include:
- maximum waves
- maximum economy
- farming
- tournament
- milestone push
- balanced growth where useful

These align well with the goal framing in the other plan. fileciteturn3file0

## What “setup” may include
Depending on model scope, setup can include:
- cards
- modules
- UWs
- perks
- substats
- scenario settings
- target farming style
- target objective weighting

The important point is that setup should be broad enough to represent what a player actually changes.

## Main feature areas

### Best setup for a chosen goal
Examples:
- best setup for max waves
- best setup for max econ
- best setup for tournament
- best setup for milestone push
- best setup for farming

### Constrained optimisation
Examples:
- best setup without changing modules
- best setup using current UWs only
- best setup while preserving one or more fixed items
- best setup under a specific tournament scenario
- best setup with perks disabled
- best setup with farming constraints

### Comparison to current setup
- show current outcome vs recommended outcome
- show what changed
- show expected gain
- highlight the most important setup changes

### Explanation and trust
- explain why the recommended setup is best
- identify which parts of the setup are doing the most work
- explain key trade-offs
- expose trust or confidence level where relevant

## Query examples
This feature should eventually answer questions like:
- what is my best setup for max waves?
- what is my best setup for econ?
- what is my best farming setup?
- what is my best tournament setup?
- what setup is best if I refuse to change modules?
- what setup is best if I keep PBH?
- what setup is best right now versus after my next few upgrades?

## Strong future expansions
This is also where side-by-side archetype comparison becomes very useful:
- current hybrid vs projected GC
- current loadout vs idealised max-wave loadout
- current econ build vs best econ build

## Why this matters
This is the feature that turns TowerSim from a passive simulator into an active setup advisor.

---

# 3. Progression Optimiser

## Purpose
The progression optimiser answers:

- what should I spend or upgrade next?
- what is the best plan over a time horizon?
- how should I use my resources to progress fastest toward a goal?

This extends the product from “best setup now” into “best account progression over time”.

## Main user promise
Given the current account, chosen goal, time horizon, and constraints, the progression optimiser should recommend:
- the best next action
- the best next spend
- the best short-term plan
- the best medium-term plan
- what should be saved for
- what is currently limiting progress
- why the recommendation is better than alternatives

This wording is directly aligned with the stronger plan from the other thread. fileciteturn3file0

## Core idea
The best upgrade is not just the one with the biggest raw gain. It is the one that provides the best value relative to:
- its cost
- the resource required
- the rate that resource is earned
- the user’s actual goal
- the planning horizon

## Planning horizons
Core practical horizons:
- next action
- next spend
- 1 week
- 1 month

These were explicitly called out as the practical v1 focus. fileciteturn3file0

## Goals it should support
Initial goal families:
1. max waves / survivability
2. max economy
3. tournament strength
4. balanced growth

## Resource vs domain
This distinction should remain explicit.

### Resource
A scarce thing the player earns, spends, allocates, or consumes.

Examples:
- coins
- lab time
- stones
- medals
- module shards
- reroll shards

### Domain
A game system or sink where resources are invested.

Examples:
- labs
- workshop
- enhancements
- ultimate weapons
- bots
- medal shop
- modules
- rerolls

The progression optimiser should optimise resources across domains. fileciteturn3file0

## Main feature areas

### Best next spend by resource
Examples:
- best coin spend
- best lab-time use
- best stone spend
- best medal spend
- best module shard allocation
- best reroll action

### Time-horizon planning
Examples:
- best 1-week progression plan
- best 1-month progression plan
- best short-term vs long-term plan

### Goal-based progression
Examples:
- maximise waves over 1 week
- maximise econ over 1 month
- improve tournament performance fastest
- balanced growth path

### Save vs spend
Examples:
- buy now vs save for a larger unlock
- short-term gain vs stronger future compounding
- immediate efficiency vs strategic milestone

### Path optimisation
Examples:
- cheapest path to reach a target
- fastest path to make GC viable
- best sequence of upgrades to gain a specific improvement

### Constraint-aware advice
Examples:
- only use coins
- only labs
- only stones
- no loadout changes
- no irreversible purchases
- tournament only
- farming only
- milestone push only

### Bottleneck detection
Examples:
- coin bottleneck
- lab-time bottleneck
- shard bottleneck
- stone bottleneck
- weak loadout
- weak stat family

## Primary optimiser families

### Coins
Questions include:
- best workshop spend
- best lab spend in coin terms
- best Enhancements spend
- best mixed coin spend across sinks
- best coin path for waves
- best coin path for economy
- best blended coin path

### Lab time
Questions include:
- best lab by time ROI
- best lab queue ordering
- best use of limited lab slots
- best lab sequence over 1 week / 1 month
- best lab given available cells for boosting

### Stones
Questions include:
- best immediate stone spend
- best save-vs-spend choice
- best unlock path
- best sync path
- best breakpoint path
- best 1-month stone plan

### Medals
Questions include:
- best medal use for bots
- best medal-shop prioritisation
- buy now vs save
- long-term medal allocation policy
- trade-off between bots and other medal sinks

### Module shards
Questions include:
- which module gets the next shard levels?
- primary vs assist trade-off
- when is a breakpoint push worth more than spreading levels?
- when does concentration beat distribution?

### Reroll shards
Questions include:
- what substats should be targeted?
- what full set should be targeted?
- when is partial rerolling worth it?
- when is it better to reroll most or all substats at once?
- should rerolls wait until the module reaches a stronger level or breakpoint first?

The distinction between standard ROI planners, breakpoint planners, and probabilistic target planners is explicitly important. Module shards and rerolls should stay separate. fileciteturn3file0turn3file2

## Spend-state and reversibility logic
The progression optimiser should understand whether an allocation is:
- permanently locked
- recoverable with friction
- recoverable for free
- reversible only through another resource cost

This matters because recommendation quality depends on whether a decision is actually practical to undo later. fileciteturn3file0turn3file2

## Main outputs
- best next spend
- best next few spends
- best 1-week plan
- best 1-month plan
- expected gain from the recommendation
- expected cost
- bottleneck summary
- save-vs-spend summary
- trust or confidence label
- explanation of why the recommendation is best

## Why this matters
This is where TowerSim becomes a progression planner, not just a build tester.

---

# 4. Build Transition Advisor

## Purpose
The build transition advisor answers:

- when is it realistic to switch build archetype?
- when does glass cannon become viable?
- what is blocking that transition?
- what should I upgrade to get there faster?

## Main user promise
Instead of vague community heuristics, TowerSim should provide a tailored account-specific answer about when an archetype switch becomes viable and worth it.

## Primary use case
The main example is:
- when should I switch to GC?

But the same logic could later apply to other archetype or strategy changes.

## Main outputs

### Readiness assessment
Possible outputs:
- not viable yet
- borderline viable
- viable in specific contexts only
- broadly viable
- clearly better than current archetype

### Gap analysis
- what is missing
- what stats or capabilities are holding the transition back
- what is most limiting readiness

### Breakpoint forecast
- when the transition becomes competitive
- what upgrade path gets there fastest
- how far away the player is from a viable switch

### Side-by-side comparison
- current build vs projected GC
- now, in 1 week, in 1 month
- strengths and weaknesses of each path

## Why this matters
This is a very practical player decision. It turns a fuzzy strategic judgment into a specific answer.

---

## Trust and confidence labels

Because not all surfaces will be equally mature, recommendations should carry trust labels.

Suggested classes:
- **Canonical**
- **Strong model**
- **Accepted model**
- **Policy heuristic**

This is especially important for:
- economy planning
- rerolls
- long-horizon compounding
- any partially modelled systems

This trust framework was a strong addition from the other planning draft. fileciteturn3file2

---

## Recommended v1 scope

### Priority product surfaces
For v1, the best practical shape is:
1. stronger estimator
2. loadout optimiser
3. progression optimiser
4. trust-labelled outputs
5. GC transition advisor after the first three are useful

### Priority resource families
For v1, the strongest resource families are:
- coins
- lab time
- stones
- medals
- module shards
- reroll shards

### Priority recommendation types
For v1:
- best next spend
- best 1-week plan
- best 1-month plan
- save vs spend
- constrained advice
- bottleneck detection

### Priority domains
For v1:
- labs
- workshop
- enhancements
- ultimate weapons
- medal shop and bots
- modules
- rerolls

### Non-goals for v1
Later, not now:
- full keys and Vault planning
- exhaustive niche-resource planning
- perfect modelling of every irregular currency
- exhaustive long-horizon branch search
- full event-state modelling

This v1 shape closely follows the better-scoped recommendations in the other plan. fileciteturn3file2

---

## Roadmap order

## Phase 1: Strengthen the Estimator
Focus:
- make max-wave estimation more comprehensive
- include damage as well as survivability
- improve run-outcome explanation
- improve comparison against alternate setups

Key question answered:
- what happens if I run this?

## Phase 2: Build the Loadout Optimiser
Focus:
- best setup for a chosen goal
- current vs recommended comparison
- constrained optimisation
- recommendation explanation
- trust-labelled setup recommendations

Key question answered:
- what setup is best?

## Phase 3: Build the Progression Optimiser
Focus:
- best next spend
- resource-specific advice
- 1-week and 1-month planning
- save vs spend logic
- progression pathing
- bottleneck detection
- trust-labelled recommendations

Key question answered:
- what should I do next, and over the next week or month?

## Phase 4: Build the Transition Advisor
Focus:
- GC viability
- build-switch breakpoints
- gap analysis
- transition planning

Key question answered:
- when should I switch archetype?

---

## Example questions TowerSim should eventually answer

### Estimator
- how far will this setup go?
- is this run damage-limited or survivability-limited?
- how much better is this setup than my current one?

### Loadout Optimiser
- what is my best setup for max waves?
- what is my best setup for max econ?
- what is my best farming setup?
- what is my best tournament setup?
- what is my best setup if I refuse to change modules?

### Progression Optimiser
- what should I spend my coins on next?
- what should I spend my stones on next?
- what is the best 1-week progression plan?
- what is the best 1-month progression plan?
- should I spend now or save?
- what is my biggest bottleneck right now?

### Build Transition Advisor
- is GC realistic for me yet?
- how far away am I from a viable GC switch?
- what upgrades get me to GC fastest?
- when does GC become better than my current build?

---

## Open questions worth preserving

These are useful unresolved questions carried forward from the other plan:

### Resource scope questions
- should gems be in v1 or shortly after?
- should cells be modelled operationally in planner logic even if lifetime tracking is not needed?
- which lower-priority resources eventually justify full optimiser treatment?

### Domain-specific modelling questions
- exact medal sink taxonomy
- exact reversibility status of each medal sink
- exact module breakpoint valuation method
- exact reroll target quality metrics
- how to evaluate full-set vs partial reroll strategies

### Planning questions
- how many recommendations should be shown by default?
- how should balanced-growth objectives be scored?
- should 1-week and 1-month plans be greedy, branch-based, or hybrid?

These are still useful future iteration targets. fileciteturn3file2

---

## Short version

If TowerSim is reduced to its strongest roadmap shape, it is:

1. **Estimator**  
   What happens if I run this setup?

2. **Loadout Optimiser**  
   What is the best setup for my goal?

3. **Progression Optimiser**  
   What should I upgrade or spend over time?

4. **Build Transition Advisor**  
   When should I change archetype, such as switching to GC?

That is the clean product roadmap.
