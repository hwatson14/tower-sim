# FREEZE_CHECKLIST (v19.0.0)

This bundle is considered "frozen" iff all items below are true:

## Execution
- [ ] `pytest` passes (unit + scenario tests)
- [ ] No placeholder/example DAG remains in active runtime path
- [ ] `config/runtime_paths.py` points to canonical `data/*` files only

## Fail-closed invariants
- [ ] Tournament mode rejects any perk application
- [ ] Heat applied at most once per wave
- [ ] Unknown tier / BC / DAG node fails loudly

## Data surfaces present
- [ ] Tier wave damage table present
- [ ] Tournament wave damage table present
- [ ] Heat table present and monotonic per league
- [ ] BC magnitudes table present and non-empty
- [ ] DAG graph present and parseable JSON

## Provenance
- [ ] MANIFEST.json exists and includes sha256 for all files
- [ ] Any future edits MUST bump version and regenerate manifest

If any checkbox is false, this bundle is not authoritative.
