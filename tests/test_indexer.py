from unittest.mock import patch, MagicMock

from second_brain.indexer import index_vault


def test_index_vault_shows_progress(vault_path, mock_embedder):
    """index_vault wraps embedding in a tqdm progress bar."""
    client = MagicMock()
    with patch("second_brain.indexer.tqdm", side_effect=lambda it, **kw: it) as mock_tqdm:
        index_vault(vault_path, mock_embedder, client, "test")
        mock_tqdm.assert_called_once()
