# R79 Architecture Fix WP1-WP6 Merge Decision

Decision: merged as an adapted architecture/governance tranche.

Accepted capability:
- Externalized state-mode contracts into KB YAML.
- Externalized compiler routing policy into KB YAML.
- Externalized scenario runtime input schema/validation into KB YAML.
- Frozen datamodels for AccountState and StatInput.
- Replaced in-place mutation sites with dataclass-safe `replace(...)` usage.
- Added contract tests and boss-wave numeric regression coverage.
- Added verification metadata fields (`kb_alignment_status`, `verdict`) to compare/verification outputs.

Concerns flagged:
- This tranche is primarily architecture control/hardening, not a large new gameplay/runtime capability tranche.
- `tests/test_smoke.py` is broad and touches output contracts; future merges should not casually rewrite it.
- The reconstructed WP6 note is historical provenance only, not original artifact proof.

Rejected:
- pycache and pytest cache artifacts.

Verification run:
- targeted contract/regression tests passed
- canonical rebuild passed in max_progression
