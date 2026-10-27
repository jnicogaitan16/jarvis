"""Memory Manager — interfaz unificada para memoria persistente de JARVIS."""

from __future__ import annotations

from jarvis.core.models import MemoryRecord, MemoryType, ProjectContext
from jarvis.memory.embeddings import cosine_similarity, generate_embedding
from jarvis.memory.store import MemoryStore


class MemoryManager:
    """Gestiona memoria persistente con búsqueda híbrida y aislamiento de proyectos."""

    def __init__(self, store: MemoryStore, embeddings_enabled: bool = True):
        self._store = store
        self._embeddings_enabled = embeddings_enabled

    # ------------------------------------------------------------------
    # Operaciones CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        content: str,
        project: str,
        source: str = "user",
        memory_type: MemoryType = MemoryType.SEMANTIC,
        confidence: float = 1.0,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> MemoryRecord:
        """Agregar un registro de memoria con embedding opcional."""
        record = MemoryRecord(
            project=project,
            memory_type=memory_type,
            source=source,
            content=content,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {},
        )
        record = self._store.add(record)

        if self._embeddings_enabled:
            embedding = generate_embedding(content)
            if embedding:
                self._store.store_embedding(record.id, embedding)

        return record

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._store.get(record_id)

    def update(self, record_id: str, **kwargs) -> bool:
        """Actualizar un registro. Regenera embedding si content cambia."""
        result = self._store.update(record_id, **kwargs)
        if result and "content" in kwargs and self._embeddings_enabled:
            embedding = generate_embedding(kwargs["content"])
            if embedding:
                self._store.store_embedding(record_id, embedding)
        return result

    def invalidate(self, record_id: str) -> bool:
        """Marcar un registro como invalidado."""
        return self._store.update(record_id, status="invalidated")

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        project: str | None = None,
        context: ProjectContext | None = None,
        limit: int = 5,
        fts_weight: float = 0.4,
        semantic_weight: float = 0.6,
    ) -> list[tuple[MemoryRecord, float]]:
        """Búsqueda híbrida: FTS5 + semántica.

        Retorna lista de (record, score) ordenada por relevancia.
        Si no hay embeddings, usa solo FTS5.
        """
        # Aplicar aislamiento de proyecto
        search_project = None
        if context:
            search_project = context.memory_namespace
        elif project:
            search_project = project

        # 1. Búsqueda FTS5
        fts_results = self._store.search_fts(query, project=search_project, limit=limit * 2)

        # 2. Búsqueda semántica (si hay embeddings)
        semantic_results: list[tuple[MemoryRecord, float]] = []
        if self._embeddings_enabled:
            query_embedding = generate_embedding(query)
            if query_embedding:
                candidates = self._store.get_all_with_embeddings(project=search_project)
                for record, emb in candidates:
                    sim = cosine_similarity(query_embedding, emb)
                    semantic_results.append((record, sim))
                semantic_results.sort(key=lambda x: x[1], reverse=True)
                semantic_results = semantic_results[:limit * 2]

        # 3. Combinar resultados
        if not fts_results and not semantic_results:
            return []

        if not semantic_results:
            # Solo FTS disponible
            return fts_results[:limit]

        if not fts_results:
            # Solo semántica disponible
            return semantic_results[:limit]

        # Combinar scores normalizados
        scores: dict[str, tuple[MemoryRecord, float]] = {}

        # FTS: rank es negativo (más negativo = más relevante), normalizar a 0-1
        if fts_results:
            max_rank = max(abs(r[1]) for r in fts_results) or 1.0
            for record, rank in fts_results:
                norm_score = 1.0 - (abs(rank) / max_rank)  # invertir: mayor = mejor
                scores[record.id] = (record, norm_score * fts_weight)

        # Semántica: similarity ya es 0-1
        for record, sim in semantic_results:
            if record.id in scores:
                existing = scores[record.id]
                scores[record.id] = (record, existing[1] + sim * semantic_weight)
            else:
                scores[record.id] = (record, sim * semantic_weight)

        combined = sorted(scores.values(), key=lambda x: x[1], reverse=True)
        return combined[:limit]

    def search_by_project(
        self,
        project: str,
        memory_type: MemoryType | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """Listar registros de un proyecto."""
        return self._store.list_by_project(
            project, memory_type=memory_type, limit=limit
        )

    # ------------------------------------------------------------------
    # Context injection
    # ------------------------------------------------------------------

    def get_context_for_prompt(
        self,
        query: str,
        project: str,
        max_records: int = 5,
        max_chars: int = 3000,
    ) -> str:
        """Recuperar contexto relevante formateado para inyectar en un prompt LLM."""
        results = self.search(query, project=project, limit=max_records)
        if not results:
            return ""

        lines = ["Contexto relevante de memoria:"]
        total_chars = 0
        for record, _score in results:
            entry = f"- [{record.source}] {record.content}"
            if total_chars + len(entry) > max_chars:
                break
            lines.append(entry)
            total_chars += len(entry)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def count(self, project: str | None = None) -> int:
        return self._store.count(project=project)

    def close(self):
        self._store.close()
