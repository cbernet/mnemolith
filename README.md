# second-brain

Semantic search over an Obsidian vault using RAG, Qdrant, and MCP.

## Architecture

```text
Obsidian vault (.md) → Indexing script → Embedding API → Qdrant (Docker)
                                                              ↑
Claude ← MCP server (second-brain-mcp) ──────────────────────┘
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
uv run second-brain index /path/to/vault

# Search (for testing outside MCP)
uv run second-brain search "query text"
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
    "second-brain": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/second-brain", "second-brain-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/second-brain` with the actual path to this project. Make sure your `.env` file is configured (especially `OPENAI_API_KEY`) and that Qdrant is running.

The server exposes a `search` tool that Claude can call to find relevant notes in your vault.

See [.mcp.json](./.mcp.json) for an example. 

## Project structure

```text
src/second_brain/
    config.py        # Environment variable handling
    main.py          # CLI entry point
tests/
docker-compose.yml
```
