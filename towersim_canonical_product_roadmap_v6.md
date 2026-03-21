# TowerSim Canonical Product Roadmap v6

## Purpose

TowerSim should become a practical decision tool for The Tower.

It should not feel like a bag of isolated calculators. It should feel like one coherent planner that can:

1. tell me what is true for my current account and scenario
2. estimate what is likely to happen
3. optimise for a chosen goal
4. advise what I should do next
5. explain why

This document is the canonical product roadmap and layer model for TowerSim. It preserves the agreed six-layer stack while explicitly merging back in the sharper progression-planning detail from the progression advisor plan.

---

## Core product questions

At the highest level, TowerSim should answer four recurring user questions:

1. **What happens if I run this setup?**
2. **What is the best setup for a chosen goal?**
3. **What should I do next to progress?**
4. **When is it realistic to change build archetype, such as switching to glass cannon?**

These define the main product surfaces:
- Estimator
- Loadout Optimiser
- Progression Optimiser
- Build Transition Advisor

---

## Canonical six-layer stack

The clean layer stack for TowerSim is:

1. **Knowledge Base**
2. **Inputs**
3. **Query Engine**
4. **Estimators**
5. **Optimisers**
6. **Advisors**

This is the canonical framing going forward.

### Why this stack is correct

- **Knowledge Base** owns game truth
- **Inputs** define the current problem state
- **Query Engine** resolves canonical truth for that state on demand
- **Estimators** forecast likely outcomes
- **Optimisers** search for the best choice under a goal and constraints
- **Advisors** turn all of that into practical guidance

### Dependency direction

The dependency direction should remain:

**Knowledge Base -> Query Engine -> Estimators -> Optimisers -> Advisors**

Inputs feed into the relevant downstream layers as needed.

Higher layers should not silently recreate truth that belongs below them.

---

## Product vision

TowerSim should feel like **one coherent account planner**, not a bag of separate tools.

Internally it may contain:
- many calculators
- many estimators
- several optimisers
- different recommendation surfaces

But externally the experience should feel unified:
- estimate a run
- compare setups
- find the best setup
- find the best next action
- understand bottlenecks
- plan the next week or month
- know when to switch strategies

---

## Core product principles

### 1. One optimiser, many queries
Do not create fake separate features if they are really just different optimiser queries.

Examples:
- best farming setup
- best tournament setup
- best max-wave setup
- best econ setup

These are all still queries against a core optimisation surface.

### 2. Keep user questions central
A feature is only valuable if it answers a repeated real question.

### 3. Explanation is part of the product
Recommendations without explanation will feel like a black box.

### 4. Time matters
Good progression advice depends on both:
- value
- time to earn the required resource

### 5. Reversibility matters
Good advice depends on whether spend is:
- permanent
- frictional to undo
- freely adjustable

### 6. Not every resource deserves equal modelling effort
Only model a resource deeply if it materially changes real decisions.

### 7. Module shards and rerolls are separate problems
They are related, but they are not the same planning problem.
- module shards = allocation and breakpoint problem
- rerolls = probabilistic target-planning problem

### 8. Query Engine must become the real truth source
Higher layers should consume query surfaces, not invent their own local truth models unless explicitly estimator logic.

### 9. Advisors must not become a garbage layer
Advisors should summarise, sequence, compare, and explain.
They should not invent hidden mechanics or bypass lower layers.

### 10. Trust labels matter
Not every recommendation will be equally mature. The product should expose recommendation confidence clearly.

---

# Layer 1: Knowledge Base

## Role

The Knowledge Base is the authoritative truth layer.

It owns:
- canonical mechanics
- formulas
- costs
- rules
- tables
- breakpoints
- scenario rules
- naming and alias contracts
- any governed truth surfaces

## Major elements

### A. Core game mechanics
- stat rules
- damage rules
- survivability rules
- timing rules
- geometry truths where canonical
- economy rules
- archetype-related mechanics
- progression mechanics

### B. Cost and progression rules
- lab costs
- lab times
- workshop costs
- enhancement costs
- ultimate weapon costs
- module shard requirements
- medal sink costs
- reroll rules
- other game-system spend rules

