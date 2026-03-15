import uuid
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from qdrant_client.http.exceptions import ResponseHandlingException

from mnemolith.config import get_postgres_dsn
from mnemolith.embeddings import MockEmbedder

load_dotenv()


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture
def vault_path() -> str:
    return str(FIXTURES_DIR)


@pytest.fixture
def mock_embedder() -> MockEmbedder:
    return MockEmbedder(dimension=384)


@pytest.fixture
def pg_pool():
    """Create a temporary test database, yield a pool to it, then drop it."""
    db_name = f"mnemolith_test_{uuid.uuid4().hex[:8]}"
    try:
        admin_dsn = get_postgres_dsn()
        admin_conn = psycopg.connect(admin_dsn, autocommit=True)
    except Exception:
        pytest.skip("PostgreSQL not reachable — run: docker compose up -d")
    admin_conn.execute(f"CREATE DATABASE {db_name}")
    admin_conn.close()

    # Build DSN for the test database
    # Replace the database name in the DSN (last path component)
    test_dsn = admin_dsn.rsplit("/", 1)[0] + f"/{db_name}"
    pool = ConnectionPool(test_dsn, open=True)
    yield pool
    pool.close()

    # Drop the test database
    admin_conn = psycopg.connect(admin_dsn, autocommit=True)
    admin_conn.execute(f"DROP DATABASE {db_name}")
    admin_conn.close()


@pytest.fixture
def qdrant_collection():
    from mnemolith.qdrant_store import get_client, delete_collection

    name = f"test_{uuid.uuid4().hex[:8]}"
    try:
        client = get_client()
        client.get_collections()  # verify connection
    except (ResponseHandlingException, OSError):
        pytest.skip("Qdrant not reachable — run: docker compose up -d")
    yield name, client
    try:
        delete_collection(client, name)
    except Exception:
        pass
