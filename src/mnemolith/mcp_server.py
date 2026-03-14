from mcp.server.fastmcp import FastMCP

from mnemolith.config import get_collection_name
from mnemolith.embeddings import build_embedder
from mnemolith.indexer import search as indexer_search
from mnemolith.qdrant_store import get_client

mcp = FastMCP("mnemolith")


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
def search(query: str, limit: int = 5) -> str:
    """Search the Obsidian vault for notes matching the query."""
    limit = max(1, min(limit, MAX_LIMIT))
    embedder = build_embedder()
    client = get_client()
    collection = get_collection_name()
    results = indexer_search(query, embedder, client, collection, limit=limit)
    return format_results(results)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