### C. Scenario and system rules
- farming conditions
- tournament conditions
- milestone conditions
- perk rules
- restrictions by mode
- scenario-specific modifiers

### D. Canonical naming and contracts
- aliases
- mapping tables
- naming contracts
- formula ownership contracts
- scenario naming contracts
- resource naming contracts

## What it should own
- what is true in the game
- canonical definitions
- authoritative tables
- rule ownership

## What it should not own
- current account state
- expected future outcomes
- search logic
- recommendation ranking
- user-facing advice

---

# Layer 2: Inputs

## Role

Inputs define the current problem state.

This layer tells TowerSim:
- what account is being evaluated
- what scenario is being evaluated
- what goal matters
- what constraints apply
- what planning horizon matters

## Major elements

### A. Account state
- current upgrades
- current inventory
- current resources
- current loadout
- current cards
- current modules
- current UWs
- current lab state
- workshop state
- progression state

### B. Goal and scenario selection
- max waves
- max economy
- farming
- tournament
- milestone push
- balanced growth
- other future goal classes if justified

### C. Constraints
Examples:
- do not change modules
- do not change a chosen card
- keep current archetype
- use only current UWs
- use only coins
- use only stones
- tournament only
- farming only
- no irreversible purchases

### D. Horizon and planning context
- immediate next action
- next spend
- 1 week
- 1 month
- target outcome if relevant

## What it should own
- what the player currently has
- what the player wants
- what the player allows the system to change
- what the decision horizon is

## What it should not own
- formulas
- canonical truth logic
- recommendation logic

---

# Layer 3: Query Engine

## Role

The Query Engine is the canonical on-demand truth layer.

It answers:
- what is true for this account, scenario, loadout, and current state?

This replaces “Calculators” as the main top-level layer name.

### Important distinction
- **Calculators are components**
- **Query Engine is the layer**

The query engine contains and orchestrates deterministic calculation surfaces.

## Major elements

### A. Stat surfaces
- effective stats
- derived stats
- scenario-adjusted stats
- setup-adjusted stats
- scenario and loadout state surfaces

### B. Cost surfaces
- upgrade costs
- spend requirements
- resource requirements
- time requirements
- current affordability surfaces

### C. Delta surfaces
- exact deltas from a proposed change
- setup-change deltas
- upgrade deltas
- breakpoint-distance deltas
- compare-current-vs-candidate deltas

### D. Spend-state and reversibility surfaces
- what is already committed
- what is freely adjustable
- what is locked
- what is recoverable with friction
- what requires another resource cost to unwind

### E. Deterministic support surfaces
- geometry-derived deterministic outputs
- timing-derived deterministic outputs
- progression-state deterministic surfaces
- breakpoint surfaces
- deterministic target gaps
- current module package and substat surfaces

## Internal component families
Likely major component families inside the query engine:
- stat calculators
- cost calculators
- progression-state calculators
- spend-state calculators
- reversibility calculators
- breakpoint calculators
- geometry calculators
- timing calculators
- target-gap surfaces
- reroll probability or exact target surfaces where applicable

## What it should own
- exact current-state truth
- exact deterministic deltas
- state-dependent canonical values
- deterministic compare surfaces

## What it should not own
- expected future outcomes
- recommendation ranking
- user-facing advice
- heuristic planning

---

# Layer 4: Estimators

## Role

Estimators forecast what is likely to happen.

They answer:
- what is likely to happen if I run this setup?
- what is likely to happen if I follow this path?
- what is the expected cost or gain of this action?

Estimators should make assumptions explicit. They should not silently pose as query-engine truth.

## Major elements

### A. Outcome estimators
- max-wave estimate
- run outcome estimate
- survivability-limited estimate
- damage-limited estimate
- boss-limited estimate
- mixed-limit estimate

### B. Income estimators
- expected coin income
- expected medal income
- expected shard income
- expected run-based gains
- expected horizon-based gains
- other meaningful resource incomes later

### C. Expected-value estimators
- expected reroll cost to target
- expected reroll cost to partial improvement
- expected value of breakpoint push
- expected value of waiting
- expected value of a candidate path

