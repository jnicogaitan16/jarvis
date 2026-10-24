"""Fixtures compartidas para tests de JARVIS."""

import pytest

from jarvis.core.events import EventStore
from jarvis.core.models import ProjectContext


@pytest.fixture
def tmp_db(tmp_path):
    """Path temporal para SQLite."""
    return str(tmp_path / "test.db")


@pytest.fixture
def event_store(tmp_db):
    """EventStore con base de datos temporal."""
    store = EventStore(db_path=tmp_db)
    yield store
    store.close()


@pytest.fixture
def personal_context():
    """ProjectContext para proyecto personal."""
    return ProjectContext(
        project_id="personal",
        display_name="Personal",
        allowed_providers=frozenset({"ollama", "gemini"}),
        allow_cloud=True,
    )


@pytest.fixture
def integratepie_context():
    """ProjectContext para IntegratePIE."""
    return ProjectContext(
        project_id="integratepie",
        display_name="IntegratePIE",
        allowed_providers=frozenset({"ollama", "gemini"}),
        allow_cloud=True,
        allow_pii_to_cloud=False,
        sensitive_patterns=frozenset({"run", "rut", "nombre_alumno"}),
    )


@pytest.fixture
def kamecol_context():
    """ProjectContext para KameCol."""
    return ProjectContext(
        project_id="kamecol",
        display_name="KameCol",
        allowed_providers=frozenset({"ollama", "gemini"}),
        allow_cloud=True,
        allow_pii_to_cloud=False,
        sensitive_patterns=frozenset({"cedula", "telefono"}),
    )
