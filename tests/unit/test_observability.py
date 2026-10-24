"""Tests para observabilidad — métricas, health checks, benchmarks."""

import pytest

from jarvis.observability.benchmarks import BenchmarkCase, BenchmarkRunner, BenchmarkSuiteResult
from jarvis.observability.health import HealthCheck, _check_sqlite, _check_memory
from jarvis.observability.metrics import AgentMetrics, MetricsCollector, SystemMetrics


class TestMetricsCollector:
    def test_collect_empty_db(self, tmp_path):
        db = str(tmp_path / "empty.db")
        collector = MetricsCollector(db_path=db)
        m = collector.collect()
        assert isinstance(m, SystemMetrics)
        assert m.total_events == 0
        assert m.llm_requests == 0

    def test_collect_with_events(self, tmp_path):
        from jarvis.core.events import EventStore
        from jarvis.core.models import EventType

        db = str(tmp_path / "metrics.db")
        store = EventStore(db_path=db)
        store.emit(EventType.ACTION, {"test": 1}, project="pie")
        store.emit(EventType.OBSERVATION, {"test": 2}, project="pie")
        store.emit(EventType.ACTION, {"test": 3}, project="kc")
        store.close()

        collector = MetricsCollector(db_path=db)
        m = collector.collect()
        assert m.total_events == 3
        assert m.events_by_type["action"] == 2
        assert m.events_by_project["pie"] == 2

    def test_collect_with_memory(self, tmp_path):
        from jarvis.memory.store import MemoryStore
        from jarvis.core.models import MemoryRecord, MemoryType

        db = str(tmp_path / "mem_metrics.db")
        store = MemoryStore(db_path=db)
        store.add(MemoryRecord(project="a", memory_type=MemoryType.SEMANTIC, source="t", content="x"))
        store.add(MemoryRecord(project="b", memory_type=MemoryType.SEMANTIC, source="t", content="y"))
        store.close()

        collector = MetricsCollector(db_path=db)
        m = collector.collect()
        assert m.memory_records == 2
        assert m.memory_by_project["a"] == 1


class TestAgentMetrics:
    def test_success_rate(self):
        am = AgentMetrics(agent_id="test", total_runs=10, successes=8, failures=2)
        assert am.success_rate == 80.0

    def test_success_rate_zero_runs(self):
        am = AgentMetrics(agent_id="test")
        assert am.success_rate == 0.0


class TestHealthChecks:
    def test_sqlite_check(self, tmp_path):
        db = str(tmp_path / "health.db")
        result = _check_sqlite(db)
        assert result.healthy is True

    def test_memory_check_empty(self, tmp_path):
        db = str(tmp_path / "no_tables.db")
        import sqlite3
        conn = sqlite3.connect(db)
        conn.close()
        result = _check_memory(db)
        assert result.healthy is True  # No tables yet is OK


class TestBenchmarkRunner:
    def test_run_suite_all_pass(self):
        cases = [
            BenchmarkCase("T-1", "Test 1", "test", {"x": 1}, {"result": "ok"}),
            BenchmarkCase("T-2", "Test 2", "test", {"x": 2}, {"result": "ok"}),
        ]
        runner = BenchmarkRunner()
        result = runner.run_suite("Test Suite", cases, lambda data: {"result": "ok"})
        assert result.total == 2
        assert result.passed == 2
        assert result.pass_rate == 100.0

    def test_run_suite_with_failure(self):
        cases = [
            BenchmarkCase("T-1", "Pass", "test", {}, {"val": 1}),
            BenchmarkCase("T-2", "Fail", "test", {}, {"val": 99}),
        ]
        runner = BenchmarkRunner()
        result = runner.run_suite("Mixed", cases, lambda data: {"val": 1})
        assert result.passed == 1
        assert result.failed == 1
        assert result.pass_rate == 50.0

    def test_run_suite_with_error(self):
        cases = [BenchmarkCase("T-1", "Error", "test", {}, {"val": 1})]
        runner = BenchmarkRunner()
        result = runner.run_suite("Error", cases, lambda data: (_ for _ in ()).throw(RuntimeError("boom")))
        assert result.errors == 1
        assert result.passed == 0

    def test_contains_evaluator(self):
        cases = [BenchmarkCase("T-1", "Contains", "test", {}, {"msg": "hello"}, evaluator="contains")]
        runner = BenchmarkRunner()
        result = runner.run_suite("Contains", cases, lambda data: {"msg": "hello world"})
        assert result.passed == 1

    def test_gte_evaluator(self):
        cases = [BenchmarkCase("T-1", "GTE", "test", {}, {"score": 5}, evaluator="gte")]
        runner = BenchmarkRunner()
        # 10 >= 5 should pass
        r1 = runner.run_suite("GTE Pass", cases, lambda data: {"score": 10})
        assert r1.passed == 1
        # 3 >= 5 should fail
        r2 = runner.run_suite("GTE Fail", cases, lambda data: {"score": 3})
        assert r2.failed == 1

    def test_suite_result_properties(self):
        sr = BenchmarkSuiteResult(name="test", total=0)
        assert sr.pass_rate == 0.0
