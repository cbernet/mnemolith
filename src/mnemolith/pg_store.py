from psycopg_pool import ConnectionPool

from mnemolith.config import get_postgres_dsn

_pool: ConnectionPool | None = None


def get_pool(dsn: str | None = None) -> ConnectionPool:
    global _pool
    if _pool is None:
        if dsn is None:
            dsn = get_postgres_dsn()
        _pool = ConnectionPool(dsn, open=True, reset=_reset_connection)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _reset_connection(conn) -> None:
    conn.read_only = False


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
