import logging
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


def test_index_and_search(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    docs = index_vault(vault_path, mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)
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


def test_index_empty_vault(tmp_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    docs = index_vault(str(tmp_path), mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)
    assert docs == []


def test_search_returns_ranked_results(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)

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


def test_search_score_threshold(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)

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


def test_hybrid_index_and_search(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    """Hybrid search with BM25 sparse + dense vectors using RRF fusion."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    docs = index_vault(
        vault_path, mock_embedder, qdrant_store, collection_name,
        sparse_embedder=sparse_embedder, state_pool=pg_pool,
    )
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


def test_hybrid_search_ignores_score_threshold(
    vault_path, mock_embedder, qdrant_store, collection_name, pg_pool,
):
    """RRF scores are ~0.016-0.05; a threshold of 0.3 must not filter all results."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    index_vault(
        vault_path, mock_embedder, qdrant_store, collection_name,
        sparse_embedder=sparse_embedder, state_pool=pg_pool,
    )

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


def test_hybrid_search_warns_on_score_threshold(
    vault_path, mock_embedder, qdrant_store, collection_name, caplog, pg_pool,
):
    """A warning must be emitted when score_threshold is passed for hybrid search."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    index_vault(
        vault_path, mock_embedder, qdrant_store, collection_name,
        sparse_embedder=sparse_embedder, state_pool=pg_pool,
    )

    with caplog.at_level(logging.WARNING, logger="mnemolith.qdrant_store"):
        search(
            "simple note",
            mock_embedder,
            qdrant_store,
            collection_name,
            limit=5,
            score_threshold=0.5,
            sparse_embedder=sparse_embedder,
        )
    assert any("score_threshold" in msg for msg in caplog.messages)


def test_dense_search_does_not_call_has_named_vectors(
    vault_path, mock_embedder, qdrant_store, collection_name, pg_pool,
):
    """After indexing with sparse, dense-only search must use cache, not API call."""
    from unittest.mock import patch

    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    index_vault(
        vault_path, mock_embedder, qdrant_store, collection_name,
        sparse_embedder=sparse_embedder, state_pool=pg_pool,
    )

    with patch.object(qdrant_store, "_has_named_vectors", wraps=qdrant_store._has_named_vectors) as mock_hnv:
        search("simple note", mock_embedder, qdrant_store, collection_name, limit=5)
        mock_hnv.assert_not_called()


def test_ensure_collection_raises_on_schema_mismatch(mock_embedder, qdrant_store, collection_name):
    """Switching SPARSE_SEARCH_ENABLED on an existing dense collection must raise."""
    qdrant_store.ensure_collection(collection_name, dimension=4, sparse=False)
    with pytest.raises(ValueError, match="--clean"):
        qdrant_store.ensure_collection(collection_name, dimension=4, sparse=True)


def test_ensure_collection_reuses_existing_sparse_collection(mock_embedder, qdrant_store, collection_name):
    """Re-running ensure_collection(sparse=True) on an existing sparse collection populates cache."""
    qdrant_store.ensure_collection(collection_name, dimension=4, sparse=True)
    # Simulate a fresh store instance that doesn't know about the collection yet
    fresh_store = QdrantStore()
    fresh_store.ensure_collection(collection_name, dimension=4, sparse=True)
    assert collection_name in fresh_store._named_vector_collections


def test_delete_by_paths(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    """delete_by_paths removes only chunks whose payload.path is in the given list."""
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)
    all_results = search("note", mock_embedder, qdrant_store, collection_name, limit=50)
    paths = sorted({r["path"] for r in all_results})
    assert len(paths) >= 2

    target = paths[0]
    qdrant_store.delete_by_paths(collection_name, [target])

    after = search("note", mock_embedder, qdrant_store, collection_name, limit=50)
    remaining = {r["path"] for r in after}
    assert target not in remaining
    assert all(p in remaining for p in paths[1:])


def test_delete_by_paths_empty_list_is_noop(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)
    before = search("note", mock_embedder, qdrant_store, collection_name, limit=50)
    qdrant_store.delete_by_paths(collection_name, [])
    after = search("note", mock_embedder, qdrant_store, collection_name, limit=50)
    assert {r["path"] for r in before} == {r["path"] for r in after}


def test_count_points(vault_path, mock_embedder, qdrant_store, collection_name, pg_pool):
    assert qdrant_store.count_points(collection_name) == 0  # collection doesn't exist
    index_vault(vault_path, mock_embedder, qdrant_store, collection_name, state_pool=pg_pool)
    assert qdrant_store.count_points(collection_name) >= 5


def test_dense_search_on_named_vector_collection(
    vault_path, mock_embedder, qdrant_store, collection_name, pg_pool,
):
    """Dense-only search still works on a collection indexed with named vectors."""
    from mnemolith.embeddings import MockSparseEmbedder
    sparse_embedder = MockSparseEmbedder()

    index_vault(
        vault_path, mock_embedder, qdrant_store, collection_name,
        sparse_embedder=sparse_embedder, state_pool=pg_pool,
    )

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
