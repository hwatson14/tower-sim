# QE unmapped-surface closure patch spec

Repo basis: uploaded `tower-sim-src.zip` snapshot inspected locally on 2026-03-28.

## Objective
Implement the unmapped-surface audit in the current repo **without reintroducing a legacy stat-engine frame**.

This tranche is about QE ownership only:
- governed numeric QE surfaces
- capability/policy QE surfaces
- account metadata surfaces
- parser-drop junk

## Scope boundary
Do this tranche only.
Do not redesign simulators, consumers, or app output formatting beyond what is needed to verify the routing changes.
Do not add new top-level folders.
Do not archive unrelated files.

## Current repo facts verified from this snapshot
- `qe/query_routing.py` loads only one exclusion bucket from `kb/global-rules/contracts/compiler-routing-policy.yaml`: `non_calculator_scope_labs`
- `qe/stat_input_compiler.py` branches on `elif name in NON_CALCULATOR_SCOPE_LABS:` and only writes `notes='non_calculator_scope:<name>'`
- `tests/app/test_main_path_smoke.py` is import-only smoke, not execution smoke
- Existing relevant files confirmed present:
  - `kb/global-rules/contracts/compiler-routing-policy.yaml`
  - `qe/query_routing.py`
  - `qe/stat_input_compiler.py`
  - `kb/cards/tables/card-base-ladders.csv`
  - `kb/cards/tables/card-effect-registry.csv`
  - `kb/cards/tables/card-masteries.csv`
  - `kb/modules/tables/module-lab-wiki-truth.csv`
  - `kb/modules/tables/module-drop-economy-wiki-truth.csv`

## Deliverables
1. Split the current blunt exclusion bucket into four routing classes.
2. Implement compiler behaviour for each class.
3. Fix the obvious alias/routing defect for `Intro Sprint`.
4. Promote the audited rows into the correct class.
5. Add tranche-focused regression tests.

---

## File-by-file patch plan

### 1) `kb/global-rules/contracts/compiler-routing-policy.yaml`

#### Replace
Current top-level key:
- `non_calculator_scope_labs`

#### With four keys
- `parser_drop_rows`
- `account_metadata_rows`
- `capability_policy_rows`
- `governed_numeric_rows`

#### Seed values

##### `parser_drop_rows`
- `END OF ARRAY`

##### `account_metadata_rows`
- `Buy Multiplier`
- `Card Presets`
- `More Round Stats`
- `Workshop Respec`
- `Reroll Daily Mission`
- `Event Relics`
- `Guild Relics`
- `Other Relics`
- `Total Relics`
- `Keys spent`

##### `capability_policy_rows`
- `Unlock Perks`
- `Auto Pick Perks`
- `Perk Option Quantity`
- `First Perk Choice`
- `Ban Perks`
- `Auto Pick Ranking`
- `Target Priority`
- `Extra Orb Adjuster`
- `Unmerge Module`
- `Armor Effect Bans`
- `Cannon Effect Bans`
- `Core Effect Bans`
- `Generator Effect Bans`

##### `governed_numeric_rows`
Move these out of the old non-calculator bucket and into governed QE routing:
- all `... Mastery` rows currently listed there
- `Assist Module Bonus - Armor`
- `Assist Module Bonus - Cannon`
- `Assist Module Bonus - Core`
- `Assist Module Bonus - Generator`
- `Assist Module Substats - Armor`
- `Assist Module Substats - Cannon`
- `Assist Module Substats - Core`
- `Assist Module Substats - Generator`
- `Module Coin Cost`
- `Module Shards Cost`
- `Improve Trade-off Perks`
- `Standard Perks Bonus`
- `Shatter Shards`
- `Reroll Shards`
- `Daily Mission Shards`
- `Starting Cash`
- `Max Interest`
- `Common Drop Chance`
- `Rare Drop Chance`
- `Basic's Ultimate`
- `Boss's Ultimate`
- `Fast's Ultimate`
- `Protector's Ultimate`
- `Ranged Ultimate`
- `Tank's Ultimate`

