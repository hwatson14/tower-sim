PACK: formula_registry_combined
Effective Paths: Copy of Effective Paths v5.00.01.xlsx
Effective Paths sha256: b40302c6d2645dc2d3cf9d880117c6f5af15189afd8cbfe3c548c577167e70b1

Coverage:
  eHP: 5/5 targets extracted (Health, Regen, Wall Health, Wall Regen, Defense%)
  eDamage: 4/4 targets extracted (Tower Damage, Attack Speed, Crit Chance, Crit Multiplier) + UW block helpers

Codex handoff (purpose):
  - Treat this pack as the authoritative 'formula/mechanics registry' extracted from Effective Paths.
  - Implement named formulas (LAMBDA) as pure functions; implement sheet-cell formulas as composition graph nodes.
  - Fail-closed if any referenced name/cell/table is missing.
  - Pay attention to 'Known EP inconsistencies' below; do not guess fixes.

Known EP inconsistencies (do NOT silently fix):
  - Defined name EPD_BST references symbol 'vault' but does not declare it as a LAMBDA parameter (as stored in workbook).
    Recommendation: keep as-is, and either (a) model vault as a global input, or (b) patch only with explicit provenance in sim.

Validation status:
  - Numeric validation against EP: BLOCKED in this environment because EP workbook does not provide reliable cached results and openpyxl does not evaluate formulas.
  - Next step for validation: build Python evaluator for these functions, then compare to values computed by Excel/Sheets for fixed IDS snapshots.

Out of scope:
  - Boss/contact/survivability mechanics beyond EP outputs
