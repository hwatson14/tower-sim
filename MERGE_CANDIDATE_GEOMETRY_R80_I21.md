# Merge Candidate: Geometry selective rebase on r80 (Iteration 21)

## Summary
This merge candidate completes the selective rebase scope for the wall-contact measurement-fit path on the latest r80 repo.

## Included
- canonical target surface
- measurement protocol
- fit ingestion scaffold
- first fit harness
- fit review
- holdout execution
- candidate acceptance workflow
- integrated fit decision report
- minimal harmonized fit pipeline
- targeted tests
- final review note

## Validation
Run with repo root on `PYTHONPATH`:

```bash
PYTHONPATH=. pytest -q \
  tests/test_geometry_wall_contact_target_surface.py \
  tests/test_geometry_wall_contact_fit_ingestion.py \
  tests/test_geometry_wall_contact_fit_harness.py \
  tests/test_geometry_wall_contact_fit_review.py \
  tests/test_geometry_wall_contact_holdout.py \
  tests/test_geometry_wall_contact_fit_decision.py \
  tests/test_geometry_wall_contact_fit_pipeline.py
```

Expected: `7 passed`

## Scope boundary
This merge candidate completes the selective rebase scope only. It does not claim full runtime geometry-chain integration or contact-truth promotion.
