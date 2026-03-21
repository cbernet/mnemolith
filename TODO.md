# Roadmap

## Backups & Restore

- [x] `mnemolith backup` CLI command (pg_dump + Qdrant snapshot API)
- [x] `mnemolith restore <backup_dir>` CLI command
- [x] Configurable backup directory (`BACKUP_DIR`, default `~/.mnemolith/backups/`)
- [x] Timestamped backup folders with `pg_dump.sql` + `qdrant_snapshot.snapshot`

## Incremental Indexing

- [ ] Store `file_hash` (content hash) in Qdrant point payloads
- [ ] On index: detect new, modified, deleted files vs existing Qdrant state
- [ ] Only embed and upsert changed files, delete vectors for removed files
- [ ] `mnemolith index` incremental by default, `--full` flag for full rebuild
- [ ] make sure vectors corresponding to deleted notes are removed

## RAG Improvements

- [x] Score threshold to filter irrelevant results
- [ ] Reranking with Cohere cross-encoder (retrieve top-20, rerank to top-5)
- [ ] Hybrid search (BM25 sparse + dense vectors in Qdrant)
- [ ] Metadata filtering (tags, folders) at search time

## VectorStore abstraction

- [X] pgvector
- [ ] refacto : backup stuff in VectorStore ?
- [ ] refacto : subpackages ?  
- [ ] will the llm know it can search directly with a single select if pgvector backend is used ?
- [ ] custom exceptions for VectorStore. which exceptions were used before ? are they all covered by CollectionNotFound ? 
- [ ] integration tests for pgvector vectors and combined searches
- [ ] update README