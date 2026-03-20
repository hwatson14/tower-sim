# R13 Completion Refresh After Helper Expansion

## Verdict

usable_with_caveats_not_fully_complete

## Key metrics

- publish_status: forbidden_for_publish
- mapped_inputs: 293
- total_inputs: 293
- mapping_pct: 100.0
- publishable: 164
- blocked: 10
- trace_only: 190
- resolved_stat_count: 174
- ep_compare_count: 27
- ep_true_formula_mismatch_count: 0
- ep_stage_scope_mismatch_count: 10
- blocked_formula_contract_count: 0
- active_unmapped_input_count: 192

## Interpretation

- Calculator-scope mapping remains fully closed at 293/293 inputs.
- Publishable surfaces improved from the earlier regenerated gate baseline to 164, driven by helper-plane exposure.
- Helper-formula emitted rows now total 4, confirming the helper plane is live rather than just policy.
- EP compared rows still show 0 true formula mismatches, with 10 remaining stage-scope mismatches.
- Overall publish status remains forbidden_for_publish because package-wide governance/classification maturity is still incomplete.

## Helper rows now emitted

- runtime_mechanic_param::cards.plasma_cannon.effect_pct = 54% (54.0)
- runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier = x11 (11.0)
- runtime_mechanic_param::uw.death_wave.coin_bonus_multiplier = x2.5 (2.5)
- runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier = x3 (3.0)

## Recommended next surfaces

Focus next on helper/runtime surfaces with strong user value and existing routed inputs, rather than widening broad EP parity claims. Likely candidates include econ or card effect helpers adjacent to the new helper plane.
