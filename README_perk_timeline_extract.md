# Perk Timeline Generator

Generates a deterministic perk selection timeline: which perk is taken at which wave, given an account's lab state, bans, and priority preferences.

## KB alignment

Every formula and threshold is grounded in a named KB source:

| Mechanic | KB source | Notes |
|----------|-----------|-------|
| Base wave requirement steps (200/250/300/350) | `kb/perks/tables/perk-wave-requirement-steps.csv` | Materialized from `kb/perks/notes/perk-system.md` |
| Perk identities and max_picks | `kb/perks/tables/perk-entity-registry.csv` | 34 perks, wiki-verified 2026-03-14 |
| Pool category weights (65/20/15) | `kb/perks/tables/perk-pool-weights.csv` | standard / ultimate_weapon / trade_off |
| PWR stacking: linear additive | `kb/perks/tables/perk-entity-registry.csv` | `stacking_type=additive` for PWR perk |
| PWR per-stack reduction: -20% | `kb/perks/tables/perk-effect-registry.csv` | `remaining_fraction=0.80` |
| Waves Required lab: additive delta | `kb/labs/tables/lab-values.csv` | level N → -N waves |
| Standard Perk Bonus: scales reduction | `kb/perks/sources/wiki-perks-baselines.md` | Verified against wiki Standard Perk Bonus page |

### PWR wave schedule formula

Wiki source: https://the-tower-idle-tower-defense.fandom.com/wiki/Perks

```
step_exact = (base - WR_lab) * (1 - PWR_qty * 0.20 * (1 + SPB / 100))
ideal_wave(N) = floor(sum of section_count * step_exact per section)
```

PWR is **retroactive** ("Perk Wave Requirement is retrospective" — wiki guide). When PWR is picked, the engine recalculates all future perk waves. If the recalculated ideal wave is at or before the current wave, the perk is awarded immediately (burst).

Verified against community reference spreadsheet (v0.14.4, WR_lab=13, SPB=25):
- Lab column (0 PWR): **45/45 exact match**
- 1 PWR column: **45/45 exact match**
- Section boundaries (perks 21, 31, 41): **all exact**

## Bug fixes from original extract

1. **Pool prunes exhausted perks.** After a perk reaches `max_picks`, it is removed from the offer pool. Previously it stayed in the pool and caused early termination if re-selected.
2. **Priority loop checks max_picks.** Exhausted perks in the priority list are skipped. Previously they were selected and triggered a hard stop.
3. **first_perk_choice respects bans.** The first-perk override now checks eligibility (not banned). Previously a banned perk could be force-inserted as the first pick.
4. **PWR is retroactive, not incremental.** Changed from incremental step accumulation to retroactive ideal-wave computation. When PWR is picked, the engine recalculates ideal waves for ALL future perks and awards immediate bursts for any that fall at or before the current wave. Matches wiki: "Perk Wave Requirement is retrospective."
5. **Wave requirement steps loaded from KB table.** Previously hardcoded as magic numbers. Now sourced from `kb/perks/tables/perk-wave-requirement-steps.csv`.

## CLI usage

```bash
python scripts/generate_perk_timeline.py \
  --policy policy.json \
  --out out/perk_timeline.json \
  --diagnostics out/perk_timeline_diag.json
```

### policy.json

```json
{
  "seed": 42,
  "target_wave": 3000,
  "waves_required_lab": 13,
  "standard_perk_bonus": 0.25,
  "perk_option_quantity": 2,
  "ban_perks_capacity": 6,
  "banned_perks": ["Interest x1.50", "x1.15 Cash Bonus"],
  "priority_order": [
    "Perk Wave Requirement -20.00%",
    "x1.20 Max Health",
    "x1.15 Damage"
  ],
  "first_perk_choice": "Perk Wave Requirement -20.00%"
}
```

| Field | Source | Notes |
|-------|--------|-------|
| `waves_required_lab` | `abs(milestones.waves_required_delta)` from v92 | Positive integer, subtracted from base |
| `standard_perk_bonus` | `Standard Perks Bonus lab level / 100` | e.g. level 25 → 0.25 |
| `perk_option_quantity` | `Perk Option Quantity` IDS value | 0–2 (adds to base 2 offers) |
| `ban_perks_capacity` | `Ban Perks` IDS value | Max bans applied from banned_perks list |

### Output format

`perk_timeline.json` — array of perk events:
```json
[
  {
    "wave": 187,
    "perk_taken": "Perk Wave Requirement -20.00%",
    "effect": "−20.00% waves required",
    "effect_stat_id": null,
    "stacking_type": "additive",
    "quantity": 1,
    "offered": ["Unlock a Random Ultimate Weapon", "x1.20 Max Health", "Land Mine Damage x3.50", "Perk Wave Requirement -20.00%"]
  }
]
```

## Included files

### Runtime code
- `tower_sim/engines/perk_timeline_generator.py` — timeline generation engine
- `tower_sim/loaders/perk_tables.py` — KB table loaders
- `tower_sim/loaders/table_paths.py` — table manifest and path resolution
- `scripts/generate_perk_timeline.py` — CLI entry point

### KB material
- `kb/perks/tables/perk-wave-requirement-steps.csv` — **new**: materialized wave requirement step thresholds
- `kb/perks/tables/perk-entity-registry.csv` — perk identities and max_picks
- `kb/perks/tables/perk-effect-registry.csv` — structured perk effects
- `kb/perks/tables/perk-pool-weights.csv` — category pool weights
- `kb/perks/tables/perks.csv` — legacy perk table
- `kb/perks/contracts/perk-runtime-contract.md`
- `kb/perks/contracts/perk-effect-application-contract.md`

### Tests
- `tests/test_perk_tables.py` — 16 tests covering all bug fixes, KB alignment, and formula verification

## Boundary

This is the timeline generator only. It does **not** include:
- Applying perk effects onto stats at runtime (v92 stat calculator handles this)
- Stat engine integration
- Loading generated timelines into v92 perk presets

The output timeline can be converted to v92's `{perk_id, picks}` format by aggregating `taken_counts` from the diagnostics output.
