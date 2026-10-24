"""Tests para modelos base de LLM."""

from jarvis.llm.base import (
    LLMRequest,
    LLMResponse,
    ProviderStatus,
    TaskComplexity,
)


class TestLLMRequest:
    def test_create_minimal(self):
        req = LLMRequest(prompt="hola")
        assert req.prompt == "hola"
        assert req.system == ""
        assert req.max_tokens == 2048
        assert req.temperature == 0.7
        assert req.project == "personal"

    def test_create_full(self):
        req = LLMRequest(
            prompt="analiza este código",
            system="Eres un QA senior",
            max_tokens=4096,
            temperature=0.3,
            project="integratepie",
        )
        assert req.project == "integratepie"
        assert req.system == "Eres un QA senior"

    def test_frozen(self):
        req = LLMRequest(prompt="test")
        try:
            req.prompt = "other"
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestLLMResponse:
    def test_create(self):
        resp = LLMResponse(
            content="Hola, soy JARVIS",
            provider="ollama",
            model="qwen2.5:7b",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            latency_ms=500,
            cost_usd=0.0,
        )
        assert resp.content == "Hola, soy JARVIS"
        assert resp.provider == "ollama"
        assert resp.total_tokens == 30
        assert resp.cost_usd == 0.0

    def test_defaults(self):
        resp = LLMResponse(content="test", provider="test", model="test")
        assert resp.input_tokens == 0
        assert resp.cost_usd == 0.0
        assert resp.cached is False


class TestProviderStatus:
    def test_available(self):
        ps = ProviderStatus(provider="ollama", available=True, model="qwen2.5:7b")
        assert ps.available is True

    def test_unavailable(self):
        ps = ProviderStatus(provider="gemini", available=False, error="No API key")
        assert ps.available is False
        assert ps.error == "No API key"


class TestTaskComplexity:
    def test_values(self):
        assert TaskComplexity.SIMPLE == "simple"
        assert TaskComplexity.COMPLEX == "complex"
        assert TaskComplexity.CODE == "code"
