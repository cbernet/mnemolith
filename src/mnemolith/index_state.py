"""Per-file indexing state. Tracks the hash of each indexed source file so
incremental indexing can decide what to re-embed.

Bump SCHEMA_VERSION whenever chunking or embedding-text construction changes —
that invalidates every stored hash and forces a re-embed on next index run.
"""

import hashlib

from psycopg_pool import ConnectionPool

SCHEMA_VERSION = "1"


def file_hash(content: bytes) -> str:
    return f"{hashlib.sha256(content).hexdigest()}:{SCHEMA_VERSION}"


def ensure_state_table(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_index_state (
                collection TEXT NOT NULL,
                path       TEXT NOT NULL,
                file_hash  TEXT NOT NULL,
                num_chunks INTEGER NOT NULL,
                indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (collection, path)
            )
        """)


def load_state(pool: ConnectionPool, collection: str) -> dict[str, tuple[str, int]]:
    """Return {path: (file_hash, num_chunks)} for the given collection."""
    ensure_state_table(pool)
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT path, file_hash, num_chunks FROM vault_index_state WHERE collection = %s",
            (collection,),
        )
        return {row[0]: (row[1], row[2]) for row in cur.fetchall()}


def save_state(
    pool: ConnectionPool,
    collection: str,
    hashes: dict[str, str],
    num_chunks: dict[str, int],
) -> None:
    """Replace the full state for `collection` with the given hashes/counts.

    Paths absent from `hashes` are removed.
    """
    ensure_state_table(pool)
    with pool.connection() as conn:
        conn.execute(
            "DELETE FROM vault_index_state WHERE collection = %s",
            (collection,),
        )
        if not hashes:
            return
        rows = [(collection, path, hashes[path], num_chunks[path]) for path in hashes]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO vault_index_state (collection, path, file_hash, num_chunks) "
                "VALUES (%s, %s, %s, %s)",
                rows,
            )


def reset_state(pool: ConnectionPool, collection: str) -> None:
    ensure_state_table(pool)
    with pool.connection() as conn:
        conn.execute(
            "DELETE FROM vault_index_state WHERE collection = %s",
            (collection,),
        )
