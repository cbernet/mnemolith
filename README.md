<p align="center">
  <img src="docs/logo.svg" alt="mnemolith logo" width="400">
</p>

<p align="center">
  <a href="https://github.com/cbernet/mnemolith/actions/workflows/ci.yml"><img src="https://github.com/cbernet/mnemolith/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/github/cbernet/mnemolith"><img src="https://codecov.io/github/cbernet/mnemolith/graph/badge.svg?token=L573NMBQTD" alt="codecov"></a>
  <a href="https://github.com/cbernet/mnemolith/actions/workflows/security-review.yml"><img src="https://github.com/cbernet/mnemolith/actions/workflows/security-review.yml/badge.svg" alt="Security Review"></a>
</p>

<p align="center"><em>Your personal knowledge base, searchable by AI.</em></p>

Mnemolith turns your [Obsidian](https://obsidian.md) vault into a semantic search engine and pairs it with a PostgreSQL database for structured data. Together, they form a unified personal knowledge base that Claude can query through [MCP](https://modelcontextprotocol.io).

- **Save your conversations as notes** - simply ask Claude to save the discussion as a note to your vault. 
- **Semantic search** — index your markdown notes into [Qdrant](https://qdrant.tech) and find them by meaning, not just keywords.
- **Structured data** — store todo lists, habit trackers, portfolios, and anything tabular in PostgreSQL. Just tell Claude what you want and it will create the necessary tables in Mnemolith. 
- **MCP integration** — Claude (Desktop or Code) searches both backends in a single conversation, bridging prose and data automatically.
- **You own everything** — notes stay as plain markdown files, data lives in a local Postgres you can inspect with CloudBeaver, and backups are a single CLI command.

```text
Obsidian vault (.md) → Indexing script → Embedding API → Qdrant (Docker)
                                                              ↑
Claude ← MCP server (mnemolith-mcp) ─────────────────────────┤
                                                              ↓
                                                   PostgreSQL (Docker)
                                                   (structured data)
                                                         ↑
                                                   CloudBeaver (Docker)
                                                   (web UI, port 8978)
```

## Documentation

- [Obsidian Setup](docs/obsidian-setup.md) — install Obsidian, set up Git backup
- [Getting Started](docs/getting-started.md) — install mnemolith, index, first search
- [Configuration](docs/configuration.md) — environment variables and options
- [Claude Integration](docs/claude-plugin.md) — MCP setup (Desktop & Code), plugin install, vault search, PostgreSQL, note creation
- [CLI Reference](docs/cli-reference.md) — all commands and flags
- [How It Works](docs/how-it-works.md) — architecture, parsing, chunking, embedding

## When to use PostgreSQL vs Obsidian

Mnemolith has two backends — use the right one for the job:

| Data type | Where | Example |
| --- | --- | --- |
| Structured: fields, states, numbers | PostgreSQL table | Portfolio holdings, habit tracker, todo list |
| Unstructured: prose, research, thinking | Obsidian note | Company research, meeting notes, journal |

**You don't need foreign keys between them.** Claude bridges both backends at query time. For example, if you track `ASML` in a PG `companies` table and write investment research in `Companies/ASML.md`, asking Claude "what's my thesis on ASML?" will pull from both sources automatically.

Resist the urge to add a `notes` table in PG — that's what your vault is for.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker (for Qdrant and PostgreSQL)
- An OpenAI API key

## Development

```bash
uv sync                              # install deps
docker compose up -d                                     # start Qdrant, PostgreSQL, CloudBeaver
uv run pytest -m "not integration and not pg_integration" # unit tests only
uv run pytest                                            # all tests (requires Qdrant + PostgreSQL)
```

## Project structure

```text
src/mnemolith/
    config.py        # Environment variable handling
    main.py          # CLI entry point (index, search, backup, restore)
    backup.py        # Backup and restore (pg_dump + Qdrant snapshots)
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

## Roadmap

- See [TODO](TODO.md)

## License

MIT
