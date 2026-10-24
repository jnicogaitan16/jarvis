"""Tests para JARVIS Web — API REST y páginas."""

import pytest
from fastapi.testclient import TestClient

from jarvis.web.app import app

client = TestClient(app)


class TestAPIHealth:
    def test_health_endpoint(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_health_has_version(self):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "version" in data


class TestAPIMetrics:
    def test_metrics_endpoint(self):
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "events_total" in data
        assert "memory_records" in data
        assert "llm_cost_usd" in data

    def test_metrics_with_days(self):
        resp = client.get("/api/v1/metrics?days=30")
        assert resp.status_code == 200
        assert resp.json()["period_days"] == 30


class TestAPIProjects:
    def test_projects_endpoint(self):
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        assert "personal" in data["projects"]


class TestAPIAgents:
    def test_agents_endpoint(self):
        resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert len(data["agents"]) >= 1
        ids = [a["id"] for a in data["agents"]]
        assert "core.echo" in ids


class TestAPIMemory:
    def test_memory_search(self):
        resp = client.get("/api/v1/memory/search?q=test")
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data

    def test_memory_search_requires_query(self):
        resp = client.get("/api/v1/memory/search")
        assert resp.status_code == 422  # Missing required param

    def test_memory_list(self):
        resp = client.get("/api/v1/memory/list?project=personal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"] == "personal"
        assert "records" in data


class TestAPIEvents:
    def test_events_endpoint(self):
        resp = client.get("/api/v1/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "count" in data


class TestWebPages:
    def test_index_page(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "JARVIS" in resp.text
        assert "Dashboard" in resp.text

    def test_memory_page(self):
        resp = client.get("/memory")
        assert resp.status_code == 200
        assert "Memoria" in resp.text

    def test_agents_page(self):
        resp = client.get("/agents")
        assert resp.status_code == 200
        assert "Agentes" in resp.text
        assert "core.echo" in resp.text

    def test_events_page(self):
        resp = client.get("/events")
        assert resp.status_code == 200
        assert "Eventos" in resp.text
