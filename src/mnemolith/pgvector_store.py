from psycopg import errors as pg_errors
from psycopg.sql import SQL, Identifier
from psycopg_pool import ConnectionPool

from mnemolith.embeddings import SparseVector as EmbSparseVector
from mnemolith.parser import Document, chunk_id
from mnemolith.vector_store import CollectionNotFoundError


class PgvectorStore:
    def __init__(self, pool: ConnectionPool | None = None):
        if pool is None:
            from mnemolith.config import get_postgres_dsn
            pool = ConnectionPool(get_postgres_dsn(), open=True)
        self.pool = pool

    def ensure_collection(self, name: str, dimension: int, sparse: bool = False) -> None:
        with self.pool.connection() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id UUID PRIMARY KEY,
                    embedding vector({}),
                    path TEXT,
                    title TEXT,
                    content TEXT,
                    tags TEXT[],
                    links TEXT[],
                    heading TEXT
                )
            """).format(Identifier(name), SQL(str(dimension))))
            conn.commit()

    def delete_collection(self, name: str) -> None:
        with self.pool.connection() as conn:
            conn.execute(SQL("DROP TABLE IF EXISTS {}").format(Identifier(name)))
            conn.commit()

    def delete_by_paths(self, collection: str, paths: list[str]) -> None:
        if not paths:
            return
        with self.pool.connection() as conn:
            conn.execute(
                SQL("DELETE FROM {} WHERE path = ANY(%s)").format(Identifier(collection)),
                (paths,),
            )
            conn.commit()

    def upsert_documents(
        self,
        collection: str,
        documents: list[Document],
        vectors: list[list[float]],
        sparse_vectors: list[EmbSparseVector] | None = None,
    ) -> None:
        if sparse_vectors is not None:
            raise NotImplementedError("pgvector backend does not support sparse vectors")
        if not documents:
            return
        rows = [
            (
                chunk_id(doc.path, doc.chunk_index),
                "[" + ",".join(str(v) for v in vector) + "]",
                doc.path, doc.title, doc.content,
                doc.tags, doc.links, doc.heading,
            )
            for doc, vector in zip(documents, vectors)
        ]
        sql = SQL("""
            INSERT INTO {} (id, embedding, path, title, content, tags, links, heading)
            VALUES (%s, %s::vector, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                path = EXCLUDED.path,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                tags = EXCLUDED.tags,
                links = EXCLUDED.links,
                heading = EXCLUDED.heading
        """).format(Identifier(collection))
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(sql, rows)

    def count_points(self, collection: str) -> int:
        try:
            with self.pool.connection() as conn:
                row = conn.execute(
                    SQL("SELECT COUNT(*) FROM {}").format(Identifier(collection))
                ).fetchone()
                return int(row[0]) if row else 0
        except pg_errors.UndefinedTable:
            return 0

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
        sparse_query: EmbSparseVector | None = None,
    ) -> list[dict]:
        if sparse_query is not None:
            raise NotImplementedError("pgvector backend does not support sparse search")
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
        try:
            with self.pool.connection() as conn:
                query = SQL("""
                    SELECT path, title, content, tags, links, heading,
                           1 - (embedding <=> %s::vector) AS score
                    FROM {}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """).format(Identifier(collection))
                rows = conn.execute(query, (vector_str, vector_str, limit)).fetchall()
        except pg_errors.UndefinedTable as e:
            raise CollectionNotFoundError(collection) from e

        results = []
        for row in rows:
            score = float(row[6])
            if score_threshold is not None and score < score_threshold:
                continue
            results.append({
                "path": row[0],
                "title": row[1],
                "content": row[2],
                "tags": row[3],
                "links": row[4],
                "heading": row[5],
                "score": score,
            })
        return results
