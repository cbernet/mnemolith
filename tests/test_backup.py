from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest


class TestBackupPostgres:
    def test_creates_dump_file(self, tmp_path, monkeypatch):
        from mnemolith.backup import backup_postgres

        monkeypatch.setenv("POSTGRES_USER", "u")
        monkeypatch.setenv("POSTGRES_PASSWORD", "p")
        monkeypatch.setenv("POSTGRES_DB", "db")
        monkeypatch.delenv("COMPOSE_FILE", raising=False)

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = b"-- PostgreSQL dump\nCREATE TABLE foo;"
            return result

        with patch("subprocess.run", side_effect=fake_run) as mock_run:
            path = backup_postgres(tmp_path)

        assert path == tmp_path / "pg_dump.sql"
        assert path.read_text() == "-- PostgreSQL dump\nCREATE TABLE foo;"
        cmd = mock_run.call_args[0][0]
        assert cmd[:2] == ["docker", "compose"]
        assert "exec" in cmd and "-T" in cmd
        assert "pg_dump" in cmd
        assert "-U" in cmd and "u" in cmd
        assert "db" in cmd

    def test_failure_raises(self, tmp_path, monkeypatch):
        from mnemolith.backup import backup_postgres

        monkeypatch.setenv("POSTGRES_USER", "u")
        monkeypatch.setenv("POSTGRES_PASSWORD", "p")
        monkeypatch.setenv("POSTGRES_DB", "db")
        monkeypatch.delenv("COMPOSE_FILE", raising=False)

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 1
            result.stderr = b"pg_dump: error"
            result.stdout = b""
            return result

        with patch("subprocess.run", side_effect=fake_run), pytest.raises(RuntimeError, match="pg_dump failed"):
            backup_postgres(tmp_path)

    def test_missing_docker_raises(self, tmp_path, monkeypatch):
        from mnemolith.backup import backup_postgres

        monkeypatch.setenv("POSTGRES_USER", "u")
        monkeypatch.setenv("POSTGRES_PASSWORD", "p")
        monkeypatch.setenv("POSTGRES_DB", "db")
        monkeypatch.delenv("COMPOSE_FILE", raising=False)

        with patch("subprocess.run", side_effect=FileNotFoundError), \
                pytest.raises(RuntimeError, match="docker compose not found"):
            backup_postgres(tmp_path)


class TestRestorePostgres:
    def test_pipes_dump_to_psql(self, tmp_path, monkeypatch):
        from mnemolith.backup import restore_postgres

        monkeypatch.setenv("POSTGRES_USER", "u")
        monkeypatch.setenv("POSTGRES_PASSWORD", "p")
        monkeypatch.setenv("POSTGRES_DB", "db")
        monkeypatch.delenv("COMPOSE_FILE", raising=False)

        dump_file = tmp_path / "pg_dump.sql"
        dump_file.write_text("CREATE TABLE foo;")

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run) as mock_run:
            restore_postgres(tmp_path)

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[:2] == ["docker", "compose"]
        assert "psql" in cmd
        # Dump content piped via stdin
        assert call_args[1]["input"] == b"CREATE TABLE foo;"

    def test_missing_dump_file_raises(self, tmp_path, monkeypatch):
        from mnemolith.backup import restore_postgres

        monkeypatch.setenv("POSTGRES_USER", "u")
        monkeypatch.setenv("POSTGRES_PASSWORD", "p")
        monkeypatch.setenv("POSTGRES_DB", "db")

        with pytest.raises(FileNotFoundError, match=r"pg_dump\.sql"):
            restore_postgres(tmp_path)


