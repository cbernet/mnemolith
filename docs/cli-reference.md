# CLI Reference

Mnemolith provides two commands: `index` and `search`.

## `mnemolith index`

Parse, chunk, embed, and store your vault in Qdrant.

```bash
uv run mnemolith index [vault_path]
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `vault_path` | Path to the Obsidian vault | `OBSIDIAN_VAULT_PATH` env var |

If `vault_path` is provided, it takes precedence over the environment variable.

**What it does:**

1. Scans all `.md` files in the vault recursively
2. Parses each file: extracts frontmatter, wiki-links, tags, and content
3. Splits documents into chunks at `##` heading boundaries
4. Embeds each chunk via the configured embedding provider
5. Upserts all vectors into Qdrant (creates the collection if it doesn't exist)

**Example:**

```bash
# Using env var
uv run mnemolith index

# Explicit path
uv run mnemolith index ~/Obsidian\ Vault
```

**Notes:**

- Indexing upserts vectors using sequential IDs — existing points at the same IDs are replaced, but points at IDs that no longer exist (e.g. from deleted notes) are **not** removed
- To fully reset the index, delete the Qdrant collection and re-run `index`
- Re-run after adding or editing notes to keep the index up to date

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
