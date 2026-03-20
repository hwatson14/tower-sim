# Future Defect Batch Protocol

Use this protocol for any future work. Do not reopen broad development without a defect ledger.

## Required sequence
1. Fresh unpack of the latest frozen zip
2. Reproduce the issue on that unpack
3. Write a narrow defect ledger:
   - defect title
   - affected surfaces
   - evidence
   - expected behavior
   - proposed fix scope
4. Patch narrowly
5. Run `pytest -q`
6. Rebuild canonical outputs:
   - `python run_stats.py --state-mode max_progression --out out`
7. Refresh audit artifacts if behavior/output changes
8. Version a new zip

## Rules
- Do not hand-edit outputs
- Do not reintroduce multiple competing `out*` directories at root
- Do not claim closure from a code diff alone; closure requires fresh outputs and tests
- Do not broaden scope mid-batch unless the defect ledger is explicitly updated

## Recommended defect-ledger headings
- Problem
- Affected surfaces
- Evidence
- Hypothesis
- Fix
- Verification
- Residual risks
