from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from mnemolith.parser import Document
from mnemolith.vector_store import CollectionNotFoundError


class QdrantStore:
    def __init__(self, url: str | None = None, api_key: str | None = None):
        if url is None:
            from mnemolith.config import get_qdrant_url
            url = get_qdrant_url()
        if api_key is None:
            from mnemolith.config import get_qdrant_api_key
            api_key = get_qdrant_api_key()
        self.client = QdrantClient(url=url, api_key=api_key)

    def ensure_collection(self, name: str, dimension: int) -> None:
        collections = [c.name for c in self.client.get_collections().collections]
        if name not in collections:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(collection_name=name)

    def upsert_documents(
        self,
        collection: str,
        documents: list[Document],
        vectors: list[list[float]],
    ) -> None:
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
        self.client.upsert(collection_name=collection, points=points)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
    ) -> list[dict]:
        from qdrant_client.http.exceptions import UnexpectedResponse
        try:
            results = self.client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
        except UnexpectedResponse as e:
            if e.status_code == 404:
                raise CollectionNotFoundError(collection) from e
            raise
        return [
            {**hit.payload, "score": hit.score}
            for hit in results.points
        ]
