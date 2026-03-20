# R23 Perk timeline integration

## What changed

- Merged the perk timeline generator runtime code, loaders, tables, and tests into the calculator baseline.
- Added `input/perks_max_progression_policy.json` as the governing policy input for projected max progression perk generation.
- Changed max progression perk resolution so that when the primary perk config has no active preset, the calculator **generates** `input/perks_projected_max.json` from the timeline generator instead of relying on a hand-maintained static preset.
- The generated timeline and diagnostics are written to:
  - `input/perks_projected_max.timeline.json`
  - `input/perks_projected_max.diagnostics.json`
  - `input/perks_max_progression_policy.runtime.json`

## Current generated result

- Active generated preset: `ProjectedMax_GeneratedTimeline`
- Unique perks selected: `34`
- Total generated picks: `79`
- Timeline rows: `79`
- Final timeline wave: `8702`
- Resolution fallback reason: `max_progression_generated_from_timeline_policy`

## Integration rule

For `state_mode=max_progression`:

1. Load the requested perk config.
2. If it already has an active preset, use it unchanged.
3. Otherwise, generate the projected max preset from the perk timeline policy plus IDS-backed values:
   - Waves Required
   - Standard Perk Bonus
   - Perk Option Quantity
   - Ban Perks
4. Use the generated preset as the authoritative max progression perk config.

## Notes

- This preserves the calculator-first rail: the generator is now part of the calculator package, and its output controls max progression perk availability.
- The generator is deterministic under the configured seed.
- The policy currently uses a high target wave to intentionally exhaust the eligible pool for projected-max availability.
