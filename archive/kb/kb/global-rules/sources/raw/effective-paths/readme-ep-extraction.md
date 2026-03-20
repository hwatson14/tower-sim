# Effective Paths extraction bundle

Source workbook: `Copy of Effective Paths v5.00.01.xlsx`

This bundle adds two things:
1. Full-sheet CSV exports (values and formulas) for selected mechanics-heavy sheets.
2. Focused module main-effect extracts and formula notes.

## Exported sheets
- Data_Val_Tables -> historical export path `legacy_ep_extracts/sheet_exports/data_val_tables__values.csv` and `legacy_ep_extracts/sheet_exports/data_val_tables__formulas.csv` (A1:GP502)
- DVT_Bot -> historical export path `legacy_ep_extracts/sheet_exports/dvt_bot__values.csv` and `legacy_ep_extracts/sheet_exports/dvt_bot__formulas.csv` (A1:BE235)
- All UWs -> historical export path `legacy_ep_extracts/sheet_exports/all_uws__values.csv` and `legacy_ep_extracts/sheet_exports/all_uws__formulas.csv` (A1:CR66)
- All Bots -> historical export path `legacy_ep_extracts/sheet_exports/all_bots__values.csv` and `legacy_ep_extracts/sheet_exports/all_bots__formulas.csv` (A1:AN54)
- Module Base Stat -> historical export path `legacy_ep_extracts/sheet_exports/module_base_stat__values.csv` and `legacy_ep_extracts/sheet_exports/module_base_stat__formulas.csv` (A1:E32)
- WSValues -> historical export path `legacy_ep_extracts/sheet_exports/wsvalues__values.csv` and `legacy_ep_extracts/sheet_exports/wsvalues__formulas.csv` (A1:L6011)
- DVT_Laboratory -> historical export path `legacy_ep_extracts/sheet_exports/dvt_laboratory__values.csv` and `legacy_ep_extracts/sheet_exports/dvt_laboratory__formulas.csv` (A1:MY103)
- DVT_Workshop -> historical export path `legacy_ep_extracts/sheet_exports/dvt_workshop__values.csv` and `legacy_ep_extracts/sheet_exports/dvt_workshop__formulas.csv` (A1:AB6011)

## Focused module files
- historical export path `legacy_ep_extracts/module_main_effects/module_main_effect_base.csv`
- historical export path `legacy_ep_extracts/module_main_effects/module_main_effect_increment_bands.csv`
- historical export path `legacy_ep_extracts/module_main_effects/module_main_effect_level_additive_curve.csv`
- historical export path `legacy_ep_extracts/module_main_effects/module_main_effect_total_multiplier_by_rarity_level.csv`
- historical export path `legacy_ep_extracts/module_main_effects/module_main_effect_formula_notes.md`
- historical export path `legacy_ep_extracts/defined_names/module_defined_names.csv`

## Intended use
- Treat full-sheet exports as audit/reference surfaces.
- Treat focused module files as KB-ready inputs for canonical mechanics integration.


Note: The `legacy_ep_extracts/...` paths above are historical extraction targets from earlier package assembly and are not bundled as live paths in this frozen KB. Use the internalized canonical tables instead.