#### Explicit note
Do **not** leave a legacy `non_calculator_scope_labs` key behind. Remove it entirely so the repo fails loudly if downstream code still depends on it.

---

### 2) `qe/query_routing.py`

#### Goal
Load the four new routing classes and export them as explicit constants.

#### Current verified behaviour
`_load_compiler_routing_policy()` currently returns:
- `non_calculator_scope_labs`
- plus existing override maps

#### Required change
Update `_load_compiler_routing_policy()` so it returns:
- `parser_drop_rows`
- `account_metadata_rows`
- `capability_policy_rows`
- `governed_numeric_rows`
- existing override maps unchanged

#### Add exported constants
Replace:
- `NON_CALCULATOR_SCOPE_LABS = compiler_routing_policy()['non_calculator_scope_labs']`

With:
- `PARSER_DROP_ROWS = compiler_routing_policy()['parser_drop_rows']`
- `ACCOUNT_METADATA_ROWS = compiler_routing_policy()['account_metadata_rows']`
- `CAPABILITY_POLICY_ROWS = compiler_routing_policy()['capability_policy_rows']`
- `GOVERNED_NUMERIC_ROWS = compiler_routing_policy()['governed_numeric_rows']`

#### Update `__all__`
Remove:
- `NON_CALCULATOR_SCOPE_LABS`

Add:
- `PARSER_DROP_ROWS`
- `ACCOUNT_METADATA_ROWS`
- `CAPABILITY_POLICY_ROWS`
- `GOVERNED_NUMERIC_ROWS`

#### Optional but recommended helper
Add a tiny helper if useful:
```python

def routing_class_for_lab_name(name: str) -> str | None:
    if name in PARSER_DROP_ROWS:
        return 'parser_drop'
    if name in ACCOUNT_METADATA_ROWS:
        return 'account_metadata'
    if name in CAPABILITY_POLICY_ROWS:
        return 'capability_policy'
    if name in GOVERNED_NUMERIC_ROWS:
        return 'governed_numeric'
    return None
```
This is optional. Only add it if it simplifies compiler code. Do not add extra files for it.

---

### 3) `qe/stat_input_compiler.py`

#### Goal
Replace the blunt `NON_CALCULATOR_SCOPE_LABS` behaviour with explicit routing-class behaviour.

#### Current verified branch
Inside the labs loop, current code does:
- if direct destination exists -> bind
- `elif name in NON_CALCULATOR_SCOPE_LABS:` -> only notes `non_calculator_scope:<name>`
- else pending routing note

#### Required imports change
Replace import of:
- `NON_CALCULATOR_SCOPE_LABS`

With imports of:
- `PARSER_DROP_ROWS`
- `ACCOUNT_METADATA_ROWS`
- `CAPABILITY_POLICY_ROWS`
- `GOVERNED_NUMERIC_ROWS`

#### Required compiler branch change
Replace the single exclusion branch with four explicit branches.

Target behaviour:

##### A. Parser drop
If `name in PARSER_DROP_ROWS`:
- do not append the row
- optionally count it in a local debug counter if there is already a diagnostics pattern in-file
- do not emit a `StatInput`

##### B. Account metadata
If `name in ACCOUNT_METADATA_ROWS`:
- bind destination to an explicit metadata lane
- use one of:
  - `('account_flag', 'account_meta.<slug>')` for boolean/inventory-style flags, or
  - `('meta_progression_param', 'account_meta.<slug>')` for numeric/account quantities

Use this exact rule unless the repo already has a better established metadata destination convention inside QE:
- booleans or toggle-like rows -> `account_flag`
- numeric/account quantities -> `meta_progression_param`

