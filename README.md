> **Role:** Explanatory overview and navigation entrypoint.

# TowerSim

## Authority map

- **Normative:** `ARCHITECTURE.md`, `AGENTS.md`
- **Scope definition:** `PROJECT_INTENT.md`
- **Status only:** `IMPLEMENTATION_STATUS.md`
- **Reference only:** `GAME_OVERVIEW.md`
- **Index only:** `REPO_MAP.yaml`, `REPO_STRUCTURE.md`

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

If you want an agent to **fetch the latest inventory/loadout/base stats without
running scripts**, use the repository's `main` branch. The stats dump workflow updates the
following files in `out/`, which you can fetch over HTTPS from GitHub:

- `out/ids_dump_latest.json` (canonical snapshot payload)
- `out/base_stats_latest.json`
- `out/inventory_latest.json`
- `out/loadout_latest.json`
- `out/base_stats_components_latest.json`
- `out/inventory_components_latest.json`
- `out/run_stats_latest.json`
- `out/ids_raw_index_latest.json`
- `out/compiled_stat_inputs_latest.json`
- `out/stat_engine_latest.json`
- `out/resolved_problem_spec_latest.json`
- `out/max_wave_latest.json`
- `out/stage_1_base_no_respec_latest.json`
- `out/stage_2_base_with_respec_latest.json`
- `out/stage_3_with_loadout_latest.json`
- `out/stage_4_with_battle_conditions_latest.json`
- `out/stage_5_end_of_run_latest.json`

Example (raw file URL; replace `<org>` and `<repo>` as needed):

```
https://raw.githubusercontent.com/<org>/<repo>/main/out/inventory_latest.json
```

If you are wiring a ChatGPT agent (or any tool runner) to pull deterministic player
data, use the IDS diagnostics helper. It emits a single JSON payload containing
`base_stats`, `inventory`, and the resolved `loadout` (default preset). The output
is stable and fail-closed when required sections are missing.

```bash
PYTHONPATH=. python scripts/dump_ids_diagnostics.py \
  --ids-path /path/to/_IDS.csv \
  --output-dir ./out
```

After running the command, confirm the stats dump artifacts land under the exact
path `out/account_snapshot.json` (same folder for the summary/diff JSON). This
snapshot is the full, canonical account state; the additional files below are
convenience extracts so agents can fetch a single slice without parsing the full
payload. The script writes dedicated extracts at:

- `out/base_stats.json`
- `out/inventory.json`
- `out/loadout.json`
- `out/base_stats_components.json`
- `out/inventory_components.json`
- `out/run_stats.json`
- `out/ids_raw_index.json`
- `out/compiled_stat_inputs.json`
- `out/stat_engine.json`
- `out/resolved_problem_spec.json`
- `out/max_wave.json`
- `out/stage_1_base_no_respec.json`
- `out/stage_2_base_with_respec.json`
- `out/stage_3_with_loadout.json`
- `out/stage_4_with_battle_conditions.json`
- `out/stage_5_end_of_run.json`

The script does not delete the files at the end of the job, so they should
remain on disk until you remove them. Key fields:

- `base_stats`: statbook rows (base/final/provenance) for labs + workshop.
- `inventory`: card/module/uw/bot/vault/etc inventory snapshots.
- `loadout`: resolved preset name, card list, module selections, and allocation
  levels for the active preset.
- `base_stats_components`: themes/labs/UWs/vault/relics/workshop/enhancements/guardians/bots slice.
- `inventory_components`: cards+mastery, card presets, modules, module presets, shard allocation slice.
- `run_stats`: start-of-run + loadout delta + end-of-run stat row projection.

If you need raw inventory rows for Themes/Songs, Guardians, or Player Stuff, add
`--include-raw`.

### `out/` artifact contract (current + proposed)

`out/` is the repository's generated-artifact root. The table below lists what is
currently produced, where it comes from, and whether it is committed/published.

