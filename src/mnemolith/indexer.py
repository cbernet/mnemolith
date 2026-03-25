from mnemolith.parser import Document, parse_vault, build_embedding_text, chunk_document
from mnemolith.embeddings import Embedder
from mnemolith.vector_store import VectorStore


def index_vault(
    vault_path: str,
    embedder: Embedder,
    store: VectorStore,
    collection: str,
    clean: bool = False,
    sparse_embedder=None,
) -> list[Document]:
    documents = parse_vault(vault_path)
    if not documents:
        return documents

    chunks = []
    for doc in documents:
        chunks.extend(chunk_document(doc))

    if clean:
        store.delete_collection(collection)
    store.ensure_collection(collection, embedder.dimension, sparse=sparse_embedder is not None)
    texts = [build_embedding_text(chunk) for chunk in chunks]
    print(f"Embedding {len(texts)} chunks...")
    vectors = embedder.embed_batch(texts)
    sparse_vectors = sparse_embedder.embed_batch(texts) if sparse_embedder else None
    store.upsert_documents(collection, chunks, vectors, sparse_vectors=sparse_vectors)
    return chunks


def search(
    query: str,
    embedder: Embedder,
    store: VectorStore,
    collection: str,
    limit: int = 5,
    score_threshold: float | None = None,
    sparse_embedder=None,
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
