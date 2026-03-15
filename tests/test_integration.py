import pytest

from mnemolith.indexer import index_vault, search


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


def test_search_score_threshold(vault_path, mock_embedder, qdrant_collection):
    collection_name, client = qdrant_collection
    index_vault(vault_path, mock_embedder, client, collection_name)

    all_results = search(
        "simple note",
        mock_embedder,
        client,
        collection_name,
        limit=10,
    )
    assert len(all_results) > 0

    # High threshold should return fewer or no results
    high_threshold = max(r["score"] for r in all_results) + 0.01
    filtered = search(
        "simple note",
        mock_embedder,
        client,
        collection_name,
        limit=10,
        score_threshold=high_threshold,
    )
    assert len(filtered) < len(all_results)