Suggested destination ids:
- `account_meta.buy_multiplier`
- `account_meta.card_presets`
- `account_meta.more_round_stats`
- `account_meta.workshop_respec`
- `account_meta.reroll_daily_mission`
- `account_meta.event_relic_count`
- `account_meta.guild_relic_count`
- `account_meta.other_relic_count`
- `account_meta.total_relic_count`
- `account_meta.keys_spent`

Set notes like:
- `account_metadata_routed:<name>`

##### C. Capability / policy
If `name in CAPABILITY_POLICY_ROWS`:
- bind destination to `capability` unless the row is more clearly an account flag
- use explicit capability ids

Suggested ids:
- `capability.perks.unlock`
- `capability.perks.auto_pick`
- `capability.perks.option_quantity`
- `capability.perks.first_choice`
- `capability.perks.ban_count`
- `capability.perks.auto_pick_ranking`
- `capability.target_priority`
- `capability.extra_orb_adjuster`
- `capability.modules.unmerge`
- `capability.modules.effect_bans.armor`
- `capability.modules.effect_bans.cannon`
- `capability.modules.effect_bans.core`
- `capability.modules.effect_bans.generator`

Value semantics:
- unlock/boolean rows -> `bool`
- count-like rows such as `Perk Option Quantity` or `Ban Perks` -> resolved numeric value if a lookup exists, otherwise keep level/value semantics but bind the destination now
- policy text rows like `Auto Pick Ranking` can remain raw if the current IDS section stores text, but must still bind destination

Set notes like:
- `capability_policy_routed:<name>`

##### D. Governed numeric
If `name in GOVERNED_NUMERIC_ROWS`:
- do **not** leave it as a note-only unresolved row
- it must bind to a real QE destination or fall through to a very explicit `governed_numeric_pending_mapping:<name>` note
- the goal of this tranche is to reduce that pending set materially, not just rename it

For this tranche, implement the rows with the clearest available KB support first:
- `Standard Perks Bonus`
- `Improve Trade-off Perks`
- `Common Drop Chance`
- `Rare Drop Chance`
- `Reroll Shards`
- `Daily Mission Shards`
- `Shatter Shards`
- `Module Coin Cost`
- `Module Shards Cost`
- all assist module bonus/substat rows
- all enemy `... Ultimate` rows
- `Intro Sprint` alias fix handled separately below

#### Destination guidance for governed numeric rows
Use existing QE destination types already in repo where possible:
- `mechanic_param`
- `runtime_mechanic_param`
- `environment_param`
- `meta_progression_param`
- `canonical_stat` only where the repo already treats that row as a canonical stat contributor

Examples:
- module economy labs -> `meta_progression_param` or `mechanic_param` depending on whether they affect economy probabilities/cost multipliers or runtime mechanics
- perk scaling labs -> `mechanic_param`
- battle-condition ultimates -> `environment_param`
- assist module effects -> `mechanic_param` or `meta_progression_param` depending on current QE consumer usage

#### Important constraint
Do not create a second generic “non calculator” sink under a new name.
Each class must now have real semantics.

---

### 4) `qe/query_routing.py` and `qe/stat_input_compiler.py` together: fix `Intro Sprint`

#### Verified current KB fact
The repo already contains:
- `kb/cards/tables/card-base-ladders.csv` rows for `INTRO_SPRINT`
- `kb/cards/tables/card-masteries.csv` row for `Intro Sprint`
- `kb/cards/tables/card-effect-registry.csv` has an `INTRO_SPRINT` row, but only for `layer=mastery`

That means the KB has real `Intro Sprint` data already. The current unmapped result is a routing/registry gap, not a source-data gap.

#### Required fix
Make base card `Intro Sprint` bind like the other cards.

#### Implementation options
Use the smallest clean fix that matches current card architecture:

##### Preferred
Add the missing base-card target in `kb/cards/tables/card-effect-registry.csv` for `INTRO_SPRINT` so `load_card_effect_targets()` can bind it automatically.

