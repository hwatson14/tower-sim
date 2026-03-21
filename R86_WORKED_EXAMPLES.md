# R86 worked examples

## Example 1: baseline contributor-map rows

Scenario:
- family_id: progression_runtime_no_perks
- state_mode: start_of_run
- account_snapshot_id: acct_demo_v1
- loadout_id: loadout_demo_farm
- scenario_id: scn_progression_no_perks
- runtime_branch_id: branch_base

Example rows for `canonical_stat::free_attack_upgrade_chance_pct`:

```yaml
- surface_id: canonical_stat::free_attack_upgrade_chance_pct
  source_class: workshop
  composition_stage: additive_pre_cap
  contributor_id: workshop.free_attack_upgrade.base
  value: 49
  value_type: integer_pct
  active: true
  gate_reason: null
  provenance_ref: workshop.track.free_attack_upgrade
- surface_id: support_surface::free_upgrade_multiplier
  source_class: cards
  composition_stage: multiplicative
  contributor_id: card.free_upgrades.multiplier
  value: 1.20
  value_type: scalar
  active: true
  gate_reason: null
  provenance_ref: cards.free_upgrades
```

## Example 2: overlay delta

```yaml
delta_id: delta_progression_wave_001
runtime_branch_id: branch_wave_187
affected_family_id: progression_runtime_no_perks
delta_type: workshop_mutation
target_scope:
  surface_ids:
    - canonical_stat::enemy_attack_level_skip_pct
changed_contributors:
  - contributor_id: workshop.enemy_attack_level_skip.base
    new_value: 27
changed_masks: []
changed_assertions: []
provenance_note: wave free-upgrade event
```

## Example 3: query response

```yaml
query_id: q_timing_demo_001
family_id: timing_tournament_no_perks
resolved_surface_rows:
  - surface_id: canonical_stat::package_chance_pct
    final_value: 33
    value_type: integer_pct
    status: resolved
  - surface_id: support_surface::timing.gcomp_cooldown_reduction_seconds
    final_value: 13
    value_type: seconds
    status: resolved
contributor_rows:
  - surface_id: canonical_stat::package_chance_pct
    source_class: cards
    composition_stage: additive_pre_cap
    contributor_id: card.recovery_package_chance
    value: 15
    value_type: integer_pct
    active: true
    gate_reason: null
    provenance_ref: cards.recovery_package_chance
trace:
  requested_surface_ids:
    - canonical_stat::package_chance_pct
    - support_surface::timing.gcomp_cooldown_reduction_seconds
  dependency_closure:
    - canonical_stat::package_chance_pct
    - support_surface::timing.gcomp_cooldown_reduction_seconds
```
