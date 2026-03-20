# Initial Cleanup Note Before Merge Intake

This cleanup pass is intentionally conservative.

## Objectives
- make the package self-describing
- eliminate misleading/missing control-plane references
- reduce AI merge ambiguity
- preserve runtime behavior

## Changes applied
- added missing entry/control-plane files referenced by manifest/readme
- corrected package description from KB-only framing to KB + calculator baseline framing
- documented canonical rebuild path and canonical shipped output bundle
- documented frozen truths and explicit non-goals in `freeze-status.md`

## Changes intentionally not applied
- no code refactors
- no formula edits
- no directory moves
- no deletion of historical governance artifacts

## Reason
The highest current risk is merge confusion, not code execution.
