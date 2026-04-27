# Roadmap

## Backups & Restore

- [x] `mnemolith backup` CLI command (pg_dump + Qdrant snapshot API)
- [x] `mnemolith restore <backup_dir>` CLI command
- [x] Configurable backup directory (`BACKUP_DIR`, default `~/.mnemolith/backups/`)
- [x] Timestamped backup folders with `pg_dump.sql` + `qdrant_snapshot.snapshot`

## Incremental Indexing

- [x] Per-file content hash tracked in `vault_index_state` (PostgreSQL)
- [x] On index: detect new, modified, deleted files vs stored state
- [x] Only embed and upsert changed files, delete vectors for removed files
- [x] `mnemolith index` incremental by default, `--full` flag for full rebuild
- [x] Vectors for deleted notes are evicted via `delete_by_paths`
- [ ] Rename optimization: detect renames by hash and update payloads in place (skip re-embed)

## Maintenance

- [x] back up procedure test
- [ ] separate docker compose stack for integration tests
- [x] cronjobs for backups

## RAG Improvements

- [x] Score threshold to filter irrelevant results
- [ ] Reranking with Cohere cross-encoder (retrieve top-20, rerank to top-5)
- [x] Hybrid search (BM25 sparse + dense vectors in Qdrant)
- [ ] Metadata filtering (tags, folders) at search time

## VectorStore abstraction

- [X] pgvector added, user can choose pgvector or qdrant
