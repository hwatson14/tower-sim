# Tournament perks disabled (hard gate)

Rule: **Perks are not applied during tournaments**.

This is enforced as a **fail-closed gate**:

- `run_context.perks_enabled` is **derived**: `True` for tiers, `False` for tournaments.
- Any attempt to apply perks when `perks_enabled=False` must raise (not silently ignore).

## Optimizer implications

- Tournament optimization must prune perk decision variables entirely.
- Tournament battle conditions vary per tournament; optimization must be conditional-to-week or robust over scenario sets.

See:
- `spec/run_context_schema.yaml`
- `spec/optimizer_context_rules.yaml`
- `src/perks/perks_gate.py`
- `tests/test_tournament_perks_disabled.py`
