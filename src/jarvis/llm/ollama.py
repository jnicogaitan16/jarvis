"""Ollama Provider — modelos locales vía Ollama REST API."""

from __future__ import annotations

import time

import httpx

from jarvis.llm.base import LLMRequest, LLMResponse, ProviderStatus


class OllamaProvider:
    """Proveedor de LLM local usando Ollama."""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def generate(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        start = time.monotonic()
        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama error: {e}") from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()

        content = data.get("message", {}).get("content", "")
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return LLMResponse(
            content=content,
            provider="ollama",
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=elapsed_ms,
            cost_usd=0.0,
        )

    def status(self) -> ProviderStatus:
        if self.is_available():
            return ProviderStatus(provider="ollama", available=True, model=self._model)
        return ProviderStatus(provider="ollama", available=False, error="Ollama no accesible")

    def list_models(self) -> list[str]:
        """Listar modelos disponibles en Ollama."""
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except (httpx.HTTPError, KeyError):
            return []
