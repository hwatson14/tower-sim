## Runbook

Current state: **spec + adapters + validations** are present, but the **executable simulation harness is not yet wired** in this workspace.

- `adapter/*` provides fail-closed state construction + loadout + tier/tournament BC hooks.
- `data/*` contains recovered tables, but **heat/BC numeric tables are incomplete** unless populated from Effective Paths or explicit wiki tables.

Next integration step:
- Import the recovered execution skeleton (`main.py`, `sim/run_sim.py`, engines) and connect it to `adapter/*`.
- Provide a CLI entrypoint that can run `evaluate_context(ctx)` end-to-end.
