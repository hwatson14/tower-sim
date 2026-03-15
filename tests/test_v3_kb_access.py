from v3.kb_access import content_sha256, load_yaml, resolve_kb_location


def test_resolve_kb_location_available() -> None:
    loc = resolve_kb_location()
    assert loc.mode == "extracted"


def test_load_yaml_from_kb_naming_contract() -> None:
    doc = load_yaml("kb/global-rules/contracts/naming-contract.yaml")
    assert doc["kind"] == "naming_contract"


def test_content_sha256_length() -> None:
    digest = content_sha256("kb/global-rules/contracts/ids-section-routing.yaml")
    assert len(digest) == 64
