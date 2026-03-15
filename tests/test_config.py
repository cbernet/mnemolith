import pytest

from mnemolith.config import get_vault_path


def test_get_vault_path(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/home/user/my-vault")
    assert get_vault_path() == "/home/user/my-vault"


def test_get_vault_path_missing(monkeypatch):
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    with pytest.raises(EnvironmentError, match="OBSIDIAN_VAULT_PATH"):
        get_vault_path()


def test_get_postgres_dsn_default(monkeypatch):
    from mnemolith.config import get_postgres_dsn

    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    assert get_postgres_dsn() == "postgresql://mnemolith:mnemolith@localhost:5432/mnemolith"


def test_get_postgres_dsn_custom(monkeypatch):
    from mnemolith.config import get_postgres_dsn

    monkeypatch.setenv("POSTGRES_DSN", "postgresql://other:other@db:5432/other")
    assert get_postgres_dsn() == "postgresql://other:other@db:5432/other"
