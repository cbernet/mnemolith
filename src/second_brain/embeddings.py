import random
from typing import Protocol

from second_brain.config import get_embedding_provider


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

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]
