# Naming contract reconstruction

## Reconstructed files
- docs/naming_migration_report.md
- docs/phase_1b_naming_alignment_report.md
- kb/global-rules/contracts/naming-contract.yaml
- kb/ledgers/notes/towersim_static_ledger_naming_contract_v1_10.md
- pyproject.toml
- registry/__init__.py
- registry/naming_contract.py
- scripts/naming_contract_check.py
- tests/test_naming_contract.py
- tests/test_naming_contract_check.py

## Verification run
Executed locally against the uploaded repo snapshot:
- `python -m pytest -q tests/test_naming_contract.py tests/test_naming_contract_check.py`
- Result: `8 passed`

## Important note
This is a reconstructed recovery branch candidate, not proof that Claude's original implementation was perfect. It is the best faithful reconstruction from:
- the uploaded repo snapshot
- the reference archive inside `tower-sim-src.zip`
- the recovered full `registry/naming_contract.py`
- the previously recovered Claude patch summary

## GitHub status
A recovery branch was created through the connector:
- `recovery/claude-naming-contract-reconstruction`

The connector write path then blocked full PR assembly because the available tool surface did not expose the base tree SHA needed to create a multi-file commit updating existing files.
