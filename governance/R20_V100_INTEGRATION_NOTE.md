# R20 v100 integration note

This package integrates the completed upstream calculator `tower_stat_calc_v100__self_contained_ai_handover.zip` into the audit rail.

## Integration rule
- Upstream calculator v100 becomes the new implementation baseline.
- Proven audit-rail improvements are carried forward where v100 did not already include them.
- Audit/governance artifacts from this workstream are preserved.
- Optimizer payloads/manifests are regenerated from the integrated `output/` snapshot.

## Carried-forward audit-rail improvements
- Fresher EP mechanics registry copy-forward (`ep_v5.03.02_extract_2026-03-17`)
- Helper/runtime exposure for Plasma Cannon effect surface
- Helper/runtime exposure for BH / DW / SL coin bonus multipliers
- Destination formula ledger helper classifications and `cash_kill_multiplier` classification
- Lab value materialization / application registry entries for BH / DW / SL coin bonus labs
- Optimizer payloads and consumption manifest regenerated against integrated outputs
- Governance artifacts from R03-R19 preserved under `governance/`

## Integrated output picture
- publishable rows: 164
- blocked rows: 10
- trace-only rows: 190
- active unmapped input count: 192
- EP true formula mismatches: 0
- EP stage-scope mismatches: 10
- helper_formula emitted rows: 4

## Helper/runtime rows confirmed emitted
- runtime_mechanic_param::cards.plasma_cannon.effect_pct = 54%
- runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier = x11
- runtime_mechanic_param::uw.death_wave.coin_bonus_multiplier = x2.5
- runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier = x3

## Optimizer payload family regenerated
- optimizer_payload_r20.json (32 rows)
- optimizer_payload_r20_eecon.json (22 rows)
- optimizer_payload_r20_ehp.json (5 rows)
- optimizer_payload_r20_edamage.json (4 rows)
- optimizer_payload_r20_survival.json (6 rows)
- optimizer_consumption_manifest_r20.json
