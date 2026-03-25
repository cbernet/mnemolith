from unittest.mock import patch

from mnemolith.mcp_server import (
    format_results,
    pg_create_table,
    pg_describe_table,
    pg_list_tables,
    pg_mutate,
    pg_query,
    search,
    vault_path,
)


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


@patch("mnemolith.mcp_server.indexer_search")
@patch("mnemolith.mcp_server.get_vector_store")
@patch("mnemolith.mcp_server.get_collection_name")
@patch("mnemolith.mcp_server.build_embedder")
def test_search_calls_indexer(mock_embedder, mock_collection, mock_store, mock_search):
    mock_search.return_value = _make_results()
    result = search("test query", 3)
    mock_search.assert_called_once()
    args = mock_search.call_args
    assert args[0][0] == "test query"
    assert args[1]["limit"] == 3
    assert "notes/python.md" in result


@patch("mnemolith.mcp_server.get_vault_path", return_value="/home/user/obsidian")
def test_vault_path(mock_get_vault):
    result = vault_path()
    assert "/home/user/obsidian" in result


# --- PostgreSQL MCP tools ---


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_list_tables(mock_get_pool, mock_pg_store):
    mock_pg_store.list_tables.return_value = ["groceries", "todos"]
    result = pg_list_tables()
    assert "groceries" in result
    assert "todos" in result


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_list_tables_empty(mock_get_pool, mock_pg_store):
    mock_pg_store.list_tables.return_value = []
    result = pg_list_tables()
    assert "No tables" in result


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_describe_table(mock_get_pool, mock_pg_store):
    mock_pg_store.describe_table.return_value = [
        {"column": "id", "type": "integer", "nullable": "NO"},
        {"column": "name", "type": "text", "nullable": "YES"},
    ]
    result = pg_describe_table("groceries")
    assert "id" in result
    assert "integer" in result
    assert "name" in result


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_create_table(mock_get_pool, mock_pg_store):
    result = pg_create_table("CREATE TABLE test (id int)")
    mock_pg_store.execute_ddl.assert_called_once()
    assert "OK" in result


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_query(mock_get_pool, mock_pg_store):
    mock_pg_store.execute_query.return_value = [
        {"id": 1, "name": "milk"},
        {"id": 2, "name": "bread"},
    ]
    result = pg_query("SELECT * FROM groceries")
    assert "milk" in result
    assert "bread" in result


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_query_no_results(mock_get_pool, mock_pg_store):
    mock_pg_store.execute_query.return_value = []
    result = pg_query("SELECT * FROM groceries")
    assert "No results" in result


@patch("mnemolith.mcp_server.pg_store")
@patch("mnemolith.mcp_server.get_pool")
def test_pg_mutate(mock_get_pool, mock_pg_store):
    mock_pg_store.execute_mutate.return_value = 3
    result = pg_mutate("DELETE FROM groceries WHERE done = true")
    assert "3" in result
    assert "row" in result
