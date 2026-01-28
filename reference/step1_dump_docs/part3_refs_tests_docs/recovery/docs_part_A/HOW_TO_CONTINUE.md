# HOW_TO_CONTINUE (v19.0.0)

## Golden rules
1) Treat this bundle as immutable; make changes only via a new iterative zip.
2) Do not invent mechanics. Use Effective Paths first, then Wiki, then _IDS.
3) Fail closed on ambiguity.

## Next development tracks
A) Optimizer:
- loadout space from _IDS
- dominance pruning (provably safe)
- objective: 0.6*coins + 0.4*cells
- tournament EV scoring via scenario runner

B) Data completeness:
- verify BC magnitudes table is complete for all BCs used in leagues
- verify heat model matches EP/Wiki exactly (league + wave + tier if applicable)
- promote remaining tier scaling surfaces (HP/attack/etc) if present in packs

## Minimal command
- Install deps (including pyyaml if YAML remains)
- Run: pytest
