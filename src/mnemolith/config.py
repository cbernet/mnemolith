import os
from pathlib import Path
from urllib.parse import quote_plus, urlparse, unquote

from dotenv import load_dotenv

load_dotenv()


def get_vault_path() -> str:
    """Return the Obsidian vault path from OBSIDIAN_VAULT_PATH env var."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        raise EnvironmentError(
            "OBSIDIAN_VAULT_PATH environment variable is not set. "
            "Set it to the absolute path of your Obsidian vault."
        )
    return vault_path


def get_qdrant_url() -> str:
    url = os.environ.get("QDRANT_URL")
    if not url:
        raise EnvironmentError("QDRANT_URL environment variable is not set.")
    return url


def get_collection_name() -> str:
    name = os.environ.get("COLLECTION_NAME")
    if not name:
        raise EnvironmentError("COLLECTION_NAME environment variable is not set.")
    return name


def get_embedding_provider() -> str:
    provider = os.environ.get("EMBEDDING_PROVIDER")
    if not provider:
        raise EnvironmentError("EMBEDDING_PROVIDER environment variable is not set.")
    return provider


def get_postgres_dsn() -> str:
    dsn = os.environ.get("POSTGRES_DSN")
    if dsn:
        return dsn
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    db = os.environ.get("POSTGRES_DB")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    if not all([user, password, db]):
        raise EnvironmentError(
            "Set either POSTGRES_DSN or POSTGRES_USER + POSTGRES_PASSWORD + POSTGRES_DB."
        )
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def get_qdrant_api_key() -> str | None:
    """Return the Qdrant API key, or None if not set."""
    return os.environ.get("QDRANT_API_KEY")


def get_vector_backend() -> str:
    return os.environ.get("VECTOR_BACKEND", "qdrant")


def get_backup_dir() -> Path:
    return Path(os.environ.get("BACKUP_DIR", "~/.mnemolith/backups")).expanduser()


def get_postgres_conn_params() -> dict[str, str]:
    """Return dict with host, port, user, password, dbname for pg_dump/psql."""
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    db = os.environ.get("POSTGRES_DB")
    if all([user, password, db]):
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        return {"host": host, "port": port, "user": user, "password": password, "dbname": db}
    dsn = os.environ.get("POSTGRES_DSN")
    if dsn:
        parsed = urlparse(dsn)
        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "dbname": parsed.path.lstrip("/"),
        }
    raise EnvironmentError(
        "Set either POSTGRES_DSN or POSTGRES_USER + POSTGRES_PASSWORD + POSTGRES_DB."
    )
