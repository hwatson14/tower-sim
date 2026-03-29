# Updated test_core_smoke.py with publish_query_surfaces

import pytest
from your_module import compare

@pytest.fixture
def monkeypatch():
    # Existing mock context
    pass

# Other existing tests...

def test_something(monkeypatch):
    # Line 91 change
    monkeypatch.setattr(compare, "publish_query_surfaces", lambda *args, **kwargs: None)
    # Additional test logic...

# Additional tests...

# Line 148 change
    monkeypatch.setattr(compare, "publish_query_surfaces", lambda *args, **kwargs: None)