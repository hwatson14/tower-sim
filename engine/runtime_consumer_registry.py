"""engine/runtime_consumer_registry.py - BACKWARD-COMPAT SHIM. Authority: qe.consumer_registry."""
from qe.consumer_registry import *  # noqa: F401, F403
from qe.consumer_registry import (  # noqa: F401
    RuntimeConsumerRule,
    ConsumerBundleDefinition,
    ResolvedConsumerBundle,
    load_surface_ownership_ledger,
    load_initial_surface_contract,
    load_consumer_bundle_contract,
    ownership_rows_by_node,
    declared_query_bundles,
    declared_family_surface_ids,
    assert_runtime_consumer_ownership_contract,
    assert_runtime_consumer_bundle_contract,
    load_consumer_bundle_definitions,
    resolve_consumer_bundle,
    list_runtime_consumer_rules,
    impacted_runtime_consumers,
)
