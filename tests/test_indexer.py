from unittest.mock import MagicMock

from mnemolith.embeddings import MockSparseEmbedder
from mnemolith.indexer import index_vault, search


def test_index_vault_calls_upsert(vault_path, mock_embedder):
    """index_vault calls store.upsert_documents with all chunks."""
    store = MagicMock()
    chunks = index_vault(vault_path, mock_embedder, store, "test")
    store.upsert_documents.assert_called_once()
    call_args = store.upsert_documents.call_args
    assert len(call_args[0][1]) == len(chunks)  # documents arg


def test_index_vault_clean_deletes_collection(vault_path, mock_embedder):
    """index_vault with clean=True deletes the collection before recreating it."""
    store = MagicMock()
    index_vault(vault_path, mock_embedder, store, "test", clean=True)
    store.delete_collection.assert_called_once_with("test")
    store.ensure_collection.assert_called_once()
    store.upsert_documents.assert_called_once()


def test_index_vault_with_sparse_embedder(vault_path, mock_embedder):
    """index_vault passes sparse_vectors to upsert_documents when sparse_embedder provided."""
    store = MagicMock()
    sparse_embedder = MockSparseEmbedder()
    chunks = index_vault(vault_path, mock_embedder, store, "test", sparse_embedder=sparse_embedder)
    call_kwargs = store.upsert_documents.call_args[1]
    assert "sparse_vectors" in call_kwargs
    assert len(call_kwargs["sparse_vectors"]) == len(chunks)
    # ensure_collection called with sparse=True
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
