"""Claude Code Provider — usa Claude Max empresarial via CLI subprocess."""

from __future__ import annotations

import json
import shutil
import subprocess
import time

from jarvis.llm.base import LLMRequest, LLMResponse, ProviderStatus


class ClaudeCodeProvider:
    """Proveedor que ejecuta Claude Code CLI como subprocess.

    Usa la sesión autenticada de Claude Max (empresarial).
    No necesita API key — usa la autenticación existente del CLI.
    """

    def __init__(self, max_turns: int = 1, timeout: int = 60):
        self._max_turns = max_turns
        self._timeout = timeout
        self._cli_path = shutil.which("claude")

    @property
    def provider_id(self) -> str:
        return "claude_code"

    @property
    def model_name(self) -> str:
        return "claude-via-cli"

    def is_available(self) -> bool:
        return self._cli_path is not None

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._cli_path:
            raise RuntimeError("Claude Code CLI no encontrado")

        prompt = request.prompt
        if request.system:
            prompt = f"{request.system}\n\n{prompt}"

        start = time.monotonic()
        try:
            result = subprocess.run(
                [
                    self._cli_path,
                    "-p", prompt,
                    "--output-format", "json",
                    "--max-turns", str(self._max_turns),
                    "--no-input",
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)

            if result.returncode != 0:
                error = result.stderr[:200] if result.stderr else "Unknown error"
                raise RuntimeError(f"Claude Code error: {error}")

            # Parsear respuesta JSON
            try:
                data = json.loads(result.stdout)
                content = data.get("result", result.stdout)
                cost = data.get("cost_usd", 0.0)
                input_tokens = data.get("input_tokens", 0)
                output_tokens = data.get("output_tokens", 0)
                model = data.get("model", "claude-via-cli")
            except (json.JSONDecodeError, TypeError):
                content = result.stdout.strip()
                cost = 0.0
                input_tokens = 0
                output_tokens = 0
                model = "claude-via-cli"

            return LLMResponse(
                content=content,
                provider="claude_code",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=elapsed_ms,
                cost_usd=cost,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            raise RuntimeError(f"Claude Code timeout ({self._timeout}s)")

    def status(self) -> ProviderStatus:
        if self.is_available():
            return ProviderStatus(provider="claude_code", available=True, model="claude-via-cli")
        return ProviderStatus(provider="claude_code", available=False, error="CLI no encontrado")
