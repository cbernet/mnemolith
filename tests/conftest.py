import uuid
from pathlib import Path

import pytest

from second_brain.embeddings import MockEmbedder


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture
def vault_path() -> str:
    return str(FIXTURES_DIR)


@pytest.fixture
def mock_embedder() -> MockEmbedder:
    return MockEmbedder(dimension=384)


@pytest.fixture
def qdrant_collection():
    from second_brain.qdrant_store import get_client, delete_collection

    name = f"test_{uuid.uuid4().hex[:8]}"
    client = get_client()
    yield name, client
    try:
        delete_collection(client, name)
    except Exception:
        pass
