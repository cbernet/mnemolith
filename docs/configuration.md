# Configuration

Mnemolith is configured through environment variables. You can set them in a `.env` file at the project root or export them in your shell. Shell values take precedence over `.env`.

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `OBSIDIAN_VAULT_PATH` | Absolute path to your Obsidian vault | *(required)* |
| `OPENAI_API_KEY` | OpenAI API key (required when using OpenAI embeddings) | — |
| `EMBEDDING_PROVIDER` | Embedding provider to use (`openai`) | `openai` |
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` |
| `COLLECTION_NAME` | Qdrant collection name | `obsidian` |
| `POSTGRES_DSN` | PostgreSQL connection string | `postgresql://mnemolith:mnemolith@localhost:5432/mnemolith` |

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

## Qdrant

By default, mnemolith connects to `http://localhost:6333`, which matches the `docker-compose.yml` included in the project.

For a remote Qdrant instance:

```bash
QDRANT_URL=https://your-qdrant-host:6333
```

## Collection name

The default collection name is `obsidian`. Change it if you want to index multiple vaults separately:

```bash
COLLECTION_NAME=work-vault
```

Switching collection names lets you keep separate indexes without conflicts — each `mnemolith index` run writes to the configured collection.

## PostgreSQL

The PostgreSQL backend stores structured personal data (todo lists, habits, tracking). The default DSN matches the `docker-compose.yml` included in the project.

For a custom PostgreSQL instance:

```bash
POSTGRES_DSN=postgresql://user:password@host:5432/dbname
```

## Example `.env` file

```bash
OBSIDIAN_VAULT_PATH=/Users/yourname/Obsidian Vault
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=obsidian
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
POSTGRES_DSN=postgresql://mnemolith:mnemolith@localhost:5432/mnemolith
```
