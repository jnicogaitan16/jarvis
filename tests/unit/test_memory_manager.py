"""Tests para Memory Manager — búsqueda híbrida y aislamiento."""

import pytest

from jarvis.core.models import MemoryType, ProjectContext
from jarvis.memory.manager import MemoryManager
from jarvis.memory.store import MemoryStore


@pytest.fixture
def manager(tmp_path):
    store = MemoryStore(db_path=str(tmp_path / "mgr.db"))
    mgr = MemoryManager(store=store, embeddings_enabled=False)  # Sin Ollama en tests
    yield mgr
    mgr.close()


class TestMemoryManagerCRUD:
    def test_add_and_get(self, manager: MemoryManager):
        rec = manager.add("PHP 8.4 con Laravel", project="pie", source="audit")
        assert rec.id
        assert rec.content == "PHP 8.4 con Laravel"

        got = manager.get(rec.id)
        assert got is not None
        assert got.project == "pie"

    def test_update(self, manager: MemoryManager):
        rec = manager.add("original", project="p")
        manager.update(rec.id, content="modified")
        got = manager.get(rec.id)
        assert got.content == "modified"

    def test_invalidate(self, manager: MemoryManager):
        rec = manager.add("will be invalid", project="p")
        manager.invalidate(rec.id)
        got = manager.get(rec.id)
        assert got.status == "invalidated"

    def test_count(self, manager: MemoryManager):
        manager.add("a", project="x")
        manager.add("b", project="x")
        manager.add("c", project="y")
        assert manager.count() == 3
        assert manager.count(project="x") == 2


class TestMemorySearch:
    def test_fts_search(self, manager: MemoryManager):
        manager.add("IntegratePIE usa PHP 8.4", project="pie")
        manager.add("KameCol usa Django 5.2", project="kc")

        results = manager.search("PHP")
        assert len(results) >= 1
        assert "PHP" in results[0][0].content

    def test_search_with_project_filter(self, manager: MemoryManager):
        manager.add("dato de pie", project="pie")
        manager.add("dato de kc", project="kc")

        results = manager.search("dato", project="pie")
        assert len(results) == 1
        assert results[0][0].project == "pie"

    def test_search_empty_results(self, manager: MemoryManager):
        manager.add("something", project="p")
        results = manager.search("zzzyyyxxx")
        assert results == []

    def test_search_by_project(self, manager: MemoryManager):
        manager.add("one", project="a")
        manager.add("two", project="a")
        manager.add("three", project="b")

        records = manager.search_by_project("a")
        assert len(records) == 2


class TestMemoryIsolation:
    """Tests de aislamiento de memoria entre proyectos — requisito de seguridad."""

    def test_search_respects_project_namespace(self, manager: MemoryManager):
        """Memoria de IntegratePIE no aparece en búsquedas de KameCol."""
        manager.add("dato confidencial de PIE", project="integratepie")
        manager.add("dato público de KameCol", project="kamecol")

        pie_ctx = ProjectContext(
            project_id="integratepie", display_name="PIE",
            memory_namespace="integratepie",
        )
        kc_ctx = ProjectContext(
            project_id="kamecol", display_name="KC",
            memory_namespace="kamecol",
        )

        pie_results = manager.search("dato", context=pie_ctx)
        kc_results = manager.search("dato", context=kc_ctx)

        assert all(r[0].project == "integratepie" for r in pie_results)
        assert all(r[0].project == "kamecol" for r in kc_results)

    def test_cross_project_not_leaked(self, manager: MemoryManager):
        """Buscar en proyecto A no retorna datos de proyecto B."""
        manager.add("secreto PHP", project="integratepie")
        results = manager.search("PHP", project="kamecol")
        assert len(results) == 0

    def test_list_by_project_isolated(self, manager: MemoryManager):
        manager.add("pie stuff", project="pie")
        manager.add("kc stuff", project="kc")

        assert len(manager.search_by_project("pie")) == 1
        assert len(manager.search_by_project("kc")) == 1
        assert manager.search_by_project("pie")[0].project == "pie"


class TestContextInjection:
    def test_get_context_for_prompt(self, manager: MemoryManager):
        manager.add("JARVIS usa Python 3.12", project="personal")
        manager.add("El MVP incluye CLI y memoria", project="personal")

        context = manager.get_context_for_prompt("Python", project="personal")
        assert "Python" in context
        assert "Contexto relevante" in context

    def test_get_context_empty(self, manager: MemoryManager):
        context = manager.get_context_for_prompt("nada", project="personal")
        assert context == ""

    def test_context_respects_max_chars(self, manager: MemoryManager):
        for i in range(20):
            manager.add(f"Registro de prueba número {i} con contenido extenso", project="p")

        context = manager.get_context_for_prompt("prueba", project="p", max_chars=200)
        assert len(context) <= 300  # Algo de margen por el header


class TestEmbeddings:
    def test_cosine_similarity(self):
        from jarvis.memory.embeddings import cosine_similarity

        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)
        assert cosine_similarity([1, 0, 0], [-1, 0, 0]) == pytest.approx(-1.0)
        assert cosine_similarity([], []) == 0.0
        assert cosine_similarity([0, 0], [0, 0]) == 0.0

    def test_cosine_similarity_different_lengths(self):
        from jarvis.memory.embeddings import cosine_similarity

        assert cosine_similarity([1, 0], [1, 0, 0]) == 0.0
