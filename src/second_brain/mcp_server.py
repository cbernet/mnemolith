from mcp.server.fastmcp import FastMCP

from second_brain.config import get_collection_name
from second_brain.embeddings import build_embedder
from second_brain.indexer import search as indexer_search
from second_brain.qdrant_store import get_client

mcp = FastMCP("second-brain")


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


@mcp.tool()
def search(query: str, limit: int = 5) -> str:
    """Search the Obsidian vault for notes matching the query."""
    embedder = build_embedder()
    client = get_client()
    collection = get_collection_name()
    results = indexer_search(query, embedder, client, collection, limit=limit)
    return format_results(results)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