##### If that registry cannot express it cleanly
Add a specific fallback mapping in `qe/query_routing.py` for `Intro Sprint` analogous to existing card fallback logic.

#### Acceptance target
After patch, `Intro Sprint` must no longer appear in the unmapped list when compiling stat inputs from the uploaded account snapshot.

---

### 5) KB-backed governed-numeric promotions

#### 5A. Perk scaling rows
Relevant rows:
- `Standard Perks Bonus`
- `Improve Trade-off Perks`

Primary files to inspect before patching:
- `kb/labs/tables/lab-application-registry.csv`
- `qe/query_perk_compiler.py`
- `kb/perks/tables/perk-effect-registry.csv`
- `kb/perks/tables/perk-entity-registry.csv`

Implementation rule:
- bind these as QE-owned numeric inputs, not metadata
- if exact value ladders are already derivable from existing lab tables, resolve them now
- otherwise bind destination now and preserve level with `governed_numeric_pending_value:<name>`

#### 5B. Module economy rows
Relevant rows:
- `Common Drop Chance`
- `Rare Drop Chance`
- `Reroll Shards`
- `Daily Mission Shards`
- `Shatter Shards`
- `Module Coin Cost`
- `Module Shards Cost`

Primary files:
- `kb/modules/tables/module-lab-wiki-truth.csv`
- `kb/modules/tables/module-drop-economy-wiki-truth.csv`
- `qe/query_module_draw_policy.py`
- `qe/query_module_drop_economy.py`
- `qe/query_module_lab_policy.py`

Implementation rule:
- if query modules already expose destination ids for these, reuse them
- otherwise create QE destination ids in one place only and route these rows there
- prefer `meta_progression_param` for drop/cost modifiers unless current code clearly treats them as runtime mechanics

#### 5C. Assist module rows
Relevant rows:
- `Assist Module Bonus - Armor`
- `Assist Module Bonus - Cannon`
- `Assist Module Bonus - Core`
- `Assist Module Bonus - Generator`
- `Assist Module Substats - Armor`
- `Assist Module Substats - Cannon`
- `Assist Module Substats - Core`
- `Assist Module Substats - Generator`

Primary files:
- `qe/stat_input_compiler.py`
- any existing assist-efficiency lookup already in that file

Implementation rule:
- these should not remain policy-only
- bind them to explicit QE numeric surfaces and preserve current assist efficiency scaling semantics

#### 5D. Battle-condition ultimates
Relevant rows:
- `Basic's Ultimate`
- `Boss's Ultimate`
- `Fast's Ultimate`
- `Protector's Ultimate`
- `Ranged Ultimate`
- `Tank's Ultimate`

Primary files:
- `kb/tournaments/*`
- `kb/enemies/*`
- `qe/query_routing.py`
- `qe/stat_input_compiler.py`

Implementation rule:
- route them to `environment_param` destinations under a stable naming family such as:
  - `enemy.basic.ultimate_enabled`
  - `enemy.boss.ultimate_enabled`
  - etc.
- if the underlying IDS values are levels or booleans, preserve the correct value type
- do not leave them in lab limbo

---

### 6) Tests

#### Add or update tests in existing folders only
Do not create a new test domain folder.

Recommended files:
- `tests/qe/test_compiler_routing_policy_split.py`
- `tests/qe/test_unmapped_surface_reclassifications.py`
- or append to an existing `tests/qe/*` file if that fits current style better

#### Required test cases

##### A. Policy contract load test
Assert `compiler_routing_policy()` now returns:
- `parser_drop_rows`
- `account_metadata_rows`
- `capability_policy_rows`
- `governed_numeric_rows`

And does **not** return:
- `non_calculator_scope_labs`

##### B. Parser junk drop test
Compile stat inputs on a tiny synthetic account state containing `END OF ARRAY` in labs/raw rows.
Assert no `StatInput` with `stat_name == 'END OF ARRAY'` survives.

