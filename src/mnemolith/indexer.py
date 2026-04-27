from pathlib import Path

from psycopg_pool import ConnectionPool

from mnemolith import index_state
from mnemolith.embeddings import Embedder, SparseEmbedder
from mnemolith.parser import Document, build_embedding_text, chunk_document, parse_vault
from mnemolith.vector_store import VectorStore


class LegacyCollectionError(Exception):
    """Incremental run found a vector collection with no tracked state.

    The collection was likely indexed by a pre-incremental version of mnemolith.
    Run `mnemolith index --full` once to migrate.
    """


def index_vault(
    vault_path: str,
    embedder: Embedder,
    store: VectorStore,
    collection: str,
    full: bool = False,
    clean: bool = False,
    sparse_embedder: SparseEmbedder | None = None,
    state_pool: ConnectionPool | None = None,
) -> list[Document]:
    if clean:
        full = True
    if state_pool is None:
        from mnemolith.pg_store import get_pool
        state_pool = get_pool()

    documents = parse_vault(vault_path)
    root = Path(vault_path)
    new_hashes = {
        doc.path: index_state.file_hash((root / doc.path).read_bytes())
        for doc in documents
    }

    if full:
        try:
            store.delete_collection(collection)
        except Exception:
            pass  # collection may not exist
        index_state.reset_state(state_pool, collection)
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
        print(f"+{len(added)} ~{len(modified)} -{len(deleted)} files")

    store.ensure_collection(collection, embedder.dimension, sparse=sparse_embedder is not None)

    if files_to_delete:
        store.delete_by_paths(collection, files_to_delete)

    chunks_to_embed: list[Document] = []
    new_chunk_counts: dict[str, int] = {}
    for doc in documents:
        if doc.path in files_to_embed:
            doc_chunks = chunk_document(doc)
            chunks_to_embed.extend(doc_chunks)
            new_chunk_counts[doc.path] = len(doc_chunks)

    if chunks_to_embed:
        texts = [build_embedding_text(c) for c in chunks_to_embed]
        print(f"Embedding {len(texts)} chunks...")
        vectors = embedder.embed_batch(texts)
        sparse_vectors = sparse_embedder.embed_batch(texts) if sparse_embedder else None
        store.upsert_documents(collection, chunks_to_embed, vectors, sparse_vectors=sparse_vectors)

    merged_chunks = {
        path: new_chunk_counts.get(path, existing_chunks.get(path, 0))
        for path in new_hashes
    }
    index_state.save_state(state_pool, collection, new_hashes, merged_chunks)

    return chunks_to_embed


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
