# Vault runtime contract

Vault is an endgame key-spend system with two normalized trees: Power and Harmony.

Rules:
- `vault-tree-registry.csv` owns tree identity and spend currency.
- `vault-contributor-routing.csv` owns the spend-path summary from Keys into vault tech trees.
- Detailed numeric effects remain owned by the domain that consumes them unless a dedicated vault stat table is later added.
- Until a broader numeric vault surface exists, vault remains mostly closed rather than fully closed for simulation.
