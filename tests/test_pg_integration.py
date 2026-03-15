import pytest
from psycopg import sql

from mnemolith.pg_store import (
    get_pool,
    close_pool,
    list_tables,
    describe_table,
    execute_ddl,
    execute_query,
    execute_mutate,
)

pytestmark = pytest.mark.pg_integration


@pytest.fixture
def pg_pool():
    try:
        pool = get_pool()
        with pool.connection() as conn:
            conn.execute("SELECT 1")
    except Exception:
        pytest.skip("PostgreSQL not reachable — run: docker compose up -d")
    yield pool
    # cleanup: only drop tables created during tests
    tables = list_tables(pool)
    for t in tables:
        if t.startswith("test_"):
            with pool.connection() as conn:
                conn.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(t)))
    close_pool()


def test_create_and_list_table(pg_pool):
    execute_ddl(pg_pool, "CREATE TABLE test_groceries (id serial PRIMARY KEY, item text NOT NULL, quantity int DEFAULT 1)")
    tables = list_tables(pg_pool)
    assert "test_groceries" in tables


def test_describe_table(pg_pool):
    execute_ddl(pg_pool, "CREATE TABLE test_desc (id serial PRIMARY KEY, name text, done boolean DEFAULT false)")
    columns = describe_table(pg_pool, "test_desc")
    col_names = [c["column"] for c in columns]
    assert "id" in col_names
    assert "name" in col_names
    assert "done" in col_names


def test_insert_query_mutate(pg_pool):
    execute_ddl(pg_pool, "CREATE TABLE test_items (id serial PRIMARY KEY, name text, quantity int)")
    execute_mutate(pg_pool, "INSERT INTO test_items (name, quantity) VALUES (%s, %s)", ("milk", 2))
    execute_mutate(pg_pool, "INSERT INTO test_items (name, quantity) VALUES (%s, %s)", ("bread", 1))

    rows = execute_query(pg_pool, "SELECT name, quantity FROM test_items ORDER BY name")
    assert len(rows) == 2
    assert rows[0]["name"] == "bread"
    assert rows[1]["name"] == "milk"
    assert rows[1]["quantity"] == 2

    count = execute_mutate(pg_pool, "UPDATE test_items SET quantity = %s WHERE name = %s", (3, "milk"))
    assert count == 1

    rows = execute_query(pg_pool, "SELECT quantity FROM test_items WHERE name = %s", ("milk",))
    assert rows[0]["quantity"] == 3

    count = execute_mutate(pg_pool, "DELETE FROM test_items WHERE name = %s", ("bread",))
    assert count == 1

    rows = execute_query(pg_pool, "SELECT * FROM test_items")
    assert len(rows) == 1