class TestBackupQdrant:
    def _make_http_mock(self, response_mock):
        """Create an httpx.Client mock that supports nested context managers."""
        http_mock = MagicMock()
        http_mock.__enter__ = lambda s: s
        http_mock.__exit__ = MagicMock(return_value=False)
        stream_ctx = MagicMock()
        stream_ctx.__enter__ = lambda s: response_mock
        stream_ctx.__exit__ = MagicMock(return_value=False)
        http_mock.stream.return_value = stream_ctx
        return http_mock

    def test_creates_snapshot_file(self, tmp_path, monkeypatch):
        from mnemolith.backup import backup_qdrant

        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
        monkeypatch.setenv("COLLECTION_NAME", "test_col")
        monkeypatch.delenv("QDRANT_API_KEY", raising=False)

        mock_store = MagicMock()
        snapshot_desc = MagicMock()
        snapshot_desc.name = "test_col-2026-03-15.snapshot"
        mock_store.client.create_snapshot.return_value = snapshot_desc

        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [b"snapshot-data-chunk"]
        http_mock = self._make_http_mock(mock_response)

        with patch("mnemolith.qdrant_store.QdrantStore", return_value=mock_store), \
                patch("httpx.Client", return_value=http_mock):
            path = backup_qdrant(tmp_path)

        assert path == tmp_path / "qdrant_snapshot.snapshot"
        assert path.read_bytes() == b"snapshot-data-chunk"
        mock_store.client.create_snapshot.assert_called_once_with("test_col", wait=True)

    def test_snapshot_download_failure_raises(self, tmp_path, monkeypatch):
        from mnemolith.backup import backup_qdrant

        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
        monkeypatch.setenv("COLLECTION_NAME", "test_col")
        monkeypatch.delenv("QDRANT_API_KEY", raising=False)

        mock_store = MagicMock()
        snapshot_desc = MagicMock()
        snapshot_desc.name = "snap.snapshot"
        mock_store.client.create_snapshot.return_value = snapshot_desc

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        http_mock = self._make_http_mock(mock_response)

        with patch("mnemolith.qdrant_store.QdrantStore", return_value=mock_store), \
                patch("httpx.Client", return_value=http_mock), \
                pytest.raises(httpx.HTTPStatusError):
            backup_qdrant(tmp_path)


class TestRestoreQdrant:
    def test_uploads_snapshot(self, tmp_path, monkeypatch):
        from mnemolith.backup import restore_qdrant

        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
        monkeypatch.setenv("COLLECTION_NAME", "test_col")
        monkeypatch.delenv("QDRANT_API_KEY", raising=False)

        snapshot_file = tmp_path / "qdrant_snapshot.snapshot"
        snapshot_file.write_bytes(b"snapshot-data")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.post", return_value=mock_response) as mock_post:
            restore_qdrant(tmp_path)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "test_col" in call_kwargs[0][0]
        assert "snapshots/upload" in call_kwargs[0][0]

    def test_missing_snapshot_file_raises(self, tmp_path, monkeypatch):
        from mnemolith.backup import restore_qdrant

        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
        monkeypatch.setenv("COLLECTION_NAME", "test_col")

        with pytest.raises(FileNotFoundError, match=r"qdrant_snapshot\.snapshot"):
            restore_qdrant(tmp_path)


class TestCreateBackup:
    def test_creates_timestamped_dir_and_runs_both(self, tmp_path, monkeypatch):
        from mnemolith.backup import create_backup

        with patch("mnemolith.backup.backup_postgres") as mock_pg, \
             patch("mnemolith.backup.backup_vector_store") as mock_qd:
            result = create_backup(tmp_path)

        # Should be a timestamped subdirectory
        assert result.parent == tmp_path
        assert result.name  # has a name
        assert result.is_dir()
        # Both backup functions called with the timestamped dir
        mock_pg.assert_called_once_with(result)
        mock_qd.assert_called_once_with(result)

    def test_uses_default_backup_dir(self, tmp_path, monkeypatch):
        from mnemolith.backup import create_backup

        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))

        with patch("mnemolith.backup.backup_postgres"), \
             patch("mnemolith.backup.backup_vector_store"):
            result = create_backup()

        assert result.parent == tmp_path

    def test_timestamp_format(self, tmp_path):
        import re

        from mnemolith.backup import create_backup

        with patch("mnemolith.backup.backup_postgres"), \
             patch("mnemolith.backup.backup_vector_store"):
            result = create_backup(tmp_path)

        assert re.match(r"\d{8}_\d{6}$", result.name)


class TestRestoreBackup:
    def test_calls_both_restores(self, tmp_path):
        from mnemolith.backup import restore_backup

        with patch("mnemolith.backup.restore_postgres") as mock_pg, \
             patch("mnemolith.backup.restore_vector_store") as mock_vs:
            restore_backup(tmp_path)

        mock_pg.assert_called_once_with(tmp_path)
        mock_vs.assert_called_once_with(tmp_path)

    def test_nonexistent_dir_raises(self):
        from mnemolith.backup import restore_backup

        with pytest.raises(FileNotFoundError, match="not found"):
            restore_backup(Path("/nonexistent/backup/dir"))
