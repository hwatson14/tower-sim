# v1.4.0 Timing Framework

Adds a generic timing layer so that UW/Bot/Guardian effects can be represented with:
- cooldown/duration
- always-on
- proc EV uptime

This addresses the "timing" dimension without hardcoding game numbers.

Outputs:
- timing primitives
- mapping primitive -> cc_source
- extraction scaffold from loadout + mechanics registry
