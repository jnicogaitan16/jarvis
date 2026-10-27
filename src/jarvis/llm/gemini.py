"""Gemini Provider — Google Gemini API vía REST (httpx)."""

from __future__ import annotations

import os
import time

import httpx

from jarvis.llm.base import LLMRequest, LLMResponse, ProviderStatus

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Pricing per million tokens (Gemini 2.5 Flash, as of 2026)
_INPUT_COST_PER_M = 0.15
_OUTPUT_COST_PER_M = 0.60


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * _INPUT_COST_PER_M + output_tokens * _OUTPUT_COST_PER_M) / 1_000_000


class GeminiProvider:
    """Proveedor cloud usando Google Gemini API."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self._model = model
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")

        contents = []
        if request.system:
            contents.append({"role": "user", "parts": [{"text": request.system}]})
            contents.append({"role": "model", "parts": [{"text": "Entendido."}]})
        contents.append({"role": "user", "parts": [{"text": request.prompt}]})

        url = f"{_GEMINI_BASE}/{self._model}:generateContent?key={self._api_key}"
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            start = time.monotonic()
            try:
                resp = httpx.post(url, json=body, timeout=self._timeout)
                if resp.status_code == 429:
                    last_error = RuntimeError(f"Rate limited (429), intento {attempt + 1}")
                    time.sleep(self._retry_delay * (2 ** attempt))
                    continue
                resp.raise_for_status()
                break
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (2 ** attempt))
                continue
            except httpx.HTTPError as e:
                raise RuntimeError(f"Gemini API error: {e}") from e
        else:
            raise RuntimeError(f"Gemini falló tras {self._max_retries} intentos: {last_error}")

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini sin candidatos: {data}")

        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        return LLMResponse(
            content=content,
            provider="gemini",
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=elapsed_ms,
            cost_usd=_estimate_cost(input_tokens, output_tokens),
        )

    def status(self) -> ProviderStatus:
        if self.is_available():
            return ProviderStatus(provider="gemini", available=True, model=self._model)
        return ProviderStatus(
            provider="gemini", available=False, error="GEMINI_API_KEY no configurada"
        )
