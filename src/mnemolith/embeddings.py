import random
from dataclasses import dataclass
from typing import Protocol

from mnemolith.config import get_embedding_provider


class Embedder(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class MockEmbedder:
    """Deterministic fake embedder for testing. Same text -> same vector."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        rng = random.Random(text)
        return [rng.uniform(-1, 1) for _ in range(self.dimension)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def build_embedder() -> Embedder:
    provider = get_embedding_provider()
    if provider == "openai":
        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedding provider: {provider}")


class OpenAIEmbedder:

    def __init__(self, model: str = "text-embedding-3-small", dimension: int = 1536):
        import openai

        self.client = openai.OpenAI()
        self.model = model
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(input=batch, model=self.model)
            results.extend(item.embedding for item in response.data)
        return results


@dataclass
class SparseVector:
    indices: list[int]
    values: list[float]


class SparseEmbedder(Protocol):
    def embed(self, text: str) -> SparseVector: ...
    def embed_batch(self, texts: list[str]) -> list[SparseVector]: ...


class MockSparseEmbedder:
    """Deterministic fake sparse embedder for testing. Same text -> same sparse vector."""

    def embed(self, text: str) -> SparseVector:
        rng = random.Random(text)
        n = rng.randint(3, 15)
        indices = sorted({rng.randint(0, 999) for _ in range(n)})
        values = [rng.uniform(0.1, 2.0) for _ in indices]
        return SparseVector(indices=indices, values=values)

    def embed_batch(self, texts: list[str]) -> list[SparseVector]:
        return [self.embed(t) for t in texts]


class BM25Embedder:
    """BM25 sparse embedder via fastembed Qdrant/bm25 model."""

    def __init__(self, model: str = "Qdrant/bm25"):
        from fastembed import SparseTextEmbedding
        self._model = SparseTextEmbedding(model_name=model)

    def embed(self, text: str) -> SparseVector:
        result = next(iter(self._model.embed([text])))
        return SparseVector(indices=result.indices.tolist(), values=result.values.tolist())

    def embed_batch(self, texts: list[str]) -> list[SparseVector]:
        results = list(self._model.embed(texts))
        return [SparseVector(indices=r.indices.tolist(), values=r.values.tolist()) for r in results]


def build_sparse_embedder() -> "BM25Embedder | None":
    from mnemolith.config import is_sparse_search_enabled
    if is_sparse_search_enabled():
        return BM25Embedder()
    return None
