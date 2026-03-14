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
