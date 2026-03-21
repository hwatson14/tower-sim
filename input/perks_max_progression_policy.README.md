# Max progression perk timeline policy

This file is the user-editable default policy for generated max progression perks.

## What to edit
- `banned_perk_aliases`: friendly aliases such as `TO3`, `TO6`
- `banned_perks`: exact perk names
- `priority_order`: preferred perks by exact name
- `first_perk_choice`: exact first perk choice if desired

## Current default bans
- `TO3` = `Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%`
- `TO6` = `Enemies Speed -40%, But Enemies Damage x2.5`

## Authority
For `state_mode=max_progression`, if `input/perks.json` has no active preset, the calculator generates the perk timeline from IDS-backed controls plus this policy file.

- The generated timeline is written to `input/perks_projected_max.timeline.json`
- The generated final state is written to `input/perks_projected_max.final_state.json`
- The generated preset used by the stat engine is written to `input/perks_projected_max.json`

The future wave progression engine should consume the timeline file directly and can derive perk state at any wave. The stat engine max progression path uses the generated final state and does not need the wave engine.
