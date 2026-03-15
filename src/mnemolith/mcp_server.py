from mcp.server.fastmcp import FastMCP

from mnemolith import pg_store
from mnemolith.config import get_collection_name
from mnemolith.embeddings import build_embedder
from mnemolith.indexer import search as indexer_search
from mnemolith.pg_store import get_pool, close_pool
from mnemolith.qdrant_store import get_client

mcp = FastMCP(
    "mnemolith",
    instructions=(
        "Personal knowledge base with two backends. "
        "Structured data (todo lists, habits, tracking) is in PostgreSQL — "
        "start with pg_list_tables to discover available tables, then pg_query to read them. "
        "Unstructured knowledge (notes, ideas, journals, references) is in the Obsidian vault — "
        "use the search tool for semantic search. "
        "For ambiguous queries, check both."
    ),
)


def format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."
    parts = []
    for r in results:
        heading = f" > {r['heading']}" if r.get("heading") else ""
        parts.append(
            f"[{r['score']:.3f}] {r['path']}: {r['title']}{heading}\n\n{r['content']}"
        )
    return "\n\n---\n\n".join(parts)


MAX_LIMIT = 50


@mcp.tool()
def search(query: str, limit: int = 5, score_threshold: float = 0.3) -> str:
    """Search the user's Obsidian vault for notes using semantic search.

    Use this for unstructured personal knowledge: notes, ideas, daily journals,
    meeting notes, references, and written reflections. NOT for structured data
    like todo lists or tracking — those are in PostgreSQL.
    """
    limit = max(1, min(limit, MAX_LIMIT))
    embedder = build_embedder()
    client = get_client()
    collection = get_collection_name()
    results = indexer_search(query, embedder, client, collection, limit=limit, score_threshold=score_threshold)
    return format_results(results)


@mcp.tool()
def pg_list_tables() -> str:
    """List all tables in the user's personal PostgreSQL database.

    Start here when looking for structured personal data like todo lists,
    habit tracking, or any tabular information. Then use pg_query to read the data.
    """
    tables = pg_store.list_tables(get_pool())
    if not tables:
        return "No tables found."
    return "\n".join(tables)


@mcp.tool()
def pg_describe_table(table_name: str) -> str:
    """Describe the columns of a table in the user's personal PostgreSQL database."""
    columns = pg_store.describe_table(get_pool(), table_name)
    if not columns:
        return f"Table '{table_name}' not found or has no columns."
    lines = [f"{c['column']} ({c['type']}, nullable={c['nullable']})" for c in columns]
    return "\n".join(lines)


@mcp.tool()
def pg_create_table(sql: str) -> str:
    """Execute a DDL statement (CREATE TABLE, ALTER TABLE, DROP TABLE) on the user's personal PostgreSQL database. Requires human approval."""
    pg_store.execute_ddl(get_pool(), sql)
    return "OK"


@mcp.tool()
def pg_query(sql: str, params: str | None = None) -> str:
    """Run a read-only SQL query (SELECT) on the user's personal PostgreSQL database.

    Use this to read structured personal data (todos, tracking, etc.) after
    discovering the schema with pg_list_tables and pg_describe_table.
    """
    p = tuple(params.split(",")) if params else None
    rows = pg_store.execute_query(get_pool(), sql, p)
    if not rows:
        return "No results."
    lines = []
    headers = list(rows[0].keys())
    lines.append(" | ".join(headers))
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(" | ".join(str(row[h]) for h in headers))
    return "\n".join(lines)


@mcp.tool()
def pg_mutate(sql: str, params: str | None = None) -> str:
    """Run a data modification query (INSERT, UPDATE, DELETE) on the user's personal PostgreSQL database. Returns affected row count."""
    p = tuple(params.split(",")) if params else None
    count = pg_store.execute_mutate(get_pool(), sql, p)
    return f"{count} row(s) affected."


import atexit

atexit.register(close_pool)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
