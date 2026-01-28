
## Data Binding (Fail-Closed)

This workspace does NOT embed balance data.

Authoritative data must be supplied externally at runtime:
- tiers.csv
- battle_conditions.csv
- heat.csv
- dag.json

Paths are declared in config/runtime_paths.py.
If any file is missing, the simulator must fail.
