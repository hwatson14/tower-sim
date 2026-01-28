# Optimizer tournament battle-condition variability

Tournaments vary battle conditions each tournament. The optimizer must be context-aware.

Supported modes:

- **conditional**: optimize for a single known `battle_conditions.set_id`
- **robust**: optimize expected value across a scenario set (set_id, weight), weights sum to 1

See:
- `spec/optimizer_scenarios.yaml`
- `src/optimizer/scenario_runner.py`
