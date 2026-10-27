"""Embeddings — generación y similitud vectorial."""

from __future__ import annotations

import math

import httpx


def generate_embedding(
    text: str,
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
) -> list[float] | None:
    """Generar embedding vía Ollama. Retorna None si no está disponible."""
    try:
        resp = httpx.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        return None
    except (httpx.HTTPError, httpx.ConnectError, KeyError):
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcular similitud coseno entre dos vectores."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
