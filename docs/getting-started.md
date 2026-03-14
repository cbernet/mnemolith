# Getting Started

Get from zero to a working semantic search over your Obsidian vault in about 10 minutes.

## Prerequisites

- An Obsidian vault (see [Obsidian Setup](obsidian-setup.md) if you need one)
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://docs.docker.com/get-docker/) (for Qdrant)
- An OpenAI API key

## 1. Clone and install

```bash
git clone https://github.com/cbernet/mnemolith.git
cd mnemolith
uv sync
```

## 2. Configure environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OBSIDIAN_VAULT_PATH=/absolute/path/to/your/vault
OPENAI_API_KEY=sk-...
```

See [Configuration](configuration.md) for all available options.

## 3. Start Qdrant

```bash
docker compose up -d
```

This starts a local Qdrant instance on port 6333 with persistent storage. Your indexed data survives restarts.

## 4. Index your vault

```bash
uv run mnemolith index
```

This parses all markdown files in your vault, chunks them by `##` headings, embeds them via OpenAI, and stores the vectors in Qdrant.

You can also pass the vault path directly instead of relying on the env var:

```bash
uv run mnemolith index /path/to/vault
```

## 5. Search

```bash
uv run mnemolith search "how to make sourdough bread"
```

Results are ranked by semantic similarity, with scores, file paths, and matching content displayed.

## What's next?

- [MCP Setup](mcp-setup.md) — let Claude search your vault directly
- [Claude Code Plugin](claude-plugin.md) — install mnemolith as a Claude Code plugin for search + note creation
- [CLI Reference](cli-reference.md) — all commands and options
