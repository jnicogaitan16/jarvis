"""LLM Usage Tracking — registro de consumo en SQLite."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jarvis.llm.base import LLMResponse

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS llm_usage (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    project     TEXT NOT NULL,
    agent_id    TEXT,
    task_type   TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens  INTEGER DEFAULT 0,
    cost_usd    REAL DEFAULT 0.0,
    latency_ms  INTEGER DEFAULT 0,
    success     INTEGER DEFAULT 1,
    error       TEXT
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_usage_project_date ON llm_usage(project, timestamp);
"""


class UsageTracker:
    """Registra consumo de LLM en SQLite."""

    def __init__(self, db_path: str | Path = "data/jarvis.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEX)

    def record(
        self,
        response: LLMResponse,
        project: str = "personal",
        agent_id: str | None = None,
        task_type: str | None = None,
    ) -> None:
        """Registrar uso exitoso."""
        self._conn.execute(
            "INSERT INTO llm_usage "
            "(id, timestamp, provider, model, project, agent_id, task_type, "
            "input_tokens, output_tokens, total_tokens, cost_usd, latency_ms, success) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (
                uuid.uuid4().hex[:12],
                datetime.now(timezone.utc).isoformat(),
                response.provider,
                response.model,
                project,
                agent_id,
                task_type,
                response.input_tokens,
                response.output_tokens,
                response.total_tokens,
                response.cost_usd,
                response.latency_ms,
            ),
        )
        self._conn.commit()

    def record_error(
        self,
        provider: str,
        model: str,
        error: str,
        project: str = "personal",
    ) -> None:
        """Registrar error de LLM."""
        self._conn.execute(
            "INSERT INTO llm_usage "
            "(id, timestamp, provider, model, project, success, error) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (
                uuid.uuid4().hex[:12],
                datetime.now(timezone.utc).isoformat(),
                provider,
                model,
                project,
                error,
            ),
        )
        self._conn.commit()

    def get_summary(self, days: int = 7) -> list[dict]:
        """Resumen de consumo agrupado por provider."""
        sql = """
        SELECT
            provider,
            COUNT(*) as requests,
            SUM(total_tokens) as tokens,
            SUM(cost_usd) as cost,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors,
            AVG(latency_ms) as avg_latency
        FROM llm_usage
        WHERE timestamp >= datetime('now', ?)
        GROUP BY provider
        ORDER BY requests DESC
        """
        rows = self._conn.execute(sql, (f"-{days} days",)).fetchall()
        return [
            {
                "provider": r[0],
                "requests": r[1],
                "tokens": r[2] or 0,
                "cost_usd": round(r[3] or 0.0, 4),
                "successes": r[4],
                "errors": r[5],
                "avg_latency_ms": int(r[6] or 0),
            }
            for r in rows
        ]

    def get_total_cost(self, days: int = 7) -> float:
        """Costo total en USD para los últimos N días."""
        row = self._conn.execute(
            "SELECT SUM(cost_usd) FROM llm_usage WHERE timestamp >= datetime('now', ?)",
            (f"-{days} days",),
        ).fetchone()
        return round(row[0] or 0.0, 4)

    def close(self):
        self._conn.close()
