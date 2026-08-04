import atexit
import hashlib
import re
from collections.abc import Iterator
from contextlib import contextmanager

from psycopg_pool import ConnectionPool

from mnemolith.config import get_postgres_dsn

_ALLOWED_DDL = re.compile(
    r"^\s*(CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE)\b",
    re.IGNORECASE,
)

_pool: ConnectionPool | None = None


def get_pool(dsn: str | None = None) -> ConnectionPool:
    global _pool
    if _pool is None:
        if dsn is None:
            dsn = get_postgres_dsn()
        _pool = ConnectionPool(dsn, open=True, reset=_reset_connection)
        atexit.register(close_pool)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _reset_connection(conn) -> None:
    conn.read_only = False


def _lock_id(key: str) -> int:
    """Map an arbitrary key to the signed 64-bit int pg_advisory_lock expects."""
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big", signed=True)


@contextmanager
def advisory_lock(pool: ConnectionPool, key: str) -> Iterator[bool]:
    """Try to take a cluster-wide lock named `key`; yield whether it was acquired.

    Session-scoped (not transaction-scoped), so it survives the commits a long
    operation makes. Another connection asking for the same key gets False —
    that's how concurrent index runs are kept from clobbering each other.
    """
    lock_id = _lock_id(key)
    with pool.connection() as conn:
        acquired = conn.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,)).fetchone()[0]
        try:
            yield acquired
        finally:
            if acquired:
                conn.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))


def list_tables(pool: ConnectionPool) -> list[str]:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        return [row[0] for row in cur.fetchall()]


def describe_table(pool: ConnectionPool, table_name: str) -> list[dict]:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position",
            (table_name,),
        )
        return [
            {"column": row[0], "type": row[1], "nullable": row[2]}
            for row in cur.fetchall()
        ]


def execute_ddl(pool: ConnectionPool, sql: str) -> None:
    if not _ALLOWED_DDL.match(sql):
        raise ValueError(
            "Only CREATE TABLE, ALTER TABLE, and DROP TABLE statements are allowed"
        )
    with pool.connection() as conn:
        conn.execute(sql)


def execute_query(pool: ConnectionPool, sql: str, params: tuple | None = None) -> list[dict]:
    with pool.connection() as conn:
        conn.read_only = True
        cur = conn.execute(sql, params)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def execute_mutate(pool: ConnectionPool, sql: str, params: tuple | None = None) -> int:
    with pool.connection() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount
