from qdrant_client import QdrantClient
from tqdm import tqdm

from second_brain.parser import Document, parse_vault, build_embedding_text, chunk_document
from second_brain.embeddings import Embedder
from second_brain.qdrant_store import ensure_collection, upsert_documents, search as qdrant_search


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
    vectors = [embedder.embed(build_embedding_text(chunk)) for chunk in tqdm(chunks, desc="Embedding")]
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
