import math
import os
from unittest.mock import Mock, patch

import pytest

from second_brain.embeddings import MockEmbedder, OpenAIEmbedder


def test_mock_embedder_dimension():
    e = MockEmbedder(dimension=128)
    vec = e.embed("hello")
    assert len(vec) == 128


def test_mock_embedder_deterministic():
    e = MockEmbedder()
    v1 = e.embed("same text")
    v2 = e.embed("same text")
    assert v1 == v2


def test_mock_embedder_different_texts():
    e = MockEmbedder()
    v1 = e.embed("text one")
    v2 = e.embed("text two")
    assert v1 != v2


def test_mock_embedder_values_in_range():
    e = MockEmbedder()
    vec = e.embed("test")
    assert all(-1 <= v <= 1 for v in vec)


def test_openai_embedder_basic_functionality():
    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        e = OpenAIEmbedder(model="text-embedding-3-small", dimension=3)
        vec = e.embed("test text")

        assert len(vec) == 3
        assert all(isinstance(v, float) for v in vec)
        mock_client.embeddings.create.assert_called_once_with(
            input="test text", model="text-embedding-3-small"
        )


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)
def test_openai_embedder_real_api():
    e = OpenAIEmbedder()
    vec = e.embed("hello world")

    assert len(vec) == 1536
    assert all(isinstance(v, float) for v in vec)
    assert not any(math.isnan(v) for v in vec)
    assert sum(abs(v) for v in vec) > 0
