# Roadmap

## Backups & Restore
- [ ] `mnemolith backup` CLI command (pg_dump + Qdrant snapshot API)
- [ ] `mnemolith restore <backup_dir>` CLI command
- [ ] Configurable backup directory (`BACKUP_DIR`, default `~/.mnemolith/backups/`)
- [ ] Timestamped backup folders with `pg_dump.sql` + `qdrant_snapshot.snapshot`

## Incremental Indexing
- [ ] Store `file_hash` (content hash) in Qdrant point payloads
- [ ] On index: detect new, modified, deleted files vs existing Qdrant state
- [ ] Only embed and upsert changed files, delete vectors for removed files
- [ ] `mnemolith index` incremental by default, `--full` flag for full rebuild
