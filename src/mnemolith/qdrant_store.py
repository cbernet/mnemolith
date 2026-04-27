import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    Fusion,
    FusionQuery,
    MatchAny,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from mnemolith.embeddings import SparseVector as EmbSparseVector
from mnemolith.parser import Document, chunk_id
from mnemolith.vector_store import CollectionNotFoundError

logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(self, url: str | None = None, api_key: str | None = None):
        if url is None:
            from mnemolith.config import get_qdrant_url
            url = get_qdrant_url()
        if api_key is None:
            from mnemolith.config import get_qdrant_api_key
            api_key = get_qdrant_api_key()
        self.client = QdrantClient(url=url, api_key=api_key)
        self._named_vector_collections: set[str] = set()

    def ensure_collection(self, name: str, dimension: int, sparse: bool = False) -> None:
        collections = [c.name for c in self.client.get_collections().collections]
        if name in collections:
            has_named = self._has_named_vectors(name)
            if sparse and not has_named:
                raise ValueError(
                    f"Collection '{name}' exists without sparse vectors. "
                    "Re-run indexing with --clean to recreate it."
                )
            if has_named:
                self._named_vector_collections.add(name)
            return
        if sparse:
            self.client.create_collection(
                collection_name=name,
                vectors_config={"dense": VectorParams(size=dimension, distance=Distance.COSINE)},
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )
            self._named_vector_collections.add(name)
        else:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(collection_name=name)

    def delete_by_paths(self, collection: str, paths: list[str]) -> None:
        if not paths:
            return
        self.client.delete(
            collection_name=collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="path", match=MatchAny(any=paths))],
                ),
            ),
        )

    def _has_named_vectors(self, collection: str) -> bool:
        info = self.client.get_collection(collection)
        return isinstance(info.config.params.vectors, dict)

    def _make_point(
        self,
        doc: Document,
        vector: list[float],
        sv: EmbSparseVector | None = None,
    ) -> PointStruct:
        payload = {
            "path": doc.path,
            "title": doc.title,
            "content": doc.content,
            "tags": doc.tags,
            "links": doc.links,
            "heading": doc.heading,
        }
        if sv is not None:
            vec = {"dense": vector, "sparse": SparseVector(indices=sv.indices, values=sv.values)}
        else:
            vec = vector
        return PointStruct(id=chunk_id(doc.path, doc.chunk_index), vector=vec, payload=payload)

    def upsert_documents(
        self,
        collection: str,
        documents: list[Document],
        vectors: list[list[float]],
        sparse_vectors: list[EmbSparseVector] | None = None,
    ) -> None:
        if sparse_vectors is not None:
            points = [
                self._make_point(doc, vector, sv)
                for doc, vector, sv in zip(documents, vectors, sparse_vectors)
            ]
        else:
            points = [
                self._make_point(doc, vector)
                for doc, vector in zip(documents, vectors)
            ]
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(collection_name=collection, points=points[i:i + batch_size])

    def count_points(self, collection: str) -> int:
        from qdrant_client.http.exceptions import UnexpectedResponse
        try:
            return self.client.count(collection_name=collection).count
        except UnexpectedResponse as e:
            if e.status_code == 404:
                return 0
            raise

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
        sparse_query: EmbSparseVector | None = None,
    ) -> list[dict]:
        """Search the collection for similar documents.

        When sparse_query is provided, hybrid search is performed using RRF
        (Reciprocal Rank Fusion). RRF scores are rank-based (~1/(1+rank)) and are
        not comparable to cosine similarity values. score_threshold is therefore
        ignored in hybrid mode; a warning is logged if one is passed.
        """
        from qdrant_client.http.exceptions import UnexpectedResponse
        try:
            if sparse_query is not None:
                if score_threshold is not None:
                    logger.warning(
                        "score_threshold is ignored for hybrid search "
                        "(RRF scores are rank-based, not cosine similarity)"
                    )
                # Hybrid search: prefetch dense + sparse, fuse with RRF
                prefetch_limit = max(limit * 4, 20)
                results = self.client.query_points(
                    collection_name=collection,
                    prefetch=[
                        Prefetch(query=query_vector, using="dense", limit=prefetch_limit),
                        Prefetch(
                            query=SparseVector(
                                indices=sparse_query.indices,
                                values=sparse_query.values,
                            ),
                            using="sparse",
                            limit=prefetch_limit,
                        ),
                    ],
                    query=FusionQuery(fusion=Fusion.RRF),
                    limit=limit,
                    # score_threshold is not applied for RRF: RRF scores are rank-based
                    # (1/(1+rank)) and not comparable to cosine similarity thresholds.
                )
            elif collection in self._named_vector_collections:
                # Dense-only on a named-vector collection: must specify using="dense"
                results = self.client.query_points(
                    collection_name=collection,
                    query=query_vector,
                    using="dense",
                    limit=limit,
                    score_threshold=score_threshold,
                )
            else:
                # Standard flat-vector collection
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
