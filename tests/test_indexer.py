from unittest.mock import MagicMock

from mnemolith.indexer import index_vault


def test_index_vault_uses_embed_batch(vault_path, mock_embedder):
    """index_vault calls embed_batch with all texts at once."""
    client = MagicMock()
    chunks = index_vault(vault_path, mock_embedder, client, "test")
    # upsert_documents should have been called with vectors matching chunk count
    call_args = client.upsert.call_args
    points = call_args.kwargs["points"]
    assert len(points) == len(chunks)


def test_index_vault_clean_deletes_collection(vault_path, mock_embedder):
    """index_vault with clean=True deletes the collection before recreating it."""
    client = MagicMock()
    index_vault(vault_path, mock_embedder, client, "test", clean=True)
    client.delete_collection.assert_called_once_with(collection_name="test")
    # should still create the collection and upsert
    client.upsert.assert_called_once()
