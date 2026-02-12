from qdrant_client import QdrantClient

from second_brain.parser import Document, parse_vault
from second_brain.embeddings import Embedder
from second_brain.qdrant_store import ensure_collection, upsert_documents, search as qdrant_search


def index_vault(
    vault_path: str,
    embedder: Embedder,
    client: QdrantClient,
    collection: str = "obsidian",
) -> list[Document]:
    documents = parse_vault(vault_path)
    if not documents:
        return documents

    ensure_collection(client, collection, embedder.dimension)
    vectors = [embedder.embed(doc.content) for doc in documents]
    upsert_documents(client, collection, documents, vectors)
    return documents


def search(
    query: str,
    embedder: Embedder,
    client: QdrantClient,
    collection: str = "obsidian",
    limit: int = 5,
) -> list[dict]:
    query_vector = embedder.embed(query)
    return qdrant_search(client, collection, query_vector, limit=limit)