### D. Time-horizon estimators
- expected 7-day income
- expected 30-day income
- expected state after a candidate plan
- expected compounding return over time

### E. Comparison estimators
- current vs projected setup outcome
- current vs optimised setup outcome
- current path vs alternate path
- current build vs projected GC

## What it should own
- uncertainty-aware forecasts
- expected gains
- expected costs
- likely outcomes under assumptions

## What it should not own
- best-choice search
- recommendation ranking
- user-facing advice wording

---

# Layer 5: Optimisers

## Role

Optimisers answer:
- what is best under this goal and these constraints?

They search, rank, and compare alternatives.

This includes:
- one-step optimisation
- bounded multi-step optimisation
- constrained optimisation
- breakpoint-aware optimisation
- save-vs-spend branching

The final user-facing plan still belongs in the Advisor layer.

## Major elements

### A. Loadout optimisation
Questions include:
- best setup for max waves
- best setup for econ
- best setup for farming
- best setup for tournament
- best setup for milestone push

### B. Resource-specific optimisation
Questions include:
- best coin spend
- best lab allocation
- best stone spend
- best medal spend
- best module shard allocation
- best reroll target

### C. Save-vs-spend branching
Questions include:
- spend now or save?
- which branch wins over the chosen horizon?
- when does the better branch flip?
- what must change for branch B to overtake branch A?

### D. Constraint-aware optimisation
Questions include:
- best choice with restricted resources
- best choice without changing modules
- best choice under scenario restrictions
- best choice while preserving specific locked items

### E. Breakpoint-aware optimisation
Questions include:
- is this breakpoint worth pushing now?
- when does concentrated spend beat spread spend?
- what path reaches the key breakpoint fastest?
- when does a higher-cost option become better?

## Major optimiser families

### Loadout optimiser
- best setup for goal
- setup alternatives
- constrained setup search
- setup trade-off ranking

### Coin optimiser
- best workshop spend
- best mixed coin spend
- best enhancement spend
- coin path by goal

### Lab optimiser
- best lab
- lab queue ordering
- lab slot allocation
- lab plan over horizon
- lab choice given available cell boosting

### Stone optimiser
- immediate stone spend
- save-vs-spend stone paths
- unlock path
- sync path
- breakpoint path

### Medal optimiser
- medal sink prioritisation
- bot vs other sink decisions
- buy now vs save
- medium-term medal policy
- trade-offs between medal domains

### Module shard allocator
- shard allocation
- concentration vs distribution
- assist vs primary trade-off
- breakpoint-driven shard spending
- target-level planning

### Reroll optimiser
- target substat plan
- full-set target plan
- partial improvement plan
- wait vs reroll now
- target-quality optimisation

### Multi-resource optimiser
- blended best-next action
- cross-resource trade-offs
- horizon-based combined pathing

## Typical optimiser outputs
Optimisers should generally produce:
- ranked actions
- ranked alternatives
- ranked bounded plans
- expected gain
- expected cost
- planning horizon
- trust or confidence label
- explanation metadata

## What it should own
- search
- ranking
- alternative comparison
- bounded path comparison
- optimisation under constraints

## What it should not own
- raw mechanics
- raw formula ownership
- final user-facing advice packaging

---

# Layer 6: Advisors

## Role

Advisors are the user-facing recommendation layer.

They answer:
- what should I do next?

This is where planning properly lives in the product view.

A planner is closer to an advisor than an optimiser in user-facing terms, because the user cares about:
- what to do next
- what to do this week
- what to do this month
- why

not whether the result came from single-step optimisation or bounded multi-step plan search.

## Major elements

### A. Best-next-action advisor
- best immediate action
- best immediate spend
- top alternatives
- what changes if the top option is blocked

### B. Horizon-planning advisors
- best 1-week plan
- best 1-month plan
- recommended action sequence
- expected gains and costs
- main assumptions that matter

### C. Save-vs-spend advisor
- buy now vs save
- branch summary
- short-term vs medium-term trade-off
- when the recommendation flips

### D. Bottleneck advisor
- biggest current bottleneck
- what is limiting progress most
- what to fix first
- what is not worth chasing yet

### E. Build-transition advisor
- GC readiness
- archetype-switch timing
- what is missing
- best path to viability
- current build vs projected new build

