"""
Memory API for Gonka.ai agent inference.

Provides long-term context storage for agents:
- Key-value storage with namespaces
- Basic semantic search using TF-IDF similarity
- Scoped per API key (agents can only access their own memory)

Stored in SQLite for persistence.
"""

import math
import re
import sqlite3
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEntry:
    key: str
    value: str
    namespace: str = "default"
    metadata: str = "{}"
    created_at: float = 0.0
    updated_at: float = 0.0


class MemoryStore:
    """Key-value memory with basic semantic search for agent long-term context."""

    def __init__(self, db_path: str = "data/memory.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    api_key TEXT NOT NULL,
                    namespace TEXT NOT NULL DEFAULT 'default',
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (api_key, namespace, key)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_ns
                ON memory (api_key, namespace)
            """)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def put(self, api_key: str, key: str, value: str,
            namespace: str = "default", metadata: str = "{}"):
        """Store or update a memory entry."""
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO memory (api_key, namespace, key, value, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (api_key, namespace, key)
                   DO UPDATE SET value = ?, metadata = ?, updated_at = ?""",
                (api_key, namespace, key, value, metadata, now, now,
                 value, metadata, now),
            )

    def get(self, api_key: str, key: str,
            namespace: str = "default") -> Optional[MemoryEntry]:
        """Get a memory entry by key."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT key, value, namespace, metadata, created_at, updated_at
                   FROM memory WHERE api_key = ? AND namespace = ? AND key = ?""",
                (api_key, namespace, key),
            ).fetchone()
            if row:
                return MemoryEntry(**dict(row))
            return None

    def delete(self, api_key: str, key: str, namespace: str = "default") -> bool:
        """Delete a memory entry."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE api_key = ? AND namespace = ? AND key = ?",
                (api_key, namespace, key),
            )
            return cursor.rowcount > 0

    def list_keys(self, api_key: str, namespace: str = "default") -> list[str]:
        """List all keys in a namespace."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key FROM memory WHERE api_key = ? AND namespace = ?",
                (api_key, namespace),
            ).fetchall()
            return [r["key"] for r in rows]

    def list_namespaces(self, api_key: str) -> list[str]:
        """List all namespaces for an API key."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT namespace FROM memory WHERE api_key = ?",
                (api_key,),
            ).fetchall()
            return [r["namespace"] for r in rows]

    def search(self, api_key: str, query: str,
               namespace: str = "default", limit: int = 10) -> list[dict]:
        """
        Basic semantic search using TF-IDF cosine similarity.

        For production, swap this with a vector store (FAISS, Qdrant, etc.).
        This implementation works for small-to-medium memory stores.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT key, value, namespace, metadata, created_at, updated_at
                   FROM memory WHERE api_key = ? AND namespace = ?""",
                (api_key, namespace),
            ).fetchall()

        if not rows:
            return []

        # Tokenize
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Calculate TF-IDF scores
        documents = [(dict(r), _tokenize(r["value"])) for r in rows]

        # IDF
        doc_count = len(documents)
        df = Counter()
        for _, tokens in documents:
            df.update(set(tokens))

        idf = {
            term: math.log((doc_count + 1) / (count + 1)) + 1
            for term, count in df.items()
        }

        # Score each document
        query_tf = Counter(query_tokens)
        query_vec = {t: tf * idf.get(t, 1.0) for t, tf in query_tf.items()}
        query_norm = math.sqrt(sum(v ** 2 for v in query_vec.values()))

        scored = []
        for row_dict, tokens in documents:
            doc_tf = Counter(tokens)
            doc_vec = {t: tf * idf.get(t, 1.0) for t, tf in doc_tf.items()}
            doc_norm = math.sqrt(sum(v ** 2 for v in doc_vec.values()))

            if query_norm == 0 or doc_norm == 0:
                continue

            dot_product = sum(
                query_vec.get(t, 0) * doc_vec.get(t, 0)
                for t in set(list(query_vec.keys()) + list(doc_vec.keys()))
            )
            similarity = dot_product / (query_norm * doc_norm)

            if similarity > 0:
                scored.append({
                    "key": row_dict["key"],
                    "value": row_dict["value"],
                    "namespace": row_dict["namespace"],
                    "similarity": round(similarity, 4),
                    "metadata": row_dict["metadata"],
                })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:limit]

    def clear_namespace(self, api_key: str, namespace: str = "default") -> int:
        """Delete all entries in a namespace."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE api_key = ? AND namespace = ?",
                (api_key, namespace),
            )
            return cursor.rowcount


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    # Remove very short tokens
    return [t for t in tokens if len(t) > 1]
