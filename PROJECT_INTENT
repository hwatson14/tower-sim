# TowerSim — Project Intent 

> **Status:** Locked intent  
> **Audience:** Humans, Codex, and any automated assistant working on this repo  
> **Purpose:** This document is the single portable source of truth for what TowerSim is, is not, and must never become.

---

## 1. What this project is

**TowerSim** is a deterministic simulator for the mobile game *The Tower — Idle Tower Defense*.

Its purpose is to compute **objective, defensible outcomes** for a given player account and scenario, under strict correctness rules:

- No invented mechanics  
- No silent defaults  
- No hidden randomness  
- Explicit assumptions  
- Fail-closed on missing data  

TowerSim is designed for **long-term correctness and maintainability**, not speed, UI polish, or probabilistic realism.

---

## 2. Core philosophy

TowerSim is **not** a frame-by-frame game simulator.

It is a **mathematical model** that answers specific questions (e.g. *“What is my maximum reachable wave?”*) using authoritative tables, frozen stat composition rules, and tightly bounded envelopes where uncertainty exists.

Anything not explicitly modeled is treated as **unknown**, not approximated.

### 2.1 Heuristic ban (explicit)

**Heuristic ban**

TowerSim forbids the introduction of heuristics, approximations, “good enough” rules, or intuitive shortcuts.

A heuristic may be used **only if**:

1. It is backed by authoritative data (tables, cited wiki sources, or committed reference artifacts), **and**
2. It is documented explicitly as an assumption in the **Assumptions Manifest** for that run.

Any heuristic not meeting **both** conditions is considered an error and must not be implemented.

If required data is missing, contributors **must fail-closed** rather than invent logic to proceed.

---

## 3. v1 scope (locked)

### 3.1 v1 objective (single, exclusive)

> **Compute Maximum Wave (Wmax)** for a fully specified scenario.

This is the **only required output** for v1.

### 3.2 Explicitly out of scope for v1

- Coins/hour, cells/hour, or any econ metrics  
- Full per-wave combat simulation  
- RNG, Monte Carlo, or sampling  
- Perk probability modeling  
- Optimisation execution (definitions allowed, execution deferred)

Econ and time-based outputs are deferred to **v2** due to additional timing and currency complexities.

---

## 4. What “Wmax” means (critical definition)

TowerSim does **not** simulate every wave.

Instead:

- Enemy strength is modeled as a **function of wave index**
- Player survivability is modeled as a **function of derived stats**
- **Wmax** is the wave at which the enemy damage envelope exceeds the player survivability envelope

This is a **root-finding / envelope-intersection problem**, not a discrete wave loop.

Wave-by-wave iteration may exist as an implementation detail, but must **never** be assumed by the architecture or required by the intent.

---

## 5. Variability model (strictly bounded)

There are **exactly two** sources of variability allowed in TowerSim.

No others may be introduced without an explicit scope revision.

### 5.1 Damage Reduction (DR) timing overlap

Certain mechanics provide temporary damage reduction via cooldown-based windows (e.g. ChronoField, Flame Bot, Black Hole).

- Their activation cycles are deterministic
- Their *phase alignment* relative to enemy hits is not observable

TowerSim models this using a **DR envelope**:

- **Best case:** maximal overlap
- **Median case:** expected overlap
- **Worst case:** minimal or no overlap

No frame-perfect timing simulation is required or allowed.

---

### 5.2 Perk acquisition order

Perk *effects* are deterministic once acquired.  
Perk *offer order* is not.

This variability affects timing, not mechanics.

Perk randomness is **never** simulated inside the core engine.

---

### 5.3 Explicit exclusions

The following are **not** sources of variability:

- Enemy targeting  
- Boss cadence  
- Damage formulas  
- Defense math order  
- Battle conditions  
- Heat scaling (once tables exist)  
- Skip mechanics (ELS/EHLS)  
- Crits, spawns, projectiles, or RNG  

If it cannot be expressed deterministically from authoritative data, it is excluded.

---

## 6. Perk resolution (separate from simulation)

Perks are handled by a **separate, offline process**.

