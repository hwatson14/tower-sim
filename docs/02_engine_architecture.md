# Engine Architecture

## Top-level engine stack

### 1. Stat engine
**Purpose:** resolve fixed-for-run account/build/loadout outputs plus perk-derived stat/runtime overlays, and recompute those outputs from current workshop snapshots when requested by progression.

#### Owns
- canonical baseline stat resolution
- fixed perk resolution from the selected/fixed perk set and perk timeline final state
- governed emitted fixed effect surfaces needed downstream
- recalculation on current workshop state snapshots when requested by progression

#### Does not own
- mode selection
- battle conditions
- heat/environment overlays
- wave progression
- in-run workshop transitions themselves
- boss combat progression

#### Internal submodules recommended
- baseline contributor resolver
- perk contributor resolver
- canonical stat aggregator
- fixed effect-surface publisher

#### Key idea
Perks are treated as a fixed contributor family for the run and therefore belong inside the stat engine as a submodule of fixed stat/effect resolution.

---

### 2. Scenario-invariant derived effects engine
**Purpose:** take fixed resolved outputs and scenario overlays, then emit reusable fixed-for-run scenario-adjusted effect surfaces.

#### Owns
- `mode_id`
- battle condition selection
- heat/environment overlays
- uptime fractions
- cooldown surfaces
- sync/overlap surfaces
- scenario-adjusted resistances and intervals
- other fixed-for-run reusable effect surfaces

#### Does not own
- canonical stat recomputation
- in-run workshop changes
- current wall state
- attack/health wave
- boss TTK

#### Internal submodules recommended
- scenario selector/validator
- overlay resolver
- cadence and uptime compiler
- overlap and sync compiler
- environment/effect surface publisher

---

### 3. Progression engine
**Purpose:** own dynamic run state and boss-wave progression.

#### Owns
- current workshop levels for all tracks
- free-upgrade state
- buy policy state
- attack wave
- health wave
- boss-wave state
- current survival/combat state
- stat recalculation triggers
- boss-wave simulation logic

#### Key dependency
Whenever workshop state changes in a way that affects derived stats, the progression engine must call the stat engine recalculation path.

#### Internal submodules recommended
- workshop state tracker
- upgrade/buy policy executor
- attack/health wave progressor
- boss TTK solver
- boss intake solver
- survival ledger writer

---

## Why this split is preferred

### Stat engine answers
> Given this account/build/perk set and current workshop snapshot, what fixed stats and fixed effect surfaces exist?

### Scenario-invariant engine answers
> Given those fixed outputs plus scenario overlays, what fixed-for-run reusable scenario-adjusted effects exist?

### Progression engine answers
> What changes during the run, and what does that do to current state and survivability?

---

## Important boundary rule
Top-level splits should follow **state-change class**, not arbitrary topic boundaries.

That means:
- fixed contributor resolution -> stat engine
- scenario overlay and invariant cadence/sync math -> scenario-invariant engine
- in-run mutable state -> progression engine

---

## Architecture note: why not a separate perk engine?
Because the perk set is fixed for the run, perk effect resolution behaves like another contributor family rather than a dynamic simulation engine. The perk timeline generator owns *when* perks are obtained and must already internalise retrospective PWR behavior; downstream engines may consume the generated timeline, but perk rule resolution itself still belongs inside the stat engine.
