"""Event Stream — almacén inmutable de eventos en SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from jarvis.core.models import Event, EventType

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    agent_id    TEXT,
    project     TEXT,
    payload     TEXT NOT NULL,
    parent_event_id TEXT
);
"""

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_project ON events(project);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
"""


class EventStore:
    """Almacén de eventos inmutables en SQLite.

    Los eventos son append-only: no se modifican ni eliminan.
    """

    def __init__(self, db_path: str | Path = "data/jarvis.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)

    def emit(
        self,
        event_type: EventType | str,
        payload: dict | None = None,
        *,
        agent_id: str | None = None,
        project: str | None = None,
        parent_event_id: str | None = None,
    ) -> Event:
        """Registrar un evento. Retorna el evento creado."""
        event = Event(
            event_type=EventType(event_type),
            payload=payload or {},
            agent_id=agent_id,
            project=project,
            parent_event_id=parent_event_id,
        )
        self._conn.execute(
            "INSERT INTO events (id, timestamp, event_type, agent_id, project, payload, parent_event_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.agent_id,
                event.project,
                json.dumps(event.payload, ensure_ascii=False, default=str),
                event.parent_event_id,
            ),
        )
        self._conn.commit()
        return event

    def query(
        self,
        *,
        event_type: EventType | str | None = None,
        project: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Consultar eventos con filtros."""
        clauses: list[str] = []
        params: list = []

        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(str(event_type))
        if project is not None:
            clauses.append("project = ?")
            params.append(project)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT id, timestamp, event_type, agent_id, project, payload, parent_event_id FROM events {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        events: list[Event] = []
        for row in rows:
            events.append(
                Event(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    event_type=EventType(row[2]),
                    agent_id=row[3],
                    project=row[4],
                    payload=json.loads(row[5]),
                    parent_event_id=row[6],
                )
            )
        return events

    def count(self, *, project: str | None = None) -> int:
        """Contar eventos totales o por proyecto."""
        if project:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM events WHERE project = ?", (project,)
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return row[0] if row else 0

    def close(self):
        self._conn.close()
