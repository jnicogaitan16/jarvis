"""Memory Store — persistencia de memoria en SQLite con FTS5."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from jarvis.core.models import MemoryRecord, MemoryType, _new_id, _now

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id          TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    source      TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}',
    confidence  REAL DEFAULT 1.0,
    status      TEXT DEFAULT 'active',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    version     INTEGER DEFAULT 1,
    tags        TEXT DEFAULT '[]',
    permissions TEXT DEFAULT '[]',
    embedding   BLOB
);

CREATE INDEX IF NOT EXISTS idx_memory_project ON memory(project);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory(status);
"""

_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    id UNINDEXED,
    project UNINDEXED,
    content,
    tags,
    tokenize='unicode61'
);
"""

_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(id, project, content, tags)
    VALUES (new.id, new.project, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
    DELETE FROM memory_fts WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
    DELETE FROM memory_fts WHERE id = old.id;
    INSERT INTO memory_fts(id, project, content, tags)
    VALUES (new.id, new.project, new.content, new.tags);
END;
"""


class MemoryStore:
    """Almacén de memoria persistente con FTS5."""

    def __init__(self, db_path: str | Path = "data/jarvis.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.executescript(_FTS_SCHEMA)
        self._conn.executescript(_FTS_TRIGGERS)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Insertar un registro de memoria."""
        now = _now().isoformat()
        if not record.id:
            record = record.model_copy(update={"id": _new_id()})
        self._conn.execute(
            "INSERT INTO memory "
            "(id, project, memory_type, source, content, metadata, confidence, "
            "status, created_at, updated_at, version, tags, permissions, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id,
                record.project,
                record.memory_type.value,
                record.source,
                record.content,
                json.dumps(record.metadata, ensure_ascii=False),
                record.confidence,
                record.status,
                record.created_at.isoformat(),
                now,
                record.version,
                json.dumps(record.tags, ensure_ascii=False),
                json.dumps(record.permissions, ensure_ascii=False),
                None,  # embedding se agrega después
            ),
        )
        self._conn.commit()
        return record

    def get(self, record_id: str) -> MemoryRecord | None:
        """Obtener un registro por ID."""
        row = self._conn.execute(
            "SELECT id, project, memory_type, source, content, metadata, confidence, "
            "status, created_at, updated_at, version, tags, permissions "
            "FROM memory WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def update(self, record_id: str, **kwargs) -> bool:
        """Actualizar campos de un registro."""
        allowed = {"content", "metadata", "confidence", "status", "tags", "version"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False

        fields["updated_at"] = _now().isoformat()
        if "metadata" in fields:
            fields["metadata"] = json.dumps(fields["metadata"], ensure_ascii=False)
        if "tags" in fields:
            fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)

        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [record_id]
        cursor = self._conn.execute(f"UPDATE memory SET {sets} WHERE id = ?", vals)
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, record_id: str) -> bool:
        """Eliminar un registro."""
        self._conn.execute("DELETE FROM memory WHERE id = ?", (record_id,))
        self._conn.commit()
        return self._conn.total_changes > 0

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_fts(
        self,
        query: str,
        project: str | None = None,
        limit: int = 10,
    ) -> list[tuple[MemoryRecord, float]]:
        """Búsqueda full-text con FTS5. Retorna (record, rank)."""
        if not query.strip():
            return []

        # Tokenizar query: cada palabra se busca con OR implícito
        # Escapar caracteres especiales de FTS5
        words = query.strip().split()
        safe_tokens = [w.replace('"', '""') for w in words if w]
        if not safe_tokens:
            return []
        fts_query = " OR ".join(f'"{t}"' for t in safe_tokens)

        if project:
            sql = """
            SELECT m.id, m.project, m.memory_type, m.source, m.content,
                   m.metadata, m.confidence, m.status, m.created_at,
                   m.updated_at, m.version, m.tags, m.permissions,
                   rank
            FROM memory_fts fts
            JOIN memory m ON fts.id = m.id
            WHERE memory_fts MATCH ? AND fts.project = ? AND m.status = 'active'
            ORDER BY rank
            LIMIT ?
            """
            rows = self._conn.execute(sql, (fts_query, project, limit)).fetchall()
        else:
            sql = """
            SELECT m.id, m.project, m.memory_type, m.source, m.content,
                   m.metadata, m.confidence, m.status, m.created_at,
                   m.updated_at, m.version, m.tags, m.permissions,
                   rank
            FROM memory_fts fts
            JOIN memory m ON fts.id = m.id
            WHERE memory_fts MATCH ? AND m.status = 'active'
            ORDER BY rank
            LIMIT ?
            """
            rows = self._conn.execute(sql, (fts_query, limit)).fetchall()

        return [(self._row_to_record(row[:13]), row[13]) for row in rows]

    def list_by_project(
        self,
        project: str,
        memory_type: MemoryType | str | None = None,
        status: str = "active",
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """Listar registros de un proyecto."""
        clauses = ["project = ?", "status = ?"]
        params: list = [project, status]

        if memory_type:
            clauses.append("memory_type = ?")
            params.append(str(memory_type))

        where = " AND ".join(clauses)
        params.append(limit)
        rows = self._conn.execute(
            f"SELECT id, project, memory_type, source, content, metadata, confidence, "
            f"status, created_at, updated_at, version, tags, permissions "
            f"FROM memory WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def count(self, project: str | None = None) -> int:
        """Contar registros activos."""
        if project:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM memory WHERE project = ? AND status = 'active'",
                (project,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM memory WHERE status = 'active'"
            ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def store_embedding(self, record_id: str, embedding: list[float]) -> None:
        """Almacenar embedding como blob."""
        import struct
        blob = struct.pack(f"{len(embedding)}f", *embedding)
        self._conn.execute(
            "UPDATE memory SET embedding = ? WHERE id = ?",
            (blob, record_id),
        )
        self._conn.commit()

    def get_embedding(self, record_id: str) -> list[float] | None:
        """Recuperar embedding de un registro."""
        import struct
        row = self._conn.execute(
            "SELECT embedding FROM memory WHERE id = ?", (record_id,)
        ).fetchone()
        if not row or not row[0]:
            return None
        blob = row[0]
        n = len(blob) // 4  # float32 = 4 bytes
        return list(struct.unpack(f"{n}f", blob))

    def get_all_with_embeddings(
        self, project: str | None = None
    ) -> list[tuple[MemoryRecord, list[float]]]:
        """Obtener todos los registros con embeddings para búsqueda semántica."""
        import struct
        if project:
            rows = self._conn.execute(
                "SELECT id, project, memory_type, source, content, metadata, confidence, "
                "status, created_at, updated_at, version, tags, permissions, embedding "
                "FROM memory WHERE embedding IS NOT NULL AND status = 'active' AND project = ?",
                (project,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, project, memory_type, source, content, metadata, confidence, "
                "status, created_at, updated_at, version, tags, permissions, embedding "
                "FROM memory WHERE embedding IS NOT NULL AND status = 'active'"
            ).fetchall()

        results = []
        for row in rows:
            record = self._row_to_record(row[:13])
            blob = row[13]
            n = len(blob) // 4
            emb = list(struct.unpack(f"{n}f", blob))
            results.append((record, emb))
        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _row_to_record(self, row: tuple) -> MemoryRecord:
        return MemoryRecord(
            id=row[0],
            project=row[1],
            memory_type=MemoryType(row[2]),
            source=row[3],
            content=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            confidence=row[6],
            status=row[7],
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9]),
            version=row[10],
            tags=json.loads(row[11]) if row[11] else [],
            permissions=json.loads(row[12]) if row[12] else [],
        )

    def close(self):
        self._conn.close()
