# TowerSim V2 UW+ Source-State Forensic Audit (Fail-Closed)

## Scope
Determine whether Ultimate Weapon Plus (UW+) **account progression/state** exists in current repo source artifacts and parser ingress paths.

Allowed verdicts:
- **A**: source exists and is parseable now
- **B**: source exists but is not yet plumbed into normalized snapshot surfaces
- **C**: source does not exist in current export/snapshot path

## Candidate surfaces inspected

### 1) Raw IDS fixture surface (account export candidate)
- File: `tests/fixtures/tower-sim-data/_IDS.csv`
- Evidence:
  - UWs section exists at fixed header slot (`SECTION_SPECS` uses `SectionSpec("UWs", 25, 25, 29)`), so parser ingests one UWs block only.
  - UWs raw rows contain explicit `UW+` rows with plus track names and lock markers, e.g. `UW+ ... Smite ... Locked ... Lo | Locked` and analogous rows for Cover Fire/Kill Wall/etc.
- Classification: **account-state source candidate present in raw export rows** (as raw row strings), but not yet represented as structured UW+ account state in snapshot model.

### 2) IDS parser ingress
- File: `tower_sim/loaders/ids_parser.py`
- Evidence:
  - Only one section spec for UWs (`SectionSpec("UWs", 25, 25, 29)`), no separate UW+ section.
  - Parser behavior is section slicing into raw rows; no dedicated UW+ model extraction in this module.
- Classification: **ingress exists for raw UWs rows**, not dedicated UW+ typed state.

### 3) Account snapshot compiler
- File: `tower_sim/loaders/account_snapshot_compiler.py`
- Evidence:
  - `_parse_ultimate_weapons` explicitly skips rows where `name == "UW+"`.
  - Output `ultimate_weapons` includes only base UW rows.
- Classification: **UW+ raw rows are discarded during snapshot compilation**.

### 4) Snapshot model surfaces
- File: `tower_sim/util/account_snapshot.py`
- Evidence:
  - `AccountSnapshot` has `ultimate_weapons` but no UW+ progression field.
- File: `tower_sim/util/ids_state.py`
- Evidence:
  - `UltimateWeaponsState` contains `uw_plus_placeholder` only (placeholder, not concrete progression state).
- Classification: **not plumbed typed UW+ account state**.

### 5) Snapshot audit payloads
- File: `audit/account_snapshot.json`
- Evidence:
  - `snapshot.raw_sections.UWs` includes multiple `"UW+"` rows with plus track names and lock/display strings.
  - `snapshot.ultimate_weapons` contains base UW entries only.
- File: `audit/account_snapshot.summary.json`
- Evidence:
  - no UW+/ultimate-weapon-plus progression keys.
- Classification: **raw evidence present; normalized snapshot UW+ state absent**.

### 6) Existing V2 Phase B source-state coverage status
- File: `tower_sim/loaders/source_state_v2.py`
- Evidence:
  - `uw_plus` listed as required family and now implemented in source-state normalization from typed snapshot fields.
- File: `audit/static_pipeline_v2_phase_b_source_state_coverage.yaml`
- Evidence:
  - `uw_plus` marked `adapter_implemented: true`, `blocked_or_deferred: false`.
- File: `tables/meta/registry/v2/quarantine_registry.yaml`
- Evidence:
  - UW+ contributor IDs remain quarantined with mapping-deferred reason until canonical contributor mapping is completed.
- Classification: **fail-closed tracking already in place**.

### 7) Reference ladders/cost tables (non-account-state)
- File: `tables/inputs/uw/uw_plus_ladders_v1.csv`
- Evidence:
  - columns include `uw_name`, `level_index`, `value`, `cost`, `plus_track_name`.
- File: `tables/inputs/uw/uw_purchase_costs_v1.csv`
- Evidence:
  - columns include `uw_plus_unlock_count`, `uw_plus_unlock_cost`.
- Classification: **reference data only** (cost/value ladders), not player progression snapshot state.

## Reference-vs-account-state separation
- **Reference ladders/cost tables:** exist and are parseable (`uw_plus_ladders_v1.csv`, `uw_purchase_costs_v1.csv`).
- **Account progression/state:** raw UW+ row tokens exist in IDS/UWs rows and are now exposed via typed `uw_plus_tracks` snapshot fields for source normalization.

## Final verdict
**A — source exists and is parseable now.**

Rationale:
- There is concrete raw account-export evidence in IDS/UWs rows (`UW+` rows with track names + lock/display values).
- Current snapshot compiler/model now expose typed UW+ row-4 state fields for source normalization.

## Smallest safe next step (no mechanics)
1. Keep UW+ contributors quarantined until canonical contributor mapping is completed against the typed UW+ source fields.
2. Add/refresh crosswalk entries tying quarantined UW+ contributor IDs to typed `uw_plus` source_state_field names.
3. Preserve fail-closed gate: UW+ stays quarantined until mapping is explicit and validated.

## External evidence needed from user (if available, to de-risk plumbing)
Optional additional evidence to strengthen future canonical contributor mapping confidence:
- At least one IDS export where one or more UW+ tracks are unlocked/non-locked (to verify row-4 level encoding beyond `Locked`).
- Any official export schema note confirming UW+ row semantics in UWs section.
