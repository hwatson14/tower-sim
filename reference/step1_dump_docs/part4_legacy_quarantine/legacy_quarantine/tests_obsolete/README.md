# Quarantined tests (obsolete)

`test_scenarios.py` was importing symbols that do not exist in the current recovery snapshot (`apply_battle_conditions`).
This made pytest fail during collection and provided no truthful gating.

These tests must be rewritten against the current adapter API once the battle-condition application layer is rebuilt.