##### C. Account metadata routing test
For one representative metadata row such as `Keys spent`:
- assert it binds to the metadata lane
- assert notes show `account_metadata_routed:Keys spent`

##### D. Capability/policy routing test
For one representative row such as `Auto Pick Perks`:
- assert destination object type is `capability`
- assert notes show `capability_policy_routed:Auto Pick Perks`

##### E. Governed numeric routing test
For one representative row such as `Common Drop Chance` or `Standard Perks Bonus`:
- assert it no longer lands as unmapped/non-calculator
- assert destination is populated

##### F. Intro Sprint regression test
Compile the uploaded account snapshot or a narrow synthetic card state.
Assert `Intro Sprint` is mapped after patch.

#### Optional but valuable
Upgrade `tests/app/test_main_path_smoke.py` from import-only to one real execution smoke using the shipped input files, but only if this can be done cheaply and deterministically.
This is not required for the tranche to close, but it is recommended because the current test file is weaker than its name implies.

---

## Acceptance criteria

### Functional acceptance
1. `kb/global-rules/contracts/compiler-routing-policy.yaml` no longer contains `non_calculator_scope_labs`.
2. `qe/query_routing.py` loads and exports the four new routing classes.
3. `qe/stat_input_compiler.py` no longer contains `NON_CALCULATOR_SCOPE_LABS`.
4. `END OF ARRAY` is dropped during compilation.
5. Representative rows from each new class bind to real QE destinations with the correct destination type.
6. `Intro Sprint` is no longer unmapped in the compiled stat inputs for the current repo snapshot.
7. At least the specifically targeted governed-numeric rows listed above are no longer note-only unresolved rows.

### Verification commands
Run these after patching:

```bash
pytest -q
python -m app.run_stats
```

If `python -m app.run_stats` still fails for known unrelated integration issues, document that clearly, but the QE tranche itself must still prove:

```bash
python - <<'PY'
from input.loader import load_inputs
from qe.stat_input_compiler import compile_stat_inputs

account_state, _, _ = load_inputs()
rows = compile_stat_inputs(account_state, preset_name=account_state.default_preset, state_mode='start_of_run')

names = {r.stat_name for r in rows}
assert 'END OF ARRAY' not in names

check = [
    'Intro Sprint',
    'Common Drop Chance',
    'Standard Perks Bonus',
    'Keys spent',
    'Auto Pick Perks',
]
for name in check:
    matched = [r for r in rows if r.stat_name == name]
    print(name, len(matched), [(r.destination_object_type, r.destination_id, r.notes) for r in matched[:3]])
PY
```

### Closure criteria
Close the tranche only if:
- the old bucket is gone
- the four-class routing is live
- `Intro Sprint` is mapped
- representative metadata, capability, and governed-numeric rows are all routed correctly
- regression tests pass

---

## Things not to do
- Do not say “stat engine” in code comments, docs, or tranche notes. This is QE ownership now.
- Do not create one-off adhoc files for each subfamily.
- Do not create another generic sink bucket under a different name.
- Do not block closure on mapping every possible mastery row if the tranche has already proven the four-lane routing model and the highest-value governed rows.

---

## Recommended execution order
1. Patch `compiler-routing-policy.yaml`
2. Patch `qe/query_routing.py`
3. Patch `qe/stat_input_compiler.py` classification logic
4. Fix `Intro Sprint`
5. Promote the explicit governed rows listed above
6. Add tests
7. Run verification
8. Report residual rows, if any, by routing class

---

## Closeout report format requested from Codex
Return a concise report with:
- files changed
- old bucket removed: yes/no
- four routing classes live: yes/no
- `Intro Sprint` mapped: yes/no
- rows reclassified by class: counts
- remaining governed-numeric pending mappings: exact list
- test results
- whether `python -m app.run_stats` passes, and if not, exact failing symbol/path
