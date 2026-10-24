# Fase 1 — JARVIS Core: Plan de Implementación

**Objetivo:** Construir el núcleo mínimo funcional de JARVIS.

Fecha: 2026-10-24

---

## 1. Alcance

Al finalizar esta fase, JARVIS tendrá:
- Repositorio Git con estructura profesional.
- Entorno virtual Python 3.12+.
- CLI funcional con Typer.
- Sistema de configuración TOML.
- Event stream persistido en SQLite.
- Modelos Pydantic para contratos core.
- ProjectContext con aislamiento básico.
- Tests con pytest.

**No incluye:** LLM, memoria semántica, agentes, integrations.

---

## 2. Prerequisitos

- [x] Plan maestro y arquitectura documentados (Fase 0)
- [ ] Python 3.12+ instalado en Mac mini
- [ ] Ollama instalado (para Fase 2, pero verificar disponibilidad)
- [ ] Git instalado y configurado

---

## 3. Tareas ordenadas

### Semana 1: Estructura y fundamentos

#### Día 1: Repositorio y entorno

**J-001: Inicializar repositorio Git**
```bash
cd /Users/nicogaitan/Developer/Personal/jarvis
git init
```

Crear `.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/

# Environment
.env

# Data
data/
*.db

# IDE
.vscode/
.idea/
.cursor/

# OS
.DS_Store
```

**J-002: Crear entorno virtual**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

**J-003: Configurar pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "jarvis"
version = "0.1.0"
description = "Plataforma personal de IA híbrida con agentes especializados"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.12.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
]

[project.scripts]
jarvis = "jarvis.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/jarvis"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

```bash
pip install -e ".[dev]"
```

#### Día 2: Estructura de directorios y modelos core

**J-004: Crear estructura del MVP**

```bash
mkdir -p src/jarvis/{core,agents,tools,llm,memory,jobs,security,integrations}
mkdir -p config/{prompts,projects}
mkdir -p data
mkdir -p tests/{unit,integration}
```

Crear `__init__.py` en cada directorio de `src/jarvis/`.

**J-006: Implementar modelos Pydantic core**

Archivo: `src/jarvis/core/models.py`

Modelos a implementar:
- `Event` — Evento inmutable del event stream.
- `ProjectContext` — Contexto de proyecto con permisos.
- `ToolAction` — Input tipado para herramientas.
- `ToolObservation` — Output tipado de herramientas.
- `JobStatus` — Estados de un trabajo.
- `MemoryRecord` — Registro de memoria.

Todos con Pydantic v2, frozen cuando corresponda.

#### Día 3: Event stream

**J-007: Implementar Event Stream en SQLite**

Archivo: `src/jarvis/core/events.py`

```python
class EventStore:
    """Almacén de eventos inmutables en SQLite."""

    def __init__(self, db_path: str = "data/jarvis.db"):
        ...

    def emit(self, event_type: str, payload: dict, **kwargs) -> Event:
        """Registrar un evento. Append-only."""
        ...

    def query(self, event_type: str = None, project: str = None,
              since: datetime = None, limit: int = 100) -> list[Event]:
        """Consultar eventos con filtros."""
        ...
```

La tabla `events` se crea automáticamente al inicializar el store.

#### Día 4: Configuración

**J-008: Sistema de configuración TOML**

Archivo: `src/jarvis/config.py`

Estructura de configuración:
```
config/
├── jarvis.toml              # Config global
├── projects/
│   ├── integratepie.toml    # Config IntegratePIE
│   ├── kamecol.toml         # Config KameCol
│   └── personal.toml        # Config personal
└── prompts/                 # Templates (vacío inicialmente)
```

**J-010: .env.example**

```env
# JARVIS Configuration
JARVIS_ENV=development

# Gemini API (opcional — Fase 2)
# GEMINI_API_KEY=

# Azure DevOps (opcional — Fase 5+)
# AZDO_PAT=
# AZDO_ORG_URL=
# AZDO_PROJECT=

# KameCol (opcional — Fase 8)
# KAMECOL_API_URL=
# KAMECOL_API_KEY=
```

#### Día 5: Seguridad y CLI

**J-009: ProjectContext y SecurityGate**

Archivo: `src/jarvis/security/context.py`

