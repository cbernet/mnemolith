from unittest.mock import patch, MagicMock

from second_brain.mcp_server import format_results, search


def _make_results():
    return [
        {
            "score": 0.92,
            "path": "notes/python.md",
            "title": "python",
            "heading": "Decorators",
            "content": "Decorators wrap functions.",
            "tags": ["python", "programming"],
            "links": ["functions"],
        },
        {
            "score": 0.85,
            "path": "journal/2024-01.md",
            "title": "2024-01",
            "heading": None,
            "content": "Started learning Qdrant.",
            "tags": ["journal"],
            "links": [],
        },
    ]


def test_format_results_includes_source_and_content():
    results = _make_results()
    text = format_results(results)
    assert "notes/python.md" in text
    assert "Decorators" in text
    assert "Decorators wrap functions." in text
    assert "journal/2024-01.md" in text
    assert "Started learning Qdrant." in text


def test_format_results_empty():
    assert "No results found" in format_results([])


@patch("second_brain.mcp_server.indexer_search")
@patch("second_brain.mcp_server.get_client")
@patch("second_brain.mcp_server.get_collection_name")
@patch("second_brain.mcp_server.build_embedder")
def test_search_calls_indexer(mock_embedder, mock_collection, mock_client, mock_search):
    mock_search.return_value = _make_results()
    result = search("test query", 3)
    mock_search.assert_called_once()
    args = mock_search.call_args
    assert args[0][0] == "test query"
    assert args[1]["limit"] == 3
    assert "notes/python.md" in result
