# R10 Helper/Optimizer Output Plane Schema

## Proposed fields

- `output_plane`: `helper_optimizer`
- `surface_group`: helper family grouping such as `econ_helper`, `damage_helper`, `perk_helper`, `uw_helper`
- `formula_origin`: `ep_helper`, `calculator_helper`, or `mixed`
- `helper_status`: `retain_not_yet_emitted`, `should_emit`, `emitted`
- `canonical_dependency_set`: list of canonical/runtime rows this helper depends on
- `optimizer_relevance`: `none`, `low`, `medium`, `high`

## Initial emission policy

Near-term helper emission candidates may be emitted once:

1. destination or calculation path exists in the calculator
2. row can be regenerated from canonical `output/` flow
3. row is labeled `output_plane=helper_optimizer`
4. row is excluded from canonical publishability counts unless explicitly promoted later