```python
class SecurityGate:
    def check_tool_access(self, tool_id: str, context: ProjectContext) -> bool:
        ...

    def check_memory_access(self, target_project: str, context: ProjectContext) -> bool:
        ...

    def sanitize_for_logging(self, text: str) -> str:
        """Redacta credenciales y PII."""
        ...
```

**J-005: CLI básico con Typer**

Archivo: `src/jarvis/cli.py`

Comandos de la Fase 1:
```python
app = typer.Typer(name="jarvis")

@app.command()
def ask(question: str, project: str = "personal"):
    """Hacer una pregunta a JARVIS."""
    # Fase 1: respuesta estática con event logging
    # Fase 2: respuesta con LLM
    ...

@app.command()
def status():
    """Ver estado del sistema."""
    ...

@app.command()
def version():
    """Ver versión de JARVIS."""
    ...
```

### Semana 2: Tests y refinamiento

#### Días 6-7: Tests

**J-012: Configurar pytest**

Archivo: `tests/conftest.py`

Fixtures:
- `tmp_db`: SQLite temporal para tests.
- `event_store`: EventStore con DB temporal.
- `project_context`: ProjectContext de prueba.

**J-011: Tests unitarios**

Tests a escribir:
```
tests/
├── unit/
│   ├── test_models.py          # Validación de modelos Pydantic
│   ├── test_events.py          # Event stream CRUD + queries
│   ├── test_config.py          # Carga de TOML, defaults
│   ├── test_security.py        # ProjectContext, SecurityGate, sanitizer
│   └── test_cli.py             # Comandos CLI básicos
└── conftest.py
```

Cobertura mínima: >80% de `core/`, `security/`, `config.py`.

#### Días 8-9: Integración y documentación

- Verificar que `pip install -e .` funciona en un venv limpio.
- Verificar que `jarvis ask "hola"` funciona end-to-end.
- Verificar que los eventos se persisten.
- Actualizar README.md con instrucciones de setup.

#### Día 10: Review y preparación de Fase 2

- Revisar todos los archivos creados.
- Limpiar TODO comments.
- Verificar que `.gitignore` cubre todo lo necesario.
- Crear branch `develop` o trabajar en `main` con commits atómicos.
- Documentar cualquier decisión que difiera del plan.

---

## 4. Dependencias mínimas (Fase 1)

```
typer>=0.12.0          # CLI
rich>=13.0.0           # Console output
pydantic>=2.0.0        # Modelos y validación
python-dotenv>=1.0.0   # Variables de entorno
```

**Dev:**
```
pytest>=8.0.0
pytest-cov>=5.0.0
```

**No instalar aún:** FastAPI, Huey, httpx, Ollama SDK, google-genai. Se agregan en las fases correspondientes.

---

## 5. Criterios de aceptación de la Fase 1

- [ ] `pip install -e .` instala JARVIS en el venv sin errores.
- [ ] `jarvis version` muestra "JARVIS v0.1.0".
- [ ] `jarvis ask "hola"` responde (aunque sea mensaje estático).
- [ ] `jarvis status` muestra información del sistema.
- [ ] Los eventos se persisten en `data/jarvis.db`.
- [ ] `pytest` pasa con >80% cobertura de core.
- [ ] `.env.example` documenta variables necesarias.
- [ ] Config TOML se carga correctamente.
- [ ] ProjectContext valida namespaces.
- [ ] SecurityGate sanitiza credenciales en logs.
- [ ] La estructura de directorios coincide con el diseño documentado.

---

## 6. Notas para el desarrollador

- **Entorno virtual primero:** `python3 -m venv .venv && source .venv/bin/activate` antes de cualquier `pip install`.
- **Commits atómicos:** Un commit por tarea completada (J-001, J-002, etc.).
- **No sobre-diseñar:** Si algo no es necesario para la Fase 1, no lo construyas.
- **Tests desde el inicio:** Escribir tests junto con el código, no después.
- **SQLite en `data/`:** El directorio `data/` está en `.gitignore`. Se crea automáticamente al primer uso.
- **Pydantic v2 estricto:** Usar `model_config = ConfigDict(strict=True)` donde corresponda.

---

## 7. Preparación para Fase 2

Al terminar la Fase 1, el sistema estará listo para:
- Agregar `llm/` con OllamaProvider y GeminiProvider.
- Agregar `httpx` y `google-genai` como dependencias.
- El LLM Router se conectará al Event Stream y Config existentes.
- El CLI `ask` evolucionará de respuesta estática a respuesta LLM.
