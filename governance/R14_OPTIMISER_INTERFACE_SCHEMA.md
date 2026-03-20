# R14 Optimiser Interface Schema

## Row-level fields
| Field | Meaning |
|---|---|
| `plane` | `canonical`, `runtime_mechanic`, or `helper_optimizer` |
| `destination` | exact calculator destination id |
| `optimizer_domain` | survivability, damage, econ, constraints, etc |
| `guarantee_level` | `high`, `medium`, or `experimental` |
| `status` | emitted calculator status |
| `publishable` | whether row is publishable in current statbook |
| `formula_class` | formula contract classification |
| `display_value` | current rendered value |
| `unit` | schema unit |
| `source_basis` | why the row is included in the optimiser contract |

## Contract rules
- `high` rows should come from stable audited canonical surfaces.
- `medium` rows may include helper/runtime rows that are resolved and intentionally emitted.
- `experimental` rows are allowed later but should not drive primary optimisation decisions.
- Any row absent from the interface ledger is out of optimiser contract scope even if present in output.
