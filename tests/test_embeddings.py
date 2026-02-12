from second_brain.embeddings import MockEmbedder


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
