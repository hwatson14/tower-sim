# Combat System

## Scope
Combat owns cross-domain runtime interactions that do not belong to a single entity family.

## Included surfaces
- damage pipeline
- effect catalog
- exception matrix
- interaction matrix
- global combat assumptions

## Boundary rule
Entity-local mechanics belong in their owning domain. Combat only owns cross-domain interactions, ordering, and exception behavior.