### F. Explanation advisor
- why this is best
- why alternatives lose
- what trust label applies
- what assumptions matter
- what should be re-checked later

## Standard user-facing output shape

Advisor outputs should try to present:
- recommendation
- top 3 or top 5 alternatives where useful
- expected gains
- expected costs
- bottlenecks
- why this wins
- trust or confidence level
- assumptions that matter most
- change trigger where relevant

### Change trigger
A particularly useful advisor behaviour is:
- what would need to change for the answer to change?
- when should this advice be re-run?
- what breakpoint flips the recommendation?

## What it should own
- practical action guidance
- recommendation sequencing
- user-facing summaries
- trade-off explanation
- explanation formatting
- trust-label presentation

## What it should not own
- hidden mechanics
- ad hoc formulas
- silent heuristics that bypass lower layers

---

## Main product surfaces built on top

Using the six-layer stack above, the main product surfaces remain:

1. **Estimator**
2. **Loadout Optimiser**
3. **Progression Optimiser**
4. **Build Transition Advisor**

These are product surfaces built on top of the canonical layer model.

---

# Product Surface 1: Estimator

## Purpose
The estimator answers:
- what happens if I run this setup?
- how far will it get?
- how much econ will it produce?
- what is limiting the run?
- how much better is one setup than another?

## Major outputs
- max-wave estimate
- econ estimate
- outcome explanation
- setup comparison

## Major future expansions
- better damage-aware max-wave estimates
- richer income estimators
- stronger comparison estimators
- compound-return estimators
- expected-cost estimators

## Why it matters
This is the foundation for everything else.

---

# Product Surface 2: Loadout Optimiser

## Purpose
The loadout optimiser answers:
- what is the best setup for my chosen goal?

This is likely the flagship product surface.

## Goals it should support
- max waves
- max econ
- farming
- tournament
- milestone push
- balanced growth where justified

## What “setup” may include
Depending on model maturity:
- cards
- modules
- UWs
- perks
- substats
- scenario settings
- target run style

## Major outputs
- best setup for max waves
- best setup for max econ
- best setup for tournament
- best setup for milestone push
- best farming setup
- constrained setup recommendation
- current vs recommended comparison
- setup explanation and trade-offs
- alternative setups that are close behind
- “why not yet?” outputs where a desired setup is not yet best

## Important behaviours
- current vs recommended comparison
- top alternatives
- explanation of major winning setup changes
- trust-labelled setup recommendations
- change triggers for when the best setup changes

## Why it matters
This is the clearest “best setup for my goal” feature and likely the most obviously valuable optimisation surface.

---

# Product Surface 3: Progression Optimiser

## Purpose
The progression optimiser answers:
- what should I do next to progress?
- what should I spend over the next week or month?
- how should I allocate resources toward my goal?

## Core idea
The best upgrade is not just the biggest raw gain. It is the option with the best value relative to:
- cost
- resource required
- time to earn the resource
- chosen goal
- planning horizon
- reversibility

## Core recommendation families
The progression optimiser should explicitly support:
- best next action
- best next spend
- save vs spend
- 1-week plan
- 1-month plan
- bottleneck summary
- why this recommendation wins
- what would flip the answer

## Resource vs domain distinction

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
A system or sink where resources are invested.

Examples:
- labs
- workshop
- enhancements
- ultimate weapons
- bots
- medal shop
- modules
- rerolls

The progression optimiser should optimise resources across domains, not confuse the two.

## Major outputs
- best next spend
- best next few spends
- best 1-week plan
- best 1-month plan
- save-vs-spend summary
- bottleneck summary
- trust-labelled recommendation
- top alternatives
- why this path wins
- what would flip the answer

## Priority resource families
For initial scope:
- coins
- lab time
- stones
- medals
- module shards
- reroll shards

## Priority domains
For initial scope:
- labs
- workshop
- enhancements
- ultimate weapons
- medal shop and bots
- modules
- rerolls

## Important distinctions restored from the progression advisor plan

### Standard ROI / path optimisers
These are more conventional planning problems:
- coins
- lab time
- stones
- medals

