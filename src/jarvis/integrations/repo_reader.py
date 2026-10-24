"""Repo Reader — acceso controlado de solo lectura a repositorios locales.

Permite a JARVIS leer código, estructura y configuración de los repos
sin modificar nada. Cada repo tiene su propia política de acceso.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RepoConfig:
    """Configuración de acceso a un repositorio."""
    project: str
    path: str
    allowed_patterns: list[str] = field(default_factory=list)  # Globs permitidos
    denied_patterns: list[str] = field(default_factory=list)   # Globs denegados
    read_only: bool = True


# Repositorios conocidos
KNOWN_REPOS: dict[str, RepoConfig] = {
    "kamecol": RepoConfig(
        project="kamecol",
        path=os.path.expanduser("~/Developer/Personal/kame.colStore"),
        allowed_patterns=["*.py", "*.ts", "*.tsx", "*.json", "*.toml", "*.yml", "*.md", "*.html", "*.css"],
        denied_patterns=[".env", "*.sqlite3", "*.db", "media/*", "node_modules/*", "__pycache__/*"],
    ),
    "iaagent": RepoConfig(
        project="iaagent",
        path=os.path.expanduser("~/Developer/Personal/IaAgent"),
        allowed_patterns=["*.py", "*.md", "*.toml", "*.json"],
        denied_patterns=[".env", "*.db", "workspace/*", "__pycache__/*"],
    ),
    "jarvis": RepoConfig(
        project="personal",
        path=os.path.expanduser("~/Developer/Personal/jarvis"),
        allowed_patterns=["*.py", "*.md", "*.toml", "*.html"],
        denied_patterns=[".env", "data/*", "*.db"],
    ),
}


class RepoReader:
    """Acceso de solo lectura a repositorios locales."""

    def __init__(self, config: RepoConfig):
        self._config = config
        self._root = Path(config.path)

    @property
    def exists(self) -> bool:
        return self._root.exists()

    def get_structure(self, max_depth: int = 3) -> list[str]:
        """Obtener estructura de directorios (sin archivos denegados)."""
        if not self.exists:
            return []

        result = []
        self._walk(self._root, result, depth=0, max_depth=max_depth)
        return result

    def read_file(self, relative_path: str) -> str | None:
        """Leer un archivo si está permitido."""
        if not self.exists:
            return None

        path = self._root / relative_path
        if not path.exists() or not path.is_file():
            return None

        if not self._is_allowed(relative_path):
            return None

        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def search_code(self, pattern: str, file_glob: str = "*.py", max_results: int = 20) -> list[dict]:
        """Buscar patrón en el código usando grep."""
        if not self.exists:
            return []

        try:
            result = subprocess.run(
                ["grep", "-rn", "--include", file_glob, "-m", str(max_results), pattern, str(self._root)],
                capture_output=True, text=True, timeout=10,
            )
            matches = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    filepath = parts[0].replace(str(self._root) + "/", "")
                    if self._is_allowed(filepath):
                        matches.append({
                            "file": filepath,
                            "line": int(parts[1]) if parts[1].isdigit() else 0,
                            "content": parts[2].strip()[:200],
                        })
            return matches[:max_results]
        except (subprocess.TimeoutExpired, Exception):
            return []

    def get_git_log(self, limit: int = 10) -> list[dict]:
        """Obtener últimos commits."""
        if not self.exists:
            return []

        try:
            result = subprocess.run(
                ["git", "-C", str(self._root), "log", f"--max-count={limit}",
                 "--pretty=format:%H|%an|%ad|%s", "--date=short"],
                capture_output=True, text=True, timeout=10,
            )
            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0][:8],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    })
            return commits
        except Exception:
            return []

    def _is_allowed(self, relative_path: str) -> bool:
        """Verificar si un archivo está permitido según la política."""
        from fnmatch import fnmatch

        # Denegar tiene prioridad
        for pattern in self._config.denied_patterns:
            if fnmatch(relative_path, pattern) or fnmatch(Path(relative_path).name, pattern):
                return False

        # Si hay allowed_patterns, debe coincidir con al menos uno
        if self._config.allowed_patterns:
            return any(
                fnmatch(Path(relative_path).name, p) or fnmatch(relative_path, p)
                for p in self._config.allowed_patterns
            )
        return True

    def _walk(self, path: Path, result: list, depth: int, max_depth: int):
        if depth > max_depth:
            return
        try:
            for item in sorted(path.iterdir()):
                rel = str(item.relative_to(self._root))
                if item.name.startswith(".") and item.name not in (".github",):
                    continue
                if any(item.name == skip for skip in ("node_modules", "__pycache__", ".venv", "venv", ".git")):
                    continue
                prefix = "  " * depth
                if item.is_dir():
                    result.append(f"{prefix}{item.name}/")
                    self._walk(item, result, depth + 1, max_depth)
                elif self._is_allowed(rel):
                    result.append(f"{prefix}{item.name}")
        except PermissionError:
            pass


def get_reader(project: str) -> RepoReader | None:
    """Obtener un RepoReader para un proyecto conocido."""
    config = KNOWN_REPOS.get(project)
    if not config:
        return None
    return RepoReader(config)
