import math
import os
from unittest.mock import Mock, patch

import pytest

from mnemolith.embeddings import (
    MockEmbedder,
    MockSparseEmbedder,
    OpenAIEmbedder,
    SparseVector,
    build_embedder,
    build_sparse_embedder,
)


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


def test_mock_embedder_embed_batch():
    e = MockEmbedder(dimension=128)
    texts = ["hello", "world", "hello"]
    vecs = e.embed_batch(texts)
    assert len(vecs) == 3
    assert all(len(v) == 128 for v in vecs)
    # deterministic: same text -> same vector
    assert vecs[0] == vecs[2]
    assert vecs[0] != vecs[1]


def test_openai_embedder_embed_batch():
    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2]),
            Mock(embedding=[0.3, 0.4]),
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        e = OpenAIEmbedder(model="text-embedding-3-small", dimension=2)
        vecs = e.embed_batch(["text one", "text two"])

        assert vecs == [[0.1, 0.2], [0.3, 0.4]]
        mock_client.embeddings.create.assert_called_once_with(
            input=["text one", "text two"], model="text-embedding-3-small"
        )


def test_openai_embedder_embed_batch_splits_large_input():
    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client

        def make_response(texts):
            r = Mock()
            r.data = [Mock(embedding=[float(i)]) for i in range(len(texts))]
            return r

        mock_client.embeddings.create.side_effect = lambda input, model, **_: make_response(input)  # noqa: A006

        e = OpenAIEmbedder(model="text-embedding-3-small", dimension=1)
        texts = [f"text {i}" for i in range(250)]
        vecs = e.embed_batch(texts, batch_size=100)

        assert len(vecs) == 250
        assert mock_client.embeddings.create.call_count == 3


def test_openai_embedder_count_tokens():
    with patch("openai.OpenAI"):
        e = OpenAIEmbedder(model="text-embedding-3-small")
        assert e.count_tokens("hello world") == 2
        assert e.count_tokens("") == 0


def test_openai_embedder_count_tokens_unknown_model():
    """Unknown model raises rather than silently guessing an encoding."""
    with patch("openai.OpenAI"):
        e = OpenAIEmbedder(model="some-future-model")
        with pytest.raises(KeyError):
            e.count_tokens("hello")


def test_openai_embedder_truncates_oversized_input():
    """Safety net: an oversized input is truncated, not sent through to fail the run."""
    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        sent = {}

        def capture(input, model, **_):  # noqa: A002
            sent["input"] = input
            r = Mock()
            r.data = [Mock(embedding=[0.0]) for _ in input]
            return r

        mock_client.embeddings.create.side_effect = capture

        e = OpenAIEmbedder(model="text-embedding-3-small", dimension=1)
        e.embed_batch(["word " * 20000])

        assert e.count_tokens(sent["input"][0]) <= e.max_input_tokens


def test_openai_embedder_embeds_when_tokenizer_unavailable():
    """The truncation safety net must never itself break a run.

    An unknown model has no tiktoken encoding, so truncation is skipped and the text
    is sent as-is -- unlike count_tokens, which raises rather than guess.
    """
    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1])]
        mock_client.embeddings.create.return_value = mock_response

        e = OpenAIEmbedder(model="some-future-model", dimension=1)
        assert e.embed_batch(["hello"]) == [[0.1]]
        assert mock_client.embeddings.create.call_args.kwargs["input"] == ["hello"]


def test_mock_embedder_count_tokens():
    e = MockEmbedder()
    assert e.count_tokens("one two three") == 3
    assert e.max_input_tokens > 0


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


def test_build_embedder_unknown_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        build_embedder()


def test_mock_sparse_embedder_returns_sparse_vector():
    e = MockSparseEmbedder()
    sv = e.embed("hello world")
    assert isinstance(sv, SparseVector)
    assert len(sv.indices) > 0
    assert len(sv.indices) == len(sv.values)
    assert all(isinstance(i, int) for i in sv.indices)
    assert all(isinstance(v, float) for v in sv.values)


def test_mock_sparse_embedder_deterministic():
    e = MockSparseEmbedder()
    sv1 = e.embed("same text")
    sv2 = e.embed("same text")
    assert sv1.indices == sv2.indices
    assert sv1.values == sv2.values


def test_mock_sparse_embedder_different_texts():
    e = MockSparseEmbedder()
    sv1 = e.embed("text one")
    sv2 = e.embed("text two")
    assert sv1.indices != sv2.indices or sv1.values != sv2.values


def test_mock_sparse_embedder_embed_batch():
    e = MockSparseEmbedder()
    results = e.embed_batch(["hello", "world", "hello"])
    assert len(results) == 3
    # deterministic: same text -> same sparse vector
    assert results[0].indices == results[2].indices
    assert results[0].values == results[2].values


def test_build_sparse_embedder_disabled(monkeypatch):
    monkeypatch.setenv("SPARSE_SEARCH_ENABLED", "false")
    assert build_sparse_embedder() is None


def test_build_sparse_embedder_enabled(monkeypatch):
    monkeypatch.setenv("SPARSE_SEARCH_ENABLED", "true")
    with patch("mnemolith.embeddings.BM25Embedder") as mock_cls:
        result = build_sparse_embedder()
        mock_cls.assert_called_once()
        assert result is mock_cls.return_value


@pytest.mark.integration
def test_bm25_embedder_produces_valid_sparse_vectors():
    """Real BM25Embedder via fastembed — verifies non-empty indices/values."""
    from mnemolith.embeddings import BM25Embedder
    e = BM25Embedder()
    sv = e.embed("the quick brown fox jumps over the lazy dog")
    assert isinstance(sv, SparseVector)
    assert len(sv.indices) > 0
    assert len(sv.indices) == len(sv.values)
    assert all(isinstance(i, int) for i in sv.indices)
    assert all(isinstance(v, float) for v in sv.values)
    # batch: same text -> same sparse vector
    results = e.embed_batch(["hello world", "hello world"])
    assert results[0].indices == results[1].indices
    assert results[0].values == results[1].values
