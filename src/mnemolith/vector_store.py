import os
from typing import Protocol

from mnemolith.embeddings import SparseVector
from mnemolith.parser import Document


class CollectionNotFoundError(Exception):
    """Raised when a search targets a collection that doesn't exist."""

    def __init__(self, collection: str):
        self.collection = collection
        super().__init__(f"Collection '{collection}' not found. Run 'mnemolith index' first.")


class VectorStore(Protocol):
    def ensure_collection(self, name: str, dimension: int, sparse: bool = False) -> None: ...
    # Idempotent: must succeed silently if the collection does not exist.
    def delete_collection(self, name: str) -> None: ...
    def delete_by_paths(self, collection: str, paths: list[str]) -> None: ...
    def count_points(self, collection: str) -> int: ...
    def upsert_documents(
        self,
        collection: str,
        documents: list[Document],
        vectors: list[list[float]],
        sparse_vectors: list[SparseVector] | None = None,
    ) -> None: ...
    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
        sparse_query: SparseVector | None = None,
    ) -> list[dict]: ...


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        backend = os.environ.get("VECTOR_BACKEND", "qdrant")
        if backend == "qdrant":
            from mnemolith.qdrant_store import QdrantStore
            _store = QdrantStore()
        elif backend == "pgvector":
            from mnemolith.pgvector_store import PgvectorStore
            _store = PgvectorStore()
        else:
            raise ValueError(f"Unknown vector backend: {backend}")
    return _store


def reset_vector_store() -> None:
    """Reset the singleton (for testing)."""
    global _store
    _store = None
