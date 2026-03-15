from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from mnemolith.parser import Document


def get_client(url: str | None = None, api_key: str | None = None) -> QdrantClient:
    if url is None:
        from mnemolith.config import get_qdrant_url
        url = get_qdrant_url()
    if api_key is None:
        from mnemolith.config import get_qdrant_api_key
        api_key = get_qdrant_api_key()
    return QdrantClient(url=url, api_key=api_key)


def ensure_collection(client: QdrantClient, name: str, dimension: int):
    collections = [c.name for c in client.get_collections().collections]
    if name not in collections:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )


def delete_collection(client: QdrantClient, name: str):
    client.delete_collection(collection_name=name)


def upsert_documents(
    client: QdrantClient,
    collection: str,
    documents: list[Document],
    vectors: list[list[float]],
):
    points = [
        PointStruct(
            id=i,
            vector=vector,
            payload={
                "path": doc.path,
                "title": doc.title,
                "content": doc.content,
                "tags": doc.tags,
                "links": doc.links,
                "heading": doc.heading,
            },
        )
        for i, (doc, vector) in enumerate(zip(documents, vectors))
    ]
    client.upsert(collection_name=collection, points=points)


def search(
    client: QdrantClient,
    collection: str,
    query_vector: list[float],
    limit: int = 5,
    score_threshold: float | None = None,
) -> list[dict]:
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        score_threshold=score_threshold,
    )
    return [
        {**hit.payload, "score": hit.score}
        for hit in results.points
    ]