| Artifact path | Producer | Status | Notes |
| --- | --- | --- | --- |
| `out/account_snapshot.json` | `scripts/dump_ids_diagnostics.py --output-dir out` | Local run output | Canonical full IDS-derived account snapshot payload used by downstream consumers. |
| `out/base_stats.json` | `scripts/dump_ids_diagnostics.py` | Local run output | Convenience extract of `account_snapshot.base_stats`. |
| `out/inventory.json` | `scripts/dump_ids_diagnostics.py` | Local run output | Convenience extract of `account_snapshot.inventory`. |
| `out/loadout.json` | `scripts/dump_ids_diagnostics.py` | Local run output | Convenience extract of resolved active preset/loadout. |
| `out/base_stats_components.json` | `scripts/dump_ids_diagnostics.py` | Local run output | `BASE_STATS` component slices (labs/workshop/etc) for diagnostics. |
| `out/inventory_components.json` | `scripts/dump_ids_diagnostics.py` | Local run output | Inventory component slices (cards/modules/presets/shards). |
| `out/run_stats.json` | `scripts/dump_ids_diagnostics.py` | Local run output | Start/loadout/end run stat projection bundle. |
| `out/ids_dump_latest.json` | `.github/workflows/stats_dump.yml` (copy from `account_snapshot.json`) | Published on `main` | Canonical remote fetch target for agents that cannot run scripts. |
| `out/base_stats_latest.json` | `.github/workflows/stats_dump.yml` | Published on `main` | Published convenience extract. |
| `out/inventory_latest.json` | `.github/workflows/stats_dump.yml` | Published on `main` | Published convenience extract. |
| `out/loadout_latest.json` | `.github/workflows/stats_dump.yml` | Published on `main` | Published convenience extract. |
| `out/base_stats_components_latest.json` | `.github/workflows/stats_dump.yml` | Published on `main` | Published diagnostics component extract. |
| `out/inventory_components_latest.json` | `.github/workflows/stats_dump.yml` | Published on `main` | Published diagnostics component extract. |
| `out/run_stats_latest.json` | `.github/workflows/stats_dump.yml` | Published on `main` | Published run projection extract. |
| `out/perk_timeline/latest.json` | `.github/workflows/perk_timeline_runner.yml` | CI artifact (not committed) | Deterministic perk timeline output for smoke validation. |
| `out/perk_timeline/diagnostics.json` | `.github/workflows/perk_timeline_runner.yml` | CI artifact (not committed) | Validation metadata for perk timeline generation. |
| `out/runner_output.json` (or custom `--output`) | `python -m tower_sim.run.runner` | Local run output | Deterministic run/evaluator result payload. |
| `out/runner_output_latest.json` | `.github/workflows/max_wave_runner.yml` | Published on `main` | Latest deterministic max-wave runner payload from CI. |
| `out/ep_export_final_stats_report_latest.json` | `.github/workflows/max_wave_runner.yml` | Published on `main` | Latest final-stats parity report generated by max-wave CI. |

Proposed additions that would reduce ambiguity and improve agent reliability:

1. `out/manifest_latest.json`
   - Include generation timestamp, git commit SHA, workflow name, schema version,
     and checksums for every `*_latest.json` file.
   - Lets agents verify they fetched a consistent artifact set and fail closed on
     mixed revisions.
2. `out/schema/account_snapshot.schema.json`
   - Publish the expected snapshot contract consumed by run APIs.
   - Makes validation explicit for external callers before they hand data to
     evaluators.
3. `out/runner_output_latest.json` (optional, if governance allows publishing)
   - One pinned deterministic smoke-run payload from CI.
   - Useful as a stable fixture for integration consumers that need a concrete
     end-to-end output example.
4. `out/provenance_latest.md`
   - Human-readable short note listing source tables/sheets and workflow inputs
     used for the latest publication.
   - Improves traceability without requiring users to inspect workflow logs.

**How does my agent know what to call?**  
If you do not want the agent running scripts, have it download the latest files
from the `main` branch (examples above). If you are running locally,
your agent can call the `dump_ids_diagnostics.py` script (or an equivalent
wrapper around it) and then read the resulting JSON file. The single call above
produces everything it needs for base stats, inventory, and loadout in one
deterministic payload (and writes the dedicated extract files listed above). If
you prefer a single artifact, you can read the sections directly from
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

Optimizer tasks are defined for future versions and are not part of the v1 task API.

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

Perk timelines are external artifacts produced by a separate offline resolver; if a run requires perks and no timeline is provided, TowerSim fails closed.

## CI workflows

Current GitHub Actions coverage includes:

- `stats_dump.yml`: exports deterministic IDS diagnostics + latest base stats/inventory/loadout artifacts.
- `max_wave_runner.yml`: runs unit tests, validates deterministic max-wave runner output schema, checks runner `w_max` against EP export max-wave targets when those rows exist, emits an end-of-run eHP/farming final-stats parity report against EP export verification rows, and publishes `out/*_latest.json` max-wave artifacts on `main`.
- `perk_timeline_runner.yml`: validates perk timeline logic and publishes a generated timeline/diagnostics artifact.


---

## Status

TowerSim is under active development.

v1 completion criteria are defined in **PROJECT_INTENT.md**.  
Missing tables or mechanics are treated as blockers, not TODOs.

---

## License

TBD (personal project; not yet licensed for redistribution).
