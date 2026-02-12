import random
from typing import Protocol


class Embedder(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]: ...


class MockEmbedder:
    """Deterministic fake embedder for testing. Same text -> same vector."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        rng = random.Random(text)
        return [rng.uniform(-1, 1) for _ in range(self.dimension)]


class OpenAIEmbedder:

    def __init__(self, model: str = "text-embedding-3-small", dimension: int = 1536):
        import openai

        self.client = openai.OpenAI()
        self.model = model
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding
