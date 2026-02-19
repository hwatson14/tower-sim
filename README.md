# TowerSim

TowerSim is a deterministic simulator for *The Tower — Idle Tower Defense* focused on objective, auditable results from explicit inputs. The v1 target is `MAX_WAVE` (`Wmax`) under fail-closed, provenance-first rules.

## Authoritative documentation
- **Repository contract (single authority):** [`CONTRACT.md`](./CONTRACT.md)
- **Agent operating rules:** [`AGENTS.md`](./AGENTS.md)
- **Repository structure contract:** [`REPO_MAP.yaml`](./REPO_MAP.yaml)
- **Implementation progress and known gaps:** [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md)
- **Testing guidance:** [`TESTING.md`](./TESTING.md)
- **Contribution/process guidance:** [`CONTRIBUTING.md`](./CONTRIBUTING.md)

## Project principles
- Deterministic over probabilistic.
- Provenance-backed mechanics over inferred behavior.
- Fail-closed over silent fallback.
- Simple, explicit architecture over abstraction-heavy design.

## v1 scope at a glance
In scope:
- Deterministic stat/mechanics pipeline.
- Deterministic `MAX_WAVE` objective evaluation.
- Auditable outputs and diagnostics.

Out of scope:
- Economy metrics (`coins/hour`, `cells/hour`, etc.).
- Frame-accurate simulation.
- RNG/Monte Carlo simulation.
- In-core perk probability simulation.
- Optimizer execution.

## Blessed run command
```bash
python -m tower_sim.run --spec fixtures/specs/max_wave.yaml
```

## Operational quickstart
For published artifact inventory, run-task routing hints, and operational commands beyond the blessed run command, see **Operational quick reference** in [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md).

## Notes for agent-driven development
This project is intentionally agent-driven and contract-governed. For implementation decisions, follow `CONTRACT.md` first, use explicit provenance for mechanics/tables, and fail closed if required authoritative inputs are missing.
