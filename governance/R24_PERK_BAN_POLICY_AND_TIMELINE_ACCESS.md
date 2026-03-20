# R24 Perk ban policy and timeline access

## Manual default bans
The editable default max progression perk-ban list now lives in:
- `input/perks_max_progression_policy.json`
- human guidance: `input/perks_max_progression_policy.README.md`

Current default bans:
- `TO3` = `Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%`
- `TO6` = `Enemies Speed -40%, But Enemies Damage x2.5`

## Authority order
For `state_mode=max_progression`:
1. If `input/perks.json` has an active preset, use it.
2. Otherwise generate from IDS-backed controls plus `input/perks_max_progression_policy.json`.

## Timeline vs final state
- Future wave engine should consume `input/perks_projected_max.timeline.json` and may reconstruct state at any wave.
- Stat engine max progression may skip the wave engine and consume the generated final state aggregated from the same timeline.

Generated outputs:
- `input/perks_projected_max.timeline.json`
- `input/perks_projected_max.final_state.json`
- `input/perks_projected_max.json`
- `input/perks_projected_max.diagnostics.json`
