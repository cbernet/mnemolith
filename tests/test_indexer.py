from unittest.mock import MagicMock

from mnemolith.indexer import index_vault


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
