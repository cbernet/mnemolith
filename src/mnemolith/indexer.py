from qdrant_client import QdrantClient

from mnemolith.parser import Document, parse_vault, build_embedding_text, chunk_document
from mnemolith.embeddings import Embedder
from mnemolith.qdrant_store import ensure_collection, upsert_documents, search as qdrant_search


def index_vault(
    vault_path: str,
    embedder: Embedder,
    client: QdrantClient,
    collection: str,
) -> list[Document]:
    documents = parse_vault(vault_path)
    if not documents:
        return documents

    chunks = []
    for doc in documents:
        chunks.extend(chunk_document(doc))

    ensure_collection(client, collection, embedder.dimension)
    texts = [build_embedding_text(chunk) for chunk in chunks]
    print(f"Embedding {len(texts)} chunks...")
    vectors = embedder.embed_batch(texts)
    upsert_documents(client, collection, chunks, vectors)
    return chunks


def search(
    query: str,
    embedder: Embedder,
    client: QdrantClient,
    collection: str,
    limit: int = 5,
) -> list[dict]:
    query_vector = embedder.embed(query)
    return qdrant_search(client, collection, query_vector, limit=limit)
