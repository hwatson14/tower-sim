# Cleanup ledger

## Moved
- docs/testing.md -> TESTING.md
- naming/catalog.yaml -> tables/registry/catalog.yaml
- tools/assemble_fullrepo_zip.py -> scripts/assemble_fullrepo_zip.py
- tools/wiki_ingest/extract_all_labs.py -> scripts/wiki_ingest/extract_all_labs.py
- tower_sim/tables/* -> tables/*
- tower_sim/wiki/cache/*.csv -> tables/wiki_cache/*
- tower_sim/wiki/*.py -> tower_sim/loaders/wiki/*.py
- tower_sim/audit/*.(md|json|yaml) -> audit/
- tower_sim/combat/* -> tower_sim/engines/combat/*
- tower_sim/enemies/wave_damage_strict.py -> tower_sim/libs/wave_damage_strict.py
- tower_sim/run_api.py -> tower_sim/run/api.py
- tower_sim/run_context.py -> tower_sim/run/context.py
- tower_sim/problem_spec.py -> tower_sim/run/problem_spec.py
- tower_sim/spec_loader.py -> tower_sim/run/spec_loader.py
- tower_sim/stat_registry.py -> tower_sim/registry/stat_registry.py
- tower_sim/ids_state.py -> tower_sim/util/ids_state.py
- tower_sim/ids_parser.py -> tower_sim/loaders/ids_parser.py
- tower_sim/ids.py -> tower_sim/loaders/ids.py
- tower_sim/sources.py -> tower_sim/loaders/sources.py
- tower_sim/bc_heat_loader.py -> tower_sim/loaders/bc_heat_loader.py
- tower_sim/tier_bc_loader.py -> tower_sim/loaders/tier_bc_loader.py
- tower_sim/tier_battle_conditions.py -> tower_sim/loaders/tier_battle_conditions.py
- tower_sim/tournament_bc_selection.py -> tower_sim/loaders/tournament_bc_selection.py
- tower_sim/battle_conditions.py -> tower_sim/engines/battle_conditions.py
- tower_sim/perk_engine.py -> tower_sim/engines/perk_engine.py
- tower_sim/perks_gate.py -> tower_sim/engines/perks_gate.py
- tower_sim/stat_engine.py -> tower_sim/engines/stat_engine.py
- tower_sim/stat_snapshots.py -> tower_sim/engines/stat_snapshots.py
- tower_sim/statbook_builder.py -> tower_sim/engines/statbook_builder.py
- tower_sim/free_upgrades.py -> tower_sim/engines/free_upgrades.py
- tower_sim/tier_rules.py -> tower_sim/engines/tier_rules.py
- tower_sim/tier_rule_apply.py -> tower_sim/engines/tier_rule_apply.py
- tower_sim/wave_engine.py -> tower_sim/engines/wave_engine.py
- tower_sim/wave_time.py -> tower_sim/engines/wave_time.py
- tower_sim/uptime.py -> tower_sim/engines/uptime.py
- tower_sim/workshop_progression.py -> tower_sim/engines/workshop_progression.py
- tower_sim/modules.py -> tower_sim/engines/modules.py
- tower_sim/assist_efficiency.py -> tower_sim/libs/assist_efficiency.py
- tower_sim/enemy_tables.py -> tower_sim/libs/enemy_tables.py
- tower_sim/modules_library.py -> tower_sim/libs/modules_library.py
- tower_sim/uw_tables.py -> tower_sim/libs/uw_tables.py
- tower_sim/statbook.py -> tower_sim/util/statbook.py
- tower_sim/engines/combat/combat_params.schema.json -> tables/schemas/combat_params.schema.json
- tests/test_max_wave_evaluator.py -> tests_quarantine/test_max_wave_evaluator.py
- tests/test_run_api.py -> tests_quarantine/test_run_api.py

## Deleted
- data/ (legacy cache directory; empty after moves)
- docs/ (migrated to root docs)
- naming/ (migrated to tables/registry)
- tools/ (migrated to scripts/)
- tower_sim/wiki/ (migrated to tower_sim/loaders/wiki)
- tower_sim/tables/ (migrated to tables/)

## Kept (relocated)
- reference/legacy/boss/boss_bc.schema.json (schema/template not referenced by code; kept for provenance)
- reference/legacy/boss/boss_bc.template.json (schema/template not referenced by code; kept for provenance)
