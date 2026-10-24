"""Tests para Memory Store."""

import pytest

from jarvis.core.models import MemoryRecord, MemoryType
from jarvis.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    s = MemoryStore(db_path=str(tmp_path / "mem.db"))
    yield s
    s.close()


def _make_record(project="personal", content="test content", source="user"):
    return MemoryRecord(
        project=project,
        memory_type=MemoryType.SEMANTIC,
        source=source,
        content=content,
    )


class TestMemoryStoreCRUD:
    def test_add_and_get(self, store: MemoryStore):
        rec = _make_record(content="PHP 8.4 con Laravel")
        added = store.add(rec)
        assert added.id

        got = store.get(added.id)
        assert got is not None
        assert got.content == "PHP 8.4 con Laravel"
        assert got.project == "personal"

    def test_get_nonexistent(self, store: MemoryStore):
        assert store.get("nonexistent") is None

    def test_update(self, store: MemoryStore):
        rec = store.add(_make_record(content="original"))
        store.update(rec.id, content="updated", confidence=0.8)

        got = store.get(rec.id)
        assert got.content == "updated"
        assert got.confidence == 0.8

    def test_update_nonexistent(self, store: MemoryStore):
        assert store.update("nope", content="x") is False

    def test_delete(self, store: MemoryStore):
        rec = store.add(_make_record())
        assert store.delete(rec.id) is True
        assert store.get(rec.id) is None

    def test_count(self, store: MemoryStore):
        assert store.count() == 0
        store.add(_make_record(project="a"))
        store.add(_make_record(project="b"))
        store.add(_make_record(project="a"))
        assert store.count() == 3
        assert store.count(project="a") == 2
        assert store.count(project="b") == 1


class TestMemoryStoreFTS:
    def test_search_basic(self, store: MemoryStore):
        store.add(_make_record(content="IntegratePIE usa PHP 8.4"))
        store.add(_make_record(content="KameCol usa Django 5.2"))

        results = store.search_fts("PHP")
        assert len(results) == 1
        assert "PHP" in results[0][0].content

    def test_search_multiple_words(self, store: MemoryStore):
        store.add(_make_record(content="Laravel es un framework PHP"))
        store.add(_make_record(content="Django es un framework Python"))
        store.add(_make_record(content="PHP es un lenguaje de programación"))

        results = store.search_fts("PHP framework")
        assert len(results) >= 1

    def test_search_with_project_filter(self, store: MemoryStore):
        store.add(_make_record(project="pie", content="PHP project"))
        store.add(_make_record(project="kc", content="PHP also here"))

        results = store.search_fts("PHP", project="pie")
        assert len(results) == 1
        assert results[0][0].project == "pie"

    def test_search_empty_query(self, store: MemoryStore):
        store.add(_make_record(content="something"))
        assert store.search_fts("") == []
        assert store.search_fts("   ") == []

    def test_search_no_results(self, store: MemoryStore):
        store.add(_make_record(content="hello world"))
        results = store.search_fts("zzzyyyxxx")
        assert len(results) == 0

    def test_search_excludes_inactive(self, store: MemoryStore):
        rec = store.add(_make_record(content="active record"))
        store.add(_make_record(content="another active"))
        store.update(rec.id, status="invalidated")

        results = store.search_fts("active")
        assert len(results) == 1


class TestMemoryStoreEmbeddings:
    def test_store_and_get_embedding(self, store: MemoryStore):
        rec = store.add(_make_record())
        emb = [0.1, 0.2, 0.3, 0.4]
        store.store_embedding(rec.id, emb)

        got = store.get_embedding(rec.id)
        assert got is not None
        assert len(got) == 4
        assert abs(got[0] - 0.1) < 0.001

    def test_get_embedding_none(self, store: MemoryStore):
        rec = store.add(_make_record())
        assert store.get_embedding(rec.id) is None

    def test_get_all_with_embeddings(self, store: MemoryStore):
        r1 = store.add(_make_record(project="a", content="first"))
        r2 = store.add(_make_record(project="a", content="second"))
        store.add(_make_record(project="a", content="no embedding"))

        store.store_embedding(r1.id, [1.0, 0.0])
        store.store_embedding(r2.id, [0.0, 1.0])

        results = store.get_all_with_embeddings(project="a")
        assert len(results) == 2

    def test_get_all_with_embeddings_project_filter(self, store: MemoryStore):
        r1 = store.add(_make_record(project="a"))
        r2 = store.add(_make_record(project="b"))
        store.store_embedding(r1.id, [1.0])
        store.store_embedding(r2.id, [1.0])

        results = store.get_all_with_embeddings(project="a")
        assert len(results) == 1
        assert results[0][0].project == "a"


class TestMemoryStorePersistence:
    def test_data_persists_across_connections(self, tmp_path):
        db = str(tmp_path / "persist.db")

        s1 = MemoryStore(db_path=db)
        s1.add(_make_record(content="I persist"))
        s1.close()

        s2 = MemoryStore(db_path=db)
        results = s2.search_fts("persist")
        assert len(results) == 1
        assert results[0][0].content == "I persist"
        s2.close()

    def test_list_by_project(self, store: MemoryStore):
        store.add(_make_record(project="pie", content="one"))
        store.add(_make_record(project="pie", content="two"))
        store.add(_make_record(project="kc", content="three"))

        pie_records = store.list_by_project("pie")
        assert len(pie_records) == 2

        kc_records = store.list_by_project("kc")
        assert len(kc_records) == 1
