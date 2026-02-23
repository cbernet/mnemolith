import argparse
import sys

from second_brain.config import get_vault_path, get_collection_name, get_embedding_provider
from second_brain.embeddings import OpenAIEmbedder
from second_brain.indexer import index_vault, search
from second_brain.qdrant_store import get_client


def build_embedder():
    provider = get_embedding_provider()
    if provider == "openai":
        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedding provider: {provider}")


def cmd_index(args):
    vault_path = args.vault_path or get_vault_path()
    embedder = build_embedder()
    client = get_client()
    chunks = index_vault(vault_path, embedder, client, get_collection_name())
    print(f"Indexed {len(chunks)} chunks.")


def cmd_search(args):
    embedder = build_embedder()
    client = get_client()
    results = search(args.query, embedder, client, get_collection_name(), limit=args.limit)
    for r in results:
        heading = f" > {r['heading']}" if r.get('heading') else ""
        print(f"[{r['score']:.3f}] {r['path']}: {r['title']}{heading}")


def main():
    parser = argparse.ArgumentParser(prog="second-brain")
    sub = parser.add_subparsers(dest="command")

    index_p = sub.add_parser("index", help="Index vault into Qdrant")
    index_p.add_argument("vault_path", nargs="?", help="Path to vault (or use OBSIDIAN_VAULT_PATH)")
    index_p.set_defaults(func=cmd_index)

    search_p = sub.add_parser("search", help="Search indexed documents")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=5)
    search_p.set_defaults(func=cmd_search)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
