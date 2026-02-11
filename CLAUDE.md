# CLAUDE.md

## Project

second-brain — Python CLI that indexes an Obsidian vault into Qdrant (vector DB) for semantic search via RAG. Used as backend for an MCP server that gives Claude access to the vault.

## Tech stack

- Python 3.13, managed with uv
- Qdrant (Docker) for vector storage
- Embedding providers: OpenAI, Cohere
- pytest for tests

## Commands

```bash
uv sync              # install deps
uv run pytest        # run tests
uv run second-brain  # run CLI
docker compose up -d # start Qdrant
```

## Coding workflow

- write tests for your code
- run the tests when you're done editing
- feel free to propose updates to CLAUDE.md based on our discussion, but keep this file simple.

## Code style

- Clean, simple Python. No overengineering.
- Functions should be atomic.
- No unnecessary abstractions — a few similar lines are better than a premature helper.
- Type hints on function signatures, not on every local variable.
- No docstrings on obvious functions. Comments only where logic isn't self-evident.
- Flat module structure unless there's a clear reason to nest.
- Use stdlib when it's enough. Add a dependency only when it earns its place.

## Project structure

- `src/second_brain/` — source code
- `tests/` — pytest tests, mirror the src structure
- `pyproject.toml` — project config, dependencies, CLI entry points
- `docker-compose.yml` — Qdrant service

## Key decisions

- Qdrant over ChromaDB: real HNSW index, better long-term performance
- Embedding provider is swappable via env var — no code changes needed to switch
- Obsidian-aware parsing: handle frontmatter (YAML), `[[wiki-links]]`, `#tags`, heading structure
- Content is bilingual FR/EN — embedding model must handle both well
