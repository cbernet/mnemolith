import logging
from dataclasses import dataclass
from pathlib import Path

from psycopg_pool import ConnectionPool

from mnemolith import index_state, pg_store
from mnemolith.embeddings import Embedder, SparseEmbedder
from mnemolith.parser import Document, build_embedding_text, chunk_document, parse_vault
from mnemolith.vector_store import VectorStore

logger = logging.getLogger(__name__)


class LegacyCollectionError(Exception):
    """Incremental run found a vector collection with no tracked state.

    The collection was likely indexed by a pre-incremental version of mnemolith.
    Run `mnemolith index --full` once to migrate.
    """


class IndexLockedError(Exception):
    """Another index run holds the collection lock. This one did nothing."""


@dataclass
class IndexResult:
    added: list[str]
    modified: list[str]
    deleted: list[str]
    chunks: list[Document]

    @property
    def changed(self) -> bool:
        return bool(self.added or self.modified or self.deleted)

    def summary(self) -> str:
        if not self.changed:
            return "Index is up to date."
        return (
            f"+{len(self.added)} ~{len(self.modified)} -{len(self.deleted)} files, "
            f"{len(self.chunks)} chunks embedded"
        )


def index_vault(
    vault_path: str,
    embedder: Embedder,
    store: VectorStore,
    collection: str,
    full: bool = False,
    clean: bool = False,
    sparse_embedder: SparseEmbedder | None = None,
    state_pool: ConnectionPool | None = None,
) -> IndexResult:
    if clean:
        full = True
    if state_pool is None:
        state_pool = pg_store.get_pool()

    with pg_store.advisory_lock(state_pool, f"index:{collection}") as acquired:
        if not acquired:
            raise IndexLockedError(
                f"Another index run is in progress for collection '{collection}'."
            )
        return _index_vault_locked(
            vault_path, embedder, store, collection, full, sparse_embedder, state_pool
        )


def _index_vault_locked(
    vault_path: str,
    embedder: Embedder,
    store: VectorStore,
    collection: str,
    full: bool,
    sparse_embedder: SparseEmbedder | None,
    state_pool: ConnectionPool,
) -> IndexResult:
    documents = parse_vault(vault_path)
    root = Path(vault_path)
    new_hashes = {
        doc.path: index_state.file_hash((root / doc.path).read_bytes())
        for doc in documents
    }

    if full:
        store.delete_collection(collection)
        index_state.reset_state(state_pool, collection)
        added = sorted(new_hashes)
        modified: list[str] = []
        deleted: list[str] = []
        files_to_embed = set(new_hashes)
        files_to_delete: list[str] = []
        existing_chunks: dict[str, int] = {}
    else:
        existing = index_state.load_state(state_pool, collection)
        if not existing and store.count_points(collection) > 0:
            raise LegacyCollectionError(
                f"Collection '{collection}' has untracked points. "
                "Run `mnemolith index --full` once to migrate."
            )
        existing_hashes = {p: h for p, (h, _) in existing.items()}
        existing_chunks = {p: n for p, (_, n) in existing.items()}
        added = [p for p in new_hashes if p not in existing_hashes]
        modified = [
            p for p in new_hashes
            if p in existing_hashes and existing_hashes[p] != new_hashes[p]
        ]
        deleted = [p for p in existing_hashes if p not in new_hashes]
        files_to_embed = set(added + modified)
        files_to_delete = modified + deleted

    store.ensure_collection(collection, embedder.dimension, sparse=sparse_embedder is not None)

    if files_to_delete:
        store.delete_by_paths(collection, files_to_delete)

    chunks_to_embed: list[Document] = []
    new_chunk_counts: dict[str, int] = {}
    for doc in documents:
        if doc.path in files_to_embed:
            doc_chunks = chunk_document(doc, count=embedder.count_tokens)
            chunks_to_embed.extend(doc_chunks)
            new_chunk_counts[doc.path] = len(doc_chunks)

    if chunks_to_embed:
        texts = [build_embedding_text(c) for c in chunks_to_embed]
        logger.info("Embedding %d chunks...", len(texts))
        vectors = embedder.embed_batch(texts)
        sparse_vectors = sparse_embedder.embed_batch(texts) if sparse_embedder else None
        store.upsert_documents(collection, chunks_to_embed, vectors, sparse_vectors=sparse_vectors)

    merged_chunks = {
        path: new_chunk_counts.get(path, existing_chunks.get(path, 0))
        for path in new_hashes
    }
    index_state.save_state(state_pool, collection, new_hashes, merged_chunks)

    return IndexResult(added, modified, deleted, chunks_to_embed)


def search(
    query: str,
    embedder: Embedder,
    store: VectorStore,
    collection: str,
    limit: int = 5,
    score_threshold: float | None = None,
    sparse_embedder: SparseEmbedder | None = None,
) -> list[dict]:
    query_vector = embedder.embed(query)
    sparse_query = sparse_embedder.embed(query) if sparse_embedder else None
    return store.search(
        collection,
        query_vector,
        limit=limit,
        score_threshold=score_threshold,
        sparse_query=sparse_query,
    )
