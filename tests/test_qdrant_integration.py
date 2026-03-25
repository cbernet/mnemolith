import uuid

import pytest

from mnemolith.indexer import index_vault, search
from mnemolith.qdrant_store import QdrantStore

pytestmark = pytest.mark.integration


@pytest.fixture
def qdrant_store():
    from qdrant_client.http.exceptions import ResponseHandlingException

    try:
        store = QdrantStore()
        store.client.get_collections()  # verify connection
    except (ResponseHandlingException, OSError):
        pytest.skip("Qdrant not reachable — run: docker compose up -d")
    return store


@pytest.fixture
def collection_name(qdrant_store):
    name = f"test_{uuid.uuid4().hex[:8]}"
    yield name
    try:
        qdrant_store.delete_collection(name)
    except Exception:
        pass


def test_index_and_search(vault_path, mock_embedder, qdrant_store, collection_name):
    docs = index_vault(vault_path, mock_embedder, qdrant_store, collection_name)
    assert len(docs) >= 5

    results = search(
        "crêpes recette française",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=3,
    )
    assert len(results) > 0
    assert all("score" in r for r in results)
    assert all("path" in r for r in results)


def test_index_empty_vault(tmp_path, mock_embedder, qdrant_store, collection_name):
    docs = index_vault(str(tmp_path), mock_embedder, qdrant_store, collection_name)
    assert docs == []


def test_search_returns_ranked_results(vault_path, mock_embedder, qdrant_store, collection_name):
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name)

    results = search(
        "simple note with basic content",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=5,
    )
    assert len(results) > 0
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_score_threshold(vault_path, mock_embedder, qdrant_store, collection_name):
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name)

    all_results = search(
        "simple note",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=10,
    )
    assert len(all_results) > 0

    high_threshold = max(r["score"] for r in all_results) + 0.01
    filtered = search(
        "simple note",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=10,
        score_threshold=high_threshold,
    )
    assert len(filtered) < len(all_results)


def test_hybrid_index_and_search(vault_path, mock_embedder, qdrant_store, collection_name):
    """Hybrid search with BM25 sparse + dense vectors using RRF fusion."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    docs = index_vault(vault_path, mock_embedder, qdrant_store, collection_name, sparse_embedder=sparse_embedder)
    assert len(docs) >= 5

    results = search(
        "simple note",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=5,
        sparse_embedder=sparse_embedder,
    )
    assert len(results) > 0
    assert all("score" in r for r in results)
    assert all("path" in r for r in results)


def test_hybrid_search_ignores_score_threshold(vault_path, mock_embedder, qdrant_store, collection_name):
    """RRF scores are ~0.016-0.05; a threshold of 0.3 must not filter all results."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, sparse_embedder=sparse_embedder)

    all_results = search(
        "simple note",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=5,
        sparse_embedder=sparse_embedder,
    )
    assert len(all_results) > 0
    max_rrf_score = max(r["score"] for r in all_results)

    # Passing a threshold above the max RRF score must not filter all results —
    # score_threshold is meaningless for rank-based RRF scores and must be ignored.
    results = search(
        "simple note",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=5,
        score_threshold=max_rrf_score + 0.1,
        sparse_embedder=sparse_embedder,
    )
    assert len(results) == len(all_results)


def test_dense_search_on_named_vector_collection(vault_path, mock_embedder, qdrant_store, collection_name):
    """Dense-only search still works on a collection indexed with named vectors."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, sparse_embedder=sparse_embedder)

    # Search without sparse_embedder — should fall back to dense with using="dense"
    results = search(
        "simple note",
        mock_embedder,
        qdrant_store,
        collection_name,
        limit=5,
    )
    assert len(results) > 0
    assert all("score" in r for r in results)
