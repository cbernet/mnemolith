import pytest

from second_brain.config import get_vault_path


def test_get_vault_path(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/home/user/my-vault")
    assert get_vault_path() == "/home/user/my-vault"


def test_get_vault_path_missing(monkeypatch):
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    with pytest.raises(EnvironmentError, match="OBSIDIAN_VAULT_PATH"):
        get_vault_path()
