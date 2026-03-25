import pytest

from mnemolith.parser import Document
from mnemolith.pgvector_store import PgvectorStore
from mnemolith.vector_store import CollectionNotFoundError

pytestmark = pytest.mark.pgvector_integration


@pytest.fixture
def pgvector_store(pg_pool):
    """PgvectorStore backed by a temporary test database."""
    store = PgvectorStore(pool=pg_pool)
    # Enable pgvector extension
    with pg_pool.connection() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    return store


@pytest.fixture
def collection_name():
    return "test_docs"


@pytest.fixture
def sample_docs():
    return [
        Document(
            path="notes/python.md",
            title="Python",
            content="Python is a programming language.",
            tags=["python", "programming"],
            links=["java"],
            heading="Intro",
        ),
        Document(
            path="notes/rust.md",
            title="Rust",
            content="Rust is a systems language.",
            tags=["rust"],
            links=[],
            heading="Overview",
        ),
    ]


def test_ensure_and_delete_collection(pgvector_store, collection_name):
    pgvector_store.ensure_collection(collection_name, 3)
    # Calling again should not raise
    pgvector_store.ensure_collection(collection_name, 3)
    pgvector_store.delete_collection(collection_name)


def test_upsert_and_search(pgvector_store, collection_name, sample_docs):
    dim = 3
    pgvector_store.ensure_collection(collection_name, dim)

    vectors = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    pgvector_store.upsert_documents(collection_name, sample_docs, vectors)

    # Search with a vector close to the first doc
    results = pgvector_store.search(collection_name, [0.9, 0.1, 0.0], limit=2)
    assert len(results) == 2
    assert results[0]["path"] == "notes/python.md"
    assert results[0]["score"] > results[1]["score"]
    assert "content" in results[0]
    assert "tags" in results[0]


def test_search_score_threshold(pgvector_store, collection_name, sample_docs):
    dim = 3
    pgvector_store.ensure_collection(collection_name, dim)
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    pgvector_store.upsert_documents(collection_name, sample_docs, vectors)

    # Very high threshold — should return fewer results
    results = pgvector_store.search(
        collection_name, [1.0, 0.0, 0.0], limit=10, score_threshold=0.99
    )
    assert len(results) <= 1


def test_search_nonexistent_collection(pgvector_store):
    with pytest.raises(CollectionNotFoundError):
        pgvector_store.search("nonexistent", [1.0, 0.0, 0.0])


def test_upsert_sparse_vectors_not_supported(pgvector_store, collection_name, sample_docs):
    from mnemolith.embeddings import SparseVector
    pgvector_store.ensure_collection(collection_name, 3)
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    sparse = [SparseVector(indices=[0], values=[1.0]), SparseVector(indices=[1], values=[1.0])]
    with pytest.raises(NotImplementedError):
        pgvector_store.upsert_documents(collection_name, sample_docs, vectors, sparse_vectors=sparse)


def test_search_sparse_query_not_supported(pgvector_store, collection_name, sample_docs):
    from mnemolith.embeddings import SparseVector
    pgvector_store.ensure_collection(collection_name, 3)
    pgvector_store.upsert_documents(collection_name, sample_docs, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    with pytest.raises(NotImplementedError):
        pgvector_store.search(collection_name, [1.0, 0.0, 0.0], sparse_query=SparseVector(indices=[0], values=[1.0]))


def test_upsert_replaces_on_reindex(pgvector_store, collection_name, sample_docs):
    dim = 3
    pgvector_store.ensure_collection(collection_name, dim)
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    pgvector_store.upsert_documents(collection_name, sample_docs, vectors)
    # Re-upsert — should replace, not duplicate
    pgvector_store.upsert_documents(collection_name, sample_docs, vectors)
    results = pgvector_store.search(collection_name, [1.0, 0.0, 0.0], limit=10)
    assert len(results) == 2
