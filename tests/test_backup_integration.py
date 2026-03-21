import pytest

from mnemolith.pg_store import execute_ddl, execute_query, execute_mutate
from mnemolith.backup import backup_postgres, restore_postgres

pytestmark = pytest.mark.pg_integration


def _setup_test_data(pg_pool):
    """Create a table and insert rows for testing."""
    execute_ddl(pg_pool, "CREATE TABLE items (id serial PRIMARY KEY, name text NOT NULL, count int)")
    execute_mutate(pg_pool, "INSERT INTO items (name, count) VALUES (%s, %s)", ("alpha", 10))
    execute_mutate(pg_pool, "INSERT INTO items (name, count) VALUES (%s, %s)", ("beta", 20))


def _get_test_db_name(pg_pool) -> str:
    """Extract database name from the pool's connection info."""
    with pg_pool.connection() as conn:
        return conn.info.dbname


def test_backup_and_restore_postgres_roundtrip(pg_pool, tmp_path, monkeypatch):
    """Full round-trip: insert data -> backup -> mutate -> restore -> verify original data."""
    db_name = _get_test_db_name(pg_pool)
    monkeypatch.setenv("POSTGRES_DB", db_name)

    _setup_test_data(pg_pool)

    # Backup
    dump_file = backup_postgres(tmp_path)
    assert dump_file.exists()
    dump_content = dump_file.read_text()
    assert "items" in dump_content
    assert "alpha" in dump_content

    # Mutate data after backup: delete a row, add a new one
    execute_mutate(pg_pool, "DELETE FROM items WHERE name = %s", ("alpha",))
    execute_mutate(pg_pool, "INSERT INTO items (name, count) VALUES (%s, %s)", ("gamma", 30))
    rows_before_restore = execute_query(pg_pool, "SELECT name FROM items ORDER BY name")
    names_before = [r["name"] for r in rows_before_restore]
    assert "alpha" not in names_before
    assert "gamma" in names_before

    # Restore
    restore_postgres(tmp_path)

    # Verify original data is back
    rows = execute_query(pg_pool, "SELECT name, count FROM items ORDER BY name")
    names = [r["name"] for r in rows]
    assert names == ["alpha", "beta"]
    assert rows[0]["count"] == 10
    assert rows[1]["count"] == 20
    # gamma should be gone
    assert "gamma" not in names


def test_backup_and_restore_multiple_tables(pg_pool, tmp_path, monkeypatch):
    """Verify backup/restore handles multiple tables correctly."""
    db_name = _get_test_db_name(pg_pool)
    monkeypatch.setenv("POSTGRES_DB", db_name)

    execute_ddl(pg_pool, "CREATE TABLE fruits (id serial PRIMARY KEY, name text)")
    execute_ddl(pg_pool, "CREATE TABLE colors (id serial PRIMARY KEY, name text)")
    execute_mutate(pg_pool, "INSERT INTO fruits (name) VALUES (%s)", ("apple",))
    execute_mutate(pg_pool, "INSERT INTO colors (name) VALUES (%s)", ("red",))

    backup_postgres(tmp_path)

    # Drop one table, modify the other
    execute_ddl(pg_pool, "DROP TABLE fruits")
    execute_mutate(pg_pool, "DELETE FROM colors")

    restore_postgres(tmp_path)

    fruits = execute_query(pg_pool, "SELECT name FROM fruits")
    colors = execute_query(pg_pool, "SELECT name FROM colors")
    assert len(fruits) == 1
    assert fruits[0]["name"] == "apple"
    assert len(colors) == 1
    assert colors[0]["name"] == "red"
