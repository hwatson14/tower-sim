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

## Agent quickstart: base stats, inventory, loadout

If you are wiring a ChatGPT agent (or any tool runner) to pull deterministic player
data, use the IDS diagnostics helper. It emits a single JSON payload containing
`base_stats`, `inventory`, and the resolved `loadout` (default preset). The output
is stable and fail-closed when required sections are missing.

```bash
PYTHONPATH=. python scripts/dump_ids_diagnostics.py \
  --ids-path /path/to/_IDS.csv \
  --output-dir ./audit
```

After running the command, confirm the IDS dump artifacts land under the exact
path `audit/account_snapshot.json` (same folder for the summary/diff JSON). This
snapshot is the full, canonical account state; the additional files below are
convenience extracts so agents can fetch a single slice without parsing the full
payload. The script writes dedicated extracts at:

- `audit/base_stats.json`
- `audit/inventory.json`
- `audit/loadout.json`

The script does not delete the files at the end of the job, so they should
remain on disk until you remove them. Key fields:

- `base_stats`: statbook rows (base/final/provenance) for labs + workshop.
- `inventory`: card/module/uw/bot/vault/etc inventory snapshots.
- `loadout`: resolved preset name, card list, module selections, and allocation
  levels for the active preset.

If you need raw inventory rows for Themes/Songs, Guardians, or Player Stuff, add
`--include-raw`.

**How does my agent know what to call?**  
In short: your agent should call the `dump_ids_diagnostics.py` script (or an
equivalent wrapper around it) and then read the resulting JSON file. The single
call above produces everything it needs for base stats, inventory, and loadout
in one deterministic payload (and writes the dedicated extract files listed
above). If you prefer a single artifact, you can read the sections directly from
`account_snapshot.json`. The fields to consume are:

- `base_stats` → list of stat rows with `stat_id`, `phase`, `base_value`,
  `final_value`, and provenance.
- `inventory` → full inventory sections (cards/modules/uw/bots/etc).
- `loadout` → resolved preset name, equipped card list, module selections,
  and allocation levels.

---

## Agent routing: run API tasks

If you want a single agent that can route to different deterministic runs based
on your request (inventory, base stats, loadout, or max wave), use the run API
task names. The run API resolves IDS into an AccountSnapshot and then executes
the task, so your agent only needs to choose which task to call.

- `BASE_STATS` → returns the StatBook for labs + workshop.
- `INVENTORY` → returns inventory snapshots (cards/modules/uw/bots/etc).
- `LOADOUT` → returns resolved preset name + equipped cards + modules.
- `MAX_WAVE` → runs deterministic max-wave evaluation.

If IDS input is missing, the API fails closed and returns missing sections, so
always pass IDS input when you call the run API.

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
