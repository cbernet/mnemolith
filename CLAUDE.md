# CLAUDE.md

## Project

second-brain — Python CLI that indexes an Obsidian vault into Qdrant (vector DB) for semantic search via RAG. Used as backend for an MCP server that gives Claude access to the vault.

The Obsidian vault path is configured via the `OBSIDIAN_VAULT_PATH` environment variable.

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

## test-driven development

- start in plan mode when I ask you to do something
- write new unit tests first
- run the tests to make sure they fail
- write the code
- make sure the tests pass by editing the code 
- run the tests when you're done editing

When you're working on a new functionality, if existing tests fail, don't modify the tests, modify the code to make sure tests pass. 

Do not overdo tests :

- group tests that can be grouped together
- don't test trivial things 

## Managing our interactions

- feel free to disagree with me (even strongly), I'm not that sensitive and I don't know everything. 
- propose updates to CLAUDE.md based on our discussion, but keep this file simple.
- propose updates to the README.md

## Code style

- Clean, simple Python. No overengineering.
- Functions should be atomic.
- No unnecessary abstractions — a few similar lines are better than a premature helper.
- Type hints on function signatures, not on every local variable.
- No docstrings on obvious functions. Comments only where logic isn't self-evident.
- Flat module structure unless there's a clear reason to nest.
- Use stdlib when it's enough. Add a dependency only when it earns its place.

## Project structure

- `src/second_brain/` — source code (`config.py` for env var handling)
- `tests/` — pytest tests, mirror the src structure
- `pyproject.toml` — project config, dependencies, CLI entry points
- `docker-compose.yml` — Qdrant service

## Key decisions

- Qdrant over ChromaDB: real HNSW index, better long-term performance
- Embedding provider is swappable via env var — no code changes needed to switch
- Obsidian-aware parsing: handle frontmatter (YAML), `[[wiki-links]]`, `#tags`, heading structure
- Content is bilingual FR/EN — embedding model must handle both well
