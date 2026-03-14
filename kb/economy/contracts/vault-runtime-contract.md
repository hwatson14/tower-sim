# Vault runtime contract

Vault is an endgame key-spend system with two normalized trees: Power and Harmony.

Rules:
- `vault-tree-registry.csv` owns tree identity and spend currency.
- `vault-contributor-routing.csv` owns the spend-path summary from Keys into vault tech trees.
- `vault-node-effect-registry.csv` owns vault node identity, destination routing, and whether the node is structural, single-level, or externalized numeric input.
- `vault-externalized-simulator-inputs.csv` owns the explicit list of vault numeric bonuses that may be supplied as resolved account-instance inputs.
- The simulator may apply externalized vault bonuses only when they are explicitly supplied for a listed field.
- Thorns timing boundary for simulator use is: thorns damage occurs immediately after incoming damage resolution.
- Same-tick precedence beyond that thorns-after-damage rule is intentionally out of scope for this package.

Closure state:
- Vault is closed for simulator use once routing, tier rules, single-level nodes, and explicit externalized numeric inputs are all respected.
- The package does not claim a bundled authoritative per-level ladder for every vault stat node.
