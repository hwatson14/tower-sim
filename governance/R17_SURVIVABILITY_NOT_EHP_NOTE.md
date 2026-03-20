# R17 survivability framing correction

Survivability is not equivalent to eHP.

For optimiser-facing payload design in this workstream, survivability should be treated as a broader outcome domain that can include:

- core state buffers such as tower HP and wall-related support
- regeneration and recovery support
- mitigation layers such as damage reduction
- boss-control support that changes whether lethal contact occurs in the first place

Accordingly, the R17 survivability payload slice includes both `optimizer_domain=survivability` rows and selected `optimizer_domain=boss_control` rows.

This does not collapse boss control into survivability as a concept. It means boss-control support is relevant input to a survivability-oriented optimiser objective.
