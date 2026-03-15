<p align="center">
  <img src="docs/logo.svg" alt="mnemolith logo" width="400">
</p>

<p align="center">
  <a href="https://github.com/cbernet/mnemolith/actions/workflows/ci.yml"><img src="https://github.com/cbernet/mnemolith/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/github/cbernet/mnemolith"><img src="https://codecov.io/github/cbernet/mnemolith/graph/badge.svg?token=L573NMBQTD" alt="codecov"></a>
  <a href="https://github.com/cbernet/mnemolith/actions/workflows/security-review.yml"><img src="https://github.com/cbernet/mnemolith/actions/workflows/security-review.yml/badge.svg" alt="Security Review"></a>
</p> Semantic search over an Obsidian vault using RAG, Qdrant, and MCP.

## Architecture

```text
Obsidian vault (.md) → Indexing script → Embedding API → Qdrant (Docker)
                                                              ↑
Claude ← MCP server (mnemolith-mcp) ─────────────────────────┤
                                                              ↓
                                                   PostgreSQL (Docker)
                                                   (structured data)
```

## Quick start

```bash
git clone https://github.com/cbernet/mnemolith.git
cd mnemolith
uv sync                          # install dependencies
cp .env.example .env             # configure (set OBSIDIAN_VAULT_PATH, OPENAI_API_KEY)
docker compose up -d             # start Qdrant + PostgreSQL
uv run mnemolith index           # index your vault
uv run mnemolith search "query"  # search
```

## Documentation

- [Obsidian Setup](docs/obsidian-setup.md) — install Obsidian, set up Git backup
- [Getting Started](docs/getting-started.md) — install mnemolith, index, first search
- [Configuration](docs/configuration.md) — environment variables and options
- [MCP Setup](docs/mcp-setup.md) — let Claude search your vault (Desktop & Code)
- [Claude Code Plugin](docs/claude-plugin.md) — plugin install, obsidian-notes skill
- [CLI Reference](docs/cli-reference.md) — all commands and flags
- [How It Works](docs/how-it-works.md) — architecture, parsing, chunking, embedding

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker (for Qdrant)
- An OpenAI API key

## Development

```bash
uv sync                              # install deps
docker compose up -d                                     # start Qdrant + PostgreSQL
uv run pytest -m "not integration and not pg_integration" # unit tests only
uv run pytest                                            # all tests (requires Qdrant + PostgreSQL)
```

## Project structure

```text
src/mnemolith/
    config.py        # Environment variable handling
    main.py          # CLI entry point (index, search commands)
    parser.py        # Obsidian-aware markdown parser (frontmatter, wiki-links, tags)
    embeddings.py    # Embedding provider abstraction (OpenAI)
    indexer.py       # Vault indexing pipeline
    qdrant_store.py  # Qdrant vector store client
    pg_store.py      # PostgreSQL structured data store
    mcp_server.py    # MCP server exposing search + SQL tools to Claude
tests/
    fixtures/vault/  # Sample markdown notes for testing
.claude-plugin/
    plugin.json      # Claude Code plugin manifest
skills/
    obsidian-notes/
        SKILL.md     # Note creation skill for Claude Code
docs/                # User documentation
```

## License

MIT
