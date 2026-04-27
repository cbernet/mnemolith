# CLI Reference

Mnemolith provides four commands: `index`, `search`, `backup`, and `restore`.

## `mnemolith index`

Parse, chunk, embed, and store your vault in the configured vector store. **Incremental by default** — only new or modified files are re-embedded; vectors for deleted files are evicted.

```bash
uv run mnemolith index [vault_path] [--full]
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `vault_path` | Path to the Obsidian vault | `OBSIDIAN_VAULT_PATH` env var |
| `--full` | Drop the collection and rebuild from scratch | off |

If `vault_path` is provided, it takes precedence over the environment variable.

**What it does (incremental run):**

1. Scans all `.md` files in the vault recursively and computes a content hash for each
2. Compares hashes against the `vault_index_state` table in PostgreSQL to find added, modified, and deleted files
3. Evicts vectors for deleted and modified files via `delete_by_paths`
4. Embeds and upserts only the chunks of added/modified files
5. Updates `vault_index_state` to reflect the new vault snapshot

**What `--full` does:**

Drops the collection, resets the state table, and rebuilds everything from scratch. Use this when:

- Migrating from a pre-incremental version of mnemolith (the first run after upgrade refuses incremental and asks you to run `--full` once).
- The chunking logic changes (mnemolith bumps a `SCHEMA_VERSION` constant in this case, which auto-invalidates state — but `--full` is the safe override).
- You want a clean slate.

**Example:**

```bash
# Incremental (default) — fast, only embeds what changed
uv run mnemolith index

# Full rebuild — re-embeds everything
uv run mnemolith index --full

# Explicit vault path
uv run mnemolith index ~/Obsidian\ Vault
```

**Notes:**

- Re-run after adding, editing, or deleting notes to keep the index up to date — the diff is fast, only changed files are re-embedded.
- The deprecated `--clean` flag still works as an alias for `--full` but will be removed in a future release.
- Renaming a file is treated as delete + add — the renamed file's chunks are re-embedded even though content is unchanged.

## `mnemolith search`

Query the indexed vault with natural language.

```bash
uv run mnemolith search "your query" [--limit N] [--score-threshold N]
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `query` | Natural language search query | *(required)* |
| `--limit` | Maximum number of results (1–50) | `5` |
| `--score-threshold` | Minimum similarity score (0–1) to include a result | *(none — all results returned)* |

**Example:**

```bash
# Default 5 results
uv run mnemolith search "weekly planning methods"

# Get more results
uv run mnemolith search "recipes with lentils" --limit 10

# Only results with high relevance
uv run mnemolith search "weekly planning methods" --score-threshold 0.5
```

**Output format:**

Results are printed from lowest to highest relevance (best match last), so the most relevant result is at the bottom of your terminal:

```
----------------------------------------------------------------------

[0.432] cooking/lentil-soup.md: lentil-soup > Ingredients

Red lentils, cumin, onion, garlic...

----------------------------------------------------------------------

[0.687] meal-planning/weekly-prep.md: weekly-prep > Monday

Batch cook lentils for the week...
```

Each result shows:

- **Score** — cosine similarity (0 to 1, higher is better)
- **Path** — file path relative to the vault root
- **Title** — filename without extension
- **Heading** — the `##` section heading, if the chunk came from a subsection
- **Content** — the matching text

## `mnemolith backup`

Create a full backup of both PostgreSQL and Qdrant data.

```bash
uv run mnemolith backup [--dir DIR]
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--dir` | Directory to store the backup | `BACKUP_DIR` env var, or `~/.mnemolith/backups/` |

**What it does:**

1. Creates a timestamped subfolder (e.g. `20260315_143022/`) inside the backup directory
2. Runs `pg_dump` inside the Docker PostgreSQL container, saves the output as `pg_dump.sql`
3. Creates a Qdrant collection snapshot via the API, downloads it as `qdrant_snapshot.snapshot`

**Example:**

```bash
# Default location (~/.mnemolith/backups/)
uv run mnemolith backup

# Custom directory
uv run mnemolith backup --dir ~/my-backups
```

**Notes:**

- Requires Docker to be running with the PostgreSQL and Qdrant containers up (`docker compose up -d`)
- Each backup is a self-contained folder with both files — safe to copy, move, or archive

## `mnemolith restore`

Restore both PostgreSQL and Qdrant data from a backup folder.

```bash
uv run mnemolith restore <backup_path>
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `backup_path` | Path to a timestamped backup folder | *(required)* |

**What it does:**

1. Reads `pg_dump.sql` from the backup folder and pipes it into `psql` inside the Docker container
2. Uploads `qdrant_snapshot.snapshot` to the Qdrant snapshot restore API

**Example:**

```bash
uv run mnemolith restore ~/.mnemolith/backups/20260315_143022
```

**Notes:**

- Restore is destructive — it overwrites existing data in both PostgreSQL and Qdrant
- Requires Docker to be running with the PostgreSQL and Qdrant containers up
