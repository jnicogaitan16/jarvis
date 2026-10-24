"""Tests para LLM Router."""

import pytest

from jarvis.core.models import ProjectContext
from jarvis.llm.base import LLMRequest, LLMResponse, ProviderStatus
from jarvis.llm.router import LLMRouter, classify_complexity


# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------

class MockProvider:
    """Provider de prueba que siempre responde."""

    def __init__(self, pid: str = "mock", model: str = "mock-model", available: bool = True):
        self._pid = pid
        self._model = model
        self._available = available
        self.call_count = 0

    @property
    def provider_id(self) -> str:
        return self._pid

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return self._available

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            content=f"Mock response from {self._pid}",
            provider=self._pid,
            model=self._model,
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            latency_ms=100,
            cost_usd=0.001 if self._pid != "ollama" else 0.0,
        )

    def status(self) -> ProviderStatus:
        return ProviderStatus(provider=self._pid, available=self._available, model=self._model)


class FailingProvider(MockProvider):
    """Provider que siempre falla."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        raise RuntimeError(f"{self._pid} falló intencionalmente")


# ---------------------------------------------------------------------------
# Tests classify_complexity
# ---------------------------------------------------------------------------

class TestClassifyComplexity:
    def test_simple(self):
        assert classify_complexity("hola") == "simple"
        assert classify_complexity("qué hora es") == "simple"

    def test_code(self):
        assert classify_complexity("analiza este código PHP") == "code"
        assert classify_complexity("hay un bug en la función") == "code"
        assert classify_complexity("def foo():") == "code"

    def test_complex(self):
        assert classify_complexity("analiza los pros y cons de esta arquitectura") == "complex"
        assert classify_complexity("compara estas dos alternativas") == "complex"
        assert classify_complexity("diseña un sistema de memoria") == "complex"

    def test_medium_by_length(self):
        long_text = "x " * 300  # >500 chars
        assert classify_complexity(long_text) == "medium"


# ---------------------------------------------------------------------------
# Tests LLMRouter
# ---------------------------------------------------------------------------

class TestLLMRouter:
    def _ctx(self, providers=("ollama",), allow_cloud=False):
        return ProjectContext(
            project_id="test",
            display_name="Test",
            allowed_providers=frozenset(providers),
            allow_cloud=allow_cloud,
        )

    def test_register_and_list(self):
        router = LLMRouter()
        mock = MockProvider("ollama")
        router.register(mock)
        statuses = router.available_providers()
        assert len(statuses) == 1
        assert statuses[0].provider == "ollama"

    def test_select_ollama_for_simple(self):
        router = LLMRouter()
        ollama = MockProvider("ollama")
        router.register(ollama)
        ctx = self._ctx(providers=("ollama",))
        req = LLMRequest(prompt="hola")

        provider = router.select_provider(req, ctx)
        assert provider.provider_id == "ollama"

    def test_select_gemini_for_complex_when_cloud_allowed(self):
        router = LLMRouter()
        ollama = MockProvider("ollama")
        gemini = MockProvider("gemini")
        router.register(ollama)
        router.register(gemini)
        ctx = self._ctx(providers=("ollama", "gemini"), allow_cloud=True)
        req = LLMRequest(prompt="analiza los trade-offs de esta arquitectura")

        provider = router.select_provider(req, ctx)
        assert provider.provider_id == "gemini"

    def test_fallback_to_ollama_when_cloud_not_allowed(self):
        router = LLMRouter()
        ollama = MockProvider("ollama")
        gemini = MockProvider("gemini")
        router.register(ollama)
        router.register(gemini)
        ctx = self._ctx(providers=("ollama", "gemini"), allow_cloud=False)
        req = LLMRequest(prompt="analiza los trade-offs de esta arquitectura")

        provider = router.select_provider(req, ctx)
        # Cloud not allowed, so complex task still goes to ollama
        assert provider.provider_id == "ollama"

    def test_fallback_to_available(self):
        router = LLMRouter()
        ollama = MockProvider("ollama", available=False)
        gemini = MockProvider("gemini")
        router.register(ollama)
        router.register(gemini)
        ctx = self._ctx(providers=("ollama", "gemini"), allow_cloud=True)
        req = LLMRequest(prompt="hola")

        provider = router.select_provider(req, ctx)
        assert provider.provider_id == "gemini"

    def test_no_providers_raises(self):
        router = LLMRouter()
        ctx = self._ctx(providers=("ollama",))
        req = LLMRequest(prompt="hola")

        with pytest.raises(RuntimeError, match="Sin proveedores"):
            router.select_provider(req, ctx)

    def test_generate_success(self):
        router = LLMRouter()
        mock = MockProvider("ollama")
        router.register(mock)
        ctx = self._ctx(providers=("ollama",))
        req = LLMRequest(prompt="hola")

        resp = router.generate(req, ctx)
        assert resp.content == "Mock response from ollama"
        assert mock.call_count == 1

    def test_generate_fallback_on_error(self):
        router = LLMRouter()
        failing = FailingProvider("ollama")
        backup = MockProvider("gemini")
        router.register(failing)
        router.register(backup)
        ctx = self._ctx(providers=("ollama", "gemini"), allow_cloud=True)
        req = LLMRequest(prompt="hola")

        resp = router.generate(req, ctx)
        assert resp.provider == "gemini"
        assert failing.call_count == 1
        assert backup.call_count == 1

    def test_generate_all_fail(self):
        router = LLMRouter()
        f1 = FailingProvider("ollama")
        f2 = FailingProvider("gemini")
        router.register(f1)
        router.register(f2)
        ctx = self._ctx(providers=("ollama", "gemini"), allow_cloud=True)
        req = LLMRequest(prompt="hola")

        with pytest.raises(RuntimeError, match="Todos los proveedores fallaron"):
            router.generate(req, ctx)

    def test_policy_restricts_provider(self):
        router = LLMRouter()
        ollama = MockProvider("ollama")
        gemini = MockProvider("gemini")
        router.register(ollama)
        router.register(gemini)
        # Only ollama allowed
        ctx = self._ctx(providers=("ollama",), allow_cloud=False)
        req = LLMRequest(prompt="analiza esto en profundidad")

        provider = router.select_provider(req, ctx)
        assert provider.provider_id == "ollama"
