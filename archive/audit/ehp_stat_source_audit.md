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

## Decisive-stat wiring campaign (source → canonical input → at-wave → Wmax)

This section runs an explicit end-to-end trace for a small decisive stat set:

- `tower_hp`
- `tower_regen`
- `def_pct`
- `wall_hp`
- `wall_regen`
- `thorns_damage_mult`
- `uw_black_hole_cooldown` (BH cd)

### Repro command and scenario

```bash
python - <<'PY'
from pathlib import Path
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.engines.stat_pipeline import build_canonical_stat_pipeline_for_problem_spec
from tower_sim.evaluators.max_wave import MaxWaveEvaluator

spec = load_problem_spec(Path('fixtures/specs/max_wave.yaml'))
ids = parse_ids(Path('tests/fixtures/tower-sim-data/_IDS.csv'))
snapshot = compile_account_snapshot(ids)

pipeline = build_canonical_stat_pipeline_for_problem_spec(
    snapshot=snapshot,
    problem_spec=spec,
    wave=spec.scenario.wave_probe,
    include_perk_timeline=False,
    materialize_stages=True,
)

result = MaxWaveEvaluator().evaluate(spec, snapshot)

print('wave_probe', spec.scenario.wave_probe)
print('w_max', result.get('w_max'))
for stat_id in [
    'tower_hp', 'tower_regen', 'def_pct', 'wall_hp', 'wall_regen',
    'thorns_damage_mult', 'uw_black_hole_cooldown',
]:
    start = pipeline.start_stage.values.get(stat_id)
    at_wave = pipeline.at_wave_stage.values.get(stat_id) if pipeline.at_wave_stage else None
    print(stat_id, 'start=', start, 'at_wave=', at_wave)
PY
```

Observed in this workspace run:

- `wave_probe=100`
- `w_max=1944`
- `tower_hp`: `226100335680000.0` → `226100335680000.0`
- `tower_regen`: `55998800000.0` → `55998800000.0`
- `def_pct`: `1.2412` → `1.2412`
- `wall_hp`: `9724000000000.0` → `9724000000000.0`
- `wall_regen`: `2500000000.0` → `2500000000.0`
- `thorns_damage_mult`: `1.26876` → `1.0150080000000001`
- `uw_black_hole_cooldown`: `46.0` → `46.0`

### Canonical wiring proof table

| Stat | Source rows / tables | Canonical input wiring | Start-of-run composition ledger | At-wave transform | Final use in evaluator path |
| --- | --- | --- | --- | --- | --- |
| `tower_hp` | Source families are tracked in lineage (`workshop`, `lab`, `card`, `relic`, `enhancement`) and observed in canonical diagnostics. | Canonical stat id `tower_hp` in required max-wave inputs. | Canonical `StatInput` uses base + delta + multiplier composition (`base_value * enhancement_multiplier + loadout_delta`), producing the start-stage scalar. | At-wave value is taken from `AtWaveSnapshot` when present; otherwise start-stage fallback is used. | Consumed in boss combat snapshot and copied into boss survivability `combat_params['tower_hp']`. |
| `tower_regen` | Source families tracked/observed in lineage (`workshop`, `lab`, `card`, `relic`, `enhancement`). | Canonical stat id `tower_regen` in required max-wave inputs. | Same canonical ledger fields (base/delta/multiplier) before start-stage result materialization. | At-wave sourced from snapshot if present. | Consumed as `combat_params['tower_regen']` in boss survivability resolution. |
| `def_pct` | Source families tracked/observed in lineage (`workshop`, `lab`, `card`, `relic`). | Canonical stat id `def_pct` in required max-wave inputs. | Composed from canonical input record; in fixture run this is base `0.98` plus delta `0.2612`. | At-wave source if present; then hard-capped through `apply_hard_cap("Defense %", value)` in combat snapshot derivation. | Passed as `combat_params['defense_pct']` to boss survivability resolution. |
| `wall_hp` | Source families tracked/observed in lineage (`workshop`, `lab`, `module`, `enhancement`). | Canonical stat id `wall_hp` in required max-wave inputs. | Canonical ledger composition resolves the start-stage wall HP scalar. | At-wave source if present. | Passed as `combat_params['wall_hp']` into boss survivability. |
| `wall_regen` | Source families tracked/observed in lineage (`workshop`, `lab`, `module`). | Canonical stat id `wall_regen` in required max-wave inputs. | Canonical ledger composition resolves start-stage wall regen scalar. | At-wave source if present. | Passed as `combat_params['wall_regen']` into boss survivability. |
| `thorns_damage_mult` | Source families tracked/observed in lineage (`workshop`, `lab`, `module`, `relic`, `enhancement`). | Canonical stat id `thorns_damage_mult` in required max-wave inputs. | Canonical ledger composition resolves start-stage thorns scalar (fixture start `1.26876`). | At-wave scalar is consumed if present, then clamped into `[0,1]` in combat snapshot derivation (fixture at-wave `1.015008...` then final combat snapshot `1.0`). | Passed as `combat_params['thorns_frac']` to boss survivability. |
| `uw_black_hole_cooldown` (BH cd) | UW track table mapping binds Black Hole cooldown from `AUW_BH_CD_ARRAY.csv`; module substat mapping also supports BH cooldown as canonical delta input. | Canonical stat id is `uw_black_hole_cooldown`; fixture start value resolves to `46.0` from `uw_section:_IDS.csv`. | Canonical ledger composition yields start-stage value and this stat is present in wave snapshot values. | At-wave is unchanged in this fixture run. | Used in timing/uptime diagnostics through `uw_pairs` as `black_hole_cooldown` for interval construction and GT/BH overlap-derived expected damage taken multiplier. This path is diagnostic/auxiliary and not a direct `boss_survivability` combat param field. |

### Scope boundary for this campaign

- This is a wiring proof pass only (source lineage + canonical inputs + stage values + evaluator consumption).
- No mechanics/formula behavior was changed.
- No new mechanics packs/files were introduced.
