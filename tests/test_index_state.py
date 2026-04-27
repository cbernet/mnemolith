import pytest

from mnemolith.index_state import (
    SCHEMA_VERSION,
    file_hash,
    load_state,
    reset_state,
    save_state,
)


@pytest.fixture
def state_pool(pg_pool):
    """A pool with the vault_index_state table created (uses pg_pool from conftest)."""
    from mnemolith.index_state import ensure_state_table
    ensure_state_table(pg_pool)
    return pg_pool


def test_file_hash_includes_schema_version():
    """file_hash output must change when SCHEMA_VERSION changes."""
    h = file_hash(b"hello world")
    assert h.endswith(f":{SCHEMA_VERSION}")


def test_file_hash_deterministic():
    """Same content -> same hash."""
    assert file_hash(b"abc") == file_hash(b"abc")


def test_file_hash_changes_with_content():
    assert file_hash(b"abc") != file_hash(b"xyz")


@pytest.mark.pg_integration
def test_save_and_load_state(state_pool):
    save_state(state_pool, "coll", {"a.md": "h1", "b.md": "h2"}, {"a.md": 2, "b.md": 1})
    state = load_state(state_pool, "coll")
    assert state == {"a.md": ("h1", 2), "b.md": ("h2", 1)}


@pytest.mark.pg_integration
def test_load_state_empty(state_pool):
    assert load_state(state_pool, "missing") == {}


@pytest.mark.pg_integration
def test_save_state_replaces_existing_paths(state_pool):
    save_state(state_pool, "coll", {"a.md": "h1"}, {"a.md": 1})
    save_state(state_pool, "coll", {"a.md": "h2"}, {"a.md": 3})
    state = load_state(state_pool, "coll")
    assert state == {"a.md": ("h2", 3)}


@pytest.mark.pg_integration
def test_save_state_isolates_collections(state_pool):
    save_state(state_pool, "c1", {"a.md": "h1"}, {"a.md": 1})
    save_state(state_pool, "c2", {"a.md": "h2"}, {"a.md": 2})
    assert load_state(state_pool, "c1") == {"a.md": ("h1", 1)}
    assert load_state(state_pool, "c2") == {"a.md": ("h2", 2)}


@pytest.mark.pg_integration
def test_save_state_removes_paths_not_in_input(state_pool):
    """save_state replaces the full set: paths not in the new dict are removed."""
    save_state(state_pool, "coll", {"a.md": "h1", "b.md": "h2"}, {"a.md": 1, "b.md": 1})
    save_state(state_pool, "coll", {"a.md": "h1"}, {"a.md": 1})
    assert load_state(state_pool, "coll") == {"a.md": ("h1", 1)}


@pytest.mark.pg_integration
def test_reset_state(state_pool):
    save_state(state_pool, "coll", {"a.md": "h1"}, {"a.md": 1})
    reset_state(state_pool, "coll")
    assert load_state(state_pool, "coll") == {}
