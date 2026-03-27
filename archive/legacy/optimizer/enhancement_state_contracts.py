# optimizer/enhancement_state_contracts.py -- BACKWARD-COMPAT SHIM (T10)
# Authority transferred to evaluators/objectives.py
# Legacy tests that monkeypatch module-level path vars must target evaluators.objectives
from evaluators.objectives import (
    ObservedRunElsScenario,
    load_enhancement_state_prep_contract,
    load_observed_run_els_contract,
    load_observed_run_els_scenarios,
    _OBSERVED_RUN_ELS_INPUT_PATH,
    _WORKSHOP_PREP_CONTRACT_PATH,
    _OBSERVED_RUN_ELS_CONTRACT_PATH,
    _REQUIRED_PREP_CONTRACT_KEYS,
    _REQUIRED_QUERY_BUNDLE_KEYS,
    _REQUIRED_QUERY_BUNDLE_REQUIREMENT_KEYS,
    _REQUIRED_SCENARIO_CONTRACT_KEYS,
    _REQUIRED_SURFACE_KEYS,
    _REQUIRED_TRUST_PAYLOAD_KEYS,
    _REQUIRED_PROVENANCE_PAYLOAD_KEYS,
    _REQUIRED_OUTPUT_LABEL_KEYS,
    _REQUIRED_OBSERVED_RUN_CONTRACT_KEYS,
    _ALLOWED_LABEL_STRENGTHS,
    _ALLOWED_TRUST_LEVELS,
    _ALLOWED_RUNTIME_STATUS,
)
