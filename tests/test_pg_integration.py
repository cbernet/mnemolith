import pytest
from psycopg_pool import ConnectionPool

from mnemolith.pg_store import (
    advisory_lock,
    describe_table,
    execute_ddl,
    execute_mutate,
    execute_query,
    list_tables,
)

pytestmark = pytest.mark.pg_integration


@pytest.fixture
def other_pool(pg_pool):
    """A second pool to the same database — a distinct session, so it sees pg_pool's locks."""
    pool = ConnectionPool(pg_pool.conninfo, open=True)
    yield pool
    pool.close()


def test_create_and_list_table(pg_pool):
    execute_ddl(pg_pool, "CREATE TABLE test_groceries "
                "(id serial PRIMARY KEY, item text NOT NULL, quantity int DEFAULT 1)")
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


def test_advisory_lock_excludes_other_session_and_releases(pg_pool, other_pool):
    with advisory_lock(pg_pool, "index:c") as acquired:
        assert acquired
        with advisory_lock(other_pool, "index:c") as second:
            assert second is False
        with advisory_lock(other_pool, "index:other") as unrelated:
            assert unrelated  # a different key is a different lock

    with advisory_lock(other_pool, "index:c") as after_release:
        assert after_release


def test_advisory_lock_releases_on_exception(pg_pool, other_pool):
    with pytest.raises(RuntimeError):  # noqa: SIM117
        with advisory_lock(pg_pool, "index:c") as acquired:
            assert acquired
            raise RuntimeError("boom")

    with advisory_lock(other_pool, "index:c") as acquired:
        assert acquired
