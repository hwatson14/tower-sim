# Codex TODO (V2 runtime-ready)

1) Implement IdentifierResolver per runtime/IDENTIFIER_RESOLVER_CONTRACT.json
2) Add closure test for eHP rooted ledger:
   - Load STAT_LEDGER_eHP_ROOTED.csv
   - Apply resolver map from IDENTIFIER_REGISTRY.csv (once filled)
   - Assert zero UNRESOLVED tokens remain, else fail-closed with report
3) Add parity harness stub (no mechanics guessing):
   - Evaluate EP roots (eHP!AH16..AH23) by executing the closed ledger graph once sources exist
   - Compare against EP computed values for one golden IDS snapshot (future)
