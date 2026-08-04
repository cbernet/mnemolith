# Configuration

Mnemolith is configured through environment variables. You can set them in a `.env` file at the project root or export them in your shell. Shell values take precedence over `.env`.

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `OBSIDIAN_VAULT_PATH` | Absolute path to your Obsidian vault | *(required)* |
| `OPENAI_API_KEY` | OpenAI API key (required when using OpenAI embeddings) | — |
| `EMBEDDING_PROVIDER` | Embedding provider to use (`openai`) | *(required)* |
| `VECTOR_BACKEND` | Vector store backend (`qdrant` or `pgvector`) | `qdrant` |
| `QDRANT_URL` | Qdrant server URL (only when `VECTOR_BACKEND=qdrant`) | *(required for Qdrant)* |
| `QDRANT_API_KEY` | Qdrant API key for authentication | *(optional — no auth if unset)* |
| `COLLECTION_NAME` | Collection/table name for vector storage | *(required)* |
| `POSTGRES_DSN` | PostgreSQL connection string (overrides component variables below) | — |
| `POSTGRES_USER` | PostgreSQL user | *(required if no DSN)* |
| `POSTGRES_PASSWORD` | PostgreSQL password | *(required if no DSN)* |
| `POSTGRES_DB` | PostgreSQL database name | *(required if no DSN)* |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `BACKUP_DIR` | Directory for backups | `~/.mnemolith/backups/` |
| `SPARSE_SEARCH_ENABLED` | Hybrid dense + BM25 sparse search (**Qdrant only**) | `true` |
| `TIKTOKEN_CACHE_DIR` | Where the tokenizer vocab is cached | *(a temp dir)* |

The `.env.example` file provides sensible values for local development — copy it to `.env` and fill in your secrets.

## Vault path

The vault path must be absolute. Mnemolith uses it for both indexing and the MCP server.

```bash
OBSIDIAN_VAULT_PATH=/Users/yourname/Obsidian Vault
```

If the path contains spaces, no quoting is needed in the `.env` file — `python-dotenv` handles it. In your shell, quote it:

```bash
export OBSIDIAN_VAULT_PATH="$HOME/Obsidian Vault"
```

## Embedding provider

Currently only OpenAI is implemented. The model used is `text-embedding-3-small` (1536 dimensions). It handles both English and French well.

To use it, set your API key:

```bash
OPENAI_API_KEY=sk-...
```

## Vector store backend

Mnemolith supports two vector store backends. Set `VECTOR_BACKEND` to choose:

### pgvector (recommended for simplicity)

Stores vectors directly in PostgreSQL using the [pgvector](https://github.com/pgvector/pgvector) extension. No extra service needed — everything lives in one database.

```bash
VECTOR_BACKEND=pgvector
COLLECTION_NAME=obsidian
```

The Docker Compose file uses the `pgvector/pgvector:pg17` image, which includes the extension out of the box.

### Qdrant (default)

Uses a dedicated [Qdrant](https://qdrant.tech) vector database with HNSW indexing.

```bash
VECTOR_BACKEND=qdrant
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=obsidian
```

For a remote Qdrant instance:

```bash
QDRANT_URL=https://your-qdrant-host:6333
```

If your Qdrant instance requires authentication:

```bash
QDRANT_API_KEY=your-secret-key
```

## Sparse search

`SPARSE_SEARCH_ENABLED` adds a BM25 sparse vector alongside the dense embedding, so keyword matches complement semantic ones. It defaults to **on**.

It only works with Qdrant. The pgvector backend raises `NotImplementedError` for sparse vectors, so the two must be paired deliberately:

```bash
VECTOR_BACKEND=pgvector
SPARSE_SEARCH_ENABLED=false   # required: pgvector has no sparse support
```

```bash
VECTOR_BACKEND=qdrant
SPARSE_SEARCH_ENABLED=true    # default
```

Switching this value changes the collection schema, so run `mnemolith index --full` afterwards.

## Tokenizer cache

Mnemolith counts tokens with [tiktoken](https://github.com/openai/tiktoken) to keep every chunk under the embedding model's input limit. The vocabulary file is downloaded once and cached.

By default that cache lives in a temporary directory, which macOS purges periodically — so a scheduled indexing job re-downloads the vocab from time to time. For cron, point it somewhere persistent:

```bash
TIKTOKEN_CACHE_DIR=~/.cache/tiktoken
```

## Collection name

The `.env.example` uses `obsidian`. Change it if you want to index multiple vaults separately:

```bash
COLLECTION_NAME=work-vault
```

Switching collection names lets you keep separate indexes without conflicts — each `mnemolith index` run writes to the configured collection.

## PostgreSQL

The PostgreSQL backend stores structured personal data (todo lists, habits, tracking).

You can configure it in two ways:

**Option 1 — Component variables** (recommended for local dev, matches docker-compose.yml):

```bash
POSTGRES_USER=mnemolith
POSTGRES_PASSWORD=your-password
POSTGRES_DB=mnemolith
# POSTGRES_HOST=localhost   # optional, defaults to localhost
# POSTGRES_PORT=5432        # optional, defaults to 5432
```

**Option 2 — Direct DSN** (overrides all component variables):

```bash
POSTGRES_DSN=postgresql://user:password@host:5432/dbname
```

## Example `.env` file

```bash
OBSIDIAN_VAULT_PATH=/Users/yourname/Obsidian Vault
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
COLLECTION_NAME=obsidian
POSTGRES_USER=mnemolith
POSTGRES_PASSWORD=change-me-to-a-strong-password
POSTGRES_DB=mnemolith

# Vector backend — pick one:
VECTOR_BACKEND=pgvector           # vectors in PostgreSQL (simple)
SPARSE_SEARCH_ENABLED=false       # required with pgvector (no sparse support)
# VECTOR_BACKEND=qdrant           # dedicated vector DB
# QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=change-me-to-a-strong-secret
```
