"""
Usage Metering for Gonka.ai gateway.

Tracks token consumption per API key, per model, per time period.
Stores data in SQLite for persistence across restarts.
"""

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UsageRecord:
    api_key: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    timestamp: float
    session_id: Optional[str] = None


class UsageMeter:
    """Tracks and queries token usage per API key and model."""

    def __init__(self, db_path: str = "data/usage.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    session_id TEXT,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_key_time
                ON usage (api_key, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_model_time
                ON usage (model, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_session
                ON usage (session_id)
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

    def record(self, record: UsageRecord):
        """Record a usage event."""
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO usage
                   (api_key, model, input_tokens, output_tokens, total_tokens,
                    latency_ms, session_id, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.api_key,
                    record.model,
                    record.input_tokens,
                    record.output_tokens,
                    record.total_tokens,
                    record.latency_ms,
                    record.session_id,
                    record.timestamp,
                ),
            )

    def get_usage_by_key(self, api_key: str, since: float = 0) -> dict:
        """Get aggregated usage for an API key since timestamp."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as request_count,
                     COALESCE(SUM(input_tokens), 0) as total_input,
                     COALESCE(SUM(output_tokens), 0) as total_output,
                     COALESCE(SUM(total_tokens), 0) as total_tokens,
                     COALESCE(AVG(latency_ms), 0) as avg_latency_ms
                   FROM usage WHERE api_key = ? AND timestamp > ?""",
                (api_key, since),
            ).fetchone()
            return dict(row)

    def get_usage_by_model(self, model: str, since: float = 0) -> dict:
        """Get aggregated usage for a model since timestamp."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as request_count,
                     COALESCE(SUM(total_tokens), 0) as total_tokens,
                     COALESCE(AVG(latency_ms), 0) as avg_latency_ms
                   FROM usage WHERE model = ? AND timestamp > ?""",
                (model, since),
            ).fetchone()
            return dict(row)

    def get_usage_by_session(self, session_id: str) -> dict:
        """Get aggregated usage for a session."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as request_count,
                     COALESCE(SUM(input_tokens), 0) as total_input,
                     COALESCE(SUM(output_tokens), 0) as total_output,
                     COALESCE(SUM(total_tokens), 0) as total_tokens,
                     COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                     MIN(timestamp) as first_request,
                     MAX(timestamp) as last_request
                   FROM usage WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
            return dict(row)

    def get_usage_breakdown(self, api_key: str, since: float = 0) -> list[dict]:
        """Get per-model usage breakdown for an API key."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT
                     model,
                     COUNT(*) as request_count,
                     SUM(input_tokens) as total_input,
                     SUM(output_tokens) as total_output,
                     SUM(total_tokens) as total_tokens,
                     AVG(latency_ms) as avg_latency_ms
                   FROM usage
                   WHERE api_key = ? AND timestamp > ?
                   GROUP BY model""",
                (api_key, since),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_global_stats(self, since: float = 0) -> dict:
        """Get global usage statistics."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as total_requests,
                     COUNT(DISTINCT api_key) as active_keys,
                     COUNT(DISTINCT model) as active_models,
                     COALESCE(SUM(total_tokens), 0) as total_tokens,
                     COALESCE(AVG(latency_ms), 0) as avg_latency_ms
                   FROM usage WHERE timestamp > ?""",
                (since,),
            ).fetchone()
            return dict(row)
