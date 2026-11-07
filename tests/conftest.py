import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from api.config import METRO_BIN


@pytest.fixture(scope="session")
def fake_embeddings():
    """Deterministic hash-based vectors: identical text maps to an identical vector. No network needed."""
    return DeterministicFakeEmbedding(size=256)


needs_binary = pytest.mark.skipif(not METRO_BIN.exists(), reason="C++ router not built (run `make`)")
