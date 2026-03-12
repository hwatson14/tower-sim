
# TowerSim v1 Handover Pack

## 1. HANDOVER_README

### Purpose
This handover provides the active v1 static contributor ledger for TowerSim.

The ledger is contributor-centric.  
Each row represents:

- one direct contributor
- from one contributor family
- affecting one target stat

This is the active working baseline built from the Tower wiki and normalized through the later review passes.

### Primary file
Use this as the canonical ledger:

```
ledger/towersim_static_ledger_latest.csv
```

### Optional views
These are filtered convenience views, not separate sources of truth:

```
ledger/optional_views/towersim_static_ledger_base_targets_iter_36.csv
ledger/optional_views/towersim_static_ledger_derived_targets_iter_36.csv
```

The master ledger remains the canonical source.

### Current status
Total active rows: **479**

Confidence distribution:
- Strong confidence rows: **475**
- Medium confidence rows: **4**
- Weak confidence rows: **0**

### Contributor families currently represented

- workshop
- enhancement
- lab
- card
- relic
- module_main
- module_sub
- module_unique
- perk
- bot
- uw
- uw_plus
- battle_condition
- guardian

### Core schema intent
Important columns in the active ledger include:

- ledger_scope
- source_family
- wiki_track_name
- source_item
- wiki_page_title
- wiki_page_url
- state_field
- max_level_field
- activation_field
- contributor_id
- semantic_type
- operation
- target_stat
- raw_or_derived
- dependencies
- unlock_notes
- wiki_semantic_note
- confidence
- uncertainty_notes
- source_ref

### Canonical rules

- `target_stat` is the canonical output column.
- `contributor_id` is the stable contributor identifier.
- The ledger is contributor-centric, not stat-centric.
- Derived-target contributors stay in the master ledger.
- Split views are for convenience only.
- **One row = one contributor → one target stat.**
- Multi-effect source items are split into multiple rows where needed.
- `operation` is explicit and should not be inferred only from names.
- `semantic_type` is descriptive, but `operation` is the engine-facing action.

### What this handover is not claiming
This handover is not claiming:

- a byte-for-byte recovery of every historical intermediate bundle
- complete certainty for every row
- full runtime combat behavior modeling
- that every downstream combat-model naming choice is frozen forever

It is a **cleaned v1 static contributor ledger baseline**.

### Remaining unresolved block
The only material unresolved block is the exact emitted value curve for the four `module_main` rows:

- module_main__damage__multiplier
- module_main__health__multiplier
- module_main__coin_bonus__multiplier
- module_main__ultimate_weapon_damage__multiplier

These rows remain **medium confidence** because the slot mapping and progression behavior are pinned, but the exact emitted curve was not fully pinned from the sourced wiki material used in the build.

### Recommended usage

For downstream use:

1. Ingest `towersim_static_ledger_latest.csv`
2. Filter by confidence if needed
3. Use `target_stat` as the canonical destination field
4. Use `operation` plus `semantic_type` instead of inferring behavior from names alone
5. Treat `uncertainty_notes` as active caveats, not decoration

### Suggested next follow-up

If another pass is done later, the highest-value next task is:

**Resolve the 4 `module_main` emitted value curves from an approved source.**

---

## 2. HANDOVER_SUMMARY

### Scope
This handover covers the active v1 static contributor ledger baseline for TowerSim, rebuilt from the last reliable downloadable working bundle and later normalized through schema cleanup, confidence burn-down, and family expansion.

### Active state snapshot

- Active ledger rows: **479**
- Strong confidence: **475**
- Medium confidence: **4**
- Weak confidence: **0**
- Duplicate `contributor_id`: **0**
- Base-target rows: **466**
- Derived-target rows: **13**

### Family coverage
The active ledger includes:

- workshop
- enhancement
- lab
- card
- relic
- module_main
- module_sub
- module_unique
- perk
- bot
- uw
- uw_plus
- battle_condition
- guardian

### Important modeling decisions already made

- `target_stat` replaced `resolved_property`
- redundant columns were removed from the active schema
- relics were aggregated to family-total contributors by target stat
- derived-target contributors remain in the master ledger
- split base-target / derived-target views exist as convenience only
- `activation_field` added because some contributors may exist but not be active
- `uw_plus` split from `uw`
- battle conditions modeled as their own contributor family
- guardian modeled at base/equipped chip parameter level

### Confidence state

Remaining medium-confidence rows:

- module_main__damage__multiplier
- module_main__health__multiplier
- module_main__coin_bonus__multiplier
- module_main__ultimate_weapon_damage__multiplier

Everything else in the active ledger is **strong confidence**.

### Consumption guidance

Use:

- the **master ledger** for canonical ingestion
- the **base-target view** if only raw/base stats are required
- the **derived-target view** if focusing on derived outputs such as wall stats

### Important caveat

This is a **functional rebuilt active baseline**, not a forensic recovery of every historical artifact.

---

## 3. OPEN_ISSUES

### Open issue 1: module_main emitted value curves

Rows affected:

- module_main__damage__multiplier
- module_main__health__multiplier
- module_main__coin_bonus__multiplier
- module_main__ultimate_weapon_damage__multiplier

### What is known

The wiki pins:

