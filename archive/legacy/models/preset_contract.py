"""models/preset_contract.py - BACKWARD-COMPAT SHIM. Authority: qe.contracts."""
from qe.contracts import (  # noqa: F401
    CANONICAL_PRESET_NAMES,
    PRESET_ALIASES,
    is_canonical_preset_name,
    is_transient_preset_namespace,
    load_preset_contract,
    load_section_layout_contract,
    normalize_preset_name,
    require_canonical_preset_name,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)
