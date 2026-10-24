"""Metrics — recopilación de métricas del sistema desde SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentMetrics:
    agent_id: str
    total_runs: int = 0
    successes: int = 0
    failures: int = 0
    avg_duration_ms: int = 0
    last_run: str = ""

    @property
    def success_rate(self) -> float:
        return (self.successes / self.total_runs * 100) if self.total_runs else 0.0


@dataclass
class SystemMetrics:
    total_events: int = 0
    events_by_type: dict[str, int] = field(default_factory=dict)
    events_by_project: dict[str, int] = field(default_factory=dict)
    memory_records: int = 0
    memory_by_project: dict[str, int] = field(default_factory=dict)
    llm_requests: int = 0
    llm_cost_usd: float = 0.0
    llm_tokens: int = 0
    agent_metrics: list[AgentMetrics] = field(default_factory=list)


class MetricsCollector:
    """Recopila métricas del sistema desde las tablas SQLite."""

    def __init__(self, db_path: str | Path = "data/jarvis.db"):
        self._db_path = str(db_path)

    def collect(self, days: int = 7) -> SystemMetrics:
        """Recopilar todas las métricas del sistema."""
        metrics = SystemMetrics()

        conn = sqlite3.connect(self._db_path)
        try:
            metrics.total_events = self._count(conn, "events")
            metrics.events_by_type = self._group_count(conn, "events", "event_type")
            metrics.events_by_project = self._group_count(conn, "events", "project")
            metrics.memory_records = self._count(conn, "memory", "status = 'active'")
            metrics.memory_by_project = self._group_count(conn, "memory", "project", "status = 'active'")

            # LLM usage
            llm_stats = self._llm_stats(conn, days)
            metrics.llm_requests = llm_stats["requests"]
            metrics.llm_cost_usd = llm_stats["cost"]
            metrics.llm_tokens = llm_stats["tokens"]

            # Agent metrics from events
            metrics.agent_metrics = self._agent_metrics(conn, days)
        except sqlite3.OperationalError:
            pass  # Tables may not exist yet
        finally:
            conn.close()

        return metrics

    def _count(self, conn: sqlite3.Connection, table: str, where: str = "") -> int:
        clause = f"WHERE {where}" if where else ""
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table} {clause}").fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            return 0

    def _group_count(self, conn: sqlite3.Connection, table: str, column: str, where: str = "") -> dict[str, int]:
        clause = f"WHERE {where}" if where else ""
        try:
            rows = conn.execute(
                f"SELECT {column}, COUNT(*) FROM {table} {clause} GROUP BY {column} ORDER BY COUNT(*) DESC"
            ).fetchall()
            return {str(r[0] or "—"): r[1] for r in rows}
        except sqlite3.OperationalError:
            return {}

    def _llm_stats(self, conn: sqlite3.Connection, days: int) -> dict:
        try:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0), COALESCE(SUM(total_tokens), 0) "
                "FROM llm_usage WHERE timestamp >= datetime('now', ?)",
                (f"-{days} days",),
            ).fetchone()
            return {"requests": row[0], "cost": round(row[1], 4), "tokens": row[2]}
        except sqlite3.OperationalError:
            return {"requests": 0, "cost": 0.0, "tokens": 0}

    def _agent_metrics(self, conn: sqlite3.Connection, days: int) -> list[AgentMetrics]:
        """Extraer métricas de agentes desde events del orchestrator."""
        try:
            rows = conn.execute(
                """
                SELECT
                    json_extract(payload, '$.agent') as agent_id,
                    COUNT(*) as runs,
                    SUM(CASE WHEN json_extract(payload, '$.success') = 1 THEN 1 ELSE 0 END) as ok,
                    SUM(CASE WHEN json_extract(payload, '$.success') = 0 THEN 1 ELSE 0 END) as fail,
                    AVG(json_extract(payload, '$.duration_ms')) as avg_ms,
                    MAX(timestamp) as last
                FROM events
                WHERE event_type = 'observation'
                  AND json_extract(payload, '$.orchestrator') = 'result'
                  AND timestamp >= datetime('now', ?)
                GROUP BY agent_id
                """,
                (f"-{days} days",),
            ).fetchall()
            return [
                AgentMetrics(
                    agent_id=r[0] or "unknown",
                    total_runs=r[1],
                    successes=r[2] or 0,
                    failures=r[3] or 0,
                    avg_duration_ms=int(r[4] or 0),
                    last_run=r[5] or "",
                )
                for r in rows
            ]
        except sqlite3.OperationalError:
            return []
