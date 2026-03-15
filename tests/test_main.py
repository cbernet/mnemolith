import subprocess
import sys
from argparse import Namespace
from unittest.mock import patch, Mock

import httpx
import pytest
from qdrant_client.http.exceptions import UnexpectedResponse

from mnemolith.main import cmd_index, cmd_search


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


@patch("mnemolith.main.get_client")
@patch("mnemolith.main.build_embedder")
@patch("mnemolith.main.index_vault", return_value=["c1", "c2", "c3"])
def test_cmd_index_success(mock_index, mock_embedder, mock_client, tmp_path, capsys):
    args = Namespace(vault_path=str(tmp_path))
    cmd_index(args)
    assert "Indexed 3 chunks" in capsys.readouterr().out
    mock_index.assert_called_once()


@patch("mnemolith.main.get_client")
@patch("mnemolith.main.build_embedder")
@patch("mnemolith.main.search")
def test_cmd_search_success(mock_search, mock_embedder, mock_client, capsys):
    mock_search.return_value = [
        {"score": 0.9, "path": "note.md", "title": "Note", "heading": "Intro", "content": "Hello"},
    ]
    args = Namespace(query="test", limit=5, score_threshold=None)
    cmd_search(args)
    output = capsys.readouterr().out
    assert "note.md" in output
    assert "0.900" in output
    assert "Hello" in output


@patch("mnemolith.main.get_client")
@patch("mnemolith.main.build_embedder")
@patch("mnemolith.main.search")
def test_cmd_search_collection_not_found(mock_search, mock_embedder, mock_client, capsys):
    mock_search.side_effect = UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=b"",
        headers=httpx.Headers(),
    )
    args = Namespace(query="test", limit=5, score_threshold=None)
    with pytest.raises(SystemExit, match="1"):
        cmd_search(args)
    assert "not found" in capsys.readouterr().out.lower()
