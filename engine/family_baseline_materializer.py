"""engine/family_baseline_materializer.py - BACKWARD-COMPAT SHIM. Authority: qe.materializer."""
from qe.materializer import (  # noqa: F401
    BaselineContributorRow,
    FamilyBaselineContributorMap,
    FamilyBaselineMaterializer,
    contributor_row_sort_key,
    load_family_contracts,
    load_family_surface_ids,
    load_surface_metadata_by_id,
    load_surface_ownership_ledger,
    load_surface_registry_contract,
    _inject_free_upgrade_cross_surface_multipliers,
    _scale_enemy_skip_thorns_relic_values,
    _scale_free_upgrade_relic_values,
    _scale_survivability_relic_vault_values,
    _scale_wall_fortification_lab_value,
)
