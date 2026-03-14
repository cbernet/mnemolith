import argparse
import sys
from pathlib import Path

from qdrant_client.http.exceptions import UnexpectedResponse

from mnemolith.config import get_vault_path, get_collection_name
from mnemolith.embeddings import build_embedder
from mnemolith.indexer import index_vault, search
from mnemolith.qdrant_store import get_client

MAX_LIMIT = 50


def cmd_index(args):
    vault_path = args.vault_path or get_vault_path()
    if not Path(vault_path).is_dir():
        print(f"Error: '{vault_path}' is not a valid directory.")
        sys.exit(1)
    embedder = build_embedder()
    client = get_client()
    chunks = index_vault(vault_path, embedder, client, get_collection_name())
    print(f"Indexed {len(chunks)} chunks.")


def cmd_search(args):
    embedder = build_embedder()
    client = get_client()
    collection = get_collection_name()
    limit = max(1, min(args.limit, MAX_LIMIT))
    try:
        results = search(args.query, embedder, client, collection, limit=limit)
    except UnexpectedResponse as e:
        if e.status_code == 404:
            print(f"Collection '{collection}' not found. Run 'mnemolith index' first.")
            sys.exit(1)
        raise
    for r in reversed(results):
        heading = f" > {r['heading']}" if r.get('heading') else ""
        print("-"*70)
        print("\n")
        print(f"[{r['score']:.3f}] {r['path']}: {r['title']}{heading}")
        print("\n")
        print(r["content"])

def main():
    parser = argparse.ArgumentParser(prog="mnemolith")
    sub = parser.add_subparsers(dest="command")

    index_p = sub.add_parser("index", help="Index vault into Qdrant")
    index_p.add_argument("vault_path", nargs="?", help="Path to vault (or use OBSIDIAN_VAULT_PATH)")
    index_p.set_defaults(func=cmd_index)

    search_p = sub.add_parser("search", help="Search indexed documents")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=5,
                          help=f"Max results (1-{MAX_LIMIT})")
    search_p.set_defaults(func=cmd_search)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
