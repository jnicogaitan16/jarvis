"""Azure DevOps Integration — extensiones para JARVIS.

Extiende el client de IAAgent con capacidades de work items
y publicación controlada con aprobación humana.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

import httpx


@dataclass(frozen=True)
class WorkItem:
    """Work item de Azure DevOps (PBI, Bug, Task, etc.)."""
    id: int
    title: str
    work_item_type: str
    state: str
    description: str = ""
    acceptance_criteria: str = ""
    assigned_to: str = ""
    tags: list[str] = field(default_factory=list)
    parent_id: int | None = None
    children_ids: list[int] = field(default_factory=list)
    url: str = ""


class _HTMLStripper(HTMLParser):
    """Elimina tags HTML y retorna texto plano."""
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts).strip()


def _strip_html(html: str) -> str:
    if not html:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


class AzureDevOpsExtended:
    """Cliente extendido de Azure DevOps para work items y publicación controlada."""

    def __init__(
        self,
        org_url: str | None = None,
        pat: str | None = None,
        project: str | None = None,
    ):
        self._org_url = (org_url or os.environ.get("AZDO_ORG_URL", "")).rstrip("/")
        self._pat = pat or os.environ.get("AZDO_PAT", "")
        self._project = project or os.environ.get("AZDO_PROJECT", "")
        self._headers = self._build_headers()

    def _build_headers(self) -> dict:
        if not self._pat:
            return {}
        encoded = base64.b64encode(f":{self._pat}".encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self._org_url and self._pat and self._project)

    # ------------------------------------------------------------------
    # Work Items
    # ------------------------------------------------------------------

    def get_work_item(self, work_item_id: int, expand: str = "Relations") -> WorkItem | None:
        """Obtener un work item por ID con relaciones."""
        if not self.is_configured:
            return None

        url = f"{self._org_url}/{self._project}/_apis/wit/workitems/{work_item_id}?$expand={expand}&api-version=7.1"
        try:
            resp = httpx.get(url, headers=self._headers, timeout=15)
            resp.raise_for_status()
            return self._parse_work_item(resp.json())
        except httpx.HTTPError:
            return None

    def get_work_items_batch(self, ids: list[int]) -> list[WorkItem]:
        """Obtener múltiples work items por IDs."""
        if not self.is_configured or not ids:
            return []

        url = f"{self._org_url}/{self._project}/_apis/wit/workitems?ids={','.join(str(i) for i in ids)}&$expand=Relations&api-version=7.1"
        try:
            resp = httpx.get(url, headers=self._headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return [self._parse_work_item(item) for item in data.get("value", [])]
        except httpx.HTTPError:
            return []

    def get_pr_work_items(self, pr_id: int, repository_id: str | None = None) -> list[WorkItem]:
        """Obtener work items vinculados a un PR."""
        if not self.is_configured:
            return []

        # Primero obtener los work item refs del PR
        repo_segment = f"/{repository_id}" if repository_id else ""
        url = (
            f"{self._org_url}/{self._project}/_apis/git/repositories"
            f"{repo_segment}/pullRequests/{pr_id}/workitems?api-version=7.1"
        )
        try:
            resp = httpx.get(url, headers=self._headers, timeout=15)
            resp.raise_for_status()
            refs = resp.json().get("value", [])
            if not refs:
                return []
            ids = [int(ref.get("id", 0)) for ref in refs if ref.get("id")]
            return self.get_work_items_batch(ids)
        except httpx.HTTPError:
            return []

    def _parse_work_item(self, data: dict) -> WorkItem:
        fields = data.get("fields", {})
        relations = data.get("relations", []) or []

        # Extraer parent y children de relaciones
        parent_id = None
        children_ids = []
        for rel in relations:
            rel_type = rel.get("attributes", {}).get("name", "")
            rel_url = rel.get("url", "")
            wi_id_match = re.search(r"/workItems/(\d+)$", rel_url)
            if wi_id_match:
                wi_id = int(wi_id_match.group(1))
                if rel_type == "Parent":
                    parent_id = wi_id
                elif rel_type == "Child":
                    children_ids.append(wi_id)

        assigned_to = ""
        assigned = fields.get("System.AssignedTo")
        if isinstance(assigned, dict):
            assigned_to = assigned.get("displayName", "")

        tags_str = fields.get("System.Tags", "")
        tags = [t.strip() for t in tags_str.split(";") if t.strip()] if tags_str else []

        wi_url = ""
        links = data.get("_links", {})
        if links and "html" in links:
            wi_url = links["html"].get("href", "")

        return WorkItem(
            id=data.get("id", 0),
            title=fields.get("System.Title", ""),
            work_item_type=fields.get("System.WorkItemType", ""),
            state=fields.get("System.State", ""),
            description=_strip_html(fields.get("System.Description", "")),
            acceptance_criteria=_strip_html(
                fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")
            ),
            assigned_to=assigned_to,
            tags=tags,
            parent_id=parent_id,
            children_ids=children_ids,
            url=wi_url,
        )

    # ------------------------------------------------------------------
    # Publisher con aprobación
    # ------------------------------------------------------------------

    def prepare_comment(self, pr_id: int, content: str, evidence_paths: list[str] | None = None) -> dict:
        """Preparar un comentario para publicación (sin publicar).

        Retorna un dict con toda la información necesaria para aprobar y publicar.
        """
        return {
            "pr_id": pr_id,
            "content": content,
            "evidence_paths": evidence_paths or [],
            "status": "pending_approval",
            "preview": content[:500] + ("..." if len(content) > 500 else ""),
        }

    def publish_comment(self, pr_id: int, content: str, repository_id: str | None = None) -> dict:
        """Publicar un comentario en un PR. Solo llamar tras aprobación humana.

        Usa el client de IAAgent si está disponible, o llama directamente a la API.
        """
        if not self.is_configured:
            return {"success": False, "error": "Azure DevOps no configurado"}

        # Intentar usar IAAgent client (más maduro)
        try:
            from jarvis.integrations.iaagent_bridge import get_azure_devops_client, is_available
            if is_available():
                azdo_mod = get_azure_devops_client()
                client = azdo_mod.AzureDevOpsClient(
                    org_url=self._org_url,
                    pat=self._pat,
                    project=self._project,
                )
                result = client.post_pr_comment(pr_id, content)
                return {"success": True, "comment_id": result.get("id"), "data": result}
        except Exception:
            pass

        # Fallback: llamada directa a la API
        repos = self._get_repositories()
        if not repos:
            return {"success": False, "error": "No se encontraron repositorios"}

        repo_id = repository_id or repos[0]["id"]
        url = (
            f"{self._org_url}/{self._project}/_apis/git/repositories/{repo_id}"
            f"/pullRequests/{pr_id}/threads?api-version=7.1"
        )
        body = {
            "comments": [{"content": content, "commentType": 1}],
            "status": 1,
        }
        try:
            resp = httpx.post(url, headers=self._headers, json=body, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "thread_id": data.get("id"), "data": data}
        except httpx.HTTPError as e:
            return {"success": False, "error": str(e)}

    def _get_repositories(self) -> list[dict]:
        url = f"{self._org_url}/{self._project}/_apis/git/repositories?api-version=7.1"
        try:
            resp = httpx.get(url, headers=self._headers, timeout=10)
            resp.raise_for_status()
            return resp.json().get("value", [])
        except httpx.HTTPError:
            return []
