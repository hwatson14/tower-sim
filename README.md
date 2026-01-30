# TowerSim

TowerSim is a **deterministic simulator** for the mobile game  
**The Tower — Idle Tower Defense**.

Its purpose is to compute **objective, defensible outcomes** (v1: *maximum reachable wave, Wmax*) for a fully specified player scenario, using **authoritative data only** and **fail-closed correctness rules**.

TowerSim prioritises:
- determinism over realism
- correctness over speed
- explicit assumptions over hidden defaults

It is designed for long-term maintainability and explainable results, not UI polish or probabilistic modelling.

---

## What TowerSim is (and is not)

**TowerSim is:**
- a mathematical model driven by frozen tables and explicit rules
- deterministic and reproducible
- strict about missing or ambiguous data (it fails instead of guessing)

**TowerSim is not:**
- a frame-by-frame game simulator
- a Monte Carlo or RNG-based model
- an economy or farming calculator (deferred to later versions)

---

## Documentation overview

This repository separates **intent**, **game context**, **architecture**, and **governance** to avoid ambiguity and duplication.

If you are new here, read these in order:

- **PROJECT_INTENT.md**  
  Why TowerSim exists, what problem it solves, its core philosophy, and the locked v1 scope.

- **GAME_OVERVIEW.md**  
  A high-level explanation of *The Tower — Idle Tower Defense* and its major systems, for readers unfamiliar with the game.

- **ARCHITECTURE.md**  
  How TowerSim is structured internally: architecture planes, data flow, determinism boundaries, and failure rules.

For repo layout and enforcement rules:

- **REPO_STRUCTURE.md**  
  Defines the allowed folder structure and what belongs where.

- **REPO_MAP.yaml**  
  The machine-enforced contract that prevents file sprawl.

- **CONTRIBUTING.md**  
  Contribution rules for humans and automated agents.

- **TESTING.md**  
  How tests and governance checks are run.

- **AGENTS.md**  
  Rules and constraints for AI agents (Codex, GPT, etc.) working in this repository.

This separation is intentional.  
If something is unclear, it likely belongs in one of the documents above rather than being inferred or duplicated.

---

## Repository principles (non-negotiable)

- No invented mechanics
- No silent defaults
- No hidden randomness
- Explicit assumptions for every run
- Fail-closed on missing data
- `tower_sim/` contains **library code only**
- Generated artefacts never live inside the library

Violations of these rules are considered correctness bugs.

---

## Status

TowerSim is under active development.

v1 completion criteria are defined in **PROJECT_INTENT.md**.  
Missing tables or mechanics are treated as blockers, not TODOs.

---

## License

TBD (personal project; not yet licensed for redistribution).

