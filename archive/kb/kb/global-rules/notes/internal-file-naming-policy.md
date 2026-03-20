# Internal File Naming Policy

Canonical KB file paths should be stable and unversioned.

Rules:
- Version the release package or zip, not canonical internal filenames.
- Allow schema/version fields inside file contents when they describe the data model.
- Imported raw source artifacts may preserve source-native naming only when provenance requires it, but the preferred KB surface remains the stable canonical copy.
- When a file is superseded, replace it in place or archive it outside the canonical KB surface. Do not accumulate v1/v2/v3 clones as parallel truths.
