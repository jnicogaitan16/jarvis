"""Tests para LLM Usage Tracking."""

import pytest

from jarvis.llm.base import LLMResponse
from jarvis.llm.usage import UsageTracker


@pytest.fixture
def tracker(tmp_path):
    t = UsageTracker(db_path=str(tmp_path / "usage.db"))
    yield t
    t.close()


class TestUsageTracker:
    def test_record_and_summary(self, tracker: UsageTracker):
        resp = LLMResponse(
            content="test",
            provider="ollama",
            model="qwen2.5:7b",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            latency_ms=500,
            cost_usd=0.0,
        )
        tracker.record(resp, project="personal")

        summary = tracker.get_summary(days=1)
        assert len(summary) == 1
        assert summary[0]["provider"] == "ollama"
        assert summary[0]["requests"] == 1
        assert summary[0]["tokens"] == 150

    def test_record_multiple_providers(self, tracker: UsageTracker):
        for provider, cost in [("ollama", 0.0), ("gemini", 0.001), ("ollama", 0.0)]:
            resp = LLMResponse(
                content="test", provider=provider, model="m",
                total_tokens=100, cost_usd=cost,
            )
            tracker.record(resp, project="personal")

        summary = tracker.get_summary(days=1)
        assert len(summary) == 2
        ollama_row = next(s for s in summary if s["provider"] == "ollama")
        assert ollama_row["requests"] == 2

    def test_record_error(self, tracker: UsageTracker):
        tracker.record_error("gemini", "gemini-flash", "timeout", project="pie")
        summary = tracker.get_summary(days=1)
        assert len(summary) == 1
        assert summary[0]["errors"] == 1
        assert summary[0]["successes"] == 0

    def test_total_cost(self, tracker: UsageTracker):
        for cost in [0.001, 0.002, 0.003]:
            resp = LLMResponse(
                content="t", provider="gemini", model="m",
                total_tokens=100, cost_usd=cost,
            )
            tracker.record(resp, project="personal")

        total = tracker.get_total_cost(days=1)
        assert total == pytest.approx(0.006, abs=0.0001)

    def test_empty_summary(self, tracker: UsageTracker):
        summary = tracker.get_summary(days=1)
        assert summary == []

    def test_total_cost_empty(self, tracker: UsageTracker):
        assert tracker.get_total_cost(days=1) == 0.0

    def test_persistence(self, tmp_path):
        db = str(tmp_path / "persist.db")
        t1 = UsageTracker(db_path=db)
        resp = LLMResponse(content="t", provider="ollama", model="m", total_tokens=50)
        t1.record(resp, project="p")
        t1.close()

        t2 = UsageTracker(db_path=db)
        summary = t2.get_summary(days=1)
        assert len(summary) == 1
        t2.close()
