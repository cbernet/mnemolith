# How It Works

This page explains mnemolith's internals: how your Obsidian notes go from markdown files to searchable vectors.

## Architecture

```
Obsidian vault (.md) → Parser → Chunker → Embedder → Qdrant
                                                        ↑
Claude ← MCP server ───────────────────────────────────┤
                                                        ↓
                                                   PostgreSQL
                                                   (structured data)
```

## Parsing

Each `.md` file in the vault is parsed with Obsidian-specific handling:

- **Frontmatter** — YAML between `---` fences is extracted as metadata (not embedded as content)
- **Wiki-links** — `[[link targets]]` are extracted and stored as metadata
- **Tags** — both frontmatter `tags:` and inline `#tags` are collected
- **Title** — derived from the filename (not from any H1 heading in the content)

Tags are enriched with the filename words (split on `-` and `_`) and the folder path components. This means a file at `cooking/lentil-soup.md` automatically gets tags like `cooking`, `lentil`, `soup` — improving search recall without manual tagging.

## Chunking

Documents are split at `##` (H2) heading boundaries. Each chunk becomes a separate vector in Qdrant.

For a file like:

```markdown
---
tags: [recipe]
---
Introduction paragraph.

## Ingredients
Flour, sugar, eggs.

## Steps
Mix and bake.
```

This produces three chunks:

1. Introduction paragraph (no heading)
2. "Ingredients" section
3. "Steps" section

Each chunk retains the original document's metadata (path, title, tags, links) so search results can always trace back to the source.

If a document has no `##` headings, it's stored as a single chunk.

## Embedding

Before embedding, each chunk is formatted into a text block that includes context:

```
# Document Title
## Section Heading

#tag1 #tag2 #cooking #lentil #soup

The actual content of the chunk...
```

This gives the embedding model more context than the raw content alone, improving search quality — especially for short chunks.

The embedding is done via OpenAI's `text-embedding-3-small` model (1536 dimensions). The model handles both French and English, which matters since the vault is bilingual.

Chunks are embedded in batch for efficiency.

## Vector storage

Vectors are stored in Qdrant using cosine similarity. Each point contains:

- **Vector** — the embedding
- **Payload** — `path`, `title`, `content`, `tags`, `links`, `heading`

The collection is created automatically on first index. Each point is keyed by a stable UUID derived from `(path, chunk_index)` so re-indexing the same chunk overwrites it idempotently.

Indexing is **incremental by default**: a `vault_index_state` table in PostgreSQL records a SHA-256 content hash per source file. On each `mnemolith index` run, mnemolith diffs the vault against this state, embeds only the new and modified files, and evicts vectors for deleted files. Run `mnemolith index --full` to drop the collection and rebuild from scratch.

## Search

When you search (via CLI or MCP):

1. Your query is embedded with the same model
2. Qdrant finds the nearest vectors by cosine similarity
3. Results are returned with their payload and similarity score

The MCP server wraps this in a tool that Claude can call, so Claude can search your vault mid-conversation without you having to run CLI commands.

## PostgreSQL backend

Alongside the vector store for unstructured notes, mnemolith provides a PostgreSQL backend for structured personal data — things like todo lists, habit tracking, or any tabular information.

The MCP server exposes five PostgreSQL tools:

- **pg_list_tables** — discover available tables
- **pg_describe_table** — inspect a table's columns and types
- **pg_create_table** — execute DDL (CREATE/ALTER/DROP TABLE only — other statements are rejected for safety)
- **pg_query** — run read-only SELECT queries
- **pg_mutate** — run INSERT/UPDATE/DELETE statements

Claude can use these tools to create tables, insert data, and query structured information on your behalf. The DDL tool is restricted to table-level operations to prevent dangerous statements like `DROP DATABASE` or `COPY ... TO PROGRAM`.
