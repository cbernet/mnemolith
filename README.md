# second-brain

Semantic search over an Obsidian vault using RAG, Qdrant, and MCP.

## Architecture

```text
Obsidian vault (.md) → Indexing script → Embedding API → Qdrant (Docker)
                                                              ↑
Claude Desktop ← MCP server (qdrant-mcp-server) ─────────────┘
```

- **Vector DB**: Qdrant in local Docker, persistent volume
- **Embedding**: configurable — OpenAI, Cohere, Voyage AI, or Ollama
- **MCP server**: `mhalder/qdrant-mcp-server` (TypeScript, multi-provider)
- **Indexing**: Python script with Obsidian-aware parsing (frontmatter, headings, wiki-links, tags)

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

## Project structure

```text
src/second_brain/
    config.py        # Environment variable handling
    main.py          # CLI entry point
tests/
docker-compose.yml
```
