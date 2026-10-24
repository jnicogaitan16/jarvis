"""Tests para IAAgent Bridge — verifican que los componentes se importan y funcionan."""

import pytest

from jarvis.integrations.iaagent_bridge import is_available

# Saltar todos los tests si IAAgent no está disponible
pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="IAAgent no disponible en esta máquina",
)


class TestBridgeImports:
    def test_iaagent_is_available(self):
        assert is_available() is True

    def test_import_diff_analyzer(self):
        from jarvis.integrations.iaagent_bridge import get_diff_analyzer
        mod = get_diff_analyzer()
        assert hasattr(mod, "DiffAnalyzer")

    def test_import_security_analyzer(self):
        from jarvis.integrations.iaagent_bridge import get_security_analyzer
        mod = get_security_analyzer()
        assert hasattr(mod, "SecurityAnalyzer")

    def test_import_static_analyzer(self):
        from jarvis.integrations.iaagent_bridge import get_static_analyzer
        mod = get_static_analyzer()
        assert hasattr(mod, "StaticAnalyzer")

    def test_import_risk_engine(self):
        from jarvis.integrations.iaagent_bridge import get_risk_engine
        mod = get_risk_engine()
        assert hasattr(mod, "RiskEngine")

    def test_import_test_case_generator(self):
        from jarvis.integrations.iaagent_bridge import get_test_case_generator
        mod = get_test_case_generator()
        assert hasattr(mod, "TestCaseGenerator")

    def test_import_pr_context_models(self):
        from jarvis.integrations.iaagent_bridge import get_pr_context_models
        mod = get_pr_context_models()
        assert hasattr(mod, "PRContext")
        assert hasattr(mod, "PRMetadata")
        assert hasattr(mod, "DiffEntry")
        assert hasattr(mod, "FileChange")

    def test_import_analysis_models(self):
        from jarvis.integrations.iaagent_bridge import get_analysis_models
        mod = get_analysis_models()
        assert hasattr(mod, "Finding")
        assert hasattr(mod, "RiskScore")
        assert hasattr(mod, "TestCase")
        assert hasattr(mod, "Severity")


class TestDiffAnalyzerIntegration:
    """Verificar que DiffAnalyzer produce resultados reales."""

    def test_analyze_empty_pr(self):
        from jarvis.integrations.iaagent_bridge import get_diff_analyzer, get_pr_context_models
        mod = get_diff_analyzer()
        models = get_pr_context_models()

        metadata = models.PRMetadata(pr_id=1, title="Test PR")
        ctx = models.PRContext(metadata=metadata)
        result = mod.DiffAnalyzer().analyze(ctx)

        assert result.stats.total_files == 0

    def test_analyze_pr_with_diff(self):
        from jarvis.integrations.iaagent_bridge import get_diff_analyzer, get_pr_context_models
        mod = get_diff_analyzer()
        models = get_pr_context_models()

        diff_text = """--- a/app/test.py
+++ b/app/test.py
@@ -1,3 +1,5 @@
+import os
+
 def hello():
-    return "hello"
+    return "world"
"""
        metadata = models.PRMetadata(pr_id=1, title="Test")
        diff = models.DiffEntry.from_raw("app/test.py", diff_text)
        change = models.FileChange(path="app/test.py", change_type=models.ChangeType.EDIT)
        ctx = models.PRContext(metadata=metadata, diffs=[diff], changes=[change])

        result = mod.DiffAnalyzer().analyze(ctx)
        assert result.stats.total_files >= 1
        assert result.stats.total_added >= 2


class TestSecurityAnalyzerIntegration:
    """Verificar que SecurityAnalyzer detecta vulnerabilidades."""

    def test_detect_hardcoded_secret(self):
        from jarvis.integrations.iaagent_bridge import get_pr_context_models, get_security_analyzer
        mod = get_security_analyzer()
        models = get_pr_context_models()

        diff_text = """--- a/config.py
+++ b/config.py
@@ -1,2 +1,3 @@
+API_KEY = "sk_live_abc123456789012345678"
 DB_HOST = "localhost"
"""
        metadata = models.PRMetadata(pr_id=1, title="Test")
        diff = models.DiffEntry.from_raw("config.py", diff_text)
        change = models.FileChange(path="config.py", change_type=models.ChangeType.EDIT)
        ctx = models.PRContext(metadata=metadata, diffs=[diff], changes=[change])

        findings = mod.SecurityAnalyzer().analyze(ctx)
        assert len(findings) >= 1


class TestToolsRegistration:
    def test_register_qa_tools(self):
        from jarvis.tools.qa.analyzers import register_qa_tools
        from jarvis.tools.registry import ToolRegistry

        registry = ToolRegistry()
        count = register_qa_tools(registry)
        assert count == 5
        assert registry.get("qa.diff_analyzer") is not None
        assert registry.get("qa.security_analyzer") is not None
        assert registry.get("qa.static_analyzer") is not None
        assert registry.get("qa.risk_engine") is not None
        assert registry.get("qa.test_case_generator") is not None


class TestToolExecution:
    """Verificar que los tools wrappean correctamente los analyzers."""

    def test_diff_analyzer_tool(self):
        from jarvis.core.models import ProjectContext, ToolAction
        from jarvis.tools.qa.analyzers import DiffAnalyzerTool

        tool = DiffAnalyzerTool()
        action = ToolAction(
            tool_id="qa.diff_analyzer",
            parameters={
                "pr_id": 1,
                "title": "Test PR",
                "diffs": [{"path": "app/test.py", "diff_text": "+def foo(): pass"}],
                "changes": [{"path": "app/test.py", "change_type": "edit"}],
            },
        )
        ctx = ProjectContext(project_id="test", display_name="Test")
        obs = tool.execute(action, ctx)
        assert obs.success is True
        assert "stats" in obs.result

    def test_security_analyzer_tool_detects_secret(self):
        from jarvis.core.models import ProjectContext, ToolAction
        from jarvis.tools.qa.analyzers import SecurityAnalyzerTool

        tool = SecurityAnalyzerTool()
        action = ToolAction(
            tool_id="qa.security_analyzer",
            parameters={
                "pr_id": 1,
                "title": "Test",
                "diffs": [{
                    "path": "config.py",
                    "diff_text": '+password = "super_secret_123"\n',
                }],
                "changes": [{"path": "config.py", "change_type": "edit"}],
            },
        )
        ctx = ProjectContext(project_id="test", display_name="Test")
        obs = tool.execute(action, ctx)
        assert obs.success is True
        assert obs.result["total"] >= 1