### 6.1 Perk Resolver (external to sim)

- Run ad hoc (“from time to time”)
- Input:
  - Perk priority order
  - Scenario type (milestone / farming)
- Output:
  - Three deterministic artifacts:
    - Best-case perk timeline
    - Median-case perk timeline
    - Worst-case perk timeline
  - Each artifact defines `(perk_id → wave acquired)`

Artifacts are:
- Versioned
- Immutable
- Explicitly referenced by the sim

### 6.2 Core rule

The TowerSim engine **never reasons about perk randomness**.

If a perk timeline is required and not provided, the run **fails-closed**.

---

## 7. Assumptions Manifest (mandatory)

Every run must surface an **explicit Assumptions Manifest**.

This includes (non-exhaustive):

- DR overlap assumptions
- Perk timeline source and version (if applicable)
- Heat table version (if tournament)
- Skip mechanic assumptions
- Any simplification affecting outcomes

Assumptions are:
- Enumerated
- Human-readable
- Part of the correctness contract

---

## 8. Scenario types (definitions only)

TowerSim recognizes three scenario types.

### 8.1 Milestone runs
- Tier: 1–21
- Perks: allowed (via external perk timelines)
- Output: Wmax

### 8.2 Tournament runs
- League (e.g. Champion, Legends)
- Battle conditions: required
- Heat table: required
- Perks: banned
- Output: Wmax
- Missing BC or heat data → **fail-closed**

### 8.3 Farming runs
- Included for completeness
- v1 output: Wmax only
- Econ metrics deferred to v2

---

## 9. Data and evidence rules

### 9.1 Authoritative sources

A mechanic may be implemented **only if backed by**:

- An in-repo table under `tables/`
- A cached wiki source with provenance
- A committed reference artifact with source notes

### 9.2 Fail-closed rule

If required data is missing:

> The simulator is **not finished**, and the run must fail.

There are:
- No fallback defaults
- No inferred values
- No “helper” logic

---

## 10. Architecture (conceptual planes)

1. **Reference plane**  
   Immutable authoritative tables and cached wiki data

2. **Derivation plane**  
   Deterministic stat composition from `_IDS.csv` + loadout

3. **Model plane**  
   Enemy scaling, survivability envelopes, skip mechanics

4. **Evaluation plane**  
   Objective evaluators (v1: Wmax)

5. **Planning / optimisation plane**  
   Defined, execution deferred

---

## 11. Optimisers (definitions only)

Defined for future versions:

1. Loadout Optimiser  
2. Workshop Coin Optimiser  
3. Stone Optimiser  
4. Lab Time Optimiser  
5. Respec Optimiser  
6. Module Reroll Optimiser  

All optimisers:
- Operate on deterministic envelopes
- Never simulate randomness
- Always report impact on Wmax (and econ in v2)

---

## 12. Interaction model (design goal)

TowerSim is designed for **conversational, mobile-friendly use**.

### Separation of concerns

- **TowerSim:** pure deterministic engine  
- **Assistant layer (e.g. ChatGPT / Custom GPT):**
  - Interprets natural language
  - Collects missing inputs
  - Produces a structured Run Spec
  - Executes or delegates execution
  - Explains results

TowerSim itself contains **no conversational logic**.

---

## 13. Run Spec (interface contract)

All runs are defined by an explicit **Run Spec**, including:

- Scenario type
- Tier / league
- Loadout
- Player snapshot reference
- DR envelope version
- Perk timeline artifact (if applicable)

Anything not in the Run Spec **does not exist**.

---

## 14. Usage goals

- Free to use
- Mobile-friendly
- No paid infrastructure required
- Suitable for ChatGPT or Custom GPT usage
- Deterministic, explainable outputs

This document is sufficient context for any compliant assistant to work on TowerSim without additional explanation.

---

## 15. Definition of done (v1)

v1 is complete when:

- Given a valid Run Spec, TowerSim returns:
  - Wmax (best / median / worst)
  - Explicit Assumptions Manifest
- Missing data causes explicit failure
- No variability exists beyond DR overlap
- Results are reproducible and explainable

---

**End of Intent v2**
