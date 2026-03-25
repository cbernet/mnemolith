import subprocess
import sys
from argparse import Namespace
from unittest.mock import patch

import pytest

from mnemolith.main import cmd_backup, cmd_index, cmd_restore, cmd_search
from mnemolith.vector_store import CollectionNotFoundError


def test_main_help():
    result = subprocess.run(
        [sys.executable, "-m", "mnemolith.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "index" in result.stdout
    assert "search" in result.stdout


def test_cmd_index_invalid_path(tmp_path):
    args = Namespace(vault_path=str(tmp_path / "nonexistent"))
    with pytest.raises(SystemExit, match="1"):
        cmd_index(args)


@patch("mnemolith.main.get_collection_name", return_value="test_collection")
@patch("mnemolith.main.get_vector_store")
@patch("mnemolith.main.build_embedder")
@patch("mnemolith.main.index_vault", return_value=["c1", "c2", "c3"])
def test_cmd_index_success(mock_index, mock_embedder, mock_store, mock_collection, tmp_path, capsys):
    args = Namespace(vault_path=str(tmp_path), clean=False)
    cmd_index(args)
    assert "Indexed 3 chunks" in capsys.readouterr().out
    mock_index.assert_called_once()


@patch("mnemolith.main.get_collection_name", return_value="test_collection")
@patch("mnemolith.main.get_vector_store")
@patch("mnemolith.main.build_embedder")
@patch("mnemolith.main.search")
def test_cmd_search_success(mock_search, mock_embedder, mock_store, mock_collection, capsys):
    mock_search.return_value = [
        {"score": 0.9, "path": "note.md", "title": "Note", "heading": "Intro", "content": "Hello"},
    ]
    args = Namespace(query="test", limit=5, score_threshold=None)
    cmd_search(args)
    output = capsys.readouterr().out
    assert "note.md" in output
    assert "0.900" in output
    assert "Hello" in output


@patch("mnemolith.main.get_collection_name", return_value="test_collection")
@patch("mnemolith.main.get_vector_store")
@patch("mnemolith.main.build_embedder")
@patch("mnemolith.main.search")
def test_cmd_search_collection_not_found(mock_search, mock_embedder, mock_store, mock_collection, capsys):
    mock_search.side_effect = CollectionNotFoundError("test_collection")
    args = Namespace(query="test", limit=5, score_threshold=None)
    with pytest.raises(SystemExit, match="1"):
        cmd_search(args)
    assert "not found" in capsys.readouterr().out.lower()


def test_main_help_shows_backup_restore():
    result = subprocess.run(
        [sys.executable, "-m", "mnemolith.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert "backup" in result.stdout
    assert "restore" in result.stdout


@patch("mnemolith.main.create_backup")
def test_cmd_backup_success(mock_create, tmp_path, capsys):
    mock_create.return_value = tmp_path / "20260315_120000"
    args = Namespace(dir=None)
    cmd_backup(args)
    output = capsys.readouterr().out
    assert "20260315_120000" in output
    mock_create.assert_called_once_with(None)


@patch("mnemolith.main.create_backup")
def test_cmd_backup_custom_dir(mock_create, tmp_path, capsys):
    mock_create.return_value = tmp_path / "20260315_120000"
    args = Namespace(dir=str(tmp_path))
    cmd_backup(args)
    mock_create.assert_called_once_with(tmp_path)


@patch("mnemolith.main.restore_backup")
def test_cmd_restore_success(mock_restore, tmp_path, capsys):
    args = Namespace(backup_path=str(tmp_path))
    cmd_restore(args)
    output = capsys.readouterr().out
    assert "Restore complete" in output
    mock_restore.assert_called_once_with(tmp_path)


def test_cmd_restore_invalid_path(capsys):
    args = Namespace(backup_path="/nonexistent/path")
    with pytest.raises(SystemExit, match="1"):
        cmd_restore(args)
