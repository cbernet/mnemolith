from psycopg.sql import SQL, Identifier
from psycopg_pool import ConnectionPool

from mnemolith.parser import Document
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
                    id SERIAL PRIMARY KEY,
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

    def upsert_documents(
        self,
        collection: str,
        documents: list[Document],
        vectors: list[list[float]],
        sparse_vectors=None,
    ) -> None:
        with self.pool.connection() as conn:
            # Clear existing data and insert fresh (reindex semantics)
            conn.execute(SQL("DELETE FROM {}").format(Identifier(collection)))
            for i, (doc, vector) in enumerate(zip(documents, vectors)):
                vector_str = "[" + ",".join(str(v) for v in vector) + "]"
                conn.execute(
                    SQL("""
                        INSERT INTO {} (id, embedding, path, title, content, tags, links, heading)
                        VALUES (%s, %s::vector, %s, %s, %s, %s, %s, %s)
                    """).format(Identifier(collection)),
                    (i, vector_str, doc.path, doc.title, doc.content,
                     doc.tags, doc.links, doc.heading),
                )
            conn.commit()

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
        sparse_query=None,
    ) -> list[dict]:
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
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg:
                raise CollectionNotFoundError(collection) from e
            raise

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