### Breakpoint / allocation optimisers
These behave differently:
- module shards

### Probabilistic target optimisers
These also behave differently:
- reroll shards

This distinction should remain explicit. They are not the same optimisation problem.

## Spend-state and reversibility logic
The progression optimiser should understand whether a spend is:
- permanently locked
- recoverable with friction
- recoverable for free
- reversible only through another resource cost

This matters because recommendation quality depends on whether a decision is practical to undo later.

## Why it matters
This is where TowerSim becomes a practical account planner rather than just a setup tester.

---

# Product Surface 4: Build Transition Advisor

## Purpose
The build transition advisor answers:
- when is it realistic to change archetype?
- when does GC become viable?
- what is blocking that transition?
- what path gets me there fastest?

## Major outputs
- readiness assessment
- gap analysis
- breakpoint forecast
- side-by-side build comparison
- recommended path to viability
- why not yet?
- what would make the transition become correct

## Suggested readiness classes
- not viable yet
- borderline viable
- viable in limited contexts
- broadly viable
- clearly better than current archetype

## Why it matters
This turns fuzzy strategic community advice into account-specific guidance.

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
- partially modelled subsystems
- transition guidance

---

## Recommended roadmap order

### Phase 1: Strengthen the Estimator
Focus:
- make max-wave estimation more comprehensive
- include damage as well as survivability
- improve run-outcome explanation
- improve setup comparison

### Phase 2: Build the Loadout Optimiser
Focus:
- best setup for a chosen goal
- constrained optimisation
- current vs recommended comparison
- top alternatives
- trust-labelled setup recommendations

### Phase 3: Build the Progression Optimiser
Focus:
- best next spend
- resource-specific advice
- 1-week and 1-month planning
- save-vs-spend logic
- bottleneck detection
- trust-labelled recommendations
- restored resource/domain clarity
- restored spend-state and reversibility logic

### Phase 4: Deepen the Build Transition Advisor
Focus:
- GC viability
- archetype-switch breakpoints
- gap analysis
- transition pathing
- “why not yet?” and “change trigger” outputs

---

## Recommended scope cuts

## True v1
If scope needs to stay tight, true v1 should be:

### Product surfaces
- stronger estimator
- loadout optimiser
- progression optimiser
- advisor outputs with trust labels

### Resource families
- coins
- lab time
- stones

### Core advisor outputs
- best next spend
- 1-week plan
- bottleneck summary
- trust label
- top alternatives

## v1.5 / v2
Then expand into:
- medals
- module shards
- reroll planning
- deeper build-transition advice
- richer horizon planning

This is the cleaner risk-controlled sequence.

---

## Major risks

### 1. Scope creep in v1
Trying to model every resource and every path too early will slow everything down.

### 2. Query Engine does not become the real truth source
If higher layers keep inventing local truth, the architecture will fragment.

### 3. Advisors absorb too much logic
If Advisors start hiding real mechanics or heuristics, the layer stack collapses.

### 4. Loadout Optimiser remains underdeveloped
This is likely the flagship product surface. If it stays vague, the roadmap weakens.

### 5. Module shards and rerolls get incorrectly unified
That will likely create a bad optimiser rather than a good one.

### 6. Progression detail gets diluted again
If the canonical doc becomes too broad, the sharper resource/domain/planning distinctions can get lost.

---

## Strong suggestions

1. Keep the six-layer stack exactly as defined here.
2. Make Query Engine the real centre of truth.
3. Make Loadout Optimiser the flagship surface.
4. Standardise advisor output shape.
5. Preserve trust labels.
6. Add “why not yet?” and “change trigger” behaviours everywhere useful.
7. Preserve the resource vs domain distinction explicitly.
8. Preserve the optimiser-family distinctions explicitly.
9. Cut true v1 harder if needed.

---

## Example user questions TowerSim should answer

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

## Short version

The clean final model is:

### Layer stack
1. Knowledge Base
2. Inputs
3. Query Engine
4. Estimators
5. Optimisers
6. Advisors

### Main product surfaces
1. Estimator
2. Loadout Optimiser
3. Progression Optimiser
4. Build Transition Advisor

This is the canonical roadmap framing going forward.