- slot-to-target mapping
- level-driven main-effect progression
- rarity/star dependent max level

### What is not yet fully pinned

The **exact emitted value curve**.

### Current treatment

```
confidence = medium
```

Rows remain in the active ledger with explicit uncertainty.

### Why this does not block v1

The unresolved block is small, localized, and explicit.

---

## 4. HANDOFF_CHECKLIST

Use this checklist when handing the ledger to another person, tool, or code path.

### Canonical data

- Use `towersim_static_ledger_latest.csv` as the master ledger
- Do not treat split views as separate sources of truth
- Use `target_stat` as the canonical output field
- Use `contributor_id` as the stable identifier

### Schema usage

- Use `operation` for engine behavior
- Use `semantic_type` for descriptive shape
- Use `state_field`, `max_level_field`, and `activation_field` where relevant
- Do not infer math from field names alone

### Confidence handling

- Treat all medium rows as known open issues
- Treat `uncertainty_notes` as active caveats
- Do not silently promote medium rows to strong

### Derived targets

- Keep derived-target contributors in the master ledger
- Use derived-target view only as a filter
- Do not remove derived contributors from canonical ingestion

### Governance

- One row = one contributor → one target stat
- Add rows only when the contributor identity and target can be defended
- Do not reintroduce removed redundant columns without reason

---

## 5. GOVERNANCE_ACTIVE

### Canonical shape

The master ledger is **contributor-centric**.

One row represents one direct contributor targeting one target stat.

- `target_stat` is canonical
- `contributor_id` is stable

### Schema rules

Redundant columns already removed:

- duplicate family column
- duplicate contributor field column
- constant field-kind column
- constant v1 static scope column

### Allowed contributor families

- workshop
- enhancement
- lab
- card
- relic
- module_main
- module_sub
- module_unique
- perk
- bot
- uw
- uw_plus
- battle_condition
- guardian

### Derived-target rule

Derived-target contributors remain in the master ledger.

Examples:

- wall health contributors
- wall regen ratio contributors
- wall thorns ratio contributors

### Confidence rules

- **strong** → pinned by sourced wiki evidence
- **medium** → contributor real but value curve uncertain
- **weak** → avoid (none currently active)

### Change-control rule

Do not add rows because they “seem right.”

Add rows only when contributor identity and target can be defended.

### Operation rule

`operation` must be explicit.  
Never use placeholder values like `review_required` in active output.

---

## 6. LEDGER_SCHEMA_DICTIONARY

| Column | Meaning |
|------|------|
| ledger_scope | Ingestion/build grouping label |
| source_family | Contributor family |
| wiki_track_name | Wiki mechanic label |
| source_item | Source item name |
| wiki_page_title | Wiki page title |
| wiki_page_url | Wiki page URL |
| state_field | Progression state field |
| max_level_field | Max progression state |
| activation_field | Equip/activation gating |
| contributor_id | Stable contributor identifier |
| semantic_type | Semantic shape of value |
| operation | Engine-facing action |
| target_stat | Canonical destination stat |
| raw_or_derived | Base or derived stat |
| dependencies | Dependencies required |
| unlock_notes | Unlock requirements |
| wiki_semantic_note | Short sourcing interpretation |
| confidence | Confidence level |
| uncertainty_notes | Explicit caveats |
| source_ref | Build-time provenance |

---

## 7. ACTIVE NAMING CONTRACT SUMMARY

### Core pattern

The ledger distinguishes:

- progression state
- contributor output
- target stat

### State field pattern

```
<source_family>__<track>__<state_kind>
```

Examples:

```
workshop__health__level
lab__health__level
uw__black_hole_size__level
```

### Contributor identifier pattern

```
<source_family>__<property_or_track>__<semantic_suffix>
```

Examples:

```
workshop__health__base
lab__health__bonus
card__health__multiplier
```

### Canonical output

Examples:

```
health
critical_factor
black_hole_duration_seconds
wall_regen
free_attack_upgrade_chance
```

### Common suffix families

- base
- multiplier
- pct
- pct_bonus
- chance
- chance_bonus
- ratio
- count
- count_bonus
- range_m
- duration_seconds
- duration_seconds_bonus
- cooldown_seconds
- cooldown_seconds_reduction
- interval_seconds_reduction
- enabled
- cap
- angle_degrees
- rotation_rate
- scalar_bonus

### Important rule

Names help readability, but engines must rely on:

- `operation`
- `target_stat`
- `semantic_type`

—not string parsing.

---

## 8. WHAT IS COMPLETE VS NOT COMPLETE

### Complete enough for v1

- contributor family coverage is broad
- ledger is contributor-centric
- schema decisions are locked
- redundant columns removed
- confidence set mostly strong
- split views exist
- uncommon families represented (perks, modules, guardian)

### Not complete

- exact module_main emitted value curves
- runtime combat model mechanics
- guarantee that all future naming will remain frozen

---

## 9. RECOMMENDED NEXT ACTIONS

### Highest value

Resolve the **4 module_main emitted value curves** from an approved source.

### Medium value

Normalize `source_ref` style for long-term provenance tracking.

### Lower value

Generate a repo-ready README explaining:

- master ledger
- optional views
- confidence handling
- derived-target contributor policy
