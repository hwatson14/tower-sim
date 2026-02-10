# EHP vertical slice - data & mapping audit (task 1)

## Scope
This audit identifies which sources currently back the vertical-slice stats needed
for the EHP stat set (Health, Health Regen, Defense %, Wall Health, Wall Regen,
Wall Fortification). It only maps existing tables and IDS inputs; no mechanics
are implemented here.

## Source inventory (current repo assets)

### Workshop base tables (WSValues / DVT_Workshop)
* **WSValues.csv** (fixture export): contains base levels for `Health` and
  `HPregen` (workshop base tower HP and regen).【F:tests/fixtures/tower-sim-data/WSValues.csv†L1-L3】
* **DVT_Workshop.csv** (fixture export): contains `Wall Health` under the
  DVT_Workshop headers (workshop+ column set).【F:tests/fixtures/tower-sim-data/DVT_Workshop.csv†L1-L3】

> Provenance note: the fixture manifest indicates WSValues/DVT_Workshop are
> exported sheets with those names; the file list is tracked under
> `tests/fixtures/tower-sim-data/manifest.json`.【F:tests/fixtures/tower-sim-data/manifest.json†L5-L19】

### Labs canonical table (labs_values_v1.csv)
The canonical labs table in `tables/labs_values_v1.csv` is promoted from
wiki-cache tables (documented in `tables/README.md`).【F:tables/README.md†L8-L10】
Relevant lab rows present:
* `LAB_HEALTH` (Health multiplier).【F:tables/labs_values_v1.csv†L42-L51】
* `LAB_HEALTH_REGEN` (Health Regen multiplier).【F:tables/labs_values_v1.csv†L142-L151】
* `LAB_WALL_HEALTH` (Wall Health % bonus).【F:tables/labs_values_v1.csv†L262-L271】
* `LAB_WALL_REGEN` (Wall Regen % bonus).【F:tables/labs_values_v1.csv†L312-L321】

### IDS inputs
The `_IDS.csv` fixture includes workshop rows for Defense % and Wall
Fortification (levels + max).【F:tests/fixtures/tower-sim-data/_IDS.csv†L31-L42】

## Mapping summary (current data availability)

Note: Effective Paths lists Wall Health and Wall Fortification separately, but
this simulator will handle Wall Fortification separately (no StatDef required);
the in-game mapping (Wall Fortification == Wall Health) should be applied at
the engine layer with explicit provenance when implementing mechanics.

| Stat | Workshop base source | Lab modifier source | Status |
| --- | --- | --- | --- |
| Health | WSValues.csv (`Health`) | labs_values_v1.csv (`LAB_HEALTH`) | **Available** |
| Health Regen | WSValues.csv (`HPregen`) | labs_values_v1.csv (`LAB_HEALTH_REGEN`) | **Available** |
| Defense % | `_IDS.csv` has WS entry | **No canonical table located** | **Blocked** (needs authoritative table/mechanic) |
| Wall Health | DVT_Workshop.csv (`Wall Health`) | labs_values_v1.csv (`LAB_WALL_HEALTH`) | **Partially available** (workshop+ base + lab %) |
| Wall Regen | **No workshop base table located** | labs_values_v1.csv (`LAB_WALL_REGEN`) | **Blocked** (base source missing) |
| Wall Fortification | `_IDS.csv` has WS entry | **No canonical table located** | **Blocked** (needs authoritative table/mechanic) |

## Gaps / fail-closed notes
* **Defense %:** No canonical table entry found in `tables/labs_values_v1.csv` or
  WSValues/DVT_Workshop fixture exports. Treat as blocked until an authoritative
  source table or sheet range is provided.
* **Wall Regen base:** Lab bonus exists, but a base wall regen workshop table is
  not present in WSValues/DVT_Workshop fixture exports. Treat as blocked.
* **Wall Fortification:** Present in `_IDS.csv` but no corresponding canonical
  table in `tables/`.

## Effective Paths workbook mapping (missing mechanics provenance)
Effective Paths models Defense %, Wall Regen, and Wall Fortification as computed
values rather than direct WS/DVT tables. The workbook locations below are the
authoritative sources for those computed mechanics and should be used when
implementing the sim-side mechanics (per fail-closed rules).

### Computed values (eHP sheet)
The eHP sheet defines the computed values at `AG16:AG22`, which point to the
authoritative formulas in `AI16:AI22`:
* **Health**: `AG16` → `AI16` (formula `EPH_HEALTH(...) * EPH_ARMOR(...)`).
* **Health Regen**: `AG17` → `AI17` (formula `EPH_REGEN(...)`).
* **Defense Absolute**: `AG18` → `AI18` (formula `EPH_DABS(...)`).
* **Defense %**: `AG19` → `AI19` (formula `EPH_DEF_PCT(...)`).
* **Wall Health**: `AG20` → `AI20` (formula `EPH_WALL_HEALTH(..., 0) * EPH_HEALTH(...) * EPH_ARMOR(...)`).
* **Wall Fortification**: `AG21` → `AI21` (formula `EPH_WALL_HEALTH(..., AU11) * EPH_HEALTH(...) * EPH_ARMOR(...)`).
* **Wall Regen**: `AG22` → `AI22` (formula `EPH_WALL_REGEN(...) * EPH_REGEN(...)`).

### Inputs (Copy of _IDS)
The `Copy of _IDS` sheet contains embedded values that match the Effective Paths
sheet inputs and should be used when tracing inputs for the above formulas.

### Computed value placeholders
The `_IDS` sheet marks the computed values as `COMPUTED_VALUE` placeholders,
indicating they must be derived from formulas:
* Defense % (`F23`).
* Wall Regen (`A39`).
* Wall Fortification (`A42`).

## Recommendation
Proceed to task 2 only after resolving missing authoritative sources for Defense
%, Wall Regen base, and Wall Fortification to preserve fail-closed behavior.

## Recheck notes (latest merge)
The repository snapshot in this workspace does not include the referenced
identifier resolver files or `tables/runtime` artifacts described in the
latest merge summary. Re-run this audit after those files are present, as they
may introduce authoritative mappings that unblock Defense %, Wall Regen base, or
Wall Fortification.
