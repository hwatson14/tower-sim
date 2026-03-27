"""engine/state_identity.py - BACKWARD-COMPAT SHIM. Authority: qe.models."""
from qe.models import (  # noqa: F401
    BoundStatInputs,
    StateIdentity,
    StateIdentityBinding,
    bind_state_identity,
    compile_stat_inputs_with_identity,
)
