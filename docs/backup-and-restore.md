# Backup & Restore

Mnemolith stores data in two places: **PostgreSQL** (structured data + pgvector embeddings if used) and optionally **Qdrant** (vector embeddings). Both are backed up and restored with a single command.

Your Obsidian vault itself is not covered here — it's plain files, best backed up with Git (see [Obsidian Setup](obsidian-setup.md)).

## Prerequisites

Docker must be running with the services up:

```bash
docker compose up -d
```

## Backup

```bash
uv run mnemolith backup
```

This creates a timestamped folder (e.g. `~/.mnemolith/backups/20260315_143022/`) containing:

| File | What it contains | When created |
|---|---|---|
| `pg_dump.sql` | Full PostgreSQL dump (structured data + pgvector tables if applicable) | Always |
| `qdrant_snapshot.snapshot` | Qdrant collection snapshot | Only when `VECTOR_BACKEND=qdrant` |

With `VECTOR_BACKEND=pgvector`, a single `pg_dump.sql` captures everything — no separate vector snapshot is needed.

### Custom backup directory

```bash
uv run mnemolith backup --dir ~/my-backups
```

Or set it permanently in your `.env`:

```bash
BACKUP_DIR=/path/to/backups
```

Default: `~/.mnemolith/backups/`.

## Restore

```bash
uv run mnemolith restore ~/.mnemolith/backups/20260315_143022
```

This restores both PostgreSQL and Qdrant (if applicable) from the given backup folder.

**Warning:** restore is destructive — it overwrites existing data in both PostgreSQL and Qdrant.

## Automating backups with cron

A daily backup is a good default. Add a cron job:

```bash
crontab -e
```

Add this line (runs daily at 2 AM):

```cron
PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
0 2 * * * cd /path/to/mnemolith && /path/to/uv run mnemolith backup >> /tmp/mnemolith-backup.log 2>&1
```

- The `PATH` specification is needed so that cron can find docker, which is needed for the backup
- To find your `uv` path: `which uv`.

### Cleanup old backups

Each backup is a self-contained folder. To keep only the last 30 days, add another cron entry:

```cron
0 3 * * * find ~/.mnemolith/backups -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
```

### Verify it works

After the first automated run, check the log and the backup directory:

```bash
cat /tmp/mnemolith-backup.log
ls -lt ~/.mnemolith/backups/ | head -5
```
