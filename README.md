# mnemolith

*Your thoughts, carved in stone.* Semantic search over an Obsidian vault using RAG, Qdrant, and MCP.

## Architecture

```text
Obsidian vault (.md) → Indexing script → Embedding API → Qdrant (Docker)
                                                              ↑
Claude ← MCP server (mnemolith-mcp) ─────────────────────────┘
```

- **Vector DB**: Qdrant in local Docker, persistent volume
- **Embedding**: configurable — OpenAI or Cohere
- **MCP server**: built-in, uses stdio transport
- **Indexing**: Python CLI with Obsidian-aware parsing (frontmatter, headings, wiki-links, tags)

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker (for Qdrant)

## Setup

```bash
# Install dependencies
uv sync

# Start Qdrant (required for indexing, search, and integration tests)
docker compose up -d

# Run unit tests only
uv run pytest -m "not integration"

# Run all tests (requires Qdrant running)
uv run pytest
```

## Usage

```bash
# Index your vault
uv run mnemolith index /path/to/vault

# Search (for testing outside MCP)
uv run mnemolith search "query text"
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Environment variables (set via `.env` or shell — shell values take precedence):

| Variable             | Description                            | Default                  |
| -------------------- | -------------------------------------- | ------------------------ |
| `OBSIDIAN_VAULT_PATH`| Absolute path to your Obsidian vault   | — (required)             |
| `QDRANT_URL`         | Qdrant server URL                      | `http://localhost:6333`  |
| `EMBEDDING_PROVIDER` | `openai`, `cohere`                     | `openai`                 |
| `OPENAI_API_KEY`     | OpenAI API key (if using OpenAI)       | —                        |
| `COHERE_API_KEY`     | Cohere API key (if using Cohere)       | —                        |
| `COLLECTION_NAME`    | Qdrant collection name                 | `obsidian`               |

NOTE: Cohere not implemented yet !

## MCP Server

The project includes an MCP server that lets Claude search your vault via semantic search.

Add the following to your MCP configuration:

```json
{
  "mcpServers": {
    "mnemolith": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mnemolith", "mnemolith-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/mnemolith` with the actual path to this project. Make sure your `.env` file is configured (especially `OPENAI_API_KEY`) and that Qdrant is running.

The server exposes a `search` tool that Claude can call to find relevant notes in your vault.

See [.mcp.json](./.mcp.json) for an example.

## Claude Code Plugin

This repo is also a **Claude Code plugin** that bundles:

- **MCP server** — semantic search over your vault (works in both Claude Code and Claude Desktop)
- **Obsidian notes skill** — create/edit notes in your vault (Claude Code only)

### Install as a plugin (Claude Code)

```bash
# From a local clone
claude plugin install /path/to/mnemolith
```

The plugin auto-registers the MCP server and the `obsidian-notes` skill. It works from private repos and local clones.

> **Note:** Skills are a Claude Code concept — they don't work in Claude Desktop. The MCP server works in both.

### Required environment variable

Set `OBSIDIAN_VAULT_PATH` so the skill and indexer know where your vault is:

```bash
export OBSIDIAN_VAULT_PATH="$HOME/Obsidian Vault"
```

## Project structure

```text
src/mnemolith/
    config.py        # Environment variable handling
    main.py          # CLI entry point (index, search commands)
    parser.py        # Obsidian-aware markdown parser (frontmatter, wiki-links, tags)
    embeddings.py    # Embedding provider abstraction (OpenAI, Cohere)
    indexer.py       # Vault indexing pipeline
    qdrant_store.py  # Qdrant vector store client
    mcp_server.py    # MCP server exposing search tool to Claude
tests/
    conftest.py
    test_config.py
    test_parser.py
    test_embeddings.py
    test_indexer.py
    test_mcp_server.py
    test_main.py
    test_integration.py
    fixtures/vault/  # Sample markdown notes for testing
.claude-plugin/
    plugin.json      # Claude Code plugin manifest
skills/
    obsidian-notes/
        SKILL.md     # Note creation skill for Claude Code
docker-compose.yml
```
