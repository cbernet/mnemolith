import os
from unittest.mock import patch

import pytest

from mnemolith.vector_store import (
    CollectionNotFoundError,
    get_vector_store,
    reset_vector_store,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_vector_store()
    yield
    reset_vector_store()


def test_collection_not_found_error():
    err = CollectionNotFoundError("my_collection")
    assert err.collection == "my_collection"
    assert "my_collection" in str(err)


@patch.dict(os.environ, {"VECTOR_BACKEND": "qdrant", "QDRANT_URL": "http://localhost:6333"})
def test_get_vector_store_qdrant():
    store = get_vector_store()
    from mnemolith.qdrant_store import QdrantStore
    assert isinstance(store, QdrantStore)


@patch.dict(os.environ, {"VECTOR_BACKEND": "qdrant", "QDRANT_URL": "http://localhost:6333"})
def test_get_vector_store_is_singleton():
    store1 = get_vector_store()
    store2 = get_vector_store()
    assert store1 is store2


@patch.dict(os.environ, {"VECTOR_BACKEND": "pgvector", "POSTGRES_DSN": "postgresql://user:pass@localhost/db"})
@patch("mnemolith.pgvector_store.ConnectionPool")
def test_get_vector_store_pgvector(mock_pool):
    store = get_vector_store()
    from mnemolith.pgvector_store import PgvectorStore
    assert isinstance(store, PgvectorStore)


@patch.dict(os.environ, {"VECTOR_BACKEND": "nonsense"})
def test_get_vector_store_unknown_backend():
    with pytest.raises(ValueError, match="Unknown vector backend"):
        get_vector_store()


@patch.dict(os.environ, {"VECTOR_BACKEND": "qdrant", "QDRANT_URL": "http://localhost:6333"})
def test_reset_clears_singleton():
    store1 = get_vector_store()
    reset_vector_store()
    store2 = get_vector_store()
    assert store1 is not store2
