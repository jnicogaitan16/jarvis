"""Tests para QA Agent — análisis de PRs con IAAgent pipeline."""

import json

import pytest

from jarvis.integrations.iaagent_bridge import is_available

pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="IAAgent no disponible en esta máquina",
)


SAMPLE_DIFF = """--- a/app/Http/Controllers/UserController.php
+++ b/app/Http/Controllers/UserController.php
@@ -10,6 +10,12 @@
 class UserController extends Controller
 {
+    public function updatePassword(Request $request)
+    {
+        $user = User::find($request->id);
+        $user->password = $request->input('password');
+        $user->save();
+    }
 }
"""

SAMPLE_SECURITY_DIFF = """--- a/config/database.php
+++ b/config/database.php
@@ -1,3 +1,4 @@
+DB_PASSWORD = "super_secret_password_123"
 return [
     'default' => env('DB_CONNECTION', 'mysql'),
"""


class TestQAAgentWithDirectData:
    """Tests del QA Agent con datos directos (sin Azure DevOps)."""

    def test_analyze_simple_pr(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.qa.agent import QAAgent

        agent = QAAgent()
        request = AgentRequest(
            intent="analyze_pr",
            payload={
                "pr_id": 1,
                "title": "Add updatePassword method",
                "diffs": [{"path": "app/Http/Controllers/UserController.php", "diff_text": SAMPLE_DIFF}],
                "changes": [{"path": "app/Http/Controllers/UserController.php", "change_type": "edit"}],
            },
            project="integratepie",
        )

        result = agent.execute(request)
        assert result.success is True
        assert "PR #1" in result.content
        assert result.data["pr_id"] == 1
        assert result.data["risk_score"] >= 0
        assert result.data["findings_total"] >= 0
        assert result.data["test_cases"] >= 0
        assert result.duration_ms > 0

    def test_analyze_pr_with_security_issue(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.qa.agent import QAAgent

        agent = QAAgent()
        request = AgentRequest(
            intent="analyze_pr",
            payload={
                "pr_id": 2,
                "title": "Update database config",
                "diffs": [{"path": "config/database.php", "diff_text": SAMPLE_SECURITY_DIFF}],
                "changes": [{"path": "config/database.php", "change_type": "edit"}],
            },
            project="integratepie",
        )

        result = agent.execute(request)
        assert result.success is True
        # Should detect the hardcoded password
        assert result.data["findings_total"] >= 1

    def test_analyze_empty_pr(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.qa.agent import QAAgent

        agent = QAAgent()
        request = AgentRequest(
            intent="analyze_pr",
            payload={
                "pr_id": 3,
                "title": "Empty PR",
                "diffs": [],
                "changes": [],
            },
            project="personal",
        )

        result = agent.execute(request)
        assert result.success is True
        assert result.data["risk_score"] == 0.0 or result.data["risk_score"] >= 0

    def test_analyze_without_pr_id_or_diffs_fails(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.qa.agent import QAAgent

        agent = QAAgent()
        request = AgentRequest(
            intent="analyze_pr",
            payload={},
            project="personal",
        )

        result = agent.execute(request)
        assert result.success is False

    def test_evidence_saved(self, tmp_path, monkeypatch):
        """Verificar que se guardan archivos de evidencia."""
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.qa.agent import QAAgent

        # Redirigir evidencias al tmp_path
        monkeypatch.chdir(tmp_path)

        agent = QAAgent()
        request = AgentRequest(
            intent="analyze_pr",
            payload={
                "pr_id": 10,
                "title": "Evidence test",
                "diffs": [{"path": "test.py", "diff_text": "+print('hello')"}],
                "changes": [{"path": "test.py", "change_type": "edit"}],
            },
            project="test",
        )

        result = agent.execute(request)
        assert result.success is True
        assert len(result.evidence) == 3  # report.md, comment.md, data.json

        # Verificar que los archivos existen
        for path in result.evidence:
            from pathlib import Path
            assert Path(path).exists()

        # Verificar contenido del JSON
        json_path = next(p for p in result.evidence if p.endswith(".json"))
        data = json.loads(Path(json_path).read_text())
        assert data["pr_id"] == 10


class TestQAAgentSpec:
    def test_spec(self):
        from jarvis.agents.qa.agent import QAAgent
        agent = QAAgent()
        s = agent.spec()
        assert s.id == "qa.analyzer"
        assert "analyze_pr" in s.skills
        assert "qa" in s.skills

    def test_can_handle(self):
        from jarvis.agents.qa.agent import QAAgent
        agent = QAAgent()
        assert agent.can_handle("analyze_pr", "integratepie") is True
        assert agent.can_handle("qa", "personal") is True
