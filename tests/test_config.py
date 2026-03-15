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


def test_get_backup_dir_default(monkeypatch, tmp_path):
    from mnemolith.config import get_backup_dir

    monkeypatch.delenv("BACKUP_DIR", raising=False)
    from pathlib import Path

    expected = Path("~/.mnemolith/backups").expanduser()
    assert get_backup_dir() == expected


def test_get_backup_dir_custom(monkeypatch, tmp_path):
    from mnemolith.config import get_backup_dir

    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "my_backups"))
    assert get_backup_dir() == tmp_path / "my_backups"


def test_get_postgres_conn_params_from_env_vars(monkeypatch):
    from mnemolith.config import get_postgres_conn_params

    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "myuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "mypass")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    monkeypatch.setenv("POSTGRES_HOST", "dbhost")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    params = get_postgres_conn_params()
    assert params == {
        "host": "dbhost",
        "port": "5433",
        "user": "myuser",
        "password": "mypass",
        "dbname": "mydb",
    }


def test_get_postgres_conn_params_from_dsn(monkeypatch):
    from mnemolith.config import get_postgres_conn_params

    monkeypatch.setenv("POSTGRES_DSN", "postgresql://u:p%40ss@host:5434/db")
    # Clear individual vars to ensure DSN parsing is used
    for var in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(var, raising=False)
    params = get_postgres_conn_params()
    assert params["host"] == "host"
    assert params["port"] == "5434"
    assert params["user"] == "u"
    assert params["password"] == "p@ss"
    assert params["dbname"] == "db"


def test_get_postgres_conn_params_defaults(monkeypatch):
    from mnemolith.config import get_postgres_conn_params

    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "myuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "mypass")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    params = get_postgres_conn_params()
    assert params["host"] == "localhost"
    assert params["port"] == "5432"
