# Perk and Legacy Engine Notes

## Final position on perks
The perk set is fixed for the entire run **once the perk timeline is generated**.

Therefore:
- the **perk timeline generator** owns when perks are obtained and must internalise retrospective PWR
- perk **effect resolution** should be folded into the stat engine as a contributor family
- the progression engine may consume the timeline to derive perk state by wave, but should not own perk timing rules

Perks should **not** be modeled as a separate top-level engine in the final architecture.

---

## Legacy perk package audit summary
The uploaded old-repo perk package is:
- structurally useful
- partially reusable
- not safe to adopt as-is

### Reusable ideas
- perk timeline / selection policy shape
- weighted-offer logic structure
- explicit decomposition of multi-effect perks into effect rows
- fail-closed mindset around invalid/missing policy state

### Not safe as-is
- old pathing assumptions
- old repo table/manifest coupling
- naming drift in `effect_stat_id` vocabulary
- incomplete alignment to current canonical/effect surface contracts

### Best use
Treat it as **seed material** for:
- selection/timeline logic
- migration reference for perk definitions

Do **not** treat it as drop-in final perk architecture.

---

## How perk resolution should work in the stat engine
Given a fixed selected perk set, the stat engine should:
1. normalize selected perks
2. expand perks into governed effect rows
3. apply perk bonus / trade-off policy logic
4. aggregate to governed output surfaces
5. publish perk-adjusted stat/effect surfaces

### Example output types
- perk-adjusted HP multiplier
- perk-adjusted regen multiplier
- perk-adjusted enemy damage modifier
- BH duration add
- CF duration add
- trade-off positive multiplier
- trade-off negative multiplier

These can be emitted as canonical stats where appropriate, or as a separate governed fixed-effect-surface namespace where they are not naturally canonical stats.

---

## Recommended migration rule from legacy perk package
Reuse policy structure and decomposition ideas, but require full remapping of:
- IDs
- target surfaces
- table paths
- output schema
before adopting any old package logic.
