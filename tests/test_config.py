import pytest

from mnemolith.config import get_vault_path


def test_get_vault_path(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/home/user/my-vault")
    assert get_vault_path() == "/home/user/my-vault"


def test_get_vault_path_missing(monkeypatch):
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    with pytest.raises(EnvironmentError, match="OBSIDIAN_VAULT_PATH"):
        get_vault_path()


def test_get_postgres_dsn_missing(monkeypatch):
    from mnemolith.config import get_postgres_dsn

    for var in ("POSTGRES_DSN", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(EnvironmentError, match="POSTGRES_DSN"):
        get_postgres_dsn()


def test_get_postgres_dsn_explicit(monkeypatch):
    from mnemolith.config import get_postgres_dsn

    monkeypatch.setenv("POSTGRES_DSN", "postgresql://other:other@db:5432/other")
    assert get_postgres_dsn() == "postgresql://other:other@db:5432/other"


def test_get_postgres_dsn_from_parts(monkeypatch):
    from mnemolith.config import get_postgres_dsn

    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "myuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "mypass")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    assert get_postgres_dsn() == "postgresql://myuser:mypass@localhost:5432/mydb"
