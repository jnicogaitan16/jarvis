"""Tests para Event Stream."""

from datetime import datetime, timezone

from jarvis.core.events import EventStore
from jarvis.core.models import EventType


class TestEventStore:
    def test_emit_and_query(self, event_store: EventStore):
        event = event_store.emit(EventType.ACTION, {"test": True})
        assert event.id
        assert event.event_type == EventType.ACTION
        assert event.payload == {"test": True}

        results = event_store.query()
        assert len(results) == 1
        assert results[0].id == event.id

    def test_emit_multiple(self, event_store: EventStore):
        event_store.emit(EventType.ACTION, {"step": 1})
        event_store.emit(EventType.OBSERVATION, {"step": 2})
        event_store.emit(EventType.SYSTEM, {"step": 3})

        results = event_store.query()
        assert len(results) == 3

    def test_query_by_type(self, event_store: EventStore):
        event_store.emit(EventType.ACTION, {"a": 1})
        event_store.emit(EventType.OBSERVATION, {"b": 2})
        event_store.emit(EventType.ACTION, {"c": 3})

        actions = event_store.query(event_type=EventType.ACTION)
        assert len(actions) == 2
        assert all(e.event_type == EventType.ACTION for e in actions)

    def test_query_by_project(self, event_store: EventStore):
        event_store.emit(EventType.ACTION, {"a": 1}, project="pie")
        event_store.emit(EventType.ACTION, {"b": 2}, project="kamecol")
        event_store.emit(EventType.ACTION, {"c": 3}, project="pie")

        pie_events = event_store.query(project="pie")
        assert len(pie_events) == 2

        kc_events = event_store.query(project="kamecol")
        assert len(kc_events) == 1

    def test_query_by_since(self, event_store: EventStore):
        event_store.emit(EventType.ACTION, {"old": True})
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        results = event_store.query(since=future)
        assert len(results) == 0

    def test_query_limit(self, event_store: EventStore):
        for i in range(20):
            event_store.emit(EventType.ACTION, {"i": i})

        results = event_store.query(limit=5)
        assert len(results) == 5

    def test_count(self, event_store: EventStore):
        assert event_store.count() == 0
        event_store.emit(EventType.ACTION, {"a": 1}, project="pie")
        event_store.emit(EventType.ACTION, {"b": 2}, project="kamecol")
        assert event_store.count() == 2
        assert event_store.count(project="pie") == 1

    def test_event_with_agent_and_parent(self, event_store: EventStore):
        parent = event_store.emit(EventType.ACTION, {"parent": True})
        child = event_store.emit(
            EventType.OBSERVATION,
            {"child": True},
            agent_id="qa.analyzer",
            parent_event_id=parent.id,
        )
        results = event_store.query()
        child_event = next(e for e in results if e.id == child.id)
        assert child_event.agent_id == "qa.analyzer"
        assert child_event.parent_event_id == parent.id

    def test_persistence(self, tmp_db):
        """Verificar que los eventos persisten tras cerrar y reabrir."""
        store1 = EventStore(db_path=tmp_db)
        store1.emit(EventType.SYSTEM, {"persistent": True})
        store1.close()

        store2 = EventStore(db_path=tmp_db)
        results = store2.query()
        assert len(results) == 1
        assert results[0].payload["persistent"] is True
        store2.close()

    def test_events_are_ordered_newest_first(self, event_store: EventStore):
        event_store.emit(EventType.ACTION, {"order": 1})
        event_store.emit(EventType.ACTION, {"order": 2})
        event_store.emit(EventType.ACTION, {"order": 3})

        results = event_store.query()
        assert results[0].payload["order"] == 3
        assert results[2].payload["order"] == 1
