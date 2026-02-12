import pytest

from second_brain.indexer import index_vault, search


pytestmark = pytest.mark.integration


def test_index_and_search(vault_path, mock_embedder, qdrant_collection):
    collection_name, client = qdrant_collection

    docs = index_vault(vault_path, mock_embedder, client, collection_name)
    assert len(docs) >= 5

    results = search(
        "crêpes recette française",
        mock_embedder,
        client,
        collection_name,
        limit=3,
    )
    assert len(results) > 0
    assert all("score" in r for r in results)
    assert all("path" in r for r in results)


def test_index_empty_vault(tmp_path, mock_embedder, qdrant_collection):
    collection_name, client = qdrant_collection
    docs = index_vault(str(tmp_path), mock_embedder, client, collection_name)
    assert docs == []


def test_search_returns_ranked_results(vault_path, mock_embedder, qdrant_collection):
    collection_name, client = qdrant_collection
    index_vault(vault_path, mock_embedder, client, collection_name)

    results = search(
        "simple note with basic content",
        mock_embedder,
        client,
        collection_name,
        limit=5,
    )
    assert len(results) > 0
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
