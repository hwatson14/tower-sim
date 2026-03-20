# Surface Ownership Ledger

## 1. Stat engine

### Owns
| Surface family | Examples | Notes |
|---|---|---|
| Workshop baseline levels | start-of-run workshop levels by track | Baseline state only |
| Current workshop snapshot inputs for recalculation | per-track current run levels | Progression owns the state transitions, stat engine owns formula resolution from the snapshot |
| Labs | canonical lab contributions | Account truth |
| Cards/loadout | equipped cards and resolved effects | Fixed for run |
| Modules | resolved module stat effects | Fixed for run |
| Relics | resolved relic contributions | Fixed for run |
| UW owned state | owned UWs and fixed stat contributions | Not scenario-adjusted uptime/sync |
| Bot owned state | owned bots and fixed stat contributions | Not scenario-adjusted cadence/sync |
| Fixed perk overlays | HP, regen, enemy damage, BH duration add, CF duration add, trade-off channels | Perk set fixed for run |
| Canonical defensive stats | `wall_hp`, `wall_regen`, `tower_defense_pct`, `tower_hp`, `tower_regen` | Fixed outputs at current recalculation step |
| Canonical boss-relevant utility/offense stats | `enemy_attack_level_skip_pct`, `enemy_health_level_skip_pct`, `tower_thorns_damage_pct`, `tower_orb_count`, `tower_orb_speed_rpm` | Fixed outputs at current recalculation step |
| Published fixed effect surfaces | perk-derived adds/multipliers that are not best expressed as canonical stats | Separate namespace, same engine |

### Does not own
- `mode_id`
- battle conditions
- heat/environment overlays
- boss interval / boss hit interval selections
- in-run workshop state transitions
- wave progression state

---

## 2. Scenario-invariant derived effects engine

### Inputs
- stat engine outputs
- `mode_id`
- battle condition selection
- heat/environment selection

### Owns
| Surface family | Examples | Notes |
|---|---|---|
| Scenario selectors | `mode_id`, active BC set, heat profile | Fixed for run |
| UW cadence surfaces | BH duration/cooldown/uptime, CF duration/cooldown/uptime | Scenario-adjusted reusable surfaces |
| UW averaged effect surfaces | CF avg DR contribution, BH uptime fraction | Fixed for run |
| Bot cadence surfaces | bot cooldowns, activation frequencies, uptime fractions | Reusable |
| Sync/overlap surfaces | GT/BH overlap, bot/UW overlap windows | Reusable |
| Scenario-adjusted resistances | plasma cannon, orb, thorns resistances | BC/heat driven |
| Scenario-adjusted intervals | boss hit interval, boss frequency if scenario changes it | Fixed for run |
| Environment overlays | enemy damage multiplier, attack speed multiplier | Fixed for run |

### Does not own
- canonical baseline stat formulas
- perk selection logic
- in-run workshop changes
- attack wave / health wave
- boss heat-up accumulation state
- boss TTK state

---

## 3. Progression engine

### Owns
| Surface family | Examples | Notes |
|---|---|---|
| In-run workshop state | current levels for every workshop track | Must track all tracks |
| Free-upgrade state | realized or expected free upgrades | Run-evolving |
| Buy-policy state | manual purchases / allocation policy | Run-evolving |
| Wave state | `boss_wave`, `attack_wave`, `health_wave` | Dynamic |
| Current survival state | wall pool start/end, regen accrued, margin | Dynamic |
| Combat state | boss remaining HP, contact timing, hits taken, heat-up stack | Dynamic |
| Recalc trigger control | when to recompute stats | Dynamic control logic |

### Consumes
- stat engine outputs
- scenario-invariant surfaces
- current run state
- stat recalculation service

---

## Temporary fallback surfaces
| Surface | Temporary owner | Final target owner | Status |
|---|---|---|---|
| Plasma Cannon boss damage % | stat engine temporary adapter | stat engine emitted surface | Temporary fallback |
| Orb boss hit cadence | scenario override / invariant engine | scenario-invariant emitted surface | Gap |
| Electron boss hit cadence | scenario override / invariant engine | scenario-invariant emitted surface | Gap |

Rule:
- every fallback must be explicit
- every fallback needs an exit condition
- no fallback may pretend to be canonical/final


## Perk timeline ownership note
The perk timeline is **static for the run once generated**, but it is not merely a final perk set if wave-accurate progression is being modeled.

- the **perk timeline generator** owns *when* perks are obtained and must handle retrospective PWR internally
- the **stat engine** owns perk effect resolution from a supplied perk state or generated final-state artifact
- the **progression engine** may consume the generated timeline to derive the active perk state at a given wave, but should not re-implement PWR timing logic
