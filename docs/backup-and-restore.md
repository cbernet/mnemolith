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

The Qdrant snapshot is deleted from the Qdrant server once it's downloaded, so snapshots don't pile up inside the container. If a backup fails, its partial folder is removed.

### Retention

After each successful backup, older backups are pruned so only the 14 most recent are kept. Change the number in your `.env`, or set it to `0` to keep everything:

```bash
BACKUP_KEEP=30
```

Only timestamped folders (`YYYYMMDD_HHMMSS`) are pruned; anything else in the backup directory is left alone.

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

Add this line (runs daily at 3pm):

```cron
PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
0 15 * * * cd /path/to/mnemolith && /path/to/uv run mnemolith backup >> /tmp/mnemolith-backup.log 2>&1
```

- The `PATH` specification is needed so that cron can find docker, which is needed for the backup
- To find your `uv` path: `which uv`.

No separate cleanup job is needed: each run prunes old backups itself (see [Retention](#retention)).

### Verify it works

After the first automated run, check the log and the backup directory:

```bash
cat /tmp/mnemolith-backup.log
ls -lt ~/.mnemolith/backups/ | head -5
```
