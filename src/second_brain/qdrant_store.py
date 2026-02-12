from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from second_brain.parser import Document


def get_client(url: str = "http://localhost:6333") -> QdrantClient:
    return QdrantClient(url=url)


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
) -> list[dict]:
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
    )
    return [
        {**hit.payload, "score": hit.score}
        for hit in results.points
    ]
