from unittest.mock import MagicMock

import pytest

from mnemolith.embeddings import MockSparseEmbedder
from mnemolith.indexer import index_vault, search


@pytest.fixture
def store():
    s = MagicMock()
    s.count_points.return_value = 0
    return s


@pytest.mark.pg_integration
def test_index_vault_calls_upsert(vault_path, mock_embedder, store, pg_pool):
    """index_vault calls store.upsert_documents with all chunks on first run."""
    chunks = index_vault(vault_path, mock_embedder, store, "test", state_pool=pg_pool)
    store.upsert_documents.assert_called_once()
    call_args = store.upsert_documents.call_args
    assert len(call_args[0][1]) == len(chunks)


@pytest.mark.pg_integration
def test_index_vault_clean_deletes_collection(vault_path, mock_embedder, store, pg_pool):
    """clean=True deletes the collection before recreating it."""
    index_vault(vault_path, mock_embedder, store, "test", clean=True, state_pool=pg_pool)
    store.delete_collection.assert_called_once_with("test")
    store.ensure_collection.assert_called_once()
    store.upsert_documents.assert_called_once()


@pytest.mark.pg_integration
def test_index_vault_with_sparse_embedder(vault_path, mock_embedder, store, pg_pool):
    """index_vault passes sparse_vectors to upsert_documents when sparse_embedder provided."""
    sparse_embedder = MockSparseEmbedder()
    chunks = index_vault(
        vault_path, mock_embedder, store, "test",
        sparse_embedder=sparse_embedder, state_pool=pg_pool,
    )
    call_kwargs = store.upsert_documents.call_args[1]
    assert "sparse_vectors" in call_kwargs
    assert len(call_kwargs["sparse_vectors"]) == len(chunks)
    store.ensure_collection.assert_called_once_with("test", mock_embedder.dimension, sparse=True)


def test_search_with_sparse_embedder(mock_embedder):
    """search passes sparse_query to store.search when sparse_embedder provided."""
    store = MagicMock()
    store.search.return_value = []
    sparse_embedder = MockSparseEmbedder()
    search("query", mock_embedder, store, "test", sparse_embedder=sparse_embedder)
    call_kwargs = store.search.call_args[1]
    assert "sparse_query" in call_kwargs
    assert call_kwargs["sparse_query"] is not None
