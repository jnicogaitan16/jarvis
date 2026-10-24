"""Job Engine — Huey con SQLite para background jobs."""

from __future__ import annotations

from pathlib import Path

from huey import SqliteHuey

_DEFAULT_DB = "data/jarvis-jobs.db"


def create_huey(db_path: str = _DEFAULT_DB) -> SqliteHuey:
    """Crear instancia de Huey con SQLite backend."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return SqliteHuey(filename=db_path, immediate=False)


# Instancia global para decoradores de tareas
huey = create_huey()
