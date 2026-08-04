from unittest.mock import MagicMock

import pytest
from psycopg_pool import ConnectionPool

from mnemolith import index_state, pg_store
from mnemolith.embeddings import MockEmbedder
from mnemolith.indexer import IndexLockedError, LegacyCollectionError, index_vault

pytestmark = pytest.mark.pg_integration


@pytest.fixture
def tmp_vault(tmp_path):
    (tmp_path / "a.md").write_text("Content A.")
    (tmp_path / "b.md").write_text("Content B.")
    return tmp_path


@pytest.fixture
def store():
    s = MagicMock()
    s.count_points.return_value = 0
    return s


@pytest.fixture
def embedder():
    return MockEmbedder(dimension=8)


def test_first_run_indexes_everything(tmp_vault, embedder, store, pg_pool):
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert len(result.chunks) == 2
    store.upsert_documents.assert_called_once()
    store.delete_by_paths.assert_not_called()
    state = index_state.load_state(pg_pool, "c")
    assert set(state.keys()) == {"a.md", "b.md"}


def test_no_changes_skips_work(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert result.chunks == []
    assert result.changed is False
    assert result.summary() == "Index is up to date."
    store.upsert_documents.assert_not_called()
    store.delete_by_paths.assert_not_called()


def test_modified_file_reembedded(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    (tmp_vault / "a.md").write_text("Content A modified.")
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert {c.path for c in result.chunks} == {"a.md"}
    store.delete_by_paths.assert_called_once_with("c", ["a.md"])
    store.upsert_documents.assert_called_once()


def test_deleted_file_evicted(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    (tmp_vault / "a.md").unlink()
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert result.chunks == []
    store.delete_by_paths.assert_called_once_with("c", ["a.md"])
    store.upsert_documents.assert_not_called()
    state = index_state.load_state(pg_pool, "c")
    assert set(state.keys()) == {"b.md"}


def test_added_file_indexed(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    (tmp_vault / "c.md").write_text("Content C.")
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert {c.path for c in result.chunks} == {"c.md"}
    store.delete_by_paths.assert_not_called()
    store.upsert_documents.assert_called_once()


def test_full_rebuilds_regardless(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    result = index_vault(str(tmp_vault), embedder, store, "c", full=True, state_pool=pg_pool)
    assert len(result.chunks) == 2
    store.delete_collection.assert_called_once_with("c")
    store.upsert_documents.assert_called_once()


def test_legacy_collection_refused(tmp_vault, embedder, store, pg_pool):
    """Empty state but non-empty vector store -> refuse incremental."""
    store.count_points.return_value = 7
    with pytest.raises(LegacyCollectionError, match="--full"):
        index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)


def test_full_recovers_legacy_collection(tmp_vault, embedder, store, pg_pool):
    """--full ignores the legacy state and rebuilds."""
    store.count_points.return_value = 7
    index_vault(str(tmp_vault), embedder, store, "c", full=True, state_pool=pg_pool)
    store.delete_collection.assert_called_once_with("c")


def test_schema_version_bump_invalidates_state(tmp_vault, embedder, store, pg_pool, monkeypatch):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    monkeypatch.setattr(index_state, "SCHEMA_VERSION", "999")
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert {c.path for c in result.chunks} == {"a.md", "b.md"}


def test_clean_alias_still_works(tmp_vault, embedder, store, pg_pool):
    """clean=True is accepted as a deprecated alias for full=True."""
    result = index_vault(str(tmp_vault), embedder, store, "c", clean=True, state_pool=pg_pool)
    assert len(result.chunks) == 2
    store.delete_collection.assert_called_once_with("c")


def test_empty_vault_first_run(tmp_path, embedder, store, pg_pool):
    result = index_vault(str(tmp_path), embedder, store, "c", state_pool=pg_pool)
    assert result.chunks == []
    store.upsert_documents.assert_not_called()


def test_subsequent_run_after_all_files_deleted(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    store.reset_mock()
    (tmp_vault / "a.md").unlink()
    (tmp_vault / "b.md").unlink()
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert result.chunks == []
    store.delete_by_paths.assert_called_once()
    deleted_paths = set(store.delete_by_paths.call_args[0][1])
    assert deleted_paths == {"a.md", "b.md"}
    assert index_state.load_state(pg_pool, "c") == {}


def test_summary_reports_each_kind_of_change(tmp_vault, embedder, store, pg_pool):
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    (tmp_vault / "a.md").write_text("Content A modified.")
    (tmp_vault / "b.md").unlink()
    (tmp_vault / "c.md").write_text("Content C.")
    result = index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert result.added == ["c.md"]
    assert result.modified == ["a.md"]
    assert result.deleted == ["b.md"]
    assert result.changed is True
    assert result.summary() == "+1 ~1 -1 files, 2 chunks embedded"


def test_indexer_writes_nothing_to_stdout(tmp_vault, embedder, store, pg_pool, capsys):
    """The MCP server speaks JSON-RPC over stdout — the indexer must never print."""
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    assert capsys.readouterr().out == ""


def test_concurrent_run_is_refused(tmp_vault, embedder, store, pg_pool):
    """A run started while another holds the collection lock must not touch state."""
    other = ConnectionPool(pg_pool.conninfo, open=True)
    try:
        with pg_store.advisory_lock(other, "index:c") as acquired:
            assert acquired
            with pytest.raises(IndexLockedError):
                index_vault(str(tmp_vault), embedder, store, "c", state_pool=pg_pool)
    finally:
        other.close()
    store.upsert_documents.assert_not_called()
    assert index_state.load_state(pg_pool, "c") == {}
